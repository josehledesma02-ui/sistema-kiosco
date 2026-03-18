import streamlit as st
import pandas as pd

def mostrar_cliente(db, id_negocio, nombre_cliente):
    # 1. BUSCAR DATOS DEL CLIENTE (Ficha personal)
    cliente_data = None
    clientes_ref = db.collection("clientes").where("id_negocio", "==", id_negocio).stream()
    for doc in clientes_ref:
        d = doc.to_dict()
        if str(d.get("nombre", "")).lower().strip() == str(nombre_cliente).lower().strip():
            cliente_data = d
            break

    # 2. OBTENER VENTAS FIADAS (Detalle de compras)
    ventas_ref = db.collection("ventas_procesadas")\
        .where("id_negocio", "==", id_negocio)\
        .where("cliente_nombre", "==", nombre_cliente)\
        .where("metodo", "==", "Fiado").stream()
    
    lista_compras = []
    total_deuda = 0
    
    for v in ventas_ref:
        v_dict = v.to_dict()
        total_deuda += v_dict.get("total", 0)
        # Guardamos los productos para el desglose
        productos = v_dict.get("productos", [])
        fecha_venda = v_dict.get("fecha", "S/F")
        for p in productos:
            lista_compras.append({
                "Fecha": fecha_venda,
                "Producto": p.get("nombre"),
                "Cant.": p.get("cantidad"),
                "Precio Unit.": f"${p.get('precio'):,.2f}",
                "Subtotal": p.get("subtotal")
            })

    # --- DISEÑO DE LA PANTALLA ---
    st.markdown(f"# 👋 ¡Hola, {nombre_cliente}!")
    st.write("---")

    # Fila de métricas principales
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Tu Deuda Total", f"${total_deuda:,.2f}")
    with col2:
        fecha_pago = cliente_data.get("fecha_pago", "No pactada") if cliente_data else "N/A"
        st.info(f"📅 **Tu próxima fecha de pago:** {fecha_pago}")

    # 3. LÓGICA DE NOTIFICACIÓN DE SALDO PENDIENTE
    # Solo se muestra si la deuda es mayor a 0 y queremos alertar algo específico
    if total_deuda > 0:
        # Aquí podrías comparar fechas, por ahora lo dejamos como aviso de cortesía
        st.warning("Recordá que podés abonar tu cuenta en el kiosco en cualquier momento.")

    # 4. DETALLE DE COMPRAS (HISTORIAL COMPLETO)
    st.subheader("🛒 Detalle de tus compras pendientes")
    
    if lista_compras:
        df = pd.DataFrame(lista_compras)
        # Formateamos la tabla para que se vea profesional
        st.dataframe(
            df, 
            column_config={
                "Subtotal": st.column_config.NumberColumn(format="$%.2f"),
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.success("🎉 ¡Excelente! No tenés compras pendientes de pago.")

    # Nota: El botón de cerrar sesión se eliminó de aquí porque ya está en el Sidebar.
