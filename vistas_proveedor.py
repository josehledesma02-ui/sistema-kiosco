import streamlit as st

def mostrar_soporte_tecnico(db, id_negocio, nombre_real, ahora):
    # Verificamos el nivel de acceso actual
    nivel = st.session_state.get("nivel_acceso", 1)
    es_restringido = (nivel == 2)

    st.markdown("---")
    
    # El expander siempre está, pero el contenido cambia según el nivel
    with st.expander("🆘 ¿Tenés algún problema o duda? Reportalo aquí"):
        if es_restringido:
            st.error("🚫 **Soporte Técnico Limitado**")
            st.info("Para enviar reportes técnicos, el negocio debe estar al día con el abono.")
        
        st.subheader("📩 Centro de Reportes")
        
        # El formulario se deshabilita si nivel es 2
        with st.form("form_reporte_error", clear_on_submit=True):
            tipo_fallo = st.selectbox("¿Qué sucede?", [
                "Error Visual", 
                "Error al Cargar Datos", 
                "Lentitud en el Sistema", 
                "Sugerencia de Mejora",
                "Otro"
            ], disabled=es_restringido)
            
            detalle = st.text_area("Describí brevemente lo que pasó:", 
                                  placeholder="Ej: No se actualiza el precio del alfajor...",
                                  disabled=es_restringido)
            
            # El botón también se deshabilita
            btn_enviar = st.form_submit_button("ENVIAR REPORTE A JL GESTIÓN", 
                                              disabled=es_restringido, 
                                              use_container_width=True)

            if btn_enviar:
                if detalle:
                    # Datos del reporte
                    reporte = {
                        "id_negocio": id_negocio,
                        "usuario": nombre_real,
                        "mensaje": detalle,
                        "tipo": tipo_fallo,
                        "fecha": ahora,
                        "estado": "pendiente"
                    }
                    
                    # Guardar en Firebase
                    db.collection("reportes_error").add(reporte)
                    
                    st.success("✅ ¡Gracias! Tu reporte fue enviado al Administrador.")
                    st.balloons() 
                else:
                    st.warning("⚠️ Por favor, escribí un detalle para que podamos ayudarte.")

    if es_restringido:
        st.caption("🔒 El envío de reportes está deshabilitado para cuentas con avisos de pago.")
