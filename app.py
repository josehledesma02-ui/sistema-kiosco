import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import os

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="JL Gestión Pro", page_icon="🏢", layout="wide")

# 2. CONFIGURACIÓN DE LOGOS
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
        'autenticado': False, 'usuario': None, 'rol': None, 
        'id_negocio': None, 'nombre_real': None
    })

def cerrar_sesion():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- 🎨 INTERFAZ ---
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
        st.subheader("JL GESTIÓN")

# --- 🚪 PANTALLA DE INGRESO ---
if not st.session_state['autenticado']:
    c1, col_login, c3 = st.columns([1, 1.5, 1])
    with col_login:
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
                        'autenticado': True, 'usuario': u_input, 'rol': d.get('rol'), 
                        'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre')
                    })
                    st.rerun()
                else: st.error("❌ Contraseña incorrecta")
            else: st.error("❌ Usuario no encontrado")

# --- 🖥️ PANEL PRINCIPAL ---
else:
    rol = st.session_state['rol']
    negocio_id = st.session_state['id_negocio']
    nombre_pantalla = st.session_state['nombre_real'] or st.session_state['usuario']

    with st.sidebar:
        mostrar_logo_interfaz()
        st.write(f"👤 **{nombre_pantalla}**")
        st.caption(f"Rol: {rol.upper()} | Sucursal: {negocio_id.upper()}")
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True):
            cerrar_sesion()

    # ==========================================
    # 1. VISTA DUEÑO (ADMINISTRACIÓN TOTAL)
    # ==========================================
    if rol == "negocio":
        st.title(f"📊 Panel de Control: {negocio_id.upper()}")
        
        tabs = st.tabs(["💰 Cuentas Clientes", "📉 Gastos Propios", "🧾 Compras/Boletas", "📦 Inventario", "👥 Empleados"])

        # TAB: CLIENTES Y DEUDAS
        with tabs[0]:
            st.subheader("Deudas de Clientes (Cuentas Corrientes)")
            movs = db.collection("cuentas_corrientes").where("Negocio", "==", negocio_id).stream()
            df_v = pd.DataFrame([m.to_dict() for m in movs])
            if not df_v.empty:
                col1, col2 = st.columns(2)
                col1.metric("TOTAL A COBRAR", f"${df_v['Subtotal'].sum():,.2f}")
                col2.metric("CLIENTES ACTIVOS", len(df_v['Nombre_Cliente'].unique()))
                st.dataframe(df_v[['Fecha', 'Nombre_Cliente', 'Producto', 'Subtotal']], use_container_width=True)
            else: st.info("No hay deudas registradas.")

        # TAB: GASTOS DEL NEGOCIO
        with tabs[1]:
            st.subheader("Registrar Gastos Mensuales")
            with st.form("form_gastos", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                cat_gasto = c1.selectbox("Categoría", ["Alquiler", "Luz/Agua", "Sueldos", "Impuestos", "Otros"])
                desc_gasto = c2.text_input("Descripción")
                monto_gasto = c3.number_input("Importe $", min_value=0.0)
                if st.form_submit_button("Guardar Gasto"):
                    db.collection("gastos").add({
                        "id_negocio": negocio_id, "categoria": cat_gasto, 
                        "descripcion": desc_gasto, "monto": monto_gasto, 
                        "fecha": datetime.now().strftime("%d/%m/%Y")
                    })
                    st.success("Gasto registrado.")

        # TAB: COMPRAS A PROVEEDORES
        with tabs[2]:
            st.subheader("Carga de Boletas de Proveedores")
            with st.form("form_compras", clear_on_submit=True):
                c1, c2 = st.columns(2)
                prov = c1.text_input("Nombre del Proveedor")
                boleta = c2.text_input("N° de Boleta/Factura")
                monto_c = c1.number_input("Total $", min_value=0.0)
                estado_c = c2.selectbox("Estado de Pago", ["Pendiente", "Pagado"])
                if st.form_submit_button("Cargar Boleta"):
                    db.collection("compras_proveedores").add({
                        "id_negocio": negocio_id, "proveedor": prov, "boleta": boleta,
                        "monto": monto_c, "estado": estado_c, "fecha": datetime.now().strftime("%d/%m/%Y")
                    })
                    st.success("Compra cargada al sistema.")

        # TAB: INVENTARIO
        with tabs[3]:
            st.subheader("Gestión de Stock")
            # Simulación de Inventario (Se puede expandir con una colección 'productos')
            st.info("Aquí podrás ver el stock crítico y actualizar precios masivos próximamente.")

        # TAB: EMPLEADOS
        with tabs[4]:
            st.subheader("Alta de Personal")
            with st.form("nuevo_empleado"):
                e_user = st.text_input("Usuario (para login)").lower().strip()
                e_nom = st.text_input("Nombre Completo")
                e_pass = st.text_input("Contraseña")
                if st.form_submit_button("Crear Acceso Empleado"):
                    db.collection("usuarios").document(e_user).set({
                        "nombre": e_nom, "password": e_pass, 
                        "rol": "empleado", "id_negocio": negocio_id
                    })
                    st.success(f"Empleado {e_nom} habilitado.")

    # ==========================================
    # 2. VISTA EMPLEADO (VENTAS)
    # ==========================================
    elif rol == "empleado":
        st.title(f"🛒 Ventas: {negocio_id.upper()}")
        t1, t2 = st.tabs(["➕ Cargar Venta", "📜 Historial Hoy"])
        
        with t1:
            clientes_ref = db.collection("clientes").where("id_negocio", "==", negocio_id).stream()
            dict_cl = {c.to_dict()['nombre']: c.id for c in clientes_ref}
            if dict_cl:
                with st.form("venta_empleado", clear_on_submit=True):
                    cl_sel = st.selectbox("Cliente", list(dict_cl.keys()))
                    prod = st.text_input("Producto")
                    prec = st.number_input("Precio", min_value=0.0)
                    if st.form_submit_button("Confirmar Carga"):
                        db.collection("cuentas_corrientes").add({
                            "Cliente": dict_cl[cl_sel], "Nombre_Cliente": cl_sel,
                            "Producto": prod, "Subtotal": prec, "Negocio": negocio_id,
                            "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Timestamp": datetime.now()
                        })
                        st.success("Cargado!")
            else: st.warning("No hay clientes registrados.")

        with t2:
            m_hoy = db.collection("cuentas_corrientes").where("Negocio", "==", negocio_id).limit(10).stream()
            df_hoy = pd.DataFrame([m.to_dict() for m in m_hoy])
            if not df_hoy.empty: st.table(df_hoy[['Nombre_Cliente', 'Producto', 'Subtotal']])

    # ==========================================
    # 3. VISTA CLIENTE
    # ==========================================
    elif rol == "cliente":
        st.header(f"👋 Hola, {nombre_pantalla}")
        movs = db.collection("cuentas_corrientes").where("Cliente", "==", st.session_state['usuario']).stream()
        df_cli = pd.DataFrame([m.to_dict() for m in movs])
        if not df_cli.empty:
            st.metric("MI SALDO PENDIENTE", f"${df_cli['Subtotal'].sum():,.2f}")
            st.write("### Detalle de mis compras")
            st.dataframe(df_cli[['Fecha', 'Producto', 'Subtotal']], use_container_width=True)
        else: st.success("No tienes deudas pendientes.")

    # ==========================================
    # 4. VISTA SUPER ADMIN
    # ==========================================
    elif rol == "super_admin":
        st.title("⚙️ Configuración Global")
        # (Aquí puedes añadir la creación de nuevos negocios/dueños)
        st.write("Panel para JL Gestión Central")
