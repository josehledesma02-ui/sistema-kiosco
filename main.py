import streamlit as st
from database import conectar_firebase, obtener_hora_argentina
import login
import vistas_dueno
import vistas_cliente

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="JL Gestión Pro", 
    page_icon="🛍️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. INICIALIZACIÓN DE DATOS CENTRALES
# ==========================================
db = conectar_firebase()
ahora = obtener_hora_argentina()

# --- ESTADO DE SESIÓN (Variables Globales) ---
if 'autenticado' not in st.session_state:
    st.session_state.update({
        'autenticado': False, 
        'usuario_id': None, 
        'rol': None, 
        'nombre_real': None, 
        'id_negocio': None,
        'promesa_pago': 'N/A',
        'carrito': []  # El carrito vive aquí para no borrarse al cambiar de pestaña
    })

# ==========================================
# 3. LÓGICA DE CONTROL DE ACCESO
# ==========================================

if not st.session_state.autenticado:
    # Si no está logueado, muestra la pantalla de Login del módulo login.py
    login.mostrar_login(db)

else:
    # --- PANEL LATERAL (SIDEBAR) COMÚN ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.nombre_real}")
        st.caption(f"🆔 Negocio: {st.session_state.id_negocio.upper()}")
        
        # Etiqueta visual según el rol
        if st.session_state.rol == "negocio":
            st.success("🛠️ ADMINISTRADOR")
        elif st.session_state.rol == "cliente":
            st.info("🛍️ VISTA CLIENTE")
        
        st.divider()
        
        # Botón para salir
        if st.button("🔴 Cerrar Sesión", use_container_width=True):
            # Limpiamos todo y reiniciamos
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # ==========================================
    # 4. REPARTIDOR DE VISTAS (MODULAR)
    # ==========================================
    rol_actual = st.session_state.rol

    if rol_actual == "negocio":
        # Llama al archivo vistas_dueno.py
        vistas_dueno.mostrar_dueno(
            db, 
            st.session_state.id_negocio, 
            ahora, 
            st.session_state.nombre_real
        )

    elif rol_actual == "cliente":
        # Llama al archivo vistas_cliente.py
        vistas_cliente.mostrar_cliente(
            db, 
            st.session_state.usuario_id, 
            st.session_state.nombre_real, 
            st.session_state.promesa_pago
        )

    elif rol_actual == "super_admin":
        st.warning("⚡ Modo Super Admin: Próximamente módulo de gestión global.")

    elif rol_actual == "empleado":
        st.info("👷 Modo Empleado: Próximamente módulo de ventas simplificado.")

# ==========================================
# FIN DEL ARCHIVO MAIN
# ==========================================
