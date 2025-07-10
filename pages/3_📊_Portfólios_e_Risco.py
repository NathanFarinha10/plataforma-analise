# pages/3_📊_Portfólios_e_Risco.py

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from pypfopt import EfficientFrontier, risk_models, expected_returns
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices
from scipy.stats import norm
import numpy as np

# --- Configuração da Página ---
st.set_page_config(
    page_title="PAG | Otimizador de Portfólios",
    page_icon="📊",
    layout="wide"
)

# --- Título e Descrição ---
st.title("Otimizador de Portfólios e Análise de Risco")
st.markdown("Crie e otimize uma carteira de investimentos com base na Teoria Moderna de Portfólios.")

# --- Barra Lateral com Inputs ---
st.sidebar.header("Montagem da Carteira")

tickers_string = st.sidebar.text_area(
    "Insira os Tickers separados por vírgula",
    "AAPL, GOOG, MSFT, NVDA, JPM, V, PFE, JNJ, MGLU3.SA, PETR4.SA",
    help="Use os códigos do Yahoo Finance. Ex: PETR4.SA para Petrobras."
)

optimize_button = st.sidebar.button("Otimizar Carteira")


# --- Funções Auxiliares ---
@st.cache_data
def get_price_data(tickers_list):
    """Baixa os dados de preços de fechamento ajustados para uma lista de tickers."""
    return yf.download(tickers_list, start="2020-01-01", end=pd.to_datetime('today').strftime('%Y-%m-%d'))['Adj Close']

def calculate_var(weights, S, confidence_level=0.95):
    """Calcula o Value at Risk (VaR) histórico do portfólio."""
    portfolio_std_dev = np.sqrt(weights.T @ S @ weights)
    # Usamos a distribuição normal para encontrar o Z-score
    z_score = norm.ppf(confidence_level)
    var = z_score * portfolio_std_dev
    return var

# --- Lógica Principal ---
if optimize_button:
    tickers = [ticker.strip().upper() for ticker in tickers_string.split(",")]
    if not tickers or tickers == ['']:
        st.warning("Por favor, insira pelo menos um ticker.")
    else:
        try:
            with st.spinner("Buscando dados e otimizando a carteira..."):
                # 1. Baixar os dados
                prices = get_price_data(tickers)
                if prices.empty or prices.isnull().all().all():
                    st.error("Não foi possível obter dados para os tickers fornecidos. Verifique os códigos.")
                else:
                    # Remove tickers que não retornaram dados (colunas só com NaN)
                    prices = prices.dropna(axis=1, how='all')
                    
                    # 2. Calcular retornos esperados e matriz de covariância
                    mu = expected_returns.mean_historical_return(prices)
                    S = risk_models.sample_cov(prices)

                    # 3. Otimizar para máximo Índice de Sharpe
                    ef = EfficientFrontier(mu, S)
                    weights = ef.max_sharpe()
                    cleaned_weights = ef.clean_weights()
                    
                    # 4. Obter performance da carteira
                    expected_return, annual_volatility, sharpe_ratio = ef.portfolio_performance(verbose=False)

                    # 5. Calcular o VaR
                    # Precisamos converter os pesos de um dicionário para um array na ordem correta
                    weight_array = np.array([cleaned_weights.get(ticker, 0) for ticker in S.columns])
                    var_95 = calculate_var(weight_array, S.values)

                    # --- Exibição dos Resultados ---
                    st.header("Carteira Otimizada (Máximo Índice de Sharpe)")

                    # Métricas da carteira
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Retorno Anual Esperado", f"{expected_return*100:.2f}%")
                    col2.metric("Volatilidade Anual", f"{annual_volatility*100:.2f}%")
                    col3.metric("Índice de Sharpe", f"{sharpe_ratio:.2f}")
                    col4.metric("VaR Histórico (95%, 1 dia)", f"{var_95*100:.2f}%", 
                               help="Com 95% de confiança, a perda máxima em 1 dia não deve exceder este percentual.")

                    # Gráfico de alocação
                    weights_df = pd.DataFrame(list(cleaned_weights.items()), columns=['Ativo', 'Peso'])
                    weights_df = weights_df[weights_df['Peso'] > 0] # Mostrar apenas ativos com alocação

                    fig = px.pie(weights_df, names='Ativo', values='Peso', title='Alocação de Ativos Recomendada')
                    st.plotly_chart(fig, use_container_width=True)

                    # Tabela com pesos
                    st.subheader("Pesos Detalhados")
                    weights_df['Peso %'] = (weights_df['Peso'] * 100).map('{:.2f}%'.format)
                    st.dataframe(weights_df[['Ativo', 'Peso %']], use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Ocorreu um erro durante a otimização: {e}")
            st.info("Dicas: Verifique se todos os tickers são válidos e se possuem histórico de preços suficiente.")

else:
    st.info("Insira os tickers dos ativos na barra lateral para montar e otimizar sua carteira.")
