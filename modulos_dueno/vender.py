import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import time

def renderizar(db, id_negocio, ahora_ar, nombre_u):
    # --- MANTENEMOS LOS ESTILOS EXACTAMENTE IGUAL ---
    st.markdown("""
        <style>
            .sub-blue {
                background: linear-gradient(90deg, #1E88E5 0%, #64B5F6 100%);
                color: white;
                padding: 10px;
                border-radius: 8px;
                font-size: 20px;
                margin-top: 15px;
                margin-bottom: 10px;
            }
            .big-font { font-size: 20px !important; font-weight: bold; }
            .total-font {
                font-size: 30px !important;
                color: #1E88E5;
                font-weight: bold;
                margin-top: 10px;
            }
            .stButton > button[key^="del_"] {
                border: none !important;
                background: transparent !important;
                color: #FF1744 !important;
                font-size: 22px !important;
                font-weight: bold !important;
                padding: 0 !important;
            }
            .stButton > button[key="vaciar_todo"] {
                background-color: #fce4ec !important;
                color: #c62828 !important;
                border: 1px solid #c62828 !important;
                margin-top: 10px;
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

    # --- CARGAR LISTA DE CLIENTES DESDE FIREBASE ---
    # Por defecto siempre está "Consumidor Final" primero
    lista_clientes = ["Consumidor Final"]
    try:
        docs_clientes = db.collection("clientes").where("id_negocio", "==", id_negocio).stream()
        for d in docs_clientes:
            info = d.to_dict()
            nombre_cli = info.get("nombre", "")
            if nombre_cli and nombre_cli not in lista_clientes:
                lista_clientes.append(nombre_cli)
    except:
        pass # Si falla o no hay clientes, queda solo "Consumidor Final"

    col_izq, col_der = st.columns([1.3, 1])

    if 'carrito' not in st.session_state:
        st.session_state.carrito = []

    if 'id_a_eliminar' in st.session_state and st.session_state.id_a_eliminar is not None:
        id_borrar = st.session_state.id_a_eliminar
        st.session_state.carrito = [item for item in st.session_state.carrito if item['id'] != id_borrar]
        st.session_state.id_a_eliminar = None
        st.rerun()

    with col_izq:
        st.markdown('<div class="sub-blue">🔍 Buscador</div>', unsafe_allow_html=True)
        lista_nombres = df_p['PRODUCTOS'].tolist()
        seleccion = st.selectbox("Elegí un producto:", [""] + lista_nombres)
        
        if seleccion:
            precio_u = df_p[df_p['PRODUCTOS'] == seleccion]['PRECIO'].values[0]
            precio_f = f"${precio_u:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
            st.markdown(f"<p class='big-font'>Precio Unitario: {precio_f}</p>", unsafe_allow_html=True)
            cant = st.number_input("Cantidad:", min_value=1, value=1, step=1)
            
            if st.button("➕ Agregar al Carrito", use_container_width=True):
                nuevo_id = str(time.time()).replace(".", "")
                st.session_state.carrito.append({
                    "id": nuevo_id, "nombre": seleccion, "cantidad": cant, "precio": precio_u, "subtotal": precio_u * cant
                })
                st.rerun()
        
        st.divider()
        st.markdown('<div class="sub-blue">📋 Detalle de la compra</div>', unsafe_allow_html=True)
        
        if st.session_state.carrito:
            for i, item in enumerate(st.session_state.carrito):
                if "id" not in item: item["id"] = f"old_{i}"
                c1, c2, c3, c4 = st.columns([3, 1, 1.5, 0.4]) 
                with c1: st.write(f"**{item['nombre']}**")
                with c2:
                    nueva_q = st.number_input("Cant.", min_value=1, value=item['cantidad'], key=f"q_{item['id']}")
                    if nueva_q != item['cantidad']:
                        st.session_state.carrito[i]['cantidad'] = nueva_q
                        st.session_state.carrito[i]['subtotal'] = item['precio'] * nueva_q
                        st.rerun()
                with c3:
                    sub_f = f"${item['subtotal']:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
                    st.markdown(f"<p style='text-align:right; font-size:18px;'>{sub_f}</p>", unsafe_allow_html=True)
                with c4:
                    if st.button("🗑️", key=f"del_{item['id']}"):
                        st.session_state.id_a_eliminar = item['id']
                        st.rerun()
            
            c1, c2 = st.columns([3, 1])
            with c2:
                if st.button("❌ Vaciar", key="vaciar_todo"):
                    st.session_state.carrito = []
                    st.rerun()
        else:
            st.info("No hay productos cargados en el ticket actual.")

    with col_der:
        st.markdown('<div class="sub-blue">💰 Resumen y Pago</div>', unsafe_allow_html=True)
        if st.session_state.carrito:
            suma_base = sum(item['subtotal'] for item in st.session_state.carrito)
            
            # --- LISTA DESPLEGABLE DE CLIENTES (NUEVA UBICACIÓN) ---
            cliente_seleccionado = st.selectbox("👤 Seleccionar Cliente:", lista_clientes, index=0)
            
            c1, c2 = st.columns(2)
            with c1: p_desc = st.number_input("Descuento %", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
            with c2: p_rec = st.number_input("Recargo %", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
            
            total_final = suma_base * (1 - p_desc/100 + p_rec/100)
            total_f = f"${total_final:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
            st.markdown(f"<p class='total-font'>TOTAL: {total_f}</p>", unsafe_allow_html=True)
            
            st.divider()
            metodo = st.selectbox("Medio de Pago:", ["Efectivo", "Débito", "Crédito", "Transferencia", "Fiado"])
            
            detalles_pago = ""
            if metodo == "Transferencia":
                detalles_pago = st.text_input("Cuenta / Detalles:")

            if st.button("🚀 CONFIRMAR VENTA", type="primary", use_container_width=True):
                # Validación para Fiado: no puede ser Consumidor Final
                if metodo == "Fiado" and cliente_seleccionado == "Consumidor Final":
                    st.warning("⚠️ Para ventas al FIADO debes seleccionar un cliente de la lista.")
                else:
                    venta_data = {
                        "id_negocio": id_negocio,
                        "vendedor": nombre_u,
                        "suma_base": suma_base,
                        "total": total_final,
                        "metodo": metodo,
                        "detalles_pago": detalles_pago,
                        "cliente_nombre": cliente_seleccionado,
                        "items": st.session_state.carrito,
                        "fecha": ahora_ar.isoformat()
                    }
                    db.collection("ventas_procesadas").add(venta_data)
                    st.session_state.carrito = []
                    st.success(f"✅ Venta registrada a: {cliente_seleccionado}")
                    st.balloons()
                    st.rerun()
        else:
            st.warning("Esperando productos... Agrega artículos desde el buscador.")
