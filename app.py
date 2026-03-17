import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime

# ==========================================
# 0. CONFIGURACIÓN VISUAL (Nombres fijos)
# ==========================================
# Cambiá el nombre de tus fotos en la carpeta a estos dos para que ande perfecto:
IMG_LOGIN = "logo.png" 
IMG_SIDEBAR = "logo_chico.png"

st.set_page_config(page_title="JL Gestión Pro", page_icon="🛍️", layout="wide")

# CONFIGURACIÓN DEL PROVEEDOR (Google Sheets)
ID_HOJA = "TU_ID_DE_GOOGLE_SHEETS_AQUI" 
URL_PROVEEDOR = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/export?format=csv"

# ==========================================
# 1. CONEXIÓN A FIREBASE
# ==========================================
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

# ==========================================
# 2. MOTOR DE SESIÓN Y FUNCIONES
# ==========================================
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
    codigo = st.session_state.search_input.strip()
    if not codigo: return
    encontrado = False
    # 1. Buscar en Stock Propio (Firebase)
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

# ==========================================
# 3. PANTALLA DE INGRESO
# ==========================================
if not st.session_state['autenticado']:
    c1, col_login, c3 = st.columns([1, 1.5, 1])
    with col_login:
        try:
            st.image(IMG_LOGIN, use_container_width=True)
        except:
            st.markdown("<h1 style='text-align: center;'>🛍️ JL GESTIÓN</h1>", unsafe_allow_html=True)
        
        u_input = st.text_input("Usuario").strip().lower()
        c_input = st.text_input("Contraseña", type="password").strip()
        if st.button("Ingresar al Sistema", use_container_width=True):
            user_ref = db.collection("usuarios").document(u_input).get()
            if user_ref.exists and str(user_ref.to_dict().get('password')) == c_input:
                d = user_ref.to_dict()
                st.session_state.update({
                    'autenticado': True, 'usuario': u_input, 'rol': d.get('rol'), 
                    'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre'), 
                    'permisos': d.get('permisos', 'todo')
                })
                st.rerun()
            else: st.error("❌ Credenciales incorrectas")

