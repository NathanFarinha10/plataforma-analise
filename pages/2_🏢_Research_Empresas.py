# pages/2_🏢_Research_Empresas.py (Versão 2.0 - Refatorada com State e Módulos)

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import numpy as np

# --- Configuração da Página ---
st.set_page_config(page_title="PAG | Research de Empresas", page_icon="🏢", layout="wide")

# ADICIONE ESTAS LISTAS DE ORDENAÇÃO NO SEU SCRIPT

DRE_ORDER = [
    'Total Revenue', 'Cost Of Revenue', 'Gross Profit', 'Operating Expense',
    'Selling General And Administration', 'Research And Development', 'Operating Income',
    'Interest Income Non Operating', 'Interest Expense Non Operating', 'Other Income Expense Non Operating',
    'Pretax Income', 'Tax Provision', 'Net Income Common Stockholders', 'Net Income',
    'Basic EPS', 'Diluted EPS', 'EBITDA'
]

BP_ORDER = [
    # Ativos Circulantes
    'Cash And Cash Equivalents', 'Receivables', 'Inventory', 'Other Current Assets', 'Total Current Assets',
    # Ativos Não Circulantes
    'Net PPE', 'Goodwill And Other Intangible Assets', 'Other Non Current Assets', 'Total Non Current Assets',
    # Total de Ativos
    'Total Assets',
    # Passivos Circulantes
    'Payables And Accrued Expenses', 'Current Debt And Capital Lease Obligation', 'Other Current Liabilities', 'Total Current Liabilities',
    # Passivos Não Circulantes
    'Long Term Debt And Capital Lease Obligation', 'Other Non Current Liabilities', 'Total Non Current Liabilities',
    # Total de Passivos
    'Total Liabilities Net Minority Interest',
    # Patrimônio Líquido
    'Stockholders Equity', 'Total Equity Gross Minority Interest',
    # Total Passivo + PL
    'Total Liabilities And Equity'
]

FCF_ORDER = [
    'Operating Cash Flow', 'Investing Cash Flow', 'Financing Cash Flow', 'End Cash Position',
    'Changes In Cash', 'Capital Expenditure', 'Free Cash Flow'
]

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
# Essencial para a página não "resetar" após cliques em botões internos
if 'analysis_run' not in st.session_state:
    st.session_state.analysis_run = False
if 'ticker_to_analyze' not in st.session_state:
    st.session_state.ticker_to_analyze = ""
if 'peers_to_analyze' not in st.session_state:
    st.session_state.peers_to_analyze = ""

# --- FUNÇÕES AUXILIARES ---
def analisar_sentimento(texto):
    texto = texto.lower()
    palavras_positivas = ['crescimento', 'lucro', 'aumento', 'supera', 'expansão', 'forte', 'otimista', 'sucesso', 'melhora', 'compra', 'growth', 'profit', 'increase', 'beats', 'expansion', 'strong', 'optimistic', 'success', 'improves', 'buy', 'upgrade']
    palavras_negativas = ['queda', 'prejuízo', 'redução', 'abaixo', 'contração', 'fraco', 'pessimista', 'falha', 'piora', 'venda', 'fall', 'loss', 'reduction', 'below', 'contraction', 'weak', 'pessimistic', 'fails', 'worsens', 'sell', 'downgrade']
    score = 0
    for p in palavras_positivas:
        if p in texto: score += 1
    for p in palavras_negativas:
        if p in texto: score -= 1
    if score > 0: return 'Positivo', '🟢'
    elif score < 0: return 'Negativo', '🔴'
    else: return 'Neutro', '⚪️'

def reorder_financial_statement(df, order_list):
    """Reordena as linhas de um dataframe financeiro de acordo com uma lista padrão."""
    existing_rows = df.index.tolist()
    ordered_rows = [row for row in order_list if row in existing_rows]
    extra_rows = [row for row in existing_rows if row not in ordered_rows]
    final_order = ordered_rows + extra_rows
    return df.reindex(final_order)

