# pages/7_💼_Wealth_Management.py

import streamlit as st
import pandas as pd
import plotly.express as px

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

st.divider()

st.success("✅ **Fase 1 Concluída:** Base dos Portfólios Modelo estabelecida. O próximo passo será detalhar os ativos recomendados para cada classe (Fase 2).")
