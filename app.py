import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import os

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="JL Gestión Pro - POS", page_icon="🛍️", layout="wide")

# 2. CONEXIÓN A FIREBASE
if not firebase_admin._apps:
    try:
        if "firebase" in st.secrets:
            creds_dict = dict(st.secrets["firebase"])
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(creds_dict)
        else:
            cred = credentials.Certificate("secretos.json")
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"⚠️ Error de conexión: {e}")
        st.stop()

db = firestore.client()

# --- 🚀 MOTOR DE SESIÓN ---
if 'autenticado' not in st.session_state:
    st.session_state.update({
        'autenticado': False, 'usuario': None, 'rol': None, 
        'id_negocio': None, 'nombre_real': None, 'permisos': 'todo',
        'carrito': []  # Inicializamos el carrito vacío
    })

def cerrar_sesion():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- 🛒 FUNCIONES DEL CARRITO ---
def agregar_al_carrito(nombre, precio, cantidad, codigo=""):
    for item in st.session_state.carrito:
        if item['nombre'] == nombre:
            item['cantidad'] += cantidad
            item['subtotal'] = item['cantidad'] * item['precio']
            return
    st.session_state.carrito.append({
        'nombre': nombre, 'precio': precio, 
        'cantidad': cantidad, 'subtotal': precio * cantidad,
        'codigo': codigo
    })

# --- 🚪 PANTALLA DE INGRESO ---
if not st.session_state['autenticado']:
    c1, col_login, c3 = st.columns([1, 1.5, 1])
    with col_login:
        st.markdown("<h2 style='text-align: center;'>JL GESTIÓN PRO</h2>", unsafe_allow_html=True)
        u_input = st.text_input("Usuario").strip().lower()
        c_input = st.text_input("Contraseña", type="password").strip()
        if st.button("Ingresar al Sistema", use_container_width=True):
            user_ref = db.collection("usuarios").document(u_input).get()
            if user_ref.exists:
                d = user_ref.to_dict()
                if str(d.get('password')) == c_input:
                    st.session_state.update({
                        'autenticado': True, 'usuario': u_input, 'rol': d.get('rol'), 
                        'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre'),
                        'permisos': d.get('permisos', 'todo')
                    })
                    st.rerun()
                else: st.error("❌ Contraseña incorrecta")
            else: st.error("❌ Usuario no encontrado")

