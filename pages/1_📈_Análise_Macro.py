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
FOMC_MEETINGS_FILE = "fomc_meetings.json"
REPORTS_DIR = "reports"
REPORTS_DIR_FOMC = "reports_fomc"
COPOM_MEETINGS_FILE = "copom_meetings.json"
REPORTS_DIR_COPOM = "reports_copom"

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
if 'copom_meetings' not in st.session_state: st.session_state.copom_meetings = load_data(COPOM_MEETINGS_FILE)

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
    """
    Busca dados de fechamento de mercado para uma lista de tickers.
    """
    try:
        # CORREÇÃO: Alterado de 'Adj Close' para 'Close' para maior robustez.
        # A coluna 'Close' é mais universal entre diferentes tipos de ativos (índices, commodities, etc.)
        data = yf.download(tickers, start=start_date)['Close']
        
        # Se baixar só um ticker, o yfinance não retorna um DF, mas uma Série.
        # Esta parte do código converte para DataFrame para manter a consistência.
        if isinstance(data, pd.Series):
            data = data.to_frame(tickers[0])
            
        return data.dropna(how='all') # Usar how='all' para não dropar linhas se um dos ativos não tiver dado no dia
        
    except Exception as e:
        st.error(f"Falha ao buscar dados de mercado com yfinance: {e}")
        return pd.DataFrame()