# ==========================================
# 4. PANEL PRINCIPAL
# ==========================================
else:
    rol, negocio_id = st.session_state['rol'], st.session_state['id_negocio']
    vendedor = st.session_state['nombre_real'] or st.session_state['usuario']

    with st.sidebar:
        try:
            st.image(IMG_SIDEBAR, width=150)
        except:
            st.write("### JL GESTIÓN PRO")
        
        st.write(f"👤 **{vendedor}**")
        st.caption(f"Sucursal: {negocio_id.upper()}")
        if st.button("🔄 Sincronizar Proveedor"): 
            cargar_datos_proveedor()
            st.success("Lista actualizada")
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True): cerrar_sesion()

    tabs = st.tabs(["🛒 Ventas", "📦 Stock", "📉 Gastos/Retiros", "📜 Historial", "👥 Personal"])

    # 🛒 PESTAÑA VENTAS
    with tabs[0]:
        nro_f = 1
        try:
            f_ref = db.collection("ventas_procesadas").where("id_negocio", "==", negocio_id).order_by("nro_factura", direction=firestore.Query.DESCENDING).limit(1).get()
            if f_ref: nro_f = f_ref[0].to_dict()['nro_factura'] + 1
        except: nro_f = 1
        
        st.subheader(f"Punto de Venta - Ticket #{str(nro_f).zfill(5)}")
        col_izq, col_der = st.columns([1.2, 1])

        with col_izq:
            st.text_input("Escanear producto...", key="search_input", on_change=procesar_escaneo)
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
            else:
                st.info("Listo para escanear.")

        with col_der:
            total = sum(it['subtotal'] for it in st.session_state.carrito)
            st.metric("TOTAL A PAGAR", f"${total:,.2f}")
            metodo = st.selectbox("Pago", ["Efectivo", "Transferencia", "Tarjeta", "Cuenta Corriente"])
            
            if st.button("✅ FINALIZAR VENTA", use_container_width=True, type="primary"):
                if st.session_state.carrito:
                    venta = {"nro_factura": nro_f, "vendedor": vendedor, "id_negocio": negocio_id, "items": st.session_state.carrito, "total": total, "metodo": metodo, "fecha": datetime.now()}
                    db.collection("ventas_procesadas").add(venta)
                    
                    # Formato Ticket
                    tkt = f"      JL GESTION PRO\n--------------------------\nTicket: {nro_f}\nFecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n--------------------------\n"
                    for it in st.session_state.carrito:
                        tkt += f"{it['nombre'][:20]}\n{it['cantidad']} x ${it['precio']} = ${it['subtotal']}\n"
                    tkt += f"--------------------------\nTOTAL: ${total}\n--------------------------\n\n\n"
                    
                    st.session_state.ultimo_ticket = tkt
                    st.session_state.carrito = []
                    st.rerun()

            if st.session_state.ultimo_ticket:
                st.download_button("🖨️ IMPRIMIR TICKET", st.session_state.ultimo_ticket, f"tkt_{nro_f}.txt", use_container_width=True)

    # 📦 PESTAÑA STOCK (Carga y Modificación)
    with tabs[1]:
        st.subheader("Control de Stock")
        op_stock = st.radio("Acción:", ["Cargar Mercadería Nueva (Boleta)", "Modificar Existente"], horizontal=True)
        
        if op_stock == "Cargar Mercadería Nueva (Boleta)":
            with st.form("new_prod", clear_on_submit=True):
                c1, c2 = st.columns(2)
                cod = c1.text_input("Código de Barras")
                nom = c1.text_input("Nombre del Producto")
                pre = c2.number_input("Precio Venta $", min_value=0.0)
                stk = c2.number_input("Cantidad", min_value=0)
                if st.form_submit_button("Guardar"):
                    db.collection("productos").add({"codigo": cod, "nombre": nom, "precio": pre, "stock": stk, "id_negocio": negocio_id})
                    st.success("Cargado con éxito.")
        else:
            busq = st.text_input("Buscar producto para editar")
            if busq:
                prods = db.collection("productos").where("id_negocio", "==", negocio_id).stream()
                match = [p for p in prods if busq.lower() in p.to_dict()['nombre'].lower() or busq == p.to_dict()['codigo']]
                for m in match:
                    p_data = m.to_dict()
                    with st.expander(f"Editar: {p_data['nombre']}"):
                        with st.form(f"e_{m.id}"):
                            u_p = st.number_input("Precio $", value=float(p_data['precio']))
                            u_s = st.number_input("Stock", value=int(p_data.get('stock', 0)))
                            if st.form_submit_button("Actualizar"):
                                db.collection("productos").document(m.id).update({"precio": u_p, "stock": u_s})
                                st.success("Actualizado.")

    # 📉 PESTAÑA GASTOS
    with tabs[2]:
        st.subheader("Gastos y Retiros")
        t_salida = st.selectbox("Tipo:", ["Gasto del Negocio", "Personal / Retiro"])
        with st.form("gastos_f", clear_on_submit=True):
            cat = st.selectbox("Concepto:", ["Proveedor", "Luz/Internet", "Sueldos", "Pérdida/Vencido", "Retiro Dueño", "Mercadería Casa"])
            mon = st.number_input("Monto $", min_value=0.0)
            det = st.text_area("Detalle")
            if st.form_submit_button("Registrar Salida"):
                db.collection("gastos").add({"id_negocio": negocio_id, "tipo": t_salida, "categoria": cat, "monto": mon, "detalle": det, "fecha": datetime.now(), "usuario": st.session_state['usuario']})
                st.success("Registrado.")

    # 📜 HISTORIAL
    with tabs[3]:
        st.subheader("Últimas 10 ventas")
        v_h = db.collection("ventas_procesadas").where("id_negocio", "==", negocio_id).order_by("fecha", direction=firestore.Query.DESCENDING).limit(10).stream()
        for v in v_h:
            vd = v.to_dict()
            st.write(f"**Ticket {vd.get('nro_factura')}** | Total: ${vd.get('total')} | {vd.get('metodo')}")

    # 👥 PERSONAL
    with tabs[4]:
        if rol == "negocio":
            st.subheader("Gestión de Usuarios")
            with st.form("u_add", clear_on_submit=True):
                un = st.text_input("Usuario").lower()
                nr = st.text_input("Nombre")
                ps = st.text_input("Contraseña")
                if st.form_submit_button("Crear"):
                    db.collection("usuarios").document(un).set({"nombre": nr, "password": ps, "rol": "empleado", "id_negocio": negocio_id})
                    st.success("Usuario creado.")
