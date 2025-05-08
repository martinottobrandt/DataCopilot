import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import calendar

# Função para formatar valores em reais (sem usar locale)
def formatar_moeda(valor):
    if pd.isna(valor):
        return "R$ 0,00"
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
    
    contas_antiga_status = contas_90_dias.groupby("Último Setor destino").size().sort_values(ascending=False).reset_index()
    gargalo = contas_antiga_status.iloc[0]["Último Setor destino"] if not contas_antiga_status.empty else "Nenhum"

    zeradas = df[df["Valor conta"] == 0].shape[0]
    sem_alta = df[df.columns[df.columns.str.lower().str.contains("alta")][0]].isna().sum() if any(df.columns.str.lower().str.contains("alta")) else 0

    # Projeção de recebíveis
    valor_total = df["Valor conta"].sum()
    projecao_30d = df[df["Data entrada"] > pd.Timestamp.today() - pd.Timedelta(days=30)]["Valor conta"].sum()
    tendencia = (projecao_30d / df["Valor conta"].sum()) * 100 if valor_total > 0 else 0

    return f"""
    **Principais insights iniciais:**
    - {zeradas} contas estão com valor zerado, o que pode indicar falha de fechamento, isenção contratual ou erro de sistema.
    - {sem_alta} contas estão associadas a pacientes sem alta, o que pode impactar o ciclo de faturamento e deve ser monitorado.
    - Cerca de {(df["Valor conta"] < df["Valor conta"].median()).mean()*100:.0f}% das contas possuem valor abaixo de R$ {df["Valor conta"].median():,.2f}, sugerindo foco em resolução de volume com baixo impacto financeiro.
    - {outliers.shape[0]} contas estão acima de R$ {limite_superior:,.2f} (outliers), recomendando revisão prioritária e validação de glosas ou auditoria específica.
    - Os convênios {', '.join(resumo_convenio.head(2).index)} concentram {resumo_convenio.head(2)["Valor_Total"].sum() / resumo_convenio["Valor_Total"].sum() * 100:.0f}% do valor total em aberto e devem ser tratados com régua especial de cobrança.
    - Identificamos {contas_90_dias.shape[0]} contas com mais de 90 dias desde a entrada, com maior concentração no setor "{gargalo}", indicando possível gargalo de processo.
    - A tendência de novos valores nos últimos 30 dias representa {tendencia:.1f}% do valor total em aberto, o que indica {' aceleração' if tendencia > 33 else ' normalidade' if tendencia > 20 else ' desaceleração'} no ciclo de faturamento.
    """

def calcular_aging(df):
    hoje = pd.Timestamp.today().normalize()
    df["Dias Pendentes"] = (hoje - df["Data entrada"].dt.normalize()).dt.days
    
    # Categorias de aging
    categorias = [
        (0, 30, "0-30 dias"),
        (31, 60, "31-60 dias"),
        (61, 90, "61-90 dias"),
        (91, 180, "91-180 dias"),
        (181, 365, "181-365 dias"),
        (366, float('inf'), "+365 dias")
    ]
    
    # Criar coluna de categoria de aging
    df["Categoria Aging"] = pd.cut(
        df["Dias Pendentes"],
        bins=[c[0]-1 for c in categorias] + [float('inf')],
        labels=[c[2] for c in categorias],
        right=True
    )
    
    return df

def calcular_kpis(df):
    # KPIs básicos
    total_contas = df.shape[0]
    valor_total = df["Valor conta"].sum()
    ticket_medio = valor_total / total_contas if total_contas > 0 else 0
    
    # KPIs avançados
    hoje = pd.Timestamp.today().normalize()
    df_temp = df.copy()
    df_temp["Dias Pendentes"] = (hoje - df_temp["Data entrada"].dt.normalize()).dt.days
    
    # Idade média das contas (em dias)
    idade_media = df_temp["Dias Pendentes"].mean()
    
    # Contas por idade
    contas_30d = df_temp[df_temp["Dias Pendentes"] <= 30].shape[0]
    contas_60d = df_temp[(df_temp["Dias Pendentes"] > 30) & (df_temp["Dias Pendentes"] <= 60)].shape[0]
    contas_90d = df_temp[(df_temp["Dias Pendentes"] > 60) & (df_temp["Dias Pendentes"] <= 90)].shape[0]
    contas_mais_90d = df_temp[df_temp["Dias Pendentes"] > 90].shape[0]
    
    # Percentual de contas acima de 90 dias
    perc_acima_90d = (contas_mais_90d / total_contas) * 100 if total_contas > 0 else 0
    
    # Valor por idade
    valor_30d = df_temp[df_temp["Dias Pendentes"] <= 30]["Valor conta"].sum()
    valor_60d = df_temp[(df_temp["Dias Pendentes"] > 30) & (df_temp["Dias Pendentes"] <= 60)]["Valor conta"].sum()
    valor_90d = df_temp[(df_temp["Dias Pendentes"] > 60) & (df_temp["Dias Pendentes"] <= 90)]["Valor conta"].sum()
    valor_mais_90d = df_temp[df_temp["Dias Pendentes"] > 90]["Valor conta"].sum()
    
    # Valor em risco (contas acima de 90 dias)
    valor_em_risco = valor_mais_90d
    perc_valor_em_risco = (valor_em_risco / valor_total) * 100 if valor_total > 0 else 0
    
    return {
        "total_contas": total_contas,
        "valor_total": valor_total,
        "ticket_medio": ticket_medio,
        "idade_media": idade_media,
        "contas_30d": contas_30d,
        "contas_60d": contas_60d,
        "contas_90d": contas_90d,
        "contas_mais_90d": contas_mais_90d,
        "perc_acima_90d": perc_acima_90d,
        "valor_30d": valor_30d,
        "valor_60d": valor_60d,
        "valor_90d": valor_90d,
        "valor_mais_90d": valor_mais_90d,
        "valor_em_risco": valor_em_risco,
        "perc_valor_em_risco": perc_valor_em_risco
    }

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Faturamento Hospitalar",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título e descrição
st.title("🏥 Análise de Faturamento Hospitalar")
st.markdown("""
    Este dashboard permite analisar as contas pendentes do hospital, identificar gargalos no processo 
    de faturamento e oportunidades de melhoria no ciclo financeiro.
""")

