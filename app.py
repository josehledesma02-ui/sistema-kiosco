import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="JL Gestión", page_icon="📊", layout="wide")

# 2. CONFIGURACIÓN DE LOGOS
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
    st.session_state.update({'autenticado': False, 'usuario': None, 'rol': None, 'id_negocio': None, 'nombre_real': None})

def cerrar_sesion():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

def mostrar_logo(ancho=250, centrar=False):
    logo_url = LOGO_SISTEMA
    if st.session_state.get('autenticado') and st.session_state.get('id_negocio') == "fabricon":
        logo_url = LOGO_FABRICON
    if centrar:
        col1, col2, col3 = st.columns([1, 2, 1]); with col2: st.image(logo_url, use_container_width=True)
    else: st.image(logo_url, width=ancho)

# --- INGRESO ---
if not st.session_state['autenticado']:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        mostrar_logo(centrar=True)
        u_input = st.text_input("Usuario").strip().lower()
        c_input = st.text_input("Contraseña", type="password").strip()
        if st.button("Ingresar", use_container_width=True):
            user_ref = db.collection("usuarios").document(u_input).get()
            if user_ref.exists:
                d = user_ref.to_dict()
                if str(d.get('password')) == c_input:
                    st.session_state.update({'autenticado': True, 'usuario': u_input, 'rol': d.get('rol'), 'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre')})
                    st.rerun()
                else: st.error("❌ Contraseña incorrecta")
            else: st.error("❌ Usuario no encontrado")

