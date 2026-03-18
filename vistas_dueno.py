import streamlit as st
from modulos_dueno import vender, gastos, historial, clientes, estadisticas

def mostrar_dueno(db, id_negocio, ahora_ar, nombre_u):
    # 1. Título principal
    st.title(f"🏬 Gestión Pro: {id_negocio.upper()}")
    
    # 2. Configuración de Pestañas
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💰 Vender", "📉 Gastos", "📜 Historial", "👥 Clientes", "📊 Estadísticas"
    ])
    
    with tab1:
        # CORRECCIÓN: Tu función en vender.py se llama 'renderizar'
        vender.renderizar(db, id_negocio, ahora_ar, nombre_u)
    
    with tab2:
        # Asumiendo que los otros siguen el estándar 'mostrar_...' o similar
        # Si estos fallan, avisame y los ajustamos igual que el de vender
        try:
            gastos.gastos(db, id_negocio, ahora_ar)
        except AttributeError:
            gastos.mostrar_gastos(db, id_negocio, ahora_ar)
        
    with tab3:
        try:
            historial.historial(db, id_negocio)
        except AttributeError:
            historial.mostrar_historial(db, id_negocio)
        
    with tab4:
        try:
            clientes.clientes(db, id_negocio)
        except AttributeError:
            clientes.mostrar_clientes(db, id_negocio)
        
    with tab5:
        try:
            estadisticas.estadisticas(db, id_negocio)
        except AttributeError:
            estadisticas.mostrar_estadisticas(db, id_negocio)

    # 3. SECCIÓN DE SOPORTE (Opcional, al final de todo)
    st.markdown("---")
    with st.expander("🆘 ¿Tenés algún problema o duda? Reportalo aquí"):
        st.subheader("📩 Centro de Reportes")
        with st.form("form_reporte_error", clear_on_submit=True):
            tipo = st.selectbox("¿Qué sucede?", ["Error Visual", "Error de Datos", "Sugerencia", "Otro"])
            detalle = st.text_area("Describí brevemente lo que pasó:")
            if st.form_submit_button("ENVIAR REPORTE"):
                if detalle:
                    reporte = {
                        "id_negocio": id_negocio,
                        "usuario": nombre_u,
                        "mensaje": detalle,
                        "tipo": tipo,
                        "fecha": ahora_ar.isoformat(),
                        "estado": "pendiente"
                    }
                    db.collection("reportes_error").add(reporte)
                    st.success("✅ ¡Gracias! Reporte enviado.")
                    st.balloons()
