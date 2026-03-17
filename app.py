import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import os

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="JL Gestión", page_icon="📊", layout="wide")

# 2. CONFIGURACIÓN DE LOGOS (RUTAS LOCALES)
# Estas rutas asumen que en tu GitHub tenés una carpeta 'static' y adentro 'images'
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

# --- 🎨 FUNCIÓN PARA LOGO DINÁMICO (LOCAL Y SEGURA) ---
def mostrar_logo(ancho=250, centrar=False):
    negocio = st.session_state.get('id_negocio')
    # Determinar qué archivo buscar
    ruta = LOGO_FABRICON if negocio == "fabricon" else LOGO_SISTEMA
    
    # Verificar si el archivo existe en la carpeta del proyecto
    if os.path.exists(ruta):
        if centrar:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(ruta, use_container_width=True)
        else:
            st.image(ruta, width=ancho)
    else:
        # Si el archivo no está, mostramos un título para que no salga el "0"
        texto_alternativo = "FABRICÓN" if negocio == "fabricon" else "JL GESTIÓN"
        if centrar:
            st.markdown(f"<h1 style='text-align: center;'>{texto_alternativo}</h1>", unsafe_allow_html=True)
        else:
            st.subheader(texto_alternativo)

# --- 🚪 PANTALLA DE INGRESO ---
if not st.session_state['autenticado']:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        mostrar_logo(centrar=True)
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

    # Barra lateral
    with st.sidebar:
        mostrar_logo(ancho=150)
        st.write(f"👤 **{nombre_pantalla}**")
        st.caption(f"Rol: {rol.upper()} | {negocio_actual}")
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True):
            cerrar_sesion()

    # --- 1. VISTA CLIENTE ---
    if rol == "cliente":
        mostrar_logo(ancho=200)
        st.markdown(f"## Hola, {nombre_pantalla}")
        st.divider()
        
        c_doc = db.collection("clientes").document(st.session_state['usuario']).get().to_dict()
        if c_doc:
            st.info(f"📅 Fecha pactada de pago: {c_doc.get('Fecha_Acuerdo_Pago', 'A convenir')}")
        
        movs = db.collection("cuentas_corrientes").where("Cliente", "==", st.session_state['usuario']).stream()
        lista = [m.to_dict() for m in movs]
        if lista:
            df = pd.DataFrame(lista)
            st.metric("SALDO PENDIENTE", f"${pd.to_numeric(df['Subtotal']).sum():,.2f}")
            st.write("### Mis Consumos")
            st.dataframe(df[['Fecha', 'Producto', 'Subtotal']], use_container_width=True)
        else:
            st.success("🎉 ¡No tenés deudas pendientes!")

    # --- 2. VISTA EMPLEADO ---
    elif rol == "empleado":
        mostrar_logo(ancho=180)
        st.title("🛒 Terminal de Ventas")
        st.subheader(f"Negocio: {negocio_actual.upper()}")
        
        clientes_ref = db.collection("clientes").where("id_negocio", "==", negocio_actual).stream()
        dict_cl = {c.to_dict()['nombre']: c.id for c in clientes_ref}
        
        if dict_cl:
            col_f, col_h = st.columns([1, 1])
            with col_f:
                with st.form("venta_empleado", clear_on_submit=True):
                    st.markdown("### Cargar Consumo")
                    cl_sel = st.selectbox("Cliente", list(dict_cl.keys()))
                    prod = st.text_input("Producto")
                    prec = st.number_input("Precio", min_value=0.0, step=50.0)
                    cant = st.number_input("Cantidad", min_value=1, value=1)
                    if st.form_submit_button("Confirmar Carga"):
                        if prod and prec > 0:
                            db.collection("cuentas_corrientes").add({
                                "Cliente": dict_cl[cl_sel], "Nombre_Cliente": cl_sel, "Producto": prod,
                                "Subtotal": prec * float(cant), "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"), 
                                "Negocio": negocio_actual
                            })
                            st.success("✅ Cargado correctamente")
                            st.rerun()
            with col_h:
                st.markdown("### Últimos 5 Movimientos")
                m_ref = db.collection("cuentas_corrientes").where("Negocio", "==", negocio_actual).limit(5).stream()
                l_m = [m.to_dict() for m in m_ref]
                if l_m: st.table(pd.DataFrame(l_m)[['Nombre_Cliente', 'Subtotal']])
        else:
            st.warning("⚠️ No hay clientes cargados en este negocio.")

    # --- 3. VISTA DUEÑO (NEGOCIO) ---
    elif rol == "negocio":
        mostrar_logo(ancho=200)
        st.title(f"📊 Dashboard: {negocio_actual.upper()}")
        
        movs = db.collection("cuentas_corrientes").where("Negocio", "==", negocio_actual).stream()
        df = pd.DataFrame([m.to_dict() for m in movs])
        
        if not df.empty:
            c1, c2 = st.columns(2)
            c1.metric("DEUDA TOTAL CLIENTES", f"${df['Subtotal'].sum():,.2f}")
            c2.metric("CLIENTES ACTIVOS", len(df['Nombre_Cliente'].unique()))
            st.write("### Ranking de Deudores")
            resumen = df.groupby('Nombre_Cliente')['Subtotal'].sum().reset_index()
            st.dataframe(resumen.sort_values(by='Subtotal', ascending=False), use_container_width=True)
        else:
            st.info("Aún no hay movimientos registrados.")

    # --- 4. VISTA PROVEEDOR ---
    elif rol == "proveedor":
        mostrar_logo(ancho=200)
        st.title("🚚 Panel de Proveedor")
        st.info("Aquí verás próximamente el estado de tus pagos y entregas.")

    # --- 5. VISTA SUPER ADMIN ---
    elif rol == "super_admin":
        mostrar_logo(ancho=200)
        st.title("⚙️ Administración Central")
        tab1, tab2 = st.tabs(["👥 Usuarios", "🏢 Negocios"])
        
        with tab1:
            with st.form("crear_usuario", clear_on_submit=True):
                c_a, c_b = st.columns(2)
                n_id = c_a.text_input("ID Usuario").strip().lower()
                n_nom = c_a.text_input("Nombre Completo")
                n_pas = c_b.text_input("Contraseña", type="password")
                n_rol = c_b.selectbox("Rol", ["cliente", "empleado", "proveedor", "negocio"])
                n_neg = st.selectbox("Negocio", ["fabricon", "kiosco_trinidad", "otro"])
                f_pag = st.text_input("Fecha Pactada (Solo Clientes)", value="05 de cada mes")
                
                if st.form_submit_button("Registrar Usuario"):
                    if n_id and n_nom and n_pas:
                        db.collection("usuarios").document(n_id).set({
                            "nombre": n_nom, "password": n_pas, "rol": n_rol, "id_negocio": n_neg
                        })
                        if n_rol == "cliente":
                            db.collection("clientes").document(n_id).set({
                                "nombre": n_nom, "Fecha_Acuerdo_Pago": f_pag, "id_negocio": n_neg
                            })
                        st.success(f"✅ {n_id} creado.")
