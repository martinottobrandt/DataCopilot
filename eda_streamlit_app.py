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
    st.dataframe(df["Valor conta"].describe().rename({"count": "Quantidade"}).to_frame().style.format({"Valor conta": formatar_moeda}))

    st.subheader("Resumo por Convênio")
    resumo_convenio = df.groupby("Convênio")["Valor conta"].agg(
        Quantidade="count",
        Valor_Total="sum",
        Valor_Médio="mean",
        Valor_Máximo="max"
    ).sort_values(by="Valor_Total", ascending=False)
    st.dataframe(resumo_convenio.style.format({
        "Valor_Total": formatar_moeda,
        "Valor_Médio": formatar_moeda,
        "Valor_Máximo": formatar_moeda
    }))

    qtd_contas = pd.pivot_table(df, index="Convênio", columns="AnoMes", values="Conta", aggfunc=pd.Series.nunique, fill_value=0)
    valor_total = pd.pivot_table(df, index="Convênio", columns="AnoMes", values="Valor conta", aggfunc="sum", fill_value=0)

    st.markdown("### Quantidade de Contas Distintas por Mês")
    st.dataframe(qtd_contas.style.format(na_rep='').set_caption("Quantidade de Contas Distintas por Mês"))

    st.markdown("### Valor Total das Contas por Mês")
    st.dataframe(valor_total.style.format(formatar_moeda).set_caption("Valor Total das Contas por Mês"))

    st.subheader("Resumo por Etapa (Último Setor Destino)")
    resumo_etapa = df.groupby("Último Setor destino")["Valor conta"].agg(
        Quantidade="count",
        Valor_Total="sum",
        Valor_Médio="mean"
    ).sort_values(by="Valor_Total", ascending=False)
    st.dataframe(resumo_etapa.style.format({
        "Valor_Total": formatar_moeda,
        "Valor_Médio": formatar_moeda
    }))

    st.subheader("Contas com Valores Outliers (mais antigas e de maior valor)")
    q1 = df["Valor conta"].quantile(0.25)
    q3 = df["Valor conta"].quantile(0.75)
    iqr = q3 - q1
    limite_superior = q3 + 1.5 * iqr
    outliers = df[df["Valor conta"] > limite_superior]
    outliers["Data entrada"] = outliers["Data entrada"].dt.strftime('%d/%m/%Y')
outliers_ordenadas = outliers.sort_values(by=["Valor conta", "Data entrada"], ascending=[False, True])
    colunas_outliers = ["Status", "Data entrada", "Valor conta"] + [col for col in outliers_ordenadas.columns if col not in ["Status", "Data entrada", "Valor conta"]]
st.dataframe(outliers_ordenadas[colunas_outliers].style.format({"Valor conta": formatar_moeda}))

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


    st.subheader("Análise de Contas por Médico")
    if "Atendimento" in df.columns and "Data entrada" in df.columns:
        df["Data entrada"] = pd.to_datetime(df["Data entrada"], errors="coerce")
        df["Mês"] = df["Data entrada"].dt.to_period("M").astype(str)
        with st.expander("Contas por Médico e por Mês", expanded=False):
            grupo_medico = df.groupby(["Atendimento", "Mês"]).agg(
                Quantidade=("Conta", "nunique"),
                Valor_Total=("Valor conta", "sum")
            ).reset_index()
            tabela_pivot = grupo_medico.pivot(index="Atendimento", columns="Mês", values="Valor_Total").fillna(0)
            st.dataframe(tabela_pivot.style.format(formatar_moeda))

else:
    st.info("Por favor, carregue uma planilha para iniciar a análise.")
