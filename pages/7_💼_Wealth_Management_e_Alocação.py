# pages/7_💼_Wealth_Management.py (Versão 4.0 - Final com Suitability Integrado)

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import yfinance as yf
import numpy as np
import time

# --- Configuração da Página ---
st.set_page_config(page_title="Wealth Management - Alocação", page_icon="💼", layout="wide")

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
# Usado para guardar o perfil do cliente entre as interações
if 'client_profile' not in st.session_state:
    st.session_state.client_profile = "Balanceado" # Começa com um perfil padrão

# --- DADOS: ALOCAÇÃO ESTRATÉGICA E BUILDING BLOCKS ---
portfolio_data = {
    "Conservador": {"Caixa": 20, "Renda Fixa Brasil": 50, "Renda Fixa Internacional": 15, "Ações Brasil": 5, "Ações Internacional": 5, "Fundos Imobiliários": 5, "Alternativos": 0},
    "Moderado": {"Caixa": 10, "Renda Fixa Brasil": 40, "Renda Fixa Internacional": 15, "Ações Brasil": 15, "Ações Internacional": 15, "Fundos Imobiliários": 5, "Alternativos": 0},
    "Balanceado": {"Caixa": 5, "Renda Fixa Brasil": 30, "Renda Fixa Internacional": 20, "Ações Brasil": 20, "Ações Internacional": 20, "Fundos Imobiliários": 5, "Alternativos": 0},
    "Crescimento": {"Caixa": 5, "Renda Fixa Brasil": 20, "Renda Fixa Internacional": 15, "Ações Brasil": 25, "Ações Internacional": 25, "Fundos Imobiliários": 5, "Alternativos": 5},
    "Agressivo": {"Caixa": 2, "Renda Fixa Brasil": 10, "Renda Fixa Internacional": 10, "Ações Brasil": 34, "Ações Internacional": 34, "Fundos Imobiliários": 5, "Alternativos": 5}
}
portfolio_list = list(portfolio_data.keys())

building_blocks_data = {
    "Caixa": [{"ticker": "Tesouro Selic (LFT)", "name": "Título Público Pós-Fixado", "rationale": "Principal ativo para reserva de emergência e posições de caixa."}],
    "Renda Fixa Brasil": [{"ticker": "IMAB11.SA", "name": "iShares IMA-B Fundo de Índice", "rationale": "Exposição a títulos públicos atrelados à inflação (NTN-Bs)."}],
    "Renda Fixa Internacional": [{"ticker": "BNDW", "name": "Vanguard Total World Bond ETF", "rationale": "ETF globalmente diversificado em títulos de alta qualidade de crédito."}],
    "Ações Brasil": [{"ticker": "BOVA11.SA", "name": "iShares Ibovespa Fundo de Índice", "rationale": "Exposição ampla ao principal índice de ações brasileiro."}],
    "Ações Internacional": [{"ticker": "IVV", "name": "iShares Core S&P 500 ETF", "rationale": "Exposição às 500 maiores empresas dos EUA."}],
    "Fundos Imobiliários": [{"ticker": "HGLG11.SA", "name": "CSHG Logística FII", "rationale": "Exemplo de FII de 'tijolo' de alta qualidade, focado no setor de galpões logísticos."}],
    "Alternativos": [{"ticker": "GOLD11.SA", "name": "Trend Ouro Fundo de Índice", "rationale": "Exposição ao Ouro como reserva de valor."}]
}

# --- FUNÇÕES AUXILIARES ---
def create_allocation_chart(portfolio_name, data):
    df = pd.DataFrame(list(data.items()), columns=['Classe de Ativo', 'Alocação (%)'])
    fig = px.pie(df, values='Alocação (%)', names='Classe de Ativo', title=f"<b>{portfolio_name}</b>", hole=.3, color_discrete_sequence=px.colors.sequential.GnBu_r)
    fig.update_traces(textposition='inside', textinfo='percent+label', insidetextfont=dict(size=14))
    fig.update_layout(showlegend=False, title_font_size=20, title_x=0.5, margin=dict(l=20, r=20, t=40, b=20))
    return fig

def get_asset_class(info, ticker_symbol):
    category = info.get('quoteType', '').upper()
    if category == 'EQUITY': return "Ações Brasil" if '.SA' in ticker_symbol.upper() else "Ações Internacional"
    if category == 'ETF':
        long_name = info.get('longName', '').upper()
        if any(term in long_name for term in ['FIXA', 'BOND', 'TREASURY']): return "Renda Fixa Internacional" if '.SA' not in ticker_symbol.upper() else "Renda Fixa Brasil"
        if any(term in long_name for term in ['FII', 'IMOBILIÁRIO', 'REAL ESTATE']): return "Fundos Imobiliários"
        if any(term in long_name for term in ['GOLD', 'OURO', 'COMMODITIES']): return "Alternativos"
        if any(term in long_name for term in ['IBOVESPA', 'SMALL', 'BRAZIL']): return "Ações Brasil"
        return "Ações Internacional"
    return "Alternativos"

