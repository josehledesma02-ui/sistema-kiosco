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

def mostrar_cabecera_identidad():
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
# 2. 🔒 SECCIÓN BLINDADA: VISTA CLIENTE
# ==========================================
def mostrar_vistas_cliente(nom_u, f_pago, c_id):
    mostrar_cabecera_identidad()
    v_fiado = list(db.collection("ventas_procesadas").where("cliente_id", "==", c_id).where("metodo", "==", "Fiado").stream())
    p_realizados = list(db.collection("pagos_clientes").where("cliente_id", "==", c_id).stream())
    saldo = sum(v.to_dict().get('total', 0) for v in v_fiado) - sum(p.to_dict().get('monto', 0) for p in p_realizados)
    st.error(f"# Tu saldo actual: ${saldo:,.2f}")
    with st.container(border=True):
        st.markdown(f"### 📝 Nota sobre tu cuenta:\nUsted se ha comprometido a cancelar el total de su deuda el día **{f_pago}**.")
        st.markdown("* **Si cumple:** Se mantienen los precios originales.\n* **Si no cumple:** Los valores se actualizarán al precio actual.")
    st.subheader("📜 Detalle de Movimientos")
    movs = []
    for v in v_fiado: movs.append({"dt": v.to_dict().get('fecha_completa'), "tipo": "C", "d": v.to_dict()})
    for p in p_realizados: movs.append({"dt": p.to_dict().get('fecha'), "tipo": "P", "d": p.to_dict()})
    movs.sort(key=lambda x: x['dt'] if x['dt'] else datetime.min, reverse=True)
    for m in movs:
        with st.container(border=True):
            d = m['d']
            if m['tipo'] == "C":
                st.write(f"🛒 {d.get('fecha_str')} - {d.get('hora_str')}hs")
                st.markdown(f"<h2 style='color:red;'>- ${d.get('total', 0):,.2f}</h2>", unsafe_allow_html=True)
            else:
                st.write(f"✅ Pago: {d.get('fecha_str')}")
                st.markdown(f"<h2 style='color:green;'>+ ${d.get('monto', 0):,.2f}</h2>", unsafe_allow_html=True)

