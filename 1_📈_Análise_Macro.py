# 1_📈_Análise_Macro.py (Versão 2.2 - Com tratamento de erro robusto)

import streamlit as st
import pandas as pd
from fredapi import Fred
import plotly.express as px
from datetime import datetime

# --- Configuração da Página ---
st.set_page_config(
    page_title="PAG | Análise Macro",
    page_icon="🌍",
    layout="wide"
)

# --- Inicialização da API do FRED ---
try:
    api_key = st.secrets["FRED_API_KEY"]
    fred = Fred(api_key=api_key)
except KeyError:
    st.error("Chave da API do FRED não encontrada. Configure-a nos 'Secrets' do Streamlit.")
    st.stop()

# --- DICIONÁRIO EXPANDIDO DE SÉRIES DO FRED ---
fred_codes = {
    "EUA": {
        "Atividade": {
            "PIB (Cresc. Anual %)": "A191RL1Q225SBEA",
            "Produção Industrial (Variação Anual %)": "INDPRO",
            "Vendas no Varejo (Variação Anual %)": "RSAFS",
            "Confiança do Consumidor": "UMCSENT"
        },
        "Inflação e Juros": {
            "Inflação ao Consumidor (CPI YoY)": "CPIAUCSL",
            "Inflação ao Produtor (PPI YoY)": "PPIACO",
            "Taxa de Juros (Fed Funds)": "FEDFUNDS",
            "Juro 10 Anos": "DGS10",
            "Juro 2 Anos": "DGS2"
        },
        "Emprego": {
            "Taxa de Desemprego": "UNRATE",
            "Criação de Vagas (Non-Farm)": "PAYEMS"
        },
        "Setor Externo": {
            "Balança Comercial": "BOPGSTB"
        }
    },
    "Brasil": {
        "Atividade": {
            "PIB (Cresc. Anual %)": "CCRETT01BRQ661N",
            "Produção Industrial (Variação Anual %)": "BRAPROINDMISMEI",
            "Vendas no Varejo (Variação Anual %)": "SLRTTO01BRM661S",
            "Confiança do Empresário Industrial": "BSEMFT02BRM460S"
        },
        "Inflação e Juros": {
            "Inflação ao Consumidor (IPCA YoY)": "FPCPITOTLZGBRA",
            "Inflação ao Produtor (IPA YoY)": "PIEAMP01BRM661N",
            "Taxa de Juros (SELIC)": "IRSTCI01BRM156N"
        },
        "Emprego": {
            "Taxa de Desemprego": "LRUNTTTTBRQ156S"
        },
        "Setor Externo": {
            "Balança Comercial (USD)": "XTEXVA01BRM667S"
        }
    }
}

# --- FUNÇÕES AUXILIARES ---
@st.cache_data
def fetch_fred_series(series_code, start_date, end_date):
    """
    Busca uma única série do FRED com tratamento de erro para não quebrar a aplicação.
    """
    try:
        return fred.get_series(series_code, start_time=start_date, end_time=end_date)
    except ValueError as e:
        st.warning(f"Não foi possível buscar a série '{series_code}'. O FRED API retornou: {e}")
        return pd.Series(dtype=float)

def plot_indicator(data, title, key_sufix):
    """Função para plotar um gráfico de linha padrão com uma chave única."""
    if data.empty:
        st.info(f"Dados para '{title}' não puderam ser exibidos (possivelmente descontinuado ou sem dados no período).")
        return
        
    fig = px.line(data, title=title)
    fig.update_layout(showlegend=False, xaxis_title="Data", yaxis_title="Valor")
    st.plotly_chart(fig, use_container_width=True, key=f"plotly_{key_sufix}")

# --- INTERFACE DO USUÁRIO (SIDEBAR) ---
st.sidebar.title("Painel de Controle")
country_selection = st.sidebar.radio(
    "Escolha a Economia para Análise",
    ["🇧🇷 Brasil", "🇺🇸 EUA"],
    key='country_select'
)

