# 1_📈_Análise_Macro.py (Versão 3.1 - Corrigindo SyntaxError)

import streamlit as st
import pandas as pd
from fredapi import Fred
from bcb import sgs # Importação para o Banco Central do Brasil
import plotly.express as px
from datetime import datetime
import numpy as np

# --- Configuração da Página ---
st.set_page_config(page_title="PAG | Análise Macro", page_icon="🌍", layout="wide")

# --- INICIALIZAÇÃO DAS APIS ---
try:
    api_key = st.secrets["FRED_API_KEY"]
    fred = Fred(api_key=api_key)
except KeyError:
    st.error("Chave da API do FRED não encontrada. Configure-a nos 'Secrets'.")
    st.stop()

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

# --- FUNÇÕES DE BUSCA DE DADOS ---
@st.cache_data
def fetch_fred_series(series_code, start_date, end_date):
    """Busca uma série do FRED."""
    try:
        return fred.get_series(series_code, start_time=start_date, end_time=end_date)
    except ValueError:
        return pd.Series(dtype=float)

@st.cache_data
def fetch_bcb_series(series_code, start_date, end_date):
    """Busca uma série do SGS do BCB."""
    try:
        # Linha Corrigida
        return sgs.get({'code': series_code}, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
    except Exception:
        return pd.DataFrame()

def plot_indicator(data, title, key_sufix):
    """Função genérica para plotar gráficos."""
    if data.empty:
        st.info(f"Dados para '{title}' não disponíveis no período selecionado.")
        return
    fig = px.line(data, title=title)
    fig.update_layout(showlegend=False, xaxis_title="Data", yaxis_title="Valor")
    st.plotly_chart(fig, use_container_width=True, key=f"plotly_{key_sufix}")

# --- UI E LÓGICA PRINCIPAL ---
st.title("Cockpit Macroeconômico")
st.sidebar.title("Painel de Controle")
country_selection = st.sidebar.radio("Escolha a Economia para Análise", ["🇧🇷 Brasil", "🇺🇸 EUA"])

st.sidebar.markdown("---")
st.sidebar.header("Filtros de Período")
start_date = st.sidebar.date_input('Data de Início', value=pd.to_datetime('2015-01-01'))
end_date = st.sidebar.date_input('Data de Fim', value=datetime.today())

# --- ANÁLISE BRASIL (FONTE: BCB) ---
if "Brasil" in country_selection:
    st.header("Análise Detalhada: 🇧🇷 Brasil (Fonte: Banco Central do Brasil)")
    tab1, tab2, tab3, tab4 = st.tabs(["Atividade Econômica", "Inflação e Juros", "Emprego", "Setor Externo"])

    with st.spinner("Carregando dados do BCB..."):
        with tab1:
            for name, code in bcb_codes_br["Atividade"].items():
                data = fetch_bcb_series(code, start_date, end_date)
                plot_indicator(data, name, key_sufix=f"br_ativ_{code}")
        with tab2:
            for name, code in bcb_codes_br["Inflação e Juros"].items():
                data = fetch_bcb_series(code, start_date, end_date)
                if not data.empty:
                    data = data.iloc[:, 0]
                    if name in ["IPCA (Inflação Anual %)", "IGP-M (Anual %)"]:
                        data = (1 + data/100).rolling(window=12).apply(np.prod, raw=True) - 1
                        data = data * 100
                    plot_indicator(data.dropna(), name, key_sufix=f"br_infl_{code}")
        with tab3:
            for name, code in bcb_codes_br["Emprego"].items():
                data = fetch_bcb_series(code, start_date, end_date)
                plot_indicator(data, name, key_sufix=f"br_emp_{code}")
        with tab4:
            for name, code in bcb_codes_br["Setor Externo"].items():
                data = fetch_bcb_series(code, start_date, end_date)
                plot_indicator(data, name, key_sufix=f"br_ext_{code}")

# --- ANÁLISE EUA (FONTE: FRED) ---
elif "EUA" in country_selection:
    st.header("Análise Detalhada: 🇺🇸 EUA (Fonte: FRED)")
    tab1, tab2, tab3, tab4 = st.tabs(["Atividade Econômica", "Inflação e Juros", "Emprego", "Setor Externo e Risco"])

    with st.spinner("Carregando dados do FRED..."):
        with tab1:
            for name, code in fred_codes_us["Atividade"].items():
                data = fetch_fred_series(code, start_date, end_date)
                if name in ["Produção Industrial (Variação Anual %)", "Vendas no Varejo (Variação Anual %)"]:
                    if not data.empty:
                        data = data.pct_change(12).dropna() * 100
                plot_indicator(data, name, key_sufix=f"us_ativ_{code}")
        with tab2:
            st.subheader("Dinâmica de Preços e Política Monetária")
            for name, code in fred_codes_us["Inflação e Juros"].items():
                if "Juro" not in name:
                    data = fetch_fred_series(code, start_date, end_date)
                    if name == "Inflação ao Produtor (PPI YoY)":
                        if not data.empty:
                            data = data.pct_change(12).dropna() * 100
                    plot_indicator(data, name, key_sufix=f"us_infl_{code}")
            st.subheader("Curva de Juros (Yield Curve)")
            juro_10a = fetch_fred_series(fred_codes_us["Inflação e Juros"]["Juro 10 Anos"], start_date, end_date)
            juro_2a = fetch_fred_series(fred_codes_us["Inflação e Juros"]["Juro 2 Anos"], start_date, end_date)
            if not juro_10a.empty and not juro_2a.empty:
                yield_spread = (juro_10a - juro_2a).dropna()
                fig = px.area(yield_spread, title="Spread 10 Anos - 2 Anos (EUA)")
                fig.add_hline(y=0, line_dash="dash", line_color="red")
                fig.update_layout(showlegend=False); st.plotly_chart(fig, use_container_width=True, key="yield_curve")
                st.caption("Valores abaixo da linha vermelha (inversão da curva) são historicamente fortes indicadores de recessão futura.")
        with tab3:
            for name, code in fred_codes_us["Emprego"].items():
                data = fetch_fred_series(code, start_date, end_date)
                plot_indicator(data, name, key_sufix=f"us_emp_{code}")
        with tab4:
            for name, code in fred_codes_us["Setor Externo"].items():
                data = fetch_fred_series(code, start_date, end_date)
                plot_indicator(data, name, key_sufix=f"us_ext_{code}")
