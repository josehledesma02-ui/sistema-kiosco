import streamlit as st
from datetime import datetime

def mostrar(db):
    st.header("🛠️ Centro de Soporte e Inteligencia")
    st.markdown("---")

    # 1. Traer reportes de la base de datos
    reportes_ref = db.collection("reportes_error").order_by("fecha", direction="DESCENDING").limit(20).stream()
    
    reportes = []
    for r in reportes_ref:
        data = r.to_dict()
        data['id'] = r.id
        reportes.append(data)

    if not reportes:
        st.info("✅ No hay reportes de error pendientes. ¡El sistema está estable!")
        return

    # 2. Layout de dos columnas: Lista de Errores y Panel de Chat
    col_lista, col_chat = st.columns([1, 1.5])

    with col_lista:
        st.subheader("📋 Reportes Recientes")
        for i, rep in enumerate(reportes):
            # Formato de cada tarjeta de error
            tipo = rep.get("tipo", "Error")
            fecha = rep.get("fecha")
            # Convertir fecha de Firebase a string legible
            fecha_str = fecha.strftime("%d/%m %H:%M") if fecha else "S/F"
            
            with st.expander(f"🔴 {tipo} - {fecha_str}"):
                st.write(f"**Usuario:** {rep.get('usuario', 'Desconocido')}")
                st.write(f"**Mensaje:** {rep.get('mensaje', 'Sin descripción')}")
                if st.button(f"Analizar con IA #{i}", use_container_width=True):
                    st.session_state.error_seleccionado = rep

    with col_chat:
        st.subheader("💬 Asistente Técnico (Gemini)")
        
        if "error_seleccionado" in st.session_state:
            err = st.session_state.error_seleccionado
            
            # Contenedor de "Chat"
            with st.container(border=True):
                st.markdown(f"**Analizando reporte ID:** `{err['id']}`")
                st.info(f"🔍 **Diagnóstico Automático:**\n\nEl error reportado por *{err['usuario']}* parece ser un problema de {err['tipo'].lower()}.")
                
                # Simulación de respuesta fluida de IA
                st.markdown("---")
                st.markdown("### 🤖 Sugerencia de Resolución:")
                if "login" in err['mensaje'].lower():
                    st.write("👉 El usuario tiene problemas con sus credenciales. Sugiero resetear su contraseña desde la **Gestión Agresiva**.")
                elif "stock" in err['mensaje'].lower():
                    st.write("👉 Parece un error de permisos en la base de datos de productos. Revisar el ID del negocio.")
                else:
                    st.write("👉 Recomiendo contactar al dueño del local para verificar si su conexión a internet es estable.")

                # Acciones rápidas
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Marcar como Solucionado", use_container_width=True):
                        db.collection("reportes_error").document(err['id']).delete()
                        st.success("Reporte eliminado.")
                        del st.session_state.error_seleccionado
                        st.rerun()
                with c2:
                    st.button("📩 Notificar al Usuario", use_container_width=True)

        else:
            st.write("👈 Seleccioná un reporte de la izquierda para iniciar la conversación técnica.")

    # 3. Función de Chat Libre (Opcional abajo)
    st.markdown("---")
    with st.expander("🗨️ Consulta libre a la IA del sistema"):
        pregunta = st.text_input("Escribí tu duda técnica aquí...")
        if pregunta:
            st.write(f"🤖 **Respuesta:** José, para resolver '{pregunta}', deberías revisar la colección de Firebase correspondiente. ¿Querés que lo haga por vos?")