# Upload de arquivo
uploaded_file = st.file_uploader("Faça upload da planilha Excel (.xlsx)", type=["xlsx"])

if uploaded_file:
    # Leitura do arquivo
    xls = pd.ExcelFile(uploaded_file)
    primeira_aba = xls.sheet_names[0]
    
    with st.spinner('Carregando e processando dados...'):
        df = pd.read_excel(xls, sheet_name=primeira_aba)
        
        # Verificar e selecionar colunas disponíveis
        colunas_necessarias = [
            "Status", "Tipo atendimento", "Conta", "Atendimento", "Status atendimento",
            "Convênio", "Categoria", "Valor conta", "Etapa anterior",
            "Último Setor destino", "Setor atendimento", "Estabelecimento",
            "Data entrada", "Médico executor"
        ]
        
        colunas_disponiveis = [col for col in colunas_necessarias if col in df.columns]
        
        if len(colunas_disponiveis) < len(colunas_necessarias):
            colunas_faltantes = set(colunas_necessarias) - set(colunas_disponiveis)
            st.warning(f"Algumas colunas esperadas não foram encontradas: {', '.join(colunas_faltantes)}")
        
        df = df[colunas_disponiveis].copy()
        
        # Converter e limpar dados
        df["Valor conta"] = pd.to_numeric(df["Valor conta"], errors="coerce")
        df["Data entrada"] = pd.to_datetime(df["Data entrada"], errors="coerce")
        
        # Adicionar colunas úteis
        df["AnoMes"] = df["Data entrada"].dt.to_period("M").astype(str)
        df = calcular_aging(df)
        
        # KPIs gerais
        kpis = calcular_kpis(df)

    # Sidebar com filtros
    st.sidebar.header("Filtros Gerais")
    
    # Filtro de data
    with st.sidebar.expander("Filtro de Data", expanded=False):
        data_min = df["Data entrada"].min().date() if not df["Data entrada"].isna().all() else datetime.today().date()
        data_max = df["Data entrada"].max().date() if not df["Data entrada"].isna().all() else datetime.today().date()
        
        data_inicio, data_fim = st.date_input(
            "Intervalo de Data:",
            value=(data_min, data_max),
            min_value=data_min,
            max_value=data_max
        )
    
    # Filtro de convênios
    with st.sidebar.expander("Filtro de Convênios", expanded=False):
        convenios_disponiveis = sorted(df["Convênio"].dropna().unique())
        todos_conv = st.checkbox("Selecionar todos os convênios", value=True)
        
        if todos_conv:
            convenios_filtrados = convenios_disponiveis
        else:
            convenios_filtrados = st.multiselect("Convênios:", convenios_disponiveis)
    
    # Filtro de médicos
    with st.sidebar.expander("Filtro de Médicos", expanded=False):
        medicos_disponiveis = sorted(df["Médico executor"].dropna().unique())
        todos_med = st.checkbox("Selecionar todos os médicos", value=True)
        
        if todos_med:
            medicos_filtrados = medicos_disponiveis
        else:
            medicos_filtrados = st.multiselect("Médicos:", medicos_disponiveis)
    
    # Filtro de status
    with st.sidebar.expander("Filtro de Status", expanded=False):
        status_disponiveis = sorted(df["Status"].dropna().unique())
        todos_status = st.checkbox("Selecionar todos os status", value=True)
        
        if todos_status:
            status_filtrados = status_disponiveis
        else:
            status_filtrados = st.multiselect("Status:", status_disponiveis)
    
    # Filtro de setor
    with st.sidebar.expander("Filtro de Setor", expanded=False):
        setores_disponiveis = sorted(df["Último Setor destino"].dropna().unique())
        todos_setores = st.checkbox("Selecionar todos os setores", value=True)
        
        if todos_setores:
            setores_filtrados = setores_disponiveis
        else:
            setores_filtrados = st.multiselect("Setores:", setores_disponiveis)
    
    # Aplicar filtros
    mask = (
        (df["Data entrada"].dt.date >= data_inicio) & 
        (df["Data entrada"].dt.date <= data_fim) &
        (df["Convênio"].isin(convenios_filtrados)) &
        (df["Médico executor"].isin(medicos_filtrados)) &
        (df["Status"].isin(status_filtrados)) &
        (df["Último Setor destino"].isin(setores_filtrados))
    )
    
    df_filtrado = df[mask]
    
    if df_filtrado.empty:
        st.error("Nenhum dado encontrado com os filtros selecionados.")
    else:
        # Recalcular KPIs com dados filtrados
        kpis_filtrados = calcular_kpis(df_filtrado)
        
        # Dashboard Principal
        st.markdown("## 📊 Dashboard Principal")
        
        # KPIs principais
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total de Contas", f"{kpis_filtrados['total_contas']:,}".replace(',', '.'))
        with col2:
            st.metric("Valor Total", formatar_moeda(kpis_filtrados['valor_total']))
        with col3:
            st.metric("Ticket Médio", formatar_moeda(kpis_filtrados['ticket_medio']))
        with col4:
            st.metric("Idade Média (dias)", f"{kpis_filtrados['idade_media']:.1f}")
        
        # KPIs secundários
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Contas > 90 dias", f"{kpis_filtrados['contas_mais_90d']:,}".replace(',', '.'), 
                     f"{kpis_filtrados['perc_acima_90d']:.1f}%")
        with col2:
            st.metric("Valor em Risco (>90d)", formatar_moeda(kpis_filtrados['valor_em_risco']), 
                     f"{kpis_filtrados['perc_valor_em_risco']:.1f}%")
        with col3:
            st.metric("Contas 0-30 dias", f"{kpis_filtrados['contas_30d']:,}".replace(',', '.'))
        with col4:
            st.metric("Contas 31-90 dias", f"{kpis_filtrados['contas_60d'] + kpis_filtrados['contas_90d']:,}".replace(',', '.'))
        
        # Gráfico de distribuição de valores por aging
        st.markdown("### 📈 Distribuição do Valor por Aging")
        aging_df = df_filtrado.groupby("Categoria Aging")["Valor conta"].sum().reset_index()
        fig_aging = px.bar(
            aging_df, 
            x="Categoria Aging", 
            y="Valor conta",
            color="Categoria Aging",
            text_auto=True,
            category_orders={"Categoria Aging": ["0-30 dias", "31-60 dias", "61-90 dias", "91-180 dias", "181-365 dias", "+365 dias"]},
            labels={"Valor conta": "Valor Total (R$)", "Categoria Aging": "Faixa de Idade"}
        )
        fig_aging.update_layout(xaxis_title="Faixa de Idade", yaxis_title="Valor Total (R$)")
        fig_aging.update_traces(texttemplate='%{y:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'), textposition='outside')
        st.plotly_chart(fig_aging, use_container_width=True)
        
        # Tabs para análises detalhadas
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📋 Insights", 
            "🏥 Análise por Convênio", 
            "🔄 Análise por Fluxo", 
            "🩺 Análise por Médico",
            "📊 Visualizações Avançadas"
        ])
        
        with tab1:
            st.markdown("### 🔍 Insights e Oportunidades de Melhoria")
            
            # Insights baseados nos dados
            st.markdown(gerar_insights(df_filtrado))
            
            # Análises específicas
            st.markdown("### 📑 Análises Detalhadas")
            
            # Criar DataFrames específicos para análise
            zeradas_df = df_filtrado[df_filtrado["Valor conta"] == 0]
            sem_alta_df = df_filtrado[df_filtrado[df_filtrado.columns[df_filtrado.columns.str.lower().str.contains("alta")][0]].isna()] if any(df_filtrado.columns.str.lower().str.contains("alta")) else pd.DataFrame()
            abaixo_mediana_df = df_filtrado[df_filtrado["Valor conta"] < df_filtrado["Valor conta"].median()]
            negativos_df = df_filtrado[df_filtrado["Valor conta"] < 0]
            
            # Calcular outliers
            q1 = df_filtrado["Valor conta"].quantile(0.25)
            q3 = df_filtrado["Valor conta"].quantile(0.75)
            iqr = q3 - q1
            limite_superior = q3 + 1.5 * iqr
            outliers_df = df_filtrado[df_filtrado["Valor conta"] > limite_superior]
            
            # Contas antigas
            antigas_df = df_filtrado[df_filtrado["Data entrada"] < pd.Timestamp.today() - pd.Timedelta(days=90)]
            
            # Função para gerar Excel para download
            from io import BytesIO
            def gerar_excel_bytes(df, nome_aba):
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name=nome_aba)
                return buffer
            
            # Lista de insights com botões de download
            insights = [
                (f"{outliers_df.shape[0]} contas são outliers (acima de {formatar_moeda(limite_superior)}).", 
                 gerar_excel_bytes(outliers_df, "Outliers"), "contas_outliers.xlsx", "outliers"),
                
                (f"{antigas_df.shape[0]} contas com mais de 90 dias desde a entrada.", 
                 gerar_excel_bytes(antigas_df, "Mais Antigas"), "contas_90_dias.xlsx", "antigas"),
                
                (f"{zeradas_df.shape[0]} contas estão com valor zerado.", 
                 gerar_excel_bytes(zeradas_df, "Zeradas"), "contas_zeradas.xlsx", "zeradas"),
                
                (f"{sem_alta_df.shape[0]} contas estão com pacientes sem alta." if not sem_alta_df.empty else "Não foram identificadas contas sem alta.", 
                 gerar_excel_bytes(sem_alta_df, "Sem Alta"), "contas_sem_alta.xlsx", "sem_alta"),
                
                (f"{negativos_df.shape[0]} contas possuem valor negativo.", 
                 gerar_excel_bytes(negativos_df, "Negativos"), "contas_valor_negativo.xlsx", "negativos"),
                
                (f"{abaixo_mediana_df.shape[0]} contas estão abaixo da mediana ({formatar_moeda(df_filtrado['Valor conta'].median())}).", 
                 gerar_excel_bytes(abaixo_mediana_df, "Abaixo Mediana"), "contas_abaixo_mediana.xlsx", "abaixo_mediana")
            ]
            
            # Mostrar insights com botões de download
            for texto, arquivo, nome_arquivo, chave in insights:
                col1, col2 = st.columns([0.9, 0.1])
                with col1:
                    st.markdown(f"- {texto}")
                with col2:
                    if arquivo.getvalue() and "Não foram identificadas" not in texto:
                        st.download_button(
                            label="⬇️", 
                            data=arquivo.getvalue(), 
                            file_name=nome_arquivo, 
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                            key=chave
                        )
        
        with tab2:
            st.markdown("### 🏥 Análise por Convênio")
            
            # Resumo por convênio
            resumo_convenio = df_filtrado.groupby("Convênio")["Valor conta"].agg(
                Quantidade="count", 
                Total="sum", 
                Média="mean",
                Mediana="median",
                Mínimo="min",
                Máximo="max"
            ).sort_values(by="Total", ascending=False)
            
            # Adicionar proporção do total
            if resumo_convenio["Total"].sum() > 0:
                resumo_convenio["% do Total"] = (resumo_convenio["Total"] / resumo_convenio["Total"].sum()) * 100
            else:
                resumo_convenio["% do Total"] = 0
            
            # Mostrar tabela estilizada
            st.dataframe(
                resumo_convenio.style.format({
                    "Total": formatar_moeda, 
                    "Média": formatar_moeda,
                    "Mediana": formatar_moeda,
                    "Mínimo": formatar_moeda,
                    "Máximo": formatar_moeda,
                    "Quantidade": "{:.0f}",
                    "% do Total": "{:.2f}%"
                }),
                height=400
            )
            
            # Gráficos
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Distribuição do Valor Total por Convênio")
                # Pegar top 10 convênios por valor
                top_convenios = resumo_convenio.head(10).reset_index()
                
                fig_pie = px.pie(
                    top_convenios, 
                    values="Total", 
                    names="Convênio",
                    hole=0.4,
                    labels={"Total": "Valor Total"}
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                st.markdown("#### Aging por Convênio")
                # Aging por convênio (top 5)
                top5_convenios = resumo_convenio.head(5).index.tolist()
                
                # Filtrar apenas top 5 convênios
                df_top5 = df_filtrado[df_filtrado["Convênio"].isin(top5_convenios)]
                
                aging_convenio = df_top5.groupby(["Convênio", "Categoria Aging"])["Valor conta"].sum().reset_index()
                
                fig_aging_conv = px.bar(
                    aging_convenio,
                    x="Convênio",
                    y="Valor conta",
                    color="Categoria Aging",
                    text_auto='.2s',
                    category_orders={"Categoria Aging": ["0-30 dias", "31-60 dias", "61-90 dias", "91-180 dias", "181-365 dias", "+365 dias"]},
                    labels={"Valor conta": "Valor Total (R$)", "Categoria Aging": "Faixa de Idade"}
                )
                st.plotly_chart(fig_aging_conv, use_container_width=True)
            
            # Análise de ticket médio
            st.markdown("#### Ticket Médio por Convênio")
            df_ticket = resumo_convenio.reset_index()[["Convênio", "Média"]].sort_values(by="Média", ascending=False)
            
            fig_ticket = px.bar(
                df_ticket.head(10),
                x="Convênio",
                y="Média",
                text_auto=True,
                labels={"Média": "Ticket Médio (R$)"}
            )
            fig_ticket.update_traces(texttemplate='%{y:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'), textposition='outside')
            st.plotly_chart(fig_ticket, use_container_width=True)
        
        with tab3:
            st.markdown("### 🔄 Análise por Fluxo")
            
            # Resumo por etapa/setor
            resumo_etapa = df_filtrado.groupby("Último Setor destino")["Valor conta"].agg(
                Quantidade="count", 
                Total="sum", 
                Média="mean"
            ).sort_values(by="Total", ascending=False)
            
            # Adicionar proporção do total
            if resumo_etapa["Total"].sum() > 0:
                resumo_etapa["% do Total"] = (resumo_etapa["Total"] / resumo_etapa["Total"].sum()) * 100
            else:
                resumo_etapa["% do Total"] = 0
            
            # Mostrar tabela
            st.dataframe(
                resumo_etapa.style.format({
                    "Total": formatar_moeda, 
                    "Média": formatar_moeda, 
                    "Quantidade": "{:.0f}",
                    "% do Total": "{:.2f}%"
                }),
                height=300
            )
            
            # Análise de fluxo
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Distribuição por Setor")
                
                # Pegar top 10 setores
                top_setores = resumo_etapa.head(10).reset_index()
                
                fig_setores = px.bar(
                    top_setores,
                    x="Último Setor destino",
                    y="Total",
                    text_auto=True,
                    labels={"Total": "Valor Total (R$)", "Último Setor destino": "Setor"}
                )
                fig_setores.update_traces(texttemplate='%{y:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'), textposition='outside')
                fig_setores.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_setores, use_container_width=True)
            
            with col2:
                st.markdown("#### Tempo Médio por Setor (dias)")
                
                # Calcular tempo médio por setor
                df_filtrado_tempo = df_filtrado.copy()
                df_filtrado_tempo["Dias Pendentes"] = (pd.Timestamp.today().normalize() - df_filtrado_tempo["Data entrada"].dt.normalize()).dt.days
                
                tempo_medio = df_filtrado_tempo.groupby("Último Setor destino")["Dias Pendentes"].mean().reset_index()
                tempo_medio = tempo_medio.sort_values(by="Dias Pendentes", ascending=False).head(10)
                
                fig_tempo = px.bar(
                    tempo_medio,
                    x="Último Setor destino",
                    y="Dias Pendentes",
                    text_auto=True,
                    labels={"Dias Pendentes": "Tempo Médio (dias)", "Último Setor destino": "Setor"}
                )
                fig_tempo.update_traces(texttemplate='%{y:.1f}', textposition='outside')
                fig_tempo.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_tempo, use_container_width=True)
            
            # Diagrama Sankey
            st.markdown("#### Fluxo Sankey - Status para Convênio")
            if "Status" in df_filtrado.columns and "Convênio" in df_filtrado.columns:
                origem = df_filtrado["Status"].fillna("Desconhecido")
                destino = df_filtrado["Convênio"].fillna("Desconhecido")
                labels = list(pd.unique(origem.tolist() + destino.tolist()))
                label_index = {k: v for v, k in enumerate(labels)}
                
                # Criar dataframe para o sankey
                sankey_df = df_filtrado.groupby([origem.name, destino.name]).size().reset_index(name="valor")
                
                # Criar figura sankey
                fig_sankey = go.Figure(go.Sankey(
                    node=dict(label=labels, pad=15, thickness=20),
                    link=dict(
                        source=sankey_df[origem.name].map(label_index),
                        target=sankey_df[destino.name].map(label_index),
                        value=sankey_df["valor"]
                    )
                ))
                st.plotly_chart(fig_sankey, use_container_width=True)
            
            # Análise de tendência temporal
            st.markdown("#### Tendência de Contas no Tempo")
            
            # Agrupar por mês
            df_tendencia = df_filtrado.copy()
            df_tendencia["Mês"] = df_tendencia["Data entrada"].dt.to_period("M")
            tendencia_mensal = df_tendencia.groupby("Mês").agg(
                Quantidade=("Conta", "count"),
                Valor_Total=("Valor conta", "sum")
            ).reset_index()
            tendencia_mensal["Mês"] = tendencia_mensal["Mês"].astype(str)
            
            # Criar gráfico de linhas
            fig_tendencia = go.Figure()
            
            # Adicionar linha para quantidade
            fig_tendencia.add_trace(go.Scatter(
                x=tendencia_mensal["Mês"],
                y=tendencia_mensal["Quantidade"],
                name="Quantidade de Contas",
                mode="lines+markers",
                yaxis="y"
            ))
            
            # Adicionar linha para valor
            fig_tendencia.add_trace(go.Scatter(
                x=tendencia_mensal["Mês"],
                y=tendencia_mensal["Valor_Total"],
                name="Valor Total (R$)",
                mode="lines+markers",
                yaxis="y2"
            ))
            
            # Configurar layout com dois eixos Y
            fig_tendencia.update_layout(
                title="Tendência de Contas e Valores",
                xaxis=dict(title="Mês"),
                yaxis=dict(title="Quantidade de Contas", side="left"),
                yaxis2=dict(
                    title="Valor Total (R$)",
                    side="right",
                    overlaying="y",
                    showgrid=False
                ),
                legend=dict(x=0.01, y=0.99)
            )
            
            st.plotly_chart(fig_tendencia, use_container_width=True)
        
        with tab4:
            st.markdown("### 🩺 Análise por Médico Executor")
            
            # Resumo por médico
            resumo_medico = df_filtrado.groupby("Médico executor")["Valor conta"].agg(
                Quantidade="count", 
                Total="sum", 
                Média="mean"
            ).sort_values(by="Total", ascending=False)
            
            # Adicionar proporção do total
            if resumo_medico["Total"].sum() > 0:
                resumo_medico["% do Total"] = (resumo_medico["Total"] / resumo_medico["Total"].sum()) * 100
            else:
                resumo_medico["% do Total"] = 0
            
            # Mostrar tabela estilizada
            st.dataframe(
                resumo_medico.style.format({
                    "Total": formatar_moeda, 
                    "Média": formatar_moeda, 
                    "Quantidade": "{:.0f}",
                    "% do Total": "{:.2f}%"
                }),
                height=300
            )
            
            # Análises visuais
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Top 10 Médicos por Valor Total")
                
                # Pegar top 10 médicos
                top_medicos = resumo_medico.head(10).reset_index()
                
                fig_medicos = px.bar(
                    top_medicos,
                    x="Médico executor",
                    y="Total",
                    text_auto=True,
                    labels={"Total": "Valor Total (R$)", "Médico executor": "Médico"}
                )
                fig_medicos.update_traces(texttemplate='%{y:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'), textposition='outside')
                fig_medicos.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_medicos, use_container_width=True)
            
            with col2:
                st.markdown("#### Top 10 Médicos por Ticket Médio")
                
                # Pegar top 10 médicos por ticket médio (com pelo menos 5 contas)
                medicos_ticket = resumo_medico[resumo_medico["Quantidade"] >= 5].sort_values(by="Média", ascending=False).head(10).reset_index()
                
                fig_ticket_med = px.bar(
                    medicos_ticket,
                    x="Médico executor",
                    y="Média",
                    text_auto=True,
                    labels={"Média": "Ticket Médio (R$)", "Médico executor": "Médico"}
                )
                fig_ticket_med.update_traces(texttemplate='%{y:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'), textposition='outside')
                fig_ticket_med.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_ticket_med, use_container_width=True)
            
            # Relação médico-convênio
            st.markdown("#### Relação Médico x Convênio")
            
            # Selecionar top 5 médicos
            top5_medicos = resumo_medico.head(5).index.tolist()
            df_med_conv = df_filtrado[df_filtrado["Médico executor"].isin(top5_medicos)]
            
            # Agrupar por médico e convênio
            med_conv = df_med_conv.groupby(["Médico executor", "Convênio"])["Valor conta"].sum().reset_index()
            
            # Criar heatmap
            pivot_med_conv = med_conv.pivot(index="Médico executor", columns="Convênio", values="Valor conta")
            
            # Preencher NaN com zeros
            pivot_med_conv = pivot_med_conv.fillna(0)
            
