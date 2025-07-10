# pages/2_🏢_Research_Empresas.py (versão de depuração e correção)

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# --- Configuração da Página ---
st.set_page_config(
    page_title="PAG | Research de Empresas",
    page_icon="🏢",
    layout="wide"
)

# --- FUNÇÃO DE ANÁLISE DE SENTIMENTO (NOSSA IA) ---
def analisar_sentimento(texto):
    texto = texto.lower()
    palavras_positivas = ['crescimento', 'lucro', 'aumento', 'supera', 'expansão', 'forte', 'otimista', 'sucesso', 'melhora', 'compra',
                          'growth', 'profit', 'increase', 'beats', 'expansion', 'strong', 'optimistic', 'success', 'improves', 'buy', 'upgrade']
    palavras_negativas = ['queda', 'prejuízo', 'redução', 'abaixo', 'contração', 'fraco', 'pessimista', 'falha', 'piora', 'venda',
                          'fall', 'loss', 'reduction', 'below', 'contraction', 'weak', 'pessimistic', 'fails', 'worsens', 'sell', 'downgrade']
    score = 0
    for palavra in palavras_positivas:
        if palavra in texto:
            score += 1
    for palavra in palavras_negativas:
        if palavra in texto:
            score -= 1
    if score > 0:
        return 'Positivo', '🟢'
    elif score < 0:
        return 'Negativo', '🔴'
    else:
        return 'Neutro', '⚪️'

# --- Título e Descrição ---
st.title("Painel de Research de Empresas")
st.markdown("Analise ações individuais do Brasil e dos EUA.")

# --- Barra Lateral com Inputs ---
st.sidebar.header("Filtros de Análise")
ticker_symbol = st.sidebar.text_input(
    "Digite o Ticker da Ação", 
    "AAPL",
    help="Exemplos: AAPL para Apple, PETR4.SA para Petrobras."
).upper()
analyze_button = st.sidebar.button("Analisar")

# --- Lógica Principal ---
if analyze_button:
    if not ticker_symbol:
        st.warning("Por favor, digite um ticker para analisar.")
    else:
        try:
            with st.spinner(f"Carregando dados de {ticker_symbol}..."):
                ticker = yf.Ticker(ticker_symbol)
                info = ticker.info
                if not info.get('longName'):
                    st.error(f"Ticker '{ticker_symbol}' não encontrado ou inválido. Verifique o código.")
                else:
                    st.header(f"Visão Geral de: {info['longName']} ({info['symbol']})")
                    # ... (o resto do código de Visão Geral e Fundamentalista permanece igual)
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("País", info.get('country', 'N/A'))
                        st.metric("Setor", info.get('sector', 'N/A'))
                        st.metric("Indústria", info.get('industry', 'N/A'))
                    with col2:
                        st.metric("Moeda", info.get('currency', 'N/A'))
                        st.metric("Preço Atual", f"{info.get('currentPrice', 0):.2f}")
                        st.metric("Valor de Mercado", f"{(info.get('marketCap', 0) / 1e9):.2f}B")

                    with st.expander("Descrição da Empresa"):
                        st.write(info.get('longBusinessSummary', 'Descrição não disponível.'))
                    
                    st.header("Análise Fundamentalista")
                    fund_col1, fund_col2, fund_col3 = st.columns(3)
                    with fund_col1:
                        st.metric("P/L (Price/Earnings)", f"{info.get('trailingPE', 0):.2f}")
                        st.metric("P/VP (Price/Book)", f"{info.get('priceToBook', 0):.2f}")
                    with fund_col2:
                        st.metric("Dividend Yield", f"{info.get('dividendYield', 0) * 100:.2f}%")
                        st.metric("Beta", f"{info.get('beta', 0):.2f}")
                    with fund_col3:
                        st.metric("EPS (Lucro por Ação)", f"{info.get('trailingEps', 0):.2f}")
                        st.metric("ROE (Return on Equity)", f"{info.get('returnOnEquity', 0) * 100:.2f}%")

                    st.header("Histórico de Cotações")
                    hist_df = ticker.history(period="5y")
                    fig = px.line(hist_df, x=hist_df.index, y="Close", title=f"Preço de Fechamento de {info['shortName']}",
                                  labels={'Close': f'Preço ({info["currency"]})', 'Date': 'Data'})
                    st.plotly_chart(fig, use_container_width=True)

                    st.header("Notícias Recentes e Análise de Sentimento")
                    news = ticker.news
                    if news:
                        for item in news:
                            # --- CÓDIGO DE DEPURAÇÃO ---
                            # Descomente a linha abaixo para ver a estrutura exata dos dados da notícia
                            # st.json(item) 
                            
                            # --- CÓDIGO CORRIGIDO E MAIS ROBUSTO ---
                            # Tenta pegar 'title', se não conseguir, tenta 'headline'.
                            titulo = item.get('title') or item.get('headline')
                            
                            if not titulo:
                                continue # Pula para o próximo item se não encontrar título
                            
                            publisher = item.get('publisher', 'Publicador não informado')
                            link = item.get('link')
                            sentimento, icone = analisar_sentimento(titulo)
                            
                            with st.expander(f"{icone} {titulo}"):
                                st.markdown(f"**Publicado por:** {publisher}")
                                st.markdown(f"**Sentimento:** {sentimento}")
                                if link:
                                    st.link_button("Ler notícia completa", link)
                    else:
                        st.write("Nenhuma notícia recente encontrada para esta ação.")

        except Exception as e:
            st.error(f"Ocorreu um erro ao buscar os dados: {e}")
else:
    st.info("Digite um ticker na barra lateral e clique em 'Analisar' para começar.")
