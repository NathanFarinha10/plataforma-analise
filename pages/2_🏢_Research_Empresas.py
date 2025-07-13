# pages/2_🏢_Research_Empresas.py (Versão com Análise Histórica)

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import numpy as np

# --- Configuração da Página ---
st.set_page_config(page_title="PAG | Research de Empresas", page_icon="🏢", layout="wide")

# --- FUNÇÕES AUXILIARES ---

def analisar_sentimento(texto):
    # (código da função de sentimento permanece o mesmo)
    texto = texto.lower()
    palavras_positivas = ['crescimento', 'lucro', 'aumento', 'supera', 'expansão', 'forte', 'otimista', 'sucesso', 'melhora', 'compra',
                          'growth', 'profit', 'increase', 'beats', 'expansion', 'strong', 'optimistic', 'success', 'improves', 'buy', 'upgrade']
    palavras_negativas = ['queda', 'prejuízo', 'redução', 'abaixo', 'contração', 'fraco', 'pessimista', 'falha', 'piora', 'venda',
                          'fall', 'loss', 'reduction', 'below', 'contraction', 'weak', 'pessimistic', 'fails', 'worsens', 'sell', 'downgrade']
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
    # (código da função de comps permanece o mesmo)
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
    # (código da função de DCF permanece o mesmo)
    try:
        ticker = yf.Ticker(ticker_symbol)
        cash_flow = ticker.cashflow
        balance_sheet = ticker.balance_sheet
        info = ticker.info
        op_cash_flow = cash_flow.loc['Operating Cash Flow'].iloc[0]
        capex = cash_flow.loc['Capital Expenditure'].iloc[0]
        fcf = op_cash_flow + capex
        total_liab = balance_sheet.loc['Total Liabilities Net Minority Interest'].iloc[0]
        total_cash = balance_sheet.loc['Cash And Cash Equivalents'].iloc[0]
        net_debt = total_liab - total_cash
        shares_outstanding = info['sharesOutstanding']
        return {'fcf': fcf, 'net_debt': net_debt, 'shares_outstanding': shares_outstanding}
    except Exception:
        return None

def calculate_dcf(fcf, net_debt, shares_outstanding, g, tg, wacc):
    # (código da função de DCF permanece o mesmo)
    if (wacc - tg) <= 0: return 0
    fcf_proj = [fcf * (1 + g)**i for i in range(1, 6)]
    terminal_value = (fcf_proj[-1] * (1 + tg)) / (wacc - tg)
    pv_fcf = [fcf_proj[i] / (1 + wacc)**(i+1) for i in range(5)]
    pv_terminal_value = terminal_value / (1 + wacc)**5
    enterprise_value = sum(pv_fcf) + pv_terminal_value
    equity_value = enterprise_value - net_debt
    return equity_value / shares_outstanding

def plot_financial_statement(df, title):
    """Função para plotar um gráfico de barras de uma demonstração financeira."""
    df_plot = df.T # Transpõe para ter anos no eixo X
    df_plot.index = df_plot.index.year # Usa apenas o ano como label
    fig = px.bar(df_plot, barmode='group', title=title)
    fig.update_layout(xaxis_title="Ano", yaxis_title="Valor")
    st.plotly_chart(fig, use_container_width=True)

# --- UI E LÓGICA PRINCIPAL ---
st.title("Painel de Research de Empresas")
st.markdown("Analise ações individuais, compare com pares e calcule o valor intrínseco.")

st.sidebar.header("Filtros de Análise")
ticker_symbol = st.sidebar.text_input("Ticker Principal", "AAPL").upper()
peers_string = st.sidebar.text_area("Tickers dos Concorrentes (para Comps)", "MSFT, GOOG, AMZN").upper()

