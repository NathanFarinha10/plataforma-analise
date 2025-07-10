# app.py

import streamlit as st
import pandas as pd
from fredapi import Fred # Importando a nova biblioteca
import plotly.express as px
from datetime import datetime

# --- Configuração da Página ---
st.set_page_config(
    page_title="PAG | Análise Macro",
    page_icon="📈",
    layout="wide"
)

# --- Inicialização da API do FRED ---
# Acessa a chave da API que guardamos nos "Secrets" do Streamlit
try:
    api_key = st.secrets["FRED_API_KEY"]
    fred = Fred(api_key=api_key)
except KeyError:
    st.error("Chave da API do FRED não encontrada. Configure-a nos 'Secrets' do Streamlit.")
    st.stop() # Interrompe a execução se a chave não for encontrada

# --- Dicionário de Séries do FRED (mesmo de antes) ---
fred_series = {
    'Taxa de Juros': {
        'EUA': 'FEDFUNDS',
        'Brasil': 'BCBPCUM'
    },
    'Inflação (YoY)': {
        'EUA': 'CPIAUCSL',
        'Brasil': 'FPCPITOTLZGBRA'
    },
    'PIB (Cresc. Anual %)': {
        'EUA': 'A191RL1Q225SBEA',
        'Brasil': 'RGDPNABRINA666NRUG'
    },
    'Taxa de Desemprego': {
        'EUA': 'UNRATE',
        'Brasil': 'LRUNTTTTBRQ156S'
    }
}

# --- Cache de Dados (Função de busca reescrita) ---
@st.cache_data
def fetch_fred_data(series_codes, start_date, end_date):
    """
    Busca dados de múltiplas séries do FRED usando a biblioteca fredapi
    e os combina em um único DataFrame.
    """
    all_data = []
    for country, code in series_codes.items():
        try:
            # Busca cada série individualmente
            series_data = fred.get_series(code, start_time=start_date, end_time=end_date)
            series_data = series_data.to_frame(name=country) # Converte para DataFrame e nomeia a coluna
            all_data.append(series_data)
        except Exception as e:
            # Avisa sobre falhas individuais sem parar o app
            st.warning(f"Não foi possível buscar dados para '{country}' (Código: {code}). Erro: {e}")
    
    if not all_data:
        return pd.DataFrame() # Retorna DF vazio se nenhuma série foi carregada

    # Concatena todos os DataFrames em um só, alinhando pelos índices (datas)
    combined_df = pd.concat(all_data, axis=1)
    return combined_df

# --- Interface do Usuário (UI) - NENHUMA MUDANÇA AQUI ---
st.title("Painel de Análise Macroeconômica")
st.markdown("Plataforma para análise comparativa de indicadores econômicos do Brasil e EUA.")

st.sidebar.header("Filtros")

selected_indicator = st.sidebar.selectbox(
    'Selecione o Indicador Econômico',
    options=list(fred_series.keys())
)

start_date = st.sidebar.date_input(
    'Data de Início',
    value=pd.to_datetime('2010-01-01'),
    min_value=pd.to_datetime('1990-01-01'),
    max_value=datetime.today()
)

end_date = st.sidebar.date_input(
    'Data de Fim',
    value=datetime.today(),
    min_value=pd.to_datetime('1990-01-01'),
    max_value=datetime.today()
)

# --- Lógica de Negócio e Exibição de Dados - NENHUMA MUDANÇA AQUI ---
series_to_fetch = fred_series[selected_indicator]

with st.spinner(f'Carregando dados de "{selected_indicator}"...'):
    data_df = fetch_fred_data(series_to_fetch, start_date, end_date)

if not data_df.empty:
    st.header(f"Análise de: {selected_indicator}")
    
    data_df_filled = data_df.ffill()

    fig = px.line(
        data_df_filled,
        x=data_df_filled.index,
        y=data_df_filled.columns,
        title=f'Comparativo de {selected_indicator}: Brasil vs. EUA',
        labels={'value': 'Valor', 'index': 'Data', 'variable': 'País'}
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Dados em Tabela")
    st.dataframe(data_df.sort_index(ascending=False).head(10).style.format(na_rep="-", formatter="{:.2f}"))
else:
    st.warning("Não foi possível carregar os dados para o período ou indicador selecionado.")

st.sidebar.markdown("---")
st.sidebar.info("Desenvolvido por Global Platform.")
