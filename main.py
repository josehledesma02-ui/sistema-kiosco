import streamlit as st
from database import conectar_firebase, obtener_hora_argentina

# IMPORTAMOS LOS MÓDULOS (Los archivos que creaste recién)
import vistas_dueno
# import vistas_cliente (lo llenaremos después)

st.set_page_config(page_title="JL Gestión Pro", layout="wide")

# Iniciamos conexión
db = conectar_firebase()
ahora = obtener_hora_argentina()

# --- SESIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.update({
        'autenticado': False, 'rol': None, 'id_negocio': None, 
        'nombre_real': None, 'usuario_id': None, 'carrito': []
    })

# --- PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align: center;'>🔐 Ingreso JL Gestión</h1>", unsafe_allow_html=True)
    
    with st.container():
        neg_id = st.text_input("ID Negocio").strip().lower()
        user_nm = st.text_input("Usuario")
        pass_wd = st.text_input("Contraseña", type="password")
        
        if st.button("INGRESAR", use_container_width=True, type="primary"):
            # Buscamos al usuario en Firebase
            u_ref = db.collection("usuarios").where("id_negocio", "==", neg_id).where("nombre", "==", user_nm).limit(1).get()
            
            if u_ref and str(u_ref[0].to_dict().get('password')) == pass_wd:
                d = u_ref[0].to_dict()
                st.session_state.update({
                    'autenticado': True, 'usuario_id': u_ref[0].id,
                    'rol': d.get('rol').lower(), 'nombre_real': d.get('nombre'),
                    'id_negocio': d.get('id_negocio')
                })
                st.rerun()
            else:
                st.error("⚠️ Datos incorrectos. Verificá ID de negocio, usuario o clave.")

# --- INTERFAZ POST-LOGIN ---
else:
    # Sidebar común para todos los roles
    with st.sidebar:
        st.title("JL Gestión")
        st.write(f"👤 **{st.session_state.nombre_real}**")
        st.write(f"🏢 {st.session_state.id_negocio.upper()}")
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # Lógica que decide qué archivo mostrar
    rol = st.session_state.rol
    
    if rol == "negocio":
        vistas_dueno.mostrar_dueno(db, st.session_state.id_negocio, ahora, st.session_state.nombre_real)
    
    elif rol == "cliente":
        st.warning("Página de cliente en construcción...")
        # Aquí llamaríamos a: vistas_cliente.mostrar_cliente(...)

    elif rol == "super_admin":
        st.info("Bienvenido, Super Admin.")
