# pages/2_🏢_Research_Empresas.py (Versão Final com Relatório Narrativo Completo)

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import numpy as np

# --- Configuração da Página ---
st.set_page_config(page_title="PAG | Research de Empresas", page_icon="🏢", layout="wide")

# --- FUNÇÕES AUXILIARES ---

@st.cache_data
def get_financial_data(ticker_symbol):
    """Busca todos os dados financeiros de uma vez para evitar erros de sequência."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        if not info.get('longName'): return None

        financials = {
            'info': info,
            'income_stmt': ticker.income_stmt,
            'balance_sheet': ticker.balance_sheet,
            'cash_flow': ticker.cashflow,
        }
        return financials
    except Exception:
        return None

@st.cache_data
def get_key_stats_for_comps(tickers):
    """Busca dados chave para a tabela de comparáveis."""
    key_stats = []
    for ticker_symbol in tickers:
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            stats = {'Ativo': info.get('symbol'), 'Empresa': info.get('shortName'), 'P/L': info.get('trailingPE'), 'P/VP': info.get('priceToBook'), 'Margem Bruta (%)': info.get('grossMargins', 0) * 100}
            key_stats.append(stats)
        except Exception: continue
    return pd.DataFrame(key_stats)

def plot_financial_statement(df, title):
    """Plota um gráfico de barras para uma demonstração financeira."""
    df_plot = df.T.sort_index(); df_plot.index = df_plot.index.year
    fig = px.bar(df_plot, barmode='group', title=title, text_auto='.2s')
    fig.update_layout(xaxis_title="Ano", yaxis_title="Valor"); st.plotly_chart(fig, use_container_width=True)

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
        if last_price > last_sma200: scores['Tendência Longo Prazo (vs. MME200)'] = 100
        else: scores['Tendência Longo Prazo (vs. MME200)'] = 0
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

@st.cache_data
def analyze_sector(info, comps_df):
    try:
        sector = info.get('sector', 'não especificado'); industry = info.get('industry', 'não especificada')
        narrative = f"A **{info.get('shortName')}** atua no setor de **{sector}**, dentro da indústria de **{industry}**. "
        if not comps_df.empty:
            peers_pe = comps_df['P/L'].median(); company_pe = info.get('trailingPE')
            if peers_pe and company_pe:
                narrative += f"Atualmente, o setor negocia a um P/L mediano de **{peers_pe:.1f}x**. Com um P/L de **{company_pe:.1f}x**, a empresa está sendo negociada "
                if company_pe > peers_pe * 1.1: narrative += "**com um prêmio** em relação aos seus pares."
                elif company_pe < peers_pe * 0.9: narrative += "**com um desconto** em relação aos seus pares."
                else: narrative += "**em linha** com seus pares."
        return narrative
    except Exception: return "Não foi possível gerar a análise setorial."

@st.cache_data
def analyze_metric_trend(financial_statement, metric_name, unit='B', is_margin=False, higher_is_better=True, statement_name='relatório'):
    try:
        series = financial_statement.loc[metric_name].sort_index()
        start_value = series.iloc[0]; end_value = series.iloc[-1]; num_years = len(series) - 1
        trend_abs = end_value - start_value; trend_rel = (trend_abs / abs(start_value)) * 100 if start_value != 0 else 0
        if trend_abs > 0: trend_text = f"uma tendência de **crescimento ({trend_rel:+.1f}%)**" if higher_is_better else f"uma tendência de **aumento ({trend_rel:+.1f}%)**, o que requer atenção"
        elif trend_abs < 0: trend_text = f"uma tendência de **contração ({trend_rel:.1f}%)**, o que requer atenção" if higher_is_better else f"uma tendência de **redução ({trend_rel:.1f}%)**, um sinal positivo"
        else: trend_text = "uma tendência de **estabilidade**"
        if is_margin: value_text = f"de {start_value:.2%} para **{end_value:.2%}**"
        elif unit == 'B': value_text = f"de {start_value/1e9:.2f}B para **{end_value/1e9:.2f}B**"
        else: value_text = f"de {start_value/1e6:.2f}M para **{end_value/1e6:.2f}M**"
        return f"Nos últimos {num_years+1} anos, a métrica exibiu {trend_text}, passando {value_text}."
    except KeyError: return f"Dados para '{metric_name}' não encontrados no {statement_name}."
    except Exception: return "Não foi possível analisar a tendência da métrica."

@st.cache_data
def analyze_roic(income_stmt, balance_sheet):
    try:
        ebit = income_stmt.loc['EBIT']; tax_provision = income_stmt.loc['Tax Provision']
        pretax_income = income_stmt.loc['Pretax Income']; tax_rate = (tax_provision / pretax_income).fillna(0)
        nopat = ebit * (1 - tax_rate)
        total_debt = balance_sheet.loc['Total Debt'] if 'Total Debt' in balance_sheet.index else balance_sheet.loc['Total Liabilities Net Minority Interest']
        equity = balance_sheet.loc['Stockholders Equity']; cash = balance_sheet.loc['Cash And Cash Equivalents']
        invested_capital = total_debt + equity - cash
        roic = (nopat / invested_capital) * 100; last_roic = roic.iloc[-1]
        if last_roic > 15: judgment = "um **excelente** nível de retorno, indicando uma forte vantagem competitiva."
        elif last_roic > 10: judgment = "um **bom** nível de retorno, sugerindo uma alocação de capital eficiente."
        else: judgment = "um nível de retorno **modesto**, que merece um olhar mais atento."
        return f"O Retorno sobre o Capital Investido (ROIC) mais recente foi de **{last_roic:.1f}%**, o que consideramos {judgment}"
    except Exception: return "Não foi possível calcular o ROIC."

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
    if not ticker_symbol: st.warning("Por favor, digite um ticker principal para analisar.")
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

            st.header(f"Relatório de Análise: {info.get('longName', ticker_symbol)}")
            
            # --- CAPÍTULO 1: SUMÁRIO E HIGHLIGHTS (Ainda como placeholder) ---
            st.subheader("Sumário Executivo e Highlights")
            st.info("Em breve: Um resumo com os principais pontos positivos, negativos e a tese de investimento final.")
            st.divider()

            # --- CAPÍTULO 2: ANÁLISE SETORIAL ---
            st.subheader("Contexto Setorial")
            st.write(analyze_sector(info, comps_df))
            st.divider()

            # --- CAPÍTULO 3: NARRATIVA DOS INDICADORES ---
            st.subheader("Análise Detalhada da Performance Financeira")
            
            narratives_col1, narratives_col2 = st.columns(2)
            with narratives_col1:
                st.markdown("**Crescimento de Receita**"); st.write(analyze_metric_trend(income_statement, 'Total Revenue', statement_name="DRE"))
                st.markdown("**Margem Bruta**"); income_statement['Gross Margin'] = income_statement['Gross Profit'] / income_statement['Total Revenue']; st.write(analyze_metric_trend(income_statement, 'Gross Margin', is_margin=True, statement_name="DRE"))
                st.markdown("**Margem Operacional**"); income_statement['Operating Margin'] = income_statement['Operating Income'] / income_statement['Total Revenue']; st.write(analyze_metric_trend(income_statement, 'Operating Margin', is_margin=True, statement_name="DRE"))
            with narratives_col2:
                st.markdown("**Lucro por Ação (EPS)**"); st.write(analyze_metric_trend(income_statement, 'Basic EPS', unit='dólares', is_margin=True, statement_name="DRE"))
                st.markdown("**Fluxo de Caixa Livre (FCF)**"); st.write(analyze_metric_trend(cash_flow, 'Free Cash Flow', statement_name="Fluxo de Caixa"))
                st.markdown("**Retorno sobre o Capital Investido (ROIC)**"); st.write(analyze_roic(income_statement, balance_sheet))
            st.markdown("**Dívida Líquida**"); balance_sheet['Net Debt'] = balance_sheet.get('Total Debt', 0) - balance_sheet.get('Cash And Cash Equivalents', 0); st.write(analyze_metric_trend(balance_sheet, 'Net Debt', higher_is_better=False, statement_name="Balanço"))
            st.divider()
            
            # --- CAPÍTULO 4: ANÁLISE HISTÓRICA DETALHADA ---
            st.header("Demonstrações Financeiras (Gráficos)")
            tab_dre, tab_bp, tab_fcf, tab_dupont = st.tabs(["Resultados (DRE)", "Balanço (BP)", "Fluxo de Caixa (FCF)", "🔥 Análise DuPont"])
            with tab_dre:
                dre_items = ['Total Revenue', 'Gross Profit', 'Operating Income', 'Net Income']
                plot_financial_statement(income_statement[income_statement.index.isin(dre_items)], "Evolução da Demonstração de Resultados")
            with tab_bp:
                bp_items = ['Total Assets', 'Total Liabilities Net Minority Interest', 'Stockholders Equity']
                plot_financial_statement(balance_sheet[balance_sheet.index.isin(bp_items)], "Evolução do Balanço Patrimonial")
            with tab_fcf:
                fcf_items = ['Operating Cash Flow', 'Investing Cash Flow', 'Financing Cash Flow', 'Free Cash Flow']
                plot_financial_statement(cash_flow[cash_flow.index.isin(fcf_items)], "Evolução do Fluxo de Caixa")
            with tab_dupont:
                dupont_df = calculate_dupont_analysis(income_statement, balance_sheet)
                if not dupont_df.empty:
                    st.dataframe(dupont_df.style.format("{:.2f}"), use_container_width=True)
                    df_plot = dupont_df.T.sort_index(); df_plot.index = df_plot.index.year
                    fig = px.line(df_plot, markers=True, title="Evolução dos Componentes do ROE")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Não foi possível calcular a Análise DuPont.")
else:
    st.info("Insira um ticker e clique em 'Gerar Relatório Completo' para iniciar a análise.")
