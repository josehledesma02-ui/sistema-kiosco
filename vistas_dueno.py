import streamlit as st
from modulos_dueno import vender, gastos, historial, clientes, estadisticas

def mostrar_dueno(db, id_negocio, ahora_ar, nombre_u):
    # 1. Título principal
    st.title(f"🏬 Gestión Pro: {id_negocio.upper()}")
    
    # 2. TUS PESTAÑAS (Con los nombres de función corregidos)
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💰 Vender", "📉 Gastos", "📜 Historial", "👥 Clientes", "📊 Estadísticas"
    ])
    
    with tab1:
        # En el archivo vender.py, la función suele llamarse mostrar_vender
        vender.mostrar_vender(db, id_negocio, ahora_ar)
    
    with tab2:
        gastos.mostrar_gastos(db, id_negocio, ahora_ar)
        
    with tab3:
        historial.mostrar_historial(db, id_negocio)
        
    with tab4:
        clientes.mostrar_clientes(db, id_negocio)
        
    with tab5:
        estadisticas.mostrar_estadisticas(db, id_negocio)

    # 3. SECCIÓN DE SOPORTE (Al final de la página)
    st.markdown("---")
    with st.expander("🆘 ¿Tenés algún problema o duda? Reportalo aquí"):
        st.subheader("📩 Centro de Reportes")
        
        with st.form("form_reporte_error", clear_on_submit=True):
            tipo_fallo = st.selectbox("¿Qué sucede?", [
                "Error Visual", "Error al Cargar Datos", 
                "Lentitud", "Sugerencia", "Otro"
            ])
            
            detalle = st.text_area("Describí brevemente lo que pasó:")
            btn_enviar = st.form_submit_button("ENVIAR REPORTE A JL GESTIÓN")

            if btn_enviar:
                if detalle:
                    reporte = {
                        "id_negocio": id_negocio,
                        "usuario": nombre_u,
                        "mensaje": detalle,
                        "tipo": tipo_fallo,
                        "fecha": ahora_ar,
                        "estado": "pendiente"
                    }
                    db.collection("reportes_error").add(reporte)
                    st.success("✅ Reporte enviado al Administrador.")
                    st.balloons()
                else:
                    st.warning("⚠️ Por favor, escribí un detalle.")
