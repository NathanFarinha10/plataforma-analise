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
            stats = {
                'Ativo': info.get('symbol'), 'Empresa': info.get('shortName'), 
                'P/L': info.get('trailingPE'), 'P/VP': info.get('priceToBook'), 
                'Margem Bruta (%)': info.get('grossMargins', 0) * 100
            }
            key_stats.append(stats)
        except Exception: continue
    return pd.DataFrame(key_stats)

def plot_financial_statement(df, title):
    """Plota um gráfico de barras para uma demonstração financeira."""
    df_plot = df.T.sort_index(); df_plot.index = df_plot.index.year
    fig = px.bar(df_plot, barmode='group', title=title, text_auto='.2s')
    fig.update_layout(xaxis_title="Ano", yaxis_title="Valor", legend_title="Métrica"); st.plotly_chart(fig, use_container_width=True)

@st.cache_data
def calculate_dupont_analysis(income_stmt, balance_sheet):
    """Calcula os componentes da Análise DuPont."""
    try:
        net_income = income_stmt.loc['Net Income']; revenue = income_stmt.loc['Total Revenue']
        total_assets = balance_sheet.loc['Total Assets']; equity = balance_sheet.loc['Stockholders Equity']
        net_profit_margin = (net_income / revenue) * 100; asset_turnover = revenue / total_assets
        financial_leverage = total_assets / equity; roe = net_profit_margin * asset_turnover * financial_leverage / 100
        return pd.DataFrame({'Margem Líquida (%)': net_profit_margin, 'Giro do Ativo': asset_turnover, 'Alavancagem Financeira': financial_leverage, 'ROE Calculado (%)': roe}).T.sort_index(axis=1)
    except KeyError: return pd.DataFrame()

# --- FUNÇÕES DE ANÁLISE NARRATIVA ---

@st.cache_data
def analyze_sector(info, comps_df):
    """Gera uma análise contextual do setor da empresa."""
    try:
        sector = info.get('sector', 'não especificado')
        industry = info.get('industry', 'não especificada')
        narrative = f"A **{info.get('shortName')}** atua no setor de **{sector}**, dentro da indústria de **{industry}**. "
        
        if not comps_df.empty:
            peers_pe = comps_df['P/L'].median()
            company_pe = info.get('trailingPE')
            if peers_pe and company_pe:
                narrative += f"Atualmente, o setor negocia a um P/L mediano de **{peers_pe:.1f}x**. Com um P/L de **{company_pe:.1f}x**, a empresa está sendo negociada "
                if company_pe > peers_pe * 1.1: narrative += "**com um prêmio** em relação aos seus pares."
                elif company_pe < peers_pe * 0.9: narrative += "**com um desconto** em relação aos seus pares."
                else: narrative += "**em linha** com seus pares."
        return narrative
    except Exception: return "Não foi possível gerar a análise setorial."

@st.cache_data
def analyze_metric_trend(financial_statement, metric_name, unit='B', is_margin=False, higher_is_better=True, statement_name='relatório'):
    """Função genérica para analisar a tendência de uma métrica financeira."""
    try:
        series = financial_statement.loc[metric_name].sort_index()
        start_value = series.iloc[0]; end_value = series.iloc[-1]
        num_years = len(series)
        
        if pd.isna(start_value) or pd.isna(end_value): return f"Dados insuficientes para analisar '{metric_name}'."
        
        trend_abs = end_value - start_value
        trend_rel = (trend_abs / abs(start_value)) * 100 if start_value != 0 else 0
        
        if trend_abs > 0:
            trend_text = f"uma tendência de **crescimento ({trend_rel:+.1f}%)**" if higher_is_better else f"uma tendência de **aumento ({trend_rel:+.1f}%)**, o que requer atenção"
        elif trend_abs < 0:
            trend_text = f"uma tendência de **contração ({trend_rel:.1f}%)**, o que requer atenção" if higher_is_better else f"uma tendência de **redução ({trend_rel:.1f}%)**, um sinal positivo"
        else:
            trend_text = "uma tendência de **estabilidade**"
            
        if is_margin: value_text = f"de {start_value:.2%} para **{end_value:.2%}**"
        elif unit == 'B': value_text = f"de {start_value/1e9:.2f}B para **{end_value/1e9:.2f}B**"
        elif unit == 'dólares': value_text = f"de ${start_value:.2f} para **${end_value:.2f}**"
        else: value_text = f"de {start_value/1e6:.2f}M para **{end_value/1e6:.2f}M**"
            
        return f"Nos últimos {num_years} anos, a métrica exibiu {trend_text}, passando {value_text}."
    except KeyError:
        return f"Dados para '{metric_name}' não encontrados no {statement_name}."
    except Exception:
        return "Não foi possível analisar a tendência da métrica."

@st.cache_data
def analyze_roic(income_stmt, balance_sheet):
    """Calcula e analisa o Retorno sobre o Capital Investido (ROIC)."""
    try:
        ebit = income_stmt.loc['EBIT'] if 'EBIT' in income_stmt.index else income_stmt.loc['Operating Income']
        tax_provision = income_stmt.loc['Tax Provision']
        pretax_income = income_stmt.loc['Pretax Income']
        tax_rate = (tax_provision / pretax_income).fillna(0)
        nopat = ebit * (1 - tax_rate)
        
        total_debt = balance_sheet.loc['Total Debt'] if 'Total Debt' in balance_sheet.index else balance_sheet.loc['Total Liabilities Net Minority Interest']
        equity = balance_sheet.loc['Stockholders Equity']
        cash = balance_sheet.loc['Cash And Cash Equivalents']
        invested_capital = total_debt + equity - cash
        
        roic = (nopat / invested_capital) * 100
        last_roic = roic.iloc[-1]
        
        if last_roic > 15: judgment = "um **excelente** nível de retorno, indicando uma forte vantagem competitiva e criação de valor."
        elif last_roic > 10: judgment = "um **bom** nível de retorno, sugerindo uma alocação de capital eficiente."
        else: judgment = "um nível de retorno **modesto**, que merece um olhar mais atento sobre a eficiência dos investimentos futuros."

        return f"O Retorno sobre o Capital Investido (ROIC) mais recente foi de **{last_roic:.1f}%**, o que consideramos {judgment}"
    except Exception:
        return "Não foi possível calcular o ROIC. Dados necessários podem estar faltando."

