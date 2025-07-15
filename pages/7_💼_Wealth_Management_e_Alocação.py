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

            st.divider()

st.success("✅ **Fase 2 Concluída:** Detalhamento dos 'Building Blocks' implementado. O próximo passo será a ferramenta de análise de carteira do cliente (Fase 3).")
