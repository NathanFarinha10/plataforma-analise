# pages/7_💼_Wealth_Management.py (Versão 5.2.2 - Final com todas as funções)

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import yfinance as yf
import numpy as np
import time

# --- Configuração da Página ---
st.set_page_config(page_title="Wealth Management - Alocação", page_icon="💼", layout="wide")

st.sidebar.image("logo.png", use_container_width=True)

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
if 'client_profile' not in st.session_state: st.session_state.client_profile = "Balanceado"
if 'backtest_results' not in st.session_state: st.session_state.backtest_results = None
if 'last_backtested_portfolio' not in st.session_state: st.session_state.last_backtested_portfolio = pd.DataFrame()

# --- DADOS: ALOCAÇÃO ESTRATÉGICA E BUILDING BLOCKS ---
portfolio_data = {
    "Conservador": {"Caixa": 20, "Renda Fixa Brasil": 50, "Renda Fixa Internacional": 15, "Ações Brasil": 5, "Ações Internacional": 5, "Fundos Imobiliários": 5, "Alternativos": 0},
    "Moderado": {"Caixa": 10, "Renda Fixa Brasil": 40, "Renda Fixa Internacional": 15, "Ações Brasil": 15, "Ações Internacional": 15, "Fundos Imobiliários": 5, "Alternativos": 0},
    "Balanceado": {"Caixa": 5, "Renda Fixa Brasil": 30, "Renda Fixa Internacional": 20, "Ações Brasil": 20, "Ações Internacional": 20, "Fundos Imobiliários": 5, "Alternativos": 0},
    "Crescimento": {"Caixa": 5, "Renda Fixa Brasil": 20, "Renda Fixa Internacional": 15, "Ações Brasil": 25, "Ações Internacional": 25, "Fundos Imobiliários": 5, "Alternativos": 5},
    "Agressivo": {"Caixa": 2, "Renda Fixa Brasil": 10, "Renda Fixa Internacional": 10, "Ações Brasil": 34, "Ações Internacional": 34, "Fundos Imobiliários": 5, "Alternativos": 5}
}
portfolio_list = list(portfolio_data.keys())
building_blocks_data = {
    "Caixa": [{"ticker": "Tesouro Selic (LFT)", "name": "Título Público Pós-Fixado", "rationale": "Principal ativo para reserva de emergência."}],
    "Renda Fixa Brasil": [{"ticker": "IMAB11.SA", "name": "iShares IMA-B Fundo de Índice", "rationale": "Exposição a títulos públicos atrelados à inflação."}],
    "Renda Fixa Internacional": [{"ticker": "BNDW", "name": "Vanguard Total World Bond ETF", "rationale": "ETF globalmente diversificado em títulos de alta qualidade."}],
    "Ações Brasil": [{"ticker": "BOVA11.SA", "name": "iShares Ibovespa Fundo de Índice", "rationale": "Exposição ampla ao principal índice de ações brasileiro."}],
    "Ações Internacional": [{"ticker": "IVV", "name": "iShares Core S&P 500 ETF", "rationale": "Exposição às 500 maiores empresas dos EUA."}],
    "Fundos Imobiliários": [{"ticker": "HGLG11.SA", "name": "CSHG Logística FII", "rationale": "Exemplo de FII de 'tijolo' de alta qualidade."}],
    "Alternativos": [{"ticker": "GOLD11.SA", "name": "Trend Ouro Fundo de Índice", "rationale": "Exposição ao Ouro como reserva de valor."}]
}

# --- FUNÇÕES AUXILIARES ---
def create_allocation_chart(portfolio_name, data):
    df = pd.DataFrame(list(data.items()), columns=['Classe de Ativo', 'Alocação (%)'])
    fig = px.pie(df, values='Alocação (%)', names='Classe de Ativo', title=f"<b>{portfolio_name}</b>", hole=.3, color_discrete_sequence=px.colors.sequential.GnBu_r)
    fig.update_traces(textposition='inside', textinfo='percent+label', insidetextfont=dict(size=14)); fig.update_layout(showlegend=False, title_font_size=20, title_x=0.5, margin=dict(l=20,r=20,t=40,b=20)); return fig

def get_asset_class(info, ticker_symbol):
    category = info.get('quoteType', '').upper(); long_name = info.get('longName', '').upper()
    if category == 'EQUITY': return "Ações Brasil" if '.SA' in ticker_symbol.upper() else "Ações Internacional"
    if category == 'ETF':
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
        except Exception: categories[ticker] = "Não Classificado"
    return categories

@st.cache_data
def get_portfolio_price_data(tickers_list, period="3y"):
    return yf.download(tickers_list, period=period, progress=False)['Close'].dropna()

