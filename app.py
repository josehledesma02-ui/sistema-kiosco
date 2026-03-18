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
    try:
        # Zona horaria corregida para evitar el error de pytz
        zona_ar = pytz.timezone('America/Argentina/Buenos_Aires')
    except:
        zona_ar = pytz.timezone('UTC')
    return datetime.now(zona_ar)

# URL DE TU GOOGLE SHEETS
ID_HOJA = "1-ay_xIqYItwOaXe80VUsEmh4gsANrk9PH72aZcUD54g"
URL_PROVEEDOR_CSV = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/export?format=csv"

# Rutas de imágenes
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
# 2. VISTA CLIENTE
# ==========================================
def mostrar_vistas_cliente(nom_u, f_pago, c_id):
    mostrar_cabecera_identidad()
    st.subheader(f"Bienvenido, {nom_u}")
    
    v_fiado = list(db.collection("ventas_procesadas").where("cliente_id", "==", c_id).where("metodo", "==", "Fiado").stream())
    p_realizados = list(db.collection("pagos_clientes").where("cliente_id", "==", c_id).stream())
    
    saldo = sum(v.to_dict().get('total', 0) for v in v_fiado) - sum(p.to_dict().get('monto', 0) for p in p_realizados)
    
    st.error(f"### Saldo Pendiente: ${saldo:,.2f}")
    st.info(f"📅 Fecha de Pago Pactada: {f_pago}")
    
    st.divider()
    st.subheader("Tus Compras Recientes")
    for v in v_fiado:
        d = v.to_dict()
        with st.container(border=True):
            st.write(f"📅 {d.get('fecha_str')} - Total: ${d.get('total', 0):,.2f}")

# ==========================================
# 3. VISTA NEGOCIO (DUEÑO)
# ==========================================
def mostrar_vistas_negocio(neg_id, nom_u):
    mostrar_cabecera_identidad()
    ahora_ar = obtener_hora_argentina()
    t1, t2, t3, t4 = st.tabs(["🛒 Ventas", "📉 Gastos", "📜 Historial", "👥 Clientes"])
    
    with t1:
        if 'df_proveedor' not in st.session_state or st.session_state.df_proveedor is None:
            try:
                raw = pd.read_csv(URL_PROVEEDOR_CSV, header=None).fillna("")
                fila_enc = 0
                for i, row in raw.iterrows():
                    if any("producto" in str(x).lower() for x in row.values):
                        fila_enc = i
                        break
                df = pd.read_csv(URL_PROVEEDOR_CSV, skiprows=fila_enc)
                df.columns = [str(c).strip() for c in df.columns]
                c_prod = next((c for c in df.columns if "producto" in c.lower()), df.columns[0])
                c_prec = next((c for c in df.columns if "precio" in c.lower()), df.columns[1])
                df_f = df.rename(columns={c_prod: "Productos", c_prec: "Precio"})
                df_f["Precio"] = pd.to_numeric(df_f["Precio"], errors='coerce').fillna(0)
                st.session_state.df_proveedor = df_f[["Productos", "Precio"]].dropna(subset=["Productos"])
            except:
                st.error("No se pudo cargar el inventario.")
                st.stop()

        df = st.session_state.df_proveedor
        busq = st.text_input("🔍 Buscar producto...", "").lower()
        df_f = df[df['Productos'].astype(str).str.contains(busq, case=False)] if busq else df
        
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1: p_sel = st.selectbox("Producto", df_f['Productos'].unique())
        with c2: cant = st.number_input("Cantidad", 0.1, 1000.0, 1.0)
        p_sug = float(df[df['Productos'] == p_sel]['Precio'].values[0])
        with c3: p_vta = st.number_input("Precio $", value=p_sug)

        if st.button("➕ AGREGAR AL CARRITO", use_container_width=True):
            st.session_state.carrito.append({'nombre': p_sel, 'cantidad': cant, 'precio': p_vta, 'subtotal': p_vta * cant})

        if st.session_state.carrito:
            st.table(pd.DataFrame(st.session_state.carrito))
            total = sum(i['subtotal'] for i in st.session_state.carrito)
            
            c_desc, c_reca = st.columns(2)
            desc = c_desc.number_input("% Descuento", 0, 100, 0)
            reca = c_reca.number_input("% Recargo", 0, 100, 0)
            total_final = total * (1 - desc/100) * (1 + reca/100)
            
            st.markdown(f"## TOTAL: ${total_final:,.2f}")
            
            metodo = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Fiado"])
            cli_id, cli_nom = None, "Consumidor Final"
            
            if metodo == "Fiado":
                clis = db.collection("usuarios").where("id_negocio", "==", neg_id).where("rol", "==", "cliente").stream()
                d_clis = {c.to_dict()['nombre']: c.id for c in clis}
                if d_clis:
                    cli_nom = st.selectbox("Cliente", list(d_clis.keys()))
                    cli_id = d_clis[cli_nom]

            if st.button("🚀 FINALIZAR VENTA", type="primary", use_container_width=True):
                db.collection("ventas_procesadas").add({
                    'id_negocio': neg_id, 'items': st.session_state.carrito, 'total': total_final,
                    'metodo': metodo, 'cliente_id': cli_id, 'cliente_nombre': cli_nom,
                    'vendedor': nom_u, 'fecha_completa': ahora_ar,
                    'fecha_str': ahora_ar.strftime("%d/%m/%Y"), 'hora_str': ahora_ar.strftime("%H:%M")
                })
                st.session_state.carrito = []
                st.success("¡Venta Guardada!")
                st.rerun()

    with t2: # GASTOS
        st.subheader("📉 Registro de Gastos")
        g_desc = st.text_input("Descripción")
        g_monto = st.number_input("Monto", 0.0)
        if st.button("Registrar"):
            db.collection("gastos").add({'id_negocio': neg_id, 'descripcion': g_desc, 'monto': g_monto, 'fecha_str': ahora_ar.strftime("%d/%m/%Y")})
            st.rerun()

    with t3: # HISTORIAL
        st.subheader("📜 Historial de Ventas")
        vtas = db.collection("ventas_procesadas").where("id_negocio", "==", neg_id).order_by("fecha_completa", direction="DESCENDING").limit(20).stream()
        for v in vtas:
            d = v.to_dict()
            st.write(f"📅 {d['fecha_str']} - {d['cliente_nombre']} - Total: **${d['total']:,.2f}**")

    with t4: # CLIENTES
        st.subheader("👥 Gestión de Clientes")
        with st.form("cli"):
            cn = st.text_input("Nombre"); cd = st.text_input("DNI"); cf = st.text_input("Pago")
            if st.form_submit_button("Crear"):
                db.collection("usuarios").add({'id_negocio': neg_id, 'nombre': cn, 'password': cd, 'rol': 'cliente', 'promesa_pago': cf})
                st.success("Guardado")