# ADICIONE ESTA FUNÇÃO JUNTO COM AS OUTRAS FUNÇÕES AUXILIARES
def calculate_performance_metrics(prices_df):
    """Calcula métricas de performance para um DataFrame de preços."""
    metrics = []
    # Usaremos o juro de 3 meses do tesouro americano como taxa livre de risco
    risk_free_rate_series = fetch_fred_series("DGS3MO", start_date)
    risk_free_rate = (risk_free_rate_series.iloc[-1] / 100) if not risk_free_rate_series.empty else 0.02

    for col in prices_df.columns:
        prices = prices_df[col].dropna()
        if prices.empty:
            continue
            
        # Retorno no ano (YTD)
        ytd_prices = prices[prices.index.year == datetime.now().year]
        ytd_return = (ytd_prices.iloc[-1] / ytd_prices.iloc[0] - 1) if not ytd_prices.empty else 0

        # Retorno em 12 meses
        return_12m = (prices.iloc[-1] / prices.iloc[-252] - 1) if len(prices) > 252 else 0
        
        # Volatilidade Anualizada
        returns = prices.pct_change()
        volatility = returns.std() * np.sqrt(252)
        
        # Índice de Sharpe
        sharpe_ratio = (return_12m - risk_free_rate) / volatility if volatility > 0 else 0
        
        metrics.append({
            "Ativo": col,
            "Retorno YTD": f"{ytd_return:.2%}",
            "Retorno 12M": f"{return_12m:.2%}",
            "Volatilidade Anual.": f"{volatility:.2%}",
            "Índice de Sharpe": f"{sharpe_ratio:.2f}"
        })
        
    return pd.DataFrame(metrics).set_index("Ativo")

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
    subtab_br_activity, subtab_br_jobs, subtab_br_inflation, subtab_br_yield, subtab_br_bc = st.tabs(["Atividade", "Mercado de Trabalho", "Inflação", "Curva de Juros", "Visão do BCB"])
    
    with subtab_br_activity:
        st.subheader("Indicadores de Atividade Econômica e Confiança")
        st.caption("Acompanhe os principais setores que movem o PIB brasileiro, do sentimento do consumidor aos dados consolidados.")
        st.divider()

        # 1. Confiança do Consumidor
        # Código SGS BCB: 4393
        plot_indicator_with_analysis(
            'bcb', {'ICC': 4393},
            "Confiança do Consumidor (FGV)",
            "Mede o otimismo dos consumidores em relação à economia. Níveis acima de 100 indicam otimismo. É um indicador antecedente do consumo.",
            "Índice", hline=100
        )
        st.divider()

        # 2. Volume de Serviços
        # Código SGS BCB: 21864 (variação anual)
        plot_indicator_with_analysis(
            'bcb', {'PMS': 21864},
            "Volume de Serviços (PMS)",
            "Mede a evolução do volume de receita do setor de serviços, o maior componente do PIB brasileiro.",
            "Var. Anual %", is_pct_change=False # O dado já vem como variação
        )
        st.divider()

        # 3. Produção Industrial
        # Código SGS BCB: 21859 (variação anual)
        plot_indicator_with_analysis(
            'bcb', {'PIM': 21859},
            "Produção Industrial (PIM-PF)",
            "Mede a produção física da indústria de transformação e extrativa. Um termômetro da saúde do setor secundário.",
            "Var. Anual %", is_pct_change=False # O dado já vem como variação
        )
        st.divider()

        # 5. IBC-Br
        # Código SGS BCB: 24369
        plot_indicator_with_analysis(
            'bcb', {'IBC-Br': 24369},
            "IBC-Br (Prévia do PIB)",
            "Índice de Atividade Econômica do BCB, considerado uma 'prévia' mensal do Produto Interno Bruto (PIB).",
            "Índice"
        )

    with subtab_br_jobs:
        st.subheader("Indicadores do Mercado de Trabalho Brasileiro")
        st.caption("Analise a dinâmica do emprego e da renda, fatores cruciais para o consumo e a saúde social do país.")
        st.divider()

        # 1. Taxa de Desemprego
        # Código SGS BCB: 24369
        plot_indicator_with_analysis(
            'bcb', {'Desemprego': 24369},
            "Taxa de Desemprego (PNADC)",
            "Percentual da força de trabalho que está desocupada, mas procurando ativamente por emprego. Medido pela PNAD Contínua (IBGE).",
            "%"
        )
        st.divider()

        # 2. Renda Real com Carteira (YoY)
        # Código SGS BCB: 28795
        plot_indicator_with_analysis(
            'bcb', {'Renda Formal': 28795},
            "Renda Média Real (Trabalhador com Carteira)",
            "Variação real (descontada a inflação) acumulada em 12 meses do rendimento médio do trabalhador com carteira assinada no setor privado.",
            "Var. Anual %",
            is_pct_change=False # O dado já vem como variação
        )
        st.divider()

        # 3. Renda Real do Setor Privado (YoY)
        # Código SGS BCB: 28794
        plot_indicator_with_analysis(
            'bcb', {'Renda Total': 28794},
            "Renda Média Real (Todos os Trabalhos - Setor Privado)",
            "Variação real (descontada a inflação) acumulada em 12 meses do rendimento médio de todos os trabalhos no setor privado (formais e informais).",
            "Var. Anual %",
            is_pct_change=False # O dado já vem como variação
        )

    with subtab_br_inflation:
        st.subheader("Indicadores de Inflação e Preços")
        st.caption("Acompanhe a dinâmica de preços ao consumidor (IPCA) e ao produtor (IGP-M), fator essencial para as decisões de juros.")
        st.divider()

        # 1. IPCA (Cheio)
        # Código SGS BCB: 433
        plot_indicator_with_analysis(
            'bcb', {'IPCA': 433},
            "IPCA (Variação Mensal)",
            "Índice de Preços ao Consumidor Amplo, a medida oficial de inflação no Brasil. A meta do BCB é baseada no seu acumulado em 12 meses.",
            unit="%",
            hline=0
        )
        st.divider()

        # 2. Média dos Núcleos do IPCA
        # Código SGS BCB: 11427
        plot_indicator_with_analysis(
            'bcb', {'Núcleos': 11427},
            "Média dos Núcleos do IPCA (Variação Mensal)",
            "Média das medidas de núcleo que excluem os itens mais voláteis. É usada pelo Banco Central para identificar a tendência da inflação.",
            unit="%",
            hline=0
        )
        st.divider()

        # Layout para Bens e Serviços
        st.markdown("##### Decomposição do IPCA: Bens vs. Serviços")
        col1, col2 = st.columns(2)
        with col1:
            # 3. IPCA Bens Industrializados
            # Código SGS BCB: 4449
            plot_indicator_with_analysis(
                'bcb', {'Bens': 4449},
                "IPCA - Bens Industrializados (MoM)",
                "Componente do IPCA que mede a variação de preços de produtos, sensíveis ao câmbio e custos de produção.",
                unit="%",
                hline=0
            )
        with col2:
            # 4. IPCA Serviços
            # Código SGS BCB: 4448
            plot_indicator_with_analysis(
                'bcb', {'Serviços': 4448},
                "IPCA - Serviços (MoM)",
                "Componente do IPCA que mede a variação de preços do setor de serviços, mais sensível à dinâmica do mercado de trabalho e salários.",
                unit="%",
                hline=0
            )
        st.divider()

        # 5. IGP-M
        # Código SGS BCB: 189
        plot_indicator_with_analysis(
            'bcb', {'IGPM': 189},
            "IGP-M (Variação Mensal)",
            "Índice Geral de Preços do Mercado. Mede a inflação de forma mais ampla, incluindo preços ao produtor. Conhecido como a 'inflação do aluguel'.",
            unit="%",
            hline=0
        )
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

    # SUBSTITUA TODO O CONTEÚDO DESTA ABA
    with subtab_br_bc:
        st.subheader("Painel de Política Monetária - Banco Central do Brasil")
        st.caption("Acompanhe os principais indicadores, o balanço e a comunicação do banco central brasileiro.")
        st.markdown("##### Indicadores Chave da Política Monetária e Fiscal")
    
        # --- INDICADORES CHAVE ---
        col1, col2 = st.columns(2)
        with col1:
            # PIB Acumulado 12M - Código SGS BCB: 4380
            plot_indicator_with_analysis('bcb', {'PIB': 4380}, "PIB Acumulado 12 Meses", "Variação real do Produto Interno Bruto acumulado nos últimos 12 meses.", unit="%", is_pct_change=False)
            st.divider()
            # Base Monetária - Código SGS BCB: 13621
            plot_indicator_with_analysis('bcb', {'Base Monetaria': 13621}, "Base Monetária", "Soma do papel-moeda em poder do público e das reservas bancárias. Reflete a 'impressão de dinheiro' pelo BCB.", unit="R$ Bilhões")
    
        with col2:
            # Dívida Líquida / PIB - Código SGS BCB: 4513
            plot_indicator_with_analysis('bcb', {'Divida/PIB': 4513}, "Dívida Líquida / PIB", "Principal indicador de saúde fiscal do país. Mede a dívida líquida do setor público como percentual do PIB.", unit="%")
            st.divider()
            # M2 - Código SGS BCB: 27841
            plot_indicator_with_analysis('bcb', {'M2': 27841}, "Agregado Monetário M2", "Medida ampla da oferta de moeda, incluindo papel-moeda, depósitos à vista e depósitos de poupança. Indica a liquidez na economia.", unit="R$ Bilhões")
        
        st.divider()
    
        # --- ACOMPANHAMENTO DO COPOM (ADAPTADO DO FOMC) ---
        st.subheader("Acompanhamento Histórico do Discurso do COPOM")
        
        meetings = st.session_state.get('copom_meetings', []) # Usar .get para segurança
        if not meetings:
            st.info("Nenhum registro de reunião do COPOM foi adicionado ainda.")
        else:
            sorted_meetings = sorted(meetings, key=lambda x: x['meeting_date'], reverse=True)
            meeting_dates = [m['meeting_date'] for m in sorted_meetings]
            selected_date = st.selectbox("Selecione a data da Reunião do COPOM para analisar:", meeting_dates, key="copom_date_select")
            
            selected_meeting = next((m for m in sorted_meetings if m['meeting_date'] == selected_date), None)
            
            if selected_meeting:
                st.metric("Decisão da Taxa Selic", selected_meeting.get("decision", "N/A"))
                
                # Análise Hawkish/Dovish
                h_score = selected_meeting.get("analysis", {}).get("hawkish", 0)
                d_score = selected_meeting.get("analysis", {}).get("dovish", 0)
                final_tone = "Hawkish 🦅" if h_score > d_score else "Dovish 🕊️" if d_score > h_score else "Neutro 😐"
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Placar Hawkish", h_score)
                c2.metric("Placar Dovish", d_score)
                c3.metric("Tom Predominante", final_tone)
                
                # Botão de Download
                if selected_meeting.get("pdf_path") and os.path.exists(selected_meeting["pdf_path"]):
                    with open(selected_meeting["pdf_path"], "rb") as pdf_file:
                        st.download_button("Baixar Ata em PDF", data=pdf_file, file_name=os.path.basename(selected_meeting["pdf_path"]), key=f"download_copom_{selected_date}")
                
                with st.expander("Ver texto completo da ata"):
                    st.text(selected_meeting.get("minutes_text", "Texto não disponível."))

        # --- MODO EDITOR (ADAPTADO PARA O COPOM) ---
        if st.session_state.get("role") == "Analista":
            st.divider()
            st.markdown("---")
            st.header("📝 Modo Editor - Reuniões do COPOM")
            
            editor_tab1, editor_tab2 = st.tabs(["Adicionar Nova Reunião", "Gerenciar Reuniões Existentes"])
            
            with editor_tab1:
                with st.form("new_copom_meeting_form"):
                    st.markdown("##### Adicionar Registro de Nova Reunião do COPOM")
                    m_date = st.date_input("Data da Reunião", key="copom_m_date")
                    m_decision = st.text_input("Decisão da Selic (ex: Manteve em 10,50%)", key="copom_m_decision")
                    m_text = st.text_area("Cole aqui o texto completo da ata:", height=250, key="copom_m_text")
                    m_pdf = st.file_uploader("Anexar arquivo da ata em PDF", key="copom_m_pdf")
                    
                    if st.form_submit_button("Salvar Nova Reunião do COPOM"):
                        if m_text and m_decision:
                            # ADAPTADO PARA O BCB: lang='pt'
                            h, d = analyze_central_bank_discourse(m_text, lang='pt')
                            new_meeting = {"meeting_date": m_date.strftime("%Y-%m-%d"), "decision": m_decision, "minutes_text": m_text, "pdf_path": "", "analysis": {"hawkish": h, "dovish": d}}
                            
                            if m_pdf:
                                if not os.path.exists(REPORTS_DIR_COPOM): os.makedirs(REPORTS_DIR_COPOM)
                                file_path = os.path.join(REPORTS_DIR_COPOM, m_pdf.name)
                                with open(file_path, "wb") as f: f.write(m_pdf.getbuffer())
                                new_meeting["pdf_path"] = file_path
                            
                            st.session_state.copom_meetings.append(new_meeting)
                            save_data(st.session_state.copom_meetings, COPOM_MEETINGS_FILE)
                            st.success("Nova reunião do COPOM salva com sucesso!"); st.rerun()
                        else:
                            st.error("Data, Decisão e Texto da Ata são campos obrigatórios.")
    
            with editor_tab2:
                st.markdown("##### Excluir um Registro de Reunião")
                if not st.session_state.get('copom_meetings', []):
                    st.info("Nenhuma reunião para gerenciar.")
                else:
                    sorted_meetings_delete = sorted(st.session_state.copom_meetings, key=lambda x: x['meeting_date'], reverse=True)
                    for i, meeting in enumerate(sorted_meetings_delete):
                        st.markdown(f"**Reunião de {meeting['meeting_date']}**")
                        if st.button("Excluir este registro", key=f"delete_copom_{meeting['meeting_date']}"):
                            st.session_state.copom_meetings = [m for m in st.session_state.copom_meetings if m['meeting_date'] != meeting['meeting_date']]
                            save_data(st.session_state.copom_meetings, COPOM_MEETINGS_FILE)
                            st.success("Registro excluído!"); st.rerun()
                        st.divider()
    
    # --- ABA EUA (VERSÃO CORRIGIDA) ---