@st.cache_data
def bulk_categorize_tickers(tickers_list):
    categories = {}
    for ticker in tickers_list:
        try:
            info = yf.Ticker(ticker).info
            if not info or 'quoteType' not in info: raise ValueError("Dados insuficientes.")
            categories[ticker] = get_asset_class(info, ticker)
            time.sleep(0.1)
        except Exception:
            categories[ticker] = "Não Classificado"
    return categories

@st.cache_data
def get_portfolio_price_data(tickers_list, period="3y"):
    return yf.download(tickers_list, period=period, progress=False)['Close'].dropna()

def calculate_portfolio_risk(prices, weights):
    if prices.empty or len(prices) < 252: return 0, 0, 0
    returns = prices.pct_change().dropna()
    p_return = np.sum(returns.mean() * weights) * 252
    p_vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
    p_sharpe = p_return / p_vol if p_vol > 0 else 0
    return p_return, p_vol, p_sharpe


# ADICIONE ESTA NOVA FUNÇÃO JUNTO COM AS OUTRAS FUNÇÕES AUXILIARES

# SUBSTITUA A FUNÇÃO ANTERIOR POR ESTA VERSÃO CORRIGIDA

@st.cache_data(ttl=86400) # Cache de 1 dia para dados de backtest
def run_backtest(portfolio_df, period="3y"):
    """
    Executa o backtest para um portfólio, retornando a performance e métricas.
    """
    tickers = portfolio_df['ticker'].tolist()
    weights = portfolio_df['weight'].values
    
    # Normaliza os pesos para garantir que somem 1
    weights = weights / weights.sum()

    try:
        prices = get_portfolio_price_data(tickers, period)
        if prices.empty:
            return None

        # --- LÓGICA CORRIGIDA ---
        # Chama a função de risco UMA VEZ e desempacota os 3 resultados
        annualized_return, annualized_vol, sharpe_ratio = calculate_portfolio_risk(prices, weights)
        
        # Calcula o retorno acumulado separadamente
        portfolio_daily_returns = (prices.pct_change().dropna() * weights).sum(axis=1)
        cumulative_returns = (1 + portfolio_daily_returns).cumprod()
        total_return = cumulative_returns.iloc[-1] - 1
        
        # Retorna um dicionário com cada métrica sendo um único número
        return {
            "cumulative_returns": cumulative_returns,
            "total_return": total_return,
            "annualized_return": annualized_return,
            "annualized_vol": annualized_vol,
            "sharpe_ratio": sharpe_ratio
        }
    except Exception as e:
        st.error(f"Erro no backtest: {e}")
        return None

# --- INTERFACE DA APLICAÇÃO ---
st.title("💼 Painel de Wealth Management e Alocação Estratégica")
st.markdown("Visão geral dos Portfólios Modelo e ferramentas de análise para assessores.")
st.divider()

# --- FASE 4: QUESTIONÁRIO DE PERFIL DE RISCO (SUITABILITY) ---
with st.expander("Definir Perfil de Risco do Cliente (Suitability)", expanded=True):
    st.markdown("Responda às perguntas abaixo para determinar o Portfólio Modelo mais adequado.")
    
    q1_options = {"Longo Prazo (acima de 5 anos)": 30, "Médio Prazo (2 a 5 anos)": 20, "Curto Prazo (até 2 anos)": 10}
    q1 = st.radio("1. Por quanto tempo você pretende manter seus investimentos aplicados?", list(q1_options.keys()), key="q1")

    q2_options = {"Compraria mais, aproveitando os preços baixos": 40, "Manteria minha posição, pois invisto para o longo prazo": 20, "Venderia toda a minha posição para evitar mais perdas": 10}
    q2 = st.radio("2. Imagine uma queda de 20% no mercado. Qual seria sua reação mais provável?", list(q2_options.keys()), key="q2")

    q3_options = {"Aumentar meu patrimônio de forma significativa, aceitando mais riscos": 30, "Gerar uma renda complementar, com um balanço entre risco e segurança": 20, "Preservar meu capital com o menor risco possível": 10}
    q3 = st.radio("3. Qual é o seu principal objetivo com esta carteira de investimentos?", list(q3_options.keys()), key="q3")
    
    if st.button("Calcular Perfil de Risco"):
        total_score = q1_options[q1] + q2_options[q2] + q3_options[q3]
        
        if total_score <= 40: profile_name = "Conservador"
        elif total_score <= 60: profile_name = "Moderado"
        elif total_score <= 75: profile_name = "Balanceado"
        elif total_score <= 90: profile_name = "Crescimento"
        else: profile_name = "Agressivo"
        
        st.session_state.client_profile = profile_name
        
        st.success(f"### Perfil de Risco Calculado: **{profile_name}**")
        st.write(f"Sua pontuação foi de **{total_score}** de 100. O portfólio modelo recomendado é o **{profile_name}**. Role para baixo para comparar a carteira do seu cliente com este modelo.")

