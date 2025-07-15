# pages/6_💰_Análise_de_Renda_Fixa.py

import streamlit as st
import pandas as pd
from fredapi import Fred
import plotly.express as px
from datetime import datetime, timedelta

# --- Configuração da Página ---
st.set_page_config(page_title="Análise de Renda Fixa", page_icon="💰", layout="wide")

# --- INICIALIZAÇÃO DA API DO FRED ---
@st.cache_resource
def get_fred_api():
    """Inicializa a conexão com a API do FRED."""
    try:
        api_key = st.secrets.get("FRED_API_KEY")
        if not api_key:
            st.error("Chave da API do FRED (FRED_API_KEY) não encontrada nos segredos do Streamlit.")
            st.stop()
        return Fred(api_key=api_key)
    except Exception as e:
        st.error(f"Falha ao inicializar a API do FRED: {e}")
        st.stop()

fred = get_fred_api()

# --- FUNÇÕES DE BUSCA DE DADOS COM CACHE ---
@st.cache_data(ttl=3600) # Cache de 1 hora
def get_yield_curve_data():
    """Busca os dados mais recentes para montar a curva de juros dos EUA."""
    maturities_codes = {
        '1 Mês': 'DGS1MO', '3 Meses': 'DGS3MO', '6 Meses': 'DGS6MO', 
        '1 Ano': 'DGS1', '2 Anos': 'DGS2', '3 Anos': 'DGS3', 
        '5 Anos': 'DGS5', '7 Anos': 'DGS7', '10 Anos': 'DGS10', 
        '20 Anos': 'DGS20', '30 Anos': 'DGS30'
    }
    yield_data = []
    for name, code in maturities_codes.items():
        try:
            # Pega o último valor disponível para cada maturidade
            latest_value = fred.get_series_latest_release(code)
            if not latest_value.empty:
                yield_data.append({'Prazo': name, 'Taxa (%)': latest_value.iloc[0]})
        except:
            continue # Pula se houver erro para um ticker específico
    
    # Ordena os prazos para o gráfico ficar correto
    maturities_order = list(maturities_codes.keys())
    df = pd.DataFrame(yield_data)
    df['Prazo'] = pd.Categorical(df['Prazo'], categories=maturities_order, ordered=True)
    return df.sort_values('Prazo')

@st.cache_data(ttl=3600)
def get_fred_series(series_codes, start_date):
    """Busca séries históricas do FRED."""
    df = pd.DataFrame()
    for name, code in series_codes.items():
        try:
            series = fred.get_series(code, start_date)
            df[name] = series
        except:
            continue
    return df.dropna()


# --- INTERFACE DA APLICAÇÃO ---
st.title("💰 Painel de Análise de Renda Fixa")
st.markdown("Um cockpit para monitorar as condições do mercado de juros, crédito e inflação.")

# --- Datas para a análise histórica ---
start_date = datetime.now() - timedelta(days=5*365) # 5 anos de histórico

# --- 1. Curva de Juros (Yield Curve) ---
st.subheader("Curva de Juros (US Treasury Yield Curve)")
yield_curve_df = get_yield_curve_data()

if yield_curve_df.empty:
    st.warning("Não foi possível obter os dados da curva de juros no momento.")
else:
    latest_date = fred.get_series_info('DGS10').loc['last_updated'].split(' ')[0]
    st.caption(f"Curva de juros do Tesouro Americano para a data mais recente disponível ({latest_date}).")
    
    fig_yield_curve = px.line(yield_curve_df, x='Prazo', y='Taxa (%)', title="Forma da Curva de Juros Atual", markers=True)
    fig_yield_curve.update_layout(xaxis_title="Vencimento do Título", yaxis_title="Taxa de Juros Anual (%)")
    st.plotly_chart(fig_yield_curve, use_container_width=True)
st.divider()


# --- 2. Spreads de Crédito ---
st.subheader("Monitor de Spreads de Crédito")
st.caption("O spread de crédito é o prêmio de risco exigido pelo mercado para investir em títulos corporativos em vez de títulos do governo. Spreads maiores indicam maior aversão ao risco.")

