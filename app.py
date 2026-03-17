import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import os

# ==========================================
# 0. CONFIGURACIÓN INICIAL
# ==========================================
st.set_page_config(page_title="JL Gestión Pro", page_icon="🛍️", layout="wide")

IMG_LOGIN = "logo.png" 
IMG_SIDEBAR = "logo_chico.png"

# URL de exportación automática para Google Sheets
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
        st.error(f"⚠️ Error de conexión: {e}")
        st.stop()

db = firestore.client()

# ==========================================
# 2. MOTOR DE DATOS (GOOGLE SHEETS)
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.update({
        'autenticado': False, 'usuario': None, 'rol': None, 
        'id_negocio': None, 'nombre_real': None,
        'carrito': [], 'df_proveedor': None
    })

def cargar_datos_proveedor():
    try:
        # Leemos el CSV
        df = pd.read_csv(URL_PROVEEDOR_CSV)
        
        # Limpieza de títulos de columnas (quita espacios)
        df.columns = df.columns.astype(str).str.strip()
        
        # BUSCADOR FLEXIBLE: No importa la posición (A, B, C...), busca por nombre
        col_prod = [c for c in df.columns if any(kw in c.lower() for kw in ['producto', 'articulo', 'descrip'])]
        col_prec = [c for c in df.columns if any(kw in c.lower() for kw in ['precio', 'venta', 'valor'])]
        
        if col_prod and col_prec:
            # Renombramos internamente para que el código no falle
            df = df.rename(columns={col_prod[0]: 'Productos', col_prec[0]: 'Precio'})
            
            # Limpieza de la columna Precio (quita $, puntos de miles y espacios)
            df['Precio'] = df['Precio'].astype(str).str.replace(r'[\$\s\.]', '', regex=True).str.replace(',', '.')
            df['Precio'] = pd.to_numeric(df['Precio'], errors='coerce').fillna(0)
            
            # Quitamos filas vacías
            df = df.dropna(subset=['Productos'])
            st.session_state.df_proveedor = df
        else:
            st.error(f"⚠️ No detecté 'Productos' o 'Precio'. Columnas leídas: {list(df.columns)}")
            
    except Exception as e:
        st.error(f"⚠️ Error al conectar con Google Sheets: {e}")

if st.session_state.df_proveedor is None:
    cargar_datos_proveedor()

# ==========================================
# 3. LÓGICA DEL CARRITO
# ==========================================
def agregar_al_carrito(nombre, precio, cantidad):
    for item in st.session_state.carrito:
        if item['nombre'] == nombre:
            item['cantidad'] += cantidad
            item['subtotal'] = item['cantidad'] * item['precio']
            return
    st.session_state.carrito.append({
        'nombre': nombre, 'precio': precio, 
        'cantidad': cantidad, 'subtotal': precio * cantidad
    })

def cerrar_sesion():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ==========================================
# 4. INTERFAZ DE USUARIO
# ==========================================

# --- LOGIN ---
if not st.session_state['autenticado']:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        if os.path.exists(IMG_LOGIN):
            st.image(IMG_LOGIN, use_container_width=True)
        else:
            st.title("🛍️ JL GESTIÓN")
        
        u_input = st.text_input("Usuario").strip().lower()
        c_input = st.text_input("Contraseña", type="password").strip()
        
        if st.button("Ingresar", use_container_width=True, type="primary"):
            user_ref = db.collection("usuarios").document(u_input).get()
            if user_ref.exists and str(user_ref.to_dict().get('password')) == c_input:
                d = user_ref.to_dict()
                st.session_state.update({
                    'autenticado': True, 'usuario': u_input, 'rol': d.get('rol'), 
                    'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre')
                })
                st.rerun()
            else:
                st.error("Credenciales incorrectas")

