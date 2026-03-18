import streamlit as st

def mostrar_empleado(db, id_negocio, ahora, nombre_real):
    # --- 1. VERIFICACIÓN DE NIVEL DE ACCESO ---
    # Traemos el nivel desde el session_state que seteamos en app.py
    nivel = st.session_state.get("nivel_acceso", 1)
    es_restringido = True if nivel == 2 else False

    st.title(f"💼 Panel de Empleado - {id_negocio.upper()}")
    st.write(f"Bienvenido/a, **{nombre_real}**")

    # Si está restringido, tiramos el aviso antes que nada
    if es_restringido:
        st.warning("⚠️ **SISTEMA EN MODO LECTURA**: Tu negocio tiene un aviso de pago pendiente. Algunas funciones de carga están deshabilitadas.")

    # --- AQUÍ IRÍA TU LÓGICA DE VENTAS / STOCK ---
    # Ejemplo de cómo bloquear un botón de venta:
    # st.button("Registrar Venta", disabled=es_restringido)

    st.write("### Tareas del día")
    st.info("Próximamente verás aquí tu agenda de turnos y objetivos.")

    # ==========================================
    # SECCIÓN DE SOPORTE TÉCNICO (PROTEGIDA)
    # ==========================================
    st.markdown("---")
    
    # Usamos el parámetro 'expanded' para que no distraiga si está todo bien
    with st.expander("🆘 ¿Tenés algún problema o duda? Reportalo aquí"):
        st.subheader("📩 Centro de Reportes")
        
        # El formulario se deshabilita si el nivel es 2 (Restringido)
        # para que ni siquiera puedan saturarte con reportes de "no puedo vender"
        with st.form("form_reporte_error", clear_on_submit=True):
            tipo_fallo = st.selectbox("¿Qué sucede?", [
                "Error Visual", 
                "Error al Cargar Datos", 
                "Lentitud en el Sistema", 
                "Sugerencia de Mejora",
                "Otro"
            ], disabled=es_restringido) # BLOQUEADO SI NO PAGÓ
            
            detalle = st.text_area("Describí brevemente lo que pasó:", 
                                  placeholder="Ej: No se actualiza el precio del alfajor...",
                                  disabled=es_restringido) # BLOQUEADO SI NO PAGÓ
            
            # El botón cambia de color o texto según el estado
            texto_boton = "ENVIAR REPORTE" if not es_restringido else "FUNCIÓN DESHABILITADA"
            btn_enviar = st.form_submit_button(texto_boton, use_container_width=True, disabled=es_restringido)

            if btn_enviar:
                if detalle:
                    reporte = {
                        "id_negocio": id_negocio,
                        "usuario": nombre_real,
                        "mensaje": detalle,
                        "tipo": tipo_fallo,
                        "fecha": ahora,
                        "estado": "pendiente"
                    }
                    
                    db.collection("reportes_error").add(reporte)
                    st.success("✅ ¡Gracias! Tu reporte fue enviado al Administrador.")
                    st.balloons() 
                else:
                    st.warning("⚠️ Por favor, escribí un detalle para que podamos ayudarte.")

    if es_restringido:
        st.caption("🔒 Algunas funciones han sido limitadas por la administración del sistema.")
