import streamlit as st
from datetime import datetime

def mostrar(db):
    st.subheader("📩 Bandeja de Entrada: Soporte Técnico")
    st.info("")
    
    try:
        # Filtramos solo por 'pendiente'
        reportes_ref = db.collection("reportes_error").where("estado", "==", "pendiente").order_by("fecha", direction="DESCENDING").stream()
        
        hay_reportes = False
        for i, doc in enumerate(reportes_ref):
            hay_reportes = True
            rep = doc.to_dict()
            id_doc = doc.id
            
            # --- DISEÑO PROFESIONAL ---
            # (El código de fecha, prioridad y fotos que ya tenemos funcionando...)
            fecha_valor = rep.get("fecha", "")
            prioridad = rep.get("prioridad", "Baja")
            emoji_prio = "🔴" if "Urgente" in prioridad else "🟢"
            titulo = f"{emoji_prio} {rep.get('id_negocio', '').upper()} - {rep.get('tipo', 'Error')}"

            with st.expander(titulo):
                st.write(f"**⏰ Fecha:** {fecha_valor[:16]}")
                st.info(f"**💬 Mensaje:** {rep.get('mensaje')}")
                
                # Fotos
                links = rep.get("fotos") or []
                if links:
                    cols = st.columns(3)
                    for idx, link in enumerate(links):
                        with cols[idx % 3]: st.image(link, use_container_width=True)

                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Resolver y Archivar", key=f"res_{id_doc}_{i}", use_container_width=True):
                        # Actualizamos estado y agregamos fecha de resolución
                        db.collection("reportes_error").document(id_doc).update({
                            "estado": "resuelto",
                            "fecha_resolucion": datetime.now().isoformat()
                        })
                        st.success("¡Solucionado! Movido al historial.")
                        st.rerun()
                with c2:
                    if st.button("🗑️ Eliminar", key=f"del_{id_doc}_{i}", use_container_width=True):
                        db.collection("reportes_error").document(id_doc).delete()
                        st.rerun()

        if not hay_reportes:
            st.success("🙌 ¡Excelente! No tenés reportes pendientes.")

    except Exception as e:
        # Nota: Si Firebase te pide un índice, aparecerá un link aquí abajo.
        st.error(f"Error: {e}")
