import streamlit as st
import pandas as pd

# Configuración del Excel de Google
ID_HOJA = "1-ay_xIqYItwOaXe80VUsEmh4gsANrk9PH72aZcUD54g"
URL_CSV = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/export?format=csv"

def renderizar(db, id_negocio, ahora_ar, nombre_u):
    st.subheader("🛒 Nueva Venta")

    # 1. Cargar Inventario
    try:
        df = pd.read_csv(URL_CSV)
        # Limpieza básica de columnas
        df.columns = [str(c).strip().lower() for c in df.columns]
        col_prod = next(c for c in df.columns if "producto" in c)
        col_prec = next(c for c in df.columns if "precio" in c)
        df_inv = df[[col_prod, col_prec]].rename(columns={col_prod: "item", col_prec: "precio"})
    except:
        st.error("Error cargando lista de precios.")
        return

    # 2. Buscador y Selección
    busqueda = st.text_input("🔍 Buscar producto...", "").lower()
    filtro = df_inv[df_inv['item'].astype(str).str.contains(busqueda, case=False)] if busqueda else df_inv
    
    col_a, col_b, col_c = st.columns([2, 1, 1])
    with col_a:
        seleccionado = st.selectbox("Producto", filtro['item'].unique())
    with col_b:
        cantidad = st.number_input("Cant.", min_value=0.5, value=1.0, step=0.5)
    
    precio_sug = float(df_inv[df_inv['item'] == seleccionado]['precio'].values[0])
    with col_c:
        precio_v = st.number_input("Precio $", value=precio_sug)

    if st.button("➕ Agregar"):
        st.session_state.carrito.append({
            'nombre': seleccionado, 'cantidad': cantidad, 
            'precio': precio_v, 'subtotal': precio_v * cantidad
        })
        st.toast("Añadido")

    # 3. Carrito y Finalización
    if st.session_state.carrito:
        st.table(pd.DataFrame(st.session_state.carrito))
        total = sum(i['subtotal'] for i in st.session_state.carrito)
        st.write(f"### Total: ${total:,.2f}")
        
        metodo = st.radio("Pago:", ["Efectivo", "Fiado"], horizontal=True)
        
        if st.button("🚀 Confirmar Venta", type="primary"):
            db.collection("ventas_procesadas").add({
                'id_negocio': id_negocio, 'items': st.session_state.carrito,
                'total': total, 'metodo': metodo, 'vendedor': nombre_u,
                'fecha_completa': ahora_ar, 'fecha_str': ahora_ar.strftime("%d/%m/%Y")
            })
            st.session_state.carrito = []
            st.success("Venta realizada")
            st.rerun()
