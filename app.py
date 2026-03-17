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
        'id_negocio': None, 'nombre_real': None, 'permisos': 'todo'
    })

def cerrar_sesion():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

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
        st.markdown("<h3 style='text-align: center;'>Panel de Control</h3>", unsafe_allow_html=True)
        u_input = st.text_input("Usuario").strip().lower()
        c_input = st.text_input("Contraseña", type="password").strip()
        if st.button("Ingresar al Sistema", use_container_width=True):
            user_ref = db.collection("usuarios").document(u_input).get()
            if user_ref.exists:
                d = user_ref.to_dict()
                if str(d.get('password')) == c_input:
                    st.session_state.update({
                        'autenticado': True, 'usuario': u_input, 'rol': d.get('rol'), 
                        'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre'),
                        'permisos': d.get('permisos', 'todo')
                    })
                    st.rerun()
                else: st.error("❌ Contraseña incorrecta")
            else: st.error("❌ Usuario no encontrado")

# --- 🖥️ PANEL PRINCIPAL ---
else:
    rol = st.session_state['rol']
    permisos = st.session_state['permisos']
    negocio_id = st.session_state['id_negocio']
    nombre_pantalla = st.session_state['nombre_real'] or st.session_state['usuario']

    with st.sidebar:
        mostrar_logo_interfaz()
        st.write(f"👤 **{nombre_pantalla}**")
        st.caption(f"Sucursal: {negocio_id.upper()}")
        if rol == "empleado":
            st.info(f"Acceso: {permisos.upper()}")
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True):
            cerrar_sesion()

    # ==========================================
    # 🏢 VISTA DUEÑO / ENCARGADO / EMPLEADO
    # ==========================================
    if rol in ["negocio", "empleado"]:
        
        # Definir qué pestañas ve cada uno según su permiso
        todas_las_tabs = ["💰 Ventas", "📉 Gastos", "🧾 Compras", "📦 Stock", "👥 Personal"]
        
        # Filtrado lógico de pestañas
        if rol == "negocio" or permisos == "encargado":
            tabs = st.tabs(todas_las_tabs)
        elif permisos == "cajero":
            tabs = st.tabs(["💰 Ventas"])
        elif permisos == "repositor":
            tabs = st.tabs(["📦 Stock", "🧾 Compras"])
        else:
            tabs = st.tabs(["Información"])

        # --- 1. SECCIÓN VENTAS (Cajero, Encargado, Dueño) ---
        if rol == "negocio" or permisos in ["encargado", "cajero"]:
            with tabs[0]:
                st.subheader("Punto de Venta y Cuentas Corrientes")
                
                # Formulario de Venta
                clientes_ref = db.collection("clientes").where("id_negocio", "==", negocio_id).stream()
                dict_cl = {c.to_dict()['nombre']: c.id for c in clientes_ref}
                
                with st.expander("➕ Registrar Nueva Venta", expanded=True):
                    if dict_cl:
                        with st.form("form_venta", clear_on_submit=True):
                            c1, c2 = st.columns(2)
                            cliente_sel = c1.selectbox("Cliente", list(dict_cl.keys()))
                            producto = c2.text_input("Producto/Servicio")
                            precio = c1.number_input("Precio $", min_value=0.0, step=100.0)
                            cantidad = c2.number_input("Cantidad", min_value=1, value=1)
                            if st.form_submit_button("Confirmar Venta"):
                                db.collection("cuentas_corrientes").add({
                                    "Cliente": dict_cl[cliente_sel], "Nombre_Cliente": cliente_sel,
                                    "Producto": producto, "Subtotal": precio * cantidad,
                                    "Negocio": negocio_id, "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                                    "Timestamp": datetime.now()
                                })
                                st.success("Venta registrada con éxito")
                    else: st.warning("No hay clientes cargados.")

                # Tabla de Deudas
                st.divider()
                st.write("### Deudas Activas")
                movs = db.collection("cuentas_corrientes").where("Negocio", "==", negocio_id).order_by("Timestamp", direction=firestore.Query.DESCENDING).limit(50).stream()
                df_v = pd.DataFrame([m.to_dict() for m in movs])
                if not df_v.empty:
                    st.dataframe(df_v[['Fecha', 'Nombre_Cliente', 'Producto', 'Subtotal']], use_container_width=True)
                    st.metric("Total en la calle", f"${df_v['Subtotal'].sum():,.2f}")

        # --- 2. SECCIÓN GASTOS (Dueño, Encargado) ---
        if rol == "negocio" or permisos == "encargado":
            with tabs[1]:
                st.subheader("Gastos del Negocio (Luz, Alquiler, Sueldos)")
                with st.form("form_gastos", clear_on_submit=True):
                    c1, c2, c3 = st.columns(3)
                    cat = c1.selectbox("Tipo", ["Alquiler", "Luz", "Sueldos", "Mercadería", "Otros"])
                    det = c2.text_input("Detalle")
                    mon = c3.number_input("Monto $", min_value=0.0)
                    if st.form_submit_button("Cargar Gasto"):
                        db.collection("gastos").add({
                            "id_negocio": negocio_id, "categoria": cat, "detalle": det,
                            "monto": mon, "fecha": datetime.now().strftime("%d/%m/%Y")
                        })
                        st.success("Gasto guardado")

        # --- 3. SECCIÓN COMPRAS / PROVEEDORES ---
        if rol == "negocio" or permisos in ["encargado", "repositor"]:
            t_idx = 2 if (rol == "negocio" or permisos == "encargado") else 1
            with tabs[t_idx]:
                st.subheader("Compras a Proveedores / Boletas")
                with st.form("form_compras", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    proveedor = c1.text_input("Proveedor")
                    boleta_n = c2.text_input("N° de Factura")
                    importe = c1.number_input("Total Factura $", min_value=0.0)
                    estado_p = c2.selectbox("Estado", ["Pendiente", "Pagado"])
                    if st.form_submit_button("Cargar Boleta"):
                        db.collection("compras_negocio").add({
                            "id_negocio": negocio_id, "proveedor": proveedor, 
                            "boleta": boleta_n, "monto": importe, "estado": estado_p,
                            "fecha": datetime.now().strftime("%d/%m/%Y")
                        })
                        st.success("Boleta ingresada al sistema")

        # --- 4. SECCIÓN STOCK (Dueño, Encargado, Repositor) ---
        if rol == "negocio" or permisos in ["encargado", "repositor"]:
            t_idx = 3 if (rol == "negocio" or permisos == "encargado") else 0
            with tabs[t_idx]:
                st.subheader("Control de Inventario")
                st.info("Aquí se visualizará el stock cargado mediante las compras.")

        # --- 5. SECCIÓN PERSONAL (Solo Dueño o Encargado) ---
        if rol == "negocio" or permisos == "encargado":
            with tabs[4]:
                st.subheader("Gestión de Usuarios y Permisos")
                with st.expander("👤 Crear Nuevo Acceso"):
                    with st.form("form_personal"):
                        u_nuevo = st.text_input("Usuario Login").lower().strip()
                        n_nuevo = st.text_input("Nombre Real")
                        p_nuevo = st.text_input("Contraseña")
                        perm_nuevo = st.selectbox("Nivel de Acceso", ["cajero", "repositor", "encargado"])
                        if st.form_submit_button("Dar de Alta"):
                            if u_nuevo and p_nuevo:
                                db.collection("usuarios").document(u_nuevo).set({
                                    "nombre": n_nuevo, "password": p_nuevo,
                                    "rol": "empleado", "id_negocio": negocio_id,
                                    "permisos": perm_nuevo
                                })
                                st.success(f"Empleado {n_nuevo} creado como {perm_nuevo}")
                            else: st.error("Faltan datos")

    # ==========================================
    # 👤 VISTA CLIENTE
    # ==========================================
    elif rol == "cliente":
        st.header(f"👋 Hola, {nombre_pantalla}")
        movs = db.collection("cuentas_corrientes").where("Cliente", "==", st.session_state['usuario']).stream()
        df_cli = pd.DataFrame([m.to_dict() for m in movs])
        if not df_cli.empty:
            st.metric("MI DEUDA ACTUAL", f"${df_cli['Subtotal'].sum():,.2f}")
            st.dataframe(df_cli[['Fecha', 'Producto', 'Subtotal']], use_container_width=True)
        else:
            st.success("Estás al día. ¡No tenés deudas!")

    # ==========================================
    # ⚙️ SUPER ADMIN
    # ==========================================
    elif rol == "super_admin":
        st.title("Administración Central JL")
        st.write("Panel para crear nuevos Negocios y Dueños.")
