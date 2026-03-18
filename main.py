import streamlit as st
from database import conectar_firebase, obtener_hora_argentina
import login  # <--- Nuevo import
import vistas_dueno
# import vistas_cliente (lo llenaremos luego)

st.set_page_config(page_title="JL Gestión Pro", layout="wide")

db = conectar_firebase()
ahora = obtener_hora_argentina()

# --- INICIALIZAR SESIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.update({'autenticado': False, 'rol': None})

# --- LÓGICA DE CONTROL ---
if not st.session_state.autenticado:
    login.mostrar_login(db) # Llama al nuevo archivo
else:
    # Sidebar y Repartidor de vistas (el código que ya tenías)
    with st.sidebar:
        st.title("JL Gestión")
        st.write(f"👤 **{st.session_state.nombre_real}**")
        if st.button("🔴 Cerrar Sesión", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    if st.session_state.rol == "negocio":
        vistas_dueno.mostrar_dueno(db, st.session_state.id_negocio, ahora, st.session_state.nombre_real)
    # ... otros roles