def calculate_portfolio_risk(prices, weights):
    if prices.empty or len(prices) < 252: return 0, 0, 0, pd.Series(dtype='float64', index=prices.columns)
    returns = prices.pct_change().dropna(); cov_matrix = returns.cov() * 252
    p_return = np.sum(returns.mean() * weights) * 252
    p_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    p_sharpe = p_return / p_vol if p_vol > 0 else 0
    marginal_contribution = weights * (cov_matrix @ weights) / p_vol
    risk_contribution_pct = marginal_contribution / p_vol
    return p_return, p_vol, p_sharpe, risk_contribution_pct

@st.cache_data
def calculate_factor_betas(portfolio_tickers, period="3y"):
    factor_tickers = {"S&P 500": "^GSPC", "Ibovespa": "^BVSP", "Juros EUA (IEF)": "IEF", "Dólar": "BRL=X"}
    all_tickers = list(set(portfolio_tickers + list(factor_tickers.values())))
    prices = get_portfolio_price_data(all_tickers, period)
    returns = prices.pct_change().dropna()
    betas = pd.DataFrame()
    for asset in portfolio_tickers:
        for factor_name, factor_ticker in factor_tickers.items():
            if asset in returns.columns and factor_ticker in returns.columns:
                # polyfit(x, y, grau) -> retorna [beta, alpha]
                beta = np.polyfit(returns[factor_ticker], returns[asset], 1)[0]
                betas.loc[asset, factor_name] = beta
    return betas

@st.cache_data(ttl=86400)
def run_backtest(portfolio_df, period="3y"):
    tickers = portfolio_df['ticker'].tolist()
    weights = portfolio_df['weight'].values
    weights = weights / weights.sum()
    try:
        prices = get_portfolio_price_data(tickers, period)
        if prices.empty: return None
        annualized_return, annualized_vol, sharpe_ratio, risk_contribution = calculate_portfolio_risk(prices, weights)
        portfolio_daily_returns = (prices.pct_change().dropna() * weights).sum(axis=1)
        cumulative_returns = (1 + portfolio_daily_returns).cumprod()
        total_return = cumulative_returns.iloc[-1] - 1
        risk_contribution.index = tickers
        return {"cumulative_returns": cumulative_returns, "total_return": total_return, "annualized_return": annualized_return, "annualized_vol": annualized_vol, "sharpe_ratio": sharpe_ratio, "risk_contribution": risk_contribution}
    except Exception as e:
        st.error(f"Erro no backtest: {e}"); return None

# --- UI DA APLICAÇÃO ---
st.title("💼 Painel de Wealth Management e Alocação Estratégica")
st.markdown("Visão geral dos Portfólios Modelo e ferramentas de análise para assessores.")
st.divider()

with st.expander("Definir Perfil de Risco do Cliente (Suitability)"):
    q1_options = {"Longo Prazo (acima de 5 anos)": 30, "Médio Prazo (2 a 5 anos)": 20, "Curto Prazo (até 2 anos)": 10}
    q1 = st.radio("1. Por quanto tempo você pretende manter seus investimentos aplicados?", list(q1_options.keys()), key="q1")
    q2_options = {"Compraria mais, aproveitando os preços baixos": 40, "Manteria minha posição": 20, "Venderia toda a minha posição": 10}
    q2 = st.radio("2. Imagine uma queda de 20% no mercado. Qual seria sua reação?", list(q2_options.keys()), key="q2")
    q3_options = {"Aumentar meu patrimônio de forma significativa": 30, "Gerar uma renda complementar": 20, "Preservar meu capital com o menor risco possível": 10}
    q3 = st.radio("3. Qual é o seu principal objetivo?", list(q3_options.keys()), key="q3")
    if st.button("Calcular Perfil de Risco"):
        total_score = q1_options[q1] + q2_options[q2] + q3_options[q3]
        if total_score <= 40: profile_name = "Conservador"
        elif total_score <= 60: profile_name = "Moderado"
        elif total_score <= 75: profile_name = "Balanceado"
        elif total_score <= 90: profile_name = "Crescimento"
        else: profile_name = "Agressivo"
        st.session_state.client_profile = profile_name
        st.success(f"### Perfil de Risco Calculado: **{profile_name}**")
st.divider()

st.subheader("Alocação Estratégica de Longo Prazo")
cols = st.columns(len(portfolio_data))
for i, (portfolio_name, data) in enumerate(portfolio_data.items()):
    with cols[i]:
        fig = create_allocation_chart(portfolio_name, data)
        if portfolio_name == st.session_state.client_profile:
            st.markdown(f"**_{portfolio_name}_** ⭐")
        st.plotly_chart(fig, use_container_width=True)
st.divider()

st.subheader("Building Blocks: Ativos Recomendados por Classe")
selected_class = st.selectbox("Escolha a Classe de Ativo:", options=list(building_blocks_data.keys()), key="bb_select")
if selected_class:
    for asset in building_blocks_data.get(selected_class, []):
        c1, c2 = st.columns([1, 4]); c1.metric("Ticker", asset["ticker"])
        with c2: st.markdown(f"**{asset['name']}**"); st.caption(asset['rationale'])
st.divider()

