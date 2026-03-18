import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

def renderizar(db, id_negocio, ahora_ar, nombre_u):
    st.header("🛒 Punto de Venta")
    
    url_sheet = "https://docs.google.com/spreadsheets/d/1-ay_xIqYItwOaXe80VUsEmh4gsANrk9PH72aZcUD54g/edit?usp=sharing"
    
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_raw = conn.read(spreadsheet=url_sheet, ttl=60, skiprows=1, usecols=[0, 2])
        
        df_p = df_raw.copy()
        df_p.columns = ["PRODUCTOS", "PRECIO"]
        df_p = df_p.dropna(subset=["PRODUCTOS"])

        def limpiar_precio(valor):
            if pd.isna(valor): return 0.0
            s = str(valor).strip().replace('$', '').replace(',', '')
            try: return float(s)
            except: return 0.0

        df_p['PRECIO'] = df_p['PRECIO'].apply(limpiar_precio)
        
    except Exception as e:
        st.error(f"❌ Error al leer Excel: {e}")
        return

    # --- DISEÑO DE COLUMNAS ---
    col_izq, col_der = st.columns([1.3, 1])

    if 'carrito' not in st.session_state:
        st.session_state.carrito = []

    with col_izq:
        st.subheader("🔍 Buscador")
        lista_nombres = df_p['PRODUCTOS'].tolist()
        seleccion = st.selectbox("Elegí un producto:", [""] + lista_nombres)
        
        if seleccion:
            precio_u = df_p[df_p['PRODUCTOS'] == seleccion]['PRECIO'].values[0]
            precio_mostrar = f"${precio_u:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
            st.markdown(f"### Precio: **{precio_mostrar}**")
            
            cant = st.number_input("Cantidad:", min_value=1, value=1, step=1)
            
            if st.button("➕ Agregar al Carrito", use_container_width=True):
                st.session_state.carrito.append({
                    "nombre": seleccion,
                    "cantidad": cant,
                    "precio": precio_u,
                    "subtotal": precio_u * cant
                })
                st.rerun()
        
        # --- TABLA DEL CARRITO (MOVIDA AQUÍ ABAJO) ---
        st.divider()
        st.subheader("📋 Detalle de la compra")
        if st.session_state.carrito:
            df_c = pd.DataFrame(st.session_state.carrito)
            st.dataframe(df_c[['nombre', 'cantidad', 'subtotal']], use_container_width=True, hide_index=True)
            if st.button("🗑️ Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()
        else:
            st.info("No hay productos en el ticket.")

    with col_der:
        st.subheader("💰 Finalizar Venta")
        if st.session_state.carrito:
            df_c = pd.DataFrame(st.session_state.carrito)
            suma_productos = df_c['subtotal'].sum()
            
            # --- SECCIÓN DE DESCUENTOS / RECARGOS (LIMPIA) ---
            c_desc, c_rec = st.columns(2)
            with c_desc:
                porcentaje_desc = st.number_input("Descuento %", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
            with c_rec:
                porcentaje_rec = st.number_input("Recargo %", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
            
            # Cálculos
            monto_descuento = (suma_productos * (porcentaje_desc / 100))
            monto_recargo = (suma_productos * (porcentaje_rec / 100))
            
            total_final = suma_productos - monto_descuento + monto_recargo
            
            # Mostrar avisos de ajustes si existen
            if monto_descuento > 0:
                st.write(f"📉 Descuento aplicado: -${monto_descuento:,.2f}")
            if monto_recargo > 0:
                st.write(f"📈 Recargo aplicado: +${monto_recargo:,.2f}")

            total_mostrar = f"${total_final:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
            st.markdown(f"## TOTAL: {total_mostrar}")
            
            # --- MEDIOS DE PAGO ---
            metodo = st.selectbox("Medio de Pago:", ["Efectivo", "Débito", "Crédito", "Transferencia", "Fiado"])
            
            detalles_pago = ""
            if metodo == "Transferencia":
                detalles_pago = st.text_input("¿A qué cuenta transfirieron?", placeholder="Ej: MP Jose, Galicia, etc.")
            
            cliente = "Consumidor Final"
            if metodo == "Fiado":
                cliente = st.text_input("Nombre/DNI del Cliente (Obligatorio):")

            if st.button("🚀 CONFIRMAR VENTA", type="primary", use_container_width=True):
                if metodo == "Fiado" and not cliente:
                    st.warning("⚠️ Debes ingresar el nombre del cliente para fiar.")
                else:
                    venta_data = {
                        "id_negocio": id_negocio,
                        "vendedor": nombre_u,
                        "subtotal_base": suma_productos,
                        "descuento_p": porcentaje_desc,
                        "recargo_p": porcentaje_rec,
                        "total": total_final,
                        "metodo": metodo,
                        "detalles_pago": detalles_pago,
                        "cliente_nombre": cliente,
                        "items": st.session_state.carrito,
                        "fecha_str": ahora_ar.strftime("%d/%m/%Y"),
                        "hora_str": ahora_ar.strftime("%H:%M"),
                        "fecha_completa": ahora_ar.isoformat()
                    }
                    db.collection("ventas_procesadas").add(venta_data)
                    st.session_state.carrito = []
                    st.success("✅ ¡Venta guardada!")
                    st.balloons()
                    st.rerun()
        else:
            st.write("Esperando productos...")

    st.divider()
    st.caption(f"Vendedor: {nombre_u} | ID: {id_negocio}")