# Criar mapa de calor com Plotly
fig_heatmap = px.imshow(
    pivot_med_conv,
    labels=dict(x="Convênio", y="Médico executor", color="Valor Total"),
    text_auto=True  # ou text_auto='.2s' para formato numérico simples
)

fig_heatmap.update_layout(height=400)
st.plotly_chart(fig_heatmap, use_container_width=True)

        
          with tab5:  # Ensure consistent indentation
        st.markdown("### 📊 Visualizações Avançadas")
        
        viz_type = st.selectbox(
            "Selecione o tipo de visualização:",
            ["Boxplot por Convênio", "TreeMap de Valor por Convênio", "Distribuição de Valores", "Mapa de Calor por Mês/Dia"]
        )
            
            if viz_type == "Boxplot por Convênio":
                st.markdown("#### Boxplot por Convênio")
                
                # Filtrar para mostrar apenas os top 10 convênios
                top10_convenios = resumo_convenio.head(10).index.tolist()
                df_box = df_filtrado[df_filtrado["Convênio"].isin(top10_convenios)]
                
                # Criar boxplot
                fig_box = px.box(
                    df_box,
                    x="Convênio",
                    y="Valor conta",
                    points="all",
                    labels={"Valor conta": "Valor da Conta (R$)", "Convênio": "Convênio"}
                )
                st.plotly_chart(fig_box, use_container_width=True)
                
                st.markdown("""
                **Como interpretar:** O boxplot mostra a distribuição dos valores das contas para cada convênio.
                - A linha central representa a mediana
                - A caixa representa o intervalo entre o primeiro quartil (25%) e o terceiro quartil (75%)
                - As linhas (whiskers) representam os valores mínimo e máximo (excluindo outliers)
                - Os pontos individuais são valores específicos de cada conta
                """)
            
            elif viz_type == "TreeMap de Valor por Convênio":
                st.markdown("#### TreeMap de Valor Total por Convênio")
                
                df_treemap = df_filtrado.groupby("Convênio")["Valor conta"].sum().reset_index()
                df_treemap = df_treemap.sort_values(by="Valor conta", ascending=False)
                
                fig_tree = px.treemap(
                    df_treemap, 
                    path=["Convênio"], 
                    values="Valor conta",
                    color="Valor conta",
                    color_continuous_scale="Viridis",
                    labels={"Valor conta": "Valor Total (R$)"}
                )
                fig_tree.update_traces(textinfo="label+value+percent")
                st.plotly_chart(fig_tree, use_container_width=True)
                
                st.markdown("""
                **Como interpretar:** O treemap mostra a proporção relativa do valor total representado por cada convênio.
                Quanto maior o retângulo, maior a participação do convênio no valor total pendente.
                """)
            
            elif viz_type == "Distribuição de Valores":
                st.markdown("#### Distribuição dos Valores das Contas")
                
                # Criar histograma com plotly
                fig_hist = px.histogram(
                    df_filtrado,
                    x="Valor conta",
                    nbins=50,
                    marginal="box",
                    labels={"Valor conta": "Valor da Conta (R$)", "count": "Frequência"}
                )
                st.plotly_chart(fig_hist, use_container_width=True)
                
                # Estatísticas da distribuição
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Média", formatar_moeda(df_filtrado["Valor conta"].mean()))
                with col2:
                    st.metric("Mediana", formatar_moeda(df_filtrado["Valor conta"].median()))
                with col3:
                    st.metric("Mínimo", formatar_moeda(df_filtrado["Valor conta"].min()))
                with col4:
                    st.metric("Máximo", formatar_moeda(df_filtrado["Valor conta"].max()))
                
                st.markdown("""
                **Como interpretar:** Este histograma mostra a distribuição dos valores das contas pendentes.
                Uma distribuição com cauda longa para a direita (positiva) é comum em dados financeiros,
                indicando poucas contas com valores muito altos e muitas contas com valores menores.
                """)
            
            elif viz_type == "Mapa de Calor por Mês/Dia":
                st.markdown("#### Mapa de Calor por Mês/Dia")
                
                # Extrair mês e dia da semana
                df_calendar = df_filtrado.copy()
                df_calendar["Mês"] = df_calendar["Data entrada"].dt.month_name()
                df_calendar["Dia da Semana"] = df_calendar["Data entrada"].dt.day_name()
                
                # Agrupar por mês e dia da semana
                calendar_agg = df_calendar.groupby(["Mês", "Dia da Semana"])["Valor conta"].agg(
                    Quantidade="count",
                    Valor_Total="sum"
                ).reset_index()
                
                # Ordenar meses e dias da semana
                meses_ordem = [calendar.month_name()[i] for i in range(1, 13)]
                dias_ordem = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                
                # Traduzir para português se necessário
                meses_pt = {
                    "January": "Janeiro", "February": "Fevereiro", "March": "Março",
                    "April": "Abril", "May": "Maio", "June": "Junho",
                    "July": "Julho", "August": "Agosto", "September": "Setembro",
                    "October": "Outubro", "November": "Novembro", "December": "Dezembro"
                }
                
                dias_pt = {
                    "Monday": "Segunda", "Tuesday": "Terça", "Wednesday": "Quarta",
                    "Thursday": "Quinta", "Friday": "Sexta", "Saturday": "Sábado", "Sunday": "Domingo"
                }
                
                calendar_agg["Mês"] = pd.Categorical(calendar_agg["Mês"], categories=meses_ordem, ordered=True)
                calendar_agg["Dia da Semana"] = pd.Categorical(calendar_agg["Dia da Semana"], categories=dias_ordem, ordered=True)
                calendar_agg = calendar_agg.sort_values(["Mês", "Dia da Semana"])
                
                # Criar pivot para o heatmap
                pivot_calendar = calendar_agg.pivot(index="Dia da Semana", columns="Mês", values="Valor_Total")
                
                # Substituir nomes em inglês por português se necessário
                pivot_calendar.index = pivot_calendar.index.map(lambda x: dias_pt.get(x, x))
                pivot_calendar.columns = pivot_calendar.columns.map(lambda x: meses_pt.get(x, x))
                
                # Criar heatmap
                fig_calendar = px.imshow(
                    pivot_calendar,
                    labels=dict(x="Mês", y="Dia da Semana", color="Valor Total"),
                    aspect="auto",
                    text_auto=lambda v: formatar_moeda(v) if not pd.isna(v) else ""
                )
                fig_calendar.update_layout(height=400)
                st.plotly_chart(fig_calendar, use_container_width=True)
                
                st.markdown("""
                **Como interpretar:** Este mapa de calor mostra a distribuição do valor total das contas de acordo com o mês e dia da semana.
                Cores mais intensas indicam maiores valores. Esse padrão pode ajudar a identificar sazonalidades ou dias da semana com maior volume financeiro.
                """)
        
        # Adicionar seção para análise preditiva
        with st.expander("🔮 Projeções e Tendências", expanded=False):
            st.markdown("### 🔮 Projeções e Tendências")
            
            # Análise de tendência mensal
            st.markdown("#### Tendência de Valores Pendentes")
            
            df_mensal = df_filtrado.copy()
            df_mensal["AnoMes"] = df_mensal["Data entrada"].dt.to_period("M")
            tendencia_valor = df_mensal.groupby("AnoMes")["Valor conta"].sum().reset_index()
            tendencia_valor["AnoMes"] = tendencia_valor["AnoMes"].astype(str)
            
            # Calcular média móvel de 3 meses
            if len(tendencia_valor) >= 3:
                tendencia_valor["Media_Movel"] = tendencia_valor["Valor conta"].rolling(window=3).mean()
            
            # Criar gráfico de tendência
            fig_trend = px.line(
                tendencia_valor,
                x="AnoMes",
                y="Valor conta",
                markers=True,
                labels={"Valor conta": "Valor Total (R$)", "AnoMes": "Mês"}
            )
            
            # Adicionar média móvel se tiver dados suficientes
            if len(tendencia_valor) >= 3:
                fig_trend.add_scatter(
                    x=tendencia_valor["AnoMes"],
                    y=tendencia_valor["Media_Movel"],
                    mode="lines",
                    name="Média Móvel (3 meses)",
                    line=dict(color="red", dash="dash")
                )
            
            st.plotly_chart(fig_trend, use_container_width=True)
            
            # Análise de sazonalidade
            st.markdown("#### Sazonalidade por Dia da Semana")
            
            df_dia_semana = df_filtrado.copy()
            df_dia_semana["Dia da Semana"] = df_dia_semana["Data entrada"].dt.day_name()
            
            # Ordenar os dias da semana
            dias_ordem = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            dias_pt = {
                "Monday": "Segunda", "Tuesday": "Terça", "Wednesday": "Quarta",
                "Thursday": "Quinta", "Friday": "Sexta", "Saturday": "Sábado", "Sunday": "Domingo"
            }
            
            dia_semana_agg = df_dia_semana.groupby("Dia da Semana")["Valor conta"].agg(
                Quantidade="count",
                Valor_Total="sum"
            ).reset_index()
            
            # Ordenar os dias e traduzir se necessário
            dia_semana_agg["Dia da Semana"] = pd.Categorical(dia_semana_agg["Dia da Semana"], categories=dias_ordem, ordered=True)
            dia_semana_agg = dia_semana_agg.sort_values("Dia da Semana")
            dia_semana_agg["Dia da Semana"] = dia_semana_agg["Dia da Semana"].map(lambda x: dias_pt.get(x, x))
            
            # Criar gráfico de barras
            col1, col2 = st.columns(2)
            
            with col1:
                fig_dia_qtd = px.bar(
                    dia_semana_agg,
                    x="Dia da Semana",
                    y="Quantidade",
                    text_auto=True,
                    labels={"Quantidade": "Quantidade de Contas", "Dia da Semana": "Dia da Semana"}
                )
                st.plotly_chart(fig_dia_qtd, use_container_width=True)
            
            with col2:
                fig_dia_valor = px.bar(
                    dia_semana_agg,
                    x="Dia da Semana",
                    y="Valor_Total",
                    text_auto=True,
                    labels={"Valor_Total": "Valor Total (R$)", "Dia da Semana": "Dia da Semana"}
                )
                fig_dia_valor.update_traces(texttemplate='%{y:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'), textposition='outside')
                st.plotly_chart(fig_dia_valor, use_container_width=True)
        
        # Adicionar seção para insights de eficiência operacional
        with st.expander("🔄 Eficiência Operacional", expanded=False):
            st.markdown("### 🔄 Análise de Eficiência Operacional")
            
            # Calcular métricas de eficiência
            df_eficiencia = df_filtrado.copy()
            df_eficiencia["Dias Pendentes"] = (pd.Timestamp.today().normalize() - df_eficiencia["Data entrada"].dt.normalize()).dt.days
            
            # Tempo médio por setor
            tempo_medio_setor = df_eficiencia.groupby("Último Setor destino")["Dias Pendentes"].mean().sort_values(ascending=False)
            
            # Gráfico de tempo médio por setor
            st.markdown("#### Tempo Médio por Setor (Top 10)")
            fig_tempo_setor = px.bar(
                tempo_medio_setor.head(10).reset_index(),
                x="Último Setor destino",
                y="Dias Pendentes",
                text_auto=True,
                labels={"Dias Pendentes": "Dias Médios", "Último Setor destino": "Setor"}
            )
            fig_tempo_setor.update_traces(texttemplate='%{y:.1f}', textposition='outside')
            fig_tempo_setor.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_tempo_setor, use_container_width=True)
            
            # Análise de gargalos
            st.markdown("#### Gargalos Identificados (Contas > 90 dias)")
            
            gargalos = df_eficiencia[df_eficiencia["Dias Pendentes"] > 90].groupby("Último Setor destino").agg(
                Quantidade=("Conta", "count"),
                Valor_Total=("Valor conta", "sum"),
                Tempo_Medio=("Dias Pendentes", "mean")
            ).sort_values(by="Quantidade", ascending=False).reset_index()
            
            if not gargalos.empty:
                gargalos["% do Total de Contas"] = (gargalos["Quantidade"] / df_eficiencia[df_eficiencia["Dias Pendentes"] > 90].shape[0]) * 100
                
                st.dataframe(
                    gargalos.head(10).style.format({
                        "Valor_Total": formatar_moeda,
                        "Tempo_Medio": "{:.1f}",
                        "% do Total de Contas": "{:.2f}%"
                    }),
                    height=300
                )
                
                # Gráfico de Pareto para gargalos
                st.markdown("#### Análise de Pareto - Gargalos por Quantidade de Contas")
                
                # Preparar dados para Pareto
                pareto_data = gargalos.copy()
                pareto_data = pareto_data.sort_values(by="Quantidade", ascending=False)
                pareto_data["Percentual Acumulado"] = pareto_data["Quantidade"].cumsum() / pareto_data["Quantidade"].sum() * 100
                
                # Criar gráfico de Pareto
                fig_pareto = go.Figure()
                
                # Adicionar barras
                fig_pareto.add_trace(go.Bar(
                    x=pareto_data["Último Setor destino"].head(10),
                    y=pareto_data["Quantidade"].head(10),
                    name="Quantidade",
                    text=pareto_data["Quantidade"].head(10),
                    textposition="outside"
                ))
                
                # Adicionar linha de percentual acumulado
                fig_pareto.add_trace(go.Scatter(
                    x=pareto_data["Último Setor destino"].head(10),
                    y=pareto_data["Percentual Acumulado"].head(10),
                    name="% Acumulado",
                    mode="lines+markers",
                    yaxis="y2",
                    line=dict(color="red"),
                    marker=dict(size=8)
                ))
                
                # Configurar layout
                fig_pareto.update_layout(
                    xaxis=dict(title="Setor"),
                    yaxis=dict(title="Quantidade de Contas", side="left"),
                    yaxis2=dict(
                        title="Percentual Acumulado (%)",
                        side="right",
                        overlaying="y",
                        range=[0, 100],
                        showgrid=False,
                        ticksuffix="%"
                    ),
                    legend=dict(x=0.01, y=0.99),
                    barmode="group"
                )
                
                st.plotly_chart(fig_pareto, use_container_width=True)
                
                st.markdown("""
                **Como interpretar o gráfico de Pareto:**
                - Este gráfico mostra quais setores concentram a maior parte das contas pendentes há mais de 90 dias
                - A linha vermelha representa o percentual acumulado
                - Setores à esquerda representam os principais gargalos que, se resolvidos, terão o maior impacto na redução de pendências
                """)
            else:
                st.info("Não foram encontradas contas com mais de 90 dias pendentes.")
        
        # Adicionar botão para exportar análise completa
        st.markdown("### 📊 Exportar Análise Completa")
        
        if st.button("Gerar Relatório Completo"):
            from io import BytesIO
            
            # Criar buffer para o Excel
            buffer = BytesIO()
            
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                # Resumo geral
                pd.DataFrame([kpis_filtrados]).to_excel(writer, sheet_name="Resumo Geral", index=False)
                
                # Análise por convênio
                resumo_convenio.reset_index().to_excel(writer, sheet_name="Análise por Convênio", index=False)
                
                # Análise por setor
                resumo_etapa.reset_index().to_excel(writer, sheet_name="Análise por Setor", index=False)
                
                # Análise por médico
                resumo_medico.reset_index().to_excel(writer, sheet_name="Análise por Médico", index=False)
                
                # Contas com problemas
                if not zeradas_df.empty:
                    zeradas_df.to_excel(writer, sheet_name="Contas Zeradas", index=False)
                
                if not outliers_df.empty:
                    outliers_df.to_excel(writer, sheet_name="Contas Outliers", index=False)
                
                if not antigas_df.empty:
                    antigas_df.to_excel(writer, sheet_name="Contas >90 dias", index=False)
                
                # Análise de aging
                df_filtrado.groupby("Categoria Aging").agg(
                    Quantidade=("Conta", "count"),
                    Valor_Total=("Valor conta", "sum")
                ).reset_index().to_excel(writer, sheet_name="Aging", index=False)
                
                # Dados filtrados
                df_filtrado.to_excel(writer, sheet_name="Dados Completos", index=False)
            
            # Oferecer para download
            st.download_button(
                label="📥 Baixar Relatório Excel",
                data=buffer.getvalue(),
                file_name=f"analise_faturamento_hospital_{datetime.today().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            st.success("Relatório gerado com sucesso! Clique no botão acima para baixar.")
else:
    st.info("👆 Faça o upload de uma planilha Excel para começar a análise de faturamento hospitalar.")
    
    # Mostrar modelo de exemplo
    st.markdown("""
    ### 📋 Como usar esta ferramenta
    
    1. Faça o upload de uma planilha Excel contendo os dados de contas pendentes do hospital
    2. A planilha deve conter as seguintes colunas:
        - Status
        - Tipo atendimento
        - Conta
        - Atendimento
        - Status atendimento
        - Convênio
        - Categoria
        - Valor conta
        - Etapa anterior
        - Último Setor destino
        - Setor atendimento
        - Estabelecimento
        - Data entrada
        - Médico executor
    3. Após o upload, utilize os filtros no painel lateral para refinar sua análise
    4. Explore as diferentes abas para obter insights específicos
    
    ### 🔍 Principais recursos
    
    - **Dashboard Principal**: Visão geral dos KPIs mais importantes
    - **Insights**: Análises rápidas com possibilidade de download de planilhas específicas
    - **Análise por Convênio**: Detalhamento financeiro por convênio
    - **Análise por Fluxo**: Identificação de gargalos no processo
    - **Análise por Médico**: Performance financeira por médico
    - **Visualizações Avançadas**: Gráficos detalhados para análise aprofundada
    - **Projeções e Tendências**: Análise temporal e sazonalidade
    - **Eficiência Operacional**: Identificação de gargalos e oportunidades de melhoria
    
    ### 📊 Exportação de dados
    
    Você pode exportar qualquer análise específica ou gerar um relatório completo em Excel.
    """)
