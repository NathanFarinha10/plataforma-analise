# 1_📈_Análise_Macro.py (Versão 3.1 - Final com Visão do Banco Central)

import streamlit as st
import pandas as pd
from fredapi import Fred
from bcb import sgs
import plotly.express as px
from datetime import datetime
import yfinance as yf
import numpy as np
import re

# --- Configuração da Página ---
st.set_page_config(page_title="PAG | Análise Macro", page_icon="🌍", layout="wide")

# --- INICIALIZAÇÃO DAS APIS ---
@st.cache_resource
def get_fred_api():
    """Inicializa a conexão com a API do FRED."""
    try:
        api_key = st.secrets.get("FRED_API_KEY")
        if not api_key:
            st.error("Chave da API do FRED (FRED_API_KEY) não configurada nos segredos do Streamlit.")
            st.stop()
        return Fred(api_key=api_key)
    except Exception as e:
        st.error(f"Falha ao inicializar API do FRED: {e}")
        st.stop()
fred = get_fred_api()

# --- FUNÇÕES AUXILIARES ---
@st.cache_data(ttl=3600)
def fetch_fred_series(code, start_date):
    """Busca uma única série do FRED de forma robusta."""
    try:
        return fred.get_series(code, start_date)
    except Exception:
        return pd.Series(dtype='float64')

@st.cache_data(ttl=3600)
def fetch_bcb_series(code, start_date):
    """Busca uma única série do BCB SGS de forma robusta."""
    try:
        df = sgs.get({str(code): code}, start=start_date)
        if not df.empty and str(code) in df.columns:
            return df[str(code)]
        else:
            return pd.Series(dtype='float64')
    except Exception:
        return pd.Series(dtype='float64')

@st.cache_data(ttl=86400)
def fetch_market_data(tickers, period="5y"):
    """Baixa dados de mercado do Yahoo Finance de forma robusta."""
    try:
        return yf.download(tickers, period=period, progress=False)['Close']
    except Exception:
        return pd.DataFrame()

def plot_indicator(data, title, y_label="Valor"):
    """Função genérica para plotar um gráfico de área."""
    if data is None or data.empty:
        st.warning(f"Não foi possível carregar os dados para {title}.")
        return
    fig = px.area(data, title=title, labels={"value": y_label, "index": "Data"})
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

def analyze_central_bank_discourse(text, lang='pt'):
    """Analisa o texto de atas de política monetária e retorna scores Hawkish/Dovish."""
    text = text.lower()
    text = re.sub(r'\d+', '', text)
    
    if lang == 'pt':
        hawkish_words = ['inflação', 'risco', 'preocupação', 'desancoragem', 'expectativas', 'cautela', 'perseverança', 'serenidade', 'aperto', 'restritiva', 'incerteza', 'desafios']
        dovish_words = ['crescimento', 'atividade', 'hiato', 'ociosidade', 'arrefecimento', 'desaceleração', 'flexibilização', 'estímulo', 'progresso']
    else: # English for FOMC
        hawkish_words = ['inflation', 'risk', 'tightening', 'restrictive', 'concern', 'hike', 'vigilance', 'uncertainty', 'upside risks']
        dovish_words = ['growth', 'employment', 'slack', 'easing', 'accommodation', 'progress', 'softening', 'cut', 'achieved']
    
    hawkish_score = sum(text.count(word) for word in hawkish_words)
    dovish_score = sum(text.count(word) for word in dovish_words)
    
    return hawkish_score, dovish_score

# --- UI DA APLICAÇÃO ---
st.title("🌍 Painel de Análise Macroeconômica")
start_date = "2010-01-01"

tab_br, tab_us, tab_global = st.tabs(["🇧🇷 Brasil", "🇺🇸 Estados Unidos", "🌐 Mercados Globais"])

