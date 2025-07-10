# pages/2_🏢_Research_Empresas.py (Versão com Análise Comparativa)

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import numpy as np
from alpha_vantage.fundamentaldata import FundamentalData

# --- Configuração da Página ---
st.set_page_config(
    page_title="PAG | Research de Empresas",
    page_icon="🏢",
    layout="wide"
)

# --- Funções Auxiliares ---
def analisar_sentimento(texto):
    # (código da função de sentimento permanece o mesmo)
    texto = texto.lower()
    palavras_positivas = ['crescimento', 'lucro', 'aumento', 'supera', 'expansão', 'forte', 'otimista', 'sucesso', 'melhora', 'compra',
                          'growth', 'profit', 'increase', 'beats', 'expansion', 'strong', 'optimistic', 'success', 'improves', 'buy', 'upgrade']
    palavras_negativas = ['queda', 'prejuízo', 'redução', 'abaixo', 'contração', 'fraco', 'pessimista', 'falha', 'piora', 'venda',
                          'fall', 'loss', 'reduction', 'below', 'contraction', 'weak', 'pessimistic', 'fails', 'worsens', 'sell', 'downgrade']
    score = 0
    for palavra in palavras_positivas:
        if palavra in texto:
            score += 1
    for palavra in palavras_negativas:
        if palavra in texto:
            score -= 1
    if score > 0:
        return 'Positivo', '🟢'
    elif score < 0:
        return 'Negativo', '🔴'
    else:
        return 'Neutro', '⚪️'

@st.cache_data
def get_key_stats(tickers):
    """Busca um conjunto de métricas fundamentalistas para uma lista de tickers."""
    key_stats = []
    for ticker_symbol in tickers:
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            
            # Dicionário para guardar as métricas de cada empresa
            stats = {
                'Ativo': info.get('symbol'),
                'Empresa': info.get('shortName'),
                'P/L': info.get('trailingPE'),
                'P/VP': info.get('priceToBook'),
                'EV/EBITDA': info.get('enterpriseToEbitda'),
                'Dividend Yield (%)': info.get('dividendYield', 0) * 100,
                'ROE (%)': info.get('returnOnEquity', 0) * 100,
                'Margem Bruta (%)': info.get('grossMargins', 0) * 100,
            }
            key_stats.append(stats)
        except Exception:
            # Ignora o ticker se houver erro
            continue
    return pd.DataFrame(key_stats)

@st.cache_data
def get_dcf_data(ticker, api_key):
    """Busca os dados necessários para o DCF da Alpha Vantage."""
    fd = FundamentalData(key=api_key, output_format='pandas')
    try:
        # Fluxo de Caixa
        cash_flow = fd.get_cash_flow_annual(symbol=ticker)[0]
        # Balanço Patrimonial
        balance_sheet = fd.get_balance_sheet_annual(symbol=ticker)[0]

        # Pegando os dados mais recentes (primeira coluna)
        fcf = float(cash_flow['freeCashFlow'].iloc[0])
        total_debt = float(balance_sheet['totalDebt'].iloc[0])
        cash_and_equivalents = float(balance_sheet['cashAndCashEquivalentsAtCarryingValue'].iloc[0])
        
        # yfinance para número de ações
        shares_outstanding = yf.Ticker(ticker).info['sharesOutstanding']
        
        return {
            'fcf': fcf,
            'net_debt': total_debt - cash_and_equivalents,
            'shares_outstanding': shares_outstanding
        }
    except Exception:
        return None

def calculate_dcf(fcf, net_debt, shares_outstanding, g, tg, wacc):
    """Calcula o valor intrínseco por ação usando um modelo DCF."""
    # Projeção de FCF para 5 anos
    fcf_proj = [fcf * (1 + g)**i for i in range(1, 6)]
    
    # Valor Terminal
    terminal_value = (fcf_proj[-1] * (1 + tg)) / (wacc - tg)
    
    # Descontando FCF e Valor Terminal
    pv_fcf = [fcf_proj[i] / (1 + wacc)**(i+1) for i in range(5)]
    pv_terminal_value = terminal_value / (1 + wacc)**5
    
    # Enterprise Value e Equity Value
    enterprise_value = sum(pv_fcf) + pv_terminal_value
    equity_value = enterprise_value - net_debt
    
    # Valor Intrínseco por Ação
    intrinsic_value = equity_value / shares_outstanding
    return intrinsic_value


# --- Título e Descrição ---
st.title("Painel de Research de Empresas")
st.markdown("Analise ações individuais e compare com seus pares de mercado.")

# --- Barra Lateral com Inputs ---
st.sidebar.header("Filtros de Análise")
ticker_symbol = st.sidebar.text_input(
    "Digite o Ticker Principal", 
    "AAPL",
    help="Ex: AAPL para Apple, PETR4.SA para Petrobras."
).upper()

# NOVO INPUT: Tickers dos concorrentes
peers_string = st.sidebar.text_area(
    "Insira os Tickers dos Concorrentes (separados por vírgula)",
    "MSFT, GOOG, AMZN",
    help="Tickers para compor a análise comparativa."
).upper()

analyze_button = st.sidebar.button("Analisar")

st.sidebar.subheader("Premissas do Modelo DCF")
growth_rate = st.sidebar.number_input("Taxa de Crescimento do FCF (anual %)", value=5.0, step=0.5, format="%.1f") / 100
terminal_growth_rate = st.sidebar.number_input("Taxa de Perpetuidade (%)", value=2.5, step=0.1, format="%.1f") / 100
wacc_rate = st.sidebar.number_input("Taxa de Desconto (WACC %)", value=9.0, step=0.5, format="%.1f") / 100

