# pages/7_💼_Wealth_Management.py

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- Configuração da Página ---
st.set_page_config(page_title="Wealth Management - Alocação", page_icon="💼", layout="wide")

# --- DADOS: ALOCAÇÃO ESTRATÉGICA DOS PORTFÓLIOS MODELO ---
# Estes dados serão a base da nossa ferramenta. No futuro, podem vir de um banco de dados ou API interna.

portfolio_data = {
    "Conservador": {
        "Caixa": 20, "Renda Fixa Brasil": 50, "Renda Fixa Internacional": 15,
        "Ações Brasil": 5, "Ações Internacional": 5, "Fundos Imobiliários": 5, "Alternativos": 0
    },
    "Moderado": {
        "Caixa": 10, "Renda Fixa Brasil": 40, "Renda Fixa Internacional": 15,
        "Ações Brasil": 15, "Ações Internacional": 15, "Fundos Imobiliários": 5, "Alternativos": 0
    },
    "Balanceado": {
        "Caixa": 5, "Renda Fixa Brasil": 30, "Renda Fixa Internacional": 20,
        "Ações Brasil": 20, "Ações Internacional": 20, "Fundos Imobiliários": 5, "Alternativos": 0
    },
    "Crescimento": {
        "Caixa": 5, "Renda Fixa Brasil": 20, "Renda Fixa Internacional": 15,
        "Ações Brasil": 25, "Ações Internacional": 25, "Fundos Imobiliários": 5, "Alternativos": 5
    },
    "Agressivo": {
        "Caixa": 2, "Renda Fixa Brasil": 10, "Renda Fixa Internacional": 10,
        "Ações Brasil": 34, "Ações Internacional": 34, "Fundos Imobiliários": 5, "Alternativos": 5
    }
}

# COLE ESTE DICIONÁRIO NO TOPO DO SEU ARQUIVO

building_blocks_data = {
    "Caixa": [
        {"ticker": "Tesouro Selic (LFT)", "name": "Título Público Pós-Fixado", "rationale": "Principal ativo para reserva de emergência e posições de caixa, com liquidez diária e baixo risco."}
    ],
    "Renda Fixa Brasil": [
        {"ticker": "IMAB11.SA", "name": "iShares IMA-B Fundo de Índice", "rationale": "Exposição a uma carteira de títulos públicos atrelados à inflação (NTN-Bs). Proteção contra a inflação."},
        {"ticker": "B5P211.SA", "name": "It Now IMA-B 5+ Fundo de Indice", "rationale": "Foco em títulos públicos atrelados à inflação de longo prazo (vencimento acima de 5 anos), buscando maior retorno e duration."}
    ],
    "Renda Fixa Internacional": [
        {"ticker": "BNDW", "name": "Vanguard Total World Bond ETF", "rationale": "ETF globalmente diversificado que investe em títulos de alta qualidade de crédito dos EUA e de outros países (com hedge cambial)."},
        {"ticker": "USTK11.SA", "name": "iShares Treasury Selic Soberano", "rationale": "Exposição a títulos do Tesouro Americano com a variação do Dólar, atrelado à taxa Selic. Proteção cambial com rendimento."}
    ],
    "Ações Brasil": [
        {"ticker": "BOVA11.SA", "name": "iShares Ibovespa Fundo de Índice", "rationale": "Exposição ampla ao principal índice de ações brasileiro, representando as maiores empresas do país."},
        {"ticker": "SMAL11.SA", "name": "iShares Small Cap Fundo de Indice", "rationale": "Foco em empresas de menor capitalização (Small Caps), que possuem maior potencial de crescimento."}
    ],
    "Ações Internacional": [
        {"ticker": "IVV", "name": "iShares Core S&P 500 ETF", "rationale": "Exposição às 500 maiores empresas dos EUA. O pilar de qualquer alocação internacional."},
        {"ticker": "XINA11.SA", "name": "iShares MSCI China Fundo de Índice", "rationale": "Exposição às principais empresas da China, permitindo capturar o crescimento da segunda maior economia do mundo."},
        {"ticker": "EURP11.SA", "name": "iShares MSCI Europe Fundo de Índice", "rationale": "Exposição diversificada às principais empresas de países desenvolvidos da Europa."}
    ],
    "Fundos Imobiliários": [
        {"ticker": "IFIX", "name": "Índice de Fundos de Investimentos Imobiliários", "rationale": "Referência do setor. A recomendação é buscar FIIs de tijolo e papel bem diversificados. Ex: HGLG11, KNIP11."},
        {"ticker": "HGLG11.SA", "name": "CSHG Logística Fundo Imobiliário", "rationale": "Exemplo de FII de 'tijolo' de alta qualidade, focado no setor de galpões logísticos."}
    ],
    "Alternativos": [
        {"ticker": "GOLD11.SA", "name": "Trend Ouro Fundo de Índice", "rationale": "Exposição ao Ouro, que historicamente serve como reserva de valor e proteção em cenários de incerteza e inflação."},
        {"ticker": "WRLD11.SA", "name": "Trend ETF MSCI ACWI Fundo de Índice", "rationale": "ETF 'All-Country World Index', a forma mais diversificada de investir em ações globais, incluindo mercados desenvolvidos e emergentes."}
    ]
}