# ==========================================
# 3. 🛠️ SECCIÓN: VISTA NEGOCIO (DUEÑO) - RECONSTRUIDA
# ==========================================
def mostrar_vistas_negocio(neg_id, nom_u):
    mostrar_cabecera_identidad()
    ahora_ar = obtener_hora_argentina()
    t1, t2, t3, t4 = st.tabs(["🛒 Ventas", "📉 Gastos", "📜 Historial", "👥 Clientes"])
    
    with t1: # VENTAS COMPLETO
        if 'df_proveedor' not in st.session_state or st.session_state.df_proveedor is None:
            raw = pd.read_csv(URL_PROVEEDOR_CSV, header=None)
            mask = raw.apply(lambda x: x.astype(str).str.contains('Productos', case=False)).any(axis=1)
            idx = mask.idxmax() if mask.any() else 0
            df = pd.read_csv(URL_PROVEEDOR_CSV, skiprows=idx)
            df.columns = df.columns.str.strip()
            st.session_state.df_proveedor = df

        df = st.session_state.df_proveedor
        
        # BUSCADOR DINÁMICO
        busqueda = st.text_input("🔍 Buscar producto...", "").lower()
        df_filtrado = df[df['Productos'].str.contains(busqueda, case=False, na=False)] if busqueda else df
        
        col_p, col_can, col_pre = st.columns([2, 1, 1])
        with col_p: p_sel = st.selectbox("Producto", df_filtrado['Productos'].dropna().unique())
        with col_can: cant = st.number_input("Cantidad", min_value=0.1, value=1.0, step=0.1)
        
        # Precio sugerido que se puede modificar
        precio_sug = float(df[df['Productos'] == p_sel]['Precio'].values[0])
        with col_pre: precio_final = st.number_input("Precio Unit. $", value=precio_sug)

        if st.button("➕ AGREGAR AL CARRITO", use_container_width=True):
            st.session_state.carrito.append({
                'nombre': p_sel, 'cantidad': cant, 'precio': precio_final, 'subtotal': precio_final * cant
            })

        if st.session_state.carrito:
            st.divider()
            df_car = pd.DataFrame(st.session_state.carrito)
            st.table(df_car)
            
            subtotal_car = df_car['subtotal'].sum()
            
            # DESCUENTO / RECARGO
            c_desc, c_rec = st.columns(2)
            with c_desc: desc_pct = st.number_input("% Descuento", min_value=0, max_value=100, value=0)
            with c_rec: rec_pct = st.number_input("% Recargo", min_value=0, value=0)
            
            total_final = subtotal_car * (1 - desc_pct/100) * (1 + rec_pct/100)
            st.markdown(f"## TOTAL A COBRAR: ${total_final:,.2f}")

            col_met, col_cli = st.columns(2)
            with col_met: met = st.selectbox("Método", ["Efectivo", "Transferencia", "Fiado"])
            with col_cli:
                cid, nom_c_vta = None, "Consumidor Final"
                if met == "Fiado":
                    clis = db.collection("usuarios").where("id_negocio", "==", neg_id).where("rol", "==", "cliente").stream()
                    d_clis = {c.to_dict()['nombre']: c.id for c in clis}
                    nom_c_vta = st.selectbox("Cliente", list(d_clis.keys()))
                    cid = d_clis[nom_c_vta]

            if st.button("🚀 PROCESAR VENTA", type="primary", use_container_width=True):
                db.collection("ventas_procesadas").add({
                    'id_negocio': neg_id, 'items': st.session_state.carrito, 'total': total_final,
                    'metodo': met, 'cliente_id': cid, 'cliente_nombre': nom_c_vta,
                    'vendedor': nom_u, 'descuento_pct': desc_pct, 'recargo_pct': rec_pct,
                    'fecha_completa': ahora_ar, 'fecha_str': ahora_ar.strftime("%d/%m/%Y"), 'hora_str': ahora_ar.strftime("%H:%M")
                })
                st.session_state.carrito = []
                st.success("Venta guardada en el historial")
                st.rerun()

    with t2: # GASTOS
        st.subheader("📉 Registro de Gastos")
        desc_g = st.text_input("Concepto")
        monto_g = st.number_input("Importe $", min_value=0.0)
        if st.button("Guardar Gasto"):
            db.collection("gastos").add({'id_negocio': neg_id, 'descripcion': desc_g, 'monto': monto_g, 'fecha_completa': ahora_ar, 'fecha_str': ahora_ar.strftime("%d/%m/%Y")})
            st.success("Gasto registrado")

    with t3: # HISTORIAL DETALLADO
        st.subheader("📜 Historial de Operaciones")
        vtas = db.collection("ventas_procesadas").where("id_negocio", "==", neg_id).order_by("fecha_completa", direction="DESCENDING").limit(30).stream()
        for v in vtas:
            d = v.to_dict()
            with st.expander(f"{d.get('fecha_str')} {d.get('hora_str')} - {d.get('cliente_nombre')} - ${d.get('total'):,.2f}"):
                st.write(f"👤 **Vendedor:** {d.get('vendedor')}")
                st.write(f"💳 **Método:** {d.get('metodo')}")
                st.write("📦 **Detalle:**")
                for i in d.get('items', []): st.write(f"- {i['cantidad']} x {i['nombre']} (${i['precio']})")

    with t4: # CLIENTES
        st.subheader("👥 Gestión de Clientes")
        with st.form("Alta"):
            cnom = st.text_input("Nombre")
            cdni = st.text_input("DNI")
            cpago = st.text_input("Fecha Pago")
            if st.form_submit_button("Registrar"):
                db.collection("usuarios").add({'id_negocio': neg_id, 'nombre': cnom, 'password': cdni, 'rol': 'cliente', 'promesa_pago': cpago})
                st.success("Cliente creado")

# ==========================================
# 4. NAVEGACIÓN Y LOGIN
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.update({'autenticado': False, 'usuario': None, 'rol': None, 'id_negocio': None, 'nombre_real': None, 'carrito': [], 'df_proveedor': None})

if not st.session_state.autenticado:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        if os.path.exists(IMG_LOGIN): st.image(IMG_LOGIN, use_container_width=True)
        mostrar_cabecera_identidad()
        neg_in = st.text_input("Negocio").strip().lower()
        u_in = st.text_input("Nombre y Apellido").strip()
        c_in = st.text_input("Contraseña (DNI)", type="password").strip()
        if st.button("Ingresar", use_container_width=True, type="primary"):
            query = db.collection("usuarios").where("id_negocio", "==", neg_in).where("nombre", "==", u_in).limit(1).get()
            if query and str(query[0].to_dict().get('password')) == c_in:
                d = query[0].to_dict()
                st.session_state.update({'autenticado': True, 'usuario': query[0].id, 'rol': str(d.get('rol')).strip().lower(), 'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre'), 'fecha_pago_cliente': d.get('promesa_pago', 'N/A')})
                st.rerun()
            st.error("❌ Datos incorrectos")
else:
    with st.sidebar:
        if os.path.exists(IMG_SIDEBAR): st.image(IMG_SIDEBAR, width=150)
        st.markdown(f"### 👤 {st.session_state.nombre_real}")
        if st.session_state.rol == "negocio": st.success("🛠️ MODO ADMINISTRADOR")
        else: st.info("🛍️ MODO CLIENTE")
        st.write(f"🏢 Negocio: **{st.session_state.id_negocio.upper()}**")
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True): 
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    if st.session_state.rol == "cliente":
        mostrar_vistas_cliente(st.session_state.nombre_real, st.session_state.fecha_pago_cliente, st.session_state.usuario)
    else:
        mostrar_vistas_negocio(st.session_state.id_negocio, st.session_state.nombre_real)
