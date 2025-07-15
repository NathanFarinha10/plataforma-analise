# Arquivo: Plataforma_PAG.py (Versão com Login Autocontido para Testes)

import streamlit as st
import streamlit_authenticator as stauth

# --- Configuração da Página ---
st.set_page_config(page_title="Plataforma PAG", page_icon="📈", layout="wide")

# --- ETAPA 1: DEFINIR SENHAS EM TEXTO PLANO (APENAS PARA TESTE) ---
# Aqui você pode definir as senhas que quiser de forma fácil.
plain_passwords = ['jsilva123', 'aoliveira123']

# --- ETAPA 2: CRIPTOGRAFAR AS SENHAS NA HORA ---
# Esta linha gera as senhas criptografadas (hashed) necessárias para a biblioteca.
hashed_passwords = stauth.Hasher(plain_passwords).generate()

# --- ETAPA 3: MONTAR A CONFIGURAÇÃO DINAMICAMENTE ---
config = {
    "credentials": {
        "usernames": {
            "jsilva": {
                "email": "j.silva@suagestora.com",
                "name": "João Silva (Advisor)",
                "password": hashed_passwords[0] # Usa a primeira senha criptografada
            },
            "aoliveira": {
                "email": "a.oliveira@suagestora.com",
                "name": "Ana Oliveira (Analista)",
                "password": hashed_passwords[1] # Usa a segunda senha criptografada
            },
        }
    },
    "cookie": {
        "expiry_days": 30, 
        "key": "uma_chave_secreta_muito_aleatoria_e_diferente", # Mude isso para qualquer string
        "name": "pag_auth_cookie_final"
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