# --- FUNÇÃO AUXILIAR PARA CRIAR OS GRÁFICOS ---
def create_allocation_chart(portfolio_name, data):
    """Cria um gráfico de pizza interativo para a alocação de um portfólio."""
    df = pd.DataFrame(list(data.items()), columns=['Classe de Ativo', 'Alocação (%)'])
    fig = px.pie(
        df,
        values='Alocação (%)',
        names='Classe de Ativo',
        title=f"<b>{portfolio_name}</b>",
        hole=.3, # Cria o efeito "donut chart"
        color_discrete_sequence=px.colors.sequential.GnBu_r # Paleta de cores
    )
    fig.update_traces(textposition='inside', textinfo='percent+label', insidetextfont=dict(size=14))
    fig.update_layout(
        showlegend=False,
        title_font_size=20,
        title_x=0.5,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig

# ADICIONE ESTAS TRÊS FUNÇÕES JUNTO COM AS OUTRAS FUNÇÕES AUXILIARES

@st.cache_data
def get_portfolio_price_data(tickers_list, period="3y"):
    """Baixa os dados de preços de fechamento para uma lista de tickers."""
    try:
        data = yf.download(tickers_list, period=period, progress=False)['Close']
        return data.dropna()
    except Exception:
        return pd.DataFrame()

@st.cache_data
def categorize_ticker(ticker_symbol):
    """Classifica um ticker em uma das 7 classes de ativos com base em heurísticas."""
    try:
        info = yf.Ticker(ticker_symbol).info
        category = info.get('quoteType', '').upper()
        fund_family = info.get('fundFamily', '').upper()

        if category == 'EQUITY':
            return "Ações Brasil" if '.SA' in ticker_symbol.upper() else "Ações Internacional"
        
        if category == 'ETF':
            long_name = info.get('longName', '').upper()
            if any(term in long_name for term in ['FIXA', 'BOND', 'TREASURY']):
                return "Renda Fixa Internacional" if '.SA' not in ticker_symbol.upper() else "Renda Fixa Brasil"
            if any(term in long_name for term in ['FII', 'IMOBILIÁRIO', 'REAL ESTATE']):
                return "Fundos Imobiliários"
            if any(term in long_name for term in ['GOLD', 'OURO', 'COMMODITIES']):
                return "Alternativos"
            if any(term in long_name for term in ['IBOVESPA', 'SMALL', 'BRAZIL']):
                 return "Ações Brasil"
            return "Ações Internacional"
        
        return "Alternativos" # Default para tipos não reconhecidos
    except Exception:
        return "Não Classificado"

def calculate_portfolio_risk(prices, weights):
    """Calcula o risco e retorno anualizado de uma carteira."""
    if prices.empty or len(prices) < 252:
        return 0, 0, 0 # Retorna 0 se não houver dados suficientes
        
    returns = prices.pct_change().dropna()
    p_return = np.sum(returns.mean() * weights) * 252
    p_vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
    p_sharpe = p_return / p_vol if p_vol > 0 else 0
    return p_return, p_vol, p_sharpe

# --- INTERFACE DA APLICAÇÃO ---

st.title("💼 Painel de Wealth Management e Alocação Estratégica")
st.markdown("Visão geral dos Portfólios Modelo e da alocação de ativos recomendada pela casa.")

st.divider()

# --- Visão Tática do Comitê de Investimentos ---
st.subheader("Visão Tática do Comitê de Investimentos")
with st.expander("Clique para ver os posicionamentos táticos atuais", expanded=True):
    st.info("""
        - **OVERWEIGHT (Alocação Acima da Estratégica):** Ações Internacionais.
          - *Justificativa:* Oportunidades em setores de tecnologia e saúde com valuations atrativos e descorrelação com o mercado local.
        - **NEUTRO:** Ações Brasil, Fundos Imobiliários, Renda Fixa Internacional.
          - *Justificativa:* Posições alinhadas à estratégia de longo prazo, aguardando maior clareza no cenário macroeconômico.
        - **UNDERWEIGHT (Alocação Abaixo da Estratégica):** Renda Fixa Brasil Pré-Fixada.
          - *Justificativa:* Incerteza fiscal no curto prazo aumenta a volatilidade. Preferência por títulos pós-fixados ou atrelados à inflação.
    """)
    st.caption(f"Última atualização: {datetime.now().strftime('%d/%m/%Y')}")

st.divider()

# --- Painel de Portfólios Modelo ---
st.subheader("Alocação Estratégica de Longo Prazo")

cols = st.columns(len(portfolio_data))

for i, (portfolio_name, data) in enumerate(portfolio_data.items()):
    with cols[i]:
        fig = create_allocation_chart(portfolio_name, data)
        st.plotly_chart(fig, use_container_width=True)

# COLE ESTA NOVA SEÇÃO NO FINAL DO SEU ARQUIVO

st.divider()

# --- Seção de Building Blocks ---
st.subheader("Building Blocks: Ativos Recomendados por Classe")
st.markdown("Selecione uma classe de ativo para ver os 'building blocks' (ETFs e títulos) recomendados para compor as carteiras.")

# Cria um menu de seleção com as classes de ativos
selected_class = st.selectbox(
    "Escolha a Classe de Ativo:",
    options=list(building_blocks_data.keys())
)

if selected_class:
    st.markdown(f"#### Ativos para a classe: **{selected_class}**")
    
    # Busca os ativos recomendados para a classe selecionada
    recommended_assets = building_blocks_data.get(selected_class, [])
    
    if not recommended_assets:
        st.warning("Nenhum ativo recomendado para esta classe no momento.")
    else:
        # Exibe cada ativo recomendado
        for asset in recommended_assets:
            col1, col2 = st.columns([1, 4])
            with col1:
                st.metric("Ticker", asset["ticker"])
            with col2:
                st.markdown(f"**{asset['name']}**")
                st.caption(asset['rationale'])
                
                # Link para análise, se for um ticker válido do Yahoo Finance
                if ".SA" in asset['ticker'] or all(c.isalpha() for c in asset['ticker']):
                    yahoo_finance_link = f"https://finance.yahoo.com/quote/{asset['ticker']}"
                    st.link_button("Ver no Yahoo Finance", yahoo_finance_link)

          # COLE ESTA NOVA SEÇÃO NO FINAL DO SEU ARQUIVO

st.divider()

# --- FASE 3: ANALISADOR DE CARTEIRA DO CLIENTE ---
st.subheader("Analisador de Carteira do Cliente")
st.markdown("Cole a carteira do cliente abaixo para analisá-la em relação aos nossos portfólios modelo.")

col_input1, col_input2 = st.columns([2,1])

with col_input1:
    portfolio_input = st.text_area(
        "Insira a carteira do cliente (um ativo por linha, formato: TICKER,VALOR)",
        "IVV,50000\nBOVA11.SA,30000\nBNDW,20000\nHGLG11.SA,10000",
        height=200
    )
with col_input2:
    model_to_compare = st.selectbox(
        "Selecione o Portfólio Modelo para Comparação:",
        options=list(portfolio_data.keys())
    )
    analyze_client_button = st.button("Analisar Carteira do Cliente", use_container_width=True)

if analyze_client_button:
    try:
        # --- Processamento e Análise dos Inputs ---
        lines = [line.strip() for line in portfolio_input.strip().split('\n') if line.strip()]
        if not lines:
            st.warning("Por favor, insira os dados da carteira.")
        else:
            with st.spinner("Analisando carteira do cliente..."):
                portfolio_list = []
                for line in lines:
                    ticker, value = line.split(',')
                    portfolio_list.append({'ticker': ticker.strip().upper(), 'value': float(value)})
                
                client_df = pd.DataFrame(portfolio_list)
                total_value = client_df['value'].sum()
                client_df['weight'] = client_df['value'] / total_value
                
                # Categoriza cada ativo
                client_df['asset_class'] = client_df['ticker'].apply(categorize_ticker)
                
                # Agrupa por classe de ativo
                client_allocation = client_df.groupby('asset_class')['weight'].sum() * 100
                
                # --- Análise de Risco ---
                tickers = client_df['ticker'].tolist()
                weights = client_df['weight'].values
                price_data = get_portfolio_price_data(tickers)
                p_return, p_vol, p_sharpe = calculate_portfolio_risk(price_data, weights)
                
                # --- Exibição dos Resultados ---
                st.markdown("##### Análise da Alocação")
                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    fig_client = create_allocation_chart("Alocação Atual do Cliente", client_allocation)
                    st.plotly_chart(fig_client, use_container_width=True)

                with col_chart2:
                    fig_model = create_allocation_chart(f"Modelo {model_to_compare}", portfolio_data[model_to_compare])
                    st.plotly_chart(fig_model, use_container_width=True)
                
                st.markdown("##### Métricas de Risco da Carteira do Cliente")
                risk1, risk2, risk3 = st.columns(3)
                risk1.metric("Retorno Anualizado", f"{p_return*100:.2f}%")
                risk2.metric("Volatilidade Anualizada", f"{p_vol*100:.2f}%")
                risk3.metric("Índice de Sharpe", f"{p_sharpe:.2f}")

    except Exception as e:
        st.error(f"Ocorreu um erro ao analisar a carteira. Verifique o formato dos dados. Erro: {e}")
        
st.success("✅ **Fase 3 Concluída:** Ferramenta de Análise de Carteira do Cliente implementada.")