st.divider()

# --- FASE 1: VISÃO TÁTICA E PORTFÓLIOS MODELO ---
st.subheader("Alocação Estratégica de Longo Prazo")
cols = st.columns(len(portfolio_data))
for i, (portfolio_name, data) in enumerate(portfolio_data.items()):
    with cols[i]:
        fig = create_allocation_chart(portfolio_name, data)
        # Destaca o portfólio recomendado com uma borda ou outro elemento visual
        if portfolio_name == st.session_state.client_profile:
            st.markdown(f"**_{portfolio_name}_** ⭐")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.plotly_chart(fig, use_container_width=True)
st.divider()

# --- FASE 2: BUILDING BLOCKS ---
st.subheader("Building Blocks: Ativos Recomendados por Classe")
selected_class = st.selectbox("Escolha a Classe de Ativo:", options=list(building_blocks_data.keys()), key="bb_select")
if selected_class:
    st.markdown(f"#### Ativos para a classe: **{selected_class}**")
    for asset in building_blocks_data.get(selected_class, []):
        col1, col2 = st.columns([1, 4])
        with col1: st.metric("Ticker", asset["ticker"])
        with col2:
            st.markdown(f"**{asset['name']}**"); st.caption(asset['rationale'])
            if ".SA" in asset['ticker'].upper() or all(c.isalpha() for c in asset['ticker']):
                st.link_button("Ver no Yahoo Finance", f"https://finance.yahoo.com/quote/{asset['ticker']}")
        st.divider()

# --- FASE 3: ANALISADOR DE CARTEIRA DO CLIENTE ---
st.subheader("Analisador de Carteira do Cliente")
# O selectbox agora usa o perfil calculado como padrão
default_index = portfolio_list.index(st.session_state.client_profile) if st.session_state.client_profile in portfolio_list else 2

col_input1, col_input2 = st.columns([2, 1])
with col_input1:
    portfolio_input = st.text_area("Insira a carteira (um ativo por linha, formato: TICKER,VALOR)", "IVV,50000\nBOVA11.SA,30000\nBNDW,20000\nHGLG11.SA,10000", height=150, key="portfolio_input_area")
with col_input2:
    model_to_compare = st.selectbox("Selecione o Portfólio Modelo para Comparação:", options=portfolio_list, index=default_index, key="model_compare_select")
    analyze_client_button = st.button("Analisar Carteira do Cliente", use_container_width=True)

if analyze_client_button and portfolio_input.strip():
    try:
        with st.spinner("Analisando carteira do cliente..."):
            lines = [line.strip() for line in portfolio_input.strip().split('\n') if line.strip()]
            portfolio_list_data = [{'ticker': line.split(',')[0].strip().upper(), 'value': float(line.split(',')[1])} for line in lines]
            
            client_df = pd.DataFrame(portfolio_list_data)
            total_value = client_df['value'].sum()
            client_df['weight'] = client_df['value'] / total_value
            
            category_map = bulk_categorize_tickers(tuple(client_df['ticker'].unique()))
            client_df['asset_class'] = client_df['ticker'].map(category_map)
            client_allocation = client_df.groupby('asset_class')['weight'].sum() * 100
            
            tickers = client_df['ticker'].tolist(); weights = client_df['weight'].values
            price_data = get_portfolio_price_data(tickers)
            p_return, p_vol, p_sharpe = calculate_portfolio_risk(price_data, weights)
            
            st.markdown("##### Análise da Alocação")
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1: st.plotly_chart(create_allocation_chart("Alocação Atual do Cliente", client_allocation), use_container_width=True)
            with col_chart2: st.plotly_chart(create_allocation_chart(f"Modelo {model_to_compare}", portfolio_data[model_to_compare]), use_container_width=True)
            
            st.markdown("##### Métricas de Risco da Carteira do Cliente")
            risk1, risk2, risk3 = st.columns(3)
            risk1.metric("Retorno Anualizado", f"{p_return*100:.2f}%")
            risk2.metric("Volatilidade Anualizada", f"{p_vol*100:.2f}%")
            risk3.metric("Índice de Sharpe", f"{p_sharpe:.2f}")

    except Exception as e:
        st.error(f"Ocorreu um erro ao analisar a carteira. Verifique o formato dos dados. Erro: {e}")

