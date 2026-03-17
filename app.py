import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import os
from streamlit_cookies_manager import EncryptedCookieManager

# 1. CONFIGURACIÓN DE COOKIES (Versión 3 para asegurar limpieza total)
cookies = EncryptedCookieManager(password="ledesma_kiosco_secure_2026_trinidad")
if not cookies.ready():
    st.stop()

# 2. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Sistema Kiosco Ledesma", page_icon="static/images/favicon.jpg", layout="wide")

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

# --- 🚀 MOTOR DE CIERRE DE SESIÓN DEFINITIVO ---
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
    
    usuario_cookie = cookies.get("kiosco_ledesma_v3")
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

# --- PANTALLA DE INGRESO ---
if not st.session_state['autenticado']:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        ruta_logo = os.path.join("static", "images", "logo_principal.png")
        if os.path.exists(ruta_logo):
            st.image(ruta_logo, use_container_width=True)
    
    st.markdown("<h1 style='text-align: center;'>Acceso al Sistema</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #0055A4;'>Maxi Kiosco Ledesma</h3>", unsafe_allow_html=True)
    
    u_input = st.text_input("Usuario", key="user_login").strip()
    c_input = st.text_input("Contraseña / DNI", type="password", key="pass_login").strip()
    mantener_sesion = st.checkbox("Mantener mi sesión iniciada")
    
    if st.button("Ingresar", use_container_width=True):
        if u_input and c_input:
            try:
                user_ref = db.collection("usuarios").document(u_input).get()
                if user_ref.exists:
                    datos = user_ref.to_dict()
                    if str(datos.get('password')) == c_input:
                        st.session_state.update({
                            'autenticado': True, 
                            'usuario': u_input,
                            'rol': datos.get('rol'),
                            'id_negocio': datos.get('id_negocio'),
                            'nombre_real': datos.get('nombre')
                        })
                        if mantener_sesion:
                            cookies["kiosco_ledesma_v3"] = u_input
                            cookies.save()
                        st.rerun()
                    else:
                        st.error("❌ Contraseña incorrecta.")
                else:
                    st.error(f"❌ Usuario no encontrado.")
            except Exception as e:
                st.error(f"⚠️ Error al validar: {e}")

# --- PANTALLA PRINCIPAL ---
else:
    rol = st.session_state['rol']
    user = st.session_state['usuario']
    negocio = st.session_state['id_negocio']
    nombre_pantalla = st.session_state['nombre_real'] or user

    # SIDEBAR
    st.sidebar.image("static/images/logo_principal.png", width=100)
    st.sidebar.write(f"**Usuario:** {nombre_pantalla}")
    st.sidebar.write(f"**Rol:** {rol.upper()}")
    
    if st.sidebar.button("🔴 Cerrar Sesión", use_container_width=True):
        if "kiosco_ledesma_v3" in cookies:
            cookies.pop("kiosco_ledesma_v3")
            cookies.save()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.query_params["logout"] = "true"
        st.rerun()

    # --- VISTA CLIENTE (DETALLE COMPLETO) ---
    if rol == "cliente":
        c_izq, c_cen, c_der = st.columns([1, 2, 1])
        with c_cen:
            st.image("static/images/logo_principal.png", use_container_width=True)
            st.markdown(f"<h1 style='text-align: center;'>Hola, {nombre_pantalla}</h1>", unsafe_allow_html=True)
        
        st.divider()

        # Lógica de Fechas de Pago
        try:
            c_doc = db.collection("clientes").document(user).get().to_dict()
            if c_doc:
                fecha_pago_str = c_doc.get('Fecha_Acuerdo_Pago', "Consultar")
                hoy = datetime.now().date()
                f_pago = datetime.strptime(fecha_pago_str, "%d/%m/%Y").date()
                dias = (f_pago - hoy).days
                
                if 0 < dias <= 3:
                    st.warning(f"🕒 ¡Recordatorio! Faltan {dias} días para tu fecha de pago ({fecha_pago_str}).")
                elif dias == 0:
                    st.info(f"📆 ¡Hoy es tu fecha pactada de pago! Muchas gracias.")
                elif dias < 0:
                    st.error(f"❌ La fecha pactada ({fecha_pago_str}) ha vencido.")
                st.write(f"📅 Fecha pactada de pago: **{fecha_pago_str}**")
        except:
            st.write("📅 Fecha de pago: Consultar con José.")

        # Resumen de Saldo
        try:
            mov_ref = db.collection("cuentas_corrientes").where("Cliente", "==", user).stream()
            lista_movs = [m.to_dict() for m in mov_ref]
            if lista_movs:
                df = pd.DataFrame(lista_movs)
                total = pd.to_numeric(df['Subtotal']).sum()
                st.metric("TU SALDO PENDIENTE", f"${total:,.2f}")
                st.table(df[['Fecha', 'Producto', 'Cantidad', 'Subtotal']])
            else:
                st.success("🎉 ¡Estás al día!")
        except:
            st.error("Error al cargar movimientos.")

        st.divider()
        
        # --- AQUÍ ESTÁ EL BLOQUE CORREGIDO ---
        with st.expander("📝 Nota sobre la vigencia de los precios", expanded=True):
            st.info("""
            **Política de precios en Cuenta Corriente:**
            
            1. **Congelamiento:** Los precios de los productos se **congelan** al valor del día en que realizaste la compra.
            2. **Condición de Pago:** Este beneficio es válido únicamente si se respeta la **Fecha Pactada de Pago** que figura arriba.
            3. **Incumplimiento:** En caso de no cancelar la deuda en la fecha acordada, los precios de los productos pendientes se **actualizarán** automáticamente al valor del día de pago efectivo, reflejando cualquier aumento que haya sufrido la mercadería en el mostrador.
            
            *Agradecemos tu cumplimiento para poder mantener este servicio de cuenta corriente.*
            """)

    # Vistas Admin/Empleado se mantienen igual...
    elif rol == "super_admin":
        st.title("Panel de Administración General")
        st.write("Módulo de gestión de José Ledesma.")