# --- CONSTRUTOR E SIMULADOR DE PORTFÓLIOS ---
st.subheader("🛠️ Construtor e Simulador de Portfólios")
st.markdown("Construa uma carteira, faça ajustes táticos e simule a performance e o risco.")

base_model_name = st.selectbox("1. Selecione um Portfólio Modelo como Base:", options=portfolio_list, index=portfolio_list.index(st.session_state.client_profile))
assets_list = []
for asset_class, weight in portfolio_data[base_model_name].items():
    if weight > 0: assets_list.append({"Classe de Ativo": asset_class, "Ticker": building_blocks_data[asset_class][0]['ticker'], "Peso (%)": weight})
st.markdown("##### 2. Visualize e Customize a Alocação")
edited_portfolio_df = st.data_editor(pd.DataFrame(assets_list), num_rows="dynamic", key="portfolio_editor", column_config={"Peso (%)": st.column_config.NumberColumn(format="%d%%")})

total_weight = edited_portfolio_df['Peso (%)'].sum()
if not np.isclose(total_weight, 100): st.warning(f"A soma dos pesos é de {total_weight:.1f}%. Ajuste para 100%.")

st.markdown("##### 3. Execute a Simulação")
if st.button("Rodar Simulação da Carteira Customizada", disabled=not np.isclose(total_weight, 100)):
    with st.spinner("Executando simulação histórica..."):
        backtest_input_df = edited_portfolio_df.copy().rename(columns={"Ticker": "ticker", "Peso (%)": "weight"})
        backtest_input_df['weight'] /= 100
        backtest_input_df = backtest_input_df[backtest_input_df['ticker'].str.match(r'^[A-Z0-9\.\^=^-]+$')]
        st.session_state.last_backtested_portfolio = backtest_input_df.copy()
        st.session_state.backtest_results = run_backtest(backtest_input_df)

if st.session_state.backtest_results:
    results = st.session_state.backtest_results
    st.subheader("Resultados da Simulação")
    
    st.markdown("###### Performance da Carteira")
    c1,c2,c3,c4 = st.columns(4); c1.metric("Retorno Total",f"{results['total_return']*100:.2f}%"); c2.metric("Retorno Anualizado",f"{results['annualized_return']*100:.2f}%"); c3.metric("Volatilidade Anualizada",f"{results['annualized_vol']*100:.2f}%"); c4.metric("Índice de Sharpe",f"{results['sharpe_ratio']:.2f}")
    fig_perf = px.line(results['cumulative_returns'], title="Performance Histórica Acumulada"); st.plotly_chart(fig_perf, use_container_width=True)

    st.markdown("###### Análise de Risco")
    risk_contrib_df = (results['risk_contribution'] * 100).reset_index().rename(columns={'index': 'Ativo', 0: 'Contribuição ao Risco (%)'})
    fig_risk = px.bar(risk_contrib_df.sort_values('Contribuição ao Risco (%)', ascending=False), x='Ativo', y='Contribuição ao Risco (%)', title='Decomposição do Risco da Carteira', text_auto='.2f', color='Contribuição ao Risco (%)', color_continuous_scale='Reds'); st.plotly_chart(fig_risk, use_container_width=True)
    
    st.divider()
    st.markdown("###### Teste de Estresse (Análise de Cenários)")
    if not st.session_state.last_backtested_portfolio.empty:
        portfolio_to_stress = st.session_state.last_backtested_portfolio
        with st.spinner("Calculando sensibilidades (betas)..."): factor_betas = calculate_factor_betas(portfolio_to_stress['ticker'].tolist())
        
        c1,c2 = st.columns(2)
        sp500_shock = c1.slider("Cenário S&P 500 (%)",-20.0,20.0,0.0,1.0); ief_shock = c1.slider("Cenário Juros EUA (IEF) (%)",-5.0,5.0,0.0,0.5)
        ibov_shock = c2.slider("Cenário Ibovespa (%)",-20.0,20.0,0.0,1.0); dollar_shock = c2.slider("Cenário Dólar (%)",-15.0,15.0,0.0,1.0)
            
        total_impact = 0
        for _, row in portfolio_to_stress.iterrows():
            ticker, weight = row['ticker'], row['weight']
            if ticker in factor_betas.index:
                asset_impact = (factor_betas.loc[ticker, "S&P 500"] * (sp500_shock/100)) + (factor_betas.loc[ticker, "Ibovespa"] * (ibov_shock/100)) + (factor_betas.loc[ticker, "Juros EUA (IEF)"] * (ief_shock/100)) + (factor_betas.loc[ticker, "Dólar"] * (dollar_shock/100))
                total_impact += asset_impact * weight
        st.metric("Impacto Estimado na Carteira", f"{total_impact * 100:.2f}%", delta_color=("inverse" if total_impact < 0 else "normal"))
        with st.expander("Ver Betas Calculados"): st.dataframe(factor_betas.style.format("{:.2f}"))
