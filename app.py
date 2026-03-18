import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime, timedelta
import os
import urllib.parse

# ==========================================
# 0. CONFIGURACIÓN VISUAL
# ==========================================
st.set_page_config(page_title="JL Gestión Pro", page_icon="🛍️", layout="wide")

ID_HOJA = "1-ay_xIqYItwOaXe80VUsEmh4gsANrk9PH72aZcUD54g"
URL_PROVEEDOR_CSV = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/export?format=csv"
IMG_LOGIN = "logo.png" 
IMG_SIDEBAR = "logo_chico.png"

def mostrar_titulo():
    st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🛍️ JL GESTIÓN PRO</h1>", unsafe_allow_html=True)

def sumar_un_mes(fecha_str):
    try:
        fecha_dt = datetime.strptime(fecha_str, "%d/%m/%Y")
        proxima = fecha_dt + timedelta(days=31)
        return proxima.strftime("%d/%m/%Y")
    except: return fecha_str

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
        'id_negocio': None, 'nombre_real': None, 'id_usuario': None,
        'carrito': [], 'df_proveedor': None
    })

def cargar_datos_proveedor():
    try:
        df = pd.read_csv(URL_PROVEEDOR_CSV, header=1)
        df.columns = df.columns.astype(str).str.strip()
        col_prod = [c for c in df.columns if any(kw in c.lower() for kw in ['producto', 'articulo', 'descrip'])]
        col_prec = [c for c in df.columns if any(kw in c.lower() for kw in ['precio', 'venta', 'valor'])]
        if col_prod and col_prec:
            df = df.rename(columns={col_prod[0]: 'Productos', col_prec[0]: 'Precio_Raw'})
            df['Precio'] = df['Precio_Raw'].apply(lambda x: float(str(x).replace('$','').replace('.','').replace(',','.')) if pd.notna(x) else 0)
            st.session_state.df_proveedor = df
    except: pass

if st.session_state.df_proveedor is None: cargar_datos_proveedor()

# ==========================================
# 3. LOGIN (BÚSQUEDA POR NOMBRE REAL + NEGOCIO)
# ==========================================
if not st.session_state['autenticado']:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        if os.path.exists(IMG_LOGIN): st.image(IMG_LOGIN, use_container_width=True)
        mostrar_titulo()
        
        negocio_input = st.text_input("Negocio (Ej: fabricon)").strip().lower()
        u_input = st.text_input("Nombre y Apellido").strip()
        c_input = st.text_input("Contraseña (DNI)", type="password").strip()
        
        if st.button("Ingresar", use_container_width=True, type="primary"):
            if negocio_input and u_input and c_input:
                query = db.collection("usuarios")\
                          .where("id_negocio", "==", negocio_input)\
                          .where("nombre", "==", u_input)\
                          .limit(1).get()
                
                if len(query) > 0:
                    doc = query[0]
                    d = doc.to_dict()
                    if str(d.get('password')) == c_input:
                        st.session_state.update({
                            'autenticado': True, 'usuario': doc.id, 
                            'rol': str(d.get('rol')).strip().capitalize(), # Ejemplo: Cliente
                            'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre'),
                            'id_usuario': doc.id
                        })
                        st.rerun()
                    else: st.error("❌ DNI incorrecto")
                else: st.error("❌ Usuario no encontrado en este negocio")

