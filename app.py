import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="JL Gestión Pro - POS", page_icon="🛍️", layout="wide")

# --- CONFIGURACIÓN DEL PROVEEDOR (Google Sheets) ---
# Reemplaza con el ID de la planilla de tu proveedor
ID_HOJA = "TU_ID_DE_GOOGLE_SHEETS_AQUI" 
URL_PROVEEDOR = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/export?format=csv"

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
        'carrito': [], 'ultimo_ticket': None, 'df_proveedor': None
    })

def cargar_datos_proveedor():
    try:
        df = pd.read_csv(URL_PROVEEDOR)
        st.session_state.df_proveedor = df
    except:
        st.session_state.df_proveedor = None

if st.session_state.df_proveedor is None:
    cargar_datos_proveedor()

def cerrar_sesion():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- 🛒 FUNCIONES DEL POS ---
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

def procesar_escaneo():
    """Busca en Stock Propio y luego en Proveedor"""
    codigo = st.session_state.search_input.strip()
    if not codigo: return
    
    encontrado = False
    # 1. Buscar en Firebase (Tu Stock)
    prod_ref = db.collection("productos").where("id_negocio", "==", st.session_state['id_negocio']).where("codigo", "==", codigo).limit(1).get()
    
    if prod_ref:
        p = prod_ref[0].to_dict()
        agregar_al_carrito(p['nombre'], float(p['precio']), 1, codigo)
        encontrado = True
    # 2. Buscar en Planilla Proveedor
    elif st.session_state.df_proveedor is not None:
        df = st.session_state.df_proveedor
        res = df[df['codigo'].astype(str) == codigo]
        if not res.empty:
            agregar_al_carrito(res.iloc[0]['nombre'], float(res.iloc[0]['precio']), 1, codigo)
            encontrado = True
            
    if not encontrado: st.toast(f"❌ No encontrado: {codigo}", icon="⚠️")
    st.session_state.search_input = ""

# --- 🚪 PANTALLA DE INGRESO ---
if not st.session_state['autenticado']:
    c1, col_login, c3 = st.columns([1, 1.5, 1])
    with col_login:
        st.markdown("<h2 style='text-align: center;'>JL GESTIÓN PRO</h2>", unsafe_allow_html=True)
        u_input = st.text_input("Usuario").strip().lower()
        c_input = st.text_input("Contraseña", type="password").strip()
        if st.button("Ingresar", use_container_width=True):
            user_ref = db.collection("usuarios").document(u_input).get()
            if user_ref.exists and str(user_ref.to_dict().get('password')) == c_input:
                d = user_ref.to_dict()
                st.session_state.update({'autenticado': True, 'usuario': u_input, 'rol': d.get('rol'), 'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre'), 'permisos': d.get('permisos', 'todo')})
                st.rerun()
            else: st.error("❌ Datos incorrectos")

