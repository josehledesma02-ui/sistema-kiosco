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
        zona_ar = pytz.timezone('America/Argentina/Buenos_Aires')
    except:
        zona_ar = pytz.timezone('UTC')
    return datetime.now(zona_ar)

# URL DE TU GOOGLE SHEETS
ID_HOJA = "1-ay_xIqYItwOaXe80VUsEmh4gsANrk9PH72aZcUD54g"
URL_PROVEEDOR_CSV = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/export?format=csv"

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
# 2. 🔒 VISTA CLIENTE (COMPLETA)
# ==========================================
def mostrar_vistas_cliente(nom_u, f_pago, c_id):
    mostrar_cabecera_identidad()
    
    # Obtener datos de Firebase
    v_fiado = list(db.collection("ventas_procesadas").where("cliente_id", "==", c_id).where("metodo", "==", "Fiado").stream())
    p_realizados = list(db.collection("pagos_clientes").where("cliente_id", "==", c_id).stream())
    
    total_deuda = sum(v.to_dict().get('total', 0) for v in v_fiado)
    total_pagado = sum(p.to_dict().get('monto', 0) for p in p_realizados)
    saldo_pendiente = total_deuda - total_pagado

    # Cabecera de Saldo
    c1, c2 = st.columns(2)
    with c1:
        st.metric("SALDO A PAGAR", f"${saldo_pendiente:,.2f}")
    with c2:
        st.info(f"📅 **Próximo vencimiento:** {f_pago}")

    st.divider()
    
    tab_mov, tab_det = st.tabs(["📜 Mis Movimientos", "📦 Detalle de Compras"])
    
    with tab_mov:
        st.subheader("Historial de Cuenta")
        movs = []
        for v in v_fiado:
            d = v.to_dict()
            movs.append({"Fecha": d.get('fecha_str'), "Tipo": "Compra 🛒", "Monto": d.get('total', 0), "Ref": d.get('fecha_completa')})
        for p in p_realizados:
            d = p.to_dict()
            movs.append({"Fecha": d.get('fecha_str'), "Tipo": "Pago ✅", "Monto": d.get('monto', 0), "Ref": d.get('fecha')})
        
        if movs:
            movs.sort(key=lambda x: str(x['Ref']), reverse=True)
            st.table(pd.DataFrame(movs)[["Fecha", "Tipo", "Monto"]])
        else:
            st.write("No hay movimientos registrados.")

    with tab_det:
        st.subheader("Productos Comprados")
        for v in v_fiado:
            d = v.to_dict()
            with st.expander(f"Ticket {d.get('fecha_str')} - Total: ${d.get('total', 0):,.2f}"):
                for item in d.get('items', []):
                    st.write(f"• {item['nombre']} (x{item['cantidad']}) - ${item['subtotal']:,.2f}")

