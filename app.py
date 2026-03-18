import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime, timedelta
import os
import urllib.parse

# ==========================================
# 0. CONFIGURACIÓN VISUAL
# ==========================================
st.set_page_config(page_title="JL Gestión Pro", page_icon="🛍️", layout="wide")

ID_HOJA = "1-ay_xIqYItwOaXe80VUsEmh4gsANrk9PH72aZcUD54g"
URL_PROVEEDOR_CSV = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/export?format=csv"
IMG_LOGIN = "logo.png" 
IMG_SIDEBAR = "logo_chico.png"

def mostrar_titulo():
    st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🛍️ JL GESTIÓN PRO</h1>", unsafe_allow_html=True)

def sumar_un_mes(fecha_str):
    try:
        fecha_dt = datetime.strptime(fecha_str, "%d/%m/%Y")
        proxima = fecha_dt + timedelta(days=31)
        return proxima.strftime("%d/%m/%Y")
    except: return fecha_str

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
        st.error(f"⚠️ Error Firebase: {e}")
        st.stop()

db = firestore.client()

# ==========================================
# 2. ESTADO DE SESIÓN
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.update({
        'autenticado': False, 'usuario': None, 'rol': None, 
        'id_negocio': None, 'nombre_real': None, 'id_usuario': None,
        'fecha_pago_cliente': None, 'carrito': [], 'df_proveedor': None
    })

# ==========================================
# 3. LOGIN (NOMBRE REAL + NEGOCIO)
# ==========================================
if not st.session_state['autenticado']:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        if os.path.exists(IMG_LOGIN): st.image(IMG_LOGIN, use_container_width=True)
        mostrar_titulo()
        
        negocio_input = st.text_input("Negocio (Ej: fabricon)").strip().lower()
        u_input = st.text_input("Nombre y Apellido").strip()
        c_input = st.text_input("Contraseña (DNI)", type="password").strip()
        
        if st.button("Ingresar", use_container_width=True, type="primary"):
            if negocio_input and u_input and c_input:
                query = db.collection("usuarios")\
                          .where("id_negocio", "==", negocio_input)\
                          .where("nombre", "==", u_input)\
                          .limit(1).get()
                
                if len(query) > 0:
                    doc = query[0]
                    d = doc.to_dict()
                    if str(d.get('password')) == c_input:
                        st.session_state.update({
                            'autenticado': True, 'usuario': doc.id, 
                            'rol': str(d.get('rol')).strip().lower(),
                            'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre'),
                            'id_usuario': doc.id, 'fecha_pago_cliente': d.get('promesa_pago', 'N/A')
                        })
                        st.rerun()
                    else: st.error("❌ DNI incorrecto")
                else: st.error("❌ Usuario no encontrado")

# ==========================================
# 4. INTERFAZ PRINCIPAL
# ==========================================
else:
    neg_id = st.session_state['id_negocio']
    nom_u = st.session_state['nombre_real']
    rol_u = st.session_state['rol']
    f_pago = st.session_state['fecha_pago_cliente']

    # --- SIDEBAR MEJORADA ---
    with st.sidebar:
        if os.path.exists(IMG_SIDEBAR): st.image(IMG_SIDEBAR, width=150)
        st.markdown(f"### 👤 {nom_u}")
        st.write(f"🏷️ **Rol:** {rol_u.capitalize()}")
        st.write(f"🏢 **Negocio:** {neg_u.upper() if 'neg_u' in locals() else neg_id.upper()}")
        
        if rol_u == "cliente":
            st.write(f"📅 **Fecha de pago:** {f_pago}")
            try:
                hoy = datetime.now()
                f_dt = datetime.strptime(f_pago, "%d/%m/%Y")
                dias = (f_dt - hoy).days
                if dias <= 5:
                    if dias >= 0: st.warning(f"⚠️ **Próximo a vencer** ({dias} días)")
                    else: st.error("🚨 **PAGO VENCIDO**")
            except: pass

        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True): 
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    mostrar_titulo()

    # --- VISTA CLIENTE ---
    if rol_u == "cliente":
        c_id = st.session_state['usuario']
        v_f = list(db.collection("ventas_procesadas").where("cliente_id", "==", c_id).where("metodo", "==", "Fiado").stream())
        p_f = list(db.collection("pagos_clientes").where("cliente_id", "==", c_id).stream())
        saldo = sum(v.to_dict().get('total', 0) for v in v_f) - sum(p.to_dict().get('monto', 0) for p in p_f)
        
        st.markdown(f"## Hola **{nom_u}**")
        st.error(f"# Tu saldo actual: ${saldo:,.2f}")

        # NOTA IMPORTANTE (RESTABLECIDA)
        with st.container(border=True):
            st.markdown(f"""
            ### 📝 Nota sobre tu cuenta:
            Usted se ha comprometido a cancelar el total de su deuda antes del día **{f_pago}**. 
            *   **Si cumple con el pago total:** Se le mantienen los precios originales de compra.
            *   **Si no cumple o deja saldo:** Los valores de los productos se actualizarán automáticamente según el precio de venta actual en el local.
            
            **Por favor, para mantener este beneficio, no deje saldo pendiente.**
            """)

        st.divider()
        st.subheader("📜 Detalle de Movimientos")
        # [Aquí continúa la lógica de movimientos (Compras y Pagos) en cuadros separados...]

    # --- VISTA DUEÑO ---
    elif rol_u == "negocio":
        tabs = st.tabs(["🛒 Ventas", "📉 Gastos", "📜 Historial", "👥 Clientes"])
        # [Aquí corre tu lógica de Dueño intacta...]
