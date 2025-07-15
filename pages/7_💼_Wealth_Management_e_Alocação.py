# pages/7_💼_Wealth_Management.py (Versão 3.1 - Final com todas as correções)

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import yfinance as yf # <-- IMPORTAÇÃO QUE FALTAVA
import numpy as np
import time

# --- Configuração da Página ---
st.set_page_config(page_title="Wealth Management - Alocação", page_icon="💼", layout="wide")

# --- DADOS: ALOCAÇÃO ESTRATÉGICA E BUILDING BLOCKS ---
portfolio_data = {
    "Conservador": {"Caixa": 20, "Renda Fixa Brasil": 50, "Renda Fixa Internacional": 15, "Ações Brasil": 5, "Ações Internacional": 5, "Fundos Imobiliários": 5, "Alternativos": 0},
    "Moderado": {"Caixa": 10, "Renda Fixa Brasil": 40, "Renda Fixa Internacional": 15, "Ações Brasil": 15, "Ações Internacional": 15, "Fundos Imobiliários": 5, "Alternativos": 0},
    "Balanceado": {"Caixa": 5, "Renda Fixa Brasil": 30, "Renda Fixa Internacional": 20, "Ações Brasil": 20, "Ações Internacional": 20, "Fundos Imobiliários": 5, "Alternativos": 0},
    "Crescimento": {"Caixa": 5, "Renda Fixa Brasil": 20, "Renda Fixa Internacional": 15, "Ações Brasil": 25, "Ações Internacional": 25, "Fundos Imobiliários": 5, "Alternativos": 5},
    "Agressivo": {"Caixa": 2, "Renda Fixa Brasil": 10, "Renda Fixa Internacional": 10, "Ações Brasil": 34, "Ações Internacional": 34, "Fundos Imobiliários": 5, "Alternativos": 5}
}
building_blocks_data = {
    "Caixa": [{"ticker": "Tesouro Selic (LFT)", "name": "Título Público Pós-Fixado", "rationale": "Principal ativo para reserva de emergência e posições de caixa."}],
    "Renda Fixa Brasil": [{"ticker": "IMAB11.SA", "name": "iShares IMA-B Fundo de Índice", "rationale": "Exposição a títulos públicos atrelados à inflação (NTN-Bs)."}],
    "Renda Fixa Internacional": [{"ticker": "BNDW", "name": "Vanguard Total World Bond ETF", "rationale": "ETF globalmente diversificado em títulos de alta qualidade de crédito."}],
    "Ações Brasil": [{"ticker": "BOVA11.SA", "name": "iShares Ibovespa Fundo de Índice", "rationale": "Exposição ampla ao principal índice de ações brasileiro."}],
    "Ações Internacional": [{"ticker": "IVV", "name": "iShares Core S&P 500 ETF", "rationale": "Exposição às 500 maiores empresas dos EUA."}],
    "Fundos Imobiliários": [{"ticker": "IFIX", "name": "Índice de Fundos de Investimentos Imobiliários", "rationale": "Referência do setor. Buscar FIIs diversificados."}],
    "Alternativos": [{"ticker": "GOLD11.SA", "name": "Trend Ouro Fundo de Índice", "rationale": "Exposição ao Ouro como reserva de valor."}]
}

# --- FUNÇÕES AUXILIARES ---
def create_allocation_chart(portfolio_name, data):
    df = pd.DataFrame(list(data.items()), columns=['Classe de Ativo', 'Alocação (%)'])
    fig = px.pie(df, values='Alocação (%)', names='Classe de Ativo', title=f"<b>{portfolio_name}</b>", hole=.3, color_discrete_sequence=px.colors.sequential.GnBu_r)
    fig.update_traces(textposition='inside', textinfo='percent+label', insidetextfont=dict(size=14))
    fig.update_layout(showlegend=False, title_font_size=20, title_x=0.5, margin=dict(l=20, r=20, t=40, b=20))
    return fig

def get_asset_class(info, ticker_symbol):
    category = info.get('quoteType', '').upper()
    if category == 'EQUITY': return "Ações Brasil" if '.SA' in ticker_symbol.upper() else "Ações Internacional"
    if category == 'ETF':
        long_name = info.get('longName', '').upper()
        if any(term in long_name for term in ['FIXA', 'BOND', 'TREASURY']): return "Renda Fixa Internacional" if '.SA' not in ticker_symbol.upper() else "Renda Fixa Brasil"
        if any(term in long_name for term in ['FII', 'IMOBILIÁRIO', 'REAL ESTATE']): return "Fundos Imobiliários"
        if any(term in long_name for term in ['GOLD', 'OURO', 'COMMODITIES']): return "Alternativos"
        if any(term in long_name for term in ['IBOVESPA', 'SMALL', 'BRAZIL']): return "Ações Brasil"
        return "Ações Internacional"
    return "Alternativos"

