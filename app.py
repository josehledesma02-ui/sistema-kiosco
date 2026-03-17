import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import os
from streamlit_cookies_manager import EncryptedCookieManager

# 1. CONFIGURACIÓN DE COOKIES
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

# 4. LÓGICA DE PERSISTENCIA Y SESIÓN
if 'autenticado' not in st.session_state:
    st.session_state.update({
        'autenticado': False, 
        'usuario': None, 
        'rol': None, 
        'id_negocio': None,
        'nombre_real': None
    })
    
    usuario_cookie = cookies.get("usuario_registrado")
    if usuario_cookie:
        try:
            # Ahora buscamos en la nueva colección "usuarios" para la persistencia
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
    
    u = st.text_input("Usuario")
    c = st.text_input("Contraseña / DNI", type="password")
    mantener_sesion = st.checkbox("Mantener mi sesión iniciada")
    
    if st.button("Ingresar", use_container_width=True):
        try:
            # BUSQUEDA MULTI-ROL en la colección 'usuarios'
            user_ref = db.collection("usuarios").document(u).get()
            
            if user_ref.exists:
                datos = user_ref.to_dict()
                if str(datos.get('password')) == c:
                    st.session_state.update({
                        'autenticado': True, 
                        'usuario': u,
                        'rol': datos.get('rol'),
                        'id_negocio': datos.get('id_negocio'),
                        'nombre_real': datos.get('nombre')
                    })
                    if mantener_sesion:
                        cookies["usuario_registrado"] = u
                        cookies.save()
                    st.rerun()
                else:
                    st.error("❌ Contraseña incorrecta.")
            else:
                st.error("❌ Usuario no encontrado.")
        except Exception as e:
            st.error(f"⚠️ Error al validar: {e}")

# --- PANTALLA PRINCIPAL (LOGICA DE ROLES) ---
else:
    rol = st.session_state['rol']
    user = st.session_state['usuario']
    negocio = st.session_state['id_negocio']

    # BARRA LATERAL
    st.sidebar.image("static/images/logo_principal.png", width=100)
    st.sidebar.write(f"**Usuario:** {user}")
    st.sidebar.write(f"**Rol:** {rol.upper()}")
    
    if st.sidebar.button("Cerrar Sesión"):
        cookies.pop("usuario_registrado")
        cookies.save()
        st.session_state.clear()
        st.rerun()

    # ---------------------------------------------------------
    # VISTA 1: SUPER ADMIN (JOSÉ)
    # ---------------------------------------------------------
    if rol == "super_admin":
        st.title(f"🏗️ Panel Global: {st.session_state['nombre_real']}")
        st.info("Sos el administrador de toda la plataforma.")
        tab1, tab2, tab3 = st.tabs(["📊 Estadísticas", "🏪 Negocios", "🚚 Proveedores"])
        
        with tab1:
            st.write("Acá verás el resumen de todos los negocios que usen tu app.")

    # ---------------------------------------------------------
    # VISTA 2: EMPLEADO
    # ---------------------------------------------------------
    elif rol == "empleado":
        st.title(f"🏪 Terminal de Empleado: {st.session_state['nombre_real']}")
        st.subheader(f"Negocio: {negocio}")
        
        t_venta, t_cuenta = st.tabs(["Vender", "Mi Asistencia y Vales"])
        with t_cuenta:
            st.write("⏱️ Próximamente: Botones para marcar entrada y salida.")
            st.write("🛒 Próximamente: Detalle de mercadería retirada.")

    # ---------------------------------------------------------
    # VISTA 3: CLIENTE (TU CÓDIGO ORIGINAL FUSIONADO)
    # ---------------------------------------------------------
    elif rol == "cliente":
        # Encabezado centrado
        c_izq, c_cen, c_der = st.columns([1, 2, 1])
        with c_cen:
            st.image("static/images/logo_principal.png", use_container_width=True)
            st.markdown(f"<div style='text-align: center;'><h1 style='margin-bottom: 0;'>Hola, {user}</h1></div>", unsafe_allow_html=True)
        
        st.divider()

        # Lógica de fechas
        try:
            # Nota: Para el cliente, buscamos sus datos de pago en la colección 'clientes'
            c_doc = db.collection("clientes").document(user).get().to_dict()
            fecha_pago_str = c_doc.get('Fecha_Acuerdo_Pago', "Consultar")
            
            hoy = datetime.now().date()
            f_pago = datetime.strptime(fecha_pago_str, "%d/%m/%Y").date()
            dias_restantes = (f_pago - hoy).days
            
            if 0 < dias_restantes <= 3:
                st.warning(f"🕒 ¡Recordatorio! Faltan {dias_restantes} días para tu fecha de pago ({fecha_pago_str}).")
            elif dias_restantes == 0:
                st.info(f"📆 ¡Hoy es tu fecha pactada de pago! Muchas gracias.")
            elif dias_restantes < 0:
                st.error(f"❌ La fecha pactada ({fecha_pago_str}) ha vencido.")
            st.write(f"📅 Fecha pactada de pago: **{fecha_pago_str}**")
        except:
            st.write("📅 Fecha de pago: Consultar con José.")

        st.divider()

        # Detalle de cuenta
        try:
            mov_ref = db.collection("cuentas_corrientes").where("Cliente", "==", user).stream()
            lista_movs = [m.to_dict() for m in mov_ref]
            
            if lista_movs:
                df_mov = pd.DataFrame(lista_movs)
                df_mov['Subtotal'] = pd.to_numeric(df_mov['Subtotal'])
                total_deuda = df_mov['Subtotal'].sum()
                st.metric("TU SALDO PENDIENTE", f"${total_deuda:,.2f}")
                columnas = ['Fecha', 'Producto', 'Cantidad', 'Precio_Unitario', 'Subtotal']
                cols_mostrar = [c for c in columnas if c in df_mov.columns]
                st.table(df_mov[cols_mostrar])
            else:
                st.success("🎉 ¡Estás al día! No registrás deudas pendientes.")
        except Exception as e:
            st.error(f"No se pudo cargar el historial: {e}")

        # Nota Legal
        st.divider()
        with st.expander("📝 Nota sobre la vigencia de los precios", expanded=True):
            st.info("""
            Los precios se **congelan** al valor del día de la compra, siempre y cuando se respete la fecha de pago pactada.
            
            **Si cumplís:** Pagás el precio acordado originalmente.
            **Si incumplís:** Los precios se actualizarán al valor del día si hubo una suba de precios general.
            """)