st.sidebar.markdown("---")
st.sidebar.header("Filtros de Período")
start_date = st.sidebar.date_input('Data de Início', value=pd.to_datetime('2015-01-01'))
end_date = st.sidebar.date_input('Data de Fim', value=datetime.today())

# --- LÓGICA PRINCIPAL DA PÁGINA ---
st.title("Cockpit Macroeconômico")

country = "Brasil" if "Brasil" in country_selection else "EUA"
st.header(f"Análise Detalhada: {country}")

tab1, tab2, tab3, tab4 = st.tabs(["Atividade Econômica", "Inflação e Juros", "Consumidor e Emprego", "Setor Externo e Risco"])

with st.spinner("Carregando dados..."):
    with tab1:
        st.subheader("Crescimento e Produção")
        for name, code in fred_codes[country]["Atividade"].items():
            if "Confiança" not in name:
                data = fetch_fred_series(code, start_date, end_date)
                if name in ["Produção Industrial (Variação Anual %)", "Vendas no Varejo (Variação Anual %)"]:
                    if not data.empty:
                        data = data.pct_change(12).dropna() * 100
                plot_indicator(data, name, key_sufix=f"tab1_{code}")

    with tab2:
        st.subheader("Dinâmica de Preços e Política Monetária")
        for name, code in fred_codes[country]["Inflação e Juros"].items():
             if "Juro" not in name:
                data = fetch_fred_series(code, start_date, end_date)
                if country == "EUA" and name == "Inflação ao Produtor (PPI YoY)":
                    if not data.empty:
                        data = data.pct_change(12).dropna() * 100
                plot_indicator(data, name, key_sufix=f"tab2_{code}")
        
        if country == "EUA":
            st.subheader("Curva de Juros (Yield Curve)")
            juro_10a = fetch_fred_series(fred_codes["EUA"]["Inflação e Juros"]["Juro 10 Anos"], start_date, end_date)
            juro_2a = fetch_fred_series(fred_codes["EUA"]["Inflação e Juros"]["Juro 2 Anos"], start_date, end_date)
            if not juro_10a.empty and not juro_2a.empty:
                yield_spread = (juro_10a - juro_2a).dropna()
                fig = px.area(yield_spread, title="Spread 10 Anos - 2 Anos (EUA)")
                fig.add_hline(y=0, line_dash="dash", line_color="red")
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True, key="yield_curve")
                st.caption("Valores abaixo da linha vermelha (inversão da curva) são historicamente fortes indicadores de recessão futura.")
        else:
            st.subheader("Taxa de Juros Básica")
            selic_code = fred_codes["Brasil"]["Inflação e Juros"]["Taxa de Juros (SELIC)"]
            data = fetch_fred_series(selic_code, start_date, end_date)
            plot_indicator(data, "Taxa SELIC", key_sufix="selic")

    with tab3:
        st.subheader("Mercado de Trabalho e Confiança")
        for name, code in fred_codes[country]["Emprego"].items():
            data = fetch_fred_series(code, start_date, end_date)
            plot_indicator(data, name, key_sufix=f"tab3_emprego_{code}")
        
        conf_code = fred_codes[country]["Atividade"].get("Confiança do Consumidor") or fred_codes[country]["Atividade"].get("Confiança do Empresário Industrial")
        conf_name = "Confiança do Consumidor" if "Confiança do Consumidor" in fred_codes[country]["Atividade"] else "Confiança do Empresário Industrial"
        data = fetch_fred_series(conf_code, start_date, end_date)
        plot_indicator(data, conf_name, key_sufix=f"tab3_conf_{conf_code}")

    with tab4:
        st.subheader("Relações Comerciais")
        for name, code in fred_codes[country]["Setor Externo"].items():
            data = fetch_fred_series(code, start_date, end_date)
            plot_indicator(data, name, key_sufix=f"tab4_{code}")
