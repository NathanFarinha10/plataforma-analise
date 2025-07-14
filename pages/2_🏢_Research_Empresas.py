# pages/2_🏢_Research_Empresas.py (Versão Final com PAG Score Completo)

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import numpy as np

# --- Configuração da Página ---
st.set_page_config(page_title="PAG | Research de Empresas", page_icon="🏢", layout="wide")

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


def generate_narrative(scores, info):
    """Gera uma narrativa analítica com base nos scores calculados."""
    quality_score, value_score, momentum_score = scores['quality'], scores['value'], scores['momentum']
    
    # Frases baseadas nos scores
    # Qualidade
    if quality_score >= 85:
        q_phrase = f"uma empresa de excelente qualidade, com fundamentos extremamente sólidos"
    elif quality_score >= 70:
        q_phrase = f"uma empresa de alta qualidade, com fundamentos robustos"
    elif quality_score >= 50:
        q_phrase = f"uma empresa com fundamentos adequados"
    else:
        q_phrase = f"uma empresa cujos fundamentos requerem cautela"
    
    # Valor
    if value_score >= 70:
        v_phrase = f"que parece ser negociada a um valuation atrativo"
    elif value_score >= 50:
        v_phrase = f"com um valuation que parece justo"
    else:
        v_phrase = f"cujo valuation parece esticado nos níveis atuais"
        
    # Momento
    if momentum_score >= 70:
        m_phrase = f"e que atualmente desfruta de um forte momento de mercado"
    elif momentum_score >= 50:
        m_phrase = f"com um momento de mercado neutro"
    else:
        m_phrase = f"apesar de um momento de mercado desafiador"

    # Constrói a narrativa final
    narrative = f"Nossa análise indica que **{info.get('shortName', 'a empresa')}** é {q_phrase}, {v_phrase} {m_phrase}. "
    
    # Adiciona uma frase de evidência baseada no ponto mais forte
    strongest_point = max(scores, key=scores.get)
    if strongest_point == 'quality':
        narrative += f"Sua alta rentabilidade, evidenciada por um ROE de **{info.get('returnOnEquity', 0) * 100:.1f}%**, é um diferencial chave."
    elif strongest_point == 'value' and scores['value'] > 50:
        upside = info.get('dcf_upside', 0)
        narrative += f"O potencial de upside de **{upside:.1f}%** em nosso modelo DCF sugere uma margem de segurança considerável."
    elif strongest_point == 'momentum' and scores['momentum'] > 50:
        narrative += "Seu forte desempenho relativo contra o índice de referência confirma o interesse do mercado no ativo."
        
    return narrative

@st.cache_data
def analyze_growth(income_stmt, info):
    """Gera uma análise narrativa sobre o crescimento da receita."""
    try:
        # Pega a série histórica de receitas e ordena do mais antigo para o mais novo
        revenue_series = income_stmt.loc['Total Revenue'].sort_index()
        
        # Calcula o CAGR (Taxa de Crescimento Anual Composta) dos últimos anos
        start_value = revenue_series.iloc[0]
        end_value = revenue_series.iloc[-1]
        num_years = len(revenue_series) - 1
        
        if start_value > 0 and num_years > 0:
            cagr = ((end_value / start_value) ** (1 / num_years)) - 1
        else:
            cagr = 0

        # Pega a estimativa de crescimento de receita do próximo ano (se disponível)
        analyst_growth_estimate = info.get('revenueGrowth', None)

        # Constrói a narrativa
        narrative = f"A companhia demonstrou um crescimento de receita histórico de **{cagr:.2%} ao ano** nos últimos {num_years+1} anos, passando de {start_value/1e9:.2f}B para {end_value/1e9:.2f}B. "
        
        if analyst_growth_estimate is not None:
            narrative += f"A expectativa de crescimento para o próximo ano, segundo o consenso de analistas, é de **{analyst_growth_estimate:.2%}**, indicando uma potencial {'aceleração' if analyst_growth_estimate > cagr else 'desaceleração'} em relação ao ritmo histórico."
        else:
            narrative += "Não há estimativas claras do consenso de analistas para o crescimento futuro da receita."
            
        return narrative
    except Exception:
        return "Não foi possível gerar a análise de crescimento de receita. Dados históricos podem estar incompletos."

