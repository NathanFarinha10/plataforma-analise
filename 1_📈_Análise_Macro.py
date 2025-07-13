# 1_📈_Análise_Macro.py (Versão 4.3 - Lógica de Exibição Corrigida)

import streamlit as st
import pandas as pd
from fredapi import Fred
from bcb import sgs
import plotly.express as px
from datetime import datetime
import numpy as np
import feedparser
from bs4 import BeautifulSoup
import socket
from concurrent.futures import ThreadPoolExecutor

# --- Configuração da Página ---
st.set_page_config(page_title="PAG | Análise Macro", page_icon="🌍", layout="wide")

# --- INICIALIZAÇÃO DAS APIS ---
try:
    api_key = st.secrets.get("FRED_API_KEY")
    if api_key: fred = Fred(api_key=api_key)
    else: st.error("Chave da API do FRED não configurada."); st.stop()
except Exception as e:
    st.error(f"Falha ao inicializar API do FRED: {e}"); st.stop()

# --- DICIONÁRIOS DE CÓDIGOS ---
fred_codes_us = {
    "Atividade": {"PIB (Cresc. Anual %)": "A191RL1Q225SBEA", "Produção Industrial (Variação Anual %)": "INDPRO", "Vendas no Varejo (Variação Anual %)": "RSAFS", "Confiança do Consumidor": "UMCSENT"},
    "Inflação e Juros": {"Inflação ao Consumidor (CPI YoY)": "CPIAUCSL", "Inflação ao Produtor (PPI YoY)": "PPIACO", "Taxa de Juros (Fed Funds)": "FEDFUNDS", "Juro 10 Anos": "DGS10", "Juro 2 Anos": "DGS2"},
    "Emprego": {"Taxa de Desemprego": "UNRATE", "Criação de Vagas (Non-Farm)": "PAYEMS"},
    "Setor Externo": {"Balança Comercial": "BOPGSTB"}
}
bcb_codes_br = {
    "Atividade": {"IBC-Br (Proxy do PIB)": 24368, "Produção Industrial (Var. 12m)": 21859, "Vendas no Varejo (Var. 12m)": 1455},
    "Inflação e Juros": {"IPCA (Inflação Anual %)": 433, "IGP-M (Anual %)": 189, "Meta Taxa Selic": 432},
    "Emprego": {"Taxa de Desemprego (PNAD Contínua)": 24369},
    "Setor Externo": {"Balança Comercial (Saldo em USD Milhões)": 2270}
}
heatmap_indicators = {
    'PMI Industrial (ISM)': ('ISM', 'level'), 'PMI de Serviços (ISM)': ('NMFBACI', 'level'), 'Otimismo Pequenas Empresas (NFIB)': ('NFIB', 'level'),
    'Pedidos Iniciais de Seg. Desemprego': ('ICSA', 'level_inv'), 'Taxa de Desemprego': ('UNRATE', 'level_inv'), 'Inflação ao Consumidor (CPI YoY)': ('CPIAUCSL', 'yoy'),
    'Core CPI (YoY)': ('CORESTICKM159SFRBATL', 'yoy'), 'Inflação ao Produtor (PPI YoY)': ('PPIACO', 'yoy'), 'Vendas no Varejo (YoY)': ('RSAFS', 'yoy'),
    'Produção Industrial (YoY)': ('INDPRO', 'yoy'), 'Construção de Novas Casas': ('HOUST', 'level'), 'Licenças de Construção': ('PERMIT', 'level'),
    'Confiança do Consumidor': ('UMCSENT', 'level'), 'Spread da Curva de Juros (10Y-2Y)': ('T10Y2Y', 'level'),
    'Spread de Crédito High-Yield': ('BAMLH0A0HYM2', 'level_inv'), 'Índice de Volatilidade (VIX)': ('VIXCLS', 'level_inv')
}
GESTORAS_FEEDS = {
    "BlackRock": "https://www.blackrock.com/us/individual/insights/feed",
    "PIMCO": "https://blog.pimco.com/en/feed",
    "J.P. Morgan AM": "https://am.jpmorgan.com/us/en/asset-management/adv/insights/rss-feed/",
    "Bridgewater": "https://www.bridgewater.com/research-and-insights/feed"
}

# --- FUNÇÕES AUXILIARES ---
@st.cache_data
def fetch_fred_series(series_code, start_date, end_date):
    try: return fred.get_series(series_code, start_time=start_date, end_time=end_date)
    except Exception: return pd.Series(dtype=float)

