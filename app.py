import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
# Importamos el gestor de cookies para mantener la sesión
from streamlit_cookies_manager import EncryptedCookieManager

# 1. CONFIGURACIÓN DE COOKIES (Clave de seguridad para recordar clientes)
cookies = EncryptedCookieManager(password="ledesma_kiosco_secure_2026_trinidad")
if not cookies.ready():
    st.stop()

# 2. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Maxi Kiosco Ledesma - Mi Cuenta", page_icon="static/images/favicon.jpg", layout="wide")

# 3. CONEXIÓN A GOOGLE SHEETS
try:
    alcance = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credenciales = ServiceAccountCredentials.from_json_keyfile_name("secretos.json", alcance)
    cliente = gspread.authorize(credenciales)
    mi_planilla = cliente.open("Gestion Maxi Kiosco")
except Exception as e:
    st.error("⚠️ Error de conexión con la base de datos. Reintentá en un momento.")
    st.stop()

# 4. LÓGICA DE PERSISTENCIA (MANTENER SESIÓN)
if 'autenticado' not in st.session_state:
    # Intentamos leer la cookie del navegador para ver si ya entró antes
    usuario_cookie = cookies.get("usuario_registrado")
    if usuario_cookie:
        try:
            hoja_c = mi_planilla.worksheet("CLIENTES_ESPECIALES")
            df_c = pd.DataFrame(hoja_c.get_all_records())
            match = df_c[df_c['Nombre'] == usuario_cookie]
            if not match.empty:
                st.session_state.update({
                    'autenticado': True, 
                    'usuario': usuario_cookie,
                    'fecha_pago': match.iloc[0]['Fecha_Acuerdo_Pago']
                })
            else:
                st.session_state.update({'autenticado': False, 'usuario': None})
        except:
            st.session_state.update({'autenticado': False, 'usuario': None})
    else:
        st.session_state.update({'autenticado': False, 'usuario': None})

# --- PANTALLA DE INGRESO (LOGIN) ---
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
    
    # OPCIÓN DE MANTENER SESIÓN
    mantener_sesion = st.checkbox("Mantener mi sesión iniciada")
    
    if st.button("Ver mi cuenta", use_container_width=True):
        try:
            hoja_c = mi_planilla.worksheet("CLIENTES_ESPECIALES")
            df_c = pd.DataFrame(hoja_c.get_all_records())
            match = df_c[(df_c['Nombre'] == u) & (df_c['DNI'].astype(str) == c)]
            
            if not match.empty:
                st.session_state.update({
                    'autenticado': True, 
                    'usuario': u,
                    'fecha_pago': match.iloc[0]['Fecha_Acuerdo_Pago']
                })
                # Si marcó la casilla, guardamos la cookie
                if mantener_sesion:
                    cookies["usuario_registrado"] = u
                    cookies.save()
                st.rerun()
            else: 
                st.error("❌ Los datos no coinciden. Verificalos con José.")
        except: 
            st.error("⚠️ No se pudo validar el usuario.")

# --- PANTALLA PRINCIPAL DEL CLIENTE ---
else:
    # Botón de salida: Borra la cookie para que pida datos la próxima vez
    if st.sidebar.button("Cerrar Sesión"):
        cookies.pop("usuario_registrado")
        cookies.save()
        st.session_state['autenticado'] = False
        st.rerun()

    # --- ENCABEZADO CENTRADO (MEJORADO) ---
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

    # 5. LÓGICA DE FECHAS
    hoy = datetime.now().date()
    try:
        f_pago = datetime.strptime(st.session_state['fecha_pago'], "%d/%m/%Y").date()
        dias_restantes = (f_pago - hoy).days
        
        if 0 < dias_restantes <= 3:
            st.warning(f"🕒 ¡Recordatorio! Faltan {dias_restantes} días para tu fecha de pago ({st.session_state['fecha_pago']}).")
        elif dias_restantes == 0:
            st.info(f"📆 ¡Hoy es tu fecha pactada de pago! Muchas gracias.")
        elif dias_restantes < 0:
            st.error(f"❌ La fecha pactada ({st.session_state['fecha_pago']}) ha vencido. Por favor, regularizá tu situación.")
        
        st.write(f"📅 Fecha pactada de pago: **{st.session_state['fecha_pago']}**")
    except:
        st.write("📅 Fecha de pago: Consultar con José.")

    st.divider()

    # 6. DETALLE DE CUENTA
    try:
        hoja_mov = mi_planilla.worksheet("CUENTAS_CORRIENTES")
        df_mov = pd.DataFrame(hoja_mov.get_all_records())
        mis_compras = df_mov[df_mov['Cliente'] == st.session_state['usuario']]
        
        if not mis_compras.empty:
            total_deuda = mis_compras['Subtotal'].sum()
            st.metric("TU SALDO PENDIENTE", f"${total_deuda:,.2f}")
            
            columnas = ['Fecha', 'Producto', 'Cantidad', 'Precio_Unitario', 'Subtotal']
            st.dataframe(mis_compras[columnas], use_container_width=True, hide_index=True)
        else:
            st.success("🎉 ¡Estás al día! No registrás deudas pendientes.")
    except:
        st.error("No se pudo cargar el historial de compras.")

    # 7. NOTA LEGAL
    st.divider()
    with st.expander("📝 Nota sobre la vigencia de los precios", expanded=True):
        st.info("""
        Los precios de los productos cargados a tu cuenta corriente se **congelan** al valor del día de la compra, **siempre y cuando se respete la fecha de pago pactada**.

        **Si cumplís:** Pagás el precio acordado originalmente.
                
        **Si incumplís:** Los precios se actualizarán al valor del día si hubo una suba de precios general.

        **Agradecemos tu cumplimiento para poder mantenerte este beneficio.**
        """)