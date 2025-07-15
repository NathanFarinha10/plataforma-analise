# pages/6_💰_Análise_de_Renda_Fixa.py (Versão 2.0 com Abas EUA/Brasil)

import streamlit as st
import pandas as pd
from fredapi import Fred
from bcb import sgs
import plotly.express as px
from datetime import datetime, timedelta

# --- Configuração da Página ---
st.set_page_config(page_title="Análise de Renda Fixa", page_icon="💰", layout="wide")

# --- INICIALIZAÇÃO DAS APIS ---
@st.cache_resource
def get_fred_api():
    try:
        api_key = st.secrets.get("FRED_API_KEY")
        if not api_key:
            st.error("Chave da API do FRED (FRED_API_KEY) não encontrada nos segredos do Streamlit.")
            st.stop()
        return Fred(api_key=api_key)
    except Exception as e:
        st.error(f"Falha ao inicializar API do FRED: {e}")
        st.stop()

fred = get_fred_api()

# --- FUNÇÕES DE BUSCA DE DADOS COM CACHE ---

# Funções para dados dos EUA (FRED)
@st.cache_data(ttl=3600)
def get_us_yield_curve_data():
    maturities_codes = {
        '1 Mês': 'DGS1MO', '3 Meses': 'DGS3MO', '6 Meses': 'DGS6MO', 
        '1 Ano': 'DGS1', '2 Anos': 'DGS2', '3 Anos': 'DGS3', 
        '5 Anos': 'DGS5', '7 Anos': 'DGS7', '10 Anos': 'DGS10', 
        '20 Anos': 'DGS20', '30 Anos': 'DGS30'
    }
    yield_data = []
    for name, code in maturities_codes.items():
        try:
            latest_value = fred.get_series_latest_release(code)
            if not latest_value.empty:
                yield_data.append({'Prazo': name, 'Taxa (%)': latest_value.iloc[0]})
        except: continue
    maturities_order = list(maturities_codes.keys())
    df = pd.DataFrame(yield_data)
    if not df.empty:
        df['Prazo'] = pd.Categorical(df['Prazo'], categories=maturities_order, ordered=True)
        return df.sort_values('Prazo')
    return df

@st.cache_data(ttl=3600)
def get_fred_series(series_codes, start_date):
    df = pd.DataFrame()
    for name, code in series_codes.items():
        try:
            series = fred.get_series(code, start_date)
            df[name] = series
        except: continue
    return df.dropna()

# Funções para dados do Brasil (BCB SGS)
@st.cache_data(ttl=3600)
def get_brazilian_real_interest_rate(start_date):
    """Busca dados da Selic e IPCA para calcular o juro real ex-post."""
    try:
        selic_diaria = sgs.get({'selic': 432}, start=start_date)
        ipca_anual = sgs.get({'ipca': 13522}, start=start_date)
        
        # Converte para decimal
        selic_diaria['selic'] /= 100
        ipca_anual['ipca'] /= 100
        
        # Consolida em base mensal para alinhamento
        df = selic_diaria.resample('M').mean().join(ipca_anual.resample('M').last()).dropna()
        
        # Fórmula do Juro Real: ((1 + nominal) / (1 + inflação)) - 1
        df['Juro Real (aa)'] = ((1 + df['selic']) / (1 + df['ipca'])) - 1
        df['Juro Real (aa)'] *= 100 # Converte para percentual
        
        return df[['Juro Real (aa)']]
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_brazilian_yield_curve():
    """Busca a Estrutura a Termo da Taxa de Juros (ETTJ) para títulos prefixados."""
    ettj_codes = {
        "1 Ano": 12469, "2 Anos": 12470, "3 Anos": 12471,
        "4 Anos": 12472, "5 Anos": 12473, "10 Anos": 12478
    }
    yield_data = []
    for name, code in ettj_codes.items():
        try:
            # Pega o último valor disponível
            latest_value = sgs.get({name: code}, last=1)
            if not latest_value.empty:
                yield_data.append({'Prazo': name, 'Taxa (%)': latest_value.iloc[0, 0]})
        except:
            continue
    
    df = pd.DataFrame(yield_data)
    if not df.empty:
        df['Prazo'] = pd.Categorical(df['Prazo'], categories=ettj_codes.keys(), ordered=True)
        return df.sort_values('Prazo')
    return df


# --- INTERFACE DA APLICAÇÃO ---
st.title("💰 Painel de Análise de Renda Fixa")
st.markdown("Um cockpit para monitorar as condições dos mercados de juros, crédito e inflação nos EUA e no Brasil.")

