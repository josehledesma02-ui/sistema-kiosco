import streamlit as st
from modulos_dueno import vender, gastos, historial, clientes, estadisticas

def mostrar_dueno(db, id_negocio, ahora_ar, nombre_u):
    st.title(f"🏬 Gestión Pro: {id_negocio.upper()}")

    # Volvemos a la estructura original de pestañas
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💰 Vender", "📉 Gastos", "📜 Historial", "👥 Clientes", "📊 Estadísticas"
    ])

    with tab1:
        # Usamos la llamada original que tenías (vender.vender)
        vender.vender(db, id_negocio, ahora_ar)

    with tab2:
        gastos.gastos(db, id_negocio, ahora_ar)

    with tab3:
        historial.historial(db, id_negocio)

    with tab4:
        clientes.clientes(db, id_negocio)

    with tab5:
        estadisticas.estadisticas(db, id_negocio)
