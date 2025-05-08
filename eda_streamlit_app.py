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
        ]} contas são outliers (acima de {formatar_moeda(limite_superior)}).", output_outliers, "contas_outliers.xlsx", "outliers"),
            (f"{antigas_df.shape[0]} contas com mais de 90 dias desde a entrada.", output_antigas, "contas_90_dias.xlsx", "antigas"),
            (f"{zeradas_df.shape[0]} contas estão com valor zerado.", output_zeradas, "contas_zeradas.xlsx", "zeradas"),
            (f"{sem_alta_df.shape[0]} contas estão com pacientes sem alta.", output_sem_alta, "contas_sem_alta.xlsx", "sem_alta"),
            (f"{negativos_df.shape[0]} contas possuem valor negativo.", output_negativos, "contas_valor_negativo.xlsx", "negativos"),
            (f"{abaixo_mediana_df.shape[0]} contas estão abaixo da mediana ({formatar_moeda(df['Valor conta'].median())}).", output_abaixo, "contas_abaixo_mediana.xlsx", "abaixo_mediana")
        ]} contas são outliers (acima de {formatar_moeda(limite_superior)}).", output_outliers, "contas_outliers.xlsx", "outliers"),
            (f"{antigas_df.shape[0]} contas com mais de 90 dias desde a entrada.", output_antigas, "contas_90_dias.xlsx", "antigas"),
            (f"{zeradas_df.shape[0]} contas estão com valor zerado.", output_zeradas, "contas_zeradas.xlsx", "zeradas"),
            (f"{sem_alta_df.shape[0]} contas estão com pacientes sem alta.", output_sem_alta, "contas_sem_alta.xlsx", "sem_alta"),
            (f"{negativos_df.shape[0]} contas possuem valor negativo.", output_negativos, "contas_valor_negativo.xlsx", "negativos"),
            (f"{abaixo_mediana_df.shape[0]} contas estão abaixo da mediana ({formatar_moeda(df['Valor conta'].median())}).", output_abaixo, "contas_abaixo_mediana.xlsx", "abaixo_mediana"),
        ]

        for texto, arquivo, nome_arquivo, chave in insights:
            col1, col2 = st.columns([0.9, 0.1])
            with col1:
                st.markdown(f"- {texto}")
            with col2:
                st.download_button(label="⬇️", data=arquivo.getvalue(), file_name=nome_arquivo, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=chave)

        # Botão para baixar CSV com os dados brutos dos insights
        insights_dados = {
            "Contas com valor zerado": [df[df["Valor conta"] == 0].shape[0]],
            "Contas com paciente sem alta": [sem_alta],
            "Contas com valor abaixo da mediana": [(df["Valor conta"] < df["Valor conta"].median()).sum()],
            "Contas com valor acima do limite (outliers)": [df[df["Valor conta"] > df["Valor conta"].quantile(0.75) + 1.5 * (df["Valor conta"].quantile(0.75) - df["Valor conta"].quantile(0.25))].shape[0]],
            "Contas com mais de 90 dias": [df[df["Data entrada"] < pd.Timestamp.today() - pd.Timedelta(days=90)].shape[0]]
        }
        df_insights = pd.DataFrame(insights_dados)
        st.download_button("📥 Baixar dados analíticos dos insights", data=df_insights.to_csv(index=False).encode('utf-8'), file_name="insights_analiticos.csv", mime="text/csv")

        df_mes = df.groupby("AnoMes").agg(Quantidade=("Conta", "nunique"), Total=("Valor conta", "sum")).reset_index()
        fig_dist = px.bar(df_mes, x="AnoMes", y=["Quantidade", "Total"], barmode="group",
                          title="Total de Contas e Valores por Mês", labels={"value": "Total", "AnoMes": "Mês"})
        st.plotly_chart(fig_dist, use_container_width=True)

        st.subheader("Estatísticas Descritivas Gerais")
        estatisticas = df["Valor conta"].describe().rename({
            "count": "Quantidade",
            "mean": "Média",
            "std": "Desvio Padrão",
            "min": "Mínimo",
            "25%": "1º Quartil",
            "50%": "Mediana",
            "75%": "3º Quartil",
            "max": "Máximo"
        }).to_frame()
        estatisticas.loc[["Média", "Mínimo", "1º Quartil", "Mediana", "3º Quartil", "Máximo"]] = estatisticas.loc[["Média", "Mínimo", "1º Quartil", "Mediana", "3º Quartil", "Máximo"]].applymap(formatar_moeda)
        st.dataframe(estatisticas)

        st.subheader("Contas com Valores Outliers")
        q1 = df["Valor conta"].quantile(0.25)
        q3 = df["Valor conta"].quantile(0.75)
        iqr = q3 - q1
        limite_superior = q3 + 1.5 * iqr
        outliers = df[df["Valor conta"] > limite_superior]
        outliers["Data entrada"] = outliers["Data entrada"].dt.strftime('%d/%m/%Y')
        outliers_ordenadas = outliers.sort_values(by="Valor conta", ascending=False)
        colunas_outliers = ["Status", "Data entrada", "Valor conta"] + [col for col in outliers_ordenadas.columns if col not in ["Status", "Data entrada", "Valor conta"]]
        st.dataframe(outliers_ordenadas[colunas_outliers].style.format({"Valor conta": formatar_moeda}))

        st.subheader("Contas Mais Antigas")
        contas_antigas = df.sort_values(by="Data entrada", ascending=True).head(20)
        contas_antigas["Data entrada"] = contas_antigas["Data entrada"].dt.strftime('%d/%m/%Y')
        colunas_antigas = ["Status", "Data entrada", "Valor conta"] + [col for col in contas_antigas.columns if col not in ["Status", "Data entrada", "Valor conta"]]
        st.dataframe(contas_antigas[colunas_antigas].style.format({"Valor conta": formatar_moeda}))

    with st.expander("📁 Análises por Convênio"):
        resumo_convenio = df.groupby("Convênio")["Valor conta"].agg(Quantidade="count", Total="sum", Média="mean").sort_values(by="Total", ascending=False)
        st.dataframe(resumo_convenio.style.format({"Total": formatar_moeda, "Média": formatar_moeda, "Quantidade": "{:.0f}"}))

    with st.expander("📂 Análises por Etapa"):
        resumo_etapa = df.groupby("Último Setor destino")["Valor conta"].agg(Quantidade="count", Total="sum", Média="mean").sort_values(by="Total", ascending=False)
        st.dataframe(resumo_etapa.style.format({"Total": formatar_moeda, "Média": formatar_moeda, "Quantidade": "{:.0f}"}))

    with st.expander("🩺 Análises por Médico Executor"):
        resumo_medico = df.groupby("Médico executor")["Valor conta"].agg(Quantidade="count", Total="sum", Média="mean").sort_values(by="Total", ascending=False)
        st.dataframe(resumo_medico.style.format({"Total": formatar_moeda, "Média": formatar_moeda, "Quantidade": "{:.0f}"}))

    with st.expander("📈 Análises Visuais"):
        st.subheader("Boxplot por Convênio")
        plt.figure(figsize=(10, 5))
        sns.boxplot(data=df, x="Convênio", y="Valor conta")
        plt.xticks(rotation=90)
        st.pyplot(plt)

        st.subheader("TreeMap de Valor Total por Convênio")
        df_treemap = df.groupby("Convênio")["Valor conta"].sum().reset_index()
        fig_tree = px.treemap(df_treemap, path=["Convênio"], values="Valor conta")
        st.plotly_chart(fig_tree, use_container_width=True)

        st.subheader("Fluxo Sankey - Status para Convênio")
        origem = df["Status"].fillna("Desconhecido")
        destino = df["Convênio"].fillna("Desconhecido")
        labels = list(pd.unique(origem.tolist() + destino.tolist()))
        label_index = {k: v for v, k in enumerate(labels)}
        sankey_df = df.groupby([origem, destino]).size().reset_index(name="valor")

        fig_sankey = go.Figure(go.Sankey(
            node=dict(label=labels, pad=15, thickness=20),
            link=dict(
                source=sankey_df[origem.name].map(label_index),
                target=sankey_df[destino.name].map(label_index),
                value=sankey_df["valor"]
            )
        ))
        st.plotly_chart(fig_sankey, use_container_width=True)
