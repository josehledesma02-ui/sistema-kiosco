import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import time

def renderizar(db, id_negocio, ahora_ar, nombre_u):
    # --- RECUPERAMOS LOS ESTILOS VISUALES LINDOS ---
    st.markdown("""
        <style>
            /* Subtítulos con degradado azul */
            .sub-blue {
                background: linear-gradient(90deg, #1E88E5 0%, #64B5F6 100%);
                color: white;
                padding: 10px;
                border-radius: 8px;
                font-size: 20px;
                margin-top: 15px;
                margin-bottom: 10px;
            }
            
            /* Fuente grande para el buscador */
            .big-font {
                font-size: 20px !important;
                font-weight: bold;
            }
            
            /* TOTAL en azul grande y llamativo */
            .total-font {
                font-size: 30px !important;
                color: #1E88E5;
                font-weight: bold;
                margin-top: 10px;
            }
            
            /* Estilo para la papelera de eliminar (Emoji centrado) */
            .stButton > button[key^="del_"] {
                border: none !important;
                background: transparent !important;
                color: #FF1744 !important; /* Rojo */
                font-size: 22px !important;
                font-weight: bold !important;
                padding: 0 !important;
            }
            
            /* Estilo para el botón de Vaciar Carrito (Chico, a la derecha) */
            .stButton > button[key="vaciar_todo"] {
                background-color: #fce4ec !important; /* Rosa pálido */
                color: #c62828 !important; /* Rojo oscuro */
                border: 1px solid #c62828 !important;
                margin-top: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

    st.header("🛒 Punto de Venta")
    
    # URL de tu hoja de Google Sheets
    url_sheet = "https://docs.google.com/spreadsheets/d/1-ay_xIqYItwOaXe80VUsEmh4gsANrk9PH72aZcUD54g/edit?usp=sharing"
    
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Leemos desde la fila 2 (skiprows=1) y columnas A y C (0 y 2)
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
        st.error(f"❌ Error al conectar con la lista de precios (Excel): {e}")
        return

    # --- DISEÑO DE COLUMNAS ---
    col_izq, col_der = st.columns([1.3, 1])

    # Inicializar carrito en la sesión
    if 'carrito' not in st.session_state:
        st.session_state.carrito = []

    # Manejo de eliminación (fuera del bucle principal para evitar errores de índice)
    if 'id_a_eliminar' in st.session_state and st.session_state.id_a_eliminar is not None:
        id_borrar = st.session_state.id_a_eliminar
        # Filtramos el carrito dejando todos los que NO tengan ese ID
        st.session_state.carrito = [item for item in st.session_state.carrito if item['id'] != id_borrar]
        # Limpiamos la orden de eliminación
        st.session_state.id_a_eliminar = None
        st.rerun()

    # --- COLUMNA IZQUIERDA (BUSCADOR Y TICKET) ---
    with col_izq:
        # Recuperamos el subtítulo lindo
        st.markdown('<div class="sub-blue">🔍 Buscador</div>', unsafe_allow_html=True)
        lista_nombres = df_p['PRODUCTOS'].tolist()
        seleccion = st.selectbox("Elegí un producto:", [""] + lista_nombres)
        
        if seleccion:
            precio_u = df_p[df_p['PRODUCTOS'] == seleccion]['PRECIO'].values[0]
            # Formato local: $1.582,00
            precio_f = f"${precio_u:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
            st.markdown(f"<p class='big-font'>Precio Unitario: {precio_f}</p>", unsafe_allow_html=True)
            
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
        st.markdown('<div class="sub-blue">📋 Detalle de la compra</div>', unsafe_allow_html=True)
        
        if st.session_state.carrito:
            # Hacemos una copia para iterar
            for i, item in enumerate(st.session_state.carrito):
                # SEGURIDAD: Si por error un item viejo no tiene ID, se lo creamos ahora
                if "id" not in item:
                    item["id"] = f"old_{i}"

                # Reajustamos columnas para centrar todo
                c1, c2, c3, c4 = st.columns([3, 1, 1.5, 0.4]) 
                with c1:
                    st.write(f"**{item['nombre']}**")
                with c2:
                    # Input de cantidad interactivo
                    nueva_q = st.number_input("Cant.", min_value=1, value=item['cantidad'], key=f"q_{item['id']}")
                    if nueva_q != item['cantidad']:
                        # Actualizamos cantidad y subtotal en el acto
                        st.session_state.carrito[i]['cantidad'] = nueva_q
                        st.session_state.carrito[i]['subtotal'] = item['precio'] * nueva_q
                        st.rerun()
                with c3:
                    # Formato precio local
                    sub_f = f"${item['subtotal']:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
                    st.markdown(f"<p style='text-align:right; font-size:18px;'>{sub_f}</p>", unsafe_allow_html=True)
                with c4:
                    # Botón de eliminar (🗑️) con llave única e ID
                    if st.button("🗑️", key=f"del_{item['id']}"):
                        # Mandamos la orden de eliminación para el próximo rerun
                        st.session_state.id_a_eliminar = item['id']
                        st.rerun()
            
            # Botón de vaciar completo (más discreto)
            st.write("") # Espacio
            c1, c2 = st.columns([3, 1])
            with c2:
                if st.button("❌ Vaciar", key="vaciar_todo"):
                    st.session_state.carrito = []
                    st.rerun()
        else:
            # Recuperamos el aviso amigable cuando está vacío
            st.info("No hay productos cargados en el ticket actual.")

    # --- COLUMNA DERECHA (RESUMEN Y PAGO) ---
    with col_der:
        st.markdown('<div class="sub-blue">💰 Resumen y Pago</div>', unsafe_allow_html=True)
        if st.session_state.carrito:
            suma_base = sum(item['subtotal'] for item in st.session_state.carrito)
            
            # Ajustes rápidos
            c1, c2 = st.columns(2)
            with c1: p_desc = st.number_input("Descuento %", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
            with c2: p_rec = st.number_input("Recargo %", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
            
            # Cálculos
            m_desc = (suma_base * p_desc / 100)
            m_rec = (suma_base * p_rec / 100)
            total_final = suma_base - m_desc + m_rec
            
            # Recuperamos TOTAL azul grande
            total_f = f"${total_final:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
            st.markdown(f"<p class='total-font'>TOTAL: {total_f}</p>", unsafe_allow_html=True)
            
            # Avisos de ajustes si existen
            if m_desc > 0: st.markdown(f"📉 *Descuento aplicado: -${m_desc:,.2f}*")
            if m_rec > 0: st.markdown(f"📈 *Recargo aplicado: +${m_rec:,.2f}*")
            
            st.divider()
            
            # Medios de Pago
            metodo = st.selectbox("Medio de Pago:", ["Efectivo", "Débito", "Crédito", "Transferencia", "Fiado"])
            detalles_pago = st.text_input("Cuenta / Detalles:") if metodo == "Transferencia" else ""
            
            cliente = "Consumidor Final"
            if metodo == "Fiado":
                cliente = st.text_input("Nombre del Cliente (Obligatorio):")

            if st.button("🚀 CONFIRMAR VENTA", type="primary", use_container_width=True):
                if metodo == "Fiado" and not cliente:
                    st.warning("⚠️ Debes ingresar el nombre del cliente para fiar.")
                else:
                    # Guardamos en Firebase (Única Verdad)
                    venta_data = {
                        "id_negocio": id_negocio,
                        "vendedor": nombre_u,
                        "suma_base": suma_base,
                        "total": total_final,
                        "metodo": metodo,
                        "detalles_pago": detalles_pago,
                        "cliente_nombre": cliente,
                        "items": st.session_state.carrito,
                        "fecha": ahora_ar.isoformat()
                    }
                    db.collection("ventas_procesadas").add(venta_data)
                    st.session_state.carrito = []
                    st.success("✅ ¡Venta registrada con éxito!")
                    st.balloons()
                    st.rerun()
        else:
            # RECUPERAMOS EL MENSAJE DE ESPERANDO PRODUCTO
            st.write("") # Espacio
            st.warning("Esperando productos... Agrega artículos desde el buscador de la izquierda.")

    # Pie de página discreto
    st.write("") # Espacio
    st.caption(f"🆔 Local: {id_negocio} | Vendedor: {nombre_u} | Lista vinc.: A2-C2")