# COLE ESTA NOVA SEÇÃO NO FINAL DO SEU ARQUIVO

st.divider()

# --- FASE 5: CONSTRUTOR E SIMULADOR DE PORTFÓLIOS ---
st.subheader("🛠️ Construtor e Simulador de Portfólios")
st.markdown("Construa uma carteira a partir dos nossos modelos, faça ajustes táticos e simule a performance histórica.")

# --- Etapa 1: Seleção do Portfólio Base ---
st.markdown("##### 1. Selecione um Portfólio Modelo como Base")
base_model_name = st.selectbox(
    "Escolha um modelo para começar:",
    options=list(portfolio_data.keys()),
    index=2, # Padrão para 'Balanceado'
    key="base_model_selector"
)

# --- Etapa 2: Customização da Carteira ---
st.markdown("##### 2. Visualize e Customize a Alocação")
st.caption("A tabela abaixo é editável. Você pode alterar os pesos das classes de ativos ou os tickers dos 'building blocks'. A soma dos pesos deve ser 100%.")

# Prepara o dataframe do portfólio para edição
if base_model_name:
    # Cria um DataFrame com os ativos e pesos do modelo selecionado
    assets_list = []
    model_allocation = portfolio_data[base_model_name]
    for asset_class, weight in model_allocation.items():
        if weight > 0:
            # Pega o primeiro 'building block' recomendado para aquela classe
            recommended_asset = building_blocks_data[asset_class][0]
            assets_list.append({
                "Classe de Ativo": asset_class,
                "Ticker": recommended_asset['ticker'],
                "Peso (%)": weight
            })
    
    portfolio_editor_df = pd.DataFrame(assets_list)

# Usa o st.data_editor para permitir a edição da carteira
edited_portfolio_df = st.data_editor(
    portfolio_editor_df,
    num_rows="dynamic", # Permite adicionar/remover linhas
    column_config={
        "Peso (%)": st.column_config.NumberColumn(
            "Peso (%)",
            help="O peso do ativo na carteira. A soma total deve ser 100.",
            min_value=0,
            max_value=100,
            step=1,
            format="%d%%"
        )
    },
    key="portfolio_editor"
)

# Validação dos pesos
total_weight = edited_portfolio_df['Peso (%)'].sum()
if not np.isclose(total_weight, 100):
    st.warning(f"A soma dos pesos é de {total_weight:.1f}%. Por favor, ajuste para que a soma seja 100%.")

# --- Etapa 3: Execução do Backtest ---
st.markdown("##### 3. Execute o Backtest")
if st.button("Rodar Backtest da Carteira Customizada", disabled=not np.isclose(total_weight, 100)):
    
    # Prepara o DataFrame para a função de backtest
    backtest_input_df = edited_portfolio_df.copy()
    backtest_input_df.rename(columns={"Ticker": "ticker", "Peso (%)": "weight"}, inplace=True)
    backtest_input_df['weight'] = backtest_input_df['weight'] / 100 # Converte para decimal
    
    # Remove linhas com tickers não-padrão que não podem ser baixados
    backtest_input_df = backtest_input_df[backtest_input_df['ticker'].str.match(r'^[A-Z0-9\.\^=^-]+$')]

    with st.spinner("Executando simulação histórica..."):
        backtest_results = run_backtest(backtest_input_df)

    if backtest_results:
        st.subheader("Resultados do Backtest")
        
        # Métricas de Performance
        res1, res2, res3, res4 = st.columns(4)
        res1.metric("Retorno Total no Período", f"{backtest_results['total_return']*100:.2f}%")
        res2.metric("Retorno Anualizado", f"{backtest_results['annualized_return']*100:.2f}%")
        res3.metric("Volatilidade Anualizada", f"{backtest_results['annualized_vol']*100:.2f}%")
        res4.metric("Índice de Sharpe", f"{backtest_results['sharpe_ratio']:.2f}")
        
        # Gráfico de Performance
        fig = px.line(backtest_results['cumulative_returns'], title="Performance Histórica da Carteira Customizada")
        fig.update_layout(yaxis_title="Retorno Acumulado", xaxis_title="Data", yaxis_tickformat=".2%")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("Não foi possível executar o backtest. Verifique os tickers e tente novamente.")
