# pages/5_🔎_Análise_de_ETFs.py

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# --- Configuração da Página ---
st.set_page_config(page_title="Analisador de ETFs", page_icon="🔎", layout="wide")

# --- FUNÇÕES AUXILIARES ---

@st.cache_data
def get_etf_data(ticker_symbol):
    """
    Busca os dados principais de um ETF e os armazena em cache.
    """
    try:
        etf = yf.Ticker(ticker_symbol)
        info = etf.info
        
        # Uma verificação simples para ver se é um ETF válido
        if 'fundFamily' not in info:
            return {"error": f"O ticker '{ticker_symbol}' não parece ser um ETF válido ou não possui dados."}

        hist = etf.history(period="5y")
        
        return {
            "info": info,
            "history": hist
        }
    except Exception as e:
        return {"error": f"Ocorreu um erro ao buscar dados para {ticker_symbol}: {e}"}

def calculate_cumulative_returns(history_df):
    """
    Calcula os retornos acumulados para diferentes períodos.
    """
    returns = {}
    if history_df.empty:
        return returns

    for period_days, period_name in [(365, "1 Ano"), (3*365, "3 Anos"), (5*365, "5 Anos")]:
        if len(history_df) > period_days:
            cumulative_return = (history_df['Close'].iloc[-1] / history_df['Close'].iloc[-period_days]) - 1
            returns[period_name] = cumulative_return * 100
    
    # Retorno total do período disponível
    total_return = (history_df['Close'].iloc[-1] / history_df['Close'].iloc[0]) - 1
    returns["Total (5A máx)"] = total_return * 100
    
    return returns

@st.cache_data
def get_benchmark_data(ticker_symbol):
    """
    Busca dados de um benchmark para comparação.
    """
    is_br = '.SA' in ticker_symbol.upper()
    benchmark_ticker = "^BVSP" if is_br else "^GSPC" # Ibovespa para BR, S&P 500 para outros
    
    try:
        benchmark = yf.Ticker(benchmark_ticker)
        hist = benchmark.history(period="5y")
        return hist, benchmark_ticker
    except Exception:
        return pd.DataFrame(), benchmark_ticker


# --- INTERFACE DA APLICAÇÃO ---

st.title("🔎 Analisador de ETFs")
st.markdown("Insira o ticker de um ETF para visualizar suas informações, performance e comparação com o mercado.")

# --- Painel de Input ---
ticker_input = st.text_input("Digite o Ticker do ETF (ex: IVV, BOVA11.SA, QQQ)", "IVV").upper()
analyze_button = st.button("Analisar ETF")

if analyze_button:
    if not ticker_input:
        st.warning("Por favor, insira um ticker para analisar.")
    else:
        with st.spinner(f"Buscando dados para {ticker_input}..."):
            etf_data = get_etf_data(ticker_input)

        if "error" in etf_data:
            st.error(etf_data["error"])
        else:
            info = etf_data["info"]
            history = etf_data["history"]

            st.header(f"Análise de: {info.get('longName', ticker_input)}")
            
            # --- Painel de Informações Gerais ---
            st.subheader("Informações Gerais")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Gestora (Família)", info.get('fundFamily', 'N/A'))
                st.metric("Preço Atual", f"{info.get('regularMarketPrice', 0):.2f} {info.get('currency', '')}")
            with col2:
                aum = info.get('totalAssets', 0)
                st.metric("Patrimônio (AUM)", f"${aum/1_000_000_000:.2f} Bilhões" if aum > 0 else "N/A")
                st.metric("Volume Médio", f"{info.get('averageDailyVolume10Day', 0):,}")
            with col3:
                ter = info.get('annualReportExpenseRatio', 0)
                st.metric("Taxa de Adm. (TER)", f"{ter*100:.3f}%" if ter > 0 else "N/A")
                st.metric("Beta", f"{info.get('beta3Year', 0):.2f}")

            with st.expander("Resumo da Estratégia do Fundo"):
                st.write(info.get('longBusinessSummary', 'Descrição não disponível.'))
            
            st.divider()

            # --- Análise de Performance ---
            st.subheader("Performance Histórica")
            
            # Gráfico de Preços
            fig_price = px.line(history, y="Close", title=f"Evolução do Preço de Fechamento - {ticker_input}")
            st.plotly_chart(fig_price, use_container_width=True)
            
            # Tabela de Retornos
            returns = calculate_cumulative_returns(history)
            if returns:
                st.markdown("##### Retornos Acumulados")
                df_returns = pd.DataFrame(list(returns.items()), columns=['Período', 'Retorno (%)'])
                st.dataframe(df_returns.style.format({'Retorno (%)': '{:.2f}%'}), use_container_width=True)
            
            st.divider()

            # --- Comparação com Benchmark ---
            st.subheader("Comparação com o Mercado")
            with st.spinner("Buscando dados do benchmark..."):
                benchmark_hist, benchmark_ticker = get_benchmark_data(ticker_input)
            
            if not benchmark_hist.empty:
                # Normaliza os preços para base 100
                comparison_df = pd.DataFrame({
                    ticker_input: history['Close'],
                    benchmark_ticker: benchmark_hist['Close']
                }).dropna()
                
                normalized_df = (comparison_df / comparison_df.iloc[0]) * 100
                
                fig_comparison = px.line(normalized_df, title=f"Performance Comparada (Base 100) - {ticker_input} vs. {benchmark_ticker}")
                st.plotly_chart(fig_comparison, use_container_width=True)
            else:
                st.warning("Não foi possível carregar os dados do benchmark para comparação.")

            st.divider()

            # --- Seção de Composição ---
            st.subheader("Composição do ETF (Principais Ativos)")
            st.info("A composição detalhada de ETFs não está disponível via API gratuita.")
            
            # Link direto para a página de holdings do Yahoo Finance
            yahoo_finance_link = f"https://finance.yahoo.com/quote/{ticker_input}/holdings"
            st.markdown(f"Para visualizar a lista completa e atualizada dos ativos que compõem este ETF, clique no link abaixo:")
            st.link_button(f"Ver Composição de {ticker_input} no Yahoo Finance", yahoo_finance_link)
