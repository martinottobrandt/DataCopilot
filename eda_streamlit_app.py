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

    return f"""
    **Principais insights iniciais:**
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
        st.markdown(gerar_insights(df))

        fig_dist = px.histogram(df, x="Valor conta", nbins=50, title="Distribuição dos Valores das Contas")
        st.plotly_chart(fig_dist, use_container_width=True)

        st.subheader("Estatísticas Descritivas Gerais")
        estatisticas = df["Valor conta"].describe().rename({"count": "Quantidade"}).to_frame()
        estatisticas.loc[["mean", "min", "25%", "50%", "75%", "max"]] = estatisticas.loc[["mean", "min", "25%", "50%", "75%", "max"]].applymap(formatar_moeda)
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
        st.dataframe(resumo_convenio.style.format({"Total": formatar_moeda, "Média": formatar_moeda}))

    with st.expander("📂 Análises por Etapa"):
        resumo_etapa = df.groupby("Último Setor destino")["Valor conta"].agg(Quantidade="count", Total="sum", Média="mean").sort_values(by="Total", ascending=False)
        st.dataframe(resumo_etapa.style.format({"Total": formatar_moeda, "Média": formatar_moeda}))

    with st.expander("🩺 Análises por Médico Executor"):
        resumo_medico = df.groupby("Médico executor")["Valor conta"].agg(Quantidade="count", Total="sum", Média="mean").sort_values(by="Total", ascending=False)
        st.dataframe(resumo_medico.style.format({"Total": formatar_moeda, "Média": formatar_moeda}))

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
