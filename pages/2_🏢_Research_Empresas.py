# pages/2_🏢_Research_Empresas.py (Versão de Depuração para Dados Financeiros)

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import numpy as np

# --- Configuração da Página ---
st.set_page_config(page_title="PAG | Research de Empresas", page_icon="🏢", layout="wide")

# --- FUNÇÕES AUXILIARES ---
# ... (outras funções auxiliares permanecem as mesmas)
def analisar_sentimento(texto):
    texto = texto.lower()
    palavras_positivas = ['crescimento', 'lucro', 'aumento', 'supera', 'expansão', 'forte', 'otimista', 'sucesso', 'melhora', 'compra', 'growth', 'profit', 'increase', 'beats', 'expansion', 'strong', 'optimistic', 'success', 'improves', 'buy', 'upgrade']
    palavras_negativas = ['queda', 'prejuízo', 'redução', 'abaixo', 'contração', 'fraco', 'pessimista', 'falha', 'piora', 'venda', 'fall', 'loss', 'reduction', 'below', 'contraction', 'weak', 'pessimistic', 'fails', 'worsens', 'sell', 'downgrade']
    score = 0; [score := score + 1 for p in palavras_positivas if p in texto]; [score := score - 1 for p in palavras_negativas if p in texto]
    if score > 0: return 'Positivo', '🟢'
    elif score < 0: return 'Negativo', '🔴'
    else: return 'Neutro', '⚪️'
@st.cache_data
def get_key_stats(tickers):
    key_stats = []; [key_stats.append({'Ativo': info.get('symbol'), 'Empresa': info.get('shortName'), 'P/L': info.get('trailingPE'), 'P/VP': info.get('priceToBook'), 'EV/EBITDA': info.get('enterpriseToEbitda'), 'Dividend Yield (%)': info.get('dividendYield', 0) * 100, 'ROE (%)': info.get('returnOnEquity', 0) * 100, 'Margem Bruta (%)': info.get('grossMargins', 0) * 100}) for ticker_symbol in tickers if (info := yf.Ticker(ticker_symbol).info)]
    return pd.DataFrame(key_stats)

