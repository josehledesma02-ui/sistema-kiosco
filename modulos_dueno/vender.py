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

    with col_der:
        st.subheader("🧾 Ticket")
        if st.session_state.carrito:
            df_c = pd.DataFrame(st.session_state.carrito)
            st.table(df_c[['nombre', 'cantidad', 'subtotal']])
            
            suma_productos = df_c['subtotal'].sum()
            
            st.divider()
            # --- SECCIÓN DE DESCUENTOS / RECARGOS ---
            st.write("### Ajustes")
            tipo_ajuste = st.radio("Aplicar:", ["Ninguno", "Descuento (%)", "Recargo (%)"], horizontal=True)
            porcentaje = 0.0
            if tipo_ajuste != "Ninguno":
                porcentaje = st.number_input(f"Porcentaje de {tipo_ajuste.lower()}:", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
            
            # Cálculo del ajuste
            monto_ajuste = (suma_productos * (porcentaje / 100))
            if tipo_ajuste == "Descuento (%)":
                total_final = suma_productos - monto_ajuste
                st.write(f"📉 Descuento aplicado: -${monto_ajuste:,.2f}")
            elif tipo_ajuste == "Recargo (%)":
                total_final = suma_productos + monto_ajuste
                st.write(f"📈 Recargo aplicado: +${monto_ajuste:,.2f}")
            else:
                total_final = suma_productos

            total_mostrar = f"${total_final:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
            st.markdown(f"## TOTAL: {total_mostrar}")
            
            # --- MEDIOS DE PAGO ACTUALIZADOS ---
            metodo = st.selectbox("Medio de Pago:", ["Efectivo", "Débito", "Crédito", "Transferencia", "Fiado"])
            
            detalles_pago = ""
            if metodo == "Transferencia":
                detalles_pago = st.text_input("Nombre de la cuenta / Banco destino:", placeholder="Ej: Mercado Pago - Mi Kiosco")
            
            cliente = "Consumidor Final"
            if metodo == "Fiado":
                cliente = st.text_input("Nombre/DNI del Cliente:", placeholder="Ej: Juan Perez")

            if st.button("🚀 FINALIZAR VENTA", type="primary", use_container_width=True):
                if metodo == "Fiado" and not cliente:
                    st.warning("⚠️ El nombre del cliente es obligatorio para ventas al fiado.")
                else:
                    venta_data = {
                        "id_negocio": id_negocio,
                        "vendedor": nombre_u,
                        "subtotal_base": suma_productos,
                        "ajuste_tipo": tipo_ajuste,
                        "ajuste_porcentaje": porcentaje,
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
                    st.success("✅ Venta Guardada")
                    st.balloons()
                    st.rerun()
            
            if st.button("🗑️ Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()
        else:
            st.info("Carrito vacío")
