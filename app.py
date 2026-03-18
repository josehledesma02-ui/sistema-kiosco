import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import os

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

def limpiar_precio_final(valor):
    if pd.isna(valor) or str(valor).strip() == "": return 0.0
    s = str(valor).strip().replace('$', '').replace(' ', '').replace(',', '')
    try: return float(s)
    except: return 0.0

def cargar_datos_proveedor():
    try:
        df = pd.read_csv(URL_PROVEEDOR_CSV, header=1)
        df.columns = df.columns.astype(str).str.strip()
        col_prod = [c for c in df.columns if any(kw in c.lower() for kw in ['producto', 'articulo', 'descrip'])]
        col_prec = [c for c in df.columns if any(kw in c.lower() for kw in ['precio', 'venta', 'valor'])]
        if col_prod and col_prec:
            df = df.rename(columns={col_prod[0]: 'Productos', col_prec[0]: 'Precio_Raw'})
            df['Precio'] = df['Precio_Raw'].apply(limpiar_precio_final)
            df = df.dropna(subset=['Productos'])
            df = df[(df['Productos'] != "") & (df['Precio'] > 0)]
            st.session_state.df_proveedor = df
    except: pass

if st.session_state.df_proveedor is None: cargar_datos_proveedor()

# ==========================================
# 3. LOGIN
# ==========================================
if not st.session_state['autenticado']:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        if os.path.exists(IMG_LOGIN): st.image(IMG_LOGIN, use_container_width=True)
        mostrar_titulo()
        u_input = st.text_input("Usuario").strip().lower()
        c_input = st.text_input("Contraseña (DNI)", type="password").strip()
        if st.button("Ingresar", use_container_width=True, type="primary"):
            user_ref = db.collection("usuarios").document(u_input).get()
            if user_ref.exists and str(user_ref.to_dict().get('password')) == c_input:
                d = user_ref.to_dict()
                st.session_state.update({
                    'autenticado': True, 'usuario': u_input, 
                    'rol': str(d.get('rol')).strip().lower(),
                    'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre'),
                    'id_usuario': u_input
                })
                st.rerun()
            else: st.error("❌ Usuario o Contraseña incorrectos")

