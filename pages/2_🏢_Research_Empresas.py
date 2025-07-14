# pages/2_🏢_Research_Empresas.py (Versão Definitiva com Layout Restaurado)

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import numpy as np

# --- Configuração da Página ---
st.set_page_config(page_title="PAG | Research de Empresas", page_icon="🏢", layout="wide")

# --- FUNÇÕES DE COLETA DE DADOS ---
@st.cache_data
def get_financial_data(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        if not info.get('longName'): return None
        financials = {
            'info': info,
            'income_stmt': ticker.income_stmt,
            'balance_sheet': ticker.balance_sheet,
            'cash_flow': ticker.cashflow,
            'news': ticker.news
        }
        return financials
    except Exception: return None

@st.cache_data
def get_key_stats_for_comps(tickers):
    key_stats = []
    for ticker_symbol in tickers:
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            stats = {
                'Ativo': info.get('symbol'), 'Empresa': info.get('shortName'), 'P/L': info.get('trailingPE'),
                'P/VP': info.get('priceToBook'), 'EV/EBITDA': info.get('enterpriseToEbitda'),
                'Margem Bruta (%)': info.get('grossMargins', 0) * 100
            }
            key_stats.append(stats)
        except Exception: continue
    return pd.DataFrame(key_stats)

# --- FUNÇÕES DE CÁLCULO E ANÁLISE ---
def calculate_dcf(info, g, tg, wacc):
    try:
        ticker = yf.Ticker(info['symbol'])
        op_cash_flow = ticker.cashflow.loc['Operating Cash Flow'].iloc[0]
        capex = ticker.cashflow.loc['Capital Expenditure'].iloc[0]
        fcf = op_cash_flow + capex
        total_liab = ticker.balance_sheet.loc['Total Liabilities Net Minority Interest'].iloc[0]
        total_cash = ticker.balance_sheet.loc['Cash And Cash Equivalents'].iloc[0]
        net_debt = total_liab - total_cash
        shares_outstanding = info['sharesOutstanding']
        
        if (wacc - tg) <= 0: return 0
        fcf_proj = [fcf * (1 + g)**i for i in range(1, 6)]
        terminal_value = (fcf_proj[-1] * (1 + tg)) / (wacc - tg)
        pv_fcf = [fcf_proj[i] / (1 + wacc)**(i+1) for i in range(5)]
        pv_terminal_value = terminal_value / (1 + wacc)**5
        enterprise_value = sum(pv_fcf) + pv_terminal_value
        equity_value = enterprise_value - net_debt
        return equity_value / shares_outstanding
    except Exception: return 0

@st.cache_data
def calculate_dupont_analysis(income_stmt, balance_sheet):
    try:
        net_income = income_stmt.loc['Net Income']; revenue = income_stmt.loc['Total Revenue']
        total_assets = balance_sheet.loc['Total Assets']; equity = balance_sheet.loc['Stockholders Equity']
        net_profit_margin = (net_income / revenue) * 100; asset_turnover = revenue / total_assets
        financial_leverage = total_assets / equity; roe = net_profit_margin * asset_turnover * financial_leverage / 100
        return pd.DataFrame({'Margem Líquida (%)': net_profit_margin, 'Giro do Ativo': asset_turnover, 'Alavancagem Financeira': financial_leverage, 'ROE Calculado (%)': roe}).T.sort_index(axis=1)
    except KeyError: return pd.DataFrame()

def plot_financial_statement(df, title):
    df_plot = df.T.sort_index(); df_plot.index = df_plot.index.year
    fig = px.bar(df_plot, barmode='group', title=title, text_auto='.2s')
    fig.update_layout(xaxis_title="Ano", yaxis_title="Valor"); st.plotly_chart(fig, use_container_width=True)

# --- FUNÇÕES DE SCORE E NARRATIVA ---
def calculate_quality_score(info):
    scores = {}; roe = info.get('returnOnEquity', 0) or 0
    if roe > 0.20: scores['ROE'] = 100
    elif roe > 0.15: scores['ROE'] = 75
    else: scores['ROE'] = max(0, (roe / 0.15) * 75)
    op_margin = info.get('operatingMargins', 0) or 0
    if op_margin > 0.15: scores['Margem Operacional'] = 100
    elif op_margin > 0.05: scores['Margem Operacional'] = 75
    else: scores['Margem Operacional'] = max(0, (op_margin / 0.05) * 75)
    if not scores: return 0, {}
    return np.mean(list(scores.values())), scores

def calculate_value_score(info, comps_df, dcf_upside):
    scores = {}; pe = info.get('trailingPE')
    if pe and not comps_df.empty:
        peers_pe = comps_df['P/L'].median()
        if peers_pe > 0:
            if pe < peers_pe * 0.8: scores['P/L Relativo'] = 100
            elif pe < peers_pe: scores['P/L Relativo'] = 75
            else: scores['P/L Relativo'] = 25
    if dcf_upside is not None:
        if dcf_upside > 50: scores['DCF Upside'] = 100
        elif dcf_upside > 20: scores['DCF Upside'] = 75
        elif dcf_upside > 0: scores['DCF Upside'] = 50
        else: scores['DCF Upside'] = 0
    if not scores: return 0, {}
    return np.mean(list(scores.values())), scores

@st.cache_data
def calculate_momentum_score(ticker_symbol):
    scores = {}; is_br = '.SA' in ticker_symbol
    benchmark = '^BVSP' if is_br else '^GSPC'
    try:
        data = yf.download([ticker_symbol, benchmark], period='1y', progress=False)['Close']
        if data.empty: return 0, {}
        data['SMA200'] = data[ticker_symbol].rolling(window=200).mean()
        last_price = data[ticker_symbol].iloc[-1]; last_sma200 = data['SMA200'].iloc[-1]
        if last_price > last_sma200: scores['Tendência Longo Prazo'] = 100
        else: scores['Tendência Longo Prazo'] = 0
        returns = data.pct_change()
        for period in [3, 6, 9]:
            days = int(period * 21)
            if len(data) > days:
                asset_return = (1 + returns[ticker_symbol].tail(days)).prod() - 1
                bench_return = (1 + returns[benchmark].tail(days)).prod() - 1
                if asset_return > bench_return: scores[f'Força Relativa {period}M'] = 100
                else: scores[f'Força Relativa {period}M'] = 0
    except Exception: return 0, {}
    if not scores: return 0, {}
    return np.mean(list(scores.values())), scores

def get_rating_from_score(score):
    if score >= 85: return "Excelente", "💎"
    elif score >= 70: return "Atrativo", "🟢"
    elif score >= 50: return "Neutro", "🟡"
    else: return "Inatrativo", "🔴"

# --- UI E LÓGICA PRINCIPAL ---
st.title("Relatório de Análise de Ações")
st.markdown("Uma análise completa combinando dados quantitativos e narrativas analíticas.")
st.sidebar.header("Filtros de Análise"); ticker_symbol = st.sidebar.text_input("Ticker Principal", "MSFT").upper()
peers_string = st.sidebar.text_area("Tickers dos Concorrentes", "AAPL, GOOG, AMZN").upper()
st.sidebar.subheader("Premissas do DCF (Opcional)"); growth_rate = st.sidebar.number_input("Crescimento do FCF (anual %)", value=5.0, step=0.5, format="%.1f") / 100
terminal_growth_rate = st.sidebar.number_input("Perpetuidade (%)", value=2.5, step=0.1, format="%.1f") / 100
wacc_rate = st.sidebar.number_input("Taxa de Desconto (WACC %)", value=9.0, step=0.5, format="%.1f") / 100

analyze_button = st.sidebar.button("Gerar Relatório Completo")

if analyze_button:
    if not ticker_symbol: 
        st.warning("Por favor, digite um ticker principal para analisar.")
    else:
        with st.spinner("Buscando e processando todos os dados... Este é um processo completo e pode levar um momento."):
            financials = get_financial_data(ticker_symbol)
            peer_tickers = [p.strip() for p in peers_string.split(",")] if peers_string else []
            comps_df = get_key_stats_for_comps(peer_tickers)
        
        if not financials:
            st.error(f"Não foi possível buscar os dados financeiros para '{ticker_symbol}'. Verifique o ticker ou a cobertura da API.")
        else:
            info = financials['info']
            income_statement = financials['income_stmt']
            balance_sheet = financials['balance_sheet']
            cash_flow = financials['cash_flow']
            news = financials['news']

            st.header(f"Relatório de Análise: {info.get('longName', ticker_symbol)}")
            
            # --- CAPÍTULO 1: SUMÁRIO E HIGHLIGHTS (Placeholder) ---
            st.subheader("Sumário Executivo e Ratings")
            st.info("Em breve: Uma tese de investimento sumarizada e os principais destaques do último resultado.")
            st.divider()

            # --- CÁLCULO DOS SCORES E DCF ---
            quality_score, quality_breakdown = calculate_quality_score(info)
            momentum_score, momentum_breakdown = calculate_momentum_score(ticker_symbol)
            intrinsic_value = calculate_dcf(info, g=growth_rate, tg=terminal_growth_rate, wacc=wacc_rate)
            dcf_upside = None
            current_price = info.get('currentPrice')
            if current_price and intrinsic_value > 0:
                dcf_upside = ((intrinsic_value / current_price) - 1) * 100
            value_score, value_breakdown = calculate_value_score(info, comps_df, dcf_upside)

            # --- SEÇÃO DE RATING E CONSENSO ---
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Rating Proprietário (PAG Score)")
                quality_rating, quality_emoji = get_rating_from_score(quality_score)
                value_rating, value_emoji = get_rating_from_score(value_score)
                momentum_rating, momentum_emoji = get_rating_from_score(momentum_score)
                st.metric("Qualidade", f"{quality_rating} {quality_emoji}", f"{quality_score:.0f} / 100")
                st.metric("Valor (Value)", f"{value_rating} {value_emoji}", f"{value_score:.0f} / 100")
                st.metric("Momento", f"{momentum_rating} {momentum_emoji}", f"{momentum_score:.0f} / 100")
            with col2:
                st.subheader("Consenso de Mercado (Wall Street)")
                recommendation = info.get('recommendationKey', 'N/A')
                target_price = info.get('targetMeanPrice', 0)
                analyst_count = info.get('numberOfAnalystOpinions', 0)
                st.metric("Recomendação Média", recommendation.upper() if recommendation != 'N/A' else 'N/A')
                st.metric("Preço-Alvo Médio", f"{target_price:.2f}" if target_price > 0 else "N/A")
                if target_price > 0 and current_price > 0:
                    upside_consensus = ((target_price / current_price) - 1) * 100
                    st.metric("Upside do Consenso", f"{upside_consensus:.2f}%")
                else: st.metric("Upside do Consenso", "N/A")
            st.divider()

            # --- SEÇÃO DE VISÃO GERAL (RESTAURADA) ---
            st.header("Visão Geral da Companhia")
            col_v1, col_v2, col_v3, col_v4 = st.columns(4)
            col_v1.metric("País", info.get('country', 'N/A'))
            col_v2.metric("Setor", info.get('sector', 'N/A'))
            col_v3.metric("Indústria", info.get('industry', 'N/A'))
            col_v4.metric("Moeda", info.get('currency', 'N/A'))
            with st.expander("Descrição do Negócio"):
                st.write(info.get('longBusinessSummary', 'Descrição não disponível.'))
            st.divider()

            # --- SEÇÃO DE ANÁLISE COMPARÁVEL (RESTAURADA) ---
            st.header("Análise Comparativa (Comps)")
            if not comps_df.empty:
                st.dataframe(comps_df.set_index('Ativo').style.format(precision=2, na_rep="N/A"), use_container_width=True)
                st.subheader("Visualização dos Múltiplos vs. Pares")
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    fig_pe = px.bar(comps_df, x='Ativo', y='P/L', title='Comparativo de P/L', text_auto='.2f')
                    st.plotly_chart(fig_pe, use_container_width=True)
                with col_c2:
                    fig_ev = px.bar(comps_df, x='Ativo', y='EV/EBITDA', title='Comparativo de EV/EBITDA', text_auto='.2f')
                    st.plotly_chart(fig_ev, use_container_width=True)
            else:
                st.info("Insira tickers de concorrentes na barra lateral para ver a análise comparativa.")
            st.divider()
            
            # --- SEÇÃO DE DEMONSTRAÇÕES FINANCEIRAS (GRÁFICOS E DUPONT) ---
            st.header("Análise Financeira Histórica")
            tab_dre, tab_bp, tab_fcf, tab_dupont = st.tabs(["Resultados (DRE)", "Balanço (BP)", "Fluxo de Caixa (FCF)", "🔥 Análise DuPont"])
            with tab_dre: plot_financial_statement(income_statement[income_statement.index.isin(['Total Revenue', 'Gross Profit', 'Operating Income', 'Net Income'])], "Evolução da Demonstração de Resultados")
            with tab_bp: plot_financial_statement(balance_sheet[balance_sheet.index.isin(['Total Assets', 'Total Liabilities Net Minority Interest', 'Stockholders Equity'])], "Evolução do Balanço Patrimonial")
            with tab_fcf: plot_financial_statement(cash_flow[cash_flow.index.isin(['Operating Cash Flow', 'Investing Cash Flow', 'Financing Cash Flow', 'Free Cash Flow'])], "Evolução do Fluxo de Caixa")
            with tab_dupont:
                dupont_df = calculate_dupont_analysis(income_statement, balance_sheet)
                if not dupont_df.empty:
                    st.dataframe(dupont_df.style.format("{:.2f}"), use_container_width=True)
                    df_plot = dupont_df.T.sort_index(); df_plot.index = df_plot.index.year
                    fig = px.line(df_plot, markers=True, title="Evolução dos Componentes do ROE")
                    st.plotly_chart(fig, use_container_width=True)
            st.divider()
            
            # --- SEÇÃO DCF ---
            st.header(f"Valuation por DCF (Modelo Proprietário)")
            if intrinsic_value > 0:
                col1_dcf, col2_dcf, col3_dcf = st.columns(3)
                col1_dcf.metric("Preço Justo (Valor Intrínseco)", f"{info.get('currency', '')} {intrinsic_value:.2f}")
                col2_dcf.metric("Preço Atual de Mercado", f"{current_price:.2f}")
                col3_dcf.metric("Potencial de Upside/Downside", f"{dcf_upside:.2f}%")
            else:
                st.warning("Não foi possível calcular o DCF com as premissas atuais. Tente ajustar as taxas de crescimento e desconto.")
            st.divider()
            
            # --- SEÇÃO HISTÓRICO DE PREÇOS ---
            st.header("Histórico de Cotações")
            hist_df = yf.Ticker(ticker_symbol).history(period="5y")
            fig_price = px.line(hist_df, x=hist_df.index, y="Close", title=f"Preço de Fechamento de {info['shortName']}", labels={'Close': f'Preço ({info["currency"]})', 'Date': 'Data'})
            st.plotly_chart(fig_price, use_container_width=True)

else:
    st.info("Insira um ticker e clique em 'Gerar Relatório Completo' para iniciar a análise.")