# --- PANEL PRINCIPAL ---
else:
    rol = st.session_state['rol']
    negocio_actual = st.session_state['id_negocio']
    nombre_pantalla = st.session_state['nombre_real'] or st.session_state['usuario']

    with st.sidebar:
        mostrar_logo(ancho=150)
        st.write(f"👤 **{nombre_pantalla}**")
        st.caption(f"Rol: {rol.upper()} | Negocio: {negocio_actual}")
        if st.button("🔴 Cerrar Sesión", use_container_width=True): cerrar_sesion()

    # --- VISTA CLIENTE ---
    if rol == "cliente":
        st.markdown(f"<h1 style='text-align: center;'>Hola, {nombre_pantalla}</h1>", unsafe_allow_html=True)
        st.divider()
        c_doc = db.collection("clientes").document(st.session_state['usuario']).get().to_dict()
        if c_doc: st.info(f"📅 Fecha pactada de pago: {c_doc.get('Fecha_Acuerdo_Pago', 'A convenir')}")
        
        movs = db.collection("cuentas_corrientes").where("Cliente", "==", st.session_state['usuario']).stream()
        lista = [m.to_dict() for m in movs]
        if lista:
            df = pd.DataFrame(lista)
            st.metric("SALDO PENDIENTE", f"${pd.to_numeric(df['Subtotal']).sum():,.2f}")
            st.dataframe(df[['Fecha', 'Producto', 'Subtotal']], use_container_width=True)
        else: st.success("🎉 ¡No tenés deudas pendientes!")

    # --- VISTA EMPLEADO ---
    elif rol == "empleado":
        st.title("🛒 Terminal de Ventas")
        clientes_ref = db.collection("clientes").where("id_negocio", "==", negocio_actual).stream()
        dict_cl = {c.to_dict()['nombre']: c.id for c in clientes_ref}
        
        if dict_cl:
            with st.form("venta"):
                cl_sel = st.selectbox("Cliente", list(dict_cl.keys()))
                prod = st.text_input("Producto")
                prec = st.number_input("Precio", min_value=0.0)
                cant = st.number_input("Cantidad", min_value=1, value=1)
                if st.form_submit_button("Cargar Venta"):
                    db.collection("cuentas_corrientes").add({
                        "Cliente": dict_cl[cl_sel], "Nombre_Cliente": cl_sel, "Producto": prod,
                        "Subtotal": prec * cant, "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"), "Negocio": negocio_actual
                    })
                    st.success("Venta cargada.")
        else: st.warning("Cargá clientes primero.")

    # --- VISTA DUEÑO (NEGOCIO) ---
    elif rol == "negocio":
        st.title(f"📊 Dashboard: {negocio_actual.upper()}")
        st.subheader("Resumen General de Cuentas Corrientes")
        
        # Obtenemos todos los movimientos de este negocio
        movs = db.collection("cuentas_corrientes").where("Negocio", "==", negocio_actual).stream()
        df = pd.DataFrame([m.to_dict() for m in movs])
        
        if not df.empty:
            col1, col2 = st.columns(2)
            total_deuda = df['Subtotal'].sum()
            col1.metric("DEUDA TOTAL CLIENTES", f"${total_deuda:,.2f}")
            col2.metric("CLIENTES ACTIVOS", len(df['Nombre_Cliente'].unique()))
            
            st.write("### Detalle por Cliente")
            resumen_cl = df.groupby('Nombre_Cliente')['Subtotal'].sum().reset_index()
            st.table(resumen_cl.sort_values(by='Subtotal', ascending=False))
        else: st.info("Aún no hay movimientos registrados.")

    # --- VISTA PROVEEDOR ---
    elif rol == "proveedor":
        st.title("🚚 Panel de Proveedor")
        st.write(f"Bienvenido, {nombre_pantalla}. Aquí podés ver tus entregas pendientes de cobro.")
        # Lógica para facturas de proveedores aquí...
        st.info("Sección en desarrollo: Aquí verás tus remitos y pagos.")

    # --- VISTA SUPER ADMIN ---
    elif rol == "super_admin":
        st.title("⚙️ Administración Central")
        # (Código de alta de usuario que ya tenías)
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
                
                st.divider()
                st.caption("Configuración adicional para Clientes")
                f_pago = st.text_input("Fecha Pactada de Pago", value="05 de cada mes")
                
                if st.form_submit_button("Registrar Usuario"):
                    if new_id and new_pass and new_name:
                        # Registro en colección usuarios
                        db.collection("usuarios").document(new_id).set({
                            "nombre": new_name, 
                            "password": new_pass, 
                            "rol": new_rol, 
                            "id_negocio": new_neg
                        })
                        # Registro paralelo en clientes si corresponde
                        if new_rol == "cliente":
                            db.collection("clientes").document(new_id).set({
                                "nombre": new_name, 
                                "Fecha_Acuerdo_Pago": f_pago, 
                                "id_negocio": new_neg
                            })
                        st.success(f"✅ Usuario '{new_id}' creado con éxito.")
                    else:
                        st.error("Por favor, completa ID, Nombre y Contraseña.")

    # --- 3. VISTA EMPLEADO ---
    elif rol == "empleado":
        st.title("🛒 Terminal de Ventas")
        st.subheader(f"Punto de Venta: {negocio_actual.upper()}")
        
        # Obtener clientes del negocio
        clientes_ref = db.collection("clientes").where("id_negocio", "==", negocio_actual).stream()
        dict_clientes = {c.to_dict()['nombre']: c.id for c in clientes_ref}
        
        if not dict_clientes:
            st.warning("No hay clientes registrados para este negocio.")
        else:
            col_form, col_hist = st.columns([1, 1])
            
            with col_form:
                with st.form("nueva_venta", clear_on_submit=True):
                    st.markdown("### Nueva Carga")
                    cliente_sel = st.selectbox("Seleccionar Cliente", options=list(dict_clientes.keys()))
                    producto = st.text_input("Producto / Concepto")
                    precio = st.number_input("Precio ($)", min_value=0.0, step=50.0)
                    cantidad = st.number_input("Cantidad", min_value=1, value=1)
                    
                    if st.form_submit_button("Confirmar y Cargar"):
                        if producto and precio > 0:
                            subtotal = precio * cantidad
                            nueva_venta = {
                                "Cliente": dict_clientes[cliente_sel],
                                "Nombre_Cliente": cliente_sel,
                                "Producto": producto,
                                "Precio_Unitario": precio,
                                "Cantidad": cantidad,
                                "Subtotal": subtotal,
                                "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                                "Negocio": negocio_actual
                            }
                            db.collection("cuentas_corrientes").add(nueva_venta)
                            st.success(f"✅ ${subtotal} cargados a {cliente_sel}")
                            st.rerun() # Para actualizar el historial
                        else:
                            st.error("Error: El producto y el precio son obligatorios.")

            with col_hist:
                st.markdown("### Últimos Movimientos")
                # Mostrar los últimos 10 movimientos del negocio
                movs_ref = db.collection("cuentas_corrientes")\
                    .where("Negocio", "==", negocio_actual)\
                    .order_by("Fecha", direction=firestore.Query.DESCENDING)\
                    .limit(10).stream()
                
                lista_movs = [m.to_dict() for m in movs_ref]
                if lista_movs:
                    df_hist = pd.DataFrame(lista_movs)
                    st.dataframe(df_hist[['Fecha', 'Nombre_Cliente', 'Producto', 'Subtotal']], use_container_width=True)
                else:
                    st.info("No hay ventas registradas recientemente.")
