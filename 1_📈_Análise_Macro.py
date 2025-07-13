# 1_📈_Análise_Macro.py (Versão 3.2 - Final e Completa)

import streamlit as st
import pandas as pd
from fredapi import Fred
from bcb import sgs
import plotly.express as px
from datetime import datetime
import numpy as np

# --- Configuração da Página ---
st.set_page_config(page_title="PAG | Análise Macro", page_icon="🌍", layout="wide")

# --- INICIALIZAÇÃO DAS APIS ---
try:
    # Use st.secrets.get para evitar erro se a chave não existir
    api_key = st.secrets.get("FRED_API_KEY")
    if api_key:
        fred = Fred(api_key=api_key)
    else:
        st.error("Chave da API do FRED não encontrada. Configure-a nos 'Secrets'.")
        st.stop()
except Exception as e:
    st.error(f"Falha ao inicializar a API do FRED: {e}")
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
heatmap_indicators = {
    'PMI Industrial (ISM)': ('ISM', 'level'),
    'PMI de Serviços (ISM)': ('NMFBACI', 'level'),
    'Otimismo Pequenas Empresas (NFIB)': ('NFIB', 'level'),
    'Pedidos Iniciais de Seg. Desemprego': ('ICSA', 'level_inv'),
    'Taxa de Desemprego': ('UNRATE', 'level_inv'),
    'Inflação ao Consumidor (CPI YoY)': ('CPIAUCSL', 'yoy'),
    'Core CPI (YoY)': ('CORESTICKM159SFRBATL', 'yoy'),
    'Inflação ao Produtor (PPI YoY)': ('PPIACO', 'yoy'),
    'Vendas no Varejo (YoY)': ('RSAFS', 'yoy'),
    'Produção Industrial (YoY)': ('INDPRO', 'yoy'),
    'Construção de Novas Casas': ('HOUST', 'level'),
    'Licenças de Construção': ('PERMIT', 'level'),
    'Confiança do Consumidor': ('UMCSENT', 'level'),
    'Spread da Curva de Juros (10Y-2Y)': ('T10Y2Y', 'level'),
    'Spread de Crédito High-Yield': ('BAMLH0A0HYM2', 'level_inv'),
    'Índice de Volatilidade (VIX)': ('VIXCLS', 'level_inv')
}

# --- FUNÇÕES DE BUSCA E CÁLCULO ---
@st.cache_data
def fetch_fred_series(series_code, start_date, end_date):
    """Busca uma série do FRED com tratamento de erro."""
    try:
        return fred.get_series(series_code, start_time=start_date, end_time=end_date)
    except Exception as e:
        st.warning(f"Não foi possível buscar a série '{series_code}' do FRED. A API pode estar instável ou a série descontinuada. Erro: {type(e).__name__}")
        return pd.Series(dtype=float)

