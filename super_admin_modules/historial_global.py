import streamlit as st
import pandas as pd
from datetime import datetime

def mostrar(db):
    st.markdown("## 📜 Historial Global de Operaciones")
    st.write("Consultá los reportes solucionados y los movimientos administrativos realizados.")

    # Usamos pestañas para que sea más limpio y profesional que un menú desplegable
    tab1, tab2, tab3 = st.tabs(["🛠️ Soporte Solucionado", "🏪 Altas de Negocios", "⚠️ Cambios Críticos"])

    with tab1:
        st.subheader("Reportes Técnicos Finalizados")
        try:
            # Traemos solo los que tienen estado "resuelto"
            resueltos_ref = db.collection("reportes_error")\
                              .where("estado", "==", "resuelto")\
                              .order_by("fecha", direction="DESCENDING").stream()
            
            hay_resueltos = False
            for i, doc in enumerate(resueltos_ref):
                hay_resueltos = True
                r = doc.to_dict()
                
                # Formato de fecha
                f_envio = r.get("fecha", "S/F")[:16].replace("T", " ")
                f_resol = r.get("fecha_resolucion", "S/F")[:16].replace("T", " ")
                
                with st.expander(f"✅ {r.get('id_negocio', 'S/N').upper()} - {r.get('tipo', 'Reporte')}"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**👤 Usuario:** {r.get('usuario')}")
                        st.write(f"**📅 Reportado:** {f_envio}")
                    with col_b:
                        st.write(f"**🚨 Prioridad:** {r.get('prioridad')}")
                        st.write(f"**✨ Solucionado:** {f_resol}")
                    
                    st.info(f"**Mensaje original:** {r.get('mensaje')}")
                    
                    # Si tenía fotos, las mostramos chiquitas por si querés re-chequear
                    if r.get("fotos"):
                        st.write("🖼️ Capturas que fueron enviadas:")
                        cols_fotos = st.columns(min(len(r.get('fotos')), 4))
                        for idx, f in enumerate(r.get('fotos')):
                            with cols_fotos[idx % 4]:
                                st.image(f, use_container_width=True)

            if not hay_resueltos:
                st.info("Todavía no hay reportes en el historial de resueltos.")
        except Exception as e:
            st.error(f"Error al cargar historial de soporte: {e}")
            st.info("💡 Si es un error de Índice, recordá que Firebase tarda unos minutos en habilitarlo.")

    with tab2:
        st.subheader("Registro de Negocios")
        st.write("Lista de los últimos negocios incorporados al sistema.")
        try:
            # Aquí leemos tu colección de negocios (asumiendo que se llama 'negocios')
            negocios_ref = db.collection("negocios").order_by("fecha_creacion", direction="DESCENDING").limit(20).stream()
            
            data_negocios = []
            for n in negocios_ref:
                d = n.to_dict()
                data_negocios.append({
                    "Negocio": d.get("nombre_negocio", "S/N"),
                    "ID": d.get("id_negocio", n.id),
                    "Alta": d.get("fecha_creacion", "S/F")[:10],
                    "Dueño": d.get("usuario_admin", "S/D")
                })
            
            if data_negocios:
                st.table(pd.DataFrame(data_negocios))
            else:
                st.info("No se encontraron registros de negocios.")
        except:
            st.warning("Aún no hay datos de negocios para mostrar o la colección tiene otro nombre.")

    with tab3:
        st.subheader("Bitácora de Cambios Críticos")
        st.write("Próximamente: Aquí verás cuando se realicen cambios manuales en stock o precios desde el Panel Admin.")
        st.empty()