analyze_button = st.sidebar.button("Analisar")

# --- Lógica Principal ---
if analyze_button:
    if not ticker_symbol:
        st.warning("Por favor, digite um ticker principal para analisar.")
    else:
        try:
            with st.spinner(f"Carregando dados de {ticker_symbol}..."):
                # ... (código existente da Visão Geral, Fundamentalista, Gráfico e Notícias)
                ticker = yf.Ticker(ticker_symbol)
                info = ticker.info
                if not info.get('longName'):
                    st.error(f"Ticker '{ticker_symbol}' não encontrado ou inválido.")
                else:
                    # (SEÇÕES ANTERIORES - VISÃO GERAL, FUNDAMENTALISTA, GRÁFICO, NOTÍCIAS)
                    # Elas continuam aqui como estavam... (código omitido para brevidade, mas está no seu arquivo)
                    st.header(f"Visão Geral de: {info['longName']} ({info['symbol']})")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("País", info.get('country', 'N/A'))
                        st.metric("Setor", info.get('sector', 'N/A'))
                        st.metric("Indústria", info.get('industry', 'N/A'))
                    with col2:
                        st.metric("Moeda", info.get('currency', 'N/A'))
                        st.metric("Preço Atual", f"{info.get('currentPrice', 0):.2f}")
                        st.metric("Valor de Mercado", f"{(info.get('marketCap', 0) / 1e9):.2f}B")

                    # ... (resto das seções anteriores)
                    # --- NOVA SEÇÃO: Análise Comparativa ---
                    st.header("Análise Comparativa de Múltiplos (Comps)")
                    
                    peer_tickers = [p.strip() for p in peers_string.split(",")]
                    all_tickers = [ticker_symbol] + peer_tickers
                    
                    with st.spinner("Buscando dados dos concorrentes..."):
                        comps_df = get_key_stats(all_tickers)

                    if not comps_df.empty:
                        # Formata o DataFrame para exibição
                        comps_df_display = comps_df.set_index('Ativo')
                        for col in ['P/L', 'P/VP', 'EV/EBITDA']:
                            comps_df_display[col] = comps_df_display[col].map('{:.2f}'.format, na_action='ignore')
                        for col in ['Dividend Yield (%)', 'ROE (%)', 'Margem Bruta (%)']:
                             comps_df_display[col] = comps_df_display[col].map('{:.2f}%'.format, na_action='ignore')
                        
                        st.dataframe(comps_df_display, use_container_width=True)

                        # Gráficos Comparativos
                        st.subheader("Visualização dos Múltiplos")
                        
                        col_chart1, col_chart2 = st.columns(2)
                        with col_chart1:
                            fig_pe = px.bar(comps_df, x='Ativo', y='P/L', title='Comparativo de P/L', text='P/L')
                            fig_pe.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                            st.plotly_chart(fig_pe, use_container_width=True)
                        with col_chart2:
                            fig_ev = px.bar(comps_df, x='Ativo', y='EV/EBITDA', title='Comparativo de EV/EBITDA', text='EV/EBITDA')
                            fig_ev.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                            st.plotly_chart(fig_ev, use_container_width=True)
                    else:
                        st.warning("Não foi possível buscar dados para a análise comparativa.")

        except Exception as e:
            st.error(f"Ocorreu um erro inesperado durante a análise: {e}")

else:
    st.info("Digite um ticker e seus concorrentes na barra lateral para começar a análise.")

                    st.header(f"Valuation por DCF: {ticker_symbol}")
                        
                        with st.spinner("Buscando dados financeiros e calculando o DCF..."):
                            try:
                                av_api_key = st.secrets["ALPHA_VANTAGE_API_KEY"]
                                dcf_data = get_dcf_data(ticker_symbol, av_api_key)
                                
                                if dcf_data:
                                    # Calcula o valor intrínseco
                                    intrinsic_value = calculate_dcf(
                                        fcf=dcf_data['fcf'],
                                        net_debt=dcf_data['net_debt'],
                                        shares_outstanding=dcf_data['shares_outstanding'],
                                        g=growth_rate,
                                        tg=terminal_growth_rate,
                                        wacc=wacc_rate
                                    )
                                    
                                    # Pega o preço atual para comparação
                                    current_price = yf.Ticker(ticker_symbol).info['currentPrice']
                                    upside = ((intrinsic_value / current_price) - 1) * 100
                    
                                    # Exibe os resultados
                                    st.subheader("Resultado do Valuation")
                                    col1, col2, col3 = st.columns(3)
                                    col1.metric("Preço Justo (Valor Intrínseco)", f"${intrinsic_value:.2f}")
                                    col2.metric("Preço Atual de Mercado", f"${current_price:.2f}")
                                    col3.metric("Potencial de Upside/Downside", f"{upside:.2f}%")
                    
                                    if upside > 20:
                                        st.success(f"Recomendação: COMPRAR. O preço justo está significativamente acima do preço de mercado (margem de segurança > 20%).")
                                    elif upside < -20:
                                        st.error(f"Recomendação: VENDER. O preço justo está significativamente abaixo do preço de mercado.")
                                    else:
                                        st.warning(f"Recomendação: MANTER. O preço de mercado está próximo ao valor justo calculado.")
                    
                                else:
                                    st.error("Não foi possível buscar os dados financeiros da Alpha Vantage para o modelo DCF. O ticker pode não ter cobertura.")
                    
                            except Exception as e:
                                st.error(f"Ocorreu um erro ao executar o modelo DCF: {e}")
                    else:
                        st.info("Insira um ticker e clique em 'Analisar' para ver a análise completa, incluindo o valuation por DCF.")
