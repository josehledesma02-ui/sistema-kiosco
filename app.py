import streamlit as st
from database import conectar_firebase, obtener_hora_argentina
import login
import vistas_dueno
import vistas_cliente

# ==========================================
# 1. CONFIGURACIÓN VISUAL PRO (UI/UX)
# ==========================================
# Estilos CSS
st.markdown("""
    <style>
        /* Fondo general de la app */
        .main { background-color: #f8f9fa; }
        
        /* Estilo de métricas */
        [data-testid="stMetricValue"] { font-size: 1.8rem !important; color: #007bff; }
        
        /* Botones generales de la derecha */
        .stButton>button {
            border-radius: 8px;
            height: 3em;
            transition: all 0.3s;
            font-weight: bold;
        }

        /* --- SIDEBAR PERSONALIZADO --- */
        [data-testid="stSidebar"] {
            background-image: linear-gradient(#2e3b4e, #1c2531);
            color: white !important;
        }

        /* Forzar que todos los textos del sidebar sean blancos */
        [data-testid="stSidebar"] * {
            color: white !important;
        }

        /* --- FIX: SELECTOR (SELECTBOX) DEL PANEL DE CONTROL --- */
        /* Cambia el recuadro del selector */
        div[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
            background-color: rgba(255, 255, 255, 0.1) !important;
            color: white !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
            border-radius: 8px;
        }

        /* Color de la flechita del selector */
        div[data-testid="stSidebar"] .stSelectbox svg {
            fill: white !important;
        }

        /* Título del selector (Panel de Control) */
        div[data-testid="stSidebar"] .stSelectbox label {
            color: #4dabf7 !important; /* Un azul claro para que resalte */
            font-weight: bold;
        }

        /* Lista desplegable que se abre (Popover) */
        div[data-baseweb="popover"] ul {
            background-color: #1c2531 !important;
            color: white !important;
            border: 1px solid #4dabf7;
        }

        div[data-baseweb="popover"] li:hover {
            background-color: #2e3b4e !important;
            color: white !important;
        }

        /* --- FIX: BOTÓN CERRAR SESIÓN --- */
        section[data-testid="stSidebar"] div.stButton > button {
            background-color: rgba(255, 255, 255, 0.15) !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
            color: white !important;
            width: 100%;
            margin-top: 10px;
        }

        section[data-testid="stSidebar"] div.stButton > button:hover {
            background-color: #ff4b4b !important; /* Rojo al pasar el mouse */
            border: none !important;
            color: white !important;
            transform: scale(1.02);
        }

        /* Icono de la campana de notificaciones o logout si existiera */
        .st-emotion-cache-17l9mre { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

/* 2. Selector 'Alta de Negocio' (Selectbox) */
/* Cambia el fondo del recuadro principal y el color del texto */
div[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
    background-color: rgba(255, 255, 255, 0.05) !important;
    color: white !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
}

/* Cambia el color de la flecha de la lista desplegable */
div[data-testid="stSidebar"] .stSelectbox svg {
    fill: white !important;
}

/* 3. La Lista Desplegable (Popover) */
/* Forzamos a que la lista de opciones que se abre también sea oscura */
div[data-baseweb="popover"] ul {
    background-color: #1c2531 !important; /* Mismo color oscuro del sidebar */
    color: white !important;
}

/* Efecto hover sobre las opciones de la lista */
div[data-baseweb="popover"] li:hover {
    background-color: #2e3b4e !important; /* Un poco más claro al pasar el mouse */
    color: white !important;
}

# ==========================================
# 2. INICIALIZACIÓN DE SERVICIOS
# ==========================================
db = conectar_firebase()
ahora = obtener_hora_argentina()

# Inicializar variables de sesión si no existen
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
    # --- FORMULARIO DE LOGIN (CORREGIDO Y ENCAPSULADO) ---
    with st.container():
        st.markdown("<h2 style='text-align: center;'>🚀 Acceso al Sistema</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            id_neg_input = st.text_input("🆔 ID del Negocio").strip()
            user_input = st.text_input("👤 Usuario (Nombre y Apellido)").strip()
            pass_input = st.text_input("🔑 Contraseña (DNI)", type="password").strip()
            
            btn_login = st.form_submit_button("INGRESAR", use_container_width=True)
            
            if btn_login:
                if id_neg_input and user_input and pass_input:
                    # Buscamos en la colección 'usuarios' filtrando por el negocio
                    usuarios_ref = db.collection("usuarios").where("id_negocio", "==", id_neg_input).stream()
                    
                    encontrado = False
                    for doc in usuarios_ref:
                        u = doc.to_dict()
                        
                        # VALIDACIÓN FLEXIBLE
                        nombre_db = str(u.get("nombre_real", "")).lower().strip()
                        usuario_db = str(u.get("usuario", "")).lower().strip()
                        input_cliente = user_input.lower().strip()
                        
                        clave_db = str(u.get("clave", "")).strip()
                        clave_input = pass_input.strip()
                        
                        if (input_cliente == nombre_db or input_cliente == usuario_db) and clave_input == clave_db:
                            st.session_state.update({
                                'autenticado': True,
                                'rol': u.get("rol"),
                                'usuario_id': doc.id,
                                'nombre_real': u.get("nombre_real"),
                                'id_negocio': id_neg_input
                            })
                            encontrado = True
                            st.success(f"✅ Bienvenido, {u.get('nombre_real')}")
                            st.rerun()
                            break
                    
                    if not encontrado:
                        st.error("❌ Datos incorrectos. Revisá el ID de negocio, Usuario o DNI.")
                else:
                    st.warning("⚠️ Completá todos los campos para ingresar.")
else:
    # --- CONTENIDO CUANDO YA ESTÁ AUTENTICADO ---
    
    # --- BARRA LATERAL (SIDEBAR) ---
    with st.sidebar:
        try:
            st.image("static/images/logo_chico.png", width=100)
        except:
            st.title("🚀 JL Gestión")
            
        st.write(f"👤 **{st.session_state.nombre_real}**")
        st.caption(f"📍 Negocio: {st.session_state.id_negocio.upper()}")
        st.divider()
        st.info(f"Rol: {st.session_state.rol.capitalize()}")
        
        if st.button("🔴 Cerrar Sesión", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        st.sidebar.markdown("---")
        st.sidebar.caption(f"🕒 {ahora.strftime('%d/%m/%Y %H:%M')}")

    # --- REPARTIDOR DE VISTAS SEGÚN ROL ---
    rol = st.session_state.rol

    if rol == "negocio":
        vistas_dueno.mostrar_dueno(
            db, 
            st.session_state.id_negocio, 
            ahora, 
            st.session_state.nombre_real
        )

    elif rol == "cliente":
        # PASAMOS EL ID_NEGOCIO Y EL NOMBRE REAL PARA BUSCAR LA DEUDA CORRECTAMENTE
        vistas_cliente.mostrar_cliente(
            db, 
            st.session_state.id_negocio,
            st.session_state.nombre_real
        )

    elif rol == "super_admin":
        # Importamos el archivo de la vista
        import vistas_super_admin
        # Llamamos a la función pasándole la base de datos y la hora
        vistas_super_admin.mostrar_super_admin(db, ahora)

    elif rol == "empleado":
        import vistas_empleado
        vistas_empleado.mostrar_empleado(db, st.session_state.id_negocio, ahora)
