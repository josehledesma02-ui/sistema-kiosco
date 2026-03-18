import streamlit as st
from modulos_dueno import vender, gastos, historial, clientes, estadisticas # <--- Agregamos este

def mostrar_dueno(db, id_negocio, ahora_ar, nombre_u):
    st.title(f"🏬 Gestión Pro: {id_negocio.upper()}")
    
    # Agregamos la pestaña "Dashboard" al principio porque al dueño es lo que más le importa
    t1, t2, t3, t4, t5 = st.tabs([
        "📊 Dashboard", "🛒 Vender", "📉 Gastos", "📜 Historial", "👥 Clientes"
    ])

    with t1:
        estadisticas.renderizar(db, id_negocio) # El nuevo módulo
        
    with t2:
        vender.renderizar(db, id_negocio, ahora_ar, nombre_u)
        
    with t3:
        gastos.renderizar(db, id_negocio, ahora_ar)

    with t4:
        historial.renderizar(db, id_negocio)

    with t5:
        clientes.renderizar(db, id_negocio)

    st.divider()
    st.info("💡 **Nota:** Sistema modular JL Gestión v2.0")