# ==========================================
# 4. INTERFAZ SEGÚN ROL
# ==========================================
else:
    negocio_id = st.session_state['id_negocio']
    vendedor_nom = st.session_state['nombre_real'] or st.session_state['usuario']
    rol_actual = st.session_state['rol']

    with st.sidebar:
        if os.path.exists(IMG_SIDEBAR): st.image(IMG_SIDEBAR, width=150)
        st.write(f"👤 **{vendedor_nom}**")
        if st.button("🔴 Cerrar Sesión", use_container_width=True): 
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    mostrar_titulo()

    # --- VISTA NEGOCIO ---
    if rol_actual == "negocio":
        tabs = st.tabs(["🛒 Ventas", "📉 Gastos", "📜 Historial", "👥 Clientes"])

        with tabs[0]: # VENTAS
            col_izq, col_der = st.columns([1.6, 1])
            with col_izq:
                busqueda = st.text_input("🔍 Buscar producto...", placeholder="Ej: Aceite...")
                if busqueda and st.session_state.df_proveedor is not None:
                    res = st.session_state.df_proveedor[st.session_state.df_proveedor['Productos'].str.contains(busqueda, case=False, na=False)]
                    for _, fila in res.head(8).iterrows():
                        n, p = fila['Productos'], fila['Precio']
                        if st.button(f"➕ {n} | ${p:,.2f}", key=f"btn_{n}"):
                            found = False
                            for item in st.session_state.carrito:
                                if item['nombre'] == n:
                                    item['cantidad'] += 1
                                    item['subtotal'] = item['cantidad'] * item['precio']
                                    found = True; break
                            if not found: st.session_state.carrito.append({'nombre': n, 'precio': p, 'cantidad': 1, 'subtotal': p})
                            st.rerun()
                st.divider()
                if st.session_state.carrito:
                    for i, it in enumerate(st.session_state.carrito):
                        c1, c2, c3, c4 = st.columns([3, 1, 1, 0.5])
                        c1.write(f"**{it['nombre']}**")
                        nueva_cant = c2.number_input("Cant", 1, 500, it['cantidad'], key=f"c_{i}", label_visibility="collapsed")
                        if nueva_cant != it['cantidad']:
                            it['cantidad'] = nueva_cant; it['subtotal'] = it['precio'] * it['cantidad']; st.rerun()
                        c3.write(f"${it['subtotal']:,.2f}")
                        if c4.button("❌", key=f"del_{i}"): st.session_state.carrito.pop(i); st.rerun()

            with col_der:
                st.markdown("### 📋 Datos de Cobro")
                c_docs = db.collection("usuarios").where("id_negocio", "==", negocio_id).where("rol", "==", "cliente").stream()
                dict_clientes = {"Consumidor Final": "final"}
                for c in c_docs: dict_clientes[c.to_dict().get('nombre', 'Sin Nombre')] = c.id
                cliente_sel = st.selectbox("Cliente", list(dict_clientes.keys()))
                metodo = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Débito", "Crédito", "Fiado"])
                info_pago = ""
                if metodo == "Transferencia": info_pago = st.text_input("Cuenta")
                st.divider()
                sub_t = sum(it['subtotal'] for it in st.session_state.carrito)
                c_desc, c_rec = st.columns(2)
                p_desc = c_desc.number_input("Descuento %", 0, 100, 0)
                p_rec = c_rec.number_input("Recargo %", 0, 100, 0)
                total_f = sub_t - (sub_t * p_desc / 100) + (sub_t * p_rec / 100)
                st.markdown(f"<div style='background:#f0f2f6;padding:20px;border-radius:10px;text-align:center;border:2px solid #1E88E5'><p style='margin:0'>TOTAL FINAL</p><h1 style='color:#1E88E5;margin:0'>${total_f:,.2f}</h1></div>", unsafe_allow_html=True)
                if st.button("🚀 REGISTRAR VENTA", use_container_width=True, type="primary"):
                    if st.session_state.carrito:
                        ahora = datetime.now()
                        db.collection("ventas_procesadas").add({
                            "vendedor": vendedor_nom, "id_negocio": negocio_id, "cliente": cliente_sel,
                            "cliente_id": dict_clientes[cliente_sel], "items": st.session_state.carrito, 
                            "total": total_f, "metodo": metodo, "info_pago": info_pago,
                            "p_descuento": p_desc, "p_recargo": p_rec, "fecha_completa": ahora, 
                            "fecha_str": ahora.strftime("%d/%m/%Y"), "hora_str": ahora.strftime("%H:%M")
                        })
                        st.session_state.carrito = []; st.success("Venta Exitosa"); st.rerun()

        with tabs[1]: # GASTOS
            st.subheader("📉 Gastos")
            with st.form("g_form"):
                m = st.number_input("Monto", 0.0); d = st.text_input("Detalle")
                if st.form_submit_button("Guardar Gasto"):
                    db.collection("gastos").add({"monto": m, "detalle": d, "id_negocio": negocio_id, "fecha": datetime.now()})
                    st.success("Gasto guardado")

        with tabs[2]: # HISTORIAL
            st.subheader("📜 Historial de Ventas")
            h_ref = db.collection("ventas_procesadas").where("id_negocio", "==", negocio_id).order_by("fecha_completa", direction=firestore.Query.DESCENDING).limit(15).stream()
            for h in h_ref:
                hd = h.to_dict()
                with st.expander(f"{hd.get('fecha_str', '')} | {hd.get('cliente', '')} | ${hd.get('total', 0):,.2f}"):
                    for i in hd.get('items', []): st.write(f"- {i['cantidad']}x {i['nombre']}")

        with tabs[3]: # CLIENTES (LISTA DE CUENTAS)
            col_reg, col_list = st.columns([1, 2.5])
            with col_reg:
                st.subheader("➕ Nuevo Cliente")
                with st.form("form_nuevo_cliente"):
                    nom_c = st.text_input("Nombre y Apellido")
                    dni_c = st.text_input("DNI")
                    tel_c = st.text_input("WhatsApp")
                    f_pago = st.text_input("Acuerdo de pago")
                    if st.form_submit_button("Guardar"):
                        u_id = f"{nom_c.lower().replace(' ', '')}_{negocio_id}"
                        db.collection("usuarios").document(u_id).set({"nombre": nom_c, "password": dni_c, "rol": "cliente", "id_negocio": negocio_id, "dni": dni_c, "tel": tel_c, "promesa_pago": f_pago})
                        st.success("✅ Cliente guardado"); st.rerun()

            with col_list:
                st.subheader("👥 Cuentas Corrientes")
                clis = db.collection("usuarios").where("id_negocio", "==", negocio_id).where("rol", "==", "cliente").stream()
                for c in clis:
                    cd = c.to_dict()
                    v_f = list(db.collection("ventas_procesadas").where("cliente_id", "==", c.id).where("metodo", "==", "Fiado").stream())
                    p_f = list(db.collection("pagos_clientes").where("cliente_id", "==", c.id).stream())
                    saldo = sum(v.to_dict().get('total', 0) for v in v_f) - sum(p.to_dict().get('monto', 0) for p in p_f)
                    with st.expander(f"👤 {cd.get('nombre')} | Saldo: ${saldo:,.2f}"):
                        c_i, c_p = st.columns([1.5, 1])
                        with c_i:
                            # AQUÍ VOLVÍ A AGREGAR EL WHATSAPP (tel)
                            st.write(f"**DNI:** {cd.get('dni', '---')} | **WA:** {cd.get('tel', '---')}")
                            st.write(f"**Promesa:** :blue[{cd.get('promesa_pago', '---')}]")
                        
                        with c_p:
                            m_entrega = st.number_input("Ingresar entrega $", 0.0, key=f"p_{c.id}")
                            if st.button("Registrar Pago", key=f"btn_{c.id}", use_container_width=True):
                                if m_entrega > 0:
                                    db.collection("pagos_clientes").add({"cliente_id": c.id, "monto": m_entrega, "fecha": datetime.now(), "fecha_str": datetime.now().strftime("%d/%m/%Y"), "hora_str": datetime.now().strftime("%H:%M"), "id_negocio": negocio_id})
                                    st.success("Registrado"); st.rerun()
                        st.divider()
                        movs = []
                        for v in v_f:
                            vd = v.to_dict()
                            it_l = ", ".join([f"{i['cantidad']}x {i['nombre']}" for i in vd.get('items', [])])
                            movs.append({"dt": vd.get('fecha_completa'), "t": f"🔴 {vd['fecha_str']} - Compra: ${vd['total']}", "s": it_l})
                        for p in p_f:
                            pd = p.to_dict()
                            movs.append({"dt": pd.get('fecha'), "t": f"🟢 {pd['fecha_str']} - Pago: ${pd['monto']}", "s": "Entrega efectivo"})
                        for m in sorted(movs, key=lambda x: x['dt'] if x['dt'] else datetime.min, reverse=True):
                            st.write(m['t']); st.caption(m['s'])

    # --- VISTA CLIENTE ---
    elif rol_actual == "cliente":
        c_id = st.session_state['usuario']
        v_f = list(db.collection("ventas_procesadas").where("cliente_id", "==", c_id).where("metodo", "==", "Fiado").stream())
        p_f = list(db.collection("pagos_clientes").where("cliente_id", "==", c_id).stream())
        saldo = sum(v.to_dict().get('total', 0) for v in v_f) - sum(p.to_dict().get('monto', 0) for p in p_f)
        
        st.markdown(f"### Hola {vendedor_nom}, tu saldo actual es:")
        st.error(f"# ${saldo:,.2f}")
        st.divider()
        st.subheader("📜 Tus Compras y Pagos")
        movs = []
        for v in v_f:
            vd = v.to_dict()
            movs.append({"dt": vd.get('fecha_completa'), "t": f"🛒 Compra {vd.get('fecha_str')}", "m": f"- ${vd.get('total')}", "s": ", ".join([f"{i['cantidad']}x {i['nombre']}" for i in vd.get('items', [])])})
        for p in p_f:
            pd = p.to_dict()
            movs.append({"dt": pd.get('fecha'), "t": f"✅ Pago {pd.get('fecha_str')}", "m": f"+ ${pd.get('monto')}", "s": "Entrega de dinero"})
        for m in sorted(movs, key=lambda x: x['dt'] if x['dt'] else datetime.min, reverse=True):
            st.write(f"**{m['t']}** | {m['s']} | **{m['m']}**")
            st.divider()
