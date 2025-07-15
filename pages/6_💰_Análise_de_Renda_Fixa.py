# pages/6_💰_Análise_de_Renda_Fixa.py (Versão 3.0 com Analisador de Títulos)

import streamlit as st
import pandas as pd
from fredapi import Fred
from bcb import sgs
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
import numpy_financial as npf

# --- Configuração da Página ---
st.set_page_config(page_title="Análise de Renda Fixa", page_icon="💰", layout="wide")

st.sidebar.image("logo.png", use_container_width=True)

# --- INICIALIZAÇÃO DAS APIS ---
@st.cache_resource
def get_fred_api():
    try:
        api_key = st.secrets.get("FRED_API_KEY")
        if not api_key: st.error("Chave da API do FRED (FRED_API_KEY) não encontrada."); st.stop()
        return Fred(api_key=api_key)
    except Exception as e:
        st.error(f"Falha ao inicializar API do FRED: {e}"); st.stop()

fred = get_fred_api()

# --- FUNÇÕES DE BUSCA DE DADOS ---
@st.cache_data(ttl=3600)
def get_us_yield_curve_data():
    codes = {'1 Mês':'DGS1MO','3 Meses':'DGS3MO','6 Meses':'DGS6MO','1 Ano':'DGS1','2 Anos':'DGS2','3 Anos':'DGS3','5 Anos':'DGS5','7 Anos':'DGS7','10 Anos':'DGS10','20 Anos':'DGS20','30 Anos':'DGS30'}
    data = []
    for name, code in codes.items():
        try:
            val = fred.get_series_latest_release(code)
            if not val.empty: data.append({'Prazo': name, 'Taxa (%)': val.iloc[0]})
        except: continue
    order = list(codes.keys())
    df = pd.DataFrame(data)
    if not df.empty:
        df['Prazo'] = pd.Categorical(df['Prazo'], categories=order, ordered=True)
        return df.sort_values('Prazo')
    return df

@st.cache_data(ttl=3600)
def get_fred_series(series_codes, start_date):
    df = pd.DataFrame()
    for name, code in series_codes.items():
        try: df[name] = fred.get_series(code, start_date)
        except: continue
    return df.dropna()

@st.cache_data(ttl=3600)
def get_brazilian_real_interest_rate(start_date):
    try:
        selic = sgs.get({'selic': 432}, start=start_date) / 100
        ipca = sgs.get({'ipca': 13522}, start=start_date) / 100
        df = selic.resample('M').mean().join(ipca.resample('M').last()).dropna()
        df['Juro Real (aa)'] = (((1 + df['selic']) / (1 + df['ipca'])) - 1) * 100
        return df[['Juro Real (aa)']]
    except Exception: return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_brazilian_yield_curve():
    codes = {"1 Ano":12469,"2 Anos":12470,"3 Anos":12471,"5 Anos":12473,"10 Anos":12478}
    data = []
    for name, code in codes.items():
        try:
            val = sgs.get({name: code}, last=1)
            if not val.empty: data.append({'Prazo': name, 'Taxa (%)': val.iloc[0, 0]})
        except: continue
    df = pd.DataFrame(data)
    if not df.empty:
        df['Prazo'] = pd.Categorical(df['Prazo'], categories=codes.keys(), ordered=True)
        return df.sort_values('Prazo')
    return df

# --- FUNÇÕES DE CÁLCULO PARA O ANALISADOR DE TÍTULOS ---
def calculate_bond_cashflows(face_value, coupon_rate, years_to_maturity, freq):
    periods = int(np.floor(years_to_maturity * freq))
    coupon_payment = (coupon_rate / freq) * face_value
    cashflows = [coupon_payment] * periods
    if periods > 0: cashflows[-1] += face_value
    return cashflows

def calculate_theoretical_price(cashflows, discount_rate, freq):
    pv_sum = 0
    for t, cf in enumerate(cashflows, 1):
        pv_sum += cf / ((1 + discount_rate / freq) ** t)
    return pv_sum

# --- INTERFACE DA APLICAÇÃO ---
st.title("💰 Painel de Análise de Renda Fixa")
st.markdown("Um cockpit para monitorar as condições dos mercados e analisar o valor relativo de títulos de dívida.")
start_date = datetime.now() - timedelta(days=5*365)

tab_us, tab_br, tab_analyzer = st.tabs(["Mercado Americano (Referência)", "Mercado Brasileiro", "Analisador de Títulos"])

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


