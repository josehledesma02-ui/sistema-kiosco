import streamlit as st
import pandas as pd

def renderizar(db, id_negocio, ahora_ar, nombre_u):
    st.header("🛒 Punto de Venta")
    
    # Cargar Productos
    prod_ref = db.collection("productos").where("id_negocio", "==", id_negocio).stream()
    prods = [p.to_dict() for p in prod_ref]
    
    if not prods:
        st.warning("No hay productos cargados en la base de datos.")
        return

    df_p = pd.DataFrame(prods)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        seleccion = st.selectbox("Seleccionar Producto", df_p['nombre'].tolist())
        cant = st.number_input("Cantidad", min_value=1, value=1)
        if st.button("➕ Agregar al Carrito"):
            # Lógica simple de carrito en session_state
            st.success(f"Agregado: {seleccion} x{cant}")

    with col2:
        st.write("### Total: $0.00")
        metodo = st.radio("Método de Pago", ["Efectivo", "Transferencia", "Fiado"])
        if st.button("✅ Finalizar Venta"):
            st.balloons()