with tab_us:
    st.header("Principais Indicadores dos Estados Unidos")
        
    subtab_us_activity, subtab_us_jobs, subtab_us_inflation, subtab_us_real_estate, subtab_us_yield, subtab_us_fed = st.tabs(["Atividade", "Mercado de Trabalho", "Inflação", "Imobiliário", "Curva de Juros", "Visão do Fed"])
        
    with subtab_us_activity:
        st.subheader("Indicadores de Atividade Econômica")
        st.caption("Analise a saúde dos setores industrial e de serviços, além da força do consumo, os principais motores da economia americana.")
        st.divider()
    
        st.markdown("#### Setor Industrial")
        col1, col2 = st.columns(2)
        with col1:
            # Novas Ordens de Manufatura - FRED: AMTMNO
            plot_indicator_with_analysis('fred', "AMTMNO", "Novas Ordens da Indústria (Manufatura)", "Mede o valor de novos pedidos feitos à indústria. É um indicador antecedente chave da produção futura.", "Var. Anual %", is_pct_change=True)
        with col2:
            # Emprego na Manufatura - FRED: MANEMP
            plot_indicator_with_analysis('fred', "MANEMP", "Emprego na Indústria (Manufatura)", "Número de trabalhadores empregados no setor industrial. Indica a saúde e a capacidade de expansão do setor.", "Var. Anual %", is_pct_change=True)
    
        # Salários na Manufatura - FRED: CES3000000003
        plot_indicator_with_analysis('fred', "CES3000000003", "Salário Médio por Hora na Indústria", "Mede a evolução do custo da mão de obra na indústria. Importante para pressões de custos e inflação de bens.", "Var. Anual %", is_pct_change=True)
        st.divider()
    
        st.markdown("#### Serviços, Consumo e Atividade Geral")
        col3, col4 = st.columns(2)
        with col3:
            # Emprego em Serviços - FRED: USPBS
            plot_indicator_with_analysis('fred', "USPBS", "Emprego em Serviços Profissionais", "Número de trabalhadores em serviços de alto valor agregado. Reflete a força do setor terciário, o maior da economia.", "Var. Anual %", is_pct_change=True)
            # Produção Industrial - FRED: INDPRO
            plot_indicator_with_analysis('fred', "INDPRO", "Produção Industrial Total", "Mede a produção física total das fábricas, minas e serviços de utilidade pública no país.", "Var. Anual %", is_pct_change=True)
    
        with col4:
            # Consumo Pessoal (PCE) - FRED: PCEC96
            plot_indicator_with_analysis('fred', "PCEC96", "Consumo Pessoal Real (PCE)", "Mede os gastos totais dos consumidores, ajustados pela inflação. É o principal componente do PIB.", "Var. Anual %", is_pct_change=True)
            # Vendas no Varejo - FRED: RSXFS
            plot_indicator_with_analysis('fred', "RSXFS", "Vendas no Varejo (Ex-Alimentação)", "Mede o total de vendas de bens no varejo. Indicador chave da força do consumo das famílias.", "Var. Anual %", is_pct_change=True)
    
        # Sentimento do Consumidor - FRED: UMCSENT
        plot_indicator_with_analysis('fred', "UMCSENT", "Sentimento do Consumidor (Univ. Michigan)", "Mede a confiança dos consumidores na economia. Um sentimento alto geralmente precede maiores gastos.", "Índice")

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
        st.divider()
    
        # --- SEÇÃO DO CPI ---
        st.markdown("#### Consumer Price Index (CPI) - Inflação ao Consumidor")
        # Gráficos do CPI Cheio e Núcleo (Anual)
        col_cpi1, col_cpi2 = st.columns(2)
        with col_cpi1:
            plot_indicator_with_analysis('fred', "CPIAUCSL", "CPI Cheio", "Mede a variação de preços de uma cesta ampla de bens e serviços.", is_pct_change=True, unit="Var. Anual %")
        with col_cpi2:
            plot_indicator_with_analysis('fred', "CPILFESL", "Core CPI (Núcleo)", "Exclui os componentes voláteis de alimentos e energia para medir a tendência de fundo da inflação.", is_pct_change=True, unit="Var. Anual %")
    
        st.markdown("###### Decomposição do CPI (Variação Mensal)")
        # Gráficos dos Componentes de Bens e Serviços (Mensal)
        col_cpi3, col_cpi4 = st.columns(2)
        with col_cpi3:
            # CPI de Bens Duráveis (MoM)
            cpi_durables = fetch_fred_series("CUSR0000SAD", start_date).pct_change(1).dropna() * 100
            if not cpi_durables.empty:
                fig = px.area(cpi_durables, title="CPI - Bens Duráveis (Variação Mensal)")
                fig.update_layout(showlegend=False, yaxis_title="Var. Mensal %")
                fig.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig, use_container_width=True, key="cpi_durables")
        with col_cpi4:
            # CPI de Serviços (MoM)
            cpi_services = fetch_fred_series("CUSR0000SASLE", start_date).pct_change(1).dropna() * 100
            if not cpi_services.empty:
                fig = px.area(cpi_services, title="CPI - Serviços (Variação Mensal)")
                fig.update_layout(showlegend=False, yaxis_title="Var. Mensal %")
                fig.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig, use_container_width=True, key="cpi_services")
        st.divider()
    
        # --- SEÇÃO DO PCE ---
        st.markdown("#### Personal Consumption Expenditures (PCE) - A Métrica do Fed")
        col_pce1, col_pce2 = st.columns(2)
        with col_pce1:
            plot_indicator_with_analysis('fred', "PCEPI", "PCE Cheio", "A medida de inflação preferida pelo Fed. Sua cesta é mais ampla e dinâmica que a do CPI.", is_pct_change=True, unit="Var. Anual %")
        with col_pce2:
            plot_indicator_with_analysis('fred', "PCEPILFE", "Core PCE (Núcleo)", "O indicador mais importante para a política monetária. A meta do Fed é de 2% para este núcleo.", is_pct_change=True, unit="Var. Anual %")
        st.divider()
    
        # --- SEÇÃO DO PPI E EXPECTATIVAS ---
        st.markdown("#### Inflação ao Produtor (PPI) e Expectativas")
        col_ppi1, col_ppi2 = st.columns(2)
        with col_ppi1:
            # PPI Cheio (YoY) - FRED: PPIACO
            plot_indicator_with_analysis('fred', "PPIACO", "PPI Cheio", "Mede a variação de preços na porta da fábrica. É um indicador antecedente da inflação ao consumidor (CPI).", is_pct_change=True, unit="Var. Anual %")
        with col_ppi2:
            # Core PPI (YoY) - FRED: WPSFD4131
            plot_indicator_with_analysis('fred', "WPSFD4131", "Core PPI (Núcleo)", "Exclui os componentes voláteis de alimentos e energia do PPI para medir a tendência de custos de produção.", is_pct_change=True, unit="Var. Anual %")
    
        # Expectativa de Inflação (Michigan) - FRED: MICH
        plot_indicator_with_analysis('fred', "MICH", "Expectativa de Inflação (Univ. Michigan - 1 Ano)", "Mede a inflação que os consumidores esperam para os próximos 12 meses. Importante para ancoragem das expectativas.", unit="%")

    with subtab_us_real_estate:
        st.subheader("Indicadores do Mercado Imobiliário Americano")
        st.caption("O setor imobiliário é um dos mais sensíveis aos juros e um dos principais motores do ciclo econômico dos EUA.")
        st.divider()
    
        # --- CUSTO DE FINANCIAMENTO ---
        st.markdown("#### Custo de Financiamento")
        # FRED: MORTGAGE30US
        plot_indicator_with_analysis(
            'fred', "MORTGAGE30US",
            "Taxa de Financiamento Imobiliário 30 Anos",
            "Mede o custo médio do crédito para compra de imóveis. É o principal fator que afeta a demanda por casas.",
            unit="%"
        )
        st.divider()
    
        # --- PIPELINE DE OFERTA ---
        st.markdown("#### Pipeline de Oferta (Novas Construções)")
        col1, col2 = st.columns(2)
        with col1:
            # FRED: PERMIT
            plot_indicator_with_analysis(
                'fred', "PERMIT",
                "Permissões de Construção (Permits)",
                "Número de novas autorizações de construção emitidas. É o principal indicador antecedente da atividade de construção futura.",
                unit="Milhares", is_pct_change=True
            )
        with col2:
            # FRED: HOUST
            plot_indicator_with_analysis(
                'fred', "HOUST",
                "Casas Iniciadas (Housing Starts)",
                "Número de novas construções de casas que foram iniciadas. Confirma a tendência apontada pelos 'Permits'.",
                unit="Milhares", is_pct_change=True
            )
        st.divider()
        
        # --- ATIVIDADE DE VENDAS E ESTOQUE ---
        st.markdown("#### Atividade de Vendas e Estoque")
        col3, col4 = st.columns(2)
        with col3:
            # FRED: HSN1F
            plot_indicator_with_analysis(
                'fred', "HSN1F",
                "Venda de Casas Novas",
                "Número de casas recém-construídas que foram vendidas. Mede a absorção da nova oferta pelo mercado.",
                unit="Milhares", is_pct_change=True
            )
        with col4:
            # FRED: EXHOSLUSM495S
            plot_indicator_with_analysis(
                'fred', "EXHOSLUSM495S",
                "Venda de Casas Usadas",
                "Número de casas existentes (usadas) que foram vendidas. Representa a maior parte do mercado imobiliário.",
                unit="Milhares", is_pct_change=True
            )
        # FRED: NHFSEPUCS
        plot_indicator_with_analysis(
            'fred', "NHFSEPUCS",
            "Estoque de Casas Novas à Venda",
            "Número de casas recém-construídas que estão no mercado, mas ainda não foram vendidas. Mede o nível de 'estoque' do setor.",
            unit="Milhares", is_pct_change=True
        )
        st.divider()
    
        # --- PREÇOS ---
        st.markdown("#### Preços")
        # FRED: CSUSHPISA
        plot_indicator_with_analysis(
            'fred', "CSUSHPISA",
            "Índice de Preços de Imóveis (Case-Shiller)",
            "Principal índice de preços de imóveis residenciais nas 20 maiores cidades dos EUA. Reflete o resultado da dinâmica de oferta e demanda.",
            unit="Índice", is_pct_change=True
        )

    with subtab_us_yield:
        st.subheader("Análise da Curva de Juros Americana")
        st.caption("A forma e os spreads da curva de juros são um dos principais indicadores antecedentes da atividade econômica.")
        st.divider()
    
        # --- NOVOS INDICADORES ADICIONADOS AQUI ---
        st.markdown("##### Taxa Básica e Juro Real")
        col1, col2 = st.columns(2)
        with col1:
            # Fed Funds Rate - FRED: FEDFUNDS
            plot_indicator_with_analysis(
                'fred', "FEDFUNDS",
                "Fed Funds Rate (Taxa Básica)",
                "A principal taxa de juros de política monetária, definida pelo Fed. É a âncora para o custo do dinheiro na economia.",
                unit="%"
            )
        with col2:
            # 10-Year TIPS - FRED: DFII10
            plot_indicator_with_analysis(
                'fred', "DFII10",
                "Juro Real de 10 Anos (TIPS)",
                "Rendimento dos títulos de 10 anos protegidos da inflação (TIPS). Mostra o retorno real esperado pelos investidores.",
                unit="%",
                hline=0
            )
        st.divider()
    
        # --- SEÇÕES EXISTENTES MANTIDAS ABAIXO ---
        st.markdown("##### Forma da Curva de Juros Atual")
        yield_curve_df = get_us_yield_curve_data()
        if not yield_curve_df.empty:
            fig_curve = px.line(yield_curve_df, x='Prazo', y='Taxa (%)', title="Curva de Juros do Tesouro Americano", markers=True)
            st.plotly_chart(fig_curve, use_container_width=True, key="us_yield_curve")
        else:
            st.warning("Não foi possível carregar os dados para a forma da curva de juros.")
        st.divider()
    
        st.markdown("##### Spreads da Curva de Juros (Indicadores de Recessão)")
        col3, col4 = st.columns(2)
        with col3:
            j10a = fetch_fred_series("DGS10", start_date)
            j2a = fetch_fred_series("DGS2", start_date)
            if not j10a.empty and not j2a.empty:
                spread = (j10a - j2a).dropna()
                fig = px.area(spread, title="Spread 10 Anos - 2 Anos")
                fig.add_hline(y=0, line_dash="dash", line_color="red")
                st.plotly_chart(fig, use_container_width=True, key="spread_10y_2y")
        with col4:
            j2a_s = fetch_fred_series("DGS2", start_date)
            j3m = fetch_fred_series("DGS3MO", start_date)
            if not j2a_s.empty and not j3m.empty:
                spread = (j2a_s - j3m).dropna()
                fig = px.area(spread, title="Spread 2 Anos - 3 Meses")
                fig.add_hline(y=0, line_dash="dash", line_color="red")
                st.plotly_chart(fig, use_container_width=True, key="spread_2y_3m")

    with subtab_us_fed:
        st.subheader("Painel de Política Monetária - Federal Reserve (Fed)")
        st.caption("Acompanhe a economia, a saúde fiscal e os agregados monetários que guiam as decisões do banco central americano.")
        st.divider()
    
        st.markdown("##### Indicadores Econômicos, Fiscais e Monetários")
        
        # --- NOVA ESTRUTURA DE INDICADORES ---
        col1, col2 = st.columns(2)
        with col1:
            # PIB (Real GDP) - FRED: GDPC1
            plot_indicator_with_analysis(
                'fred', "GDPC1",
                "PIB Real dos EUA",
                "Mede o valor de todos os bens e serviços produzidos na economia, ajustado pela inflação. O principal termômetro da atividade econômica.",
                unit="Var. Anual %",
                is_pct_change=True
            )
        with col2:
            # Dívida/PIB - FRED: GFDEGDQ188S
            plot_indicator_with_analysis(
                'fred', "GFDEGDQ188S",
                "Dívida Pública / PIB",
                "Mede a dívida total do governo federal como um percentual do PIB. Um indicador chave da saúde fiscal do país.",
                unit="%"
            )
    
        # Ativos do Fed - FRED: WALCL
        balance_sheet = fetch_fred_series("WALCL", start_date)
        if not balance_sheet.empty:
            # A divisão por 1M é para exibir em Trilhões, por isso o gráfico é manual
            fig_bal = px.area(balance_sheet / 1000000, title="Ativos Totais no Balanço do Fed")
            fig_bal.update_layout(showlegend=False, yaxis_title="$ Trilhões")
            st.plotly_chart(fig_bal, use_container_width=True, key="fed_balance_sheet")
        else:
            st.warning("Não foi possível carregar dados do balanço do Fed.")
        
        st.divider()
        col3, col4 = st.columns(2)
        with col3:
            # M1 Money Supply - FRED: M1SL
            plot_indicator_with_analysis(
                'fred', "M1SL",
                "Agregado Monetário M1",
                "Mede a oferta de moeda mais líquida (papel-moeda e depósitos à vista).",
                unit="Var. Anual %",
                is_pct_change=True
            )
        with col4:
            # M2 Money Supply - FRED: M2SL
            plot_indicator_with_analysis(
                'fred', "M2SL",
                "Agregado Monetário M2",
                "Medida mais ampla que o M1, incluindo também depósitos a prazo e fundos do mercado monetário.",
                unit="Var. Anual %",
                is_pct_change=True
            )
        
        # --- SEÇÃO DE ANÁLISE DE DISCURSO (MANTIDA) ---
        st.divider()
        st.subheader("Acompanhamento Histórico do Discurso do FOMC")
        
        meetings = st.session_state.get('fomc_meetings', [])
        if not meetings:
            st.info("Nenhum registro de reunião do FOMC foi adicionado ainda.")
        else:
            # O resto da lógica de visualização e edição do FOMC continua aqui, inalterada...
            sorted_meetings = sorted(meetings, key=lambda x: x['meeting_date'], reverse=True)
            meeting_dates = [m['meeting_date'] for m in sorted_meetings]
            selected_date = st.selectbox("Selecione a data da Reunião do FOMC para analisar:", meeting_dates, key="fomc_date_select")
            
            selected_meeting = next((m for m in sorted_meetings if m['meeting_date'] == selected_date), None)
            
            if selected_meeting:
                st.metric("Decisão de Juros Tomada", selected_meeting.get("decision", "N/A"))
                h_score = selected_meeting.get("analysis", {}).get("hawkish", 0)
                d_score = selected_meeting.get("analysis", {}).get("dovish", 0)
                final_tone = "Hawkish 🦅" if h_score > d_score else "Dovish 🕊️" if d_score > h_score else "Neutro 😐"
                
                c1_fomc, c2_fomc, c3_fomc = st.columns(3)
                c1_fomc.metric("Placar Hawkish", h_score)
                c2_fomc.metric("Placar Dovish", d_score)
                c3_fomc.metric("Tom Predominante", final_tone)
                
                if selected_meeting.get("pdf_path") and os.path.exists(selected_meeting["pdf_path"]):
                    with open(selected_meeting["pdf_path"], "rb") as pdf_file:
                        st.download_button("Baixar Ata em PDF", data=pdf_file, file_name=os.path.basename(selected_meeting["pdf_path"]), key=f"download_fomc_{selected_date}")
                
                with st.expander("Ver texto completo da ata"):
                    st.text(selected_meeting.get("minutes_text", "Texto não disponível."))
    
        # --- MODO EDITOR (MANTIDO) ---
        if st.session_state.get("role") == "Analista":
            # A lógica do modo editor do FOMC continua aqui, inalterada...
            st.divider()
            st.markdown("---")
            st.header("📝 Modo Editor - Reuniões do FOMC")
            
            editor_tab1, editor_tab2 = st.tabs(["Adicionar Nova Reunião", "Gerenciar Reuniões Existentes"])
            
            with editor_tab1:
                with st.form("new_meeting_form"):
                    st.markdown("##### Adicionar Registro de Nova Reunião")
                    m_date = st.date_input("Data da Reunião", key="fomc_m_date")
                    m_decision = st.text_input("Decisão de Juros (ex: Manteve em 5.25%-5.50%)", key="fomc_m_decision")
                    m_text = st.text_area("Cole aqui o texto completo da ata:", height=250, key="fomc_m_text")
                    m_pdf = st.file_uploader("Anexar arquivo da ata em PDF", key="fomc_m_pdf")
                    
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
                if not st.session_state.get('fomc_meetings', []):
                    st.info("Nenhuma reunião para gerenciar.")
                else:
                    sorted_meetings_delete = sorted(st.session_state.fomc_meetings, key=lambda x: x['meeting_date'], reverse=True)
                    for i, meeting in enumerate(sorted_meetings_delete):
                        st.markdown(f"**Reunião de {meeting['meeting_date']}**")
                        if st.button("Excluir este registro", key=f"delete_fomc_{meeting['meeting_date']}"):
                            st.session_state.fomc_meetings = [m for m in st.session_state.fomc_meetings if m['meeting_date'] != meeting['meeting_date']]
                            save_data(st.session_state.fomc_meetings, FOMC_MEETINGS_FILE)
                            st.success("Registro excluído!"); st.rerun()
                        st.divider()


