import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

def renderizar(db, id_negocio, ahora_ar, nombre_u):
    # Estilo personalizado mejorado
    st.markdown("""
        <style>
            /* Agrandar letra de tablas y textos generales */
            .stTable td, .stTable th { font-size: 18px !important; }
            .big-font { font-size: 20px !important; font-weight: bold; }
            .total-font { font-size: 30px !important; color: #1E88E5; font-weight: bold; }
            
            /* Estilo para la X roja de eliminar (sin recuadro) */
            .btn-eliminar {
                color: #FF1744; /* Rojo brillante */
                font-size: 22px;
                font-weight: bold;
                text-decoration: none; /* Sin subrayado */
                cursor: pointer;
                border: none;
                background: none;
                padding: 0;
                margin-left: 10px;
            }
            .btn-eliminar:hover {
                color: #B71C1C; /* Rojo más oscuro al pasar el mouse */
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
        st.error(f"❌ Error al leer Excel: {e}")
        return

    col_izq, col_der = st.columns([1.3, 1])

    if 'carrito' not in st.session_state:
        st.session_state.carrito = []

    # Manejo de eliminación (fuera del bucle de renderizado para evitar errores)
    if 'eliminar_indice' in st.session_state and st.session_state.eliminar_indice is not None:
        idx_a_borrar = st.session_state.eliminar_indice
        if 0 <= idx_a_borrar < len(st.session_state.carrito):
            st.session_state.carrito.pop(idx_a_borrar)
        st.session_state.eliminar_indice = None # Limpiar orden de eliminación
        st.rerun()

    with col_izq:
        st.subheader("🔍 Buscador")
        lista_nombres = df_p['PRODUCTOS'].tolist()
        seleccion = st.selectbox("Elegí un producto:", [""] + lista_nombres)
        
        if seleccion:
            precio_u = df_p[df_p['PRODUCTOS'] == seleccion]['PRECIO'].values[0]
            precio_f = f"${precio_u:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
            st.markdown(f"<p class='big-font'>Precio Unitario: {precio_f}</p>", unsafe_allow_html=True)
            
            cant = st.number_input("Cantidad:", min_value=1, value=1, step=1)
            
            if st.button("➕ Agregar al Carrito", use_container_width=True):
                st.session_state.carrito.append({
                    "nombre": seleccion,
                    "cantidad": cant,
                    "precio": precio_u,
                    "subtotal": precio_u * cant
                })
                st.rerun()
        
        st.divider()
        st.subheader("📋 Detalle de la compra")
        if st.session_state.carrito:
            # Mostramos cada ítem con opciones de edición y eliminación limpia
            for i, item in enumerate(st.session_state.carrito):
                # Reajustamos columnas para dar espacio a la X
                c1, c2, c3, c4 = st.columns([3, 1, 1.5, 0.3]) 
                with c1:
                    st.markdown(f"**{item['nombre']}**")
                with c2:
                    nueva_cant = st.number_input(f"Cant.", min_value=1, value=item['cantidad'], key=f"cant_{i}")
                    if nueva_cant != item['cantidad']:
                        st.session_state.carrito[i]['cantidad'] = nueva_cant
                        st.session_state.carrito[i]['subtotal'] = item['precio'] * nueva_cant
                        st.rerun()
                with c3:
                    sub_f = f"${item['subtotal']:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
                    st.markdown(f"<p style='text-align:right; font-size:18px;'>{sub_f}</p>", unsafe_allow_html=True)
                with c4:
                    # USAMOS UN BOTÓN INVISIBLE CON HTML PARA LA X ROJA LIMPIA
                    # Al hacer clic, guardamos el índice en session_state para borrarlo arriba
                    if st.button("X", key=f"del_btn_{i}", help="Eliminar producto"):
                         st.session_state.eliminar_indice = i
                         st.rerun()
                         
                    # Aplicamos estilo CSS a la X del botón generado por Streamlit (hack visual)
                    st.markdown(f"""
                        <style>
                            div[data-testid="stButton"] > button[key="del_btn_{i}"] {{
                                background: none !important;
                                border: none !important;
                                color: #FF1744 !important; /* Rojo */
                                font-size: 22px !important;
                                font-weight: bold !important;
                                padding: 0 !important;
                                margin: 0 !important;
                                box-shadow: none !important;
                            }}
                            div[data-testid="stButton"] > button[key="del_btn_{i}"]:hover {{
                                color: #B71C1C !important; /* Rojo oscuro */
                                background: none !important;
                            }}
                        </style>
                    """, unsafe_allow_html=True)
            
            st.divider()
            if st.button("🗑️ Vaciar Carrito Completo", use_container_width=True):
                st.session_state.carrito = []
                st.rerun()
        else:
            st.info("No hay productos en el ticket.")

    with col_der:
        st.subheader("💰 Resumen y Pago")
        if st.session_state.carrito:
            suma_productos = sum(item['subtotal'] for item in st.session_state.carrito)
            
            c_desc, c_rec = st.columns(2)
            with c_desc:
                porcentaje_desc = st.number_input("Descuento %", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
            with c_rec:
                porcentaje_rec = st.number_input("Recargo %", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
            
            monto_descuento = (suma_productos * (porcentaje_desc / 100))
            monto_recargo = (suma_productos * (porcentaje_rec / 100))
            total_final = suma_productos - monto_descuento + monto_recargo
            
            if monto_descuento > 0: st.write(f"📉 Descuento: -${monto_descuento:,.2f}")
            if monto_recargo > 0: st.write(f"📈 Recargo: +${monto_recargo:,.2f}")

            total_f = f"${total_final:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
            st.markdown(f"<p class='total-font'>TOTAL: {total_f}</p>", unsafe_allow_html=True)
            
            metodo = st.selectbox("Medio de Pago:", ["Efectivo", "Débito", "Crédito", "Transferencia", "Fiado"])
            
            detalles_pago = ""
            if metodo == "Transferencia":
                detalles_pago = st.text_input("Cuenta destino:", placeholder="Ej: Mercado Pago")
            
            cliente = "Consumidor Final"
            if metodo == "Fiado":
                cliente = st.text_input("Nombre Cliente:")

            if st.button("✅ CONFIRMAR VENTA", type="primary", use_container_width=True):
                if metodo == "Fiado" and not cliente:
                    st.warning("⚠️ El nombre es obligatorio para fiar.")
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
                    st.success("¡Venta guardada!")
                    st.balloons()
                    st.rerun()
        else:
            st.write("Esperando productos...")
