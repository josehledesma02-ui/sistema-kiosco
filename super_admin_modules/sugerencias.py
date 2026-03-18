import streamlit as st

def mostrar(db):
    st.header("💡 Sugerencias de los Clientes")
    
    # Buscamos en una colección nueva llamada 'sugerencias'
    sugs_ref = db.collection("sugerencias").order_by("fecha", direction="DESCENDING").stream()
    
    for s in sugs_ref:
        data = s.to_dict()
        with st.expander(f"De: {data.get('id_negocio')} - {data.get('titulo')}"):
            st.write(f"**Fecha:** {data.get('fecha')}")
            st.info(data.get('mensaje'))
            
            # Botones de acción para vos
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Marcar como: En Proceso", key=f"pro_{s.id}"):
                    db.collection("sugerencias").document(s.id).update({"estado": "En Proceso"})
            with col2:
                if st.button("Marcar como: Completado", key=f"com_{s.id}"):
                    db.collection("sugerencias").document(s.id).update({"estado": "Completado"})