# --- ABA MERCADOS GLOBAIS ---
with tab_global:
    st.header("Índices e Indicadores de Mercado Global")
    subtab_equity, subtab_commodities, subtab_risk, subtab_valuation, subtab_big_players = st.tabs(["Ações", "Commodities", "Risco", "Valuation", "Visão dos Big Players"])
    with subtab_equity:
    st.subheader("Análise de Performance de Índices Globais")
    tickers = {"S&P 500": "^GSPC", "Ibovespa": "^BVSP", "Nasdaq": "^IXIC", "DAX (Alemanha)": "^GDAXI", "Nikkei (Japão)": "^N225"}
    
    # --- SEÇÃO 1: GRÁFICO DE PERFORMANCE ---
    sel = st.multiselect("Selecione os índices:", options=list(tickers.keys()), default=["S&P 500", "Ibovespa"])
    
    if sel:
        selected_tickers_map = {name: code for name, code in tickers.items() if name in sel}
        data = fetch_market_data(list(selected_tickers_map.values()))
        
        if not data.empty:
            # Renomeia as colunas de volta para os nomes amigáveis
            data.rename(columns={code: name for name, code in selected_tickers_map.items()}, inplace=True)
            
            st.markdown("##### Performance Normalizada (Base 100)")
            st.plotly_chart(px.line((data / data.dropna().iloc[0]) * 100, title="Performance Relativa dos Índices"), use_container_width=True)
            
            # --- SEÇÃO 2: TABELA DE MÉTRICAS DE PERFORMANCE ---
            st.markdown("##### Métricas de Performance e Risco")
            st.dataframe(calculate_performance_metrics(data), use_container_width=True)
            st.divider()

            # --- SEÇÃO 3: ANÁLISE DE RISCO (VOLATILIDADE MÓVEL) ---
            st.markdown("##### Volatilidade Móvel (60 dias)")
            st.caption("A volatilidade móvel mostra a evolução do risco (desvio-padrão dos retornos) ao longo do tempo.")
            rolling_vol = data.pct_change().rolling(window=60).std() * np.sqrt(252)
            st.plotly_chart(px.line(rolling_vol, title="Volatilidade Anualizada Móvel (60d)"), use_container_width=True)
            st.divider()

    # --- SEÇÃO 4: ANÁLISE DE VALUATION ---
    st.markdown("##### Análise de Valuation (P/L do S&P 500)")
    # FRED: MULTPL/SP500_PE_RATIO_MONTH
    plot_indicator_with_analysis(
        'fred', "MULTPL/SP500_PE_RATIO_MONTH",
        "Índice Preço/Lucro (P/L) do S&P 500",
        "Mede quantas vezes o preço do índice negocia em relação ao lucro das empresas. Usado para avaliar se o mercado está 'caro' ou 'barato' frente à sua história.",
        unit="Ratio"
    )
    st.divider()

    # --- SEÇÃO 5: ANÁLISE DE ESTILO/FATOR ---
    st.markdown("##### Análise de Estilo: Growth vs. Value")
    factor_tickers = {"Growth (Crescimento)": "VUG", "Value (Valor)": "VTV"}
    factor_data = fetch_market_data(list(factor_tickers.values()))
    if not factor_data.empty:
        factor_data.rename(columns={code: name for name, code in factor_tickers.items()}, inplace=True)
        # Ratio de performance
        factor_ratio = (factor_data["Growth (Crescimento)"] / factor_data["Value (Valor)"]).dropna()
        st.plotly_chart(px.line(factor_ratio, title="Ratio de Performance: Growth vs. Value"), use_container_width=True)
        st.caption("Um ratio crescente indica que ações de 'Growth' estão performando melhor que ações de 'Value'.")
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