@st.cache_data
def get_key_stats(tickers):
    key_stats = []
    for ticker_symbol in tickers:
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            stats = {'Ativo': info.get('symbol'), 'Empresa': info.get('shortName'), 'P/L': info.get('trailingPE'), 'P/VP': info.get('priceToBook'), 'EV/EBITDA': info.get('enterpriseToEbitda'), 'Dividend Yield (%)': info.get('dividendYield', 0) * 100, 'ROE (%)': info.get('returnOnEquity', 0) * 100, 'Margem Bruta (%)': info.get('grossMargins', 0) * 100}
            key_stats.append(stats)
        except Exception: continue
    return pd.DataFrame(key_stats)

@st.cache_data
def get_dcf_data_from_yf(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        op_cash_flow = ticker.cashflow.loc['Operating Cash Flow'].iloc[0]
        capex = ticker.cashflow.loc['Capital Expenditure'].iloc[0]
        fcf = op_cash_flow + capex
        total_liab = ticker.balance_sheet.loc['Total Liabilities Net Minority Interest'].iloc[0]
        total_cash = ticker.balance_sheet.loc['Cash And Cash Equivalents'].iloc[0]
        net_debt = total_liab - total_cash
        shares_outstanding = info['sharesOutstanding']
        return {'fcf': fcf, 'net_debt': net_debt, 'shares_outstanding': shares_outstanding, 'ebitda': info.get('ebitda')}
    except Exception: return None

def calculate_dcf(fcf, net_debt, shares_outstanding, g, tg, wacc):
    if (wacc - tg) <= 0: return 0
    fcf_proj = [fcf * (1 + g)**i for i in range(1, 6)]
    terminal_value = (fcf_proj[-1] * (1 + tg)) / (wacc - tg)
    pv_fcf = [fcf_proj[i] / (1 + wacc)**(i+1) for i in range(5)]
    pv_terminal_value = terminal_value / (1 + wacc)**5
    enterprise_value = sum(pv_fcf) + pv_terminal_value
    equity_value = enterprise_value - net_debt
    return equity_value / shares_outstanding

def plot_financial_statement(df, title):
    df_plot = df.T.sort_index(); df_plot.index = df_plot.index.year
    fig = px.bar(df_plot, barmode='group', title=title, text_auto='.2s')
    fig.update_layout(xaxis_title="Ano", yaxis_title="Valor"); st.plotly_chart(fig, use_container_width=True)

@st.cache_data
def calculate_dupont_analysis(income_stmt, balance_sheet):
    try:
        net_income = income_stmt.loc['Net Income']; revenue = income_stmt.loc['Total Revenue']
        total_assets = balance_sheet.loc['Total Assets']; equity = balance_sheet.loc['Stockholders Equity']
        net_profit_margin = (net_income / revenue) * 100; asset_turnover = revenue / total_assets
        financial_leverage = total_assets / equity
        roe = net_profit_margin * asset_turnover * financial_leverage / 100
        return pd.DataFrame({'Margem Líquida (%)': net_profit_margin, 'Giro do Ativo': asset_turnover, 'Alavancagem Financeira': financial_leverage, 'ROE Calculado (%)': roe}).T.sort_index(axis=1)
    except KeyError: return pd.DataFrame()

def formatar_numero(n):
    """Formata um número para uma string legível (Milhões, Bilhões)."""
    if pd.isna(n):
        return "-"
    n = float(n)
    if abs(n) >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f} B"
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:.2f} M"
    if abs(n) >= 1_000:
        return f"{n / 1_000:.2f} K"
    return f"{n:.2f}"