# --- ABA BRASIL ---
with tab_br:
    st.header("Principais Indicadores do Brasil")
    subtab_br_activity, subtab_br_inflation, subtab_br_bc = st.tabs(["Atividade e Emprego", "Inflação e Juros", "Visão do Banco Central"])
    
    with subtab_br_activity:
        st.subheader("Atividade Econômica")
        plot_indicator(fetch_bcb_series(24369, start_date).pct_change(12).dropna() * 100, "IBC-Br (Prévia do PIB, Var. Anual %)", "Variação %")
        st.subheader("Emprego")
        plot_indicator(fetch_bcb_series(24369, start_date), "Taxa de Desemprego (PNADC %)", "% da Força de Trabalho")

    with subtab_br_inflation:
        st.subheader("Inflação")
        plot_indicator(fetch_bcb_series(13522, start_date), "IPCA (Inflação ao Consumidor, Acum. 12M %)", "Variação %")
        st.subheader("Taxa de Juros")
        plot_indicator(fetch_bcb_series(432, start_date), "Taxa Selic (Anualizada %)", "Taxa %")
    
    with subtab_br_bc:
        st.subheader("Indicadores Monetários (BCB)")
        plot_indicator(fetch_bcb_series(27841, start_date).pct_change(12).dropna()*100, "Agregado Monetário M2 (Var. Anual %)", "Variação %")
        st.divider()
        st.subheader("Análise do Discurso (Ata do Copom)")
        copom_text = st.text_area("Cole aqui o texto da ata do Copom para análise:", height=200, key="copom_text")
        if st.button("Analisar Discurso do Copom", key="copom_btn"):
            if copom_text.strip():
                h_score, d_score = analyze_central_bank_discourse(copom_text, lang='pt')
                col1, col2, col3 = st.columns(3)
                col1.metric("Placar Hawkish 🦅", h_score)
                col2.metric("Placar Dovish 🕊️", d_score)
                balance = h_score - d_score
                final_tone = "Hawkish" if balance > 0 else "Dovish" if balance < 0 else "Neutro"
                col3.metric("Balanço Final", final_tone)
            else:
                st.warning("Por favor, insira um texto para ser analisado.")

# --- ABA EUA ---
with tab_us:
    st.header("Principais Indicadores dos Estados Unidos")
    subtab_us_activity, subtab_us_inflation, subtab_us_yield, subtab_us_bc = st.tabs(["Atividade e Emprego", "Inflação e Juros", "Curva de Juros", "Visão do Fed"])
    
    with subtab_us_activity:
        st.subheader("Atividade Econômica")
        plot_indicator(fetch_fred_series("GDPC1", start_date).pct_change(4).dropna() * 100, "PIB Real (Var. Anual %)", "Variação %")
        st.subheader("Emprego")
        plot_indicator(fetch_fred_series("UNRATE", start_date), "Taxa de Desemprego (%)", "% da Força de Trabalho")

    with subtab_us_inflation:
        st.subheader("Inflação")
        plot_indicator(fetch_fred_series("CPIAUCSL", start_date).pct_change(12).dropna() * 100, "CPI (Var. Anual %)", "Variação %")
        st.subheader("Taxa de Juros")
        plot_indicator(fetch_fred_series("FEDFUNDS", start_date), "Federal Funds Rate (%)", "Taxa %")
    
    with subtab_us_yield:
        st.subheader("Spread da Curva de Juros (10 Anos - 2 Anos)")
        juro_10a = fetch_fred_series("DGS10", start_date)
        juro_2a = fetch_fred_series("DGS2", start_date)
        if not juro_10a.empty and not juro_2a.empty:
            yield_spread = (juro_10a - juro_2a).dropna()
            fig = px.area(yield_spread, title="Spread 10 Anos - 2 Anos (EUA)")
            fig.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Inversão (Sinal de Recessão)")
            st.plotly_chart(fig, use_container_width=True)
    
    with subtab_us_bc:
        st.subheader("Indicadores Monetários (Fed)")
        plot_indicator(fetch_fred_series("M2SL", start_date).pct_change(12).dropna()*100, "Agregado Monetário M2 (Var. Anual %)", "Variação %")
        st.divider()
        st.subheader("Análise do Discurso (Ata do FOMC)")
        fomc_text = st.text_area("Cole aqui o texto da ata do FOMC para análise:", height=200, key="fomc_text")
        if st.button("Analisar Discurso do FOMC", key="fomc_btn"):
            if fomc_text.strip():
                h_score, d_score = analyze_central_bank_discourse(fomc_text, lang='en')
                col1, col2, col3 = st.columns(3)
                col1.metric("Placar Hawkish 🦅", h_score)
                col2.metric("Placar Dovish 🕊️", d_score)
                balance = h_score - d_score
                final_tone = "Hawkish" if balance > 0 else "Dovish" if balance < 0 else "Neutro"
                col3.metric("Balanço Final", final_tone)
            else:
                st.warning("Por favor, insira um texto para ser analisado.")

