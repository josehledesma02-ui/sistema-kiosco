import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import time

def renderizar(db, id_negocio, ahora_ar, nombre_u):
    # Estilos visuales
    st.markdown("""
        <style>
            .stButton > button {
                border: none !important;
                background: transparent !important;
                color: #FF4B4B !important;
                font-size: 22px !important;
                font-weight: bold !important;
            }
            .precio-grande {
                font-size: 19px;
                font-weight: bold;
                text-align: right;
                color: #2E7D32;
            }
        </style>
    """, unsafe_allow_html=True)

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
        st.error(f"❌ Error al conectar con Excel: {e}")
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
            precio_f = f"${precio_u:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
            st.markdown(f"**Precio Unitario: {precio_f}**")
            
            cant = st.number_input("Cantidad:", min_value=1, value=1, step=1)
            
            if st.button("➕ Agregar al Carrito", use_container_width=True):
                # Generamos un ID único usando el tiempo actual
                nuevo_id = str(time.time()).replace(".", "")
                st.session_state.carrito.append({
                    "id": nuevo_id,
                    "nombre": seleccion,
                    "cantidad": cant,
                    "precio": precio_u,
                    "subtotal": precio_u * cant
                })
                st.rerun()
        
        st.divider()
        st.subheader("📋 Detalle de la compra")
        
        if st.session_state.carrito:
            # Usamos una lista para marcar qué borrar y evitar errores de índice
            indice_a_borrar = None
            
            for i, item in enumerate(st.session_state.carrito):
                # SEGURIDAD: Si por error un item viejo no tiene ID, se lo creamos ahora
                if "id" not in item:
                    item["id"] = f"old_{i}"

                c1, c2, c3, c4 = st.columns([3, 1, 1.5, 0.4])
                with c1:
                    st.write(f"**{item['nombre']}**")
                with c2:
                    nueva_q = st.number_input("Cant.", min_value=1, value=item['cantidad'], key=f"q_{item['id']}")
                    if nueva_q != item['cantidad']:
                        st.session_state.carrito[i]['cantidad'] = nueva_q
                        st.session_state.carrito[i]['subtotal'] = item['precio'] * nueva_q
                        st.rerun()
                with c3:
                    sub_f = f"${item['subtotal']:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
                    st.markdown(f"<p class='precio-grande'>{sub_f}</p>", unsafe_allow_html=True)
                with c4:
                    if st.button("🗑️", key=f"del_{item['id']}"):
                        indice_a_borrar = i
            
            if indice_a_borrar is not None:
                st.session_state.carrito.pop(indice_a_borrar)
                st.rerun()

            if st.button("❌ Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()
        else:
            st.info("Ticket vacío")

    with col_der:
        st.subheader("💰 Resumen y Pago")
        if st.session_state.carrito:
            suma_base = sum(item['subtotal'] for item in st.session_state.carrito)
            
            c1, c2 = st.columns(2)
            with c1: p_desc = st.number_input("Desc %", min_value=0.0, value=0.0)
            with c2: p_rec = st.number_input("Rec %", min_value=0.0, value=0.0)
            
            total = suma_base * (1 - p_desc/100 + p_rec/100)
            total_f = f"${total:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
            st.markdown(f"## TOTAL: {total_f}")
            
            metodo = st.selectbox("Pago:", ["Efectivo", "Débito", "Crédito", "Transferencia", "Fiado"])
            detalles = st.text_input("Cuenta:") if metodo == "Transferencia" else ""
            cliente = st.text_input("Nombre Cliente:") if metodo == "Fiado" else "Consumidor Final"

            if st.button("✅ CONFIRMAR VENTA", type="primary", use_container_width=True):
                venta = {
                    "vendedor": nombre_u,
                    "total": total,
                    "metodo": metodo,
                    "detalles_pago": detalles,
                    "cliente": cliente,
                    "items": st.session_state.carrito,
                    "fecha": ahora_ar.isoformat()
                }
                db.collection("ventas_procesadas").add(venta)
                st.session_state.carrito = []
                st.success("¡Venta guardada!")
                st.rerun()
