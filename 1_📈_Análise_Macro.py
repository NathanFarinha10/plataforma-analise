# 1_📈_Análise_Macro.py (Versão 2.0 com Mercados Globais)

import streamlit as st
import pandas as pd
from fredapi import Fred
from bcb import sgs
import plotly.express as px
from datetime import datetime
import yfinance as yf
import numpy as np

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
    """Busca uma única série do FRED."""
    return fred.get_series(code, start_date)

@st.cache_data(ttl=3600)
def fetch_bcb_series(code, start_date):
    """Busca uma única série do BCB SGS de forma robusta."""
    try:
        # Tenta buscar os dados
        df = sgs.get({str(code): code}, start=start_date)
        
        # Verifica se o dataframe não está vazio e se a coluna esperada existe
        if not df.empty and str(code) in df.columns:
            return df[str(code)] # Retorna a série de dados
        else:
            # Se não encontrar, retorna uma Série vazia para evitar erros
            return pd.Series(dtype='float64')
            
    except Exception:
        # Em caso de qualquer outro erro na API, também retorna uma série vazia
        return pd.Series(dtype='float64')

@st.cache_data(ttl=86400)
def fetch_market_data(tickers, period="5y"):
    """Baixa dados de mercado do Yahoo Finance."""
    return yf.download(tickers, period=period, progress=False)['Close']

def plot_indicator(data, title, y_label="Valor"):
    """Função genérica para plotar um gráfico de área."""
    if data is None or data.empty:
        st.warning(f"Não foi possível carregar os dados para {title}.")
        return
    fig = px.area(data, title=title, labels={"value": y_label, "index": "Data"})
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# --- UI DA APLICAÇÃO ---
st.title("🌍 Painel de Análise Macroeconômica")
start_date = "2010-01-01"

tab_br, tab_us, tab_global = st.tabs(["🇧🇷 Brasil", "🇺🇸 Estados Unidos", "🌐 Mercados Globais"])

# --- ABA BRASIL ---
with tab_br:
    st.header("Principais Indicadores do Brasil")
    subtab_br_activity, subtab_br_inflation = st.tabs(["Atividade e Emprego", "Inflação e Juros"])
    
    with subtab_br_activity:
        st.subheader("Atividade Econômica")
        plot_indicator(fetch_bcb_series(24369, start_date).pct_change(12).dropna() * 100, "IBC-Br (Prévia do PIB, Var. Anual %)", "Variação %")
        plot_indicator(fetch_bcb_series(1473, start_date).pct_change(12).dropna() * 100, "Vendas no Varejo (Var. Anual %)", "Variação %")
        
        st.subheader("Emprego")
        plot_indicator(fetch_bcb_series(24369, start_date), "Taxa de Desemprego (PNADC %)", "% da Força de Trabalho")

    with subtab_br_inflation:
        st.subheader("Inflação")
        plot_indicator(fetch_bcb_series(13522, start_date), "IPCA (Inflação ao Consumidor, Acum. 12M %)", "Variação %")
        
        st.subheader("Taxa de Juros")
        plot_indicator(fetch_bcb_series(432, start_date), "Taxa Selic (Anualizada %)", "Taxa %")

# --- ABA EUA ---
with tab_us:
    st.header("Principais Indicadores dos Estados Unidos")
    subtab_us_activity, subtab_us_inflation, subtab_us_yield = st.tabs(["Atividade e Emprego", "Inflação e Juros", "Curva de Juros"])

    with subtab_us_activity:
        st.subheader("Atividade Econômica")
        plot_indicator(fetch_fred_series("GDPC1", start_date).pct_change(4).dropna() * 100, "PIB Real (Var. Anual %)", "Variação %")
        plot_indicator(fetch_fred_series("INDPRO", start_date).pct_change(12).dropna() * 100, "Produção Industrial (Var. Anual %)", "Variação %")

        st.subheader("Emprego")
        plot_indicator(fetch_fred_series("UNRATE", start_date), "Taxa de Desemprego (%)", "% da Força de Trabalho")

    with subtab_us_inflation:
        st.subheader("Inflação")
        plot_indicator(fetch_fred_series("CPIAUCSL", start_date).pct_change(12).dropna() * 100, "CPI (Inflação ao Consumidor, Var. Anual %)", "Variação %")

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
            fig.update_layout(showlegend=False, yaxis_title="Diferença Percentual")
            st.plotly_chart(fig, use_container_width=True)