# --- 🖥️ PANEL PRINCIPAL ---
else:
    rol, permisos, negocio_id = st.session_state['rol'], st.session_state['permisos'], st.session_state['id_negocio']
    vendedor_actual = st.session_state['nombre_real'] or st.session_state['usuario']

    with st.sidebar:
        st.write(f"👤 **{vendedor_actual}**")
        st.caption(f"Sucursal: {negocio_id.upper()}")
        if st.button("🔄 Sincronizar Proveedor"): 
            cargar_datos_proveedor()
            st.success("Lista actualizada")
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True): cerrar_sesion()

    tabs = st.tabs(["🛒 Ventas POS", "📦 Stock / Inventario", "📉 Gastos y Retiros", "📜 Historial", "👥 Personal"])

    # ========================== 🛒 VENTAS (POS) ==========================
    with tabs[0]:
        nro_factura = 1
        try:
            fact_ref = db.collection("ventas_procesadas").where("id_negocio", "==", negocio_id).order_by("nro_factura", direction=firestore.Query.DESCENDING).limit(1).get()
            if fact_ref: nro_factura = fact_ref[0].to_dict()['nro_factura'] + 1
        except: nro_factura = 1
        
        st.title(f"Punto de Venta - Factura N° {str(nro_factura).zfill(6)}")
        col_izq, col_der = st.columns([1.2, 1])

        with col_izq:
            st.subheader("🔍 Lector / Buscador")
            st.text_input("Escanee aquí...", key="search_input", on_change=procesar_escaneo, placeholder="Foco aquí para el escáner")
            
            with st.expander("Añadir Manualmente"):
                with st.form("manual", clear_on_submit=True):
                    m_nom = st.text_input("Producto")
                    m_pre = st.number_input("Precio $", min_value=0.0)
                    if st.form_submit_button("Añadir"):
                        agregar_al_carrito(m_nom, m_pre, 1)
                        st.rerun()

        with col_der:
            st.subheader("🛒 Carrito")
            if st.session_state.carrito:
                for i, it in enumerate(st.session_state.carrito):
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 0.5])
                    c1.write(f"**{it['nombre']}**")
                    it['cantidad'] = c2.number_input("Q", min_value=1, value=it['cantidad'], key=f"q_{i}", label_visibility="collapsed")
                    it['subtotal'] = it['precio'] * it['cantidad']
                    c3.write(f"${it['subtotal']:,.2f}")
                    if c4.button("❌", key=f"del_{i}"): 
                        st.session_state.carrito.pop(i)
                        st.rerun()
                
                st.divider()
                subtotal = sum(it['subtotal'] for it in st.session_state.carrito)
                st.markdown(f"## TOTAL: ${subtotal:,.2f}")
                metodo = st.selectbox("Medio de Pago", ["Efectivo", "Transferencia", "Tarjeta", "Cuenta Corriente"])
                
                if st.button("✅ PROCESAR Y GENERAR TICKET", use_container_width=True, type="primary"):
                    venta_data = {
                        "nro_factura": nro_factura, "vendedor": vendedor_actual, "id_negocio": negocio_id,
                        "items": st.session_state.carrito, "total": subtotal, "metodo_pago": metodo, "fecha": datetime.now()
                    }
                    db.collection("ventas_procesadas").add(venta_data)
                    
                    # Generar texto para impresora térmica (58mm)
                    ticket = f"      JL GESTION PRO\n--------------------------\n"
                    ticket += f"Ticket: {str(nro_factura).zfill(6)}\n"
                    ticket += f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                    ticket += f"--------------------------\n"
                    for it in st.session_state.carrito:
                        ticket += f"{it['nombre'][:20]}\n{it['cantidad']} x ${it['precio']} = ${it['subtotal']}\n"
                    ticket += f"--------------------------\n"
                    ticket += f"TOTAL: ${subtotal:,.2f}\n"
                    ticket += f"Pago: {metodo}\n\n    GRACIAS POR SU COMPRA\n\n\n"
                    
                    st.session_state.ultimo_ticket = ticket
                    st.session_state.carrito = []
                    st.rerun()

            if st.session_state.ultimo_ticket:
                st.download_button("🖨️ DESCARGAR TICKET (IMPRIMIR)", st.session_state.ultimo_ticket, f"ticket_{nro_factura}.txt", use_container_width=True)
                if st.button("Nueva Venta"):
                    st.session_state.ultimo_ticket = None
                    st.rerun()

    # ========================== 📦 STOCK (CARGAR O MODIFICAR) ==========================
    with tabs[1]:
        st.subheader("Gestión de Stock Propio")
        modo = st.radio("Acción:", ["Cargar Nuevo (Boleta)", "Modificar Existente"], horizontal=True)
        
        if modo == "Cargar Nuevo (Boleta)":
            with st.form("nuevo_p", clear_on_submit=True):
                c1, c2 = st.columns(2)
                ncod = c1.text_input("Código de Barras")
                nnom = c1.text_input("Nombre del Producto")
                npre = c2.number_input("Precio de Venta $", min_value=0.0)
                nsto = c2.number_input("Stock Inicial", min_value=0)
                if st.form_submit_button("Guardar en Stock"):
                    if ncod and nnom:
                        db.collection("productos").add({"codigo": ncod, "nombre": nnom, "precio": npre, "stock": nsto, "id_negocio": negocio_id})
                        st.success(f"{nnom} registrado.")
        else:
            busq = st.text_input("Buscar por Nombre o Código para editar")
            if busq:
                prods = db.collection("productos").where("id_negocio", "==", negocio_id).stream()
                match = [p for p in prods if busq.lower() in p.to_dict()['nombre'].lower() or busq == p.to_dict()['codigo']]
                for m in match:
                    p_data = m.to_dict()
                    with st.expander(f"Editar: {p_data['nombre']}"):
                        with st.form(f"edit_{m.id}"):
                            upre = st.number_input("Precio $", value=float(p_data['precio']))
                            usto = st.number_input("Stock actual", value=int(p_data.get('stock', 0)))
                            if st.form_submit_button("Actualizar Datos"):
                                db.collection("productos").document(m.id).update({"precio": upre, "stock": usto})
                                st.success("Actualizado")

    # ========================== 📉 GASTOS Y RETIROS ==========================
    with tabs[2]:
        st.subheader("Salidas de Dinero")
        tipo_g = st.selectbox("Tipo de Salida:", ["Gasto del Negocio", "Personal / Retiro de Dueño"])
        
        with st.form("f_gastos", clear_on_submit=True):
            col1, col2 = st.columns(2)
            if tipo_g == "Gasto del Negocio":
                cat = col1.selectbox("Concepto:", ["Compra Proveedor", "Luz/Internet Local", "Sueldos", "Pérdida (Roto/Fallado)", "Otros"])
            else:
                cat = col1.selectbox("Concepto Personal:", ["Retiro Efectivo", "Mercadería Casa", "Boletas del Hogar"])
            
            monto = col1.number_input("Monto $", min_value=0.0)
            deta = col2.text_area("Detalle / Observación")
            if st.form_submit_button("Registrar"):
                db.collection("gastos").add({
                    "id_negocio": negocio_id, "tipo": tipo_g, "categoria": cat, 
                    "monto": monto, "detalle": deta, "fecha": datetime.now(), "usuario": st.session_state['usuario']
                })
                st.success("Registrado correctamente.")

    # ========================== 📜 HISTORIAL ==========================
    with tabs[3]:
        st.subheader("Últimas Ventas")
        v_h = db.collection("ventas_procesadas").where("id_negocio", "==", negocio_id).order_by("fecha", direction=firestore.Query.DESCENDING).limit(20).stream()
        h_lista = [{"N°": d.to_dict().get('nro_factura'), "Total": d.to_dict().get('total'), "Pago": d.to_dict().get('metodo_pago')} for d in v_h]
        if h_lista: st.table(h_lista)

    # ========================== 👥 PERSONAL ==========================
    with tabs[4]:
        st.subheader("Usuarios")
        if rol == "negocio":
            with st.expander("Crear Nuevo Usuario"):
                with st.form("u_new"):
                    u = st.text_input("Usuario").lower()
                    n = st.text_input("Nombre")
                    p = st.text_input("Clave")
                    per = st.selectbox("Rol", ["cajero", "encargado"])
                    if st.form_submit_button("Dar de alta"):
                        db.collection("usuarios").document(u).set({"nombre": n, "password": p, "rol": "empleado", "id_negocio": negocio_id, "permisos": per})
                        st.success("Creado")
