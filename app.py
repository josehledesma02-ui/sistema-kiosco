import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import pytz
import os

# ==========================================
# 0. CONFIGURACIÓN Y HORA ARGENTINA
# ==========================================
st.set_page_config(page_title="JL Gestión Pro", page_icon="🛍️", layout="wide")

def obtener_hora_argentina():
    zona_ar = pytz.timezone('America/Argentina/Buenos_Aires')
    return datetime.now(zona_ar)

ID_HOJA = "1-ay_xIqYItwOaXe80VUsEmh4gsANrk9PH72aZcUD54g"
NOMBRE_HOJA = "Hoja 1"
URL_PROVEEDOR_CSV = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/gviz/tq?tqx=out:csv&sheet={NOMBRE_HOJA.replace(' ', '%20')}"

IMG_LOGIN = "logo.png" 
IMG_SIDEBAR = "logo_chico.png"

def mostrar_titulo():
    st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🛍️ JL GESTIÓN PRO</h1>", unsafe_allow_html=True)

# ==========================================
# 1. CONEXIÓN A FIREBASE
# ==========================================
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
        st.error(f"⚠️ Error Firebase: {e}")
        st.stop()

db = firestore.client()

# ==========================================
# 2. ESTADO DE SESIÓN
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.update({
        'autenticado': False, 'usuario': None, 'rol': None, 
        'id_negocio': None, 'nombre_real': None, 'carrito': [], 'df_proveedor': None
    })

# ==========================================
# 3. LOGIN
# ==========================================
if not st.session_state.autenticado:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        if os.path.exists(IMG_LOGIN): st.image(IMG_LOGIN, use_container_width=True)
        mostrar_titulo()
        neg_in = st.text_input("Negocio").strip().lower()
        u_in = st.text_input("Nombre y Apellido").strip()
        c_in = st.text_input("Contraseña (DNI)", type="password").strip()
        
        if st.button("Ingresar", use_container_width=True, type="primary"):
            query = db.collection("usuarios").where("id_negocio", "==", neg_in).where("nombre", "==", u_in).limit(1).get()
            if query:
                d = query[0].to_dict()
                if str(d.get('password')) == c_in:
                    st.session_state.update({
                        'autenticado': True, 'usuario': query[0].id, 'rol': str(d.get('rol')).strip().lower(),
                        'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre'),
                        'fecha_pago_cliente': d.get('promesa_pago', 'N/A')
                    })
                    st.rerun()
            st.error("❌ Datos incorrectos")

# ==========================================
# 4. INTERFAZ PRINCIPAL
# ==========================================
else:
    rol_u = st.session_state.rol
    neg_id = st.session_state.id_negocio
    nom_u = st.session_state.nombre_real
    ahora_ar = obtener_hora_argentina()

    with st.sidebar:
        if os.path.exists(IMG_SIDEBAR): st.image(IMG_SIDEBAR, width=150)
        st.write(f"👤 **{nom_u}**")
        if st.button("🔴 Cerrar Sesión"): 
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    mostrar_titulo()

    # --- VISTA DUEÑO ---
    if rol_u == "negocio":
        t1, t2, t3, t4 = st.tabs(["🛒 Ventas", "📉 Gastos", "📜 Historial", "👥 Clientes"])
        
        with t1:
            if st.session_state.df_proveedor is None:
                # Cargamos sin encabezado para buscar dónde empieza la tabla realmente
                raw = pd.read_csv(URL_PROVEEDOR_CSV, header=None)
                # Buscamos la fila que contiene "Productos"
                mask = raw.apply(lambda x: x.astype(str).str.contains('Productos', case=False)).any(axis=1)
                idx = mask.idxmax() if mask.any() else 0
                # Re-cargamos el DF desde esa fila
                df = pd.read_csv(URL_PROVEEDOR_CSV, skiprows=idx)
                df.columns = df.columns.str.strip()
                st.session_state.df_proveedor = df

            df = st.session_state.df_proveedor
            if 'Productos' in df.columns:
                p_sel = st.selectbox("Producto", df['Productos'].dropna().unique())
                cant = st.number_input("Cantidad", min_value=0.1, value=1.0)
                
                if st.button("Agregar"):
                    # Buscamos precio en la columna 'Precio' (columna C)
                    pre = df[df['Productos'] == p_sel]['Precio'].values[0]
                    st.session_state.carrito.append({
                        'nombre': p_sel, 'cantidad': cant, 'precio': float(pre), 'subtotal': float(pre) * cant
                    })
                
                if st.session_state.carrito:
                    st.table(pd.DataFrame(st.session_state.carrito))
                    metodo = st.selectbox("Método", ["Efectivo", "Transferencia", "Fiado"])
                    if st.button("Finalizar Venta"):
                        db.collection("ventas_procesadas").add({
                            'id_negocio': neg_id, 'items': st.session_state.carrito,
                            'total': sum(i['subtotal'] for i in st.session_state.carrito),
                            'metodo': metodo, 'fecha_completa': ahora_ar, 'fecha_str': ahora_ar.strftime("%d/%m/%Y")
                        })
                        st.session_state.carrito = []
                        st.rerun()

        with t2: st.write("Sección Gastos Activa")
        with t3: st.write("Sección Historial Activa")
        with t4: st.write("Sección Clientes Activa")

    # --- VISTA CLIENTE (RESTAURADA) ---
    elif rol_u == "cliente":
        f_pago = st.session_state.fecha_pago_cliente
        c_id = st.session_state.usuario
        
        # Cálculo de Saldo
        v_f = list(db.collection("ventas_procesadas").where("cliente_id", "==", c_id).where("metodo", "==", "Fiado").stream())
        p_f = list(db.collection("pagos_clientes").where("cliente_id", "==", c_id).stream())
        saldo = sum(v.to_dict().get('total', 0) for v in v_f) - sum(p.to_dict().get('monto', 0) for p in p_f)

        st.error(f"## Tu saldo actual: ${saldo:,.2f}")

        # LA NOTA QUE NO DEBO TOCAR MÁS:
        with st.container(border=True):
            st.markdown(f"""
            ### 📝 Nota sobre tu cuenta:
            Usted se ha comprometido a cancelar el total de su deuda el día **{f_pago}**. 
            *   **Si cumple con el pago total:** Se le mantienen los precios originales de compra.
            *   **Si no cumple o deja saldo:** Los valores de los productos se actualizarán automáticamente según el precio de venta actual en el local.
            
            **Por favor, para mantener este beneficio, no deje saldo pendiente.**
            """)

        st.subheader("📜 Detalle de Movimientos")
        # Aquí iría el bucle de movimientos que ya teníamos...
