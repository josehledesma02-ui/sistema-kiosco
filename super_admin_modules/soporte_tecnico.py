import streamlit as st
from datetime import datetime
import google.generativeai as genai

def mostrar(db):
    st.subheader("📩 Bandeja de Entrada: Soporte Técnico")
    
    # --- 1. CONFIGURACIÓN DE IA (GÉMINIS) ---
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("❌ No se encontró 'GEMINI_API_KEY' en los Secrets.")
        model = None
    else:
        try:
            # Forzamos la configuración básica
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            
            # SOLUCIÓN CLAVE: Especificamos el modelo sin prefijos raros
            # y dejamos que la librería decida la mejor ruta v1
            model = genai.GenerativeModel('gemini-1.5-flash')
            
        except Exception as e:
            st.warning(f"⚠️ Error al conectar con la IA: {e}")
            model = None

    try:
        # Traemos solo los reportes que están "pendientes"
        reportes_ref = db.collection("reportes_error").where("estado", "==", "pendiente").order_by("fecha", direction="DESCENDING").stream()
        
        hay_reportes = False
        for i, doc in enumerate(reportes_ref):
            hay_reportes = True
            rep = doc.to_dict()
            id_doc = doc.id
            
            # --- 2. PROCESAMIENTO DE FECHA ---
            fecha_valor = rep.get("fecha", "")
            fecha_mostrar = "S/F"
            if fecha_valor:
                try:
                    # Formateamos para que sea legible (Ej: 18/03 15:30)
                    dt = datetime.fromisoformat(fecha_valor.replace('Z', '+00:00'))
                    fecha_mostrar = dt.strftime("%d/%m %H:%M")
                except:
                    fecha_mostrar = str(fecha_valor)[:16]

            # --- 3. SEMÁFORO DE PRIORIDAD ---
            prioridad = rep.get("prioridad", "Baja")
            if "Urgente" in prioridad:
                emoji_prio = "🔴"
            elif "Alta" in prioridad:
                emoji_prio = "🟠"
            elif "Media" in prioridad:
                emoji_prio = "🟡"
            else:
                emoji_prio = "🟢"

            # --- 4. TÍTULO E INTERFAZ ---
            titulo = f"{emoji_prio} {rep.get('id_negocio', 'S/N').upper()} - {rep.get('tipo', 'Reporte')} ({fecha_mostrar})"

            with st.expander(titulo):
                st.write(f"**👤 Usuario:** {rep.get('usuario', 'Desconocido')}")
                st.write(f"**🚨 Prioridad:** {prioridad}")
                st.info(f"**💬 Mensaje del Cliente:**\n\n{rep.get('mensaje', 'Sin detalle')}")
                
                # Mostrar imágenes si existen
                fotos = rep.get("fotos") or rep.get("links_fotos") or []
                if fotos:
                    st.write("🖼️ **Capturas adjuntas:**")
                    cols_fotos = st.columns(3)
                    for idx, link in enumerate(fotos):
                        with cols_fotos[idx % 3]:
                            st.image(link, use_container_width=True)
                            st.markdown(f"[🔗 Ver Grande]({link})")

                # --- 5. CHAT CON ASISTENTE DE IA (JL-IA) ---
                st.markdown("---")
                st.markdown("#### 🤖 Consultar Solución a la IA")
                
                if model:
                    consulta = st.text_input("¿Qué necesitás saber sobre este error, José?", key=f"ai_input_{id_doc}")
                    
                    if consulta:
                        with st.spinner("Analizando reporte con Géminis..."):
                            # Le damos todo el contexto a la IA
                            prompt_contexto = f"""
                            Eres el Ingeniero de Soporte Senior de 'JL Gestión'.
                            Estás analizando un error reportado por un cliente:
                            - Negocio: {rep.get('id_negocio')}
                            - Tipo de Error: {rep.get('tipo')}
                            - Mensaje original: {rep.get('mensaje')}
                            - Prioridad: {prioridad}
                            
                            José (el administrador) te pregunta: {consulta}
                            
                            Responde de forma técnica, amigable y muy breve.
                            """
                            try:
                                respuesta_ia = model.generate_content(prompt_contexto)
                                st.chat_message("assistant").write(respuesta_ia.text)
                            except Exception as e:
                                st.error(f"Error al generar respuesta: {e}")
                else:
                    st.info("💡 El chat de IA requiere la API Key configurada.")

                st.divider()
                
                # --- 6. BOTONES DE ACCIÓN ---
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("✅ Resolver y Archivar", key=f"btn_res_{id_doc}", use_container_width=True):
                        db.collection("reportes_error").document(id_doc).update({
                            "estado": "resuelto",
                            "fecha_resolucion": datetime.now().isoformat()
                        })
                        st.success("¡Reporte solucionado!")
                        st.rerun()
                
                with col_btn2:
                    if st.button("🗑️ Eliminar Reporte", key=f"btn_del_{id_doc}", use_container_width=True):
                        db.collection("reportes_error").document(id_doc).delete()
                        st.warning("Reporte eliminado de la base de datos.")
                        st.rerun()

        if not hay_reportes:
            st.success("🙌 ¡Excelente! No tenés reportes pendientes en este momento.")

    except Exception as e:
        st.error(f"Ocurrió un error al cargar los reportes: {e}")
