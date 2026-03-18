import streamlit as st
from modulos_dueno import vender, gastos, historial, clientes, estadisticas

def mostrar_dueno(db, id_negocio, ahora_ar, nombre_u):
    # 1. Título principal
    st.title(f"🏬 Gestión Pro: {id_negocio.upper()}")
    
    # 2. Configuración de Pestañas (Tabs)
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💰 Vender", "📉 Gastos", "📜 Historial", "👥 Clientes", "📊 Estadísticas"
    ])
    
    with tab1:
        # Pestaña Vender
        vender.renderizar(db, id_negocio, ahora_ar, nombre_u)
    
    with tab2:
        # Pestaña Gastos
        gastos.renderizar(db, id_negocio, ahora_ar)
        
    with tab3:
        # Pestaña Historial
        historial.renderizar(db, id_negocio)
        
    with tab4:
        # Pestaña Clientes
        clientes.renderizar(db, id_negocio)
        
    with tab5:
        # Pestaña Estadísticas
        estadisticas.renderizar(db, id_negocio)

    # 3. SECCIÓN DE SOPORTE (Centro de Reportes)
    st.markdown("---")
    with st.expander("🆘 ¿Tenés algún problema o duda? Reportalo aquí"):
        st.subheader("📩 Centro de Reportes")
        with st.form("form_reporte_error", clear_on_submit=True):
            tipo = st.selectbox("¿Qué sucede?", [
                "Error Visual", 
                "Error de Datos", 
                "Sugerencia", 
                "Otro"
            ])
            detalle = st.text_area("Describí brevemente lo que pasó:")
            btn_enviar = st.form_submit_button("ENVIAR REPORTE A JL GESTIÓN")

            if btn_enviar:
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
                    st.success("✅ ¡Gracias! Tu reporte fue enviado con éxito.")
                    st.balloons()
                else:
                    st.warning("⚠️ Por favor, escribe un detalle antes de enviar.")
