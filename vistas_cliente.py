import streamlit as st
import pandas as pd

def mostrar_cliente(db, id_usuario, nombre_real, fecha_pago):
    st.markdown(f"## 🙌 ¡Hola, {nombre_real}!")
    st.write("Bienvenido a tu resumen de cuenta.")

    # 1. Traer datos de Firebase
    # Ventas que fueron "Fiado"
    v_fiado = list(db.collection("ventas_procesadas").where("cliente_id", "==", id_usuario).where("metodo", "==", "Fiado").stream())
    # Pagos que el cliente ya hizo
    p_realizados = list(db.collection("pagos_clientes").where("cliente_id", "==", id_usuario).stream())

    # 2. Calcular Saldo
    total_deuda = sum(v.to_dict().get('total', 0) for v in v_fiado)
    total_pagado = sum(p.to_dict().get('monto', 0) for p in p_realizados)
    saldo_pendiente = total_deuda - total_pagado

    # 3. Mostrar Resumen Gigante
    col1, col2 = st.columns(2)
    with col1:
        st.error(f"### Tu Saldo:\n# ${saldo_pendiente:,.2f}")
    with col2:
        st.info(f"📅 **Próximo Pago:**\n### {fecha_pago}")

    st.divider()

    # 4. Pestañas de Detalles
    tab_historial, tab_tickets = st.tabs(["📜 Mis Movimientos", "📦 Detalle de Compras"])

    with tab_historial:
        st.subheader("Historial de Cuenta")
        movs = []
        for v in v_fiado:
            d = v.to_dict()
            movs.append({"Fecha": d.get('fecha_str'), "Tipo": "Compra 🛒", "Monto": d.get('total', 0)})
        for p in p_realizados:
            d = p.to_dict()
            movs.append({"Fecha": d.get('fecha_str'), "Tipo": "Pago ✅", "Monto": d.get('monto', 0)})
        
        if movs:
            df_movs = pd.DataFrame(movs)
            st.table(df_movs)
        else:
            st.write("No hay movimientos registrados.")

    with tab_tickets:
        st.subheader("Tus Compras Detalladas")
        if not v_fiado:
            st.