# --- PANEL DE CONTROL ---
else:
    negocio_id = st.session_state['id_negocio']
    vendedor = st.session_state['nombre_real'] or st.session_state['usuario']

    with st.sidebar:
        if os.path.exists(IMG_SIDEBAR):
            st.image(IMG_SIDEBAR, width=130)
        st.write(f"👤 **{vendedor}**")
        if st.button("🔄 Sincronizar Lista"): 
            cargar_datos_proveedor()
            st.toast("Lista actualizada")
        st.divider()
        if st.button("🔴 Salir", use_container_width=True): cerrar_sesion()

    tabs = st.tabs(["🛒 Ventas", "📉 Gastos", "📜 Historial"])

    # --- PESTAÑA VENTAS ---
    with tabs[0]:
        col_v, col_r = st.columns([1.6, 1])

        with col_v:
            busqueda = st.text_input("🔍 Buscar producto...", placeholder="Escribe para buscar en el Excel...")
            
            if busqueda and st.session_state.df_proveedor is not None:
                df = st.session_state.df_proveedor
                # Filtro de búsqueda
                res = df[df['Productos'].str.contains(busqueda, case=False, na=False)]
                
                if not res.empty:
                    for _, fila in res.head(8).iterrows():
                        nombre = fila['Productos']
                        precio = fila['Precio']
                        if st.button(f"➕ {nombre} | ${precio:,.2f}", key=f"btn_{nombre}_{precio}"):
                            agregar_al_carrito(nombre, precio, 1)
                            st.toast(f"Añadido: {nombre}")
            
            st.divider()
            if st.session_state.carrito:
                for i, it in enumerate(st.session_state.carrito):
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 0.5])
                    c1.write(f"**{it['nombre']}**")
                    it['cantidad'] = c2.number_input("Cant", 1, 1000, it['cantidad'], key=f"v_{i}", label_visibility="collapsed")
                    it['subtotal'] = it['precio'] * it['cantidad']
                    c3.write(f"${it['subtotal']:,.2f}")
                    if c4.button("❌", key=f"del_{i}"):
                        st.session_state.carrito.pop(i)
                        st.rerun()

        with col_r:
            total_v = sum(it['subtotal'] for it in st.session_state.carrito)
            st.markdown(f"<div style='background:#f0f2f6;padding:20px;border-radius:10px;text-align:center'><p style='margin:0'>TOTAL A COBRAR</p><h1 style='color:#2e7d32;margin:0'>${total_v:,.2f}</h1></div>", unsafe_allow_html=True)
            
            metodo = st.selectbox("Pago", ["Efectivo", "Transferencia", "Débito", "Crédito", "Fiado"])
            
            if st.button("✅ REGISTRAR VENTA", use_container_width=True, type="primary"):
                if st.session_state.carrito:
                    venta = {
                        "vendedor": vendedor, "id_negocio": negocio_id, 
                        "items": st.session_state.carrito, "total": total_v, 
                        "metodo": metodo, "fecha": datetime.now()
                    }
                    db.collection("ventas_procesadas").add(venta)
                    st.success("Venta guardada")
                    st.session_state.carrito = []
                    st.rerun()

    # --- PESTAÑA GASTOS ---
    with tabs[1]:
        st.subheader("Registrar Salida de Dinero")
        with st.form("g_form", clear_on_submit=True):
            tg = st.radio("Tipo", ["Negocio", "Personal"], horizontal=True)
            cg = st.selectbox("Categoría", ["Mercadería", "Luz/Gas", "Sueldos", "Varios"])
            mg = st.number_input("Monto $", min_value=0.0)
            if st.form_submit_button("Guardar Gasto"):
                db.collection("gastos").add({
                    "id_negocio": negocio_id, "tipo": tg, "categoria": cg, 
                    "monto": mg, "fecha": datetime.now(), "usuario": st.session_state.usuario
                })
                st.success("Gasto registrado")

    # --- PESTAÑA HISTORIAL ---
    with tabs[2]:
        st.subheader("Últimas 15 ventas")
        v_ref = db.collection("ventas_procesadas").where("id_negocio", "==", negocio_id).order_by("fecha", direction=firestore.Query.DESCENDING).limit(15).stream()
        for v in v_ref:
            d = v.to_dict()
            st.write(f"📅 {d['fecha'].strftime('%H:%M')} | **${d['total']:,.2f}** | {d['metodo']}")