@st.cache_data
def bulk_categorize_tickers(tickers_list):
    categories = {}
    for ticker in tickers_list:
        try:
            info = yf.Ticker(ticker).info
            if not info or 'quoteType' not in info: raise ValueError("Dados insuficientes.")
            categories[ticker] = get_asset_class(info, ticker)
            time.sleep(0.1)
        except Exception:
            categories[ticker] = "Não Classificado"
    return categories

@st.cache_data
def get_portfolio_price_data(tickers_list, period="3y"):
    return yf.download(tickers_list, period=period, progress=False)['Close'].dropna()

def calculate_portfolio_risk(prices, weights):
    if prices.empty or len(prices) < 252: return 0, 0, 0
    returns = prices.pct_change().dropna()
    p_return = np.sum(returns.mean() * weights) * 252
    p_vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
    p_sharpe = p_return / p_vol if p_vol > 0 else 0
    return p_return, p_vol, p_sharpe

# --- INTERFACE DA APLICAÇÃO ---
st.title("💼 Painel de Wealth Management e Alocação Estratégica")
st.markdown("Visão geral dos Portfólios Modelo e ferramentas de análise para assessores.")
st.divider()

# --- Visão Tática e Portfólios Modelo ---
with st.expander("Visão Tática do Comitê de Investimentos", expanded=True):
    st.info("OVERWEIGHT: Ações Internacionais | NEUTRO: Ações Brasil, FIIs | UNDERWEIGHT: Renda Fixa Pré-Fixada.")
    st.caption(f"Última atualização: {datetime.now().strftime('%d/%m/%Y')}")
st.subheader("Alocação Estratégica de Longo Prazo")
cols = st.columns(len(portfolio_data))
for i, (portfolio_name, data) in enumerate(portfolio_data.items()):
    with cols[i]:
        st.plotly_chart(create_allocation_chart(portfolio_name, data), use_container_width=True)
st.divider()

# --- Seção de Building Blocks ---
st.subheader("Building Blocks: Ativos Recomendados por Classe")
selected_class = st.selectbox("Escolha a Classe de Ativo:", options=list(building_blocks_data.keys()))
if selected_class:
    st.markdown(f"#### Ativos para a classe: **{selected_class}**")
    for asset in building_blocks_data.get(selected_class, []):
        col1, col2 = st.columns([1, 4])
        with col1: st.metric("Ticker", asset["ticker"])
        with col2:
            st.markdown(f"**{asset['name']}**"); st.caption(asset['rationale'])
            if ".SA" in asset['ticker'] or all(c.isalpha() for c in asset['ticker']):
                st.link_button("Ver no Yahoo Finance", f"https://finance.yahoo.com/quote/{asset['ticker']}")
        st.divider()

# --- Analisador de Carteira do Cliente ---
st.subheader("Analisador de Carteira do Cliente")
col_input1, col_input2 = st.columns([2, 1])
with col_input1:
    portfolio_input = st.text_area("Insira a carteira (um ativo por linha, formato: TICKER,VALOR)", "IVV,50000\nBOVA11.SA,30000\nBNDW,20000\nHGLG11.SA,10000", height=150)
with col_input2:
    model_to_compare = st.selectbox("Selecione o Portfólio Modelo para Comparação:", options=list(portfolio_data.keys()))
    analyze_client_button = st.button("Analisar Carteira do Cliente", use_container_width=True)

if analyze_client_button and portfolio_input.strip():
    try:
        with st.spinner("Analisando carteira do cliente..."):
            lines = [line.strip() for line in portfolio_input.strip().split('\n')]
            portfolio_list = [{'ticker': line.split(',')[0].strip().upper(), 'value': float(line.split(',')[1])} for line in lines]
            
            client_df = pd.DataFrame(portfolio_list)
            total_value = client_df['value'].sum()
            client_df['weight'] = client_df['value'] / total_value
            
            category_map = bulk_categorize_tickers(tuple(client_df['ticker'].unique()))
            client_df['asset_class'] = client_df['ticker'].map(category_map)
            client_allocation = client_df.groupby('asset_class')['weight'].sum() * 100
            
            tickers = client_df['ticker'].tolist(); weights = client_df['weight'].values
            price_data = get_portfolio_price_data(tickers)
            p_return, p_vol, p_sharpe = calculate_portfolio_risk(price_data, weights)
            
            st.markdown("##### Análise da Alocação")
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1: st.plotly_chart(create_allocation_chart("Alocação Atual do Cliente", client_allocation), use_container_width=True)
            with col_chart2: st.plotly_chart(create_allocation_chart(f"Modelo {model_to_compare}", portfolio_data[model_to_compare]), use_container_width=True)
            
            st.markdown("##### Métricas de Risco da Carteira do Cliente")
            risk1, risk2, risk3 = st.columns(3)
            risk1.metric("Retorno Anualizado", f"{p_return*100:.2f}%")
            risk2.metric("Volatilidade Anualizada", f"{p_vol*100:.2f}%")
            risk3.metric("Índice de Sharpe", f"{p_sharpe:.2f}")

    except Exception as e:
        st.error(f"Ocorreu um erro ao analisar a carteira. Verifique o formato dos dados. Erro: {e}")
