import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import os

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="JL Gestión", page_icon="📊", layout="wide")

# 2. CONFIGURACIÓN DE LOGOS (RUTAS LOCALES)
LOGO_SISTEMA = "static/images/logo_principal.png"
LOGO_FABRICON = "static/images/fabricon.png"

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

# --- 🎨 FUNCIÓN PARA LOGO (SIDEBAR O LOGIN) ---
def mostrar_logo_interfaz(login=False):
    negocio = st.session_state.get('id_negocio')
    ruta = LOGO_FABRICON if negocio == "fabricon" else LOGO_SISTEMA
    
    if os.path.exists(ruta):
        if login:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2: st.image(ruta, use_container_width=True)
        else:
            st.image(ruta, use_container_width=True)
    else:
        texto = "FABRICÓN" if negocio == "fabricon" else "JL GESTIÓN"
        st.subheader(texto)

# --- 🚪 PANTALLA DE INGRESO ---
if not st.session_state['autenticado']:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        mostrar_logo_interfaz(login=True)
        st.markdown("<h3 style='text-align: center;'>Iniciar Sesión</h3>", unsafe_allow_html=True)
        u_input = st.text_input("Usuario").strip().lower()
        c_input = st.text_input("Contraseña", type="password").strip()
        if st.button("Ingresar", use_container_width=True):
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
                else: st.error("❌ Contraseña incorrecta")
            else: st.error("❌ Usuario no encontrado")

# --- 🖥️ PANEL PRINCIPAL ---
else:
    rol = st.session_state['rol']
    negocio_actual = st.session_state['id_negocio']
    nombre_pantalla = st.session_state['nombre_real'] or st.session_state['usuario']

    # --- BARRA LATERAL ---
    with st.sidebar:
        mostrar_logo_interfaz() 
        st.write(f"👤 **{nombre_pantalla}**")
        st.caption(f"Sucursal: {negocio_actual.upper()}")
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True):
            cerrar_sesion()

    # --- 🟢 VISTA EMPLEADO (PUNTO DE VENTA) ---
    if rol == "empleado":
        st.markdown(f"# 🛒 Sistema de Ventas: {negocio_actual.upper()}")
        
        # DISEÑO DE PESTAÑAS TIPO PROGRAMA
        tab_venta, tab_anular, tab_caja = st.tabs(["➕ Nueva Venta", "❌ Historial y Anular", "📊 Resumen Diario"])

        # --- PESTAÑA 1: CARGA DE VENTAS ---
        with tab_venta:
            st.subheader("Registrar Consumo de Cliente")
            clientes_ref = db.collection("clientes").where("id_negocio", "==", negocio_actual).stream()
            dict_cl = {c.to_dict()['nombre']: c.id for c in clientes_ref}
            
            if dict_cl:
                with st.form("venta_rapida", clear_on_submit=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        cl_sel = st.selectbox("Seleccionar Cliente", list(dict_cl.keys()))
                        prod = st.text_input("Producto / Concepto", placeholder="Ej: Coca Cola 1.5L")
                    with col_b:
                        prec = st.number_input("Precio Unitario", min_value=0.0, step=50.0)
                        cant = st.number_input("Cantidad", min_value=1, value=1)
                    
                    if st.form_submit_button("🚀 Confirmar Venta", use_container_width=True):
                        if prod and prec > 0:
                            # Guardamos la venta
                            db.collection("cuentas_corrientes").add({
                                "Cliente": dict_cl[cl_sel],
                                "Nombre_Cliente": cl_sel,
                                "Producto": prod,
                                "Subtotal": float(prec * cant),
                                "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                                "Negocio": negocio_actual,
                                "Timestamp": datetime.now() # Para ordenar por tiempo
                            })
                            st.success(f"✅ Registrado: {cant}x {prod} para {cl_sel}")
                            st.rerun()
            else:
                st.warning("No hay clientes registrados en este negocio.")

        # --- PESTAÑA 2: HISTORIAL Y ANULACIÓN ---
        with tab_anular:
            st.subheader("Últimos movimientos")
            st.write("Si hubo un error o rotura, podés eliminar la venta aquí.")
            
            # Traer últimos 15 movimientos
            m_ref = db.collection("cuentas_corrientes")\
                      .where("Negocio", "==", negocio_actual)\
                      .order_by("Timestamp", direction=firestore.Query.DESCENDING)\
                      .limit(15).stream()
            
            movs_lista = []
            for m in m_ref:
                d = m.to_dict()
                d['id_doc'] = m.id # Necesitamos el ID para borrar
                movs_lista.append(d)
            
            if movs_lista:
                df_historial = pd.DataFrame(movs_lista)
                st.dataframe(df_historial[['Fecha', 'Nombre_Cliente', 'Producto', 'Subtotal']], use_container_width=True)
                
                st.divider()
                st.markdown("### 🛠️ Anular Operación")
                # Creamos una lista amigable para el selector de borrar
                opciones_anular = {f"{m['Fecha']} | {m['Nombre_Cliente']} | {m['Producto']} (${m['Subtotal']})": m['id_doc'] for m in movs_lista}
                
                seleccion_borrar = st.selectbox("Seleccione la venta a ELIMINAR:", ["---"] + list(opciones_anular.keys()))
                motivo = st.text_input("Motivo de la anulación (Ej: Producto roto)")

                if st.button("❌ Eliminar Venta Permanentemente", type="primary", use_container_width=True):
                    if seleccion_borrar != "---" and motivo:
                        id_para_borrar = opciones_anular[seleccion_borrar]
                        db.collection("cuentas_corrientes").document(id_para_borrar).delete()
                        st.error(f"Operación Anulada: {seleccion_borrar}")
                        st.rerun()
                    else:
                        st.warning("Seleccioná una venta y escribí un motivo.")
            else:
                st.info("No hay ventas registradas recientemente.")

        # --- PESTAÑA 3: RESUMEN (CIERRE DE CAJA) ---
        with tab_caja:
            st.subheader("Resumen de hoy")
            hoy = datetime.now().strftime("%d/%m/%Y")
            
            # Filtramos solo lo de hoy de la lista que ya trajimos (o pedimos de nuevo si preferís)
            ventas_hoy = [v for v in movs_lista if hoy in v['Fecha']]
            
            if ventas_hoy:
                df_hoy = pd.DataFrame(ventas_hoy)
                total_dia = df_hoy['Subtotal'].sum()
                st.metric("Total Vendido Hoy (Cuentas Corrientes)", f"${total_dia:,.2f}")
                st.table(df_hoy[['Nombre_Cliente', 'Producto', 'Subtotal']])
            else:
                st.info("Todavía no se registraron ventas hoy.")

    # --- RESTO DE ROLES (Resumidos para el código completo) ---
    elif rol == "cliente":
        st.markdown(f"## Hola, {nombre_pantalla}")
        # (Aquí iría tu lógica de cliente que ya tenías)

    elif rol == "negocio":
        st.title(f"📊 Dashboard: {negocio_actual.upper()}")
        # (Aquí iría tu lógica de dueño que ya tenías)

    elif rol == "super_admin":
        st.title("⚙️ Administración Central")
        # (Aquí iría tu lógica de creación de usuarios)