# ==========================================
# 4. LOGIN Y BARRA LATERAL (RECUPERADA)
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.update({'autenticado': False, 'usuario': None, 'rol': None, 'id_negocio': None, 'nombre_real': None, 'carrito': [], 'df_proveedor': None})

if not st.session_state.autenticado:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        if os.path.exists(IMG_LOGIN): st.image(IMG_LOGIN, use_container_width=True)
        mostrar_cabecera_identidad()
        neg_in = st.text_input("ID Negocio").strip().lower()
        u_in = st.text_input("Usuario").strip()
        c_in = st.text_input("Clave", type="password").strip()
        if st.button("Ingresar", use_container_width=True, type="primary"):
            q = db.collection("usuarios").where("id_negocio", "==", neg_in).where("nombre", "==", u_in).limit(1).get()
            if q and str(q[0].to_dict().get('password')) == c_in:
                d = q[0].to_dict()
                st.session_state.update({
                    'autenticado': True, 'usuario': q[0].id, 'rol': str(d.get('rol')).strip().lower(),
                    'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre'),
                    'fecha_pago_cliente': d.get('promesa_pago', 'N/A')
                })
                st.rerun()
            else:
                st.error("Datos incorrectos")
else:
    # --- PANEL IZQUIERDO (RESTAURADO) ---
    with st.sidebar:
        if os.path.exists(IMG_SIDEBAR): 
            st.image(IMG_SIDEBAR, width=150)
        st.markdown(f"### 👤 {st.session_state.nombre_real}")
        st.write(f"🏢 Negocio: **{st.session_state.id_negocio.upper()}**")
        
        if st.session_state.rol == "negocio":
            st.success("🛠️ MODO ADMINISTRADOR")
        else:
            st.info("🛍️ MODO CLIENTE")
            st.write(f"📅 Pago: {st.session_state.fecha_pago_cliente}")
            
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
    # ------------------------------------

    if st.session_state.rol == "cliente":
        mostrar_vistas_cliente(st.session_state.nombre_real, st.session_state.fecha_pago_cliente, st.session_state.usuario)
    else:
        mostrar_vistas_negocio(st.session_state.id_negocio, st.session_state.nombre_real)
