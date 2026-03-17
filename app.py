import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import os

# ==========================================
# 0. CONFIGURACIÓN INICIAL Y LOGOS
# ==========================================
st.set_page_config(page_title="JL Gestión Pro", page_icon="🛍️", layout="wide")

IMG_LOGIN = "logo.png" 
IMG_SIDEBAR = "logo_chico.png"

# URL de exportación automática para Google Sheets (formato CSV)
ID_HOJA = "1-ay_xIqYItwOaXe80VUsEmh4gsANrk9PH72aZcUD54g"
URL_PROVEEDOR_CSV = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/export?format=csv"

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
        st.error(f"⚠️ Error de conexión a Base de Datos: {e}")
        st.stop()

db = firestore.client()

# ==========================================
# 2. MOTOR DE SESIÓN Y FUNCIONES
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.update({
        'autenticado': False, 'usuario': None, 'rol': None, 
        'id_negocio': None, 'nombre_real': None,
        'carrito': [], 'ultimo_ticket': None, 'df_proveedor': None
    })

def cargar_datos_proveedor():
    try:
        df = pd.read_csv(URL_PROVEEDOR_CSV)
        # Limpieza de precios (quita $ y comas para que sean números)
        if 'Precio' in df.columns:
            df['Precio'] = df['Precio'].replace(r'[\$,]', '', regex=True).astype(float)
        st.session_state.df_proveedor = df
    except Exception as e:
        st.error(f"⚠️ Error al cargar lista de precios: {e}")

if st.session_state.df_proveedor is None:
    cargar_datos_proveedor()

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

def cerrar_sesion():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ==========================================
# 3. PANTALLA DE LOGIN
# ==========================================
if not st.session_state['autenticado']:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        if os.path.exists(IMG_LOGIN):
            st.image(IMG_LOGIN, use_container_width=True)
        else:
            st.markdown("<h1 style='text-align: center;'>🛍️ JL GESTIÓN</h1>", unsafe_allow_html=True)
        
        u_input = st.text_input("Usuario").strip().lower()
        c_input = st.text_input("Contraseña", type="password").strip()
        
        if st.button("Ingresar al Sistema", use_container_width=True, type="primary"):
            user_ref = db.collection("usuarios").document(u_input).get()
            if user_ref.exists and str(user_ref.to_dict().get('password')) == c_input:
                d = user_ref.to_dict()
                st.session_state.update({
                    'autenticado': True, 'usuario': u_input, 'rol': d.get('rol'), 
                    'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre')
                })
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")

