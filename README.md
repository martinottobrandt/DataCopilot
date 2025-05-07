
# DataCopilot

**DataCopilot** é um aplicativo interativo desenvolvido com Streamlit para auxiliar na **análise exploratória de dados** hospitalares, com foco em **contas médicas pendentes**. Ele oferece recursos como análise por convênio, status de atendimento, valores outliers e fluxos entre etapas do processo de faturamento.

## 🚀 Funcionalidades

- Estatísticas descritivas dos valores de conta
- Resumo por convênio (total de contas, valor médio, total)
- Análise mensal por convênio (contas distintas e valor total)
- Identificação de contas com valores atípicos (outliers)
- Visualizações gráficas: Boxplot, TreeMap e Sankey
- Filtro interativo por convênio

## 📦 Requisitos

Antes de rodar o app, instale as dependências:

```bash
pip install -r requirements.txt
```

## ▶️ Como executar

Execute o app com Streamlit:

```bash
streamlit run eda_streamlit_app.py
```

## 🌐 Publicação

Este projeto pode ser publicado diretamente no [Streamlit Cloud](https://streamlit.io/cloud) vinculando este repositório GitHub.

## 📁 Estrutura

```
data-copilot/
├── eda_streamlit_app.py       # Código principal do app
├── requirements.txt           # Dependências
└── README.md                  # Este arquivo
```

## 📄 Licença

Distribuído sob a licença MIT. Sinta-se à vontade para usar, modificar e expandir.

---

Criado com ❤️ por [Seu Nome ou Empresa]