@st.cache_data
def calculate_financial_ratios(income_stmt, balance_sheet):
    ratios = {}
    try:
        current_assets = balance_sheet.loc['Current Assets']; current_liabilities = balance_sheet.loc['Current Liabilities']
        ratios['Liquidez Corrente'] = current_assets / current_liabilities
    except KeyError: pass 
    try:
        if 'Total Debt' in balance_sheet.index: total_debt = balance_sheet.loc['Total Debt']
        else: total_debt = balance_sheet.loc['Total Liabilities Net Minority Interest']
        equity = balance_sheet.loc['Stockholders Equity']
        ratios['Dívida / Patrimônio'] = total_debt / equity
    except KeyError: pass
    try:
        op_income = income_stmt.loc['Operating Income']; revenue = income_stmt.loc['Total Revenue']
        ratios['Margem Operacional (%)'] = (op_income / revenue) * 100
    except KeyError: pass
    try:
        revenue = income_stmt.loc['Total Revenue']; total_assets = balance_sheet.loc['Total Assets']
        ratios['Giro do Ativo'] = revenue / total_assets
    except KeyError: pass
    if not ratios: return pd.DataFrame()
    return pd.DataFrame(ratios).T.sort_index(axis=1)

def calculate_quality_score(info, dcf_data):
    scores = {}
    roe = info.get('returnOnEquity', 0) or 0
    if roe > 0.20: scores['ROE'] = 100
    elif roe > 0.15: scores['ROE'] = 75
    else: scores['ROE'] = max(0, (roe / 0.15) * 75)
    op_margin = info.get('operatingMargins', 0) or 0
    if op_margin > 0.15: scores['Margem Operacional'] = 100
    elif op_margin > 0.05: scores['Margem Operacional'] = 75
    else: scores['Margem Operacional'] = max(0, (op_margin / 0.05) * 75)
    if dcf_data and dcf_data.get('ebitda') and dcf_data['ebitda'] > 0:
        net_debt_ebitda = dcf_data['net_debt'] / dcf_data['ebitda']
        if net_debt_ebitda < 1: scores['Alavancagem'] = 100
        elif net_debt_ebitda < 3: scores['Alavancagem'] = 75
        elif net_debt_ebitda < 5: scores['Alavancagem'] = 25
        else: scores['Alavancagem'] = 0
    if not scores: return 0, {}
    return np.mean(list(scores.values())), scores

def get_rating_from_score(score):
    if score >= 85: return "Excelente", "💎"
    elif score >= 70: return "Atrativo", "🟢"
    elif score >= 50: return "Neutro", "🟡"
    else: return "Inatrativo", "🔴"

def calculate_value_score(info, comps_df, dcf_upside):
    scores = {}
    pe = info.get('trailingPE')
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
    scores = {}
    is_br = '.SA' in ticker_symbol
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

# --- UI E LÓGICA PRINCIPAL ---
st.title("Painel de Research de Empresas")
st.markdown("Analise ações individuais, compare com pares e calcule o valor intrínseco.")

# --- BARRA LATERAL (SIDEBAR) COM LÓGICA DE ESTADO ---
st.sidebar.header("Filtros de Análise")
ticker_symbol_input = st.sidebar.text_input("Ticker Principal", "AAPL", key="ticker_input").upper()
peers_string_input = st.sidebar.text_area("Tickers dos Concorrentes (para Comps)", "MSFT, GOOG, AMZN", key="peers_input").upper()

if st.sidebar.button("Analisar", key="analyze_button"):
    st.session_state.analysis_run = True
    st.session_state.ticker_to_analyze = ticker_symbol_input
    st.session_state.peers_to_analyze = peers_string_input