# --- FUNÇÃO MODIFICADA PARA DEPURAÇÃO ---
@st.cache_data
def get_financial_data(ticker_symbol):
    """Busca todos os dados financeiros com depuração de erros aprimorada."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        if not info.get('longName'): return None
        
        # Para depuração, podemos exibir as chaves disponíveis
        st.write("Índices do Fluxo de Caixa (Cashflow):", ticker.cashflow.index.tolist())
        st.write("Índices do Balanço Patrimonial (Balance Sheet):", ticker.balance_sheet.index.tolist())

        op_cash_flow = ticker.cashflow.loc['Operating Cash Flow'].iloc[0]
        capex = ticker.cashflow.loc['Capital Expenditure'].iloc[0]
        fcf = op_cash_flow + capex
        total_liab = ticker.balance_sheet.loc['Total Liabilities Net Minority Interest'].iloc[0]
        total_cash = ticker.balance_sheet.loc['Cash And Cash Equivalents'].iloc[0]
        net_debt = total_liab - total_cash
        shares_outstanding = info['sharesOutstanding']
        
        financials = {
            'info': info, 'income_stmt': ticker.income_stmt,
            'balance_sheet': ticker.balance_sheet, 'cash_flow': ticker.cashflow,
            'dcf_data': {
                'fcf': fcf, 'net_debt': net_debt, 
                'shares_outstanding': shares_outstanding, 'ebitda': info.get('ebitda')
            }
        }
        return financials
    except Exception as e:
        # Exibe o erro exato na tela
        st.error(f"Erro detalhado ao buscar dados financeiros em get_financial_data: {e}")
        return None

# (Restante das funções permanece o mesmo)
def calculate_dcf(dcf_data, g, tg, wacc):
    if (wacc - tg) <= 0: return 0
    fcf_proj = [dcf_data['fcf'] * (1 + g)**i for i in range(1, 6)]; terminal_value = (fcf_proj[-1] * (1 + tg)) / (wacc - tg)
    pv_fcf = [fcf_proj[i] / (1 + wacc)**(i+1) for i in range(5)]; pv_terminal_value = terminal_value / (1 + wacc)**5
    enterprise_value = sum(pv_fcf) + pv_terminal_value; equity_value = enterprise_value - dcf_data['net_debt']
    return equity_value / dcf_data['shares_outstanding']
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
        financial_leverage = total_assets / equity; roe = net_profit_margin * asset_turnover * financial_leverage / 100
        return pd.DataFrame({'Margem Líquida (%)': net_profit_margin, 'Giro do Ativo': asset_turnover, 'Alavancagem Financeira': financial_leverage, 'ROE Calculado (%)': roe}).T.sort_index(axis=1)
    except KeyError: return pd.DataFrame()
def calculate_quality_score(info, dcf_data):
    scores = {}; roe = info.get('returnOnEquity', 0) or 0
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
def generate_narrative(scores, info, growth_narrative, margin_narrative):
    quality_score, value_score, momentum_score = scores['quality'], scores['value'], scores['momentum']
    if quality_score >= 85: q_phrase = "uma empresa de excelente qualidade, com fundamentos extremamente sólidos"
    elif quality_score >= 70: q_phrase = "uma empresa de alta qualidade, com fundamentos robustos"
    elif quality_score >= 50: q_phrase = "uma empresa com fundamentos adequados"
    else: q_phrase = f"uma empresa cujos fundamentos requerem cautela"
    if value_score >= 70: v_phrase = "que parece ser negociada a um valuation atrativo"
    elif value_score >= 50: v_phrase = "com um valuation que parece justo"
    else: v_phrase = f"cujo valuation parece esticado nos níveis atuais"
    if momentum_score >= 70: m_phrase = "e que atualmente desfruta de um forte momento de mercado."
    elif momentum_score >= 50: m_phrase = f"com um momento de mercado neutro."
    else: m_phrase = f"apesar de um momento de mercado desafiador."
    tese = f"Nossa análise indica que **{info.get('shortName', 'a empresa')}** é {q_phrase}, {v_phrase} {m_phrase}"
    return tese
@st.cache_data
def analyze_growth(income_stmt, info):
    try:
        revenue_series = income_stmt.loc['Total Revenue'].sort_index()
        start_value = revenue_series.iloc[0]; end_value = revenue_series.iloc[-1]
        num_years = len(revenue_series) - 1
        if start_value > 0 and num_years > 0: cagr = ((end_value / start_value) ** (1 / num_years)) - 1
        else: cagr = 0
        analyst_growth_estimate = info.get('revenueGrowth')
        narrative = f"A companhia demonstrou um crescimento de receita histórico de **{cagr:.2%} ao ano** nos últimos {num_years+1} anos, passando de {start_value/1e9:.2f}B para {end_value/1e9:.2f}B. "
        if analyst_growth_estimate is not None:
            narrative += f"A expectativa de crescimento para o próximo ano, segundo o consenso de analistas, é de **{analyst_growth_estimate:.2%}**, indicando uma potencial {'aceleração' if analyst_growth_estimate > cagr else 'desaceleração'} em relação ao ritmo histórico."
        else: narrative += "Não há estimativas claras do consenso de analistas para o crescimento futuro da receita."
        return narrative
    except Exception: return "Não foi possível gerar a análise de crescimento de receita."
@st.cache_data
def analyze_margins(income_stmt, comps_df):
    try:
        gross_margin_series = (income_stmt.loc['Gross Profit'] / income_stmt.loc['Total Revenue']) * 100
        last_year_margin = gross_margin_series.iloc[-1]; trend = last_year_margin - gross_margin_series.iloc[0]
        if trend > 2: trend_text = "uma clara tendência de expansão"
        elif trend < -2: trend_text = "uma preocupante tendência de contração"
        else: trend_text = "uma tendência de estabilidade"
        peers_margin = comps_df['Margem Bruta (%)'].median() if not comps_df.empty else None
        if peers_margin is not None:
            if last_year_margin > peers_margin * 1.1: peers_text = f"superior à mediana de seus pares ({peers_margin:.1f}%)."
            elif last_year_margin < peers_margin * 0.9: peers_text = f"abaixo da mediana de seus pares ({peers_margin:.1f}%)."
            else: peers_text = f"em linha com a mediana de seus pares ({peers_margin:.1f}%)."
        else: peers_text = "."
        return f"A margem bruta da empresa, atualmente em **{last_year_margin:.1f}%**, exibe {trend_text} e está {peers_text}"
    except Exception: return "Não foi possível gerar a análise de margens."
# --- UI E LÓGICA PRINCIPAL ---
st.title("Painel de Research de Empresas")
# (Resto do código da UI e Lógica Principal mantido)
