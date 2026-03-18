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
    zona_ar = pytz.timezone('America/Argentina_Buenos_Aires')
    return datetime.now(zona_ar)

# URL DE TU GOOGLE SHEETS (IMPORTANTE: Debe estar compartido como "Cualquier persona con el enlace puede leer")
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
    
    st.subheader("📜 Detalle de Movimientos")
    movs = []
    for v in v_fiado: movs.append({"dt": v.to_dict().get('fecha_completa'), "tipo": "C", "d": v.to_dict()})
    for p in p_realizados: movs.append({"dt": p.to_dict().get('fecha'), "tipo": "P", "d": p.to_dict()})
    movs.sort(key=lambda x: x['dt'] if x['dt'] else datetime.min, reverse=True)
    
    for m in movs:
        with st.container(border=True):
            d = m['d']
            if m['tipo'] == "C":
                st.write(f"🛒 {d.get('fecha_str')} - {d.get('hora_str')}hs - Total: ${d.get('total', 0):,.2f}")
            else:
                st.write(f"✅ Pago recibido: {d.get('fecha_str')} - Monto: ${d.get('monto', 0):,.2f}")

# ==========================================
# 3. 🛠️ SECCIÓN: VISTA NEGOCIO (DUEÑO)
# ==========================================
def mostrar_vistas_negocio(neg_id, nom_u):
    mostrar_cabecera_identidad()
    ahora_ar = obtener_hora_argentina()
    t1, t2, t3, t4 = st.tabs(["🛒 Ventas", "📉 Gastos", "📜 Historial", "👥 Clientes"])
    
    with t1: # PESTAÑA VENTAS
        if 'df_proveedor' not in st.session_state or st.session_state.df_proveedor is None:
            try:
                # Lectura flexible del CSV
                raw = pd.read_csv(URL_PROVEEDOR_CSV, header=None).fillna("")
                fila_inicio = 0
                for i, row in raw.iterrows():
                    if any("producto" in str(x).lower() for x in row.values):
                        fila_inicio = i
                        break
                df = pd.read_csv(URL_PROVEEDOR_CSV, skiprows=fila_inicio)
                df.columns = [str(c).strip() for c in df.columns]
                
                c_prod = next((c for c in df.columns if "producto" in c.lower()), None)
                c_prec = next((c for c in df.columns if "precio" in c.lower()), None)
                
                if c_prod and c_prec:
                    df = df.rename(columns={c_prod: "Productos", c_prec: "Precio"})
                    df["Precio"] = pd.to_numeric(df["Precio"], errors='coerce').fillna(0)
                    st.session_state.df_proveedor = df[["Productos", "Precio"]].dropna(subset=["Productos"])
                else:
                    st.error("⚠️ No se detectaron las columnas de 'Productos' o 'Precio'.")
                    st.stop()
            except Exception as e:
                st.error(f"Error cargando el Excel: {e}")
                st.stop()

        df = st.session_state.df_proveedor
        busqueda = st.text_input("🔍 Buscar producto...", "").lower()
        df_f = df[df['Productos'].astype(str).str.contains(busqueda, case=False)] if busqueda else df
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1: 
            p_sel = st.selectbox("Seleccionar", df_f['Productos'].unique())
        with col2: 
            cant = st.number_input("Cantidad", min_value=0.1, value=1.0, step=0.1)
        
        precio_base = float(df[df['Productos'] == p_sel]['Precio'].values[0])
        with col3: 
            precio_edit = st.number_input("Precio Unit. $", value=precio_base)

        if st.button("➕ AGREGAR", use_container_width=True):
            st.session_state.carrito.append({
                'nombre': p_sel, 'cantidad': cant, 'precio': precio_edit, 'subtotal': precio_edit * cant
            })

        if st.session_state.carrito:
            st.divider()
            df_c = pd.DataFrame(st.session_state.carrito)
            st.table(df_c)
            sub_total = df_c['subtotal'].sum()
            
            c_d, c_r = st.columns(2)
            with c_d: desc = st.number_input("% Descuento", 0, 100, 0)
            with c_r: rec = st.number_input("% Recargo", 0, 500, 0)
            
            total_final = sub_total * (1 - desc/100) * (1 + rec/100)
            st.markdown(f"## TOTAL: ${total_final:,.2f}")

            m_col, cl_col = st.columns(2)
            with m_col: 
                metodo = st.selectbox("Pago", ["Efectivo", "Transferencia", "Fiado"])
            with cl_col:
                cid, n_cli = None, "Consumidor Final"
                if metodo == "Fiado":
                    query_c = db.collection("usuarios").where("id_negocio", "==", neg_id).where("rol", "==", "cliente").stream()
                    dict_c = {c.to_dict()['nombre']: c.id for c in query_c}
                    if dict_c:
                        n_cli = st.selectbox("Asignar a:", list(dict_c.keys()))
                        cid = dict_c[n_cli]

            if st.button("🚀 FINALIZAR VENTA", type="primary", use_container_width=True):
                db.collection("ventas_procesadas").add({
                    'id_negocio': neg_id, 'items': st.session_state.carrito, 'total': total_final,
                    'metodo': metodo, 'cliente_id': cid, 'cliente_nombre': n_cli,
                    'vendedor': nom_u, 'fecha_completa': ahora_ar, 
                    'fecha_str': ahora_ar.strftime("%d/%m/%Y"), 'hora_str': ahora_ar.strftime("%H:%M")
                })
                st.session_state.carrito = []
                st.success("¡Venta exitosa!")
                st.rerun()

    with t2: # GASTOS
        st.subheader("📉 Gastos")
        dg = st.text_input("Concepto")
        mg = st.number_input("Monto", 0.0)
        if st.button("Guardar Gasto"):
            db.collection("gastos").add({'id_negocio': neg_id, 'descripcion': dg, 'monto': mg, 'fecha_str': ahora_ar.strftime("%d/%m/%Y")})
            st.success("Gasto guardado")

    with t3: # HISTORIAL
        st.subheader("📜 Historial")
        vtas = db.collection("ventas_procesadas").where("id_negocio", "==", neg_id).order_by("fecha_completa", direction="DESCENDING").limit(20).stream()
        for v in vtas:
            d = v.to_dict()
            st.write(f"**{d['fecha_str']} {d['hora_str']}** - {d['cliente_nombre']} - ${d['total']:,.2f} ({d['metodo']})")

    with t4: # CLIENTES
        st.subheader("👥 Registro de Clientes")
        with st.form("N"):
            n = st.text_input("Nombre"); d = st.text_input("DNI"); f = st.text_input("Fecha Pago")
            if st.form_submit_button("Registrar"):
                db.collection("usuarios").add({'id_negocio': neg_id, 'nombre': n, 'password': d, 'rol': 'cliente', 'promesa_pago': f})
                st.success("Cliente creado correctamente")

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
            q = db.collection("usuarios").where("id_negocio", "==", neg_in).where("nombre", "==", u_in).limit(1).get()
            if q and str(q[0].to_dict().get('password')) == c_in:
                d = q[0].to_dict()
                st.session_state.update({'autenticado': True, 'usuario': q[0].id, 'rol': str(d.get('rol')).strip().lower(), 'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre'), 'fecha_pago_cliente': d.get('promesa_pago', 'N/A')})
                st.rerun()
            st.error("Datos incorrectos")
else:
    with st.sidebar:
        if os.path.exists(IMG_SIDEBAR): st.image(IMG_SIDEBAR, width=150)
        st.markdown(f"### 👤 {st.session_state.nombre_real}")
        if st.session_state.rol == "negocio": st.success("🛠️ MODO ADMINISTRADOR")
        else: st.info("🛍️ MODO CLIENTE")
        st.divider()
        if st.button("🔴 Cerrar Sesión"): 
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
    if st.session_state.rol == "cliente":
        mostrar_vistas_cliente(st.session_state.nombre_real, st.session_state.fecha_pago_cliente, st.session_state.usuario)
    else:
        mostrar_vistas_negocio(st.session_state.id_negocio, st.session_state.nombre_real)
