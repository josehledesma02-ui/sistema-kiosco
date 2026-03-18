import streamlit as st
from modulos_dueno import vender, gastos, historial, clientes, estadisticas

def mostrar_dueno(db, id_negocio, ahora_ar, nombre_u):
    # 1. Título exacto como lo tenías
    st.title(f"🏬 Gestión Pro: {id_negocio.upper()}")
    
    # 2. Las 5 pestañas originales
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💰 Vender", "📉 Gastos", "📜 Historial", "👥 Clientes", "📊 Estadísticas"
    ])
    
    with tab1:
        # Probamos con la función estándar de tus módulos
        vender.mostrar_vender(db, id_negocio, ahora_ar)
    
    with tab2:
        gastos.mostrar_gastos(db, id_negocio, ahora_ar)
        
    with tab3:
        historial.mostrar_historial(db, id_negocio)
        
    with tab4:
        clientes.mostrar_clientes(db, id_negocio)
        
    with tab5:
        estadisticas.mostrar_estadisticas(db, id_negocio)
