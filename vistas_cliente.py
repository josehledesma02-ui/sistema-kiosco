import streamlit as st
import pandas as pd

def mostrar_cliente(db, id_cliente, nombre_c, promesa):
    st.title(f"👋 ¡Hola, {nombre_c}!")
    st.subheader("📋 Estado de tu Cuenta Corriente")

    # Buscamos todas las ventas "Fiado" de este cliente
    ventas_ref = db.collection("ventas_procesadas").where("cliente_id", "==", id_cliente).stream()
    
    lista_deudas = []
    total_deuda = 0
    
    for v in ventas_ref:
        d = v.to_dict()
        if d.get("metodo") == "Fiado":
            lista_deudas.append({
                "Fecha": d.get("fecha_str"),
                "Monto": d.get("total")
            })
            total_deuda += d.get("total")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Tu Deuda Total", f"${total_deuda:,.2f}")
    with col2:
        st.info(f"📅 **Promesa de Pago:** {promesa}")

    st.divider()

    if lista_deudas:
        st.write("### 📜 Detalle de tus compras")
        st.table(pd.DataFrame(lista_deudas))
    else:
        st.success("✅ ¡Estás al día!")

    if st.button("🚪 Cerrar Sesión"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
