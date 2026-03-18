import streamlit as st

def mostrar_cliente(db, id_negocio, nombre_cliente):
    # 1. BUSCAR DATOS DEL CLIENTE (Para la fecha de pago)
    cliente_data = None
    try:
        # Buscamos en la colección 'clientes' para traer su ficha personal
        clientes_ref = db.collection("clientes").where("id_negocio", "==", id_negocio).stream()
        for doc in clientes_ref:
            d = doc.to_dict()
            # Comparamos nombres limpiando espacios y mayúsculas
            if str(d.get("nombre", "")).lower().strip() == str(nombre_cliente).lower().strip():
                cliente_data = d
                break
    except Exception as e:
        st.error(f"Error al conectar con la ficha del cliente: {e}")

    # 2. CALCULAR DEUDA TOTAL (Fiado)
    total_deuda = 0
    try:
        # Buscamos en 'ventas_procesadas' lo que debe este cliente
        ventas_ref = db.collection("ventas_procesadas")\
            .where("id_negocio", "==", id_negocio)\
            .where("cliente_nombre", "==", nombre_cliente)\
            .where("metodo", "==", "Fiado").stream()
        
        for v in ventas_ref:
            v_dict = v.to_dict()
            total_deuda += v_dict.get("total", 0)
    except Exception as e:
        st.error(f"Error al calcular la deuda: {e}")

    # --- DISEÑO DE LA PANTALLA ---
    st.markdown(f"# 👋 ¡Hola, {nombre_cliente}!")
    st.subheader("📋 Estado de tu Cuenta Corriente")

    # Tarjetas de información
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Tu Deuda Total", f"${total_deuda:,.2f}")
    
    with col2:
        # Si no hay fecha en la ficha, ponemos N/A
        fecha_pago = cliente_data.get("fecha_pago", "No pactada") if cliente_data else "N/A"
        st.info(f"📅 **Promesa de Pago:** {fecha_pago}")

    # Mensaje de estado
    if total_deuda > 0:
        st.warning(f"⚠️ Tenés un saldo pendiente de ${total_deuda:,.2f}")
        
        # Opcional: Mostrar detalle simple
        with st.expander("Ver por qué tengo esta deuda"):
            st.write("Aquí se listarán tus últimas compras fiadas próximamente.")
    else:
        st.success("✅ ¡Estás al día! No tenés deudas pendientes.")

    # Botón de salir (dentro del área de trabajo)
    if st.button("Cerrar Sesión"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