st.sidebar.subheader("Premissas do Modelo DCF")
growth_rate = st.sidebar.number_input("Taxa de Crescimento do FCF (anual %)", value=5.0, step=0.5, format="%.1f") / 100
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
            # --- SEÇÃO 1: VISÃO GERAL ---
            st.header(f"Visão Geral de: {info['longName']} ({info['symbol']})")
            # (código da visão geral mantido)
            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("País", info.get('country', 'N/A')); st.metric("Setor", info.get('sector', 'N/A'))
            with col2: st.metric("Moeda", info.get('currency', 'N/A')); st.metric("Preço Atual", f"{info.get('currentPrice', 0):.2f}")
            with col3: st.metric("P/L", f"{info.get('trailingPE', 0):.2f}"); st.metric("P/VP", f"{info.get('priceToBook', 0):.2f}")
            with col4: st.metric("Dividend Yield", f"{info.get('dividendYield', 0) * 100:.2f}%"); st.metric("Beta", f"{info.get('beta', 0):.2f}")
            with st.expander("Descrição da Empresa"): st.write(info.get('longBusinessSummary', 'Descrição não disponível.'))

            # --- NOVA SEÇÃO: ANÁLISE HISTÓRICA ---
            st.header("Análise Financeira Histórica")
            with st.spinner("Buscando demonstrações financeiras anuais..."):
                ticker_obj = yf.Ticker(ticker_symbol)
                income_statement = ticker_obj.income_stmt
                balance_sheet = ticker_obj.balance_sheet
                cash_flow = ticker_obj.cashflow

                tab_dre, tab_bp, tab_fcf = st.tabs(["Demonstração de Resultados (DRE)", "Balanço Patrimonial (BP)", "Fluxo de Caixa (FCF)"])
                
                with tab_dre:
                    st.subheader("Evolução da Receita e Lucro")
                    dre_items = ['Total Revenue', 'Gross Profit', 'Operating Income', 'Net Income']
                    dre_df = income_statement[income_statement.index.isin(dre_items)]
                    plot_financial_statement(dre_df, "Demonstração de Resultados Anual")

                with tab_bp:
                    st.subheader("Evolução dos Ativos e Passivos")
                    bp_items = ['Total Assets', 'Total Liabilities Net Minority Interest', 'Stockholders Equity']
                    bp_df = balance_sheet[balance_sheet.index.isin(bp_items)]
                    plot_financial_statement(bp_df, "Balanço Patrimonial Anual")

                with tab_fcf:
                    st.subheader("Evolução dos Fluxos de Caixa")
                    fcf_items = ['Operating Cash Flow', 'Investing Cash Flow', 'Financing Cash Flow', 'Free Cash Flow']
                    # Free Cash Flow pode não estar disponível em todos os casos, adicionamos tratamento de erro
                    fcf_items_available = [item for item in fcf_items if item in cash_flow.index]
                    fcf_df = cash_flow[cash_flow.index.isin(fcf_items_available)]
                    plot_financial_statement(fcf_df, "Fluxo de Caixa Anual")
            
            # --- SEÇÕES EXISTENTES (COMPS, DCF, etc.) ---
            # (O restante do código para as outras seções é mantido como estava)
            st.header("Análise Comparativa de Múltiplos (Comps)")
            peer_tickers = [p.strip() for p in peers_string.split(",")] if peers_string else []
            if peer_tickers:
                all_tickers = [ticker_symbol] + peer_tickers
                with st.spinner("Buscando dados dos concorrentes..."):
                    comps_df = get_key_stats(all_tickers)
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
            
            st.header(f"Valuation por DCF: {ticker_symbol}")
            with st.spinner("Buscando dados financeiros e calculando o DCF..."):
                dcf_data = get_dcf_data_from_yf(ticker_symbol)
                if dcf_data:
                    intrinsic_value = calculate_dcf(fcf=dcf_data['fcf'], net_debt=dcf_data['net_debt'], shares_outstanding=dcf_data['shares_outstanding'], g=growth_rate, tg=terminal_growth_rate, wacc=wacc_rate)
                    current_price = info.get('currentPrice')
                    if current_price and intrinsic_value > 0:
                        upside = ((intrinsic_value / current_price) - 1) * 100
                        st.subheader("Resultado do Valuation")
                        col1_dcf, col2_dcf, col3_dcf = st.columns(3)
                        col1_dcf.metric("Preço Justo (Valor Intrínseco)", f"{info.get('currency', '')} {intrinsic_value:.2f}")
                        col2_dcf.metric("Preço Atual de Mercado", f"{info.get('currency', '')} {current_price:.2f}")
                        col3_dcf.metric("Potencial de Upside/Downside", f"{upside:.2f}%")
                        if upside > 20: st.success(f"RECOMENDAÇÃO: COMPRAR...")
                        elif upside < -20: st.error(f"RECOMENDAÇÃO: VENDER...")
                        else: st.warning(f"RECOMENDAÇÃO: MANTER...")
            
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
                        if link: st.link_button("Ler Artigo Completo ↗️", link)
            else: st.write("Nenhuma notícia recente encontrada para esta ação.")

else:
    st.info("Insira um ticker e clique em 'Analisar' para ver a análise completa.")