@st.cache_data
def fetch_bcb_series(series_code, start_date, end_date):
    """Busca uma série do SGS do BCB."""
    try:
        return sgs.get({'code': series_code}, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'))
    except Exception:
        return pd.DataFrame()

@st.cache_data
def calculate_heatmap_data(indicators, start_date, end_date):
    """Busca, transforma e calcula o percentil para os dados do heatmap."""
    df_raw = pd.DataFrame()
    for name, (code, _) in indicators.items():
        series = fetch_fred_series(code, start_date, end_date)
        if not series.empty:
            # Resample para frequência mensal para padronizar
            df_raw[name] = series.resample('M').last()

    if df_raw.empty:
        return pd.DataFrame()

    df_transformed = pd.DataFrame()
    for name, (_, trans_type) in indicators.items():
        if name in df_raw.columns:
            series = df_raw[name].ffill()
            if trans_type == 'yoy':
                df_transformed[name] = series.pct_change(12) * 100
            elif trans_type == 'level_inv':
                # Para indicadores inversos (alto=ruim), multiplicamos por -1 para o cálculo do percentil
                df_transformed[name] = series * -1
            else: # 'level'
                df_transformed[name] = series
    
    # Calcula o percentil na janela móvel de 10 anos (120 meses)
    df_percentile = df_transformed.rolling(window=120, min_periods=24).rank(pct=True) * 100
    return df_percentile.dropna(how='all', axis=1)

def plot_indicator(data, title, key_suffix):
    """Função genérica para plotar gráficos."""
    if data.empty:
        st.info(f"Dados para '{title}' não disponíveis no período selecionado.")
        return
    fig = px.line(data, title=title)
    fig.update_layout(showlegend=False, xaxis_title="Data", yaxis_title="Valor")
    st.plotly_chart(fig, use_container_width=True, key=f"plotly_{key_suffix}")

# --- UI E LÓGICA PRINCIPAL ---
st.title("Cockpit Macroeconômico")
st.sidebar.title("Painel de Controle")
country_selection = st.sidebar.radio("Escolha a Economia para Análise", ["🇧🇷 Brasil", "🇺🇸 EUA"])

st.sidebar.markdown("---")
st.sidebar.header("Filtros de Período")
start_date = st.sidebar.date_input('Data de Início', value=pd.to_datetime('2000-01-01'))
end_date = st.sidebar.date_input('Data de Fim', value=datetime.today())

if "Brasil" in country_selection:
    st.header("Análise Detalhada: 🇧🇷 Brasil (Fonte: Banco Central do Brasil)")
    tab1, tab2, tab3, tab4 = st.tabs(["Atividade Econômica", "Inflação e Juros", "Emprego", "Setor Externo"])
    with st.spinner("Carregando dados do BCB..."):
        with tab1:
            for name, code in bcb_codes_br["Atividade"].items():
                data = fetch_bcb_series(code, start_date, end_date)
                plot_indicator(data, name, key_suffix=f"br_ativ_{code}")
        with tab2:
            for name, code in bcb_codes_br["Inflação e Juros"].items():
                data = fetch_bcb_series(code, start_date, end_date)
                if not data.empty:
                    data = data.iloc[:, 0]
                    if name in ["IPCA (Inflação Anual %)", "IGP-M (Anual %)"]:
                        # Calcula a variação anualizada (acumulado 12m)
                        data = (1 + data/100).rolling(window=12).apply(np.prod, raw=True) - 1
                        data = data * 100
                    plot_indicator(data.dropna(), name, key_suffix=f"br_infl_{code}")
        with tab3:
            for name, code in bcb_codes_br["Emprego"].items():
                data = fetch_bcb_series(code, start_date, end_date)
                plot_indicator(data, name, key_suffix=f"br_emp_{code}")
        with tab4:
            for name, code in bcb_codes_br["Setor Externo"].items():
                data = fetch_bcb_series(code, start_date, end_date)
                plot_indicator(data, name, key_suffix=f"br_ext_{code}")

elif "EUA" in country_selection:
    st.header("Análise Detalhada: 🇺🇸 EUA (Fonte: FRED)")
    tab_heatmap, tab_activity, tab_inflation, tab_employment, tab_external = st.tabs(["🔥 Heatmap", "Atividade", "Inflação e Juros", "Emprego", "Setor Externo"])

    with tab_heatmap:
        st.subheader("Diagnóstico Visual da Economia")
        with st.spinner("Calculando o Heatmap dinâmico..."):
            heatmap_data = calculate_heatmap_data(heatmap_indicators, start_date, end_date)
            if not heatmap_data.empty:
                # Mostra os últimos 3 anos de dados mensais para melhor visualização
                heatmap_display = heatmap_data.last('36M').dropna(how='all').T
                styled_df = heatmap_display.style.background_gradient(cmap='coolwarm', axis=1)\
                                                 .format("{:.0f}", na_rep="-")\
                                                 .set_properties(**{'width': '60px', 'text-align': 'center'})
                st.dataframe(styled_df, use_container_width=True)
                st.caption("Valores representam o percentil do indicador em uma janela móvel de 10 anos. Vermelho (quente) = próximo de 100. Azul (frio) = próximo de 0.")
            else:
                st.warning("Não foi possível gerar o heatmap. A API do FRED pode estar instável ou sem dados para o período.")

    with tab_activity:
        for name, code in fred_codes_us["Atividade"].items():
            data = fetch_fred_series(code, start_date, end_date)
            if name in ["Produção Industrial (Variação Anual %)", "Vendas no Varejo (Variação Anual %)"]:
                if not data.empty: data = data.pct_change(12).dropna() * 100
            plot_indicator(data, name, key_suffix=f"us_act_{code}")

    with tab_inflation:
        for name, code in fred_codes_us["Inflação e Juros"].items():
            if "Juro" not in name:
                data = fetch_fred_series(code, start_date, end_date)
                if name == "Inflação ao Produtor (PPI YoY)":
                    if not data.empty: data = data.pct_change(12).dropna() * 100
                plot_indicator(data, name, key_suffix=f"us_inf_{code}")
        
        st.subheader("Curva de Juros (Yield Curve)")
        juro_10a = fetch_fred_series(fred_codes_us["Inflação e Juros"]["Juro 10 Anos"], start_date, end_date)
        juro_2a = fetch_fred_series(fred_codes_us["Inflação e Juros"]["Juro 2 Anos"], start_date, end_date)
        if not juro_10a.empty and not juro_2a.empty:
            yield_spread = (juro_10a - juro_2a).dropna()
            fig = px.area(yield_spread, title="Spread 10 Anos - 2 Anos (EUA)")
            fig.add_hline(y=0, line_dash="dash", line_color="red")
            fig.update_layout(showlegend=False); st.plotly_chart(fig, use_container_width=True, key="yield_curve")
            st.caption("Valores abaixo da linha vermelha (inversão da curva) são historicamente fortes indicadores de recessão futura.")

    with tab_employment:
        for name, code in fred_codes_us["Emprego"].items():
            data = fetch_fred_series(code, start_date, end_date)
            plot_indicator(data, name, key_suffix=f"us_emp_{code}")
    
    with tab_external:
        for name, code in fred_codes_us["Setor Externo"].items():
            data = fetch_fred_series(code, start_date, end_date)
            plot_indicator(data, name, key_suffix=f"us_ext_{code}")