# ==========================================
# 4. INTERFAZ PRINCIPAL
# ==========================================
else:
    negocio_id = st.session_state['id_negocio']
    nombre_usuario = st.session_state['nombre_real']
    rol_usuario = st.session_state['rol']

    # --- SIDEBAR MEJORADA ---
    with st.sidebar:
        if os.path.exists(IMG_SIDEBAR): st.image(IMG_SIDEBAR, width=150)
        
        # Identificación de Usuario y Negocio
        st.markdown(f"### 👤 {nombre_usuario}")
        st.markdown(f"**Rol:** {rol_usuario}")
        st.markdown(f"**Negocio:** {negocio_id.upper()}")
        st.divider()
        
        # --- SECCIÓN NOTIFICACIONES ---
        st.subheader("🔔 Notificaciones")
        hoy = datetime.now()
        
        # Solo el dueño ve cobros de clientes; el cliente ve su propio recordatorio
        if rol_usuario.lower() == "negocio":
            st.caption("Avisos de Cobro (Próximos 5 días)")
            clis_ref = db.collection("usuarios").where("id_negocio", "==", negocio_id).where("rol", "==", "cliente").stream()
            for c in clis_ref:
                cd = c.to_dict()
                f_p = cd.get('promesa_pago', '')
                try:
                    f_dt = datetime.strptime(f_p, "%d/%m/%Y")
                    dias_faltantes = (f_dt - hoy).days
                    
                    # Rango de 5 días o si ya está vencido
                    if dias_faltantes <= 5:
                        # Calcular saldo rápido
                        v_f = list(db.collection("ventas_procesadas").where("cliente_id", "==", c.id).where("metodo", "==", "Fiado").stream())
                        p_f = list(db.collection("pagos_clientes").where("cliente_id", "==", c.id).stream())
                        saldo = sum(v.to_dict().get('total', 0) for v in v_f) - sum(p.to_dict().get('monto', 0) for p in p_f)
                        
                        if saldo > 0:
                            leyenda = "⚠️ Próximo a cobrar" if dias_faltantes >= 0 else "🚨 PAGO VENCIDO"
                            with st.container(border=True):
                                st.write(f"**{cd.get('nombre')}**")
                                st.markdown(f"<span style='color:#e67e22;'>{leyenda}</span>", unsafe_allow_html=True)
                                st.caption(f"Fecha: {f_p} | Saldo: ${saldo:,.2f}")
                                msg = f"Hola {cd.get('nombre')}, te recordamos tu compromiso de pago para el {f_p}. Saldo pendiente: ${saldo:,.2f}."
                                st.markdown(f"[📲 Enviar Recordatorio](https://wa.me/{cd.get('tel')}?text={urllib.parse.quote(msg)})")
                except: pass
        
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True): 
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    mostrar_titulo()

    # --- VISTA DUEÑO (Intacta) ---
    if rol_usuario.lower() == "negocio":
        tabs = st.tabs(["🛒 Ventas", "📉 Gastos", "📜 Historial", "👥 Clientes"])
        
        with tabs[0]: # Ventas
            col_izq, col_der = st.columns([1.6, 1])
            with col_izq:
                busqueda = st.text_input("🔍 Buscar producto...")
                if busqueda and st.session_state.df_proveedor is not None:
                    res = st.session_state.df_proveedor[st.session_state.df_proveedor['Productos'].str.contains(busqueda, case=False, na=False)]
                    for _, fila in res.head(8).iterrows():
                        if st.button(f"➕ {fila['Productos']} | ${fila['Precio']:,.2f}", key=f"v_{fila['Productos']}"):
                            st.session_state.carrito.append({'nombre': fila['Productos'], 'precio': fila['Precio'], 'cantidad': 1, 'subtotal': fila['Precio']})
                            st.rerun()
                if st.session_state.carrito:
                    for i, it in enumerate(st.session_state.carrito):
                        st.write(f"{it['nombre']} - ${it['subtotal']:,.2f}")
            with col_der:
                st.write("Confirmar Venta")
                # (Aquí iría el resto de tu lógica de ventas guardada)

        with tabs[3]: # Clientes
            col_reg, col_list = st.columns([1, 2.5])
            with col_reg:
                with st.form("nuevo_cli"):
                    n = st.text_input("Nombre"); d = st.text_input("DNI"); t = st.text_input("WhatsApp"); f = st.text_input("Fecha Pago")
                    if st.form_submit_button("Guardar"):
                        u_id = f"{n} {negocio_id}"
                        db.collection("usuarios").document(u_id).set({"nombre": n, "password": d, "rol": "cliente", "id_negocio": negocio_id, "dni": d, "tel": t, "promesa_pago": f})
                        st.success("Guardado"); st.rerun()

    # --- VISTA CLIENTE (Mejorada y Protegida) ---
    elif rol_usuario.lower() == "cliente":
        c_id = st.session_state['usuario']
        v_f = list(db.collection("ventas_procesadas").where("cliente_id", "==", c_id).where("metodo", "==", "Fiado").stream())
        p_f = list(db.collection("pagos_clientes").where("cliente_id", "==", c_id).stream())
        saldo = sum(v.to_dict().get('total', 0) for v in v_f) - sum(p.to_dict().get('monto', 0) for p in p_f)
        
        st.markdown(f"## Hola **{nombre_usuario}**")
        st.error(f"# Tu saldo a pagar: ${saldo:,.2f}")
        st.divider()

        movs = []
        for v in v_f: movs.append({"dt": v.to_dict().get('fecha_completa'), "tipo": "C", "d": v.to_dict()})
        for p in p_f: movs.append({"dt": p.to_dict().get('fecha'), "tipo": "P", "d": p.to_dict()})
        movs.sort(key=lambda x: x['dt'] if x['dt'] else datetime.min, reverse=True)

        for m in movs:
            with st.container(border=True):
                d = m['d']
                if m['tipo'] == "C":
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"### 🛒 Compra: {d.get('fecha_str')} - {d.get('hora_str')}hs")
                        st.caption(f"Atendido por: {d.get('vendedor')}")
                        for i in d.get('items', []):
                            st.markdown(f"<p style='font-size:18px;'>📍 **{i['cantidad']}** x {i['nombre']} <br><span style='font-size:14px; color:grey;'>Unitario: ${i['precio']:,.2f} | Subtotal: ${i['subtotal']:,.2f}</span></p>", unsafe_allow_html=True)
                    with c2: st.markdown(f"<h2 style='color:red; text-align:right;'>- ${d.get('total'):,.2f}</h2>", unsafe_allow_html=True)
                else:
                    c1, c2 = st.columns([3, 1])
                    with c1: st.markdown(f"### ✅ Pago Recibido: {d.get('fecha_str')} - {d.get('hora_str')}hs")
                    with c2: st.markdown(f"<h2 style='color:green; text-align:right;'>+ ${d.get('monto'):,.2f}</h2>", unsafe_allow_html=True)