# --- ABA MERCADOS GLOBAIS ---
with tab_global:
    st.header("Índices e Indicadores de Mercado Global")
    
    subtab_equity, subtab_commodities, subtab_risk, subtab_valuation = st.tabs(["Índices de Ações", "Commodities & Moedas", "Risco & Volatilidade", "Valuation"])

    with subtab_equity:
        st.subheader("Performance Comparada de Índices de Ações")
        equity_tickers = {
            "S&P 500 (EUA)": "^GSPC", "Ibovespa (Brasil)": "^BVSP", "Nasdaq (EUA Tech)": "^IXIC",
            "DAX (Alemanha)": "^GDAXI", "Nikkei 225 (Japão)": "^N225", "FTSE 100 (Reino Unido)": "^FTSE"
        }
        selected_indices = st.multiselect("Selecione os índices para comparar:", options=list(equity_tickers.keys()), default=["S&P 500 (EUA)", "Ibovespa (Brasil)", "Nasdaq (EUA Tech)"])
        
        if selected_indices:
            tickers_to_fetch = [equity_tickers[i] for i in selected_indices]
            market_data = fetch_market_data(tickers_to_fetch)
            if not market_data.empty:
                normalized_data = (market_data / market_data.dropna().iloc[0]) * 100
                fig = px.line(normalized_data, title="Performance Normalizada (Base 100)")
                fig.update_layout(yaxis_title="Performance (Base 100)", xaxis_title="Data", legend_title="Índice")
                st.plotly_chart(fig, use_container_width=True)

    with subtab_commodities:
        st.subheader("Preços de Commodities e Taxas de Câmbio")
        col1, col2 = st.columns(2)
        with col1:
            commodity_tickers = {"Petróleo WTI": "CL=F", "Ouro": "GC=F", "Cobre": "HG=F"}
            commodity_data = fetch_market_data(list(commodity_tickers.values()))
            if not commodity_data.empty:
                commodity_data.rename(columns=lambda c: next(k for k, v in commodity_tickers.items() if v == c), inplace=True)
                st.plotly_chart(px.line(commodity_data, title="Evolução de Commodities"), use_container_width=True)
        with col2:
            currency_tickers = {"Dólar vs Real": "BRL=X", "Euro vs Dólar": "EURUSD=X", "Dólar vs Iene": "JPY=X"}
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
            fig.update_layout(showlegend=False, yaxis_title="Pontos do Índice")
            st.plotly_chart(fig, use_container_width=True)
        
        btc_data = fetch_market_data(["BTC-USD"])
        if not btc_data.empty:
            st.plotly_chart(px.line(btc_data, title="Preço do Bitcoin (USD) - Proxy de Apetite a Risco"), use_container_width=True)

    # SUBSTITUA TODO O CONTEÚDO DENTRO DE 'with subtab_valuation:' POR ISTO

    # SUBSTITUA TODO O CONTEÚDO DENTRO DE 'with subtab_valuation:' POR ISTO

    with subtab_valuation:
        st.subheader("Prêmio de Risco do Equity (Equity Risk Premium - ERP)")
        st.caption("Compara o retorno implícito da bolsa (Earnings Yield do Shiller P/E) com o retorno de um título do governo (10-Year Treasury Yield). Um prêmio alto (diferença grande entre as linhas) sugere que as ações estão atrativas em relação à renda fixa.")
        
        # Códigos nativos e confiáveis do FRED
        shiller_pe_code = "SHILLER_PE_RATIO_MONTH"
        treasury_10y_code = "DGS10"
        
        # Busca os dados
        shiller_pe_ratio = fetch_fred_series(shiller_pe_code, start_date)
        treasury_yield = fetch_fred_series(treasury_10y_code, start_date)
        
        if not shiller_pe_ratio.empty and not treasury_yield.empty:
            # Calcula o Earnings Yield (inverso do P/E)
            earnings_yield = (1 / shiller_pe_ratio) * 100
            
            # Monta o DataFrame para o gráfico
            df_erp = pd.DataFrame({
                "Earnings Yield (Bolsa)": earnings_yield,
                "Juro de 10 Anos (Renda Fixa)": treasury_yield
            }).dropna()

            fig = px.line(df_erp, title="Earnings Yield (Shiller PE) vs. Juro de 10 Anos (EUA)")
            fig.update_layout(yaxis_title="Taxa Anual (%)", xaxis_title="Data", legend_title="Indicador")
            st.plotly_chart(fig, use_container_width=True)

            # Gráfico do Prêmio de Risco (a diferença entre os dois)
            df_erp["Prêmio de Risco (ERP)"] = df_erp["Earnings Yield (Bolsa)"] - df_erp["Juro de 10 Anos (Renda Fixa)"]
            fig_premium = px.area(df_erp["Prêmio de Risco (ERP)"], title="Prêmio de Risco Histórico (ERP)")
            fig_premium.add_hline(y=df_erp["Prêmio de Risco (ERP)"].mean(), line_dash="dash", line_color="red", annotation_text="Média Histórica")
            fig_premium.update_layout(showlegend=False, yaxis_title="Prêmio Percentual (%)")
            st.plotly_chart(fig_premium, use_container_width=True)
            
        else:
            st.warning("Não foi possível carregar os dados para a análise de Valuation.")
