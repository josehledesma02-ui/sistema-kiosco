import streamlit as st
# Agregamos el import del nuevo módulo que creaste
from super_admin_modules import dashboard, gestion_negocios, soporte_tecnico, sugerencias, alta_negocios

def mostrar_super_admin(db, ahora):
    st.title("⚡ SISTEMA MAESTRO (José Admin)")
    
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
