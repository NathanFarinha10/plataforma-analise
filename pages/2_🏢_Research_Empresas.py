# pages/2_🏢_Research_Empresas.py (Versão Definitiva, Corrigida e Completa)

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import numpy as np

# --- Configuração da Página ---
st.set_page_config(page_title="PAG | Research de Empresas", page_icon="🏢", layout="wide")

# ==============================================================================
# --- SEÇÃO DE DEFINIÇÃO DE TODAS AS FUNÇÕES ---
# ==============================================================================

@st.cache_data
def get_financial_data(ticker_symbol):
    """Busca todos os dados financeiros essenciais de uma vez."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        if not info.get('longName'): return None

        financials = {
            'info': info,
            'income_stmt': ticker.income_stmt,
            'balance_sheet': ticker.balance_sheet,
            'cash_flow': ticker.cashflow,
            'earnings_dates': ticker.earnings_dates,
            'news': ticker.news
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
            stats = {
                'Ativo': info.get('symbol'), 'Empresa': info.get('shortName'), 'P/L': info.get('trailingPE'),
                'P/VP': info.get('priceToBook'), 'EV/EBITDA': info.get('enterpriseToEbitda'),
                'Margem Bruta (%)': info.get('grossMargins', 0) * 100
            }
            key_stats.append(stats)
        except Exception: continue
    return pd.DataFrame(key_stats)

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
        if num_years < 1: return f"Dados históricos insuficientes para analisar a tendência de '{metric_name}'."
        cagr = ((end_value / start_value) ** (1 / num_years)) - 1 if start_value != 0 and np.sign(start_value) == np.sign(end_value) else 0
        
        if cagr > 0.01: trend_text = f"uma tendência de **crescimento**, com uma taxa anual composta (CAGR) de **{cagr:.2%}**" if higher_is_better else f"uma tendência de **aumento**, com CAGR de **{cagr:.2%}**, o que requer atenção"
        elif cagr < -0.01: trend_text = f"uma tendência de **contração** (CAGR de **{cagr:.2%}**), o que requer atenção" if higher_is_better else f"uma tendência de **redução** (CAGR de **{cagr:.2%}**), um sinal positivo"
        else: trend_text = "uma tendência de **estabilidade**"
            
        if is_margin: value_text = f"passando de {start_value:.2%} para **{end_value:.2%}**"
        elif unit == 'B': value_text = f"passando de {start_value/1e9:.2f}B para **{end_value/1e9:.2f}B**"
        else: value_text = f"passando de {start_value:.2f} para **{end_value:.2f}**"
        
        return f"Nos últimos {num_years+1} anos, a métrica exibiu {trend_text}, {value_text}."
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

@st.cache_data
def analyze_highlights(earnings_dates):
    """Analisa o último resultado trimestral contra as expectativas."""
    try:
        last_earning = earnings_dates.iloc[-1]
        reported_eps = last_earning.get('Reported EPS')
        estimated_eps = last_earning.get('EPS Estimate')
        if pd.notna(reported_eps) and pd.notna(estimated_eps):
            surprise = ((reported_eps / estimated_eps) - 1) * 100
            if surprise > 0:
                return f"No último resultado divulgado, a empresa **superou as expectativas** do mercado, reportando um Lucro por Ação (EPS) de **${reported_eps:.2f}**, cerca de **{surprise:.1f}% acima** do estimado."
            else:
                return f"No último resultado divulgado, a empresa **frustrou as expectativas** do mercado, reportando um Lucro por Ação (EPS) de **${reported_eps:.2f}**, cerca de **{abs(surprise):.1f}% abaixo** do estimado."
        return "Não há dados suficientes para comparar o último resultado com as expectativas do mercado."
    except Exception: return "Não foi possível analisar os destaques do último resultado."

def generate_summary_and_thesis(scores, info, dcf_upside):
    """Gera a tese de investimento final e os pontos chave."""
    quality_score, value_score, momentum_score = scores['quality'], scores['value'], scores['momentum']
    
    if quality_score >= 70 and value_score >= 70: tese = "Oportunidade de investimento em uma empresa de alta qualidade negociando a um valuation atrativo."
    elif quality_score >= 70 and value_score < 50: tese = "Uma empresa de alta qualidade, porém seu valuation atual parece esticado, sugerindo cautela."
    elif quality_score < 50 and value_score >= 70: tese = "Uma potencial oportunidade de 'turnaround' ou 'deep value', mas que exige uma análise aprofundada dos riscos associados à baixa qualidade dos fundamentos."
    else: tese = "A combinação de fundamentos que requerem atenção e um valuation não atrativo sugere uma posição de cautela no momento."
        
    bull_points = []; bear_points = []
    
    if quality_score >= 85: bull_points.append("💎 Qualidade Fundamental Excelente (ROE e Margens Elevadas)")
    if value_score >= 85: bull_points.append("🟢 Valuation Muito Atrativo vs. Pares e DCF")
    if momentum_score >= 70: bull_points.append("📈 Forte Momento de Mercado e Tendência de Alta")
    if dcf_upside and dcf_upside > 20: bull_points.append(f"💰 Upside de {dcf_upside:.0f}% em nosso Modelo DCF")

    if quality_score < 50: bear_points.append("🔴 Qualidade Fundamental Baixa (Rentabilidade e Margens Fracas)")
    if value_score < 50: bear_points.append("⚠️ Valuation Esticado ou Acima dos Pares")
    if momentum_score < 50: bear_points.append("📉 Momento de Mercado Desafiador ou Tendência de Baixa")
        
    return tese, bull_points, bear_points

# ==============================================================================
# --- UI E LÓGICA PRINCIPAL ---
# ==============================================================================

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
            earnings_dates = financials['earnings_dates']
            news = financials['news']

            st.header(f"Relatório de Análise: {info.get('longName', ticker_symbol)}")
            
            # CÁLCULO DE TODOS OS SCORES E VALUATIONS PRIMEIRO
            quality_score, quality_breakdown = calculate_quality_score(info)
            momentum_score, momentum_breakdown = calculate_momentum_score(ticker_symbol)
            intrinsic_value = calculate_dcf(info, g=growth_rate, tg=terminal_growth_rate, wacc=wacc_rate)
            dcf_upside = None
            current_price = info.get('currentPrice')
            if current_price and intrinsic_value > 0:
                dcf_upside = ((intrinsic_value / current_price) - 1) * 100
            value_score, value_breakdown = calculate_value_score(info, comps_df, dcf_upside)
            
            # SEÇÃO DE SUMÁRIO E HIGHLIGHTS
            st.subheader("Sumário Executivo e Destaques")
            tese, bull_points, bear_points = generate_summary_and_thesis({'quality': quality_score, 'value': value_score, 'momentum': momentum_score}, info, dcf_upside)
            st.info(f"**Tese de Investimento:** \"{tese}\"")
            col1_sum, col2_sum = st.columns(2)
            with col1_sum:
                st.markdown("**Pontos Fortes (Bull Case)**")
                if bull_points:
                    for point in bull_points: st.markdown(f"- {point}")
                else: st.caption("Nenhum ponto forte destacado pelos critérios.")
            with col2_sum:
                st.markdown("**Riscos e Pontos de Atenção (Bear Case)**")
                if bear_points:
                    for point in bear_points: st.markdown(f"- {point}")
                else: st.caption("Nenhum risco destacado pelos critérios.")
            st.markdown("**Destaques do Último Resultado:** " + analyze_highlights(earnings_dates))
            st.divider()

            # SEÇÃO DE RATINGS E CONSENSO
            st.header("Ratings e Visão de Mercado")
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Rating Proprietário (PAG Score)")
                quality_rating, quality_emoji = get_rating_from_score(quality_score); value_rating, value_emoji = get_rating_from_score(value_score); momentum_rating, momentum_emoji = get_rating_from_score(momentum_score)
                st.metric("Qualidade", f"{quality_rating} {quality_emoji}", f"{quality_score:.0f} / 100")
                st.metric("Valor (Value)", f"{value_rating} {value_emoji}", f"{value_score:.0f} / 100")
                st.metric("Momento", f"{momentum_rating} {momentum_emoji}", f"{momentum_score:.0f} / 100")
            with col2:
                st.subheader("Consenso de Mercado (Wall Street)")
                recommendation = info.get('recommendationKey', 'N/A'); target_price = info.get('targetMeanPrice', 0); analyst_count = info.get('numberOfAnalystOpinions', 0)
                st.metric("Recomendação Média", recommendation.upper() if recommendation != 'N/A' else 'N/A')
                st.metric("Preço-Alvo Médio", f"{target_price:.2f}" if target_price > 0 else "N/A")
                if target_price > 0 and current_price > 0:
                    upside_consensus = ((target_price / current_price) - 1) * 100
                    st.metric("Upside do Consenso", f"{upside_consensus:.2f}%")
                else: st.metric("Upside do Consenso", "N/A")
            st.divider()

            # SEÇÃO NARRATIVA
            st.header("Análise Detalhada da Performance Financeira")
            col_narrative1, col_narrative2 = st.columns(2)
            with col_narrative1:
                st.markdown("**Contexto Setorial:** " + analyze_sector(info, comps_df))
                st.markdown("**Crescimento de Receita:** " + analyze_metric_trend(income_statement, 'Total Revenue', statement_name="DRE"))
                st.markdown("**Margem Bruta:** " + analyze_metric_trend(income_statement, 'Gross Margin', is_margin=True, statement_name="DRE"))
            with col_narrative2:
                st.markdown("**Margem Operacional:** " + analyze_metric_trend(income_statement, 'Operating Margin', is_margin=True, statement_name="DRE"))
                st.markdown("**Lucro por Ação (EPS):** " + analyze_metric_trend(income_statement, 'Basic EPS', unit='dólares', is_margin=False, statement_name="DRE"))
                st.markdown("**Retorno sobre o Capital Investido (ROIC):** " + analyze_roic(income_statement, balance_sheet))
            st.divider()
            
            # SEÇÃO GRÁFICOS E DCF
            st.header("Análise Financeira e Valuation")
            tab_charts, tab_dcf, tab_comps = st.tabs(["Demonstrações Financeiras", "Modelo DCF", "Análise de Comparáveis"])
            with tab_charts:
                st.subheader("Análise Gráfica Histórica")
                tab_dre, tab_bp, tab_fcf, tab_dupont = st.tabs(["DRE", "Balanço", "Fluxo de Caixa", "🔥 DuPont"])
                with tab_dre: plot_financial_statement(income_statement[income_statement.index.isin(['Total Revenue', 'Gross Profit', 'Operating Income', 'Net Income'])], "Evolução da Demonstração de Resultados")
                with tab_bp: plot_financial_statement(balance_sheet[balance_sheet.index.isin(['Total Assets', 'Total Liabilities Net Minority Interest', 'Stockholders Equity'])], "Evolução do Balanço Patrimonial")
                with tab_fcf: plot_financial_statement(cash_flow[cash_flow.index.isin(['Operating Cash Flow', 'Investing Cash Flow', 'Financing Cash Flow', 'Free Cash Flow'])], "Evolução do Fluxo de Caixa")
                with tab_dupont:
                    st.subheader("Decomposição do ROE (Análise DuPont)")
                    dupont_df = calculate_dupont_analysis(income_statement, balance_sheet)
                    if not dupont_df.empty:
                        st.dataframe(dupont_df.style.format("{:.2f}"), use_container_width=True)
                        df_plot = dupont_df.T.sort_index(); df_plot.index = df_plot.index.year
                        fig = px.line(df_plot, markers=True, title="Evolução dos Componentes do ROE")
                        st.plotly_chart(fig, use_container_width=True)
            with tab_dcf:
                st.subheader("Valuation por Fluxo de Caixa Descontado (DCF)")
                if intrinsic_value > 0:
                    col1_dcf, col2_dcf, col3_dcf = st.columns(3)
                    col1_dcf.metric("Preço Justo (Modelo PAG)", f"{info.get('currency', '')} {intrinsic_value:.2f}")
                    col2_dcf.metric("Preço Atual de Mercado", f"{current_price:.2f}")
                    col3_dcf.metric("Potencial de Upside/Downside", f"{dcf_upside:.2f}%")
                else: st.warning("Não foi possível calcular o DCF com as premissas atuais.")
            with tab_comps:
                st.subheader("Análise de Múltiplos vs. Pares")
                if not comps_df.empty:
                    st.dataframe(comps_df.set_index('Ativo').style.format(precision=2, na_rep="N/A"), use_container_width=True)
                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        fig_pe = px.bar(comps_df, x='Ativo', y='P/L', title='Comparativo de P/L', text_auto='.2f'); st.plotly_chart(fig_pe, use_container_width=True)
                    with col_c2:
                        fig_ev = px.bar(comps_df, x='Ativo', y='EV/EBITDA', title='Comparativo de EV/EBITDA', text_auto='.2f'); st.plotly_chart(fig_ev, use_container_width=True)
                else: st.info("Insira tickers de concorrentes para ver a análise comparativa.")
            st.divider()

            # SEÇÃO FINAL: GRÁFICO DE PREÇOS E NOTÍCIAS
            st.header("Performance de Mercado e Notícias")
            col_price, col_news = st.columns([2, 1])
            with col_price:
                st.subheader("Histórico de Cotações (5 Anos)")
                hist_df = yf.Ticker(ticker_symbol).history(period="5y")
                fig_price = px.line(hist_df, x=hist_df.index, y="Close", title=f"Preço de Fechamento de {info['shortName']}")
                st.plotly_chart(fig_price, use_container_width=True)
            with col_news:
                st.subheader("Últimas Notícias")
                if news:
                    for item in news[:5]: # Mostra as 5 notícias mais recentes
                        st.markdown(f"[{item.get('title')}]({item.get('link')})")
                        st.caption(f"Fonte: {item.get('publisher')}")
                        st.divider()
                else: st.write("Nenhuma notícia recente encontrada.")
else:
    st.info("Insira um ticker e clique em 'Gerar Relatório Completo' para iniciar a análise.")