# ==========================================
# 4. PANEL PRINCIPAL (SISTEMA POST-LOGIN)
# ==========================================
else:
    negocio_id = st.session_state['id_negocio']
    vendedor = st.session_state['nombre_real'] or st.session_state['usuario']

    # SIDEBAR
    with st.sidebar:
        if os.path.exists(IMG_SIDEBAR):
            st.image(IMG_SIDEBAR, width=150)
        st.write(f"👤 **{vendedor}**")
        st.caption(f"Sucursal: {negocio_id.upper()}")
        if st.button("🔄 Sincronizar Precios"): 
            cargar_datos_proveedor()
            st.success("Lista actualizada")
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True):
            cerrar_sesion()

    tabs = st.tabs(["🛒 Ventas", "📦 Stock", "📉 Gastos", "📜 Historial"])

    # --- TABS: VENTAS ---
    with tabs[0]:
        st.subheader("Punto de Venta")
        col_izq, col_der = st.columns([1.5, 1])

        with col_izq:
            busqueda = st.text_input("🔍 Buscar producto o escanear...", placeholder="Escribe nombre o código...")
            
            if busqueda and st.session_state.df_proveedor is not None:
                df = st.session_state.df_proveedor
                # Filtra por nombre o por código si existe la columna
                res = df[df['Productos'].str.contains(busqueda, case=False, na=False)]
                
                if not res.empty:
                    st.write("Resultados:")
                    for _, fila in res.head(5).iterrows():
                        if st.button(f"➕ {fila['Productos']} - ${fila['Precio']}", key=f"btn_{fila['Productos']}"):
                            agregar_al_carrito(fila['Productos'], fila['Precio'], 1)
                            st.toast(f"Agregado: {fila['Productos']}")

            st.divider()
            if st.session_state.carrito:
                for i, it in enumerate(st.session_state.carrito):
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 0.5])
                    c1.write(f"**{it['nombre']}**")
                    it['cantidad'] = c2.number_input("Cant", 1, 100, it['cantidad'], key=f"q_{i}", label_visibility="collapsed")
                    it['subtotal'] = it['precio'] * it['cantidad']
                    c3.write(f"${it['subtotal']:,.2f}")
                    if c4.button("❌", key=f"del_{i}"):
                        st.session_state.carrito.pop(i)
                        st.rerun()

        with col_der:
            total = sum(it['subtotal'] for it in st.session_state.carrito)
            st.markdown(f"### TOTAL: ${total:,.2f}")
            metodo = st.selectbox("Pago", ["Efectivo", "Transferencia", "Tarjeta", "Fiado"])
            
            if st.button("✅ FINALIZAR VENTA", use_container_width=True, type="primary"):
                if st.session_state.carrito:
                    venta = {
                        "vendedor": vendedor, "id_negocio": negocio_id, 
                        "items": st.session_state.carrito, "total": total, 
                        "metodo": metodo, "fecha": datetime.now()
                    }
                    db.collection("ventas_procesadas").add(venta)
                    st.success("Venta guardada!")
                    st.session_state.carrito = []
                    st.rerun()

    # --- TABS: STOCK (ADMINISTRACIÓN) ---
    with tabs[1]:
        st.subheader("Control de Stock Propio")
        with st.form("nuevo_producto", clear_on_submit=True):
            c1, c2 = st.columns(2)
            cod = c1.text_input("Código de Barras")
            nom = c1.text_input("Nombre del Producto")
            pre = c2.number_input("Precio Venta $", min_value=0.0)
            stk = c2.number_input("Cantidad inicial", min_value=0)
            if st.form_submit_button("Guardar en Stock"):
                db.collection("productos").add({
                    "codigo": cod, "nombre": nom, "precio": pre, 
                    "stock": stk, "id_negocio": negocio_id
                })
                st.success("Producto guardado.")

    # --- TABS: GASTOS ---
    with tabs[2]:
        st.subheader("Registro de Salidas / Gastos")
        with st.form("form_gastos", clear_on_submit=True):
            tipo = st.radio("Tipo de Gasto", ["Negocio", "Retiro Personal"], horizontal=True)
            cat = st.selectbox("Categoría", ["Proveedor", "Servicios", "Sueldos", "Varios"])
            monto = st.number_input("Monto $", min_value=0.0)
            det = st.text_input("Detalle")
            if st.form_submit_button("Registrar"):
                db.collection("gastos").add({
                    "id_negocio": negocio_id, "tipo": tipo, "categoria": cat, 
                    "monto": monto, "detalle": det, "fecha": datetime.now(), 
                    "usuario": st.session_state['usuario']
                })
                st.success("Gasto registrado correctamente.")

    # --- TABS: HISTORIAL ---
    with tabs[3]:
        st.subheader("Últimas Ventas")
        ventas_ref = db.collection("ventas_procesadas").where("id_negocio", "==", negocio_id).order_by("fecha", direction=firestore.Query.DESCENDING).limit(10).stream()
        for v in ventas_ref:
            vd = v.to_dict()
            fecha_v = vd['fecha'].strftime("%H:%M - %d/%m")
            st.write(f"🕒 {fecha_v} | **${vd['total']}** | {vd['metodo']} | {vd['vendedor']}")
