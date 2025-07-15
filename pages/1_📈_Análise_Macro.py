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
def fetch_fred_series(code, start_date):
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
    subtab_br_activity, subtab_br_inflation, subtab_br_bc, subtab_br_big_players = st.tabs(["Atividade e Emprego", "Inflação e Juros", "Visão do BCB", "Visão dos Big Players"])
    
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
    subtab_us_activity, subtab_us_inflation, subtab_us_yield, subtab_us_bc, subtab_us_big_players = st.tabs(["Atividade", "Inflação", "Curva de Juros", "Visão do Fed", "Visão dos Big Players"])
    
    with subtab_us_activity:
        st.subheader("Atividade Econômica")
        plot_indicator(fetch_fred_series("GDPC1", start_date).pct_change(4).dropna() * 100, "PIB Real (Var. Anual %)")
    with subtab_us_inflation:
        st.subheader("Inflação e Juros")
        plot_indicator(fetch_fred_series("CPIAUCSL", start_date).pct_change(12).dropna() * 100, "CPI (Var. Anual %)")
    with subtab_us_yield:
        st.subheader("Spread da Curva de Juros (10 Anos - 2 Anos)")
        s10a = fetch_fred_series("DGS10", start_date); s2a = fetch_fred_series("DGS2", start_date)
        if not s10a.empty and not s2a.empty:
            spread = (s10a - s2a).dropna()
            fig = px.area(spread, title="Spread 10A - 2A"); fig.add_hline(y=0, line_dash="dash", line_color="red"); st.plotly_chart(fig, use_container_width=True)
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
