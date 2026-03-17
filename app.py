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
st.set_page_config(page_title="Maxi Kiosco Ledesma - Mi Cuenta", page_icon="static/images/favicon.jpg", layout="wide")

# 3. CONEXIÓN A FIREBASE (Adaptada para PC y Nube con limpieza de llave)
if not firebase_admin._apps:
    try:
        if "firebase" in st.secrets:
            # Si estamos en la nube (Streamlit Cloud)
            creds_dict = dict(st.secrets["firebase"])
            # ESTA LÍNEA ES CLAVE: Limpia los saltos de línea de la llave privada
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(creds_dict)
        else:
            # Si estamos en tu computadora local
            cred = credentials.Certificate("secretos.json")
            
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"⚠️ Error de conexión: {e}")
        st.stop()

db = firestore.client()

# 4. LÓGICA DE PERSISTENCIA (Firebase)
if 'autenticado' not in st.session_state:
    usuario_cookie = cookies.get("usuario_registrado")
    if usuario_cookie:
        try:
            # Buscamos en la colección "clientes"
            doc = db.collection("clientes").document(usuario_cookie).get()
            if doc.exists:
                datos = doc.to_dict()
                st.session_state.update({
                    'autenticado': True, 
                    'usuario': usuario_cookie,
                    'fecha_pago': datos.get('Fecha_Acuerdo_Pago')
                })
            else:
                st.session_state.update({'autenticado': False, 'usuario': None})
        except:
            st.session_state.update({'autenticado': False, 'usuario': None})
    else:
        st.session_state.update({'autenticado': False, 'usuario': None})

# --- PANTALLA DE INGRESO ---
if not st.session_state['autenticado']:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        ruta_logo = os.path.join("static", "images", "logo_principal.png")
        if os.path.exists(ruta_logo):
            st.image(ruta_logo, use_container_width=True)
    
    st.markdown("<h1 style='text-align: center;'>Maxi Kiosco Ledesma</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #0055A4;'>Ingresá tus datos para ver tu cuenta</h3>", unsafe_allow_html=True)
    
    u = st.text_input("Nombre de Usuario")
    c = st.text_input("DNI (Contraseña)", type="password")
    mantener_sesion = st.checkbox("Mantener mi sesión iniciada")
    
    if st.button("Ver mi cuenta", use_container_width=True):
        try:
            # Buscamos el cliente por ID (su nombre)
            cliente_ref = db.collection("clientes").document(u).get()
            
            if cliente_ref.exists:
                datos = cliente_ref.to_dict()
                # Verificamos DNI (asegurando que sea string para comparar)
                if str(datos.get('DNI')) == c:
                    st.session_state.update({
                        'autenticado': True, 
                        'usuario': u,
                        'fecha_pago': datos.get('Fecha_Acuerdo_Pago')
                    })
                    if mantener_sesion:
                        cookies["usuario_registrado"] = u
                        cookies.save()
                    st.rerun()
                else:
                    st.error("❌ Los datos no coinciden. Verificalos con José.")
            else:
                st.error("❌ Usuario no encontrado.")
        except: 
            st.error("⚠️ Error al validar.")

# --- PANTALLA PRINCIPAL DEL CLIENTE ---
else:
    if st.sidebar.button("Cerrar Sesión"):
        cookies.pop("usuario_registrado")
        cookies.save()
        st.session_state['autenticado'] = False
        st.rerun()

    # --- ENCABEZADO CENTRADO ---
    c_izq, c_cen, c_der = st.columns([1, 2, 1])
    with c_cen:
        st.image("static/images/logo_principal.png", use_container_width=True)
        st.markdown(f"""
            <div style='text-align: center;'>
                <h1 style='margin-bottom: 0;'>Hola, {st.session_state['usuario']}</h1>
                <h3 style='color: #0055A4; margin-top: 0;'>Maxi Kiosco Ledesma - Tu Libreta Virtual</h3>
            </div>
            """, unsafe_allow_html=True)
    
    st.divider()

    # 5. LÓGICA DE FECHAS (Idéntica a la tuya)
    hoy = datetime.now().date()
    try:
        f_pago = datetime.strptime(st.session_state['fecha_pago'], "%d/%m/%Y").date()
        dias_restantes = (f_pago - hoy).days
        if 0 < dias_restantes <= 3:
            st.warning(f"🕒 ¡Recordatorio! Faltan {dias_restantes} días para tu fecha de pago ({st.session_state['fecha_pago']}).")
        elif dias_restantes == 0:
            st.info(f"📆 ¡Hoy es tu fecha pactada de pago! Muchas gracias.")
        elif dias_restantes < 0:
            st.error(f"❌ La fecha pactada ({st.session_state['fecha_pago']}) ha vencido.")
        st.write(f"📅 Fecha pactada de pago: **{st.session_state['fecha_pago']}**")
    except:
        st.write("📅 Fecha de pago: Consultar con José.")

    st.divider()

    # 6. DETALLE DE CUENTA (Cambiado a st.table para que NO se pueda descargar)
    try:
        mov_ref = db.collection("cuentas_corrientes").where("Cliente", "==", st.session_state['usuario']).stream()
        lista_movs = [m.to_dict() for m in mov_ref]
        
        if lista_movs:
            df_mov = pd.DataFrame(lista_movs)
            df_mov['Subtotal'] = pd.to_numeric(df_mov['Subtotal'])
            total_deuda = df_mov['Subtotal'].sum()
            
            st.metric("TU SALDO PENDIENTE", f"${total_deuda:,.2f}")
            
            # Ordenamos las columnas para que se vea prolijo
            columnas = ['Fecha', 'Producto', 'Cantidad', 'Precio_Unitario', 'Subtotal']
            cols_mostrar = [c for c in columnas if c in df_mov.columns]
            
            # IMPORTANTE: Usamos st.table para eliminar la opción de descarga
            st.table(df_mov[cols_mostrar])
        else:
            st.success("🎉 ¡Estás al día! No registrás deudas pendientes.")
    except Exception as e:
        st.error(f"No se pudo cargar el historial: {e}"
                )

    # 7. NOTA LEGAL (Aseguramos que esté al final de todo)
    st.divider()
    with st.expander("📝 Nota sobre la vigencia de los precios", expanded=True):
        st.info("""
        Los precios se **congelan** al valor del día de la compra, siempre y cuando se respete la fecha de pago pactada.
        
        **Si cumplís:** Pagás el precio acordado originalmente.
                
        **Si incumplís:** Los precios se actualizarán al valor del día si hubo una suba de precios general.
        """)