@st.cache_data
def analyze_margins(income_stmt, info, comps_df):
    """Gera uma análise narrativa sobre as margens da empresa."""
    try:
        # Pega a série histórica de margens
        gross_margin_series = (income_stmt.loc['Gross Profit'] / income_stmt.loc['Total Revenue']) * 100
        
        # Análise da Tendência
        first_year_margin = gross_margin_series.iloc[0]
        last_year_margin = gross_margin_series.iloc[-1]
        trend = last_year_margin - first_year_margin
        
        if trend > 2: # Melhoria de mais de 2 pontos percentuais
            trend_text = "uma clara tendência de expansão, "
        elif trend < -2:
            trend_text = "uma preocupante tendência de contração, "
        else:
            trend_text = "uma tendência de estabilidade, "
            
        # Comparação com Pares
        peers_margin = comps_df['Margem Bruta (%)'].median()
        if peers_margin > 0:
            if last_year_margin > peers_margin * 1.1: # 10% acima da mediana
                peers_text = f"e opera com margens significativamente superiores à mediana de seus pares ({peers_margin:.1f}%)."
            elif last_year_margin < peers_margin * 0.9: # 10% abaixo da mediana
                peers_text = f"porém opera com margens abaixo da mediana de seus pares ({peers_margin:.1f}%)."
            else:
                peers_text = f"e opera com margens em linha com a mediana de seus pares ({peers_margin:.1f}%)."
        else:
            peers_text = "."

        # Constrói a narrativa final
        narrative = f"A margem bruta da empresa, atualmente em **{last_year_margin:.1f}%**, exibe {trend_text} {peers_text}"
        
        return narrative
    except Exception:
        return "Não foi possível gerar a análise de margens. Dados históricos podem estar incompletos."

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
        last_price = data[ticker_symbol].iloc[-1]
        last_sma200 = data['SMA200'].iloc[-1]
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

st.sidebar.header("Filtros de Análise"); ticker_symbol = st.sidebar.text_input("Ticker Principal", "AAPL").upper()
peers_string = st.sidebar.text_area("Tickers dos Concorrentes (para Comps)", "MSFT, GOOG, AMZN").upper()
st.sidebar.subheader("Premissas do Modelo DCF"); growth_rate = st.sidebar.number_input("Taxa de Crescimento do FCF (anual %)", value=5.0, step=0.5, format="%.1f") / 100
terminal_growth_rate = st.sidebar.number_input("Taxa de Perpetuidade (%)", value=2.5, step=0.1, format="%.1f") / 100
wacc_rate = st.sidebar.number_input("Taxa de Desconto (WACC %)", value=9.0, step=0.5, format="%.1f") / 100

analyze_button = st.sidebar.button("Analisar")

