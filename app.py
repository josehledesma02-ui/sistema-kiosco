# ==========================================
# 1. CONFIGURACIÓN VISUAL PRO (UI/UX)
# ==========================================
st.set_page_config(
    page_title="JL Gestión Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS - Corregidos para que se vea todo en el sidebar
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
        div[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
            background-color: rgba(255, 255, 255, 0.1) !important;
            color: white !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
            border-radius: 8px;
        }

        div[data-testid="stSidebar"] .stSelectbox svg {
            fill: white !important;
        }

        div[data-testid="stSidebar"] .stSelectbox label {
            color: #4dabf7 !important; 
            font-weight: bold;
        }

        /* Lista desplegable (Popover) */
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
            background-color: #ff4b4b !important;
            border: none !important;
            color: white !important;
            transform: scale(1.02);
        }
    </style>
    """, unsafe_allow_html=True)