@st.cache_data
def fetch_bcb_series(series_code, start_date, end_date):
    try: return sgs.get({'code': series_code}, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
    except Exception: return pd.DataFrame()

@st.cache_data
def calculate_heatmap_data(indicators, start_date, end_date):
    df_raw = pd.DataFrame(); [df_raw.update({name: s.resample('M').last()}) for name, (code, _) in indicators.items() if not (s := fetch_fred_series(code, start_date, end_date)).empty]
    if df_raw.empty: return pd.DataFrame()
    df_transformed = pd.DataFrame(); [df_transformed.update({name: s.pct_change(12) * 100 if t == 'yoy' else (s * -1 if t == 'level_inv' else s)}) for name, (_, t) in indicators.items() if name in df_raw.columns and not (s := df_raw[name].ffill()).empty]
    return df_transformed.rolling(window=120, min_periods=24).rank(pct=True) * 100

def fetch_single_feed_with_timeout(gestora_url_tuple):
    gestora, url = gestora_url_tuple
    original_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(10)
    try:
        feed = feedparser.parse(url)
        socket.setdefaulttimeout(original_timeout)
        if feed.entries:
            for entry in feed.entries: entry['gestora'] = gestora
            return gestora, 'success', feed.entries
        else: return gestora, 'empty', []
    except Exception as e:
        socket.setdefaulttimeout(original_timeout)
        return gestora, 'fail', []

def clean_html(raw_html):
    return BeautifulSoup(raw_html, "html.parser").get_text(separator=" ", strip=True) if raw_html else ""

def plot_indicator(data, title, key_suffix):
    if data.empty:
        st.info(f"Dados para '{title}' não disponíveis."); return
    fig = px.line(data, title=title); fig.update_layout(showlegend=False, xaxis_title="Data", yaxis_title="Valor")
    st.plotly_chart(fig, use_container_width=True, key=f"plotly_{key_suffix}")

def display_consensus_feed():
    st.subheader("A Visão das Gestoras Globais")
    st.info("Clique no botão abaixo para buscar em tempo real os últimos relatórios e artigos.")

    if st.button("Buscar Últimos Relatórios", key="fetch_consensus"):
        all_entries = []
        status_placeholder = st.empty()
        
        with st.spinner("Buscando feeds..."):
            with ThreadPoolExecutor(max_workers=len(GESTORAS_FEEDS)) as executor:
                results = executor.map(fetch_single_feed_with_timeout, GESTORAS_FEEDS.items())
                
                status_messages = []
                for gestora, status, entries in results:
                    if status == 'success':
                        status_messages.append(f"<li>{gestora}: ✅ Sucesso</li>")
                        all_entries.extend(entries)
                    else:
                        status_messages.append(f"<li>{gestora}: ❌ Falhou (Timeout ou Vazio)</li>")
                
                status_placeholder.markdown("<ul>" + "".join(status_messages) + "</ul>", unsafe_allow_html=True)

        if all_entries:
            sorted_entries = sorted(all_entries, key=lambda x: x.get('published_parsed'), reverse=True)
            st.success(f"Busca concluída! Exibindo os {min(25, len(sorted_entries))} artigos mais recentes encontrados.")
            st.divider()
            
            for entry in sorted_entries[:25]:
                try: published_date = pd.to_datetime(entry.get('published')).strftime('%d/%m/%Y')
                except: published_date = "Data Indisponível"
                
                st.markdown(f"##### [{entry.get('title', 'Título não disponível')}]({entry.get('link', '#')})")
                st.caption(f"Fonte: **{entry.get('gestora')}** | Publicado em: {published_date}")
                summary = clean_html(entry.get('summary'))
                if summary:
                    st.caption(summary, unsafe_allow_html=True)
                st.divider()
        else:
            st.error("Nenhum artigo pôde ser carregado na busca atual.")

# --- UI E LÓGICA PRINCIPAL ---
st.title("Cockpit Macroeconômico")
st.sidebar.title("Painel de Controle")
country_selection = st.sidebar.radio("Escolha a Economia para Análise", ["🇧🇷 Brasil", "🇺🇸 EUA"])
st.sidebar.markdown("---")
st.sidebar.header("Filtros de Período")
start_date = st.sidebar.date_input('Data de Início', value=pd.to_datetime('2010-01-01'))
end_date = st.sidebar.date_input('Data de Fim', value=datetime.today())

# ... (A lógica de exibição das abas permanece a mesma da versão anterior)
if "Brasil" in country_selection:
    st.header("Análise Detalhada: 🇧🇷 Brasil")
    tabs = st.tabs(["Atividade", "Inflação e Juros", "Emprego", "Setor Externo", "🌎 Consenso"])
    with tabs[0]:
        with st.spinner("Carregando dados do BCB..."):
            for name, code in bcb_codes_br["Atividade"].items(): plot_indicator(fetch_bcb_series(code, start_date, end_date), name, key_suffix=f"br_act_{code}")
    with tabs[1]:
        with st.spinner("Carregando dados do BCB..."):
            for name, code in bcb_codes_br["Inflação e Juros"].items():
                data = fetch_bcb_series(code, start_date, end_date)
                if not data.empty:
                    data = data.iloc[:, 0]
                    if name in ["IPCA (Inflação Anual %)", "IGP-M (Anual %)"]: data = ((1 + data/100).rolling(window=12).apply(np.prod, raw=True) - 1) * 100
                    plot_indicator(data.dropna(), name, key_suffix=f"br_inf_{code}")
    with tabs[2]:
        with st.spinner("Carregando dados do BCB..."):
            for name, code in bcb_codes_br["Emprego"].items(): plot_indicator(fetch_bcb_series(code, start_date, end_date), name, key_suffix=f"br_emp_{code}")
    with tabs[3]:
        with st.spinner("Carregando dados do BCB..."):
            for name, code in bcb_codes_br["Setor Externo"].items(): plot_indicator(fetch_bcb_series(code, start_date, end_date), name, key_suffix=f"br_ext_{code}")
    with tabs[4]:
        display_consensus_feed()

elif "EUA" in country_selection:
    st.header("Análise Detalhada: 🇺🇸 EUA")
    tabs = st.tabs(["🔥 Heatmap", "Atividade", "Inflação e Juros", "Emprego", "Setor Externo", "🌎 Consenso"])
    with tabs[0]:
        st.subheader("Diagnóstico Visual da Economia");
        with st.spinner("Calculando o Heatmap dinâmico..."):
            heatmap_data = calculate_heatmap_data(heatmap_indicators, start_date, end_date)
            if not heatmap_data.empty:
                heatmap_display = heatmap_data.last('36M').dropna(how='all').T
                styled_df = heatmap_display.style.background_gradient(cmap='coolwarm', axis=1).format("{:.0f}", na_rep="-").set_properties(**{'width': '60px', 'text-align': 'center'})
                st.dataframe(styled_df, use_container_width=True)
                st.caption("Valores representam o percentil do indicador em uma janela móvel de 10 anos.")
            else: st.warning("Não foi possível gerar o heatmap.")
    with tabs[1]:
        for name, code in fred_codes_us["Atividade"].items():
            data = fetch_fred_series(code, start_date, end_date)
            if name in ["Produção Industrial (Variação Anual %)", "Vendas no Varejo (Variação Anual %)"]:
                if not data.empty: data = data.pct_change(12).dropna() * 100
            plot_indicator(data, name, key_suffix=f"us_act_{code}")
    with tabs[2]:
        for name, code in fred_codes_us["Inflação e Juros"].items():
            if "Juro" not in name: plot_indicator(fetch_fred_series(code, start_date, end_date), name, key_suffix=f"us_inf_{code}")
        st.subheader("Curva de Juros (Yield Curve)")
        juro_10a = fetch_fred_series(fred_codes_us["Inflação e Juros"]["Juro 10 Anos"], start_date, end_date)
        juro_2a = fetch_fred_series(fred_codes_us["Inflação e Juros"]["Juro 2 Anos"], start_date, end_date)
        if not juro_10a.empty and not juro_2a.empty:
            yield_spread = (juro_10a - juro_2a).dropna()
            fig = px.area(yield_spread, title="Spread 10 Anos - 2 Anos (EUA)"); fig.add_hline(y=0, line_dash="dash", line_color="red"); fig.update_layout(showlegend=False); st.plotly_chart(fig, use_container_width=True, key="yield_curve")
            st.caption("Inversão da curva (valores < 0) é um forte indicador de recessão futura.")
    with tabs[3]:
        for name, code in fred_codes_us["Emprego"].items(): plot_indicator(fetch_fred_series(code, start_date, end_date), name, key_suffix=f"us_emp_{code}")
    with tabs[4]:
        for name, code in fred_codes_us["Setor Externo"].items(): plot_indicator(fetch_fred_series(code, start_date, end_date), name, key_suffix=f"us_ext_{code}")
    with tabs[5]:
        display_consensus_feed()
