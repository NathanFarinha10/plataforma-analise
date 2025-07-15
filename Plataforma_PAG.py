# Arquivo: Plataforma_PAG.py (Versão com Logo na Sidebar)

import streamlit as st

# --- Configuração da Página ---
st.set_page_config(
    page_title="Plataforma PAG", 
    page_icon="📈", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- Adiciona a logo no topo da barra lateral ---
# Esta linha deve estar em todas as páginas para consistência.
try:
    st.sidebar.image("logo.png", use_container_width=True)
except Exception:
    st.sidebar.warning("Arquivo de logo 'logo.png' não encontrado.")


# --- BANCO DE DADOS DE USUÁRIOS E SENHAS (PARA TESTE) ---
VALID_CREDENTIALS = {
    "jsilva": "senha123",
    "aoliveira": "senha456"
}

def login_form():
    """Função para criar e gerenciar o formulário de login."""
    st.title("Bem-vindo à Plataforma PAG")
    st.markdown("Por favor, faça o login para continuar.")
    
    with st.form("login_form"):
        username = st.text_input("Usuário").lower() # Converte para minúsculas
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            # Verifica se o usuário e a senha correspondem ao nosso dicionário
            if username in VALID_CREDENTIALS and password == VALID_CREDENTIALS[username]:
                st.session_state["authentication_status"] = True
                st.session_state["username"] = username
                
                user_details = {
                    "jsilva": {"name": "João Silva", "role": "Advisor"},
                    "aoliveira": {"name": "Ana Oliveira", "role": "Analista"}
                }
                st.session_state["name"] = user_details[username]["name"]
                st.session_state["role"] = user_details[username]["role"]
                st.rerun() 
            else:
                st.error("Usuário ou senha incorreto(a)")

# --- LÓGICA DE EXIBIÇÃO DA PÁGINA ---

# Se o usuário não estiver autenticado, mostra o formulário de login
if not st.session_state.get("authentication_status"):
    login_form()
else:
    # Se o login for bem-sucedido, mostra o conteúdo principal
    
    # Conteúdo da barra lateral para usuários logados
    with st.sidebar:
        st.write(f'Bem-vindo(a), *{st.session_state["name"]}*')
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Conteúdo da página principal
    st.title("Plataforma de Análise da Gestora (PAG)")
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
