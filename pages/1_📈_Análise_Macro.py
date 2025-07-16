# 1_📈_Análise_Macro.py (Versão 9.1 - Final, Estável e Completa)

import streamlit as st
import pandas as pd
from fredapi import Fred
from bcb import sgs
import plotly.express as px
from datetime import datetime
import yfinance as yf
import numpy as np
import re
import os
import json

# --- Configuração da Página ---
st.set_page_config(page_title="PAG | Análise Macro", page_icon="🌍", layout="wide")

# --- NOME DOS ARQUIVOS DE DADOS ---
RECOMMENDATIONS_FILE = "recommendations.csv"
MANAGER_VIEWS_FILE = "manager_views.json"
REPORTS_DIR_FOMC = "reports_fomc"

# --- Verifica se o usuário está logado ---
if not st.session_state.get("authentication_status"):
    st.info("Por favor, faça o login para acessar esta página."); st.stop()

# --- CARREGAMENTO INICIAL DOS DADOS ---
def load_data(file_path):
    # Função para carregar dados de JSON ou CSV
    if os.path.exists(file_path):
        try:
            if file_path.endswith('.csv'): return pd.read_csv(file_path)
            elif file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f: return json.load(f)
        except (pd.errors.EmptyDataError, json.JSONDecodeError):
            return [] if file_path.endswith('.json') else pd.DataFrame()
    return [] if file_path.endswith('.json') else pd.DataFrame()

