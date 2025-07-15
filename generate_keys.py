# Arquivo: generate_keys.py
import streamlit_authenticator as stauth

hashed_passwords = stauth.Hasher(['senha_do_joao', 'senha_da_ana']).generate()
print(hashed_passwords)
