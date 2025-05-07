import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(layout="wide")
st.title("Análise de Contas Pendentes - Hospital")

# Upload do arquivo
uploaded_file = st.file_uploader("Faça upload da planilha Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name="Planilha1")

    # Seleção das colunas relevantes
    colunas = [
        "Status", "Tipo atendimento", "Conta", "Atendimento", "Status atendimento",
        "Convênio", "Categoria", "Valor conta", "Etapa anterior",
        "Último Setor destino", "Setor atendimento", "Estabelecimento",
        "Data entrada"
    ]
    df = df[colunas].copy()
    df["Valor conta"] = pd.to_numeric(df["Valor conta"], errors="coerce")
    df["Data entrada"] = pd.to_datetime(df["Data entrada"], errors="coerce")
    df["AnoMes"] = df["Data entrada"].dt.to_period("M").astype(str)

    # Filtro por convênio no cabeçalho
    convenios_disponiveis = sorted(df["Convênio"].dropna().unique())
    convenios_filtrados = st.multiselect("Filtrar por Convênio:", options=convenios_disponiveis, default=convenios_disponiveis)
    df = df[df["Convênio"].isin(convenios_filtrados)]

    st.subheader("Estatísticas Descritivas Gerais")
    st.dataframe(df["Valor conta"].describe().to_frame())

    st.subheader("Resumo por Convênio")
    resumo_convenio = df.groupby("Convênio")["Valor conta"].agg(
        Total_Contas="count",
        Valor_Total="sum",
        Valor_Médio="mean",
        Valor_Máximo="max"
    ).sort_values(by="Valor_Total", ascending=False)
    st.dataframe(resumo_convenio)

    st.subheader("Análise de Contas por Mês e Convênio")
    qtd_contas = pd.pivot_table(df, index="Convênio", columns="AnoMes", values="Conta", aggfunc=pd.Series.nunique, fill_value=0)
    valor_total = pd.pivot_table(df, index="Convênio", columns="AnoMes", values="Valor conta", aggfunc="sum", fill_value=0)

    st.markdown("### Quantidade de Contas Distintas por Mês")
    st.dataframe(qtd_contas)

    st.markdown("### Valor Total das Contas por Mês")
    st.dataframe(valor_total)

    st.subheader("Resumo por Etapa (Último Setor Destino)")
    resumo_etapa = df.groupby("Último Setor destino")["Valor conta"].agg(
        Total_Contas="count",
        Valor_Total="sum",
        Valor_Médio="mean"
    ).sort_values(by="Valor_Total", ascending=False)
    st.dataframe(resumo_etapa)

    st.subheader("Contas com Valores Outliers")
    q1 = df["Valor conta"].quantile(0.25)
    q3 = df["Valor conta"].quantile(0.75)
    iqr = q3 - q1
    limite_superior = q3 + 1.5 * iqr
    outliers = df[df["Valor conta"] > limite_superior]
    st.dataframe(outliers)

    st.subheader("Boxplot de Valores por Convênio")
    plt.figure(figsize=(10, 5))
    sns.boxplot(data=df, x="Convênio", y="Valor conta")
    plt.xticks(rotation=90)
    st.pyplot(plt)

    st.subheader("TreeMap de Valor Total por Convênio")
    df_treemap = df.groupby("Convênio")["Valor conta"].sum().reset_index()
    fig_tree = px.treemap(df_treemap, path=["Convênio"], values="Valor conta",
                          title="Distribuição do Valor Total das Contas por Convênio")
    st.plotly_chart(fig_tree, use_container_width=True)

    st.subheader("Fluxo Sankey: Status → Convênio")
    origem_sankey = df["Status"].fillna("Desconhecido")
    destino_sankey = df["Convênio"].fillna("Desconhecido")
    todos_nos_sankey = list(pd.unique(origem_sankey.tolist() + destino_sankey.tolist()))
    mapa_sankey = {nome: i for i, nome in enumerate(todos_nos_sankey)}
    fluxo_sankey = df.groupby([origem_sankey, destino_sankey]).size().reset_index(name="quantidade")

    sankey_fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=todos_nos_sankey
        ),
        link=dict(
            source=fluxo_sankey[origem_sankey.name].map(mapa_sankey),
            target=fluxo_sankey[destino_sankey.name].map(mapa_sankey),
            value=fluxo_sankey["quantidade"]
        )
    )])
    sankey_fig.update_layout(title_text="Fluxo das Contas: Status → Convênio", font_size=10)
    st.plotly_chart(sankey_fig, use_container_width=True)

else:
    st.info("Por favor, carregue uma planilha para iniciar a análise.")
