import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="JHL Gestión", page_icon="📊", layout="wide")

# 2. CONFIGURACIÓN DE LOGOS DESDE GITHUB
# Usuario: josehledesma02-ui | Repositorio: sistema-kiosco
GITHUB_BASE = "https://raw.githubusercontent.com/josehledesma02-ui/sistema-kiosco/main"
LOGO_SISTEMA = f"{GITHUB_BASE}/logo_principal.png"
LOGO_FABRICON = f"{GITHUB_BASE}/fabricon.png"

# 3. CONEXIÓN A FIREBASE
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
        'autenticado': False, 
        'usuario': None, 
        'rol': None, 
        'id_negocio': None,
        'nombre_real': None
    })

def cerrar_sesion():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- 🎨 FUNCIÓN PARA LOGO DINÁMICO ---
def mostrar_logo(ancho=200):
    # Si el logo no carga (URL rota), Streamlit mostrará un error amigable o nada
    try:
        if not st.session_state['autenticado']:
            st.image(LOGO_SISTEMA, width=ancho)
        else:
            negocio = st.session_state.get('id_negocio')
            if negocio == "fabricon":
                st.image(LOGO_FABRICON, width=ancho)
            else:
                st.image(LOGO_SISTEMA, width=ancho)
    except:
        st.subheader("JHL Gestión")

# --- PANTALLA DE INGRESO ---
if not st.session_state['autenticado']:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        mostrar_logo(ancho=250)
        st.markdown("<h4 style='text-align: center;'>Acceso JHL Gestión</h4>", unsafe_allow_html=True)
        
        u_input = st.text_input("Usuario", key="u_log").strip()
        c_input = st.text_input("Contraseña", type="password", key="p_log").strip()
        
        if st.button("Ingresar", use_container_width=True):
            if u_input and c_input:
                user_ref = db.collection("usuarios").document(u_input).get()
                if user_ref.exists:
                    d = user_ref.to_dict()
                    if str(d.get('password')) == c_input:
                        st.session_state.update({
                            'autenticado': True, 
                            'usuario': u_input,
                            'rol': d.get('rol'), 
                            'id_negocio': d.get('id_negocio'),
                            'nombre_real': d.get('nombre')
                        })
                        st.rerun()
                    else:
                        st.error("❌ Contraseña incorrecta")
                else:
                    st.error("❌ Usuario no encontrado")

# --- PANTALLA PRINCIPAL ---
else:
    rol = st.session_state['rol']
    nombre_pantalla = st.session_state['nombre_real'] or st.session_state['usuario']

    # SIDEBAR
    with st.sidebar:
        mostrar_logo(ancho=120)
        st.write(f"👤 **{nombre_pantalla}**")
        st.write(f"Rol: {rol.upper()}")
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True):
            cerrar_sesion()

    # --- 1. VISTA CLIENTE ---
    if rol == "cliente":
        c_izq, c_cen, c_der = st.columns([1, 2, 1])
        with c_cen:
            mostrar_logo(ancho=250)
            st.markdown(f"<h1 style='text-align: center;'>Hola, {nombre_pantalla}</h1>", unsafe_allow_html=True)
        
        st.divider()

        # Detalle de Saldo y Fechas
        try:
            user = st.session_state['usuario']
            c_doc = db.collection("clientes").document(user).get().to_dict()
            if c_doc:
                fecha_pago_str = c_doc.get('Fecha_Acuerdo_Pago', "Consultar")
                st.write(f"📅 Fecha pactada de pago: **{fecha_pago_str}**")
            
            mov_ref = db.collection("cuentas_corrientes").where("Cliente", "==", user).stream()
            lista_movs = [m.to_dict() for m in mov_ref]
            if lista_movs:
                df = pd.DataFrame(lista_movs)
                total = pd.to_numeric(df['Subtotal']).sum()
                st.metric("TU SALDO PENDIENTE", f"${total:,.2f}")
                st.table(df[['Fecha', 'Producto', 'Subtotal']])
            else:
                st.success("🎉 ¡No tenés deudas pendientes!")
        except:
            st.info("Cargando información de cuenta...")

        with st.expander("📝 Nota sobre la vigencia de los precios", expanded=True):
            st.info("""
            **Política de precios en Cuenta Corriente:**
            *   **Precios:** Se congelan al día de la compra.
            *   **Condición:** Respetar la **Fecha Pactada de Pago**.
            *   **Incumplimiento:** Los precios se actualizarán al valor del día de pago efectivo.
            """)

    # --- 2. VISTA SUPER ADMIN ---
    elif rol == "super_admin":
        st.title("Panel Administrativo")
        tab1, tab2 = st.tabs(["👥 Usuarios", "🏢 Negocios"])
        
        with tab1:
            st.subheader("Alta de Usuario")
            with st.form("crear_usuario"):
                new_id = st.text_input("Usuario ID (ej: jose01)")
                new_name = st.text_input("Nombre Completo")
                new_pass = st.text_input("Contraseña")
                new_rol = st.selectbox("Rol", ["cliente", "empleado", "super_admin"])
                new_neg = st.selectbox("Negocio", ["fabricon", "kiosco_trinidad", "otro"])
                if st.form_submit_button("Crear"):
                    db.collection("usuarios").document(new_id).set({
                        "nombre": new_name, "password": new_pass, "rol": new_rol, "id_negocio": new_neg
                    })
                    st.success(f"Usuario {new_id} creado con éxito.")

    # --- 3. VISTA EMPLEADO ---
    elif rol == "empleado":
        st.title("Terminal de Ventas")
        st.write(f"Negocio: **{st.session_state.get('id_negocio').upper()}**")
