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

# Estilos CSS para que no parezca un Excel y se vea como un Software
st.markdown("""
    <style>
        /* Fondo y contenedores */
        .main { background-color: #f8f9fa; }
        [data-testid="stMetricValue"] { font-size: 1.8rem !important; color: #007bff; }
        
        /* Estilo de botones */
        .stButton>button {
            border-radius: 8px;
            height: 3em;
            transition: all 0.3s;
            font-weight: bold;
        }
        .stButton>button:hover {
            border-color: #007bff;
            color: #007bff;
            transform: translateY(-2px);
        }
        
        /* Sidebar decorado */
        [data-testid="stSidebar"] {
            background-image: linear-gradient(#2e3b4e, #1c2531);
            color: white;
        }
        [data-testid="stSidebar"] * { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. INICIALIZACIÓN DE SERVICIOS
# ==========================================
db = conectar_firebase()
ahora = obtener_hora_argentina()

# Inicializar variables de sesión para que no den error al arrancar
if 'autenticado' not in st.session_state:
    st.session_state.update({
        'autenticado': False,
        'rol': None,
        'usuario_id': None,
        'nombre_real': "Usuario",
        'id_negocio': None,
        'carrito': [] # Carrito global para que no se pierda al navegar
    })

# ==========================================
# 3. CONTROL DE ACCESO (LOGIN O PANEL)
# ==========================================

if not st.session_state.autenticado:
    # Si no está logueado, llamamos al módulo de login
    login.mostrar_login(db)
else:
    # --- BARRA LATERAL (SIDEBAR) ---
    with st.sidebar:
        # Espacio para Logo (si existe en tu carpeta static/images)
        try:
            st.image("static/images/logo_chico.png", width=100)
        except:
            st.title("🚀 JL Gestión")
            
        st.write(f"👤 **{st.session_state.nombre_real}**")
        st.caption(f"📍 Negocio: {st.session_state.id_negocio.upper()}")
        st.divider()
        
        # Menú de navegación rápido (opcional, las pestañas están en el centro)
        st.info(f"Rol: {st.session_state.rol.capitalize()}")
        
        if st.button("🔴 Cerrar Sesión", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # --- REPARTIDOR DE VISTAS SEGÚN ROL ---
    rol = st.session_state.rol

    if rol == "negocio":
        # Llama al archivo que gestiona las pestañas del Dueño
        vistas_dueno.mostrar_dueno(
            db, 
            st.session_state.id_negocio, 
            ahora, 
            st.session_state.nombre_real
        )

    elif rol == "cliente":
        # Llama a la vista simplificada de deudas para el cliente
        vistas_cliente.mostrar_cliente(
            db, 
            st.session_state.usuario_id, 
            st.session_state.nombre_real,
            st.session_state.get('promesa_pago', 'N/A')
        )

    elif rol == "super_admin":
        st.title("⚡ Panel Maestro (Super Admin)")
        st.write("Gestionando todos los negocios activos...")
        # Aquí llamarías a vistas_super_admin.renderizar()

    elif rol == "empleado":
        # El empleado usa una versión recortada de las herramientas del dueño
        import vistas_empleado
        vistas_empleado.mostrar_empleado(db, st.session_state.id_negocio, ahora)

# ==========================================
# 4. FOOTER / NOTA AL PIE
# ==========================================
st.sidebar.markdown("---")
st.sidebar.caption(f"🕒 {ahora.strftime('%d/%m/%Y %H:%M')}")
