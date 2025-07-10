# 1_📈_Análise_Macro.py (Versão 2.0 - Cockpit Macroeconômico)

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
# Estruturado por País e Categoria para a nova interface
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
    """Busca uma única série do FRED."""
    return fred.get_series(series_code, start_time=start_date, end_time=end_date)

def plot_indicator(data, title):
    """Função para plotar um gráfico de linha padrão."""
    fig = px.line(data, title=title)
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# --- INTERFACE DO USUÁRIO (SIDEBAR) ---
st.sidebar.title("Painel de Controle")
analysis_scope = st.sidebar.radio(
    "Escolha o Escopo da Análise",
    ["Visão Geral Comparativa", "Análise Detalhada: 🇧🇷 Brasil", "Análise Detalhada: 🇺🇸 EUA"],
    captions=["Compare os principais indicadores", "Mergulhe na economia brasileira", "Mergulhe na economia americana"]
)

st.sidebar.markdown("---")
st.sidebar.header("Filtros de Período")
start_date = st.sidebar.date_input('Data de Início', value=pd.to_datetime('2015-01-01'))
end_date = st.sidebar.date_input('Data de Fim', value=datetime.today())

# --- LÓGICA PRINCIPAL DA PÁGINA ---
st.title("Cockpit Macroeconômico")

# --- VISÃO COMPARATIVA ---
if analysis_scope == "Visão Geral Comparativa":
    st.header("Comparativo Brasil vs. EUA")
    
    comparative_indicators = {
        "PIB (Cresc. Anual %)": (fred_codes["Brasil"]["Atividade"]["PIB (Cresc. Anual %)"], fred_codes["EUA"]["Atividade"]["PIB (Cresc. Anual %)"]),
        "Inflação ao Consumidor (YoY)": (fred_codes["Brasil"]["Inflação e Juros"]["Inflação ao Consumidor (IPCA YoY)"], fred_codes["EUA"]["Inflação e Juros"]["Inflação ao Consumidor (CPI YoY)"]),
        "Taxa de Juros Básica": (fred_codes["Brasil"]["Inflação e Juros"]["Taxa de Juros (SELIC)"], fred_codes["EUA"]["Inflação e Juros"]["Taxa de Juros (Fed Funds)"]),
        "Taxa de Desemprego": (fred_codes["Brasil"]["Emprego"]["Taxa de Desemprego"], fred_codes["EUA"]["Emprego"]["Taxa de Desemprego"]),
    }

    for name, (br_code, us_code) in comparative_indicators.items():
        with st.spinner(f"Carregando {name}..."):
            br_data = fetch_fred_series(br_code, start_date, end_date).rename("Brasil")
            us_data = fetch_fred_series(us_code, start_date, end_date).rename("EUA")
            combined_data = pd.concat([br_data, us_data], axis=1).ffill()
            plot_indicator(combined_data, name)

# --- VISÕES DETALHADAS POR PAÍS ---
else:
    country = "Brasil" if "Brasil" in analysis_scope else "EUA"
    st.header(f"Análise Detalhada: {country}")

    # Organiza os indicadores em abas
    tab1, tab2, tab3, tab4 = st.tabs(["Atividade Econômica", "Inflação e Juros", "Consumidor e Emprego", "Setor Externo e Risco"])

    with tab1: # Atividade Econômica
        st.subheader("Crescimento e Produção")
        for name, code in fred_codes[country]["Atividade"].items():
            data = fetch_fred_series(code, start_date, end_date)
            # Para alguns indicadores, a variação percentual anual é mais informativa
            if name in ["Produção Industrial (Variação Anual %)", "Vendas no Varejo (Variação Anual %)"]:
                data = data.pct_change(12).dropna() * 100
            plot_indicator(data, name)

    with tab2: # Inflação e Juros
        st.subheader("Dinâmica de Preços e Política Monetária")
        for name, code in fred_codes[country]["Inflação e Juros"].items():
             if "Juro" not in name: # Plotamos os juros separadamente
                data = fetch_fred_series(code, start_date, end_date)
                if country == "EUA" and name == "Inflação ao Produtor (PPI YoY)":
                    data = data.pct_change(12).dropna() * 100
                plot_indicator(data, name)
        
        # Gráfico especial para a Curva de Juros (EUA)
        if country == "EUA":
            st.subheader("Curva de Juros (Yield Curve)")
            with st.spinner("Calculando o spread da curva de juros..."):
                juro_10a = fetch_fred_series(fred_codes["EUA"]["Inflação e Juros"]["Juro 10 Anos"], start_date, end_date)
                juro_2a = fetch_fred_series(fred_codes["EUA"]["Inflação e Juros"]["Juro 2 Anos"], start_date, end_date)
                yield_spread = (juro_10a - juro_2a).dropna()
                fig = px.area(yield_spread, title="Spread 10 Anos - 2 Anos (EUA)")
                fig.add_hline(y=0, line_dash="dash", line_color="red")
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
                st.caption("Valores abaixo da linha vermelha (inversão da curva) são historicamente fortes indicadores de recessão futura.")

    with tab3: # Consumidor e Emprego
        st.subheader("Mercado de Trabalho e Confiança")
        for name, code in fred_codes[country]["Emprego"].items():
            data = fetch_fred_series(code, start_date, end_date)
            plot_indicator(data, name)
        
        # Confiança do Consumidor (está no dict de Atividade, mas pertence a este painel)
        conf_code = fred_codes[country]["Atividade"].get("Confiança do Consumidor") or fred_codes[country]["Atividade"].get("Confiança do Empresário Industrial")
        conf_name = "Confiança do Consumidor" if "Confiança do Consumidor" in fred_codes[country]["Atividade"] else "Confiança do Empresário Industrial"
        data = fetch_fred_series(conf_code, start_date, end_date)
        plot_indicator(data, conf_name)

    with tab4: # Setor Externo e Risco
        st.subheader("Relações Comerciais")
        for name, code in fred_codes[country]["Setor Externo"].items():
            data = fetch_fred_series(code, start_date, end_date)
            plot_indicator(data, name)
