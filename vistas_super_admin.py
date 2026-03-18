import streamlit as st
# Importamos todos los módulos de la carpeta super_admin_modules
from super_admin_modules import (
    dashboard, 
    gestion_negocios, 
    soporte_tecnico, 
    sugerencias, 
    alta_negocios,
    historial_global  # <--- 1. AGREGADO AQUÍ
)

def mostrar_super_admin(db, ahora):
    # Título principal del Panel Maestro
    st.title("⚡ SISTEMA MAESTRO (José Admin)")
    st.markdown("---")

    # Menú lateral específico para el Super Admin
    menu = [
        "📊 Dashboard Global", 
        "🆕 Alta de Negocio", 
        "🏪 Gestión Agresiva", 
        "🛠️ Soporte & Errores", 
        "📜 Historial Global",  # <--- 2. AGREGADO AL MENÚ
        "💡 Sugerencias Recibidas"
    ]
    
    # Selector del menú lateral
    choice = st.sidebar.selectbox("Panel de Control", menu)

    # Lógica de navegación del Super Admin
    if choice == "📊 Dashboard Global":
        dashboard.mostrar(db)
        
    elif choice == "🆕 Alta de Negocio":
        # Llamamos al nuevo módulo pasándole 'ahora' para la fecha de alta
        alta_negocios.mostrar(db, ahora)
        
    elif choice == "🏪 Gestión Agresiva":
        gestion_negocios.mostrar(db)
        
    elif choice == "🛠️ Soporte & Errores":
        soporte_tecnico.mostrar(db)

    elif choice == "📜 Historial Global": # <--- 3. LÓGICA AGREGADA
        historial_global.mostrar(db)
        
    elif choice == "💡 Sugerencias Recibidas":
        sugerencias.mostrar(db)
