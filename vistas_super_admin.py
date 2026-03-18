import streamlit as st
# Agregamos el import del nuevo módulo que creaste
from super_admin_modules import dashboard, gestion_negocios, soporte_tecnico, sugerencias, alta_negocios

def mostrar_super_admin(db, ahora):
    st.title("⚡ SISTEMA MAESTRO (José Admin)")
    /* ========================================== */
        /* FIX: SELECTBOX DEL PANEL DE CONTROL       */
        /* ========================================== */
        /* Cambia el color del texto y el fondo del selector en el sidebar */
        div[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
            background-color: rgba(255, 255, 255, 0.05) !important;
            color: white !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 8px;
        }

        /* Cambia el color de la flechita del selector */
        div[data-testid="stSidebar"] .stSelectbox svg {
            fill: white !important;
        }

        /* Estilo para las opciones cuando se despliega la lista */
        div[data-baseweb="popover"] ul {
            background-color: #1c2531 !important; /* Fondo oscuro igual al sidebar */
            color: white !important;
        }

        div[data-baseweb="popover"] li:hover {
            background-color: #2e3b4e !important; /* Resalte al pasar el mouse */
        }
    # Menú lateral actualizado con la opción de Alta
    menu = [
        "📊 Dashboard Global", 
        "🆕 Alta de Negocio", 
        "🏪 Gestión Agresiva", 
        "🛠️ Soporte & Errores", 
        "💡 Sugerencias Recibidas"
    ]
    choice = st.sidebar.selectbox("Panel de Control", menu)

    if choice == "📊 Dashboard Global":
        dashboard.mostrar(db)
        
    elif choice == "🆕 Alta de Negocio":
        # Llamamos al nuevo módulo pasándole 'ahora' para la fecha de alta
        alta_negocios.mostrar(db, ahora)
        
    elif choice == "🏪 Gestión Agresiva":
        gestion_negocios.mostrar(db)
        
    elif choice == "🛠️ Soporte & Errores":
        soporte_tecnico.mostrar(db)
        
    elif choice == "💡 Sugerencias Recibidas":
        sugerencias.mostrar(db)
