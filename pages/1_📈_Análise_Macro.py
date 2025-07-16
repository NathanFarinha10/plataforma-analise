# 1_📈_Análise_Macro.py (Versão 4.1.1 - Final com Correção de Indentação)

import streamlit as st
import pandas as pd
from fredapi import Fred
from bcb import sgs
import plotly.express as px
from datetime import datetime
import yfinance as yf
import numpy as np
import re
import os
import json

# --- Configuração da Página ---
st.set_page_config(page_title="PAG | Análise Macro", page_icon="🌍", layout="wide")

st.sidebar.image("logo.png", use_container_width=True)

# --- NOME DO ARQUIVO DE DADOS ---
DATA_FILE = "recommendations.csv"
RECOMMENDATIONS_FILE = "recommendations.csv"
MANAGER_VIEWS_FILE = "manager_views.json"
REPORTS_DIR = "reports"

# --- Verifica se o usuário está logado ---
if not st.session_state.get("authentication_status"):
    st.info("Por favor, faça o login para acessar esta página.")
    st.stop()

# --- CARREGAMENTO DOS DADOS PERSISTENTES ---
if 'big_players_data' not in st.session_state:
    if os.path.exists(DATA_FILE):
        st.session_state.big_players_data = pd.read_csv(DATA_FILE)
    else:
        st.session_state.big_players_data = pd.DataFrame(columns=["País", "Gestora", "Classe de Ativo", "Recomendação", "Data"])

def load_data():
    if os.path.exists(RECOMMENDATIONS_FILE):
        recs = pd.read_csv(RECOMMENDATIONS_FILE)
    else:
        recs = pd.DataFrame(columns=["Gestora", "Classe de Ativo", "Recomendação", "Data"])
    
    if os.path.exists(MANAGER_VIEWS_FILE):
        with open(MANAGER_VIEWS_FILE, 'r', encoding='utf-8') as f:
            views = json.load(f)
    else:
        views = {} # Estrutura padrão será criada se o arquivo não existir
    
    return recs, views

recommendations_df, manager_views = load_data()

# --- INICIALIZAÇÃO DAS APIS ---
@st.cache_resource
def get_fred_api():
    try:
        api_key = st.secrets.get("FRED_API_KEY")
        if not api_key:
            st.error("Chave da API do FRED não configurada."); st.stop()
        return Fred(api_key=api_key)
    except Exception as e:
        st.error(f"Falha ao inicializar API do FRED: {e}"); st.stop()
fred = get_fred_api()

# --- FUNÇÕES AUXILIARES ---
@st.cache_data(ttl=3600)
# SUBSTITUA A SUA FUNÇÃO fetch_fred_series POR ESTA VERSÃO DE DIAGNÓSTICO

@st.cache_data(ttl=3600)
def fetch_fred_series(code, start_date):
    """Busca uma única série do FRED de forma robusta."""
    try: return fred.get_series(code, start_date)
    except: return pd.Series(dtype='float64')
        
@st.cache_data(ttl=3600)
def fetch_bcb_series(code, start_date):
    try:
        df = sgs.get({str(code): code}, start=start_date)
        if not df.empty and str(code) in df.columns: return df[str(code)]
        else: return pd.Series(dtype='float64')
    except Exception: return pd.Series(dtype='float64')

@st.cache_data(ttl=86400)
def fetch_market_data(tickers, period="5y"):
    try: return yf.download(tickers, period=period, progress=False)['Close']
    except: return pd.DataFrame()

def plot_indicator(data, title, y_label="Valor"):
    if data is None or data.empty:
        st.warning(f"Não foi possível carregar os dados para {title}.")
        return
    fig = px.area(data, title=title, labels={"value": y_label, "index": "Data"})
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# SUBSTITUA A FUNÇÃO ANTIGA POR ESTA VERSÃO CORRETA

