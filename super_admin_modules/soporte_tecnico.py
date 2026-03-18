import streamlit as st
from datetime import datetime

def mostrar(db):
    st.subheader("🛠️ Centro de Soporte Técnico")
    
    try:
        # Traemos los reportes ordenados por fecha
        reportes_ref = db.collection("reportes_error").order_by("fecha", direction="DESCENDING").stream()
        
        for doc in reportes_ref:
            rep = doc.to_dict()
            id_doc = doc.id
            
            # --- CORRECCIÓN DE FECHA ---
            fecha = rep.get("fecha")
            if isinstance(fecha, str):
                try:
                    # Si es texto (ISO format), lo convertimos a objeto datetime
                    fecha_obj = datetime.fromisoformat(fecha)
                    fecha_str = fecha_obj.strftime("%d/%m %H:%M")
                except:
                    fecha_str = fecha # Si falla, mostramos el texto tal cual
            elif hasattr(fecha, 'strftime'):
                # Si ya es un objeto de fecha (Timestamp de Firebase)
                fecha_str = fecha.strftime("%d/%m %H:%M")
            else:
                fecha_str = "S/F"
            # ---------------------------

            # Diseño de cada tarjeta de reporte
            with st.expander(f"📌 {rep.get('tipo', 'Reporte')} - {rep.get('id_negocio', 'S/N')} ({fecha_str})"):
                st.write(f"**Usuario:** {rep.get('usuario', 'Desconocido')}")
                st.write(f"**Mensaje:** {rep.get('mensaje', 'Sin detalle')}")
                st.write(f"**Estado:** {rep.get('estado', 'pendiente')}")
                
                c1, c2 = st.columns(2)
                if c1.button("✅ Marcar como Resuelto", key=f"res_{id_doc}"):
                    db.collection("reportes_error").document(id_doc).update({"estado": "resuelto"})
                    st.success("Reporte actualizado.")
                    st.rerun()
                
                if c2.button("🗑️ Eliminar", key=f"del_{id_doc}"):
                    db.collection("reportes_error").document(id_doc).delete()
                    st.warning("Reporte eliminado.")
                    st.rerun()

    except Exception as e:
        st.error(f"Error al cargar los reportes: {e}")
