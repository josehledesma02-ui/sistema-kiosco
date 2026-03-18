import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

def renderizar(db, id_negocio, ahora_ar, nombre_u):
    st.header("🛒 Punto de Venta")
    
    url_sheet = "https://docs.google.com/spreadsheets/d/1-ay_xIqYItwOaXe80VUsEmh4gsANrk9PH72aZcUD54g/edit?usp=sharing"
    
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Leemos: Fila 2 como cabecera (skiprows=1) y columnas A y C (0 y 2)
        df_raw = conn.read(spreadsheet=url_sheet, ttl=60, skiprows=1, usecols=[0, 2])
        
        df_p = df_raw.copy()
        df_p.columns = ["PRODUCTOS", "PRECIO"]
        df_p = df_p.dropna(subset=["PRODUCTOS"])

        # --- LIMPIEZA PROFUNDA DE PRECIOS ---
        def limpiar_precio(valor):
            if pd.isna(valor): return 0.0
            s = str(valor).strip()
            # 1. Quitamos el símbolo $ si lo tiene
            s = s.replace('$', '')
            # 2. Quitamos la coma (separador de miles americano)
            s = s.replace(',', '')
            # 3. Ahora que queda "1582.00", lo pasamos a número
            try:
                return float(s)
            except:
                return 0.0

        df_p['PRECIO'] = df_p['PRECIO'].apply(limpiar_precio)
        
    except Exception as e:
        st.error(f"❌ Error al leer Excel: {e}")
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
            # Buscamos el precio convertido
            precio_u = df_p[df_p['PRODUCTOS'] == seleccion]['PRECIO'].values[0]
            
            # Mostramos en pantalla con formato humano (Argentina)
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
            # Mostramos la tabla del carrito
            st.table(df_c[['nombre', 'cantidad', 'subtotal']])
            
            total_final = df_c['subtotal'].sum()
            total_mostrar = f"${total_final:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
            st.markdown(f"## TOTAL: {total_mostrar}")
            
            metodo = st.selectbox("Pago:", ["Efectivo", "Transferencia", "Fiado"])
            cliente = st.text_input("Nombre/DNI Cliente:") if metodo == "Fiado" else "Consumidor Final"

            if st.button("🚀 FINALIZAR VENTA", type="primary", use_container_width=True):
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
                st.success("✅ Venta Guardada")
                st.rerun()
            
            if st.button("🗑️ Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()
        else:
            st.info("Carrito vacío")