start_date = datetime.now() - timedelta(days=5*365)
tab_us, tab_br = st.tabs(["Mercado Americano (Referência)", "Mercado Brasileiro"])


# --- ABA DO MERCADO AMERICANO ---
with tab_us:
    st.header("Indicadores do Mercado de Referência dos EUA")
    
    # Curva de Juros (Yield Curve)
    st.subheader("Curva de Juros (US Treasury Yield Curve)")
    yield_curve_df_us = get_us_yield_curve_data()
    if yield_curve_df_us.empty:
        st.warning("Não foi possível obter os dados da curva de juros no momento.")
    else:
        latest_date = fred.get_series_info('DGS10').loc['last_updated'].split(' ')[0]
        st.caption(f"Curva de juros do Tesouro Americano para a data mais recente disponível ({latest_date}).")
        fig = px.line(yield_curve_df_us, x='Prazo', y='Taxa (%)', title="Forma da Curva de Juros Atual", markers=True)
        fig.update_layout(xaxis_title="Vencimento do Título", yaxis_title="Taxa de Juros Anual (%)")
        st.plotly_chart(fig, use_container_width=True)
    st.divider()

    # Spreads de Crédito
    st.subheader("Monitor de Spreads de Crédito")
    spread_codes = {"Spread High Yield": "BAMLH0A0HYM2", "Spread Investment Grade": "BAMLC0A4CBBB"}
    spreads_df = get_fred_series(spread_codes, start_date)
    if spreads_df.empty:
        st.warning("Não foi possível obter os dados de spread de crédito.")
    else:
        fig = px.line(spreads_df, title="Evolução dos Spreads de Crédito (EUA)")
        st.plotly_chart(fig, use_container_width=True)
    st.divider()
    
    # Expectativa de Inflação e Juro Real
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Expectativa de Inflação")
        inflation_codes = {"10 Anos": "T10YIE", "5 Anos": "T5YIE"}
        inflation_df = get_fred_series(inflation_codes, start_date)
        if not inflation_df.empty:
            st.plotly_chart(px.line(inflation_df, title="Inflação Implícita (Breakeven)"), use_container_width=True)
    with col2:
        st.subheader("Juros Reais (TIPS)")
        real_yield_codes = {"10 Anos": "DFII10"}
        real_yield_df = get_fred_series(real_yield_codes, start_date)
        if not real_yield_df.empty:
            fig = px.area(real_yield_df, title="Juro Real Americano")
            fig.add_hline(y=0, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True)
    st.divider()
    
    # Índice MOVE
    st.subheader("Índice de Volatilidade do Mercado de Juros (MOVE)")
    move_codes = {"Índice MOVE": "MOVE"}
    move_df = get_fred_series(move_codes, start_date)
    if not move_df.empty:
        st.plotly_chart(px.line(move_df, title="Evolução do Índice de Volatilidade MOVE"), use_container_width=True)


# --- ABA DO MERCADO BRASILEIRO ---
with tab_br:
    st.header("Indicadores do Mercado Brasileiro")

    # Juro Real Brasileiro
    st.subheader("Taxa de Juro Real (Ex-Post)")
    st.caption("Calculado como a Taxa Selic anualizada subtraída da inflação (IPCA) acumulada em 12 meses.")
    real_interest_br_df = get_brazilian_real_interest_rate(start_date)
    if real_interest_br_df.empty:
        st.warning("Não foi possível obter os dados para o cálculo do juro real brasileiro.")
    else:
        fig = px.area(real_interest_br_df, title="Evolução da Taxa de Juro Real no Brasil")
        fig.add_hline(y=0, line_dash="dash", line_color="red")
        fig.update_layout(yaxis_title="Taxa Real de Juros Anual (%)", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    st.divider()
    
    # Curva de Juros Brasileira
    st.subheader("Curva de Juros Pré-Fixada (ETTJ)")
    yield_curve_df_br = get_brazilian_yield_curve()
    if yield_curve_df_br.empty:
        st.warning("Não foi possível obter os dados da curva de juros brasileira.")
    else:
        st.caption("Taxas de mercado para Títulos Públicos Prefixados (LTN). Fonte: B3 / Anbima")
        fig = px.line(yield_curve_df_br, x='Prazo', y='Taxa (%)', title="Forma da Curva de Juros Pré-Fixada Atual", markers=True)
        fig.update_layout(xaxis_title="Vencimento do Título", yaxis_title="Taxa de Juros Anual (%)")
        st.plotly_chart(fig, use_container_width=True)
