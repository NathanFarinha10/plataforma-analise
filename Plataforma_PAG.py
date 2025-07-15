# Arquivo: Plataforma_PAG.py (Nosso novo ponto de entrada principal)

import streamlit as st
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

# --- Configuração da Página ---
st.set_page_config(page_title="Plataforma PAG", page_icon="📈", layout="wide")

# --- LÓGICA DE AUTENTICAÇÃO ---
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

# Renderiza o formulário de login no centro da página
name, authentication_status, username = authenticator.login('main')

# --- CONTROLE DE ACESSO ---
if st.session_state["authentication_status"]:
    # Se o login for bem-sucedido, mostra o conteúdo principal e o menu
    
    # Barra lateral com saudação e botão de logout
    with st.sidebar:
        st.write(f'Bem-vindo(a), *{st.session_state["name"]}*')
        authenticator.logout('Logout', 'main')

    # Conteúdo principal da página de boas-vindas
    st.title("Bem-vindo à Plataforma de Análise da Gestora (PAG)")
    st.markdown("---")
    st.header("Navegue pelas nossas ferramentas de análise no menu à esquerda.")
    st.info("""
    **Módulos Disponíveis:**
    - **Análise Macro:** Monitore os principais indicadores econômicos e de mercado.
    - **Research de Empresas:** Faça uma análise profunda de ações individuais.
    - **Análise de ETFs:** Avalie a performance e características de ETFs.
    - **Análise de Renda Fixa:** Acompanhe o mercado de juros e analise títulos.
    - **Wealth Management:** Utilize nossas ferramentas de alocação de portfólios e análise de clientes.
    """)

elif st.session_state["authentication_status"] is False:
    st.error('Usuário/senha incorreto(a)')
elif st.session_state["authentication_status"] is None:
    st.warning('Por favor, insira seu usuário e senha')
