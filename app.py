import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="JL Gestión", page_icon="📊", layout="wide")

# 2. CONFIGURACIÓN DE LOGOS (GitHub)
USER = "josehledesma02-ui"
REPO = "sistema-kiosco"
BRANCH = "main"
URL_BASE = f"https://raw.githubusercontent.com/{USER}/{REPO}/{BRANCH}/static/images"

LOGO_SISTEMA = f"{URL_BASE}/logo_principal.png"
LOGO_FABRICON = f"{URL_BASE}/fabricon.png"

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
def mostrar_logo(ancho=250, centrar=False):
    logo_url = LOGO_SISTEMA
    if st.session_state.get('autenticado') and st.session_state.get('id_negocio') == "fabricon":
        logo_url = LOGO_FABRICON
    
    if centrar:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(logo_url, use_container_width=True)
    else:
        st.image(logo_url, width=ancho)

# --- PANTALLA DE INGRESO ---
if not st.session_state['autenticado']:
    st.write("") 
    c1, c2, c3 = st.columns([1, 2, 1])
    
    with c2:
        mostrar_logo(centrar=True)
        st.markdown("<h2 style='text-align: center;'>Acceso JL GESTIÓN</h2>", unsafe_allow_html=True)
        st.write("") 
        
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

# --- PANTALLA PRINCIPAL (LOGUEADO) ---
else:
    rol = st.session_state['rol']
    negocio_actual = st.session_state['id_negocio']
    nombre_pantalla = st.session_state['nombre_real'] or st.session_state['usuario']

    # SIDEBAR
    with st.sidebar:
        mostrar_logo(ancho=150)
        st.write(f"👤 **{nombre_pantalla}**")
        st.write(f"Rol: {rol.upper()}")
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True):
            cerrar_sesion()

    # --- 1. VISTA CLIENTE ---
    if rol == "cliente":
        c_izq, c_cen, c_der = st.columns([1, 2, 1])
        with c_cen:
            mostrar_logo(centrar=True)
            st.markdown(f"<h1 style='text-align: center;'>Hola, {nombre_pantalla}</h1>", unsafe_allow_html=True)
        
        st.divider()
        try:
            user = st.session_state['usuario']
            c_doc = db.collection("clientes").document(user).get().to_dict()
            if c_doc:
                st.write(f"📅 Fecha pactada de pago: **{c_doc.get('Fecha_Acuerdo_Pago', 'Consultar')}**")
            
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

    # --- 2. VISTA SUPER ADMIN ---
    elif rol == "super_admin":
        st.title("Panel Administrativo")
        tab1, tab2 = st.tabs(["👥 Usuarios", "🏢 Negocios"])
        
        with tab1:
            st.subheader("Alta de Usuario")
            with st.form("crear_usuario", clear_on_submit=True):
                col_a, col_b = st.columns(2)
                new_id = col_a.text_input("Usuario ID (ej: jose01)").strip().lower()
                new_name = col_a.text_input("Nombre Completo")
                new_pass = col_b.text_input("Contraseña", type="password")
                new_rol = col_b.selectbox("Rol", ["cliente", "empleado", "proveedor", "negocio"])
                new_neg = st.selectbox("Negocio", ["fabricon", "kiosco_trinidad", "otro"])
                
                st.caption("Si es cliente:")
                f_pago = st.text_input("Fecha Pactada de Pago", value="05 de cada mes")
                
                if st.form_submit_button("Registrar"):
                    if new_id and new_pass:
                        # Registro en usuarios
                        db.collection("usuarios").document(new_id).set({
                            "nombre": new_name, "password": new_pass, "rol": new_rol, "id_negocio": new_neg
                        })
                        # Si es cliente, creamos su ficha técnica
                        if new_rol == "cliente":
                            db.collection("clientes").document(new_id).set({
                                "nombre": new_name, "Fecha_Acuerdo_Pago": f_pago, "id_negocio": new_neg
                            })
                        st.success(f"✅ Usuario {new_id} creado.")

    # --- 3. VISTA EMPLEADO ---
    elif rol == "empleado":
        st.title("🛒 Terminal de Ventas")
        st.write(f"Punto de Venta: **{negocio_actual.upper()}**")
        
        # Obtener lista de clientes del negocio para el selector
        clientes_ref = db.collection("clientes").where("id_negocio", "==", negocio_actual).stream()
        dict_clientes = {c.to_dict()['nombre']: c.id for c in clientes_ref}
        
        if not dict_clientes:
            st.warning("No hay clientes registrados en este negocio.")
        else:
            with st.form("nueva_venta", clear_on_submit=True):
                st.subheader("Cargar Producto a Cuenta Corriente")
                cliente_sel = st.selectbox("Seleccionar Cliente", options=list(dict_clientes.keys()))
                producto = st.text_input("Producto / Concepto")
                precio = st.number_input("Precio ($)", min_value=0.0, step=100.0)
                cantidad = st.number_input("Cantidad", min_value=1, value=1)
                
                if st.form_submit_button("Confirmar Venta"):
                    if producto and precio > 0:
                        nueva_venta = {
                            "Cliente": dict_clientes[cliente_sel],
                            "Producto": producto,
                            "Precio_Unitario": precio,
                            "Cantidad": cantidad,
                            "Subtotal": precio * cantidad,
                            "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Negocio": negocio_actual
                        }
                        db.collection("cuentas_corrientes").add(nueva_venta)
                        st.success(f"✅ Venta cargada a {cliente_sel}")
                    else:
                        st.error("Completa el producto y el precio.")
