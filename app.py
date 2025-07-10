# app.py

import streamlit as st
import pandas as pd
import pandas_datareader.data as web
import plotly.express as px
from datetime import datetime

# --- Configuração da Página ---
# A função set_page_config deve ser a primeira chamada do Streamlit no script.
st.set_page_config(
    page_title="PAG | Análise Macro",
    page_icon="📈",
    layout="wide"
)

# --- Dicionário de Séries do FRED ---
# Organiza os códigos dos indicadores para fácil acesso.
fred_series = {
    'Taxa de Juros': {
        'EUA': 'FEDFUNDS',
        'Brasil': 'BCBPCUM'  # Selic (BCB)
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

# --- Cache de Dados ---
# O decorator @st.cache_data garante que os dados sejam baixados apenas uma vez,
# mesmo que o usuário interaja com a página. Isso torna o app muito mais rápido.
@st.cache_data
def fetch_fred_data(series_codes, start_date, end_date):
    """
    Busca dados de múltiplas séries do FRED e os combina em um único DataFrame.
    """
    try:
        df = web.DataReader(series_codes.values(), 'fred', start_date, end_date)
        # Renomeia as colunas para os nomes dos países para clareza
        df = df.rename(columns=dict(zip(series_codes.values(), series_codes.keys())))
        return df
    except Exception as e:
        st.error(f"Erro ao buscar dados: {e}")
        return pd.DataFrame()

# --- Interface do Usuário (UI) ---

# Título da Aplicação
st.title("Painel de Análise Macroeconômica")
st.markdown("Plataforma para análise comparativa de indicadores econômicos do Brasil e EUA.")

# Sidebar para filtros e controles
st.sidebar.header("Filtros")

# Seleção do Indicador
selected_indicator = st.sidebar.selectbox(
    'Selecione o Indicador Econômico',
    options=list(fred_series.keys())
)

# Seleção do Período
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


# --- Lógica de Negócio e Exibição de Dados ---

# Busca os códigos correspondentes ao indicador selecionado
series_to_fetch = fred_series[selected_indicator]

# Informa ao usuário o que está sendo carregado
with st.spinner(f'Carregando dados de "{selected_indicator}"...'):
    # Busca os dados usando a função com cache
    data_df = fetch_fred_data(series_to_fetch, start_date, end_date)

# Verifica se os dados foram carregados com sucesso
if not data_df.empty:
    st.header(f"Análise de: {selected_indicator}")
    
    # Preenche valores ausentes para garantir continuidade no gráfico
    # O método 'ffill' (forward fill) preenche um valor NaN com o último valor válido.
    data_df_filled = data_df.ffill()

    # Cria o gráfico interativo com Plotly Express
    fig = px.line(
        data_df_filled,
        x=data_df_filled.index,
        y=data_df_filled.columns,
        title=f'Comparativo de {selected_indicator}: Brasil vs. EUA',
        labels={'value': 'Valor', 'DATE': 'Data', 'variable': 'País'}
    )
    # Exibe o gráfico no Streamlit
    st.plotly_chart(fig, use_container_width=True)

    # Exibe a tabela de dados brutos
    st.subheader("Dados em Tabela")
    # Mostra os últimos 10 registros, com formatação para 2 casas decimais
    st.dataframe(data_df.sort_index(ascending=False).head(10).style.format("{:.2f}"))
else:
    st.warning("Não foi possível carregar os dados para o período ou indicador selecionado.")

st.sidebar.markdown("---")
st.sidebar.info("Desenvolvido por Global Platform.")
