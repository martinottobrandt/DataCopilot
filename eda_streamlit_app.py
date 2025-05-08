import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO

def formatar_moeda(valor):
    return f'R$ {valor:,.2f}'.replace(',', 'v').replace('.', ',').replace('v', '.')

st.set_page_config(layout="wide")
st.title("Análise de Contas Pendentes - Hospital")

uploaded_file = st.file_uploader("Faça upload da planilha Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    primeira_aba = xls.sheet_names[0]
    df = pd.read_excel(xls, sheet_name=primeira_aba)

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

    zeradas_df = df[df["Valor conta"] == 0]
    sem_alta_df = df[df[df.columns[df.columns.str.lower().str.contains("alta")][0]].isna()] if any(df.columns.str.lower().str.contains("alta")) else df.iloc[0:0]
    abaixo_mediana_df = df[df["Valor conta"] < df["Valor conta"].median()]
    negativos_df = df[df["Valor conta"] < 0]
    limite_superior = df["Valor conta"].quantile(0.75) + 1.5 * (df["Valor conta"].quantile(0.75) - df["Valor conta"].quantile(0.25))
    outliers_df = df[df["Valor conta"] > limite_superior]
    antigas_df = df[df["Data entrada"] < pd.Timestamp.today() - pd.Timedelta(days=90)]

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

    st.markdown("**Principais insights iniciais:**")
    for texto, arquivo, nome_arquivo, chave in insights:
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            st.markdown(f"- {texto}")
        with col2:
            st.download_button(label="⬇️", data=arquivo.getvalue(), file_name=nome_arquivo, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=chave)
