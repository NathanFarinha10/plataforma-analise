# Arquivo: Plataforma_PAG.py (Versão Final com Splash, Login e Dashboard)

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime
import time

# --- Configuração da Página ---
st.set_page_config(
    page_title="Highpar Global", 
    page_icon="📈", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- Adiciona a logo no topo da barra lateral ---
try:
    st.sidebar.image("logo.png", use_container_width=True)
except Exception:
    # Se a logo não for encontrada, não quebra a aplicação
    st.sidebar.warning("Logo não encontrada.")

# --- BANCO DE DADOS DE USUÁRIOS E SENHAS (PARA TESTE) ---
VALID_CREDENTIALS = {
    "jsilva": "senha123",
    "aoliveira": "senha456"
}

# --- FUNÇÕES AUXILIARES ---
@st.cache_data(ttl=900) # Cache de 15 minutos para dados de mercado
def get_homepage_market_data():
    """Busca os dados de mercado para o ticker do topo da página."""
    tickers = {
        "S&P 500": "^GSPC", "Ibovespa": "^BVSP", "Dólar (USD/BRL)": "BRL=X",
        "VIX": "^VIX", "US 10Y Treasury": "^TNX"
    }
    data = yf.download(list(tickers.values()), period="5d", progress=False)['Close']
    results = {}
    for name, ticker in tickers.items():
        if ticker in data.columns and not data[ticker].isnull().all():
            latest_price = data[ticker].dropna().iloc[-1]
            previous_price = data[ticker].dropna().iloc[-2]
            change = ((latest_price / previous_price) - 1) * 100
            results[name] = {"price": latest_price, "change": change}
    return results

def login_form():
    """Função para criar e gerenciar o formulário de login."""
    st.title("Bem-vindo à Highpar Global")
    st.markdown("Por favor, faça o login para continuar.")
    
    with st.form("login_form"):
        username = st.text_input("Usuário").lower()
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if username in VALID_CREDENTIALS and password == VALID_CREDENTIALS[username]:
                st.session_state["authentication_status"] = True
                st.session_state["username"] = username
                user_details = {"jsilva": {"name": "João Silva", "role": "Advisor"}, "aoliveira": {"name": "Ana Oliveira", "role": "Analista"}}
                st.session_state["name"] = user_details.get(username, {}).get("name", "Usuário")
                st.session_state["role"] = user_details.get(username, {}).get("role", "Visitante")
                st.rerun()
            else:
                st.error("Usuário ou senha incorreto(a)")

# --- LÓGICA DE EXIBIÇÃO PRINCIPAL ---

# 1. TELA DE SPLASH (só roda uma vez por sessão)
if 'splash_screen_done' not in st.session_state:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("logo.png", use_container_width=True)
        except Exception:
            st.markdown("<h1 style='text-align: center;'>Highpar Global</h1>", unsafe_allow_html=True)
        with st.spinner("Carregando plataforma..."):
            time.sleep(4)
    st.session_state.splash_screen_done = True
    st.rerun()

# 2. TELA DE LOGIN (se o usuário não estiver autenticado)
if not st.session_state.get("authentication_status"):
    login_form()

# 3. DASHBOARD PRINCIPAL (se o usuário estiver autenticado)
else:
    # Barra lateral para usuários logados
    with st.sidebar:
        st.write(f'Bem-vindo(a), *{st.session_state["name"]}*')
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                if key != 'splash_screen_done': del st.session_state[key]
            st.rerun()

    # Conteúdo do Dashboard
    st.title("Dashboard de Visão Geral - Highpar Global")
    st.caption(f"Dados de mercado atualizados em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    try:
        market_data = get_homepage_market_data()
        c1, c2, c3, c4, c5 = st.columns(5)
        if "S&P 500" in market_data: c1.metric("S&P 500", f"{market_data['S&P 500']['price']:.2f}", f"{market_data['S&P 500']['change']:.2f}%")
        if "Ibovespa" in market_data: c2.metric("Ibovespa", f"{market_data['Ibovespa']['price']:.2f}", f"{market_data['Ibovespa']['change']:.2f}%")
        if "Dólar (USD/BRL)" in market_data: c3.metric("Dólar (USD/BRL)", f"{market_data['Dólar (USD/BRL)']['price']:.2f}", f"{market_data['Dólar (USD/BRL)']['change']:.2f}%")
        if "US 10Y Treasury" in market_data: c4.metric("US 10Y Yield", f"{market_data['US 10Y Treasury']['price']:.2f}%", f"{market_data['US 10Y Treasury']['change']:.2f}%")
        if "VIX" in market_data: c5.metric("VIX (Volatilidade)", f"{market_data['VIX']['price']:.2f}", f"{market_data['VIX']['change']:.2f}%", delta_color="inverse")
    except Exception as e:
        st.warning(f"Não foi possível carregar os dados do ticker de mercado no momento: {e}")

    st.divider()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Visão Estratégica Highpar")
        st.info("OVERWEIGHT: Ações Internacionais.\n\nNEUTRO: Ações Brasil, FIIs.\n\nUNDERWEIGHT: Renda Fixa Pré-Fixada.")
        st.caption("Visão tática do nosso Comitê de Investimentos.")

    with col2:
        st.subheader("Pulso dos Mercados (Últimos 30 dias)")
        data_sp500 = yf.download("^GSPC", period="1mo", progress=False)['Close']
        data_tnx = yf.download("^TNX", period="1mo", progress=False)['Close']
        tab1, tab2 = st.tabs(["Ações (S&P 500)", "Juros (US 10Y)"])
        with tab1:
            st.area_chart(data_sp500)
        with tab2:
            st.area_chart(data_tnx)

    st.divider()
    st.header("Navegue pelos Módulos de Análise")
    st.info("Utilize o menu à esquerda para acessar as ferramentas detalhadas de cada área.")
