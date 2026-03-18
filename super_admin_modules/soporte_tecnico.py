import streamlit as st
from datetime import datetime

def mostrar(db):
    st.subheader("🛠️ Centro de Soporte Técnico")
    
    try:
        # Traemos los reportes ordenados por fecha
        # Usamos stream() para obtener los documentos
        reportes_ref = db.collection("reportes_error").order_by("fecha", direction="DESCENDING").stream()
        
        hay_reportes = False
        for doc in reportes_ref:
            hay_reportes = True
            rep = doc.to_dict()
            id_doc = doc.id
            
            # --- CORRECCIÓN DE FECHA BLINDADA ---
            fecha_valor = rep.get("fecha")
            fecha_str = "S/F"
            
            if fecha_valor:
                # Caso 1: Es un objeto Timestamp de Firebase
                if hasattr(fecha_valor, 'strftime'):
                    fecha_str = fecha_valor.strftime("%d/%m %H:%M")
                # Caso 2: Es un texto (String)
                elif isinstance(fecha_valor, str):
                    try:
                        # Intentamos convertir formato ISO
                        fecha_obj = datetime.fromisoformat(fecha_valor.replace('Z', '+00:00'))
                        fecha_str = fecha_obj.strftime("%d/%m %H:%M")
                    except:
                        # Si falla la conversión, mostramos los primeros 16 caracteres del texto
                        fecha_str = str(fecha_valor)[:16]
                else:
                    fecha_str = str(fecha_valor)
            # -----------------------------------

            # Diseño de cada tarjeta de reporte
            with st.expander(f"📌 {rep.get('tipo', 'Reporte')} - {rep.get('id_negocio', 'S/N')} ({fecha_str})"):
                st.write(f"**Usuario:** {rep.get('usuario', 'Desconocido')}")
                st.info(f"**Mensaje:** {rep.get('mensaje', 'Sin detalle')}")
                st.write(f"**Estado:** {rep.get('estado', 'pendiente')}")
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Resolver", key=f"res_{id_doc}", use_container_width=True):
                        db.collection("reportes_error").document(id_doc).update({"estado": "resuelto"})
                        st.success("Actualizado")
                        st.rerun()
                
                with c2:
                    if st.button("🗑️ Eliminar", key=f"del_{id_doc}", use_container_width=True):
                        db.collection("reportes_error").document(id_doc).delete()
                        st.warning("Eliminado")
                        st.rerun()

        if not hay_reportes:
            st.info("No hay reportes registrados por el momento.")

    except Exception as e:
        st.error(f"Error crítico en soporte: {e}")
