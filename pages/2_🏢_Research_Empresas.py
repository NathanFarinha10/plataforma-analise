# pages/2_🏢_Research_Empresas.py (Versão com Análise DuPont)

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import numpy as np

# --- Configuração da Página ---
st.set_page_config(page_title="PAG | Research de Empresas", page_icon="🏢", layout="wide")

# --- FUNÇÕES AUXILIARES ---

# (As funções analisar_sentimento, get_key_stats, get_dcf_data_from_yf, calculate_dcf permanecem as mesmas)
def analisar_sentimento(texto):
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
    df_plot = df.T.sort_index()
    df_plot.index = df_plot.index.year
    fig = px.bar(df_plot, barmode='group', title=title, text_auto='.2s')
    fig.update_layout(xaxis_title="Ano", yaxis_title="Valor")
    st.plotly_chart(fig, use_container_width=True)

# --- NOVA FUNÇÃO PARA A ANÁLISE DUPONT ---
@st.cache_data
def calculate_dupont_analysis(income_stmt, balance_sheet):
    """Calcula os componentes da Análise DuPont para os anos disponíveis."""
    try:
        # Extrai os dados necessários
        net_income = income_stmt.loc['Net Income']
        revenue = income_stmt.loc['Total Revenue']
        total_assets = balance_sheet.loc['Total Assets']
        equity = balance_sheet.loc['Stockholders Equity']

        # Calcula os componentes
        net_profit_margin = (net_income / revenue) * 100
        asset_turnover = revenue / total_assets
        financial_leverage = total_assets / equity
        
        # Calcula o ROE (como verificação)
        roe = net_profit_margin * asset_turnover * financial_leverage / 100

        # Monta o DataFrame
        dupont_df = pd.DataFrame({
            'Margem Líquida (%)': net_profit_margin,
            'Giro do Ativo': asset_turnover,
            'Alavancagem Financeira': financial_leverage,
            'ROE Calculado (%)': roe
        }).T.sort_index(axis=1) # Garante que os anos estejam em ordem

        return dupont_df
    except KeyError:
        return pd.DataFrame() # Retorna DF vazio se alguma conta não for encontrada

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
            # --- SEÇÕES EXISTENTES (VISÃO GERAL, COMPS, DCF, etc.) ---
            st.header(f"Visão Geral de: {info['longName']} ({info['symbol']})")
            # ... (código da visão geral)

            # --- ANÁLISE HISTÓRICA E DUPONT ---
            st.header("Análise Financeira Histórica e DuPont")
            with st.spinner("Buscando demonstrações financeiras anuais..."):
                ticker_obj = yf.Ticker(ticker_symbol)
                income_statement = ticker_obj.income_stmt
                balance_sheet = ticker_obj.balance_sheet
                cash_flow = ticker_obj.cashflow

                tab_dre, tab_bp, tab_fcf, tab_dupont = st.tabs(["Resultados (DRE)", "Balanço (BP)", "Fluxo de Caixa (FCF)", "🔥 Análise DuPont"])
                
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
                    fcf_items_available = [item for item in fcf_items if item in cash_flow.index]
                    fcf_df = cash_flow[cash_flow.index.isin(fcf_items_available)]
                    plot_financial_statement(fcf_df, "Fluxo de Caixa Anual")
                
                # --- NOVA ABA: ANÁLISE DUPONT ---
                with tab_dupont:
                    st.subheader("Decomposição do ROE (Return on Equity)")
                    dupont_df = calculate_dupont_analysis(income_statement, balance_sheet)
                    
                    if not dupont_df.empty:
                        # Exibe a tabela com os dados
                        st.dataframe(dupont_df.style.format("{:.2f}"), use_container_width=True)
                        
                        # Prepara os dados para o gráfico de linhas
                        df_plot = dupont_df.T.sort_index()
                        df_plot.index = df_plot.index.year
                        
                        fig_dupont = px.line(df_plot, markers=True,
                                             title="Evolução dos Componentes do ROE (Análise DuPont)")
                        fig_dupont.update_layout(xaxis_title="Ano", yaxis_title="Valor / Múltiplo",
                                                 legend_title="Componentes")
                        st.plotly_chart(fig_dupont, use_container_width=True)
                        st.caption("A Análise DuPont decompõe o ROE em: Lucratividade (Margem Líquida), Eficiência (Giro do Ativo) e Risco (Alavancagem Financeira).")
                    else:
                        st.warning("Não foi possível calcular a Análise DuPont. Dados financeiros necessários podem estar faltando.")

            # --- O restante das seções (Comps, DCF, etc.) continua aqui ---
            # ... (código omitido para manter a clareza, mas está no seu arquivo)
            # ...
else:
    st.info("Insira um ticker e clique em 'Analisar' para ver a análise completa.")
