import streamlit as st
from datetime import datetime

def mostrar(db):
    st.subheader("🛠️ Panel de Control de Soporte Técnico")
    st.write("Gestioná los reportes enviados por los negocios y revisá las capturas de error.")

    try:
        # Traemos los reportes ordenados por fecha (más recientes primero)
        reportes_ref = db.collection("reportes_error").order_by("fecha", direction="DESCENDING").stream()
        
        hay_reportes = False
        for doc in reportes_ref:
            hay_reportes = True
            rep = doc.to_dict()
            id_doc = doc.id
            
            # --- PROCESAMIENTO DE FECHA ---
            fecha_valor = rep.get("fecha")
            fecha_str = "S/F"
            if fecha_valor:
                if isinstance(fecha_valor, str):
                    try:
                        fecha_obj = datetime.fromisoformat(fecha_valor.replace('Z', '+00:00'))
                        fecha_str = fecha_obj.strftime("%d/%m %H:%M")
                    except:
                        fecha_str = str(fecha_valor)[:16]
                elif hasattr(fecha_valor, 'strftime'):
                    fecha_str = fecha_valor.strftime("%d/%m %H:%M")

            # --- COLOR SEGÚN PRIORIDAD ---
            prioridad = rep.get("prioridad", "Baja")
            emoji_prio = "🟢"
            if prioridad == "Urgente": emoji_prio = "🔴"
            elif prioridad == "Alta": emoji_prio = "🟠"
            elif prioridad == "Media": emoji_prio = "🟡"

            # --- DISEÑO DEL EXPANDER ---
            titulo_expander = f"{emoji_prio} {rep.get('id_negocio', 'S/N').upper()} - {rep.get('tipo', 'Reporte')} ({fecha_str})"
            
            with st.expander(titulo_expander):
                st.write(f"**👤 Usuario:** {rep.get('usuario', 'Desconocido')}")
                st.write(f"**🚨 Prioridad:** {prioridad}")
                st.info(f"**💬 Mensaje:** {rep.get('mensaje', 'Sin detalle')}")

                # --- SECCIÓN DE FOTOS (ImgBB) ---
                links = rep.get("links_fotos", []) # Cambiamos a 'links_fotos' que es como lo guarda el nuevo reporte
                if links:
                    st.write("🖼️ **Capturas adjuntas:**")
                    cols = st.columns(len(links) if len(links) < 4 else 4)
                    for idx, link in enumerate(links):
                        with cols[idx % 4]:
                            st.image(link, use_container_width=True)
                            st.markdown(f"[🔗 Ver pantalla completa]({link})")
                else:
                    st.write("⚪ _Sin capturas adjuntas._")

                st.divider()
                
                # --- ACCIONES ---
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Marcar como Resuelto", key=f"res_{id_doc}", use_container_width=True):
                        db.collection("reportes_error").document(id_doc).update({"estado": "resuelto"})
                        st.success("Reporte marcado como resuelto.")
                        st.rerun()
                with c2:
                    if st.button("🗑️ Eliminar Reporte", key=f"del_{id_doc}", use_container_width=True):
                        db.collection("reportes_error").document(id_doc).delete()
                        st.warning("Reporte eliminado definitivamente.")
                        st.rerun()

        if not hay_reportes:
            st.info("No hay reportes técnicos en la lista. ¡Todo funciona bien!")

    except Exception as e:
        st.error(f"Error al cargar el panel de soporte: {e}")