if analyze_button:
    if not ticker_symbol:
        st.warning("Por favor, digite um ticker principal para analisar.")
    else:
        info = yf.Ticker(ticker_symbol).info
        if not info.get('longName'):
            st.error(f"Ticker '{ticker_symbol}' não encontrado ou inválido.")
        else:
            with st.spinner("Analisando... Este processo pode levar um momento."):
                dcf_data = get_dcf_data_from_yf(ticker_symbol)
                peer_tickers = [p.strip() for p in peers_string.split(",")] if peers_string else []
                comps_df = get_key_stats(peer_tickers)

           # SUBSTITUA O BLOCO DA SEÇÃO DE RATING POR ESTE

            # --- SEÇÃO 1: RATING PROPRIETÁRIO E NARRATIVA ---
            st.header(f"Análise de {info['longName']} ({info['symbol']})")
            st.subheader(f"Rating Proprietário (PAG Score) & Tese de Investimento")
            
            # Calcula os dados necessários ANTES de exibir
            dcf_upside = None
            if dcf_data:
                intrinsic_value = calculate_dcf(fcf=dcf_data['fcf'], net_debt=dcf_data['net_debt'], shares_outstanding=dcf_data['shares_outstanding'], g=growth_rate, tg=terminal_growth_rate, wacc=wacc_rate)
                current_price = info.get('currentPrice')
                if current_price and intrinsic_value > 0:
                    dcf_upside = ((intrinsic_value / current_price) - 1) * 100
                    info['dcf_upside'] = dcf_upside # Adiciona ao dicionário info para uso na narrativa
            
            # Calcula os scores
            quality_score, quality_breakdown = calculate_quality_score(info, dcf_data)
            quality_rating, quality_emoji = get_rating_from_score(quality_score)
            
            value_score, value_breakdown = calculate_value_score(info, comps_df, dcf_upside)
            value_rating, value_emoji = get_rating_from_score(value_score)
            
            momentum_score, momentum_breakdown = calculate_momentum_score(ticker_symbol)
            momentum_rating, momentum_emoji = get_rating_from_score(momentum_score)
            
            # Exibe os scores
            col1_rat, col2_rat, col3_rat = st.columns(3)
            with col1_rat:
                st.metric("Qualidade", f"{quality_rating} {quality_emoji}", f"{quality_score:.0f} / 100")
                with st.expander("Ver detalhes"): st.write(quality_breakdown)
            with col2_rat:
                st.metric("Valor (Value)", f"{value_rating} {value_emoji}", f"{value_score:.0f} / 100")
                with st.expander("Ver detalhes"): st.write(value_breakdown)
            with col3_rat:
                st.metric("Momento", f"{momentum_rating} {momentum_emoji}", f"{momentum_score:.0f} / 100")
                with st.expander("Ver detalhes"): st.write(momentum_breakdown)
            
            # Gera e exibe a narrativa
            scores = {'quality': quality_score, 'value': value_score, 'momentum': momentum_score}
            narrative = generate_narrative(scores, info)
            st.info(f"**Tese de Investimento:** \"{narrative}\"")
            st.divider()

            st.subheader("Consenso de Mercado (Wall Street)")
            recommendation = info.get('recommendationKey', 'N/A'); target_price = info.get('targetMeanPrice', 0); current_price = info.get('currentPrice', 0); analyst_count = info.get('numberOfAnalystOpinions', 0)
            col1_cons, col2_cons, col3_cons, col4_cons = st.columns(4)
            col1_cons.metric("Recomendação Média", recommendation.upper() if recommendation != 'N/A' else 'N/A')
            col2_cons.metric("Preço-Alvo Médio", f"{target_price:.2f}" if target_price > 0 else "N/A")
            if target_price > 0 and current_price > 0:
                upside_consensus = ((target_price / current_price) - 1) * 100
                col3_cons.metric("Upside do Consenso", f"{upside_consensus:.2f}%")
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
           
            # --- CAPÍTULO: CRESCIMENTO DE RECEITA ---
            st.subheader("Crescimento de Receita")
            with st.spinner("Analisando tendências de receita..."):
                # Reutiliza o DRE já buscado para a análise histórica
                income_statement_data = yf.Ticker(ticker_symbol).income_stmt
                growth_narrative = analyze_growth(income_statement_data, info)
                st.write(growth_narrative)
            
            st.divider()
            
            # --- CAPÍTULO: MARGEM BRUTA ---
            st.subheader("Margem Bruta")
            with st.spinner("Analisando tendências de margem..."):
                # Reutiliza os dados já buscados
                margin_narrative = analyze_margins(income_statement, info, comps_df)
                st.write(margin_narrative)
            
            st.divider()
            
            st.header("Análise Financeira Histórica e DuPont")
            ticker_obj = yf.Ticker(ticker_symbol)
            income_statement = ticker_obj.income_stmt
            balance_sheet = ticker_obj.balance_sheet
            cash_flow = ticker_obj.cashflow
            tab_dre, tab_bp, tab_fcf, tab_dupont = st.tabs(["Resultados (DRE)", "Balanço (BP)", "Fluxo de Caixa (FCF)", "🔥 Análise DuPont"])
            with tab_dre:
                st.subheader("Evolução da Receita e Lucro"); dre_items = ['Total Revenue', 'Gross Profit', 'Operating Income', 'Net Income']
                dre_df = income_statement[income_statement.index.isin(dre_items)]; plot_financial_statement(dre_df, "Demonstração de Resultados Anual")
            with tab_bp:
                st.subheader("Evolução dos Ativos e Passivos"); bp_items = ['Total Assets', 'Total Liabilities Net Minority Interest', 'Stockholders Equity']
                bp_df = balance_sheet[balance_sheet.index.isin(bp_items)]; plot_financial_statement(bp_df, "Balanço Patrimonial Anual")
            with tab_fcf:
                st.subheader("Evolução dos Fluxos de Caixa"); fcf_items = ['Operating Cash Flow', 'Investing Cash Flow', 'Financing Cash Flow', 'Free Cash Flow']
                fcf_items_available = [item for item in fcf_items if item in cash_flow.index]
                fcf_df = cash_flow[cash_flow.index.isin(fcf_items_available)]; plot_financial_statement(fcf_df, "Fluxo de Caixa Anual")
            with tab_dupont:
                st.subheader("Decomposição do ROE (Return on Equity)")
                dupont_df = calculate_dupont_analysis(income_statement, balance_sheet)
                if not dupont_df.empty:
                    st.dataframe(dupont_df.style.format("{:.2f}"), use_container_width=True)
                    df_plot = dupont_df.T.sort_index(); df_plot.index = df_plot.index.year
                    fig_dupont = px.line(df_plot, markers=True, title="Evolução dos Componentes do ROE")
                    fig_dupont.update_layout(xaxis_title="Ano", yaxis_title="Valor / Múltiplo", legend_title="Componentes"); st.plotly_chart(fig_dupont, use_container_width=True)
                    st.caption("ROE = (Margem Líquida) x (Giro do Ativo) x (Alavancagem Financeira)")
                else: st.warning("Não foi possível calcular a Análise DuPont.")
            
            st.header("Análise Comparativa de Múltiplos (Comps)")
            if peers_string:
                if not comps_df.empty:
                    metric_cols = ['P/L', 'P/VP', 'EV/EBITDA', 'Dividend Yield (%)', 'ROE (%)', 'Margem Bruta (%)']
                    for col in metric_cols: comps_df[col] = pd.to_numeric(comps_df[col], errors='coerce')
                    formatter = {col: "{:.2f}" for col in metric_cols}
                    st.dataframe(comps_df.set_index('Ativo').style.format(formatter, na_rep="N/A"), use_container_width=True)
                    st.subheader("Visualização dos Múltiplos")
                    col_chart1, col_chart2 = st.columns(2)
                    with col_chart1: fig_pe = px.bar(comps_df, x='Ativo', y='P/L', title='Comparativo de P/L', text_auto='.2f'); st.plotly_chart(fig_pe, use_container_width=True)
                    with col_chart2: fig_ev = px.bar(comps_df, x='Ativo', y='EV/EBITDA', title='Comparativo de EV/EBITDA', text_auto='.2f'); st.plotly_chart(fig_ev, use_container_width=True)
                else: st.warning("Não foi possível buscar dados para a análise comparativa.")
            else: st.info("Insira tickers de concorrentes na barra lateral para ver a análise comparativa.")
            
            st.header(f"Valuation por DCF (Modelo Proprietário)")
            if dcf_data and intrinsic_value > 0:
                st.subheader("Resultado do Valuation")
                col1_dcf, col2_dcf, col3_dcf = st.columns(3)
                col1_dcf.metric("Preço Justo (Valor Intrínseco)", f"{info.get('currency', '')} {intrinsic_value:.2f}")
                col2_dcf.metric("Preço Atual de Mercado", f"{info.get('currency', '')} {current_price:.2f}")
                col3_dcf.metric("Potencial de Upside/Downside", f"{dcf_upside:.2f}%")
                if dcf_upside > 20: st.success(f"RECOMENDAÇÃO (MODELO PAG): COMPRAR")
                elif dcf_upside < -20: st.error(f"RECOMENDAÇÃO (MODELO PAG): VENDER")
                else: st.warning(f"RECOMENDAÇÃO (MODELO PAG): MANTER")

            st.header("Histórico de Cotações")
            hist_df = yf.Ticker(ticker_symbol).history(period="5y")
            fig_price = px.line(hist_df, x=hist_df.index, y="Close", title=f"Preço de Fechamento de {info['shortName']}", labels={'Close': f'Preço ({info["currency"]})', 'Date': 'Data'})
            st.plotly_chart(fig_price, use_container_width=True)

            st.header("Notícias Recentes e Análise de Sentimento")
            news = yf.Ticker(ticker_symbol).news
            if news:
                for item in news:
                    content = item.get('content', {});
                    if not content: continue
                    titulo = content.get('title')
                    if not titulo: continue
                    provider = item.get('provider', {}); publisher = provider.get('displayName', 'Não Informado')
                    link = item.get('canonicalUrl', {}).get('url'); sentimento, icone = analisar_sentimento(titulo)
                    with st.expander(f"{icone} {titulo}"):
                        st.markdown(f"**Publicado por:** {publisher}"); st.markdown(f"**Sentimento:** {sentimento}")
                        if link: st.link_button("Ler notícia completa", link)
            else: st.write("Nenhuma notícia recente encontrada para esta ação.")
else:
    st.info("Insira um ticker e clique em 'Analisar' para ver a análise completa.")