credit_spread_codes = {
    "Spread High Yield (Risco Alto)": "BAMLH0A0HYM2",
    "Spread Investment Grade (Risco Baixo/Médio)": "BAMLC0A4CBBB"
}
spreads_df = get_fred_series(credit_spread_codes, start_date)

if spreads_df.empty:
    st.warning("Não foi possível obter os dados de spread de crédito.")
else:
    fig_spreads = px.line(spreads_df, title="Evolução dos Spreads de Crédito (EUA)")
    fig_spreads.update_layout(yaxis_title="Spread sobre o Tesouro (%)", xaxis_title="Data", legend_title="Tipo de Título")
    st.plotly_chart(fig_spreads, use_container_width=True)
st.divider()


# --- 3. Expectativa de Inflação ---
st.subheader("Expectativa de Inflação (Breakeven)")
st.caption("Medida pela diferença entre os juros dos títulos nominais e os títulos protegidos contra a inflação (TIPS). Indica a inflação média anual que o mercado espera para os próximos anos.")

inflation_codes = {
    "Expectativa de Inflação (10 Anos)": "T10YIE",
    "Expectativa de Inflação (5 Anos)": "T5YIE"
}
inflation_df = get_fred_series(inflation_codes, start_date)

if inflation_df.empty:
    st.warning("Não foi possível obter os dados de expectativa de inflação.")
else:
    fig_inflation = px.line(inflation_df, title="Inflação Implícita no Mercado de Títulos (EUA)")
    fig_inflation.update_layout(yaxis_title="Inflação Anual Esperada (%)", xaxis_title="Data", legend_title="Horizonte")
    st.plotly_chart(fig_inflation, use_container_width=True)

# ADICIONE ESTE BLOCO NO FINAL DO ARQUIVO 6_💰_Análise_de_Renda_Fixa.py

st.divider()
# --- 4. Juros Reais (TIPS) ---
st.subheader("Juros Reais (Rendimento dos TIPS)")
st.caption("Representa o retorno de um título do Tesouro Americano de 10 anos que já é protegido contra a inflação. Quando está negativo, o investimento considerado o mais seguro do mundo está perdendo poder de compra.")

real_yield_codes = {
    "Juro Real de 10 Anos (EUA)": "DFII10"
}
real_yield_df = get_fred_series(real_yield_codes, start_date)

if real_yield_df.empty:
    st.warning("Não foi possível obter os dados de juros reais.")
else:
    fig_real_yield = px.area(real_yield_df, title="Evolução do Juro Real Americano (TIPS 10 Anos)")
    fig_real_yield.add_hline(y=0, line_dash="dash", line_color="red") # Linha de referência no zero
    fig_real_yield.update_layout(yaxis_title="Taxa de Juro Real (%)", xaxis_title="Data", showlegend=False)
    st.plotly_chart(fig_real_yield, use_container_width=True)

# ADICIONE ESTE SEGUNDO BLOCO LOGO ABAIXO DO ANTERIOR

st.divider()
# --- 5. Índice de Volatilidade (MOVE) ---
st.subheader("Índice de Volatilidade do Mercado de Juros (MOVE)")
st.caption("Conhecido como o 'VIX dos Títulos', o Índice MOVE mede a incerteza e a volatilidade esperada no mercado de renda fixa americano. Valores altos indicam grande incerteza (medo).")

move_codes = {
    "Índice MOVE": "MOVE"
}
move_df = get_fred_series(move_codes, start_date)

if move_df.empty:
    st.warning("Não foi possível obter os dados do Índice MOVE.")
else:
    fig_move = px.line(move_df, title="Evolução do Índice de Volatilidade MOVE")
    fig_move.update_layout(yaxis_title="Pontos do Índice", xaxis_title="Data", showlegend=False)
    st.plotly_chart(fig_move, use_container_width=True)