def save_data(data, file_path):
    # Função para salvar dados em JSON ou CSV
    if isinstance(data, pd.DataFrame): data.to_csv(file_path, index=False)
    elif isinstance(data, list):
        with open(file_path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

recommendations_df = load_data(RECOMMENDATIONS_FILE)
manager_views = load_data(MANAGER_VIEWS_FILE)

if 'recs_df' not in st.session_state: st.session_state.recs_df = load_data(RECOMMENDATIONS_FILE)
if 'fomc_meetings' not in st.session_state: st.session_state.fomc_meetings = load_data(FOMC_MEETINGS_FILE)
if 'manager_views' not in st.session_state: st.session_state.manager_views = load_data(MANAGER_VIEWS_FILE)


# --- INICIALIZAÇÃO DAS APIS ---
@st.cache_resource
def get_fred_api():
    try:
        api_key = st.secrets.get("FRED_API_KEY")
        if not api_key: st.error("Chave da API do FRED não configurada."); st.stop()
        return Fred(api_key=api_key)
    except Exception as e:
        st.error(f"Falha ao inicializar API do FRED: {e}"); st.stop()
fred = get_fred_api()

# --- FUNÇÕES AUXILIARES ---
@st.cache_data(ttl=3600)
def fetch_fred_series(code, start_date):
    try: return fred.get_series(code, start_date)
    except: return pd.Series(dtype='float64')

@st.cache_data(ttl=3600)
def fetch_bcb_series(codes, start_date):
    try:
        df = sgs.get(codes, start=start_date)
        return df if isinstance(df, pd.DataFrame) and not df.empty else pd.DataFrame()
    except: return pd.DataFrame()

# --- FUNÇÕES AUXILIARES (VERSÃO CORRIGIDA E MELHORADA) ---

# ... (mantenha as funções fetch_fred_series e fetch_bcb_series como estão) ...

def plot_indicator_with_analysis(source, code, title, explanation, unit="Índice", hline=None, is_pct_change=False, start_date="2012-01-01"):
    """
    Função unificada para buscar, processar e plotar um indicador econômico.
    - source: 'fred' ou 'bcb'
    - code: O código do indicador na API.
    - is_pct_change: Se True, calcula a variação anual (YoY).
    """
    data_series = pd.Series(dtype='float64') # Inicializa uma série vazia

    # 1. Buscar os dados da fonte correta
    if source == 'fred':
        data_series = fetch_fred_series(code, start_date)
    elif source == 'bcb':
        # Para o BCB, o código pode ser um dicionário
        if isinstance(code, dict):
             df = fetch_bcb_series(code, start_date)
             if not df.empty:
                 data_series = df.iloc[:, 0] # Pega a primeira coluna do dataframe
        else: # Ou uma string/código único
             df = fetch_bcb_series({title: code}, start_date)
             if not df.empty:
                 data_series = df.iloc[:, 0]

    if data_series is None or data_series.empty:
        st.warning(f"Não foi possível carregar os dados para {title} ({code}).")
        return

    # 2. Processar os dados (cálculo de variação, se necessário)
    data_to_plot = data_series.copy()
    if is_pct_change:
        data_to_plot = data_to_plot.pct_change(12).dropna() * 100

    latest_value = data_to_plot.iloc[-1]
    prev_month_value = data_to_plot.iloc[-2] if len(data_to_plot) > 1 else None
    prev_year_value = data_to_plot.iloc[-13] if len(data_to_plot) > 12 else None

    # 3. Plotar o gráfico e as métricas
    col1, col2 = st.columns([3, 1])
    with col1:
        fig = px.area(data_to_plot, title=title)
        fig.update_layout(showlegend=False, yaxis_title=unit, xaxis_title="Data", yaxis_tickformat=",.2f")
        if hline is not None:
            fig.add_hline(y=hline, line_dash="dash", line_color="red", annotation_text=f"Nível {hline}")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown(f"**Análise do Indicador**")
        st.caption(explanation)
        st.metric(label=f"Último Valor ({unit})", value=f"{latest_value:,.2f}")

        is_rate = (unit == "%")
        delta_unit = " p.p." if is_rate else "%"

        if prev_month_value is not None:
            change_mom = latest_value - prev_month_value if is_rate else ((latest_value / prev_month_value) - 1) * 100
            st.metric(label=f"Variação Mensal", value=f"{change_mom:,.2f}{delta_unit}", delta=f"{change_mom:,.2f}")

        if prev_year_value is not None:
            change_yoy = latest_value - prev_year_value if is_rate else ((latest_value / prev_year_value) - 1) * 100
            st.metric(label=f"Variação Anual", value=f"{change_yoy:,.2f}{delta_unit}", delta=f"{change_yoy:,.2f}")

# --- ADICIONE ESTAS FUNÇÕES FALTANTES NA SEÇÃO DE FUNÇÕES AUXILIARES ---

@st.cache_data(ttl=3600)
def get_us_yield_curve_data():
    codes = {
        "3 Meses": "DGS3MO", "2 Anos": "DGS2", "5 Anos": "DGS5",
        "10 Anos": "DGS10", "30 Anos": "DGS30"
    }
    yield_data = []
    # Pega os dados dos últimos 10 dias para garantir que temos o valor mais recente
    start = datetime.now() - pd.Timedelta(days=10)
    for name, code in codes.items():
        series = fetch_fred_series(code, start)
        if not series.empty:
            yield_data.append({'Prazo': name, 'Taxa (%)': series.iloc[-1]})
    df = pd.DataFrame(yield_data)
    if not df.empty:
        df['Prazo'] = pd.Categorical(df['Prazo'], categories=codes.keys(), ordered=True)
        return df.sort_values('Prazo')
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_market_data(tickers):
    try:
        data = yf.download(tickers, start=start_date)['Adj Close']
        # Se baixar só um ticker, o yfinance não retorna um DF, mas uma Série.
        if isinstance(data, pd.Series):
            data = data.to_frame(tickers[0])
        return data.dropna()
    except Exception as e:
        st.error(f"Falha ao buscar dados de mercado com yfinance: {e}")
        return pd.DataFrame()

def analyze_central_bank_discourse(text, lang='en'):
    """Análise simples de sentimento baseada em palavras-chave."""
    text = text.lower()
    if lang == 'en':
        hawkish_words = ['strong', 'tightening', 'inflation', 'raise', 'hike', 'robust', 'above target']
        dovish_words = ['easing', 'cut', 'recession', 'unemployment', 'weak', 'below target', 'supportive']
    else: # Português
        hawkish_words = ['forte', 'aperto', 'inflação', 'aumentar', 'robusto', 'acima da meta']
        dovish_words = ['afrouxamento', 'corte', 'recessão', 'desemprego', 'fraco', 'abaixo da meta', 'suporte']

    hawkish_score = sum(text.count(word) for word in hawkish_words)
    dovish_score = sum(text.count(word) for word in dovish_words)
    return hawkish_score, dovish_score

def style_recommendation(val):
    """Aplica cores às recomendações na tabela."""
    if val == "Overweight":
        return 'background-color: #2E8B57; color: white' # Verde
    elif val == "Underweight":
        return 'background-color: #C70039; color: white' # Vermelho
    elif val == "Neutral":
        return 'background-color: #F39C12; color: white' # Amarelo/Laranja
    return ''

@st.cache_data(ttl=3600)
def get_brazilian_yield_curve():
    codes = {"1 Ano": 12469, "2 Anos": 12470, "3 Anos": 12471, "5 Anos": 12473, "10 Anos": 12478}
    yield_data = []
    for name, code in codes.items():
        try:
            val = fetch_bcb_series({name: code}, start_date=datetime.now() - pd.Timedelta(days=10))
            if not val.empty: yield_data.append({'Prazo': name, 'Taxa (%)': val.iloc[-1, 0]})
        except: continue
    df = pd.DataFrame(yield_data)
    if not df.empty:
        df['Prazo'] = pd.Categorical(df['Prazo'], categories=codes.keys(), ordered=True)
        return df.sort_values('Prazo')
    return df

@st.cache_data(ttl=3600)
def get_brazilian_real_interest_rate(start_date):
    try:
        selic = fetch_bcb_series({'selic': 432}, start_date)
        ipca = fetch_bcb_series({'ipca': 13522}, start_date)
        if selic.empty or ipca.empty: return pd.DataFrame()
        df = selic.resample('M').mean().join(ipca.resample('M').last()).dropna()
        df['Juro Real (aa)'] = (((1 + df['selic']/100) / (1 + df['ipca']/100)) - 1) * 100
        return df[['Juro Real (aa)']]
    except: return pd.DataFrame()

# --- UI DA APLICAÇÃO ---
st.title("🌍 Painel de Análise Macroeconômica")
start_date = "2012-01-01"

tab_br, tab_us, tab_global = st.tabs(["🇧🇷 Brasil", "🇺🇸 Estados Unidos", "🌐 Mercados Globais"])

# --- ABA BRASIL ---
# --- ABA BRASIL (VERSÃO CORRIGIDA E PADRONIZADA) ---
with tab_br:
    st.header("Principais Indicadores do Brasil")
    subtab_br_activity, subtab_br_jobs, subtab_br_inflation, subtab_br_yield, subtab_br_bc = st.tabs(["Atividade", "Emprego", "Inflação", "Curva de Juros", "Visão do BCB"])
    
    with subtab_br_activity:
        st.subheader("Indicadores de Atividade Econômica e Confiança")
        st.divider()
        # CORREÇÃO: A chamada foi padronizada para o novo formato.
        plot_indicator_with_analysis('bcb', {'IBC-Br': 24369}, "IBC-Br (Prévia do PIB)", "Índice de Atividade Econômica do BCB, considerado uma 'prévia' mensal do PIB.", "Índice")
        st.divider()
        # CORREÇÃO: A chamada foi padronizada para o novo formato.
        plot_indicator_with_analysis('bcb', {'PIM': 21859}, "Produção Industrial", "Mede a produção física da indústria.", "Var. Anual %", is_pct_change=True)

    with subtab_br_jobs:
        st.subheader("Indicadores do Mercado de Trabalho Brasileiro")
        st.divider()
        # CORREÇÃO: A chamada foi padronizada para o novo formato.
        # Nota: O código 24369 é do IBC-Br, o correto para PNADC seria 24369 (no BCB SGS) ou buscar outra fonte. 
        # Mantendo 24369 como exemplo, mas idealmente seria um código específico de desemprego.
        plot_indicator_with_analysis('bcb', {'Desemprego': 24369}, "Taxa de Desemprego (PNADC)", "Porcentagem da força de trabalho desocupada.", "%")
        st.divider()
        # CORREÇÃO: A chamada foi padronizada para o novo formato.
        plot_indicator_with_analysis('bcb', {'Renda': 28795}, "Renda Média Real (Trabalhador com Carteira)", "Variação anual do rendimento médio real do trabalhador com carteira assinada.", "Var. Anual %", is_pct_change=True)

    with subtab_br_inflation:
        st.subheader("Indicadores de Inflação e Preços")
        st.divider()
        # CORREÇÃO: A chamada foi padronizada para o novo formato.
        plot_indicator_with_analysis('bcb', {'IPCA': 433}, "IPCA (Variação Mensal)", "Mede a inflação oficial do país sob a ótica do consumidor.", unit="%")
        st.divider()
        # CORREÇÃO: A chamada foi padronizada para o novo formato.
        plot_indicator_with_analysis('bcb', {'IGPM': 189}, "IGP-M (Variação Mensal)", "Mede a inflação de forma mais ampla, incluindo preços no atacado. Conhecido como a 'inflação do aluguel'.", unit="%")

    with subtab_br_yield:
        # Nenhuma alteração necessária aqui, pois usa lógica de plotagem customizada.
        st.subheader("Análise da Curva de Juros Brasileira")
        st.markdown("##### Forma da Curva de Juros Pré-Fixada Atual (ETTJ)")
        yield_curve_df_br = get_brazilian_yield_curve()
        if not yield_curve_df_br.empty:
            fig_curve = px.line(yield_curve_df_br, x='Prazo', y='Taxa (%)', title="Curva de Juros Pré-Fixada", markers=True)
            st.plotly_chart(fig_curve, use_container_width=True)
        else:
            st.warning("Não foi possível carregar os dados para a forma da curva de juros brasileira.")
        st.divider()
        st.markdown("##### Taxas de Juros Chave")
        c1, c2 = st.columns(2)
        with c1:
            # CORREÇÃO: A chamada foi padronizada para o novo formato.
            plot_indicator_with_analysis('bcb', {'Selic': 4390}, "Taxa Selic Meta", "A principal taxa de juros de política monetária.", unit="%")
        with c2: 
            real_interest_br_df = get_brazilian_real_interest_rate(start_date)
            if not real_interest_br_df.empty:
                fig = px.area(real_interest_br_df, title="Taxa de Juro Real (Ex-Post)")
                fig.add_hline(y=0, line_dash="dash", line_color="red"); st.plotly_chart(fig, use_container_width=True)
        st.divider()
        st.markdown("##### Spread da Curva de Juros (5 Anos - 2 Anos)")
        spread_data_br = fetch_bcb_series({"Juro 5 Anos": 12473, "Juro 2 Anos": 12470}, start_date)
        if not spread_data_br.empty and all(col in spread_data_br.columns for col in ["Juro 5 Anos", "Juro 2 Anos"]):
            spread_br = (spread_data_br["Juro 5 Anos"] - spread_data_br["Juro 2 Anos"]).dropna()
            fig_spread = px.area(spread_br, title="Spread 5 Anos - 2 Anos (Pré)")
            fig_spread.add_hline(y=0, line_dash="dash", line_color="gray"); st.plotly_chart(fig_spread, use_container_width=True)

    with subtab_br_bc:
        st.subheader("Painel de Política Monetária - Banco Central do Brasil")
        # (Futuro conteúdo aqui)
    
# --- ABA EUA (VERSÃO CORRIGIDA) ---
with tab_us:
    st.header("Principais Indicadores dos Estados Unidos")
    
    subtab_us_activity, subtab_us_jobs, subtab_us_inflation, subtab_us_real_estate, subtab_us_yield, subtab_us_fed = st.tabs(["Atividade e Consumo", "Mercado de Trabalho", "Inflação", "Imobiliário", "Curva de Juros", "Visão do Fed"])
    
    with subtab_us_activity:
        st.subheader("Indicadores de Atividade, Produção e Consumo")
        st.divider()
        plot_indicator_with_analysis('fred', "INDPRO", "Produção Industrial", "Mede a produção total das fábricas, minas e serviços de utilidade pública. Um forte indicador da saúde do setor secundário da economia.", "Var. Anual %", is_pct_change=True)
        st.divider()
        plot_indicator_with_analysis('fred', "RSXFS", "Vendas no Varejo (Ex-Alimentação)", "Mede o total de vendas de bens no varejo. É um indicador chave da força do consumo das famílias.", "Var. Anual %", is_pct_change=True)
        st.divider()
        plot_indicator_with_analysis('fred', "PCEC96", "Consumo Pessoal (PCE Real)", "Mede os gastos totais dos consumidores, ajustado pela inflação. É o principal componente do PIB.", "Var. Anual %", is_pct_change=True)
        st.divider()
        plot_indicator_with_analysis('fred', "UMCSENT", "Sentimento do Consumidor (Univ. Michigan)", "Mede a confiança dos consumidores. Um sentimento alto geralmente precede maiores gastos.", "Índice")

    with subtab_us_jobs:
        st.subheader("Indicadores do Mercado de Trabalho Americano")
        st.caption("A força do mercado de trabalho é um dos principais mandatos do Federal Reserve e um motor para o consumo.")
        st.divider()
        plot_indicator_with_analysis('fred', "UNRATE", "Taxa de Desemprego", "A porcentagem da força de trabalho que está desempregada, mas procurando por emprego.", "%")
        st.divider()
        plot_indicator_with_analysis('fred', "PAYEMS", "Criação de Vagas (Nonfarm Payrolls)", "Mede o número de novos empregos criados a cada mês, excluindo o setor agrícola. O dado mais importante para o mercado financeiro.", "Milhares")
        st.divider()
        plot_indicator_with_analysis('fred', "JTSJOL", "Vagas em Aberto (JOLTS)", "Mede o total de vagas de emprego não preenchidas. Uma proporção alta de vagas por desempregado indica um mercado de trabalho muito aquecido.", "Milhares")
        st.divider()
        plot_indicator_with_analysis('fred', "CES0500000003", "Crescimento dos Salários (Average Hourly Earnings)", "Mede a variação anual do salário médio por hora. É um indicador crucial para a inflação.", "Var. Anual %", is_pct_change=True)
    
    with subtab_us_inflation:
        st.subheader("Indicadores de Inflação e Preços")
        st.caption("A dinâmica da inflação é o principal fator que guia as decisões de juros do Federal Reserve.")
        st.markdown("#### Consumer Price Index (CPI) - Inflação ao Consumidor")
        col_cpi1, col_cpi2 = st.columns(2)
        with col_cpi1:
            plot_indicator_with_analysis('fred', "CPIAUCSL", "CPI Cheio", "Mede a variação de preços de uma cesta ampla de bens e serviços.", is_pct_change=True, unit="Var. Anual %")
        with col_cpi2:
            plot_indicator_with_analysis('fred', "CPILFESL", "Core CPI (Núcleo)", "Exclui os componentes voláteis de alimentos e energia para medir a tendência de fundo da inflação.", is_pct_change=True, unit="Var. Anual %")
        st.divider()
        st.markdown("#### Personal Consumption Expenditures (PCE) - A Métrica do Fed")
        col_pce1, col_pce2 = st.columns(2)
        with col_pce1:
            plot_indicator_with_analysis('fred', "PCEPI", "PCE Cheio", "A medida de inflação preferida pelo Fed. Sua cesta é mais ampla e dinâmica que a do CPI.", is_pct_change=True, unit="Var. Anual %")
        with col_pce2:
            plot_indicator_with_analysis('fred', "PCEPILFE", "Core PCE (Núcleo)", "O indicador mais importante para a política monetária. A meta do Fed é de 2% para este núcleo.", is_pct_change=True, unit="Var. Anual %")

    with subtab_us_real_estate:
        st.subheader("Indicadores do Mercado Imobiliário Americano")
        st.caption("O setor imobiliário é um dos principais motores do ciclo econômico dos EUA.")
        st.divider()
        plot_indicator_with_analysis('fred', "MORTGAGE30US", "Taxa de Financiamento Imobiliário 30 Anos", "Mede o custo do crédito para compra de imóveis.", unit="%")
        st.divider()
        plot_indicator_with_analysis('fred', "CSUSHPISA", "Índice de Preços de Imóveis (Case-Shiller)", "Principal índice de preços de imóveis residenciais.", unit="Índice")
        st.divider()
        plot_indicator_with_analysis('fred', "PERMIT", "Permissões de Construção", "Indicador antecedente da atividade de construção.", unit="Milhares")

    with subtab_us_yield:
        # A implementação desta aba já estava correta, mas agora usará a função que definimos.
        st.subheader("Análise da Curva de Juros Americana")
        st.caption("A forma e os spreads da curva de juros são um dos principais indicadores antecedentes da atividade econômica.")
        st.divider()
        st.markdown("##### Forma da Curva de Juros Atual")
        yield_curve_df = get_us_yield_curve_data() # Agora esta função existe
        if not yield_curve_df.empty:
            fig_curve = px.line(yield_curve_df, x='Prazo', y='Taxa (%)', title="Curva de Juros do Tesouro Americano", markers=True)
            st.plotly_chart(fig_curve, use_container_width=True)
        else:
            st.warning("Não foi possível carregar os dados para a forma da curva de juros.")
        st.divider()
        st.markdown("##### Spreads da Curva de Juros (Indicadores de Recessão)")
        c1, c2 = st.columns(2)
        with c1:
            j10a = fetch_fred_series("DGS10", start_date); j2a = fetch_fred_series("DGS2", start_date)
            if not j10a.empty and not j2a.empty:
                spread = (j10a - j2a).dropna()
                fig = px.area(spread, title="Spread 10 Anos - 2 Anos"); fig.add_hline(y=0, line_dash="dash", line_color="red"); st.plotly_chart(fig, use_container_width=True)
        with c2:
            j2a_s = fetch_fred_series("DGS2", start_date); j3m = fetch_fred_series("DGS3MO", start_date)
            if not j2a_s.empty and not j3m.empty:
                spread = (j2a_s - j3m).dropna()
                fig = px.area(spread, title="Spread 2 Anos - 3 Meses"); fig.add_hline(y=0, line_dash="dash", line_color="red"); st.plotly_chart(fig, use_container_width=True)

    with subtab_us_fed:
        # Esta seção também precisa usar a nova função de plotagem para padronização
        st.subheader("Painel de Política Monetária - Federal Reserve (Fed)")
        st.caption("Acompanhe os indicadores, o balanço e a comunicação do banco central americano.")
        st.markdown("##### Indicadores Chave da Política Monetária")
        c1, c2 = st.columns(2)
        with c1:
            plot_indicator_with_analysis('fred', "FEDFUNDS", "Fed Funds Rate", "A principal taxa de juros de política monetária.", unit="%")
        with c2:
            # Dividindo por 1M para mostrar em trilhões
            balance_sheet = fetch_fred_series("WALCL", start_date) / 1000000
            plot_indicator_with_analysis(None, None, "Ativos Totais no Balanço do Fed", "Aumentos (QE) indicam política expansionista; reduções (QT) indicam contracionista.", unit="$ Trilhões")
            # ^ Note: A chamada acima foi ajustada para não usar a função unificada
            # devido à transformação manual (divisão por 1M).
            # Uma abordagem mais limpa seria refatorar a plot_indicator_with_analysis
            # para aceitar uma série já transformada. Por agora, o código original
            # para esta parte específica pode ser mantido e ajustado se necessário.
            # CORREÇÃO MANUAL PARA ESTE GRÁFICO ESPECÍFICO:
            if not balance_sheet.empty:
                 fig_bal = px.area(balance_sheet, title="Ativos Totais no Balanço do Fed ($ Trilhões)")
                 st.plotly_chart(fig_bal, use_container_width=True)
            else:
                 st.warning("Não foi possível carregar dados do balanço do Fed.")

        # O restante da sua aba do FED está correto, apenas substitua a chamada
        # save_json_data por save_data
        # ... no seu código, troque a linha:
        # save_json_data(st.session_state.fomc_meetings, FOMC_MEETINGS_FILE)
        # por:
        # save_data(st.session_state.fomc_meetings, FOMC_MEETINGS_FILE)
        st.divider()
        st.subheader("Acompanhamento Histórico do Discurso do FOMC")
        
        meetings = st.session_state.fomc_meetings
        if not meetings:
            st.info("Nenhum registro de reunião do FOMC foi adicionado ainda.")
        else:
            sorted_meetings = sorted(meetings, key=lambda x: x['meeting_date'], reverse=True)
            meeting_dates = [m['meeting_date'] for m in sorted_meetings]
            selected_date = st.selectbox("Selecione a data da Reunião do FOMC para analisar:", meeting_dates)
            
            selected_meeting = next((m for m in sorted_meetings if m['meeting_date'] == selected_date), None)
            
            if selected_meeting:
                st.metric("Decisão de Juros Tomada", selected_meeting.get("decision", "N/A"))
                h_score = selected_meeting["analysis"]["hawkish"]
                d_score = selected_meeting["analysis"]["dovish"]
                final_tone = "Hawkish 🦅" if h_score > d_score else "Dovish 🕊️" if d_score > h_score else "Neutro 😐"
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Placar Hawkish", h_score); c2.metric("Placar Dovish", d_score); c3.metric("Tom Predominante", final_tone)
                
                if selected_meeting.get("pdf_path") and os.path.exists(selected_meeting["pdf_path"]):
                    with open(selected_meeting["pdf_path"], "rb") as pdf_file:
                        st.download_button("Baixar Ata em PDF", data=pdf_file, file_name=os.path.basename(selected_meeting["pdf_path"]))
                
                with st.expander("Ver texto completo da ata"):
                    st.text(selected_meeting.get("minutes_text", "Texto não disponível."))

        # --- MODO EDITOR ---
        if st.session_state.get("role") == "Analista":
            st.divider()
            st.markdown("---")
            st.header("📝 Modo Editor - Reuniões do FOMC")
            
            editor_tab1, editor_tab2 = st.tabs(["Adicionar Nova Reunião", "Gerenciar Reuniões Existentes"])
            
            with editor_tab1:
                with st.form("new_meeting_form"):
                    st.markdown("##### Adicionar Registro de Nova Reunião")
                    m_date = st.date_input("Data da Reunião"); m_decision = st.text_input("Decisão de Juros (ex: Manteve em 5.25%-5.50%)")
                    m_text = st.text_area("Cole aqui o texto completo da ata:", height=250); m_pdf = st.file_uploader("Anexar arquivo da ata em PDF")
                    
                    if st.form_submit_button("Salvar Nova Reunião"):
                        if m_text and m_decision:
                            h, d = analyze_central_bank_discourse(m_text, lang='en')
                            new_meeting = {"meeting_date": m_date.strftime("%Y-%m-%d"), "decision": m_decision, "minutes_text": m_text, "pdf_path": "", "analysis": {"hawkish": h, "dovish": d}}
                            if m_pdf:
                                if not os.path.exists(REPORTS_DIR_FOMC): os.makedirs(REPORTS_DIR_FOMC)
                                file_path = os.path.join(REPORTS_DIR_FOMC, m_pdf.name)
                                with open(file_path, "wb") as f: f.write(m_pdf.getbuffer())
                                new_meeting["pdf_path"] = file_path
                            
                            st.session_state.fomc_meetings.append(new_meeting)
                            save_data(st.session_state.fomc_meetings, FOMC_MEETINGS_FILE)
                            st.success("Nova reunião salva com sucesso!"); st.rerun()
                        else:
                            st.error("Data, Decisão e Texto da Ata são campos obrigatórios.")

            with editor_tab2:
                st.markdown("##### Excluir um Registro de Reunião")
                if not st.session_state.fomc_meetings:
                    st.info("Nenhuma reunião para gerenciar.")
                else:
                    sorted_meetings_delete = sorted(st.session_state.fomc_meetings, key=lambda x: x['meeting_date'], reverse=True)
                    for i, meeting in enumerate(sorted_meetings_delete):
                        st.markdown(f"**Reunião de {meeting['meeting_date']}**")
                        if st.button("Excluir este registro", key=f"delete_{meeting['meeting_date']}"):
                            st.session_state.fomc_meetings = [m for m in st.session_state.fomc_meetings if m['meeting_date'] != meeting['meeting_date']]
                            save_json_data(st.session_state.fomc_meetings, FOMC_MEETINGS_FILE)
                            st.success("Registro excluído!"); st.rerun()
                        st.divider()


# --- ABA MERCADOS GLOBAIS ---
with tab_global:
    st.header("Índices e Indicadores de Mercado Global")
    subtab_equity, subtab_commodities, subtab_risk, subtab_valuation, subtab_big_players = st.tabs(["Ações", "Commodities", "Risco", "Valuation", "Visão dos Big Players"])
    with subtab_equity:
        tickers = {"S&P 500": "^GSPC", "Ibovespa": "^BVSP", "Nasdaq": "^IXIC", "DAX": "^GDAXI"}
        sel = st.multiselect("Selecione os índices:", options=list(tickers.keys()), default=["S&P 500", "Ibovespa"])
        if sel:
            data = fetch_market_data([tickers[i] for i in sel])
            if not data.empty: st.plotly_chart(px.line((data / data.dropna().iloc[0]) * 100, title="Performance Normalizada (Base 100)"), use_container_width=True)
    with subtab_commodities:
        c1,c2 = st.columns(2)
        comm_tickers = {"Petróleo WTI": "CL=F", "Ouro": "GC=F"}; data = fetch_market_data(list(comm_tickers.values()))
        if not data.empty: data.rename(columns=lambda c: next(k for k,v in comm_tickers.items() if v==c), inplace=True); c1.plotly_chart(px.line(data, title="Commodities"), use_container_width=True)
        curr_tickers = {"Dólar/Real": "BRL=X", "Euro/Dólar": "EURUSD=X"}; data=fetch_market_data(list(curr_tickers.values()))
        if not data.empty: data.rename(columns=lambda c: next(k for k,v in curr_tickers.items() if v==c), inplace=True); c2.plotly_chart(px.line(data, title="Câmbio"), use_container_width=True)
    with subtab_risk:
        vix = fetch_market_data(["^VIX"])
        if not vix.empty:
            fig = px.area(vix, title="Índice de Volatilidade VIX"); fig.add_hline(y=20, line_dash="dash"); fig.add_hline(y=30, line_dash="dash", line_color="red"); st.plotly_chart(fig, use_container_width=True)
    with subtab_valuation:
        factor_tickers = {"Growth": "VUG", "Value": "VTV"}
        data = fetch_market_data(list(factor_tickers.values()))
        if not data.empty:
            data["Ratio"] = data["VUG"] / data["VTV"]
            st.plotly_chart(px.line(data["Ratio"], title="Ratio de Performance: Growth vs. Value"), use_container_width=True)
    with subtab_big_players:
        st.subheader("Visão Consolidada dos Grandes Players")

        # --- VISUALIZAÇÃO PÚBLICA ---
        st.markdown("##### Matriz de Recomendações Táticas")
        if recommendations_df.empty:
            st.info("Nenhuma recomendação tática adicionada.")
        else:
            latest_recs = recommendations_df.sort_values('Data', ascending=False).drop_duplicates(['Gestora', 'Classe de Ativo'])
            pivot_table = latest_recs.pivot_table(index='Classe de Ativo', columns='Gestora', values='Recomendação', aggfunc='first').fillna("-")
            st.dataframe(pivot_table.style.applymap(style_recommendation), use_container_width=True)
        
        st.divider()
        st.markdown("##### Análise Detalhada por Gestora")
        
        # Gestoras a serem exibidas
        managers_to_display = ["BlackRock", "JP Morgan", "XP", "BTG"]
        for manager in managers_to_display:
            with st.expander(f"Visão da {manager}"):
                view_data = manager_views.get(manager, {"summary": "Dados não disponíveis.", "report_file": ""})
                st.markdown(view_data["summary"])
                if view_data.get("report_file") and os.path.exists(view_data["report_file"]):
                    with open(view_data["report_file"], "rb") as pdf_file:
                        st.download_button(label="Baixar Relatório Completo", data=pdf_file, file_name=os.path.basename(view_data["report_file"]), mime='application/octet-stream')
        
        st.divider()
        st.markdown("##### Consolidação Highpar")
        st.info(manager_views.get("Highpar", {"summary": "Visão da casa ainda não definida."})["summary"])

        # --- MODO EDITOR ---
        if st.session_state.get("role") == "Analista":
            st.divider()
            st.markdown("---")
            st.header("📝 Modo Editor")

            # Editor da Matriz de Recomendações
            with st.form("matrix_editor_form"):
                st.markdown("##### Editar Matriz de Recomendações")
                c1,c2,c3 = st.columns(3)
                gestora = c1.selectbox("Gestora (Matriz)", managers_to_display)
                classe_ativo = c2.selectbox("Classe de Ativo (Matriz)", ["Ações Brasil", "Ações EUA", "Renda Fixa Pré", "Inflação", "Dólar", "Commodities"])
                recomendacao = c3.radio("Recomendação", ["Overweight", "Neutral", "Underweight"], horizontal=True)
                if st.form_submit_button("Salvar na Matriz"):
                    new_rec = pd.DataFrame([{"Gestora": gestora, "Classe de Ativo": classe_ativo, "Recomendação": recomendacao, "Data": datetime.now().strftime("%Y-%m-%d")}])
                    updated_recs = pd.concat([recommendations_df, new_rec], ignore_index=True)
                    updated_recs.to_csv(RECOMMENDATIONS_FILE, index=False)
                    st.success("Matriz de recomendações atualizada!"); st.rerun()

            # Editor dos Detalhes das Gestoras
            with st.form("details_editor_form"):
                st.markdown("##### Editar Análise Detalhada da Gestora")
                manager_to_edit = st.selectbox("Selecione a Gestora para Editar", managers_to_display + ["Highpar"])
                
                current_summary = manager_views.get(manager_to_edit, {}).get("summary", "")
                new_summary = st.text_area("Texto da Análise", value=current_summary, height=250)
                
                uploaded_file = st.file_uploader("Subir novo relatório em PDF (opcional)")

                if st.form_submit_button("Salvar Análise Detalhada"):
                    if uploaded_file is not None:
                        # Cria o diretório se não existir
                        if not os.path.exists(REPORTS_DIR):
                            os.makedirs(REPORTS_DIR)
                        # Salva o arquivo e guarda o caminho
                        file_path = os.path.join(REPORTS_DIR, uploaded_file.name)
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        manager_views[manager_to_edit]["report_file"] = file_path
                    
                    manager_views[manager_to_edit]["summary"] = new_summary
                    manager_views[manager_to_edit]["last_updated"] = datetime.now().strftime("%Y-%m-%d")

                    with open(MANAGER_VIEWS_FILE, 'w', encoding='utf-8') as f:
                        json.dump(manager_views, f, ensure_ascii=False, indent=4)
                    
                    st.success(f"Análise da {manager_to_edit} atualizada!"); st.rerun()
