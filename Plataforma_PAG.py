# Arquivo: Plataforma_PAG.py (Versão com Novo Dashboard Inicial)

import streamlit as st
import streamlit_authenticator as stauth
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- Configuração da Página ---
st.set_page_config(
    page_title="Highpar Global", # <-- NOME ATUALIZADO
    page_icon="📈", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- Adiciona a logo na barra lateral ---
try:
    st.sidebar.image("logo.png", use_container_width=True)
except Exception:
    st.sidebar.warning("Arquivo de logo 'logo.png' não encontrado.")

# --- DADOS E LÓGICA DE LOGIN (Simplificado) ---
# (O código de login permanece o mesmo)
# ...

# --- FUNÇÃO AUXILIAR PARA O NOVO DASHBOARD ---
@st.cache_data(ttl=900) # Cache de 15 minutos para dados de mercado
def get_homepage_market_data():
    tickers = {
        "S&P 500": "^GSPC",
        "Ibovespa": "^BVSP",
        "Dólar (USD/BRL)": "BRL=X",
        "VIX": "^VIX",
        "US 10Y Treasury": "^TNX"
    }
    data = yf.download(list(tickers.values()), period="5d", progress=False)['Close']
    
    results = {}
    for name, ticker in tickers.items():
        latest_price = data[ticker].iloc[-1]
        previous_price = data[ticker].iloc[-2]
        change = ((latest_price / previous_price) - 1) * 100
        results[name] = {"price": latest_price, "change": change}
    
    return results

# --- LÓGICA DE EXIBIÇÃO DA PÁGINA ---
if not st.session_state.get("authentication_status"):
    # (A lógica do formulário de login permanece a mesma)
    # ...
else:
    # --- NOVO DASHBOARD PARA USUÁRIOS LOGADOS ---
    with st.sidebar:
        st.write(f'Bem-vindo(a), *{st.session_state["name"]}*')
        st.button("Logout", on_click=lambda: st.session_state.clear(), use_container_width=True)

    st.title("Dashboard de Visão Geral - Highpar Global") # <-- TÍTULO ATUALIZADO
    st.caption(f"Dados atualizados em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    # --- Market Ticker ---
    try:
        market_data = get_homepage_market_data()
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric(label="S&P 500", value=f"{market_data['S&P 500']['price']:.2f}", delta=f"{market_data['S&P 500']['change']:.2f}%")
        c2.metric(label="Ibovespa", value=f"{market_data['Ibovespa']['price']:.2f}", delta=f"{market_data['Ibovespa']['change']:.2f}%")
        c3.metric(label="Dólar (USD/BRL)", value=f"{market_data['Dólar (USD/BRL)']['price']:.2f}", delta=f"{market_data['Dólar (USD/BRL)']['change']:.2f}%")
        c4.metric(label="US 10Y Yield", value=f"{market_data['US 10Y Treasury']['price']:.2f}%", delta=f"{market_data['US 10Y Treasury']['change']:.2f}%")
        c5.metric(label="VIX (Volatilidade)", value=f"{market_data['VIX']['price']:.2f}", delta=f"{market_data['VIX']['change']:.2f}%", delta_color="inverse")
    except Exception as e:
        st.warning(f"Não foi possível carregar os dados do ticker de mercado: {e}")

    st.divider()

    # --- Visão da Casa e Resumo dos Mercados ---
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Visão Estratégica Highpar")
        st.info("""
        - **OVERWEIGHT:** Ações Internacionais.
        - **NEUTRO:** Ações Brasil, FIIs.
        - **UNDERWEIGHT:** Renda Fixa Pré-Fixada.
        """)
        st.caption("Visão tática do nosso Comitê de Investimentos para o trimestre.")

    with col2:
        st.subheader("Pulso dos Mercados")
        # Dados para os mini-gráficos
        sp500_hist = yf.download("^GSPC", period="1mo", progress=False)['Close']
        tnx_hist = yf.download("^TNX", period="1mo", progress=False)['Close']
        
        tab1, tab2, tab3 = st.tabs(["Ações (S&P 500)", "Juros (US 10Y)", "Última Visão de Player"])
        with tab1:
            st.line_chart(sp500_hist)
        with tab2:
            st.line_chart(tnx_hist)
        with tab3:
            # Esta parte pode ser conectada ao seu arquivo de recomendações no futuro
            st.markdown("##### BlackRock | **Overweight** em Ações EUA")
            st.caption("Relatório de Julho/2025: 'Vemos resiliência nos lucros corporativos, sustentando uma visão positiva para ações de qualidade no mercado americano.'")

    st.divider()
    st.header("Navegue pelos Módulos de Análise")
    st.info("Utilize o menu à esquerda para acessar as ferramentas detalhadas de cada área.")
