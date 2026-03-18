import streamlit as st
# Importamos todos los módulos de la carpeta super_admin_modules
from super_admin_modules import (
    dashboard, 
    gestion_negocios, 
    soporte_tecnico, 
    sugerencias, 
    alta_negocios
)

def mostrar_super_admin(db, ahora):
    # Título principal del Panel Maestro
    st.title("⚡ SISTEMA MAESTRO (José Admin)")
    st.markdown("---")

    # Menú lateral específico para el Super Admin
    # Agregamos iconos para que sea más visual y fácil de leer
    menu = [
        "📊 Dashboard Global", 
        "🆕 Alta de Negocio", 
        "🏪 Gestión Agresiva", 
        "🛠️ Soporte & Errores", 
        "💡 Sugerencias Recibidas"
    ]
    
    # Este es el selector que ahora se verá oscuro gracias al CSS en app.py
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
