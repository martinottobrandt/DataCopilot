import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

# Função para formatar valores em reais (sem usar locale)
def formatar_moeda(valor):
    return f'R$ {valor:,.2f}'.replace(',', 'v').replace('.', ',').replace('v', '.')

# Função para gerar insights iniciais
def gerar_insights(df):
    q1 = df["Valor conta"].quantile(0.25)
    q3 = df["Valor conta"].quantile(0.75)
    iqr = q3 - q1
    limite_superior = q3 + 1.5 * iqr
    outliers = df[df["Valor conta"] > limite_superior]

    resumo_convenio = df.groupby("Convênio")["Valor conta"].agg(
        Quantidade="count",
        Valor_Total="sum"
    ).sort_values(by="Valor_Total", ascending=False)

    contas_90_dias = df[df["Data entrada"] < pd.Timestamp.today() - pd.Timedelta(days=90)]

    zeradas = df[df["Valor conta"] == 0].shape[0]
    sem_alta = df[df.columns[df.columns.str.lower().str.contains("alta")][0]].isna().sum() if any(df.columns.str.lower().str.contains("alta")) else 0

    return f"""
    **Principais insights iniciais:**
    - {zeradas} contas estão com valor zerado, o que pode indicar falha de fechamento, isenção contratual ou erro de sistema.
    - {sem_alta} contas estão associadas a pacientes sem alta, o que pode impactar o ciclo de faturamento e deve ser monitorado.**
    - Cerca de {(df["Valor conta"] < df["Valor conta"].median()).mean()*100:.0f}% das contas possuem valor abaixo de R$ {df["Valor conta"].median():,.2f}, sugerindo foco em resolução de volume com baixo impacto financeiro.
    - {outliers.shape[0]} contas estão acima de R$ {limite_superior:,.2f} (outliers), recomendando revisão prioritária e validação de glosas ou auditoria específica.
    - Os convênios {', '.join(resumo_convenio.head(2).index)} concentram {resumo_convenio.head(2)["Valor_Total"].sum() / resumo_convenio["Valor_Total"].sum() * 100:.0f}% do valor total em aberto e devem ser tratados com régua especial de cobrança.
    - Identificamos {contas_90_dias.shape[0]} contas com mais de 90 dias desde a entrada, indicando falha de processo de fechamento ou cobrança.
    """

st.set_page_config(layout="wide")
st.title("Análise de Contas Pendentes - Hospital")

# Upload do arquivo
uploaded_file = st.file_uploader("Faça upload da planilha Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    primeira_aba = xls.sheet_names[0]
    df = pd.read_excel(xls, sheet_name=primeira_aba)

    # Seleção das colunas relevantes
    colunas = [
        "Status", "Tipo atendimento", "Conta", "Atendimento", "Status atendimento",
        "Convênio", "Categoria", "Valor conta", "Etapa anterior",
        "Último Setor destino", "Setor atendimento", "Estabelecimento",
        "Data entrada", "Médico executor"
    ]
    df = df[colunas].copy()
    df["Valor conta"] = pd.to_numeric(df["Valor conta"], errors="coerce")
    df["Data entrada"] = pd.to_datetime(df["Data entrada"], errors="coerce")
    df["AnoMes"] = df["Data entrada"].dt.to_period("M").astype(str)

    # Filtros gerais de Convênio e Médico
    st.sidebar.header("Filtros Gerais")

    convenios_disponiveis = sorted(df["Convênio"].dropna().unique())
    todos_conv = st.sidebar.checkbox("Selecionar todos os convênios", value=True)
    if todos_conv:
        convenios_filtrados = convenios_disponiveis
    else:
        convenios_filtrados = st.sidebar.multiselect("Convênios:", options=convenios_disponiveis, default=[])

    medicos_disponiveis = sorted(df["Médico executor"].dropna().unique())
    todos_med = st.sidebar.checkbox("Selecionar todos os médicos", value=True)
    if todos_med:
        medicos_filtrados = medicos_disponiveis
    else:
        medicos_filtrados = st.sidebar.multiselect("Médicos:", options=medicos_disponiveis, default=[])

    df = df[df["Convênio"].isin(convenios_filtrados)]
    df = df[df["Médico executor"].isin(medicos_filtrados)]

    with st.expander("📊 Análises Gerais"):
        st.subheader("Distribuição Geral das Contas")
        zeradas_df = df[df["Valor conta"] == 0]
        sem_alta_df = df[df[df.columns[df.columns.str.lower().str.contains("alta")][0]].isna()] if any(df.columns.str.lower().str.contains("alta")) else df.iloc[0:0]
        abaixo_mediana_df = df[df["Valor conta"] < df["Valor conta"].median()]
        negativos_df = df[df["Valor conta"] < 0]
        limite_superior = df["Valor conta"].quantile(0.75) + 1.5 * (df["Valor conta"].quantile(0.75) - df["Valor conta"].quantile(0.25))
        outliers_df = df[df["Valor conta"] > limite_superior]
        antigas_df = df[df["Data entrada"] < pd.Timestamp.today() - pd.Timedelta(days=90)]

        st.markdown("**Principais insights iniciais:**")

        from io import BytesIO

        def gerar_excel_bytes(df, nome_aba):
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name=nome_aba)
            return buffer

        output_outliers = gerar_excel_bytes(outliers_df, "Outliers")
        output_antigas = gerar_excel_bytes(antigas_df, "Mais Antigas")
        output_zeradas = gerar_excel_bytes(zeradas_df, "Zeradas")
        output_sem_alta = gerar_excel_bytes(sem_alta_df, "Sem Alta")
        output_negativos = gerar_excel_bytes(negativos_df, "Negativos")
        output_abaixo = gerar_excel_bytes(abaixo_mediana_df, "Abaixo Mediana")

        insights = [
            (f"{outliers_df.shape[0]} contas são outliers (acima de {formatar_moeda(limite_superior)}).", output_outliers, "contas_outliers.xlsx", "outliers"),
            (f"{antigas_df.shape[0]} contas com mais de 90 dias desde a entrada.", output_antigas, "contas_90_dias.xlsx", "antigas"),
            (f"{zeradas_df.shape[0]} contas estão com valor zerado.", output_zeradas, "contas_zeradas.xlsx", "zeradas"),
            (f"{sem_alta_df.shape[0]} contas estão com pacientes sem alta.", output_sem_alta, "contas_sem_alta.xlsx", "sem_alta"),
            (f"{negativos_df.shape[0]} contas possuem valor negativo.", output_negativos, "contas_valor_negativo.xlsx", "negativos"),
            (f"{abaixo_mediana_df.shape[0]} contas estão abaixo da mediana ({formatar_moeda(df['Valor conta'].median())}).", output_abaixo, "contas_abaixo_mediana.xlsx", "abaixo_mediana")
        ]

        for texto, arquivo, nome_arquivo, chave in insights:
            col1, col2 = st.columns([0.9, 0.1])
            with col1:
                st.markdown(f"- {texto}")
            with col2:
                st.download_button(label="⬇️", data=arquivo.getvalue(), file_name=nome_arquivo, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=chave)
            (f"{outliers_df.shape[0
