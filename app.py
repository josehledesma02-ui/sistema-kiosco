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
        # LEER DESDE LA FILA 2 (header=1 en pandas significa fila 2 del Excel)
        df = pd.read_csv(URL_PROVEEDOR_CSV, header=1)
        
        # Limpieza de títulos de columnas
        df.columns = df.columns.astype(str).str.strip()
        
        # BUSCADOR FLEXIBLE: Busca las columnas sin importar si es A, B, C...
        col_prod = [c for c in df.columns if any(kw in c.lower() for kw in ['producto', 'articulo', 'descrip'])]
        col_prec = [c for c in df.columns if any(kw in c.lower() for kw in ['precio', 'venta', 'valor'])]
        
        if col_prod and col_prec:
            # Renombramos internamente para que el sistema no falle
            df = df.rename(columns={col_prod[0]: 'Productos', col_prec[0]: 'Precio'})
            
            # Limpieza de Precios: Quita $, puntos, comas y espacios
            df['Precio'] = df['Precio'].astype(str).str.replace(r'[\$\s\.]', '', regex=True).str.replace(',', '.')
            df['Precio'] = pd.to_numeric(df['Precio'], errors='coerce').fillna(0)
            
            # Quita filas donde no haya nombre de producto
            df = df.dropna(subset=['Productos'])
            st.session_state.df_proveedor = df
            st.success("✅ Lista de precios vinculada correctamente.")
        else:
            st.error(f"⚠️ No encontré 'Productos' (A2) o 'Precio' (C2). Columnas detectadas: {list(df.columns)}")
            
    except Exception as e:
        st.error(f"⚠️ Error al conectar con Google Sheets: {e}")

if st.session_state.df_proveedor is None:
    cargar_datos_proveedor()

# ==========================================
# 3. FUNCIONES DE VENTA
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

else:
    negocio_id = st.session_state['id_negocio']
    vendedor = st.session_state['nombre_real'] or st.session_state['usuario']

    with st.sidebar:
        if os.path.exists(IMG_SIDEBAR):
            st.image(IMG_SIDEBAR, width=130)
        st.write(f"👤 **{vendedor}**")
        if st.button("🔄 Actualizar Lista"): 
            cargar_datos_proveedor()
            st.rerun()
        st.divider()
        if st.button("🔴 Salir", use_container_width=True): cerrar_sesion()

    tabs = st.tabs(["🛒 Ventas", "📉 Gastos", "📜 Historial"])

    # --- VENTAS ---
    with tabs[0]:
        col_izq, col_der = st.columns([1.6, 1])

        with col_izq:
            busqueda = st.text_input("🔍 Buscar producto...", placeholder="Escribe el nombre...")
            
            if busqueda and st.session_state.df_provider is not None:
                df = st.session_state.df_proveedor
                res = df[df['Productos'].str.contains(busqueda, case=False, na=False)]
                
                if not res.empty:
                    for _, fila in res.head(10).iterrows():
                        if st.button(f"➕ {fila['Productos']} - ${fila['Precio']:,.2f}", key=f"b_{fila['Productos']}"):
                            agregar_al_carrito(fila['Productos'], fila['Precio'], 1)
                            st.toast(f"Agregado: {fila['Productos']}")
            
            st.divider()
            if st.session_state.carrito:
                for i, it in enumerate(st.session_state.carrito):
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 0.5])
                    c1.write(f"**{it['nombre']}**")
                    it['cantidad'] = c2.number_input("Cant", 1, 1000, it['cantidad'], key=f"q_{i}", label_visibility="collapsed")
                    it['subtotal'] = it['precio'] * it['cantidad']
                    c3.write(f"${it['subtotal']:,.2f}")
                    if c4.button("❌", key=f"del_{i}"):
                        st.session_state.carrito.pop(i)
                        st.rerun()

        with col_der:
            total_v = sum(it['subtotal'] for it in st.session_state.carrito)
            st.markdown(f"<div style='background:#f0f2f6;padding:20px;border-radius:10px;text-align:center'><p style='margin:0'>TOTAL A COBRAR</p><h1 style='color:#2e7d32;margin:0'>${total_v:,.2f}</h1></div>", unsafe_allow_html=True)
            
            metodo = st.selectbox("Forma de Pago", ["Efectivo", "Transferencia", "Débito", "Crédito", "Fiado"])
            
            if st.button("✅ FINALIZAR VENTA", use_container_width=True, type="primary"):
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

    # --- PESTAÑAS RESTANTES ---
    with tabs[1]:
        st.subheader("Registrar Gasto")
        with st.form("gasto"):
            m = st.number_input("Monto $", min_value=0.0)
            d = st.text_input("Concepto")
            if st.form_submit_button("Guardar"):
                db.collection("gastos").add({"monto": m, "detalle": d, "fecha": datetime.now(), "id_negocio": negocio_id})
                st.success("Registrado")

    with tabs[2]:
        st.subheader("Historial de hoy")
        v_ref = db.collection("ventas_procesadas").where("id_negocio", "==", negocio_id).order_by("fecha", direction=firestore.Query.DESCENDING).limit(10).stream()
        for v in v_ref:
            d = v.to_dict()
            st.write(f"🕒 {d['fecha'].strftime('%H:%M')} - Total: **${d['total']:,.2f}** ({d['metodo']})")