# --- LÓGICA DE EXIBIÇÃO DA ANÁLISE (CONTROLADA PELO session_state) ---
if st.session_state.analysis_run:
    ticker_symbol = st.session_state.ticker_to_analyze
    peers_string = st.session_state.peers_to_analyze
    
    if not ticker_symbol:
        st.warning("Por favor, digite um ticker principal para analisar.")
    else:
        info = yf.Ticker(ticker_symbol).info
        if not info.get('longName'):
            st.error(f"Ticker '{ticker_symbol}' não encontrado ou inválido.")
            st.session_state.analysis_run = False
        else:
            with st.spinner("Analisando... Este processo pode levar um momento."):
                dcf_data = get_dcf_data_from_yf(ticker_symbol)
                peer_tickers = [p.strip() for p in peers_string.split(",")] if peers_string else []
                comps_df = get_key_stats(peer_tickers)

            st.header(f"Análise de {info['longName']} ({info['symbol']})")

            st.subheader(f"Rating Proprietário (PAG Score)")
            quality_score, quality_breakdown = calculate_quality_score(info, dcf_data)
            quality_rating, quality_emoji = get_rating_from_score(quality_score)
            # O dcf_upside é None aqui, pois o cálculo agora é feito sob demanda
            value_score, value_breakdown = calculate_value_score(info, comps_df, dcf_upside=None)
            value_rating, value_emoji = get_rating_from_score(value_score)
            momentum_score, momentum_breakdown = calculate_momentum_score(ticker_symbol)
            momentum_rating, momentum_emoji = get_rating_from_score(momentum_score)

            col1_rat, col2_rat, col3_rat = st.columns(3)
            with col1_rat: st.metric("Qualidade", f"{quality_rating} {quality_emoji}", f"{quality_score:.0f} / 100"); st.expander("Detalhes").write(quality_breakdown)
            with col2_rat: st.metric("Valor (Value)", f"{value_rating} {value_emoji}", f"{value_score:.0f} / 100"); st.expander("Detalhes").write(value_breakdown)
            with col3_rat: st.metric("Momento", f"{momentum_rating} {momentum_emoji}", f"{momentum_score:.0f} / 100"); st.expander("Detalhes").write(momentum_breakdown)
            st.divider()

            st.subheader("Consenso de Mercado (Wall Street)")
            recommendation = info.get('recommendationKey', 'N/A'); target_price = info.get('targetMeanPrice', 0); current_price = info.get('currentPrice', 0); analyst_count = info.get('numberOfAnalystOpinions', 0)
            col1_cons, col2_cons, col3_cons, col4_cons = st.columns(4)
            col1_cons.metric("Recomendação Média", recommendation.upper() if recommendation != 'N/A' else 'N/A')
            col2_cons.metric("Preço-Alvo Médio", f"{target_price:.2f}" if target_price > 0 else "N/A")
            if target_price > 0 and current_price > 0: col3_cons.metric("Upside do Consenso", f"{((target_price / current_price) - 1) * 100:.2f}%")
            else: col3_cons.metric("Upside do Consenso", "N/A")
            col4_cons.metric("Nº de Analistas", f"{analyst_count}" if analyst_count > 0 else "N/A")
            st.divider()

            st.subheader("Visão Geral e Métricas Chave")
            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("País", info.get('country', 'N/A')); st.metric("Setor", info.get('sector', 'N/A'))
            with col2: st.metric("Moeda", info.get('currency', 'N/A')); st.metric("Preço Atual", f"{current_price:.2f}")
            with col3: st.metric("P/L", f"{info.get('trailingPE', 0):.2f}"); st.metric("P/VP", f"{info.get('priceToBook', 0):.2f}")
            with col4: st.metric("Dividend Yield", f"{info.get('dividendYield', 0) * 100:.2f}%"); st.metric("Beta", f"{info.get('beta', 0):.2f}")
            with st.expander("Descrição da Empresa"): st.write(info.get('longBusinessSummary', 'Descrição não disponível.'))

            st.header("Análise Financeira Histórica")
            ticker_obj = yf.Ticker(ticker_symbol)
            income_statement = ticker_obj.income_stmt; balance_sheet = ticker_obj.balance_sheet; cash_flow = ticker_obj.cashflow
            tab_dre, tab_bp, tab_fcf, tab_dupont, tab_ratios = st.tabs(["Resultados (DRE)", "Balanço (BP)", "Fluxo de Caixa (FCF)", "🔥 Análise DuPont", "📊 Ratios Financeiros"])
            
           # SUBSTITUA O CONTEÚDO DA ABA DRE
            with tab_dre:
                st.subheader("Evolução da Receita e Lucro")
                dre_items_chart = ['Total Revenue', 'Gross Profit', 'Operating Income', 'Net Income']
                plot_financial_statement(income_statement[income_statement.index.isin(dre_items_chart)], "Demonstração de Resultados Anual (Resumo)")
                
                with st.expander("Visualizar Demonstração de Resultados (DRE) completa"):
                    # Prepara a tabela para exibição
                    df_dre = income_statement.copy()
                    df_bp = reorder_financial_statement(df_bp, BP_ORDER)
                    df_dre = reorder_financial_statement(df_dre, DRE_ORDER)
                    df_dre.dropna(how='all', inplace=True) # Remove linhas sem nenhum dado
                    df_dre.columns = df_dre.columns.year # Usa apenas o ano como coluna
                    # Aplica a formatação em todas as células
                    df_dre_formatted = df_dre.applymap(formatar_numero)
                    st.dataframe(df_dre_formatted, use_container_width=True)
            # SUBSTITUA O CONTEÚDO DA ABA BP
            with tab_bp:
                st.subheader("Evolução dos Ativos e Passivos")
                bp_items_chart = ['Total Assets', 'Total Liabilities Net Minority Interest', 'Stockholders Equity']
                plot_financial_statement(balance_sheet[balance_sheet.index.isin(bp_items_chart)], "Balanço Patrimonial Anual (Resumo)")
            
                with st.expander("Visualizar Balanço Patrimonial (BP) completo"):
                    df_bp = balance_sheet.copy()
                    df_bp.dropna(how='all', inplace=True)
                    df_bp.columns = df_bp.columns.year
                    df_bp_formatted = df_bp.applymap(formatar_numero)
                    st.dataframe(df_bp_formatted, use_container_width=True)
            # SUBSTITUA O CONTEÚDO DA ABA FCF
            with tab_fcf:
                st.subheader("Evolução dos Fluxos de Caixa")
                fcf_items_chart = [item for item in ['Operating Cash Flow', 'Investing Cash Flow', 'Financing Cash Flow', 'Free Cash Flow'] if item in cash_flow.index]
                plot_financial_statement(cash_flow[cash_flow.index.isin(fcf_items_chart)], "Fluxo de Caixa Anual (Resumo)")
            
                with st.expander("Visualizar Fluxo de Caixa (FCF) completo"):
                    df_fcf = cash_flow.copy()
                    df_fcf = reorder_financial_statement(df_fcf, FCF_ORDER)
                    df_fcf.dropna(how='all', inplace=True)
                    df_fcf.columns = df_fcf.columns.year
                    df_fcf_formatted = df_fcf.applymap(formatar_numero)
                    st.dataframe(df_fcf_formatted, use_container_width=True)
            with tab_dupont:
                st.subheader("Decomposição do ROE (Return on Equity)")
                dupont_df = calculate_dupont_analysis(income_statement, balance_sheet)
                if not dupont_df.empty:
                    st.dataframe(dupont_df.style.format("{:.2f}"), use_container_width=True)
                    df_plot = dupont_df.T.sort_index(); df_plot.index = df_plot.index.year
                    fig_dupont = px.line(df_plot, markers=True, title="Evolução dos Componentes do ROE"); st.plotly_chart(fig_dupont, use_container_width=True)
                else: st.warning("Não foi possível calcular a Análise DuPont.")
            with tab_ratios:
                st.subheader("Análise de Indicadores Financeiros Chave")
                ratios_df = calculate_financial_ratios(income_statement, balance_sheet)
                if not ratios_df.empty:
                    df_plot_ratios = ratios_df.T.sort_index(); df_plot_ratios.index = df_plot_ratios.index.year
                    col1, col2 = st.columns(2)
                    if 'Liquidez Corrente' in df_plot_ratios.columns:
                        with col1: st.metric("Liquidez Corrente (x)", f"{df_plot_ratios['Liquidez Corrente'].iloc[-1]:.2f}"); st.plotly_chart(px.line(df_plot_ratios, y='Liquidez Corrente', title='Evolução da Liquidez Corrente', markers=True), use_container_width=True)
                    if 'Dívida / Patrimônio' in df_plot_ratios.columns:
                        with col2: st.metric("Dívida / Patrimônio (x)", f"{df_plot_ratios['Dívida / Patrimônio'].iloc[-1]:.2f}"); st.plotly_chart(px.line(df_plot_ratios, y='Dívida / Patrimônio', title='Evolução do Endividamento', markers=True), use_container_width=True)
                    if 'Margem Operacional (%)' in df_plot_ratios.columns:
                        with col1: st.metric("Margem Operacional (%)", f"{df_plot_ratios['Margem Operacional (%)'].iloc[-1]:.2f}%"); st.plotly_chart(px.line(df_plot_ratios, y='Margem Operacional (%)', title='Evolução da Margem Operacional', markers=True), use_container_width=True)
                    if 'Giro do Ativo' in df_plot_ratios.columns:
                        with col2: st.metric("Giro do Ativo (x)", f"{df_plot_ratios['Giro do Ativo'].iloc[-1]:.2f}"); st.plotly_chart(px.line(df_plot_ratios, y='Giro do Ativo', title='Evolução do Giro do Ativo', markers=True), use_container_width=True)
                else: st.warning("Dados insuficientes para calcular os ratios financeiros.")
            
            st.header("Análise Comparativa de Múltiplos (Comps)")
            if peers_string:
                if not comps_df.empty:
                    metric_cols = ['P/L', 'P/VP', 'EV/EBITDA', 'Dividend Yield (%)', 'ROE (%)', 'Margem Bruta (%)']
                    comps_df[metric_cols] = comps_df[metric_cols].apply(pd.to_numeric, errors='coerce')
                    st.dataframe(comps_df.set_index('Ativo').style.format("{:.2f}", subset=metric_cols, na_rep="N/A"), use_container_width=True)
                    col_chart1, col_chart2 = st.columns(2)
                    with col_chart1: st.plotly_chart(px.bar(comps_df, x='Ativo', y='P/L', title='Comparativo de P/L', text_auto='.2f'), use_container_width=True)
                    with col_chart2: st.plotly_chart(px.bar(comps_df, x='Ativo', y='EV/EBITDA', title='Comparativo de EV/EBITDA', text_auto='.2f'), use_container_width=True)
                else: st.warning("Não foi possível buscar dados para a análise comparativa.")
            else: st.info("Insira tickers de concorrentes na barra lateral para ver a análise comparativa.")
            
            st.header("💰 Valuation por DCF (Modelo Proprietário)")
            with st.expander("Clique aqui para realizar a análise de DCF", expanded=False):
                st.info("Insira as premissas do modelo e clique em 'Calcular' para ver o resultado.")
                col1, col2, col3 = st.columns(3)
                with col1: g_dcf = st.number_input("Cresc. FCF (anual %)", 5.0, step=0.5, format="%.1f", key="dcf_g") / 100
                with col2: tg_dcf = st.number_input("Perpetuidade (%)", 2.5, step=0.1, format="%.1f", key="dcf_tg") / 100
                with col3: wacc_dcf = st.number_input("WACC (%)", 9.0, step=0.5, format="%.1f", key="dcf_wacc") / 100
                if st.button("Calcular Preço Justo", key="dcf_button"):
                    if dcf_data:
                        intrinsic_value = calculate_dcf(fcf=dcf_data['fcf'], net_debt=dcf_data['net_debt'], shares_outstanding=dcf_data['shares_outstanding'], g=g_dcf, tg=tg_dcf, wacc=wacc_dcf)
                        if intrinsic_value > 0 and current_price > 0:
                            dcf_upside = ((intrinsic_value / current_price) - 1) * 100
                            st.subheader("Resultado do Valuation")
                            c1, c2, c3 = st.columns(3)
                            c1.metric("Preço Justo (Valor Intrínseco)", f"{info.get('currency', '')} {intrinsic_value:.2f}")
                            c2.metric("Preço Atual de Mercado", f"{info.get('currency', '')} {current_price:.2f}")
                            c3.metric("Potencial de Upside/Downside", f"{dcf_upside:.2f}%")
                            if dcf_upside > 20: st.success("RECOMENDAÇÃO (MODELO PAG): COMPRAR")
                            elif dcf_upside < -20: st.error("RECOMENDAÇÃO (MODELO PAG): VENDER")
                            else: st.warning("RECOMENDAÇÃO (MODELO PAG): MANTER")
                        else: st.error("Não foi possível calcular. Verifique se WACC > Perpetuidade e se há Preço Atual.")
                    else: st.error("Dados financeiros não carregados. Impossível rodar o DCF.")

            # SUBSTITUA A SEÇÃO DE HISTÓRICO DE COTAÇÕES POR ESTE BLOCO

            st.header("Histórico de Cotações")
            try:
                hist_df = yf.Ticker(ticker_symbol).history(period="5y")
                
                # Verifica se o dataframe retornado está vazio
                if hist_df.empty:
                    st.warning(f"Não foi possível obter o histórico de cotações para o ticker {ticker_symbol}.")
                else:
                    # Se os dados foram obtidos, plota o gráfico
                    fig_price = px.line(hist_df, y="Close", title=f"Preço de Fechamento de {info['shortName']}")
                    st.plotly_chart(fig_price, use_container_width=True)
            
            except Exception as e:
                # Se ocorrer qualquer outro erro na chamada do yfinance, exibe uma mensagem
                st.error(f"Ocorreu um erro ao buscar o histórico de cotações: {e}")

            # SUBSTITUA A SEÇÃO DE NOTÍCIAS INTEIRA POR ESTE BLOCO

            # SUBSTITUA A SEÇÃO DE NOTÍCIAS POR ESTE BLOCO DE DEPURAÇÃO

            # SUBSTITUA O BLOCO DE TESTE POR ESTE CÓDIGO FINAL

            st.header("Notícias Recentes e Análise de Sentimento")
            # Adicionamos uma nota ao usuário sobre a instabilidade da fonte de dados
            st.caption("Nota: A busca de notícias da fonte de dados pode ser instável e não funcionar para todos os ativos.")
            
            try:
                # 1. Fazemos a chamada real à API
                news = yf.Ticker(ticker_symbol).news
                
                # 2. Verificamos se a chamada retornou uma lista vazia
                if not news:
                    st.info("A busca por notícias não retornou resultados para este ativo.")
                else:
                    # 3. Se houver notícias, exibimos
                    for item in news[:5]: 
                        titulo = item.get('title')
                        if not titulo:
                            continue
                        
                        publisher = item.get('publisher', 'Não Informado')
                        link = item.get('link')
                        sentimento, icone = analisar_sentimento(titulo)
                        
                        with st.expander(f"{icone} {titulo}"):
                            st.markdown(f"**Publicado por:** {publisher} | **Sentimento:** {sentimento}")
                            if link:
                                st.link_button("Ler notícia completa", link)
            
            except Exception as e:
                # 4. Se qualquer outro erro ocorrer, nós o capturamos e exibimos
                st.warning(f"Ocorreu um erro ao tentar carregar as notícias: {e}")
else:
    st.info("Insira um ticker e clique em 'Analisar' para ver a análise completa.")