# ==========================================
# 3. 🛠️ VISTA NEGOCIO (DUEÑO)
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
                st.error("Error cargando inventario.")
                st.stop()

        df = st.session_state.df_proveedor
        busq = st.text_input("🔍 Buscar...", "").lower()
        df_f = df[df['Productos'].astype(str).str.contains(busq, case=False)] if busq else df
        
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1: p_sel = st.selectbox("Elegir", df_f['Productos'].unique())
        with c2: cant = st.number_input("Cant", 0.1, 100.0, 1.0)
        p_sug = float(df[df['Productos'] == p_sel]['Precio'].values[0])
        with c3: p_edit = st.number_input("Precio $", value=p_sug)

        if st.button("➕ AGREGAR", use_container_width=True):
            st.session_state.carrito.append({'nombre': p_sel, 'cantidad': cant, 'precio': p_edit, 'subtotal': p_edit * cant})

        if st.session_state.carrito:
            st.table(pd.DataFrame(st.session_state.carrito))
            total = sum(i['subtotal'] for i in st.session_state.carrito)
            
            cd, cr = st.columns(2)
            desc = cd.number_input("% Desc", 0, 100, 0)
            reca = cr.number_input("% Reca", 0, 100, 0)
            total_f = total * (1 - desc/100) * (1 + reca/100)
            
            st.markdown(f"## TOTAL: ${total_f:,.2f}")
            
            met = st.selectbox("Pago", ["Efectivo", "Transferencia", "Fiado"])
            c_id, c_nom = None, "Consumidor Final"
            
            if met == "Fiado":
                clis = db.collection("usuarios").where("id_negocio", "==", neg_id).where("rol", "==", "cliente").stream()
                dict_clis = {c.to_dict()['nombre']: c.id for c in clis}
                if dict_clis:
                    c_nom = st.selectbox("Asignar a", list(dict_clis.keys()))
                    c_id = dict_clis[c_nom]

            if st.button("🚀 COBRAR", type="primary", use_container_width=True):
                db.collection("ventas_procesadas").add({
                    'id_negocio': neg_id, 'items': st.session_state.carrito, 'total': total_f,
                    'metodo': met, 'cliente_id': c_id, 'cliente_nombre': c_nom,
                    'vendedor': nom_u, 'fecha_completa': ahora_ar,
                    'fecha_str': ahora_ar.strftime("%d/%m/%Y"), 'hora_str': ahora_ar.strftime("%H:%M")
                })
                st.session_state.carrito = []
                st.success("¡Venta Exitosa!")
                st.rerun()

    with t2: # GASTOS
        st.subheader("📉 Gastos")
        desc_g = st.text_input("Concepto")
        monto_g = st.number_input("Monto $", 0.0)
        if st.button("Guardar Gasto"):
            db.collection("gastos").add({'id_negocio': neg_id, 'descripcion': desc_g, 'monto': monto_g, 'fecha_str': ahora_ar.strftime("%d/%m/%Y")})
            st.success("Gasto guardado.")

    with t3: # HISTORIAL
        st.subheader("📜 Historial")
        vtas = db.collection("ventas_procesadas").where("id_negocio", "==", neg_id).order_by("fecha_completa", direction="DESCENDING").limit(20).stream()
        for v in vtas:
            d = v.to_dict()
            st.write(f"📌 {d['fecha_str']} - {d['cliente_nombre']} - **${d['total']:,.2f}**")

    with t4: # CLIENTES
        st.subheader("👥 Clientes")
        with st.form("new_cli"):
            n_ = st.text_input("Nombre"); d_ = st.text_input("DNI"); f_ = st.text_input("Pago")
            if st.form_submit_button("Crear"):
                db.collection("usuarios").add({'id_negocio': neg_id, 'nombre': n_, 'password': d_, 'rol': 'cliente', 'promesa_pago': f_})
                st.success("Creado")

# ==========================================
# 4. NAVEGACIÓN Y LOGIN (PANEL IZQUIERDO)
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
        if st.button("Entrar", use_container_width=True, type="primary"):
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
    # --- BARRA LATERAL RESTAURADA ---
    with st.sidebar:
        if os.path.exists(IMG_SIDEBAR): st.image(IMG_SIDEBAR, width=150)
        st.markdown(f"### 👤 {st.session_state.nombre_real}")
        st.write(f"🏢 Negocio: **{st.session_state.id_negocio.upper()}**")
        
        if st.session_state.rol == "negocio":
            st.success("🛠️ ADMINISTRADOR")
        else:
            st.info("🛍️ CLIENTE")
            st.write(f"📅 Pago: {st.session_state.fecha_pago_cliente}")
            
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
    # --------------------------------

    if st.session_state.rol == "cliente":
        mostrar_vistas_cliente(st.session_state.nombre_real, st.session_state.fecha_pago_cliente, st.session_state.usuario)
    else:
        mostrar_vistas_negocio(st.session_state.id_negocio, st.session_state.nombre_real)
