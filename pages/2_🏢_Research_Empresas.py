# pages/2_🏢_Research_Empresas.py

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# --- Configuração da Página ---
st.set_page_config(
    page_title="PAG | Research de Empresas",
    page_icon="🏢",
    layout="wide"
)

# --- Título e Descrição ---
st.title("Painel de Research de Empresas")
st.markdown("Analise ações individuais do Brasil e dos EUA.")

# --- Barra Lateral com Inputs ---
st.sidebar.header("Filtros de Análise")
ticker_symbol = st.sidebar.text_input(
    "Digite o Ticker da Ação", 
    "AAPL",  # Valor padrão (Apple)
    help="Exemplos: AAPL para Apple, PETR4.SA para Petrobras."
).upper()

analyze_button = st.sidebar.button("Analisar")

# --- Lógica Principal ---
if analyze_button:
    if not ticker_symbol:
        st.warning("Por favor, digite um ticker para analisar.")
    else:
        try:
            with st.spinner(f"Carregando dados de {ticker_symbol}..."):
                # Baixa os dados da ação usando yfinance
                ticker = yf.Ticker(ticker_symbol)
                
                # Pega as informações da empresa (um dicionário)
                info = ticker.info

                # Verifica se o ticker é válido (se 'longName' existe)
                if not info.get('longName'):
                    st.error(f"Ticker '{ticker_symbol}' não encontrado ou inválido. Verifique o código.")
                else:
                    # --- Seção de Informações Gerais ---
                    st.header(f"Visão Geral de: {info['longName']} ({info['symbol']})")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("País", info.get('country', 'N/A'))
                        st.metric("Setor", info.get('sector', 'N/A'))
                        st.metric("Indústria", info.get('industry', 'N/A'))

                    with col2:
                        st.metric("Moeda", info.get('currency', 'N/A'))
                        st.metric("Preço Atual", f"{info.get('currentPrice', 0):.2f}")
                        st.metric("Valor de Mercado", f"{(info.get('marketCap', 0) / 1e9):.2f} Bilhões")

                    with st.expander("Descrição da Empresa"):
                        st.write(info.get('longBusinessSummary', 'Descrição não disponível.'))
                    
                    # --- Seção de Gráfico de Preços ---
                    st.header("Histórico de Cotações")
                    
                    # Baixa o histórico de preços
                    hist_df = ticker.history(period="5y") # 5 anos de histórico

                    fig = px.line(
                        hist_df, 
                        x=hist_df.index, 
                        y="Close", 
                        title=f"Preço de Fechamento de {info['shortName']}",
                        labels={'Close': 'Preço de Fechamento (USD)', 'Date': 'Data'}
                    )
                    st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Ocorreu um erro ao buscar os dados: {e}")

else:
    st.info("Digite um ticker na barra lateral e clique em 'Analisar' para começar.")
