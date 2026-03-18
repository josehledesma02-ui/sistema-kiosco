import streamlit as st
from datetime import datetime

def mostrar(db):
    st.subheader("🛠️ Panel de Control de Soporte Técnico")
    
    try:
        # Traemos todos los reportes
        reportes_ref = db.collection("reportes_error").order_by("fecha", direction="DESCENDING").stream()
        
        hay_reportes = False
        for doc in reportes_ref:
            hay_reportes = True
            rep = doc.to_dict()
            id_doc = doc.id
            
            # 1. PROCESAMIENTO DE FECHA (Igual al anterior)
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

            # 2. SEMÁFORO DE PRIORIDAD (Con respaldo si no existe el campo)
            prioridad = rep.get("prioridad", "Baja")
            # Mapeo manual por si el texto no coincide exacto
            if "Urgente" in prioridad: emoji_prio = "🔴"
            elif "Alta" in prioridad: emoji_prio = "🟠"
            elif "Media" in prioridad: emoji_prio = "🟡"
            else: emoji_prio = "🟢"

      # --- DISEÑO DEL EXPANDER ---
            titulo = f"{emoji_prio} {rep.get('id_negocio', 'S/N').upper()} - {rep.get('tipo', 'Reporte')} ({fecha_str})"
            
            with st.expander(titulo):
                st.write(f"**👤 Usuario:** {rep.get('usuario', 'Desconocido')}")
                st.write(f"**🚨 Prioridad:** {prioridad}")
                st.info(f"**💬 Mensaje:** {rep.get('mensaje', 'Sin detalle')}")

                # --- MOSTRAR IMÁGENES (Corregido) ---
                links = rep.get("fotos") or rep.get("links_fotos") or rep.get("urls_fotos")
                
                if links and isinstance(links, list) and len(links) > 0:
                    st.write("🖼️ **Capturas adjuntas:**")
                    # Mostramos las imágenes una debajo de la otra
                    for idx, link in enumerate(links):
                        st.image(link, caption=f"Evidencia {idx+1}", use_container_width=True)
                        st.markdown(f"[🔗 Ver en pantalla completa]({link})")
                else:
                    st.warning("⚠️ El sistema no detectó imágenes en este reporte.")

                st.divider()
                
                # --- BOTONES DE ACCIÓN ---
                # --- BUSCAMOS TODOS LOS REPORTES ---
        hay_reportes = False
        for i, doc in enumerate(reportes_ref): # Agregamos 'i' para que sea un número único
            hay_reportes = True
            rep = doc.to_dict()
            id_doc = doc.id
            
            # ... (todo el código anterior de fecha, prioridad y fotos) ...

            with st.expander(titulo):
                # ... (toda la info del reporte) ...

                st.divider()
                
                # --- BOTONES DE ACCIÓN (CON KEY ÚNICA) ---
                c1, c2 = st.columns(2)
                with c1:
                    # Usamos el ID del doc + el índice del loop para que sea ÚNICO
                    if st.button("✅ Resolver", key=f"res_{id_doc}_{i}", use_container_width=True):
                        db.collection("reportes_error").document(id_doc).update({"estado": "resuelto"})
                        st.success("Resuelto")
                        st.rerun()
                with c2:
                    if st.button("🗑️ Eliminar", key=f"del_{id_doc}_{i}", use_container_width=True):
                        db.collection("reportes_error").document(id_doc).delete()
                        st.warning("Eliminado")
                        st.rerun()

        if not hay_reportes:
            st.info("No hay reportes pendientes.")

    except Exception as e:
        st.error(f"Error en el panel: {e}")