def plot_indicator_with_analysis(code, title, explanation, unit="Índice", start_date="2005-01-01", is_pct_change=False, hline=None):
    """
    Função final que plota o gráfico e exibe análise com variação percentual ou em p.p.
    """
    data = fetch_fred_series(code, start_date).dropna()
    if data.empty:
        st.warning(f"Não foi possível carregar os dados para {title}."); return

    data_to_plot = data.pct_change(12).dropna() * 100 if is_pct_change else data
    if data_to_plot.empty:
        st.warning(f"Dados insuficientes para calcular a variação de {title}."); return

    latest_value = data_to_plot.iloc[-1]
    prev_month_value = data_to_plot.iloc[-2] if len(data_to_plot) > 1 else None
    prev_year_value = data_to_plot.iloc[-13] if len(data_to_plot) > 12 else None
    
    col1, col2 = st.columns([3, 1])
    with col1:
        fig = px.area(data_to_plot, title=title)
        fig.update_layout(showlegend=False, yaxis_title=unit, xaxis_title="Data")
        if hline is not None:
            fig.add_hline(y=hline, line_dash="dash", line_color="red", annotation_text=f"Nível {hline}")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown(f"**Análise do Indicador**"); st.caption(explanation)
        st.metric(label=f"Último Valor ({unit})", value=f"{latest_value:,.2f}")
        
        # --- LÓGICA CORRIGIDA E APRIMORADA PARA VARIAÇÃO ---
        is_rate = (unit == "%") or (is_pct_change)

        if prev_month_value is not None:
            if is_rate: # Se for taxa, calcula variação em pontos percentuais (p.p.)
                change_mom = latest_value - prev_month_value
                unit_label = " p.p."
            else: # Se for nível, calcula variação percentual (%)
                change_mom = ((latest_value / prev_month_value) - 1) * 100 if prev_month_value != 0 else 0
                unit_label = "%"
            st.metric(label=f"Variação Mensal", value=f"{change_mom:,.2f}{unit_label}", delta=f"{change_mom:,.2f}")

        if prev_year_value is not None:
            if is_rate: # Se for taxa, calcula variação em p.p.
                change_yoy = latest_value - prev_year_value
                unit_label = " p.p."
            else: # Se for nível, calcula variação em %
                change_yoy = ((latest_value / prev_year_value) - 1) * 100 if prev_year_value != 0 else 0
                unit_label = "%"
            st.metric(label=f"Variação Anual", value=f"{change_yoy:,.2f}{unit_label}", delta=f"{change_yoy:,.2f}")


def analyze_central_bank_discourse(text, lang='pt'):
    text = text.lower(); text = re.sub(r'\d+', '', text)
    if lang == 'pt':
        hawkish_words = ['inflação','risco','preocupação','desancoragem','expectativas','cautela','perseverança','serenidade','aperto','restritiva','incerteza','desafios']
        dovish_words = ['crescimento','atividade','hiato','ociosidade','arrefecimento','desaceleração','flexibilização','estímulo','progresso']
    else:
        hawkish_words = ['inflation','risk','tightening','restrictive','concern','hike','vigilance','uncertainty','upside risks']
        dovish_words = ['growth','employment','slack','easing','accommodation','progress','softening','cut','achieved']
    hawkish_score = sum(text.count(word) for word in hawkish_words)
    dovish_score = sum(text.count(word) for word in dovish_words)
    return hawkish_score, dovish_score

def style_recommendation(val):
    colors = {'Overweight': 'rgba(40, 167, 69, 0.7)', 'Underweight': 'rgba(220, 53, 69, 0.7)', 'Neutral': 'rgba(255, 193, 7, 0.7)'}
    return f'background-color: {colors.get(val, "transparent")}; color: white; text-align: center; font-weight: bold;'

# --- UI DA APLICAÇÃO ---
st.title("🌍 Painel de Análise Macroeconômica")
start_date = "2010-01-01"

# --- ABA PRINCIPAL ---
tab_br, tab_us, tab_global = st.tabs(["🇧🇷 Brasil", "🇺🇸 Estados Unidos", "🌐 Mercados Globais"])

# --- ABA BRASIL ---
with tab_br:
    st.header("Principais Indicadores do Brasil")
    subtab_br_activity, subtab_br_inflation, subtab_br_bc = st.tabs(["Atividade e Emprego", "Inflação e Juros", "Visão do BCB"])
    
    with subtab_br_activity:
        st.subheader("Atividade Econômica")
        plot_indicator(fetch_bcb_series(24369, start_date).pct_change(12).dropna() * 100, "IBC-Br (Var. Anual %)", "Variação %")
    
    with subtab_br_inflation:
        st.subheader("Inflação e Juros")
        plot_indicator(fetch_bcb_series(13522, start_date), "IPCA (Acum. 12M %)")
    
    with subtab_br_bc:
        st.subheader("Indicadores Monetários (BCB)")
        plot_indicator(fetch_bcb_series(27841, start_date).pct_change(12).dropna()*100, "M2 (Var. Anual %)")
        st.divider()
        st.subheader("Análise do Discurso (Ata do Copom)")
        copom_text = st.text_area("Cole aqui o texto da ata do Copom:", height=150, key="copom_text")
        if st.button("Analisar Discurso do Copom"):
            if copom_text.strip():
                h_score, d_score = analyze_central_bank_discourse(copom_text, lang='pt')
                c1,c2,c3 = st.columns(3); c1.metric("Placar Hawkish 🦅",h_score); c2.metric("Placar Dovish 🕊️",d_score)
                bal = "Hawkish" if h_score > d_score else "Dovish" if d_score > h_score else "Neutro"
                c3.metric("Balanço Final", bal)
    

