# pages/3_📊_Portfólios_e_Risco.py (Versão Leve)

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import numpy as np

# --- Configuração da Página ---
st.set_page_config(
    page_title="PAG | Análise de Portfólios",
    page_icon="📊",
    layout="wide"
)

# --- Título e Descrição ---
st.title("Análise de Carteira com Pesos Iguais")
st.markdown("Analise o risco e o retorno de uma carteira diversificada com alocação igual entre os ativos.")

# --- Barra Lateral com Inputs ---
st.sidebar.header("Montagem da Carteira")
tickers_string = st.sidebar.text_area(
    "Insira os Tickers separados por vírgula",
    "AAPL, GOOG, MSFT, NVDA, JPM, V, PFE, JNJ, MGLU3.SA, PETR4.SA",
    help="Use os códigos do Yahoo Finance. Ex: PETR4.SA para Petrobras."
)
run_button = st.sidebar.button("Analisar Carteira")

# --- Funções Auxiliares ---
@st.cache_data
def get_price_data(tickers_list):
    """Baixa os dados de preços de fechamento ajustados."""
    try:
        data = yf.download(tickers_list, start="2020-01-01", end=pd.to_datetime('today').strftime('%Y-%m-%d'))['Adj Close']
        return data.dropna(axis=1, how='all') # Remove colunas que não tiveram dados
    except Exception:
        return pd.DataFrame()

def calculate_portfolio_metrics(prices, weights):
    """Calcula as métricas de um portfólio com base nos pesos."""
    # Retornos diários
    returns = prices.pct_change().dropna()
    
    # Retorno anualizado do portfólio
    portfolio_return = np.sum(returns.mean() * weights) * 252
    
    # Covariância e Volatilidade Anualizada
    cov_matrix = returns.cov() * 252
    portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    
    # Índice de Sharpe (assumindo taxa livre de risco de 0)
    sharpe_ratio = portfolio_return / portfolio_volatility
    
    # VaR Histórico (95%)
    # Z-score para 95% de confiança é 1.645
    z_score = 1.645
    # VaR diário
    daily_var = portfolio_volatility / np.sqrt(252) * z_score
    
    return portfolio_return, portfolio_volatility, sharpe_ratio, daily_var

# --- Lógica Principal ---
if run_button:
    tickers = [ticker.strip().upper() for ticker in tickers_string.split(",")]
    if not tickers or tickers == ['']:
        st.warning("Por favor, insira pelo menos um ticker.")
    else:
        with st.spinner("Buscando dados e analisando a carteira..."):
            prices = get_price_data(tickers)
            
            if prices.empty:
                st.error("Não foi possível obter dados para os tickers fornecidos. Verifique os códigos e o período.")
            else:
                # 1. Definir pesos iguais
                num_assets = len(prices.columns)
                weights = np.full(num_assets, 1/num_assets)
                
                # 2. Calcular as métricas
                p_return, p_vol, p_sharpe, p_var = calculate_portfolio_metrics(prices, weights)

                # --- Exibição dos Resultados ---
                st.header("Análise da Carteira (Pesos Iguais)")
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Retorno Anual Estimado", f"{p_return*100:.2f}%")
                col2.metric("Volatilidade Anual", f"{p_vol*100:.2f}%")
                col3.metric("Índice de Sharpe", f"{p_sharpe:.2f}")
                col4.metric("VaR (95%, 1 dia)", f"{p_var*100:.2f}%", 
                           help="Com 95% de confiança, a perda máxima em 1 dia não deve exceder este percentual.")

                # Gráfico de alocação
                weights_df = pd.DataFrame({'Ativo': prices.columns, 'Peso': weights})
                fig = px.pie(weights_df, names='Ativo', values='Peso', title='Alocação de Ativos (Pesos Iguais)')
                st.plotly_chart(fig, use_container_width=True)
                
                # Gráfico de performance histórica
                st.subheader("Performance Histórica da Carteira")
                returns = prices.pct_change().dropna()
                portfolio_cumulative_returns = (1 + (returns * weights).sum(axis=1)).cumprod() - 1
                
                fig_perf = px.line(portfolio_cumulative_returns, title="Retorno Acumulado da Carteira")
                fig_perf.update_layout(yaxis_title="Retorno Acumulado", xaxis_title="Data", showlegend=False)
                st.plotly_chart(fig_perf, use_container_width=True)

else:
    st.info("Insira os tickers dos ativos na barra lateral para analisar a carteira.")
