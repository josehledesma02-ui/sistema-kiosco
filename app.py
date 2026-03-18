import streamlit as st
from database import conectar_firebase, obtener_hora_argentina
import login
import vistas_dueno
import vistas_cliente

# ==========================================
# 1. CONFIGURACIÓN VISUAL PRO (UI/UX)
# ==========================================
st.set_page_config(
    page_title="JL Gestión Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS Unificados (Sidebar oscuro + Texto blanco + Botones visibles)
st.markdown("""
    <style>
        /* Fondo general de la app */
        .main { background-color: #f8f9fa; }
        
        /* Estilo de métricas */
        [data-testid="stMetricValue"] { font-size: 1.8rem !important; color: #007bff; }
        
        /* Botones generales */
        .stButton>button {
            border-radius: 8px;
            height: 3em;
            transition: all 0.3s;
            font-weight: bold;
        }

        /* --- SIDEBAR PERSONALIZADO --- */
        [data-testid="stSidebar"] {
            background-image: linear-gradient(#2e3b4e, #1c2531);
        }

        /* FORZAR TODO EL TEXTO DEL SIDEBAR A BLANCO (Reloj, Negocio, Rol) */
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
        [data-testid="stSidebar"] .stText p {
            color: white !important;
            opacity: 1 !important;
        }

        /* Estilo específico para el ID de Negocio y el Reloj */
        [data-testid="stSidebar"] .stCaption {
            color: white !important;
        }

        /* --- FIX SELECTOR (SELECTBOX) --- */
        div[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
            background-color: rgba(255, 255, 255, 0.1) !important;
            color: white !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
            border-radius: 8px;
        }

        div[data-testid="stSidebar"] .stSelectbox svg {
            fill: white !important;
        }

        /* Título del selector (Panel de Control) */
        div[data-testid="stSidebar"] .stSelectbox label p {
            color: #4dabf7 !important;
            font-weight: bold !important;
        }

        /* Lista desplegable */
        div[data-baseweb="popover"] ul {
            background-color: #1c2531 !important;
            color: white !important;
            border: 1px solid #4dabf7;
        }

        div[data-baseweb="popover"] li {
            color: white !important;
        }

        div[data-baseweb="popover"] li:hover {
            background-color: #2e3b4e !important;
        }

        /* --- FIX BOTÓN CERRAR SESIÓN --- */
        section[data-testid="stSidebar"] div.stButton > button {
            background-color: rgba(255, 255, 255, 0.15) !important;
            border: 1px solid rgba(255, 255, 255, 0.4) !important;
            color: white !important;
            width: 100% !important;
            display: block;
        }

        section[data-testid="stSidebar"] div.stButton > button:hover {
            background-color: #ff4b4b !important;
            border: none !important;
            color: white !important;
            transform: scale(1.02);
        }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. INICIALIZACIÓN DE SERVICIOS
# ==========================================
db = conectar_firebase()
ahora = obtener_hora_argentina()

if 'autenticado' not in st.session_state:
    st.session_state.update({
        'autenticado': False,
        'rol': None,
        'usuario_id': None,
        'nombre_real': None,
        'id_negocio': None
    })

# ==========================================
# 3. CONTROL DE ACCESO (LOGIN O PANEL)
# ==========================================

if not st.session_state.autenticado:
    with st.container():
        st.markdown("<h2 style='text-align: center;'>🚀 Acceso al Sistema</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            id_neg_input = st.text_input("🆔 ID del Negocio").strip()
            user_input = st.text_input("👤 Usuario").strip()
            pass_input = st.text_input("🔑 Contraseña (DNI)", type="password").strip()
            
            btn_login = st.form_submit_button("INGRESAR", use_container_width=True)
            
            if btn_login:
                if id_neg_input and user_input and pass_input:
                    usuarios_ref = db.collection("usuarios").where("id_negocio", "==", id_neg_input).stream()
                    encontrado = False
                    for doc in usuarios_ref:
                        u = doc.to_dict()
                        nombre_db = str(u.get("nombre_real", "")).lower().strip()
                        usuario_db = str(u.get("usuario", "")).lower().strip()
                        input_cliente = user_input.lower().strip()
                        clave_db = str(u.get("clave", "")).strip()
                        
                        if (input_cliente == nombre_db or input_cliente == usuario_db) and pass_input == clave_db:
                            st.session_state.update({
                                'autenticado': True,
                                'rol': u.get("rol"),
                                'usuario_id': doc.id,
                                'nombre_real': u.get("nombre_real"),
                                'id_negocio': id_neg_input
                            })
                            encontrado = True
                            st.rerun()
                            break
                    if not encontrado:
                        st.error("❌ Datos incorrectos.")
                else:
                    st.warning("⚠️ Completá todos los campos.")
else:
    # --- BARRA LATERAL (SIDEBAR) ---
    with st.sidebar:
        try:
            st.image("static/images/logo_chico.png", width=100)
        except:
            st.title("🚀 JL Gestión")

        # --- AQUÍ LA NOTIFICACIÓN PARA EL SUPER ADMIN ---
        if st.session_state.rol == "super_admin":
            pendientes = db.collection("reportes_error").where("estado", "==", "pendiente").stream()
            cant = len(list(pendientes))
            if cant > 0:
                st.error(f"🔔 {cant} Reportes Nuevos")
            
        st.write(f"👤 **{st.session_state.nombre_real}**")
        st.caption(f"📍 Negocio: {st.session_state.id_negocio.upper()}")
        st.info(f"Rol: {st.session_state.rol.capitalize()}")
        
        if st.button("🔴 Cerrar Sesión"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        st.markdown("---")
        # Reloj corregido con CSS para que sea blanco
        st.caption(f"🕒 {ahora.strftime('%d/%m/%Y %H:%M')}")

    # --- REPARTIDOR DE VISTAS SEGÚN ROL ---
    rol = st.session_state.rol
    if rol == "negocio":
        vistas_dueno.mostrar_dueno(db, st.session_state.id_negocio, ahora, st.session_state.nombre_real)
    elif rol == "cliente":
        vistas_cliente.mostrar_cliente(db, st.session_state.id_negocio, st.session_state.nombre_real)
    elif rol == "super_admin":
        import vistas_super_admin
        vistas_super_admin.mostrar_super_admin(db, ahora)
    elif rol == "empleado":
        import vistas_empleado
        vistas_empleado.mostrar_empleado(db, st.session_state.id_negocio, ahora)
