import streamlit as st
from modulos_dueno import vender, gastos, historial, clientes, estadisticas, reportes

def mostrar_dueno(db, id_negocio, ahora_ar, nombre_u):
    # 1. Título principal
    st.title(f"🏬 Gestión Pro: {id_negocio.upper()}")
    
    # 2. Configuración de 6 Pestañas
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "💰 Vender", "📉 Gastos", "📜 Historial", "👥 Clientes", "📊 Estadísticas", "🆘 Soporte"
    ])
    
    with tab1:
        vender.renderizar(db, id_negocio, ahora_ar, nombre_u)
    
    with tab2:
        gastos.renderizar(db, id_negocio, ahora_ar)
        
    with tab3:
        historial.renderizar(db, id_negocio)
        
    with tab4:
        clientes.renderizar(db, id_negocio)
        
    with tab5:
        estadisticas.renderizar(db, id_negocio)
        
    with tab6:
        # Pestaña dedicada al Soporte
        reportes.renderizar(db, id_negocio, ahora_ar, nombre_u)