# --- ABA MERCADOS GLOBAIS ---
with tab_global:
    st.header("Índices e Indicadores de Mercado Global")
    subtab_equity, subtab_commodities, subtab_risk, subtab_valuation = st.tabs(["Índices de Ações", "Commodities & Moedas", "Risco & Volatilidade", "Valuation"])

    with subtab_equity:
        st.subheader("Performance Comparada de Índices de Ações")
        equity_tickers = {"S&P 500 (EUA)": "^GSPC", "Ibovespa (Brasil)": "^BVSP", "Nasdaq (EUA Tech)": "^IXIC", "DAX (Alemanha)": "^GDAXI", "Nikkei 225 (Japão)": "^N225"}
        selected_indices = st.multiselect("Selecione os índices:", options=list(equity_tickers.keys()), default=["S&P 500 (EUA)", "Ibovespa (Brasil)"])
        if selected_indices:
            tickers_to_fetch = [equity_tickers[i] for i in selected_indices]
            market_data = fetch_market_data(tickers_to_fetch)
            if not market_data.empty:
                normalized_data = (market_data / market_data.dropna().iloc[0]) * 100
                st.plotly_chart(px.line(normalized_data, title="Performance Normalizada (Base 100)"), use_container_width=True)

    with subtab_commodities:
        st.subheader("Preços de Commodities e Taxas de Câmbio")
        col1, col2 = st.columns(2)
        with col1:
            commodity_tickers = {"Petróleo WTI": "CL=F", "Ouro": "GC=F"}
            commodity_data = fetch_market_data(list(commodity_tickers.values()))
            if not commodity_data.empty:
                commodity_data.rename(columns=lambda c: next(k for k, v in commodity_tickers.items() if v == c), inplace=True)
                st.plotly_chart(px.line(commodity_data, title="Evolução de Commodities"), use_container_width=True)
        with col2:
            currency_tickers = {"Dólar vs Real": "BRL=X", "Euro vs Dólar": "EURUSD=X"}
            currency_data = fetch_market_data(list(currency_tickers.values()))
            if not currency_data.empty:
                currency_data.rename(columns=lambda c: next(k for k, v in currency_tickers.items() if v == c), inplace=True)
                st.plotly_chart(px.line(currency_data, title="Evolução de Câmbio"), use_container_width=True)

    with subtab_risk:
        st.subheader("Medidores de Risco de Mercado")
        vix_data = fetch_market_data(["^VIX"])
        if not vix_data.empty:
            fig = px.area(vix_data, title="Índice de Volatilidade VIX ('Índice do Medo')")
            fig.add_hline(y=20, line_dash="dash", line_color="gray", annotation_text="Nível Normal")
            fig.add_hline(y=30, line_dash="dash", line_color="red", annotation_text="Nível Alto (Estresse)")
            st.plotly_chart(fig, use_container_width=True)
        
    with subtab_valuation:
        st.subheader("Análise de Fatores: Growth vs. Value (EUA)")
        factor_tickers = {"Growth": "VUG", "Value": "VTV"}
        factor_data = fetch_market_data(list(factor_tickers.values()))
        if not factor_data.empty:
            factor_data["Growth / Value Ratio"] = factor_data["VUG"] / factor_data["VTV"]
            fig = px.line(factor_data["Growth / Value Ratio"], title="Ratio de Performance: Growth vs. Value")
            st.plotly_chart(fig, use_container_width=True)
