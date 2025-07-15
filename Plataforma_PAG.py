# Arquivo: Plataforma_PAG.py
import streamlit as st
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

st.set_page_config(page_title="Plataforma PAG", page_icon="📈", layout="wide")

try:
    with open('config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)
except FileNotFoundError:
    st.error("Arquivo 'config.yaml' não encontrado. Crie-o na pasta principal.")
    st.stop()

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

authenticator.login()

if st.session_state["authentication_status"]:
    with st.sidebar:
        st.write(f'Bem-vindo(a), *{st.session_state["name"]}*')
        authenticator.logout('Logout', 'main')
    st.title("Bem-vindo à Plataforma de Análise da Gestora (PAG)")
    st.markdown("---")
    st.header("Navegue pelas nossas ferramentas de análise no menu à esquerda.")

elif st.session_state["authentication_status"] is False:
    st.error('Usuário/senha incorreto(a)')
elif st.session_state["authentication_status"] is None:
    st.warning('Por favor, insira seu usuário e senha')