# --- ABA DO ANALISADOR DE TÍTULOS ---
with tab_analyzer:
    st.header("Analisador de Valor Relativo de Títulos")
    st.info("Esta ferramenta calcula o 'preço justo' de um título com base nas condições de mercado atuais (juros e spreads) e o compara com o preço real de negociação.")

    # --- INPUTS DO ANALISTA ---
    st.markdown("##### 1. Insira as Características do Título")
    col1, col2, col3 = st.columns(3)
    with col1:
        market_price_pct = st.number_input("Preço de Mercado Atual (% Valor de Face)", 1.0, value=99.0, step=0.1, format="%.2f")
        face_value = st.number_input("Valor de Face", 1, value=1000)
    with col2:
        coupon_rate_pct = st.number_input("Taxa de Cupom Anual (%)", 0.0, value=6.0, step=0.1, format="%.2f")
        maturity_date = st.date_input("Data de Vencimento", pd.to_datetime("2034-07-15"))
    with col3:
        risk_levels = {"Soberano/AAA": "AAA", "Investment Grade (A-BBB)": "BBB", "High Yield (BB+ ou abaixo)": "HY"}
        risk_level = st.selectbox("Nível de Risco do Emissor", options=list(risk_levels.keys()))
        freq = st.selectbox("Frequência do Cupom", [2, 1], format_func=lambda x: "Semestral" if x == 2 else "Anual")
    
    analyze_bond_button = st.button("Analisar Valor Relativo do Título")

    if analyze_bond_button:
        # --- PREPARAÇÃO DOS DADOS DE MERCADO ---
        us_yield_curve = get_us_yield_curve_data()
        spread_codes = {"BBB": "BAMLC0A4CBBB", "HY": "BAMLH0A0HYM2"}
        spreads_df = get_fred_series({k: v for k, v in spread_codes.items() if k in risk_levels.values()}, "2000-01-01")
        
        if us_yield_curve.empty or spreads_df.empty:
            st.error("Não foi possível carregar os dados de mercado necessários para a análise.")
        else:
            # --- CÁLCULO ---
            years_to_maturity = (maturity_date - datetime.now().date()).days / 365.25
            if years_to_maturity <= 0: st.error("Data de vencimento deve ser no futuro."); st.stop()

            # 1. Obter Taxa Livre de Risco interpolada da curva de juros
            maturities_num = {'1 Mês':1/12,'3 Meses':3/12,'6 Meses':6/12,'1 Ano':1,'2 Anos':2,'3 Anos':3,'5 Anos':5,'7 Anos':7,'10 Anos':10,'20 Anos':20,'30 Anos':30}
            us_yield_curve['PrazoNum'] = us_yield_curve['Prazo'].map(maturities_num)
            risk_free_rate = np.interp(years_to_maturity, us_yield_curve['PrazoNum'], us_yield_curve['Taxa (%)']) / 100

            # 2. Obter Spread de Crédito
            selected_risk = risk_levels[risk_level]
            credit_spread = 0
            if selected_risk != "AAA":
                credit_spread = spreads_df[selected_risk].iloc[-1] / 100

            # 3. Calcular Taxa de Desconto Teórica e Preço Justo
            theoretical_discount_rate = risk_free_rate + credit_spread
            bond_cashflows = calculate_bond_cashflows(face_value, coupon_rate_pct/100, years_to_maturity, freq)
            theoretical_price = calculate_theoretical_price(bond_cashflows, theoretical_discount_rate, freq)
            
            # --- EXIBIÇÃO DOS RESULTADOS ---
            st.divider()
            st.markdown("##### 2. Resultados da Análise de Mercado")
            
            res1, res2, res3 = st.columns(3)
            with res1:
                st.metric("Preço Justo de Mercado (Teórico)", f"{theoretical_price:,.2f}",
                          help=f"Calculado com taxa livre de risco de {risk_free_rate*100:.2f}% + spread de {credit_spread*100:.2f}%.")
            with res2:
                market_price = market_price_pct/100 * face_value
                st.metric("Preço de Mercado (Informado)", f"{market_price:,.2f}")
            with res3:
                diff = ((market_price / theoretical_price) - 1) * 100
                st.metric("Diferença (Prêmio/Desconto)", f"{diff:.2f}%", 
                          delta=f"{'Caro' if diff > 0 else 'Barato'}", delta_color="inverse",
                          help="Se positivo, o título está sendo negociado mais caro que o preço justo teórico. Se negativo, mais barato.")
            
            st.info(f"**Conclusão:** Com uma taxa de desconto exigida pelo mercado de **{theoretical_discount_rate*100:.2f}%** (para este prazo e risco), o preço justo do título seria **{theoretical_price:,.2f}**. O preço de mercado atual de **{market_price:,.2f}** está **{'%.2f%% %s' % (abs(diff), 'acima (caro)' if diff > 0 else 'abaixo (barato)')}** deste valor.")
            
            # Visualização na Curva de Juros
            with st.expander("Ver Posição do Título na Curva de Juros"):
                fig = px.line(us_yield_curve, x='Prazo', y='Taxa (%)', title="Curva de Juros dos EUA vs. Taxa Exigida pelo Título", markers=True)
                # Adiciona o ponto da taxa teórica
                fig.add_scatter(x=[f"{years_to_maturity:.1f} Anos"], y=[theoretical_discount_rate*100], mode='markers', marker=dict(size=12, color='red'), name='Taxa Exigida (Justa)')
                st.plotly_chart(fig, use_container_width=True)
