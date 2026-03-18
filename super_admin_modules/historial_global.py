import streamlit as st
import pandas as pd

def mostrar(db):
    st.subheader("📜 Historial de Operaciones JL Gestión")
    
    categoria = st.selectbox("Seleccionar categoría de historial:", [
        "🛠️ Soporte Solucionado", 
        "🏪 Altas de Negocios", 
        "⚠️ Modificaciones Críticas"
    ])

    if categoria == "🛠️ Soporte Solucionado":
        # Traemos solo los RESUELTOS
        resueltos = db.collection("reportes_error").where("estado", "==", "resuelto").order_by("fecha", direction="DESCENDING").stream()
        
        for doc in resueltos:
            r = doc.to_dict()
            with st.expander(f"✅ {r.get('id_negocio').upper()} - {r.get('tipo')}"):
                st.write(f"**Reportado por:** {r.get('usuario')}")
                st.write(f"**Problema:** {r.get('mensaje')}")
                st.write(f"**📅 Resuelto el:** {r.get('fecha_resolucion', 'S/D')[:16]}")
                if r.get("fotos"):
                    st.write(f"📎 Contenía {len(r.get('fotos'))} capturas.")

    elif categoria == "🏪 Altas de Negocios":
        st.info("Aquí se mostrarán los negocios creados recientemente.")
        # Aquí podés hacer un stream de tu colección 'negocios' o 'usuarios'
        # Ejemplo rápido:
        negocios = db.collection("negocios").order_by("fecha_creacion", direction="DESCENDING").stream()
        for neg in negocios:
            n = neg.to_dict()
            st.text(f"🏪 {n.get('nombre_negocio')} - Creado: {n.get('fecha_creacion')[:10]}")

    elif categoria == "⚠️ Modificaciones Críticas":
        st.warning("Bitácora de cambios manuales en stock o precios (Próximamente)")
        # Aquí podrías leer una colección llamada 'logs_sistema'