# --- UI E LÓGICA PRINCIPAL ---
st.title("Relatório de Análise de Ações")
st.markdown("Uma análise completa combinando dados quantitativos e narrativas analíticas.")
st.sidebar.header("Filtros de Análise"); ticker_symbol = st.sidebar.text_input("Ticker Principal", "MSFT").upper()
peers_string = st.sidebar.text_area("Tickers dos Concorrentes", "AAPL, GOOG, AMZN").upper()

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

            st.header(f"Relatório de Análise: {info.get('longName', ticker_symbol)}")
            
            # --- CAPÍTULO 1: SUMÁRIO E HIGHLIGHTS (Placeholders) ---
            st.subheader("Sumário Executivo e Highlights")
            st.info("Em breve: Um resumo com os principais pontos positivos, negativos e a tese de investimento final.")
            st.divider()

            # --- CAPÍTULO 2: ANÁLISE SETORIAL ---
            st.subheader("Contexto Setorial")
            st.write(analyze_sector(info, comps_df))
            st.divider()

            # --- CAPÍTULOS NARRATIVOS DAS MÉTRICAS ---
            st.subheader("Análise Detalhada da Performance Financeira")
            
            with st.container(border=True):
                st.markdown("**Crescimento de Receita**")
                st.write(analyze_metric_trend(income_statement, 'Total Revenue', statement_name="DRE"))
            
            with st.container(border=True):
                st.markdown("**Margem Bruta**")
                income_statement['Gross Margin'] = income_statement['Gross Profit'] / income_statement['Total Revenue']
                st.write(analyze_metric_trend(income_statement, 'Gross Margin', is_margin=True, statement_name="DRE"))

            with st.container(border=True):
                st.markdown("**Margem Operacional**")
                income_statement['Operating Margin'] = income_statement['Operating Income'] / income_statement['Total Revenue']
                st.write(analyze_metric_trend(income_statement, 'Operating Margin', is_margin=True, statement_name="DRE"))
            
            with st.container(border=True):
                st.markdown("**Lucro por Ação (EPS)**")
                st.write(analyze_metric_trend(income_statement, 'Basic EPS', unit='dólares', is_margin=True, statement_name="DRE"))

            with st.container(border=True):
                st.markdown("**Fluxo de Caixa Livre (FCF)**")
                st.write(analyze_metric_trend(cash_flow, 'Free Cash Flow', statement_name="Fluxo de Caixa"))
            
            with st.container(border=True):
                st.markdown("**Retorno sobre o Capital Investido (ROIC)**")
                st.write(analyze_roic(income_statement, balance_sheet))
            
            with st.container(border=True):
                st.markdown("**Dívida Líquida**")
                balance_sheet['Net Debt'] = balance_sheet.get('Total Debt', 0) - balance_sheet.get('Cash And Cash Equivalents', 0)
                st.write(analyze_metric_trend(balance_sheet, 'Net Debt', higher_is_better=False, statement_name="Balanço"))

            st.divider()
            
            # --- SEÇÃO DE GRÁFICOS DETALHADOS ---
            st.header("Análise Financeira Gráfica")
            tab_dre, tab_bp, tab_fcf, tab_dupont = st.tabs(["Resultados (DRE)", "Balanço (BP)", "Fluxo de Caixa (FCF)", "🔥 Análise DuPont"])
            with tab_dre:
                dre_items = ['Total Revenue', 'Gross Profit', 'Operating Income', 'Net Income']
                plot_financial_statement(income_statement[income_statement.index.isin(dre_items)], "Demonstração de Resultados Anual")
            with tab_bp:
                bp_items = ['Total Assets', 'Total Liabilities Net Minority Interest', 'Stockholders Equity']
                plot_financial_statement(balance_sheet[balance_sheet.index.isin(bp_items)], "Balanço Patrimonial Anual")
            with tab_fcf:
                fcf_items = ['Operating Cash Flow', 'Investing Cash Flow', 'Financing Cash Flow', 'Free Cash Flow']
                plot_financial_statement(cash_flow[cash_flow.index.isin(fcf_items)], "Fluxo de Caixa Anual")
            with tab_dupont:
                dupont_df = calculate_dupont_analysis(income_statement, balance_sheet)
                if not dupont_df.empty:
                    st.dataframe(dupont_df.style.format("{:.2f}"), use_container_width=True)
                    df_plot = dupont_df.T.sort_index(); df_plot.index = df_plot.index.year
                    fig = px.line(df_plot, markers=True, title="Evolução dos Componentes do ROE")
                    fig.update_layout(xaxis_title="Ano", yaxis_title="Valor / Múltiplo", legend_title="Componentes");
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Não foi possível calcular a Análise DuPont.")
else:
    st.info("Insira um ticker e clique em 'Gerar Relatório Completo' para iniciar a análise.")