# --- ABA EUA ---
with tab_us:
    st.header("Principais Indicadores dos Estados Unidos")
    subtab_us_activity, subtab_us_jobs, subtab_us_inflation, subtab_us_yield, subtab_us_real_estate, subtab_us_bc = st.tabs(["Atividade", "Mercado de Trabalho", "Inflação", "Curva de Juros", "Mercado Imobiliário", "Visão do Fed"])
    
    with subtab_us_activity:
        st.subheader("Indicadores de Atividade, Produção e Consumo")
        st.divider()


        plot_indicator_with_analysis(
            code="INDPRO", title="Produção Industrial",
            explanation="Mede a produção total das fábricas, minas e serviços de utilidade pública. Um forte indicador da saúde do setor secundário da economia.",
            unit="Var. Anual %", is_pct_change=True
        )
        st.divider()
        plot_indicator_with_analysis(
            code="RSXFS", title="Vendas no Varejo (Ex-Alimentação)",
            explanation="Mede o total de vendas de bens no varejo, excluindo serviços de alimentação. É um indicador chave da força do consumo das famílias.",
            unit="Var. Anual %", is_pct_change=True
        )
        st.divider()
        plot_indicator_with_analysis(
            code="PCEC96", title="Consumo Pessoal (PCE Real)",
            explanation="Mede os gastos totais dos consumidores em bens e serviços, ajustado pela inflação. É o principal componente do PIB e reflete a demanda agregada.",
            unit="Var. Anual %", is_pct_change=True
        )
        st.divider()
        plot_indicator_with_analysis(
            code="AMTMNO", title="Novas Ordens à Manufatura",
            explanation="Mede o valor em dólares de novos pedidos feitos à indústria. É um indicador antecedente, pois sinaliza a produção futura.",
            unit="Var. Anual %", is_pct_change=True
        )
        st.divider()
        plot_indicator_with_analysis(
            code="MANEMP", title="Emprego na Manufatura",
            explanation="Mede o número de trabalhadores empregados no setor industrial. Sua tendência ajuda a avaliar a saúde do mercado de trabalho e da indústria.",
            unit="Milhares"
        )
        st.divider()
        plot_indicator_with_analysis(
            code="UMCSENT", title="Sentimento do Consumidor (Univ. Michigan)",
            explanation="Mede a confiança dos consumidores em relação à economia e suas finanças pessoais. Um sentimento alto geralmente precede maiores gastos.",
            unit="Índice"
        )


    with subtab_us_jobs:
        st.subheader("Indicadores do Mercado de Trabalho Americano")
        st.caption("A força do mercado de trabalho é um dos principais mandatos do Federal Reserve e um motor para o consumo.")
        st.divider()

        plot_indicator_with_analysis(
            code="UNRATE", title="Taxa de Desemprego",
            explanation="A porcentagem da força de trabalho que está desempregada, mas procurando por emprego. É o principal indicador da saúde do mercado de trabalho.",
            unit="%"
        )
        st.divider()
        plot_indicator_with_analysis(
            code="PAYEMS", title="Criação de Vagas (Nonfarm Payrolls)",
            explanation="Mede o número de novos empregos criados a cada mês, excluindo o setor agrícola. O dado mais importante para o mercado financeiro.",
            unit="Milhares"
        )
        st.divider()
        plot_indicator_with_analysis(
            code="JTSJOL", title="Vagas em Aberto (JOLTS)",
            explanation="Mede o total de vagas de emprego não preenchidas. Uma proporção alta de vagas por desempregado indica um mercado de trabalho muito aquecido.",
            unit="Milhares"
        )
        st.divider()
        plot_indicator_with_analysis(
            code="CES0500000003", title="Crescimento dos Salários (Average Hourly Earnings)",
            explanation="Mede a variação anual do salário médio por hora. É um indicador crucial para a inflação, pois salários mais altos podem levar a um aumento no consumo e nos preços.",
            unit="Var. Anual %", is_pct_change=True
        )
    
    with subtab_us_inflation:
        st.subheader("Indicadores de Inflação e Preços")
        st.caption("A dinâmica da inflação é o principal fator que guia as decisões de juros do Federal Reserve.")
        
        # --- CPI ---
        st.markdown("#### Consumer Price Index (CPI) - Inflação ao Consumidor")
        col_cpi1, col_cpi2 = st.columns(2)
        with col_cpi1:
            plot_indicator_with_analysis("CPIAUCSL", "CPI Cheio", "Mede a variação de preços de uma cesta ampla de bens e serviços, incluindo alimentos e energia. É a principal medida de inflação para o público.")
        with col_cpi2:
            plot_indicator_with_analysis("CPILFESL", "Core CPI (Núcleo)", "Exclui os componentes voláteis de alimentos e energia para medir a tendência de fundo da inflação. É muito observado pelo Fed.")
        
        col_cpi3, col_cpi4 = st.columns(2)
        with col_cpi3:
            plot_indicator_with_analysis("CUSR0000SAD", "CPI - Bens Duráveis", "Mede a inflação específica de bens de consumo duráveis, como carros e eletrodomésticos.")
        with col_cpi4:
            plot_indicator_with_analysis("CUSR0000SAS", "CPI - Serviços", "Mede a inflação no setor de serviços, que é mais sensível aos salários e geralmente mais 'pegajosa'.")

        st.divider()

        # --- PCE ---
        # --- PCE CORRIGIDO ---
        st.markdown("#### Personal Consumption Expenditures (PCE) - A Métrica do Fed")
        col_pce1, col_pce2 = st.columns(2)
        with col_pce1:
            plot_indicator_with_analysis("PCEPI", "PCE Cheio", "A medida de inflação preferida pelo Fed.", is_pct_change=True, unit="Var. Anual %")
        with col_pce2:
            plot_indicator_with_analysis("PCEPILFE", "Core PCE (Núcleo)", "O indicador mais importante para a política monetária. A meta do Fed é de 2% para este núcleo.", is_pct_change=True, unit="Var. Anual %")
        
        st.divider()

        # --- PPI & Expectativas ---
        st.markdown("#### Producer Price Index (PPI) & Expectativas")
        col_ppi1, col_ppi2 = st.columns(2)
        with col_ppi1:
            plot_indicator_with_analysis("PPIACO", "PPI Cheio", "Mede a inflação na porta da fábrica (preços no atacado). É um indicador antecedente para a inflação ao consumidor (CPI).")
        with col_ppi2:
            plot_indicator_with_analysis("PPIFES", "Core PPI (Núcleo)", "Exclui alimentos e energia do PPI para mostrar a tendência de fundo dos preços ao produtor.")
        
        # Para o MICH, não calculamos variação percentual, apenas mostramos o índice
        st.divider()
        mich_data = fetch_fred_series("MICH", start_date)
        fig_mich = px.line(mich_data, title="Expectativa de Inflação (Univ. Michigan - 1 Ano)")
        fig_mich.update_layout(showlegend=False, yaxis_title="Inflação Esperada (%)")
        st.plotly_chart(fig_mich, use_container_width=True)
        st.caption("Mede a inflação que os consumidores esperam para os próximos 12 meses. Importante para o Fed, pois as expectativas podem influenciar a inflação futura.")

    
    with subtab_us_yield:
        st.subheader("Spread da Curva de Juros (10 Anos - 2 Anos)")
        s10a = fetch_fred_series("DGS10", start_date); s2a = fetch_fred_series("DGS2", start_date)
        if not s10a.empty and not s2a.empty:
            spread = (s10a - s2a).dropna()
            fig = px.area(spread, title="Spread 10A - 2A"); fig.add_hline(y=0, line_dash="dash", line_color="red"); st.plotly_chart(fig, use_container_width=True)
    with subtab_us_real_estate:
        st.subheader("Indicadores do Mercado Imobiliário Americano")
        st.caption("O setor imobiliário é um dos principais motores do ciclo econômico dos EUA.")
        st.divider()

        plot_indicator_with_analysis(
            code="MORTGAGE30US",
            title="Taxa de Financiamento Imobiliário 30 Anos",
            explanation="Mede o custo do crédito para compra de imóveis. Taxas mais altas desestimulam a demanda, enquanto taxas mais baixas a incentivam.",
            unit="%"
        )
        st.divider()
        plot_indicator_with_analysis(
            code="CSUSHPISA",
            title="S&P/Case-Shiller U.S. National Home Price Index",
            explanation="Principal índice de preços de imóveis residenciais. Mostra a valorização (ou desvalorização) das casas. É um indicador de inflação de ativos.",
            unit="Índice"
        )
        st.divider()
        plot_indicator_with_analysis(
            code="PERMIT",
            title="Permissões de Construção",
            explanation="É um indicador antecedente da atividade de construção. Um aumento nas permissões sinaliza um aquecimento do setor no futuro próximo.",
            unit="Milhares"
        )
        st.divider()
        plot_indicator_with_analysis(
            code="HOUST",
            title="Novas Casas Iniciadas",
            explanation="Mede o número de novas residências que começaram a ser construídas. É um indicador direto da atividade atual do setor de construção.",
            unit="Milhares"
        )
        st.divider()
        plot_indicator_with_analysis(
            code="HSN1F",
            title="Casas Novas Vendidas",
            explanation="Mede a força da demanda por novas propriedades. Um aumento nas vendas indica um mercado aquecido e confiança do consumidor.",
            unit="Milhares"
        )
        st.divider()
        plot_indicator_with_analysis(
            code="EXHOSLUSM495S",
            title="Casas Existentes à Venda (Estoque)",
            explanation="Mede o estoque de casas usadas disponíveis para venda. Um estoque baixo pressiona os preços para cima; um estoque alto indica um mercado mais fraco.",
            unit="Milhares"
        )
    with subtab_us_bc:
        st.subheader("Indicadores Monetários (Fed)")
        plot_indicator(fetch_fred_series("M2SL", start_date).pct_change(12).dropna()*100, "M2 (Var. Anual %)")
        st.divider()
        st.subheader("Análise do Discurso (Ata do FOMC)")
        fomc_text = st.text_area("Cole aqui o texto da ata do FOMC:", height=150, key="fomc_text")
        if st.button("Analisar Discurso do FOMC"):
            if fomc_text.strip():
                h,d = analyze_central_bank_discourse(fomc_text, lang='en')
                c1,c2,c3 = st.columns(3); c1.metric("Placar Hawkish 🦅", h); c2.metric("Placar Dovish 🕊️",d)
                bal = "Hawkish" if h>d else "Dovish" if d>h else "Neutro"
                c3.metric("Balanço Final", bal)