# --- 🖥️ PANEL PRINCIPAL ---
else:
    rol = st.session_state['rol']
    permisos = st.session_state['permisos']
    negocio_id = st.session_state['id_negocio']
    vendedor_actual = st.session_state['nombre_real'] or st.session_state['usuario']

    with st.sidebar:
        st.write(f"👤 Vendedor: **{vendedor_actual}**")
        st.caption(f"Sucursal: {negocio_id.upper()}")
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True):
            cerrar_sesion()

    # Definir pestañas según permisos
    if rol == "negocio" or permisos == "encargado":
        tabs = st.tabs(["🛒 Ventas POS", "📜 Historial Facturas", "📉 Gastos", "📦 Stock", "👥 Personal"])
    elif permisos == "cajero":
        tabs = st.tabs(["🛒 Ventas POS", "📜 Historial Facturas"])
    else:
        tabs = st.tabs(["📦 Stock", "🧾 Compras"])

    # ==========================================
    # 🛒 MODULO DE VENTAS (POS)
    # ==========================================
    if rol == "negocio" or permisos in ["encargado", "cajero"]:
        with tabs[0]:
            # 1. Obtener Número de Factura Correlativo
            fact_ref = db.collection("ventas_procesadas").where("id_negocio", "==", negocio_id).order_by("nro_factura", direction=firestore.Query.DESCENDING).limit(1).get()
            nro_factura = fact_ref[0].to_dict()['nro_factura'] + 1 if fact_ref else 1
            
            st.title(f"Punto de Venta - Factura N° {str(nro_factura).zfill(6)}")
            
            col_izq, col_der = st.columns([1.2, 1])

            with col_izq:
                st.subheader("🔍 Buscador de Productos")
                busqueda = st.text_input("Ingrese nombre o escanee código de barras", key="search_input")
                
                # Simulación de búsqueda (Aquí conectarías con tu colección 'productos')
                with st.expander("Añadir Producto Manualmente", expanded=True):
                    with st.form("add_product", clear_on_submit=True):
                        c1, c2, c3 = st.columns([2,1,1])
                        p_nom = c1.text_input("Nombre del Producto")
                        p_pre = c2.number_input("Precio $", min_value=0.0, step=50.0)
                        p_cant = c3.number_input("Cant.", min_value=1, value=1)
                        if st.form_submit_button("Añadir al Carrito"):
                            if p_nom:
                                agregar_al_carrito(p_nom, p_pre, p_cant, busqueda)
                                st.rerun()

            with col_der:
                st.subheader("🛒 Carrito")
                if st.session_state.carrito:
                    # Mostrar tabla del carrito
                    for i, item in enumerate(st.session_state.carrito):
                        c_a, c_b, c_c, c_d = st.columns([3, 1.5, 1.5, 0.5])
                        c_a.write(f"**{item['nombre']}**")
                        
                        # Modificar cantidad
                        nueva_q = c_b.number_input("Cant.", min_value=1, value=item['cantidad'], key=f"q_{i}", label_visibility="collapsed")
                        item['cantidad'] = nueva_q
                        item['subtotal'] = item['precio'] * nueva_q
                        
                        c_c.write(f"${item['subtotal']:,.2f}")
                        if c_d.button("❌", key=f"del_{i}"):
                            st.session_state.carrito.pop(i)
                            st.rerun()
                    
                    st.divider()
                    subtotal = sum(item['subtotal'] for item in st.session_state.carrito)
                    
                    # Descuentos y Recargos
                    cd1, cd2 = st.columns(2)
                    desc = cd1.number_input("% Descuento", min_value=0, max_value=100, value=0)
                    reca = cd2.number_input("% Recargo", min_value=0, max_value=100, value=0)
                    
                    total_final = subtotal * (1 - desc/100) * (1 + reca/100)
                    
                    st.markdown(f"### TOTAL A PAGAR: ${total_final:,.2f}")
                    
                    # Métodos de Pago
                    metodo = st.selectbox("Medio de Pago", ["Efectivo", "Tarjeta Débito", "Tarjeta Crédito", "Transferencia", "Cuenta Corriente"])
                    
                    extra_info = ""
                    if metodo == "Transferencia":
                        extra_info = st.text_input("Nombre de la cuenta / Banco origen")
                    
                    id_cliente_cc = ""
                    if metodo == "Cuenta Corriente":
                        cl_ref = db.collection("clientes").where("id_negocio", "==", negocio_id).stream()
                        dict_cl = {c.to_dict()['nombre']: c.id for c in cl_ref}
                        if dict_cl:
                            id_cliente_cc = st.selectbox("Seleccione Cliente", list(dict_cl.keys()))
                        else:
                            st.warning("No hay clientes registrados para Cuenta Corriente.")

                    if st.button("🚀 PROCESAR VENTA", use_container_width=True, type="primary"):
                        venta_data = {
                            "nro_factura": nro_factura,
                            "vendedor": vendedor_actual,
                            "id_negocio": negocio_id,
                            "items": st.session_state.carrito,
                            "subtotal": subtotal,
                            "total": total_final,
                            "metodo_pago": metodo,
                            "extra_info": extra_info,
                            "fecha": datetime.now(),
                            "fecha_str": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        }
                        
                        # 1. Guardar venta general
                        db.collection("ventas_procesadas").add(venta_data)
                        
                        # 2. Si es CC, impactar en cuenta corriente
                        if metodo == "Cuenta Corriente" and id_cliente_cc:
                            db.collection("cuentas_corrientes").add({
                                "Cliente": dict_cl[id_cliente_cc],
                                "Nombre_Cliente": id_cliente_cc,
                                "Producto": f"Factura N° {nro_factura}",
                                "Subtotal": total_final,
                                "Negocio": negocio_id,
                                "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                                "Timestamp": datetime.now()
                            })
                        
                        st.success(f"Factura {nro_factura} procesada con éxito")
                        st.session_state.carrito = [] # Limpiar carrito
                        st.rerun()
                else:
                    st.info("El carrito está vacío.")

        # ==========================================
        # 📜 HISTORIAL DE FACTURAS
        # ==========================================
        with tabs[1]:
            st.subheader("Historial de Ventas")
            ventas_h = db.collection("ventas_procesadas").where("id_negocio", "==", negocio_id).order_by("fecha", direction=firestore.Query.DESCENDING).limit(50).stream()
            
            h_data = []
            for v in ventas_h:
                d = v.to_dict()
                h_data.append({
                    "N° Factura": d['nro_factura'],
                    "Fecha": d['fecha_str'],
                    "Vendedor": d.get('vendedor', 'N/A'),
                    "Medio Pago": d['metodo_pago'],
                    "Total": f"${d['total']:,.2f}"
                })
            
            if h_data:
                st.dataframe(pd.DataFrame(h_data), use_container_width=True)
            else:
                st.info("No hay ventas registradas aún.")

    # (Las demás secciones como GASTOS, STOCK y PERSONAL se mantienen con la lógica que ya tenías)
    # --- SECCIÓN GASTOS (Solo Dueño/Encargado) ---
    if rol == "negocio" or permisos == "encargado":
        with tabs[2]:
            st.subheader("Gestión de Gastos")
            with st.form("form_gastos_v2"):
                c1, c2 = st.columns(2)
                tipo_g = c1.selectbox("Concepto", ["Mercadería", "Luz", "Alquiler", "Sueldos", "Otros"])
                monto_g = c2.number_input("Monto $", min_value=0.0)
                if st.form_submit_button("Registrar Gasto"):
                    db.collection("gastos").add({
                        "id_negocio": negocio_id, "categoria": tipo_g, 
                        "monto": monto_g, "fecha": datetime.now().strftime("%d/%m/%Y")
                    })
                    st.success("Gasto guardado.")
