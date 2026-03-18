import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

def renderizar(db, id_negocio, ahora_ar, nombre_u):
    st.header("🛒 Punto de Venta")
    st.caption(f"Lista de precios vinculada: {id_negocio}")

    # 1. CONEXIÓN A TU GOOGLE SHEET REAL
    url_sheet = "https://docs.google.com/spreadsheets/d/1-ay_xIqYItwOaXe80VUsEmh4gsANrk9PH72aZcUD54g/edit?usp=sharing"
    
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Leemos la hoja (usamos ttl=60 para que se actualice cada minuto si cambias el Excel)
        df_raw = conn.read(spreadsheet=url_sheet, ttl=60)
        
        # Limpieza de columnas (Tu Excel tiene: "PRODUCTOS" y "PRECIO")
        df_p = df_raw.copy()
        df_p.columns = [c.strip().upper() for c in df_p.columns]
        
        if "PRODUCTOS" not in df_p.columns or "PRECIO" not in df_p.columns:
            st.error("⚠️ La hoja de Excel debe tener las columnas: PRODUCTOS y PRECIO")
            return

        # Limpiamos los precios (Quitamos $, puntos y espacios)
        df_p['PRECIO'] = df_p['PRECIO'].replace(r'[\$,\.]', '', regex=True).astype(float)
        
    except Exception as e:
        st.error(f"❌ Error al conectar con Google Sheets: {e}")
        return

    # 2. INTERFAZ DE VENTA
    col_izq, col_der = st.columns([1.5, 1])

    if 'carrito' not in st.session_state:
        st.session_state.carrito = []

    with col_izq:
        st.subheader("🔍 Buscar Producto")
        lista_nombres = df_p['PRODUCTOS'].dropna().tolist()
        
        # Buscador con autocompletado
        seleccion = st.selectbox("Escribí el nombre del producto:", [""] + lista_nombres)
        
        if seleccion:
            # Buscamos el precio del elegido
            precio_u = df_p[df_p['PRODUCTOS'] == seleccion]['PRECIO'].values[0]
            st.markdown(f"### Precio: **${precio_u:,.2f}**")
            
            cant = st.number_input("Cantidad:", min_value=1, value=1, step=1)
            subtotal = precio_u * cant
            
            if st.button("➕ Agregar al Carrito", use_container_width=True):
                st.session_state.carrito.append({
                    "nombre": seleccion,
                    "cantidad": cant,
                    "precio": precio_u,
                    "subtotal": subtotal
                })
                st.rerun()

    with col_der:
        st.subheader("🧾 Detalle de Venta")
        if st.session_state.carrito:
            df_c = pd.DataFrame(st.session_state.carrito)
            st.table(df_c[['nombre', 'cantidad', 'subtotal']])
            
            total_final = df_c['subtotal'].sum()
            st.markdown(f"## TOTAL: ${total_final:,.2f}")
            
            metodo = st.selectbox("Método de Pago:", ["Efectivo", "Transferencia", "Fiado"])
            
            cliente = "Consumidor Final"
            if metodo == "Fiado":
                cliente = st.text_input("Nombre del Cliente (DNI):", placeholder="Ej: Juan Perez")

            if st.button("🚀 FINALIZAR VENTA", type="primary", use_container_width=True):
                if metodo == "Fiado" and not cliente:
                    st.warning("⚠️ Para ventas al fiado, debés poner un nombre.")
                else:
                    # GUARDAR EN FIREBASE (Para tus estadísticas)
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
                    st.success("✅ ¡Venta registrada con éxito!")
                    st.balloons()
                    st.rerun()
            
            if st.button("🗑️ Vaciar"):
                st.session_state.carrito = []
                st.rerun()
        else:
            st.info("El carrito está vacío.")

    st.divider()
    st.caption("💡 Si cambias un precio en el Excel, la App lo tomará en 60 segundos.")