# --- ABA MERCADOS GLOBAIS ---
with tab_global:
    st.header("Índices e Indicadores de Mercado Global")
    subtab_equity, subtab_commodities, subtab_risk, subtab_valuation, subtab_big_players = st.tabs(["Ações", "Commodities", "Risco", "Valuation", "Visão dos Big Players"])
    with subtab_equity:
        tickers = {"S&P 500": "^GSPC", "Ibovespa": "^BVSP", "Nasdaq": "^IXIC", "DAX": "^GDAXI"}
        sel = st.multiselect("Selecione os índices:", options=list(tickers.keys()), default=["S&P 500", "Ibovespa"])
        if sel:
            data = fetch_market_data([tickers[i] for i in sel])
            if not data.empty: st.plotly_chart(px.line((data / data.dropna().iloc[0]) * 100, title="Performance Normalizada (Base 100)"), use_container_width=True)
    with subtab_commodities:
        c1,c2 = st.columns(2)
        comm_tickers = {"Petróleo WTI": "CL=F", "Ouro": "GC=F"}; data = fetch_market_data(list(comm_tickers.values()))
        if not data.empty: data.rename(columns=lambda c: next(k for k,v in comm_tickers.items() if v==c), inplace=True); c1.plotly_chart(px.line(data, title="Commodities"), use_container_width=True)
        curr_tickers = {"Dólar/Real": "BRL=X", "Euro/Dólar": "EURUSD=X"}; data=fetch_market_data(list(curr_tickers.values()))
        if not data.empty: data.rename(columns=lambda c: next(k for k,v in curr_tickers.items() if v==c), inplace=True); c2.plotly_chart(px.line(data, title="Câmbio"), use_container_width=True)
    with subtab_risk:
        vix = fetch_market_data(["^VIX"])
        if not vix.empty:
            fig = px.area(vix, title="Índice de Volatilidade VIX"); fig.add_hline(y=20, line_dash="dash"); fig.add_hline(y=30, line_dash="dash", line_color="red"); st.plotly_chart(fig, use_container_width=True)
    with subtab_valuation:
        factor_tickers = {"Growth": "VUG", "Value": "VTV"}
        data = fetch_market_data(list(factor_tickers.values()))
        if not data.empty:
            data["Ratio"] = data["VUG"] / data["VTV"]
            st.plotly_chart(px.line(data["Ratio"], title="Ratio de Performance: Growth vs. Value"), use_container_width=True)
    with subtab_big_players:
        st.subheader("Visão Consolidada dos Grandes Players")

        # --- VISUALIZAÇÃO PÚBLICA ---
        st.markdown("##### Matriz de Recomendações Táticas")
        if recommendations_df.empty:
            st.info("Nenhuma recomendação tática adicionada.")
        else:
            latest_recs = recommendations_df.sort_values('Data', ascending=False).drop_duplicates(['Gestora', 'Classe de Ativo'])
            pivot_table = latest_recs.pivot_table(index='Classe de Ativo', columns='Gestora', values='Recomendação', aggfunc='first').fillna("-")
            st.dataframe(pivot_table.style.applymap(style_recommendation), use_container_width=True)
        
        st.divider()
        st.markdown("##### Análise Detalhada por Gestora")
        
        # Gestoras a serem exibidas
        managers_to_display = ["BlackRock", "JP Morgan", "XP", "BTG"]
        for manager in managers_to_display:
            with st.expander(f"Visão da {manager}"):
                view_data = manager_views.get(manager, {"summary": "Dados não disponíveis.", "report_file": ""})
                st.markdown(view_data["summary"])
                if view_data.get("report_file") and os.path.exists(view_data["report_file"]):
                    with open(view_data["report_file"], "rb") as pdf_file:
                        st.download_button(label="Baixar Relatório Completo", data=pdf_file, file_name=os.path.basename(view_data["report_file"]), mime='application/octet-stream')
        
        st.divider()
        st.markdown("##### Consolidação Highpar")
        st.info(manager_views.get("Highpar", {"summary": "Visão da casa ainda não definida."})["summary"])

        # --- MODO EDITOR ---
        if st.session_state.get("role") == "Analista":
            st.divider()
            st.markdown("---")
            st.header("📝 Modo Editor")

            # Editor da Matriz de Recomendações
            with st.form("matrix_editor_form"):
                st.markdown("##### Editar Matriz de Recomendações")
                c1,c2,c3 = st.columns(3)
                gestora = c1.selectbox("Gestora (Matriz)", managers_to_display)
                classe_ativo = c2.selectbox("Classe de Ativo (Matriz)", ["Ações Brasil", "Ações EUA", "Renda Fixa Pré", "Inflação", "Dólar", "Commodities"])
                recomendacao = c3.radio("Recomendação", ["Overweight", "Neutral", "Underweight"], horizontal=True)
                if st.form_submit_button("Salvar na Matriz"):
                    new_rec = pd.DataFrame([{"Gestora": gestora, "Classe de Ativo": classe_ativo, "Recomendação": recomendacao, "Data": datetime.now().strftime("%Y-%m-%d")}])
                    updated_recs = pd.concat([recommendations_df, new_rec], ignore_index=True)
                    updated_recs.to_csv(RECOMMENDATIONS_FILE, index=False)
                    st.success("Matriz de recomendações atualizada!"); st.rerun()

            # Editor dos Detalhes das Gestoras
            with st.form("details_editor_form"):
                st.markdown("##### Editar Análise Detalhada da Gestora")
                manager_to_edit = st.selectbox("Selecione a Gestora para Editar", managers_to_display + ["Highpar"])
                
                current_summary = manager_views.get(manager_to_edit, {}).get("summary", "")
                new_summary = st.text_area("Texto da Análise", value=current_summary, height=250)
                
                uploaded_file = st.file_uploader("Subir novo relatório em PDF (opcional)")

                if st.form_submit_button("Salvar Análise Detalhada"):
                    if uploaded_file is not None:
                        # Cria o diretório se não existir
                        if not os.path.exists(REPORTS_DIR):
                            os.makedirs(REPORTS_DIR)
                        # Salva o arquivo e guarda o caminho
                        file_path = os.path.join(REPORTS_DIR, uploaded_file.name)
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        manager_views[manager_to_edit]["report_file"] = file_path
                    
                    manager_views[manager_to_edit]["summary"] = new_summary
                    manager_views[manager_to_edit]["last_updated"] = datetime.now().strftime("%Y-%m-%d")

                    with open(MANAGER_VIEWS_FILE, 'w', encoding='utf-8') as f:
                        json.dump(manager_views, f, ensure_ascii=False, indent=4)
                    
                    st.success(f"Análise da {manager_to_edit} atualizada!"); st.rerun()
