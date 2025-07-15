# Arquivo: Plataforma_PAG.py (Versão com Tela de Splash)

import streamlit as st
import streamlit_authenticator as stauth
import time

# --- Configuração da Página ---
st.set_page_config(page_title="Plataforma PAG", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

# --- LÓGICA DA TELA DE SPLASH ---
# Usamos o session_state para garantir que a splash screen só apareça uma vez por sessão.
if 'splash_screen_done' not in st.session_state:
    
    # Centraliza a logo e o spinner
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            # Tenta carregar a logo. Use um placeholder se o arquivo não existir.
            st.image("logo.png", use_container_width=True)
        except Exception:
            st.warning("Arquivo 'logo.png' não encontrado. Exibindo placeholder.")
            st.markdown("<h1 style='text-align: center;'>PAG</h1>", unsafe_allow_html=True)
            
        # Spinner de carregamento
        with st.spinner("Carregando plataforma..."):
            time.sleep(4) # Pausa por 4 segundos

    # Marca a splash screen como concluída e recarrega o script
    st.session_state.splash_screen_done = True
    st.rerun()

# O restante do código só será executado DEPOIS que a splash screen terminar.

# --- DADOS DE LOGIN (MÉTODO SIMPLIFICADO) ---
# Senhas criptografadas para 'jsilva123' e 'aoliveira123'
config = {
    "credentials": {
        "usernames": {
            "jsilva": {"email": "j.silva@suagestora.com", "name": "João Silva (Advisor)", "password": "$2b$12$EGyPzL2nL0vG0i/q.1oV..q4QxLAb7e5rvKj/yJzD9d/AlJld2P2G"},
            "aoliveira": {"email": "a.oliveira@suagestora.com", "name": "Ana Oliveira (Analista)", "password": "$2b$12$N9dG1WJb2e7p.Q0b6a5k.uI9h8g7f6e5d4c3b2a1"},
        }
    },
    "cookie": {"expiry_days": 30, "key": "chave_secreta_final_pag", "name": "pag_auth_cookie"},
}

# --- LÓGICA DE AUTENTICAÇÃO ---
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

authenticator.login()

# --- CONTROLE DE ACESSO ---
if st.session_state.get("authentication_status"):
    with st.sidebar:
        st.write(f'Bem-vindo(a), *{st.session_state["name"]}*')
        authenticator.logout('Logout', 'main')
    
    # Remove a mensagem de "Please enter username and password" após o login
    st.markdown("<style>.stAlert {display: none;}</style>", unsafe_allow_html=True)

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
