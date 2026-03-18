import streamlit as st
from datetime import datetime

def mostrar(db):
    st.subheader("📩 Bandeja de Entrada: Soporte Técnico")
    
    try:
        # Filtramos solo por 'pendiente'
        reportes_ref = db.collection("reportes_error").where("estado", "==", "pendiente").order_by("fecha", direction="DESCENDING").stream()
        
        hay_reportes = False
        for i, doc in enumerate(reportes_ref):
            hay_reportes = True
            rep = doc.to_dict()
            id_doc = doc.id
            
            # --- 1. PROCESAMIENTO DE FECHA (Indispensable) ---
            fecha_valor = rep.get("fecha", "")
            fecha_str = "S/F"
            if fecha_valor:
                try:
                    # Intentamos formatear la fecha para que se vea linda
                    dt = datetime.fromisoformat(fecha_valor.replace('Z', '+00:00'))
                    fecha_str = dt.strftime("%d/%m %H:%M")
                except:
                    fecha_str = str(fecha_valor)[:16]

            # --- 2. SEMÁFORO DE PRIORIDAD ---
            prioridad = rep.get("prioridad", "Baja")
            if "Urgente" in prioridad:
                emoji_prio = "🔴"
            elif "Alta" in prioridad:
                emoji_prio = "🟠"
            elif "Media" in prioridad:
                emoji_prio = "🟡"
            else:
                emoji_prio = "🟢"

            # --- 3. DISEÑO DEL EXPANDER ---
            titulo = f"{emoji_prio} {rep.get('id_negocio', 'S/N').upper()} - {rep.get('tipo', 'Reporte')} ({fecha_str})"

            with st.expander(titulo):
                st.write(f"**👤 Usuario:** {rep.get('usuario', 'Desconocido')}")
                st.write(f"**🚨 Prioridad:** {prioridad}")
                st.info(f"**💬 Mensaje:** {rep.get('mensaje', 'Sin detalle')}")
                
                # Fotos (Buscamos en todos los nombres posibles por las dudas)
                links = rep.get("fotos") or rep.get("links_fotos") or []
                if links:
                    st.write("🖼️ **Capturas adjuntas:**")
                    cols = st.columns(3)
                    for idx, link in enumerate(links):
                        with cols[idx % 3]: 
                            st.image(link, use_container_width=True)
                            st.markdown(f"[🔗 Ver]({link})")

                # --- 🤖 ASISTENTE DE IA PARA SOLUCIÓN ---
                st.divider()
                st.markdown("### 🤖 Consultar a Asistente de IA")
                
                # Caja de chat para que hables conmigo sobre ESTE error específico
                consulta_ia = st.text_input("¿En qué te ayudo con este reporte, José?", 
                                            placeholder="Ej: ¿Cómo arreglo este error de CSS? o ¿Qué pudo fallar aquí?",
                                            key=f"ia_query_{id_doc}")

                if consulta_ia:
                    with st.spinner("Analizando reporte..."):
                        # Aquí es donde yo entro en acción. 
                        # Simulamos la respuesta técnica basada en el reporte
                        st.chat_message("assistant").write(f"**Análisis de JL-IA:** José, analizando el reporte de {rep.get('id_negocio')}, el problema de '{rep.get('tipo')}' suele deberse a un conflicto en la base de datos. Te sugiero revisar el campo 'stock' en Firebase.")
                        st.caption("Nota: Para que esto sea automático, conectaremos tu API Key en el próximo paso.")
                c1, c2 = st.columns(2)
                
                st.divider()
                
                with c1:
                    if st.button("✅ Resolver y Archivar", key=f"res_{id_doc}_{i}", use_container_width=True):
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
        st.error(f"Error: {e}")
