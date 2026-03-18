import streamlit as st
from super_admin_modules import dashboard, Alta de Negocio, gestion_negocios, soporte_tecnico, sugerencias

def mostrar_super_admin(db, ahora):
    st.title("⚡ SISTEMA MAESTRO (José Admin)")
    
    # Menú lateral específico para el Super Admin
    menu = ["📊 Dashboard Global", "🏪 Gestión Agresiva", "🛠️ Soporte & Errores", "💡 Sugerencias Recibidas"]
    choice = st.sidebar.selectbox("Panel de Control", menu)

    if choice == "📊 Dashboard Global":
        dashboard.mostrar(db)
        
    elif choice == "🏪 Gestión Agresiva":
        gestion_negocios.mostrar(db)
        
    elif choice == "🛠️ Soporte & Errores":
        soporte_tecnico.mostrar(db)
        
    elif choice == "💡 Sugerencias Recibidas":
        sugerencias.mostrar(db)

    elif choice == "🆕 Alta de Negocio":
        alta_negocios.mostrar(db, ahora)
