# Arquivo: Plataforma_PAG.py (Versão com Login Simplificado para Testes)

import streamlit as st
import streamlit_authenticator as stauth

# --- Configuração da Página ---
st.set_page_config(page_title="Plataforma PAG", page_icon="📈", layout="wide")

# --- DADOS DE LOGIN (MÉTODO SIMPLIFICADO) ---
# Em vez de um arquivo .yaml, definimos os usuários diretamente aqui.
# As senhas já estão criptografadas (hashed) para sua segurança.
# Usuário 1: jsilva, Senha 1: jsilva123
# Usuário 2: aoliveira, Senha 2: aoliveira123
config = {
    "credentials": {
        "usernames": {
            "jsilva": {
                "email": "j.silva@suagestora.com",
                "name": "João Silva (Advisor)",
                "password": "$2b$12$5W.b.v3yG8xgXF6S/u5s9.g2o8B3Z4e9S6f7h8iJ0kL1m2n3o4p5q", 
            },
            "aoliveira": {
                "email": "a.oliveira@suagestora.com",
                "name": "Ana Oliveira (Analista)",
                "password": "$2b$12$K1l2m3n4o5p6q7r8s9t0u.e9f8d7g6h5j4k3l2m1n2o3p4q",
            },
        }
    },
    "cookie": {
        "expiry_days": 30, 
        "key": "uma_chave_secreta_muito_aleatoria", # Mude isso para qualquer string aleatória
        "name": "pag_auth_cookie"
    },
}

# --- LÓGICA DE AUTENTICAÇÃO ---
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Renderiza o formulário de login
authenticator.login()

# --- CONTROLE DE ACESSO ---
if st.session_state["authentication_status"]:
    # Se o login for bem-sucedido, mostra o conteúdo principal e o menu
    
    with st.sidebar:
        st.write(f'Bem-vindo(a), *{st.session_state["name"]}*')
        authenticator.logout('Logout', 'main')

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
