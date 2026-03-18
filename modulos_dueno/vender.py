import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

def renderizar(db, id_negocio, ahora_ar, nombre_u):
    st.header("🛒 Punto de Venta")
    
    url_sheet = "https://docs.google.com/spreadsheets/d/1-ay_xIqYItwOaXe80VUsEmh4gsANrk9PH72aZcUD54g/edit?usp=sharing"
    
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # AJUSTE CLAVE: 
        # skiprows=1 le dice que empiece a leer desde la fila 2.
        # usecols=[0, 2] le dice que solo tome la columna A (0) y la C (2).
        df_raw = conn.read(spreadsheet=url_sheet, ttl=60, skiprows=1, usecols=[0, 2])
        
        # Renombramos para que el código sea fácil de leer
        df_p = df_raw.copy()
        df_p.columns = ["PRODUCTOS", "PRECIO"]
        
        # Limpieza: eliminamos filas vacías y limpiamos precios
        df_p = df_p.dropna(subset=["PRODUCTOS"])
        df_p['PRECIO'] = df_p['PRECIO'].astype(str).replace(r'[\$,\.]', '', regex=True).astype(float)
        
    except Exception as e:
        st.error(f"❌ Error al leer Excel (Fila A2/C2): {e}")
        return

    # --- INTERFAZ DE VENTA ---
    col_izq, col_der = st.columns([1.5, 1])

    if 'carrito' not in st.session_state:
        st.session_state.carrito = []

    with col_izq:
        st.subheader("🔍 Buscador")
        lista_nombres = df_p['PRODUCTOS'].tolist()
        seleccion = st.selectbox("Elegí un producto:", [""] + lista_nombres)
        
        if seleccion:
            precio_u = df_p[df_p['PRODUCTOS'] == seleccion]['PRECIO'].values[0]
            st.markdown(f"### Precio: **${precio_u:,.2f}**")
            
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
            
            total_final = df_c['subtotal'].sum()
            st.markdown(f"## TOTAL: ${total_final:,.2f}")
            
            metodo = st.selectbox("Pago:", ["Efectivo", "Transferencia", "Fiado"])
            cliente = st.text_input("Nombre/DNI Cliente:") if metodo == "Fiado" else "Consumidor Final"

            if st.button("🚀 FINALIZAR", type="primary", use_container_width=True):
                venta_data = {
                    "id_negocio": id_negocio,
                    "vendedor": nombre_u,
                    "total": total_final,
                    "metodo": metodo,
                    "cliente_nombre": cliente,
                    "items": st.session_state.carrito,
                    "fecha_str": ahora_ar.strftime("%d/%m/%Y"),
                    "hora_str": ahora_ar.strftime("%H:%M"),
                    "fecha_completa": ahora_ar.isoformat()
                }
                db.collection("ventas_procesadas").add(venta_data)
                st.session_state.carrito = []
                st.success("Venta Guardada")
                st.rerun()
            
            if st.button("🗑️ Vaciar"):
                st.session_state.carrito = []
                st.rerun()
        else:
            st.info("Carrito vacío")

    st.divider()
    st.caption("Configurado para leer Productos (Col A) y Precios (Col C) desde la fila 2.")
