import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import os
from streamlit_cookies_manager import EncryptedCookieManager

# 1. CONFIGURACIÓN DE COOKIES (Clave única para JHL Gestión)
cookies = EncryptedCookieManager(password="jhl_gestion_secure_key_2026")
if not cookies.ready():
    st.stop()

# 2. CONFIGURACIÓN DE PÁGINA (Nombre Neutral)
st.set_page_config(page_title="JHL Gestión", page_icon="📊", layout="wide")

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

# --- 🚀 MOTOR DE CIERRE DE SESIÓN (REFORZADO) ---
if st.query_params.get("logout") == "true":
    st.query_params.clear()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# 4. LÓGICA DE PERSISTENCIA Y SESIÓN
if 'autenticado' not in st.session_state:
    st.session_state.update({
        'autenticado': False, 
        'usuario': None, 
        'rol': None, 
        'id_negocio': None,
        'nombre_real': None
    })
    
    usuario_cookie = cookies.get("jhl_session_token")
    if usuario_cookie:
        try:
            doc = db.collection("usuarios").document(usuario_cookie).get()
            if doc.exists:
                datos = doc.to_dict()
                st.session_state.update({
                    'autenticado': True, 
                    'usuario': usuario_cookie,
                    'rol': datos.get('rol'),
                    'id_negocio': datos.get('id_negocio'),
                    'nombre_real': datos.get('nombre')
                })
        except:
            pass

# --- 🎨 FUNCIÓN PARA LOGO DINÁMICO ---
def mostrar_logo(ancho=200):
    if not st.session_state['autenticado']:
        ruta = "static/images/logo_sistema.png" # Logo genérico JHL
    else:
        negocio = st.session_state.get('id_negocio', 'sistema')
        ruta = f"static/images/{negocio}.png" # Logo del negocio específico
    
    if os.path.exists(ruta):
        st.image(ruta, width=ancho)
    else:
        st.subheader("JHL Gestión")

# --- PANTALLA DE INGRESO ---
if not st.session_state['autenticado']:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        mostrar_logo()
        st.markdown("<h2 style='text-align: center;'>Acceso al Sistema</h2>", unsafe_allow_html=True)
        
        u_input = st.text_input("Usuario", key="u_log").strip()
        c_input = st.text_input("Contraseña", type="password", key="p_log").strip()
        recordarme = st.checkbox("Mantener mi sesión iniciada")
        
        if st.button("Ingresar", use_container_width=True):
            if u_input and c_input:
                user_ref = db.collection("usuarios").document(u_input).get()
                if user_ref.exists:
                    d = user_ref.to_dict()
                    if str(d.get('password')) == c_input:
                        st.session_state.update({
                            'autenticado': True, 'usuario': u_input,
                            'rol': d.get('rol'), 'id_negocio': d.get('id_negocio'),
                            'nombre_real': d.get('nombre')
                        })
                        if recordarme:
                            cookies["jhl_session_token"] = u_input
                            cookies.save()
                        st.rerun()
                    else:
                        st.error("Contraseña incorrecta")
                else:
                    st.error("Usuario no encontrado")

# --- PANTALLA PRINCIPAL ---
else:
    rol = st.session_state['rol']
    user = st.session_state['usuario']
    nombre_pantalla = st.session_state['nombre_real'] or user

    # SIDEBAR NEUTRAL
    with st.sidebar:
        mostrar_logo(ancho=100)
        st.write(f"👤 **{nombre_pantalla}**")
        st.write(f"Rol: {rol.upper()}")
        st.divider()
        
        if st.button("🔴 Cerrar Sesión", use_container_width=True):
            if "jhl_session_token" in cookies:
                del cookies["jhl_session_token"]
                cookies.save()
            st.query_params["logout"] = "true"
            st.rerun()

    # --- VISTA CLIENTE ---
    if rol == "cliente":
        c_izq, c_cen, c_der = st.columns([1, 2, 1])
        with c_cen:
            mostrar_logo(ancho=250)
            st.markdown(f"<h1 style='text-align: center;'>Hola, {nombre_pantalla}</h1>", unsafe_allow_html=True)
        
        st.divider()

        # Fechas de Pago
        try:
            c_doc = db.collection("clientes").document(user).get().to_dict()
            if c_doc:
                fecha_pago_str = c_doc.get('Fecha_Acuerdo_Pago', "Consultar")
                hoy = datetime.now().date()
                f_pago = datetime.strptime(fecha_pago_str, "%d/%m/%Y").date()
                dias = (f_pago - hoy).days
                
                if 0 < dias <= 3:
                    st.warning(f"🕒 Faltan {dias} días para tu pago ({fecha_pago_str}).")
                elif dias == 0:
                    st.info(f"📆 ¡Hoy es tu fecha pactada de pago!")
                elif dias < 0:
                    st.error(f"❌ La fecha pactada ({fecha_pago_str}) ha vencido.")
                st.write(f"📅 Fecha pactada de pago: **{fecha_pago_str}**")
        except:
            st.write("📅 Fecha de pago: Consultar con administración.")

        # Detalle de Saldo
        try:
            mov_ref = db.collection("cuentas_corrientes").where("Cliente", "==", user).stream()
            lista_movs = [m.to_dict() for m in mov_ref]
            if lista_movs:
                df = pd.DataFrame(lista_movs)
                total = pd.to_numeric(df['Subtotal']).sum()
                st.metric("TU SALDO PENDIENTE", f"${total:,.2f}")
                st.table(df[['Fecha', 'Producto', 'Subtotal']])
            else:
                st.success("🎉 ¡Estás al día!")
        except:
            st.error("No se pudieron cargar los movimientos.")

        st.divider()

        # --- NOTA DE VIGENCIA COMPLETA ---
        with st.expander("📝 Nota sobre la vigencia de los precios", expanded=True):
            st.info("""
            **Política de precios en Cuenta Corriente:**
            
            1. **Congelamiento:** Los precios de los productos se **congelan** al valor del día en que realizaste la compra.
            2. **Condición de Pago:** Este beneficio es válido únicamente si se respeta la **Fecha Pactada de Pago** que figura arriba.
            3. **Incumplimiento:** En caso de no cancelar la deuda en la fecha acordada, los precios de los productos pendientes se **actualizarán** automáticamente al valor del día de pago efectivo, reflejando cualquier aumento que haya sufrido la mercadería en el mostrador.
            
            *Agradecemos tu cumplimiento para poder mantener este servicio de cuenta corriente.*
            """)

    # --- VISTA ADMIN ---
    elif rol == "super_admin":
        st.title("Panel de Administración Central - JHL Gestión")
        st.write("Bienvenido, José.")
        # Aquí irán los módulos de carga de usuarios y negocios
