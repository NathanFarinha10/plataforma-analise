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
FOMC_MEETINGS_FILE = "fomc_meetings.json"
REPORTS_DIR = "reports_fomc" # Diretório para atas do FOMC

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

# --- FUNÇÕES DE CARREGAMENTO E SALVAMENTO DE DADOS ---
def load_json_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return [] # Retorna lista vazia se o arquivo não existir

def save_json_data(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- CARREGAMENTO INICIAL DOS DADOS DO FOMC ---
if 'fomc_meetings' not in st.session_state:
    st.session_state.fomc_meetings = load_json_data(FOMC_MEETINGS_FILE)

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

def plot_indicator_with_analysis(source, code, title, explanation, unit="Índice", start_date="2005-01-01", is_pct_change=False, hline=None):
    """
    Função genérica que busca dados do FRED ou BCB e plota com análise.
    """
    if source == 'fred':
        data = fetch_fred_series(code, start_date).dropna()
    elif source == 'bcb':
        data = fetch_bcb_series(code, start_date).dropna()
    else:
        st.error("Fonte de dados desconhecida."); return

    if data.empty: st.warning(f"Não foi possível carregar os dados para {title}."); return
    
    data_to_plot = data.pct_change(12).dropna() * 100 if is_pct_change else data
    if data_to_plot.empty: st.warning(f"Dados insuficientes para calcular a variação de {title}."); return

    latest_value = data_to_plot.iloc[-1]
    prev_month_value = data_to_plot.iloc[-2] if len(data_to_plot) > 1 else None
    prev_year_value = data_to_plot.iloc[-13] if len(data_to_plot) > 12 else None
    
    col1, col2 = st.columns([3, 1])
    with col1:
        fig = px.area(data_to_plot, title=title)
        fig.update_layout(showlegend=False, yaxis_title=unit, xaxis_title="Data")
        if hline is not None: fig.add_hline(y=hline, line_dash="dash", line_color="red", annotation_text=f"Nível {hline}")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown(f"**Análise do Indicador**"); st.caption(explanation)
        st.metric(label=f"Último Valor ({unit})", value=f"{latest_value:,.2f}")
        is_rate = (unit == "%") or (is_pct_change)
        if prev_month_value is not None:
            change_mom = ((latest_value / prev_month_value) - 1) * 100 if not is_rate and prev_month_value != 0 else latest_value - prev_month_value
            unit_label = "%" if not is_rate else " p.p."
            st.metric(label=f"Variação Mensal", value=f"{change_mom:,.2f}{unit_label}", delta=f"{change_mom:,.2f}")
        if prev_year_value is not None:
            change_yoy = ((latest_value / prev_year_value) - 1) * 100 if not is_rate and prev_year_value != 0 else latest_value - prev_year_value
            unit_label = "%" if not is_rate else " p.p."
            st.metric(label=f"Variação Anual", value=f"{change_yoy:,.2f}{unit_label}", delta=f"{change_yoy:,.2f}")

# SUBSTITUA A SUA FUNÇÃO get_us_yield_curve_data PELA VERSÃO CORRIGIDA ABAIXO

@st.cache_data(ttl=3600)
def get_us_yield_curve_data():
    """Busca os dados mais recentes para montar a curva de juros dos EUA."""
    maturities_codes = {
        '1 Mês': 'DGS1MO', 
        '3 Meses': 'DTB3',       # <-- CÓDIGO CORRIGIDO
        '6 Meses': 'DTB6',       # <-- CÓDIGO CORRIGIDO
        '1 Ano': 'DGS1', 
        '2 Anos': 'DGS2', 
        '3 Anos': 'DGS3', 
        '5 Anos': 'DGS5', 
        '7 Anos': 'DGS7', 
        '10 Anos': 'DGS10', 
        '20 Anos': 'DGS20', 
        '30 Anos': 'DGS30'
    }
    yield_data = []
    for name, code in maturities_codes.items():
        try:
            # Pega o último valor disponível para cada maturidade
            latest_value = fred.get_series_latest_release(code)
            if not latest_value.empty:
                yield_data.append({'Prazo': name, 'Taxa (%)': latest_value.iloc[0]})
        except:
            continue
    
    # Ordena os prazos para o gráfico ficar correto
    maturities_order = list(maturities_codes.keys())
    df = pd.DataFrame(yield_data)
    if not df.empty:
        df['Prazo'] = pd.Categorical(df['Prazo'], categories=maturities_order, ordered=True)
        return df.sort_values('Prazo')
    return df

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
    subtab_br_activity, subtab_br_inflation, subtab_br_bc = st.tabs(["Atividade", "Inflação e Juros", "Visão do BCB"])
    
    with subtab_br_activity:
        st.subheader("Indicadores de Atividade Econômica e Confiança")
        st.divider()

        plot_indicator_with_analysis(
            source='bcb', code=24369, title="IBC-Br (Prévia do PIB)",
            explanation="Índice de Atividade Econômica do Banco Central, considerado uma 'prévia' mensal do PIB. Mede o ritmo da economia como um todo.",
            unit="Índice"
        )
        st.divider()
        plot_indicator_with_analysis(
            source='bcb', code=21859, title="Produção Industrial (PIM-PF)",
            explanation="Mede a produção física da indústria de transformação e extrativa. Um termômetro da saúde do setor secundário.",
            unit="Var. Anual %", is_pct_change=True
        )
        st.divider()
        plot_indicator_with_analysis(
            source='bcb', code=1473, title="Vendas no Varejo (PMC - Volume)",
            explanation="Mede o volume de vendas do comércio varejista. Principal indicador para medir a força do consumo das famílias.",
            unit="Var. Anual %", is_pct_change=True
        )
        st.divider()
        plot_indicator_with_analysis(
            source='bcb', code=24424, title="Volume de Serviços (PMS)",
            explanation="Mede a receita bruta real do setor de serviços, que é o maior componente do PIB brasileiro. Essencial para entender a dinâmica da economia.",
            unit="Var. Anual %", is_pct_change=True
        )
        st.divider()
        plot_indicator_with_analysis(
            source='bcb', code=4393.3, title="Índice de Confiança do Consumidor (ICC - FGV)",
            explanation="Mede o quão otimistas os consumidores estão em relação à economia e suas finanças. É um indicador antecedente do consumo futuro.",
            unit="Índice"
        )
    
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
    subtab_us_activity, subtab_us_jobs, subtab_us_inflation, subtab_us_yield, subtab_us_real_estate, subtab_us_fed = st.tabs(["Atividade", "Mercado de Trabalho", "Inflação", "Curva de Juros", "Mercado Imobiliário", "Visão do Fed"])
    
    with subtab_us_activity:
        st.subheader("Indicadores de Atividade, Produção e Consumo")
        st.divider()
        # --- CORREÇÃO: ADICIONADO 'source=fred' ---
        plot_indicator_with_analysis('fred', "INDPRO", "Produção Industrial", "Mede a produção total das fábricas, minas e serviços de utilidade pública.", "Var. Anual %", is_pct_change=True)
        st.divider()
        plot_indicator_with_analysis('fred', "RSXFS", "Vendas no Varejo (Ex-Alimentação)", "Mede o total de vendas de bens no varejo. É um indicador chave da força do consumo das famílias.", "Var. Anual %", is_pct_change=True)
        st.divider()
        plot_indicator_with_analysis('fred', "PCEC96", "Consumo Pessoal (PCE Real)", "Mede os gastos totais dos consumidores, ajustado pela inflação. É o principal componente do PIB.", "Var. Anual %", is_pct_change=True)
        st.divider()
        plot_indicator_with_analysis('fred', "AMTMNO", "Novas Ordens à Manufatura", "Mede o valor de novos pedidos feitos à indústria. É um indicador antecedente, pois sinaliza a produção futura.", "Var. Anual %", is_pct_change=True)
        st.divider()
        plot_indicator_with_analysis('fred', "UMCSENT", "Sentimento do Consumidor (Univ. Michigan)", "Mede a confiança dos consumidores. Um sentimento alto geralmente precede maiores gastos.", "Índice")


     with subtab_us_jobs:
        st.subheader("Indicadores do Mercado de Trabalho Americano")
        st.divider()
        plot_indicator_with_analysis('fred', "UNRATE", "Taxa de Desemprego", "A porcentagem da força de trabalho que está desempregada, mas procurando por emprego.", "%")
        st.divider()
        plot_indicator_with_analysis('fred', "PAYEMS", "Criação de Vagas (Nonfarm Payrolls)", "Mede o número de novos empregos criados a cada mês, excluindo o setor agrícola.", "Milhares")
        st.divider()
        plot_indicator_with_analysis('fred', "JTSJOL", "Vagas em Aberto (JOLTS)", "Mede o total de vagas de emprego não preenchidas. Uma proporção alta de vagas por desempregado indica um mercado aquecido.", "Milhares")
        st.divider()
        plot_indicator_with_analysis('fred', "CES0500000003", "Crescimento dos Salários (Average Hourly Earnings)", "Mede a variação anual do salário médio por hora. É um indicador crucial para a inflação.", "Var. Anual %", is_pct_change=True)
    
    with subtab_us_inflation:
        st.subheader("Indicadores de Inflação e Preços")
        st.caption("A dinâmica da inflação é o principal fator que guia as decisões de juros do Federal Reserve.")
        
        st.markdown("#### Consumer Price Index (CPI) - Inflação ao Consumidor")
        col_cpi1, col_cpi2 = st.columns(2)
        with col_cpi1:
            plot_indicator_with_analysis('fred', "CPIAUCSL", "CPI Cheio", "Mede a variação de preços de uma cesta ampla de bens e serviços, incluindo alimentos e energia.", is_pct_change=True, unit="Var. Anual %")
        with col_cpi2:
            plot_indicator_with_analysis('fred', "CPILFESL", "Core CPI (Núcleo)", "Exclui os componentes voláteis de alimentos e energia para medir a tendência de fundo da inflação.", is_pct_change=True, unit="Var. Anual %")
        
        st.divider()

        st.markdown("#### Personal Consumption Expenditures (PCE) - A Métrica do Fed")
        col_pce1, col_pce2 = st.columns(2)
        with col_pce1:
            plot_indicator_with_analysis('fred', "PCEPI", "PCE Cheio", "A medida de inflação preferida pelo Fed. Sua cesta é mais ampla e dinâmica que a do CPI.", is_pct_change=True, unit="Var. Anual %")
        with col_pce2:
            plot_indicator_with_analysis('fred', "PCEPILFE", "Core PCE (Núcleo)", "O indicador mais importante para a política monetária. A meta do Fed é de 2% para este núcleo.", is_pct_change=True, unit="Var. Anual %")

        st.divider()

        st.markdown("#### Producer Price Index (PPI) & Expectativas")
        col_ppi1, col_ppi2 = st.columns(2)
        with col_ppi1:
            plot_indicator_with_analysis('fred', "PPIACO", "PPI Cheio (Final Demand)", "Mede a inflação na porta da fábrica (preços no atacado). É um indicador antecedente para a inflação ao consumidor (CPI).", is_pct_change=True, unit="Var. Anual %")
        with col_ppi2:
            plot_indicator_with_analysis('fred', "MICH", "Expectativa de Inflação (Michigan, 1 Ano)", "Mede a inflação que os consumidores esperam para os próximos 12 meses. Importante para o Fed, pois as expectativas podem influenciar a inflação futura.", unit="%")

    
   with subtab_us_yield:
        st.subheader("Análise da Curva de Juros Americana")
        st.caption("A forma e os spreads da curva de juros são um dos principais indicadores antecedentes da atividade econômica.")
        st.divider()

        st.markdown("##### Forma da Curva de Juros Atual")
        @st.cache_data(ttl=3600)
        def get_us_yield_curve_data():
            codes = {'1 Mês':'DGS1MO','3 Meses':'DTB3','6 Meses':'DTB6','1 Ano':'DGS1','2 Anos':'DGS2','5 Anos':'DGS5','10 Anos':'DGS10','30 Anos':'DGS30'}
            data = []
            for name, code in codes.items():
                try:
                    val = fetch_fred_series(code, datetime.now() - pd.Timedelta(days=10)) # Busca dados recentes
                    if not val.empty: data.append({'Prazo': name, 'Taxa (%)': val.iloc[-1]})
                except: continue
            df = pd.DataFrame(data)
            if not df.empty: df['Prazo'] = pd.Categorical(df['Prazo'], categories=codes.keys(), ordered=True); return df.sort_values('Prazo')
            return df
        
        yield_curve_df = get_us_yield_curve_data()
        if not yield_curve_df.empty:
            fig_curve = px.line(yield_curve_df, x='Prazo', y='Taxa (%)', title="Curva de Juros do Tesouro Americano", markers=True)
            st.plotly_chart(fig_curve, use_container_width=True)
        else:
            st.warning("Não foi possível carregar os dados para a forma da curva de juros.")
        
        st.divider()
        st.markdown("##### Spreads da Curva de Juros (Indicadores de Recessão)")
        col1, col2 = st.columns(2)
        with col1:
            j10a = fetch_fred_series("DGS10", start_date); j2a = fetch_fred_series("DGS2", start_date)
            if not j10a.empty and not j2a.empty:
                spread = (j10a - j2a).dropna()
                fig = px.area(spread, title="Spread 10 Anos - 2 Anos"); fig.add_hline(y=0, line_dash="dash", line_color="red"); st.plotly_chart(fig, use_container_width=True)
                st.caption("A inversão deste spread (abaixo de zero) historicamente antecede recessões.")
        with col2:
            j2a_s = fetch_fred_series("DGS2", start_date); j3m = fetch_fred_series("DGS3MO", start_date)
            if not j2a_s.empty and not j3m.empty:
                spread = (j2a_s - j3m).dropna()
                fig = px.area(spread, title="Spread 2 Anos - 3 Meses"); fig.add_hline(y=0, line_dash="dash", line_color="red"); st.plotly_chart(fig, use_container_width=True)
                st.caption("Considerado pelo Fed um indicador de recessão de curto prazo muito confiável.")

    
    with subtab_us_real_estate:
        st.subheader("Indicadores do Mercado Imobiliário Americano")
        st.caption("O setor imobiliário é um dos principais motores do ciclo econômico dos EUA.")
        st.divider()

        plot_indicator_with_analysis('fred', 
            "MORTGAGE30US", "Taxa de Financiamento Imobiliário 30 Anos",
            "Mede o custo do crédito para compra de imóveis. Taxas mais altas desestimulam a demanda.",
            unit="%"
        )
        st.divider()
        plot_indicator_with_analysis('fred', 
            "CSUSHPISA", "Índice de Preços de Imóveis (Case-Shiller)",
            "Principal índice de preços de imóveis residenciais. Mostra a valorização das casas.",
            unit="Índice"
        )
        st.divider()
        plot_indicator_with_analysis('fred', 
            "PERMIT", "Permissões de Construção",
            "Indicador antecedente da atividade de construção. Um aumento nas permissões sinaliza aquecimento do setor.",
            unit="Milhares"
        )
        st.divider()
        plot_indicator_with_analysis('fred', 
            "HSN1F", "Casas Novas Vendidas",
            "Mede a força da demanda por novas propriedades. Um aumento nas vendas indica um mercado aquecido.",
            unit="Milhares"
        )

    with subtab_us_fed:
        st.subheader("Painel de Política Monetária - Federal Reserve (Fed)")
        st.caption("Acompanhe as ferramentas e os indicadores que guiam as decisões do banco central americano.")
        st.divider()

        st.markdown("##### Política de Juros e Balanço do Fed")
        col1, col2 = st.columns(2)
        with col1:
            plot_indicator_with_analysis('fred', "FEDFUNDS", "Fed Funds Rate", "A principal taxa de juros de política monetária, definida pelo FOMC.", unit="%")
        with col2:
            plot_indicator_with_analysis('fred', "WALCL", "Ativos Totais no Balanço do Fed", "Aumentos (QE) indicam política expansionista; reduções (QT) indicam política contracionista.", unit="$ Trilhões")

        st.divider()
        st.markdown("##### Agregados Monetários e Contexto Fiscal")
        col3, col4 = st.columns(2)
        with col3:
            plot_indicator_with_analysis('fred', "M2SL", "Agregado Monetário M2", "Mede a quantidade de 'dinheiro' na economia. Sua variação pode ser um indicador antecedente de inflação.", "Var. Anual %", is_pct_change=True)
        with col4:
            debt = fetch_fred_series("GFDEBTN", start_date); gdp = fetch_fred_series("GDP", start_date)
            if not debt.empty and not gdp.empty:
                gdp = gdp.resample('D').ffill()
                debt_to_gdp = (debt / (gdp * 1_000_000_000)).dropna() * 100
                fig_debt = px.area(debt_to_gdp, title="Dívida Pública / PIB (%)"); fig_debt.update_layout(showlegend=False, yaxis_title="%"); st.plotly_chart(fig_debt, use_container_width=True)

        st.divider()
        st.subheader("Acompanhamento Histórico do Discurso do FOMC")
        # (O código do histórico do FOMC permanece o mesmo aqui)
        
        meetings = st.session_state.fomc_meetings
        if not meetings:
            st.info("Nenhum registro de reunião do FOMC foi adicionado ainda.")
        else:
            sorted_meetings = sorted(meetings, key=lambda x: x['meeting_date'], reverse=True)
            meeting_dates = [m['meeting_date'] for m in sorted_meetings]
            selected_date = st.selectbox("Selecione a data da Reunião do FOMC para analisar:", meeting_dates)
            
            selected_meeting = next((m for m in sorted_meetings if m['meeting_date'] == selected_date), None)
            
            if selected_meeting:
                st.metric("Decisão de Juros Tomada", selected_meeting.get("decision", "N/A"))
                h_score = selected_meeting["analysis"]["hawkish"]
                d_score = selected_meeting["analysis"]["dovish"]
                final_tone = "Hawkish 🦅" if h_score > d_score else "Dovish 🕊️" if d_score > h_score else "Neutro 😐"
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Placar Hawkish", h_score); c2.metric("Placar Dovish", d_score); c3.metric("Tom Predominante", final_tone)
                
                if selected_meeting.get("pdf_path") and os.path.exists(selected_meeting["pdf_path"]):
                    with open(selected_meeting["pdf_path"], "rb") as pdf_file:
                        st.download_button("Baixar Ata em PDF", data=pdf_file, file_name=os.path.basename(selected_meeting["pdf_path"]))
                
                with st.expander("Ver texto completo da ata"):
                    st.text(selected_meeting.get("minutes_text", "Texto não disponível."))

        # --- MODO EDITOR ---
        if st.session_state.get("role") == "Analista":
            st.divider()
            st.markdown("---")
            st.header("📝 Modo Editor - Reuniões do FOMC")
            
            editor_tab1, editor_tab2 = st.tabs(["Adicionar Nova Reunião", "Gerenciar Reuniões Existentes"])
            
            with editor_tab1:
                with st.form("new_meeting_form"):
                    st.markdown("##### Adicionar Registro de Nova Reunião")
                    m_date = st.date_input("Data da Reunião"); m_decision = st.text_input("Decisão de Juros (ex: Manteve em 5.25%-5.50%)")
                    m_text = st.text_area("Cole aqui o texto completo da ata:", height=250); m_pdf = st.file_uploader("Anexar arquivo da ata em PDF")
                    
                    if st.form_submit_button("Salvar Nova Reunião"):
                        if m_text and m_decision:
                            h, d = analyze_central_bank_discourse(m_text, lang='en')
                            new_meeting = {"meeting_date": m_date.strftime("%Y-%m-%d"), "decision": m_decision, "minutes_text": m_text, "pdf_path": "", "analysis": {"hawkish": h, "dovish": d}}
                            if m_pdf:
                                if not os.path.exists(REPORTS_DIR_FOMC): os.makedirs(REPORTS_DIR_FOMC)
                                file_path = os.path.join(REPORTS_DIR_FOMC, m_pdf.name)
                                with open(file_path, "wb") as f: f.write(m_pdf.getbuffer())
                                new_meeting["pdf_path"] = file_path
                            
                            st.session_state.fomc_meetings.append(new_meeting)
                            save_json_data(st.session_state.fomc_meetings, FOMC_MEETINGS_FILE)
                            st.success("Nova reunião salva com sucesso!"); st.rerun()
                        else:
                            st.error("Data, Decisão e Texto da Ata são campos obrigatórios.")

            with editor_tab2:
                st.markdown("##### Excluir um Registro de Reunião")
                if not st.session_state.fomc_meetings:
                    st.info("Nenhuma reunião para gerenciar.")
                else:
                    sorted_meetings_delete = sorted(st.session_state.fomc_meetings, key=lambda x: x['meeting_date'], reverse=True)
                    for i, meeting in enumerate(sorted_meetings_delete):
                        st.markdown(f"**Reunião de {meeting['meeting_date']}**")
                        if st.button("Excluir este registro", key=f"delete_{meeting['meeting_date']}"):
                            st.session_state.fomc_meetings = [m for m in st.session_state.fomc_meetings if m['meeting_date'] != meeting['meeting_date']]
                            save_json_data(st.session_state.fomc_meetings, FOMC_MEETINGS_FILE)
                            st.success("Registro excluído!"); st.rerun()
                        st.divider()


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
