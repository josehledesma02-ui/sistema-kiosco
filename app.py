import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime, timedelta
import os
import urllib.parse

# ==========================================
# 0. CONFIGURACIÓN VISUAL Y FUNCIONES
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
# 4. INTERFAZ PRINCIPAL
# ==========================================
else:
    negocio_id = st.session_state['id_negocio']
    vendedor_nom = st.session_state['nombre_real'] or st.session_state['usuario']
    rol_actual = st.session_state['rol']

    with st.sidebar:
        if os.path.exists(IMG_SIDEBAR): st.image(IMG_SIDEBAR, width=150)
        st.write(f"👤 **{vendedor_nom}**")
        st.divider()
        st.subheader("🔔 Notificaciones")
        
        # Alertas de Cobro
        st.markdown("📅 **Próximos Cobros**")
        clis_ref = db.collection("usuarios").where("id_negocio", "==", negocio_id).where("rol", "==", "cliente").stream()
        hoy = datetime.now()
        for c in clis_ref:
            cd = c.to_dict()
            fecha_p = cd.get('promesa_pago', '')
            try:
                fecha_dt = datetime.strptime(fecha_p, "%d/%m/%Y")
                if (fecha_dt - hoy).days <= 3:
                    v_f = list(db.collection("ventas_procesadas").where("cliente_id", "==", c.id).where("metodo", "==", "Fiado").stream())
                    p_f = list(db.collection("pagos_clientes").where("cliente_id", "==", c.id).stream())
                    saldo = sum(v.to_dict().get('total', 0) for v in v_f) - sum(p.to_dict().get('monto', 0) for p in p_f)
                    if saldo > 0:
                        with st.container(border=True):
                            st.markdown(f"⚠️ **{cd.get('nombre')}**")
                            st.caption(f"Vence: {fecha_p} | Saldo: ${saldo:,.2f}")
                            msg = f"Hola {cd.get('nombre')}, te recuerdo amablemente que se acerca tu fecha de pago ({fecha_p}). Tu saldo pendiente es de ${saldo:,.2f}. ¡Muchas gracias!"
                            msg_url = urllib.parse.quote(msg); tel = str(cd.get('tel')).replace(" ", "").replace("+", "")
                            st.markdown(f"[📲 Avisar por WA](https://wa.me/{tel}?text={msg_url})")
            except: pass
        
        st.divider()
        st.markdown("🚀 **Ofertas del Día**")
        if st.session_state.df_proveedor is not None:
            ofertas = st.session_state.df_proveedor[st.session_state.df_proveedor['Productos'].str.contains('OFERTA|PROMO|DESCUENTO', case=False, na=False)]
            if not ofertas.empty:
                for _, row in ofertas.head(5).iterrows():
                    st.info(f"🏷️ {row['Productos']}\n\n**${row['Precio']:,.2f}**")
        
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True): 
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    mostrar_titulo()

    # --- VISTA NEGOCIO (SIN CAMBIOS) ---
    if rol_actual == "negocio":
        tabs = st.tabs(["🛒 Ventas", "📉 Gastos", "📜 Historial", "👥 Clientes"])
        # (Aquí va el mismo código de las pestañas de dueño que ya funcionaba)
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
                                    item['cantidad'] += 1; item['subtotal'] = item['cantidad'] * item['precio']; found = True; break
                            if not found: st.session_state.carrito.append({'nombre': n, 'precio': p, 'cantidad': 1, 'subtotal': p})
                            st.rerun()
                if st.session_state.carrito:
                    for i, it in enumerate(st.session_state.carrito):
                        c1, c2, c3, c4 = st.columns([3, 1, 1, 0.5])
                        c1.write(f"**{it['nombre']}**")
                        nueva_cant = c2.number_input("Cant", 1, 500, it['cantidad'], key=f"c_{i}", label_visibility="collapsed")
                        if nueva_cant != it['cantidad']: it['cantidad'] = nueva_cant; it['subtotal'] = it['precio'] * it['cantidad']; st.rerun()
                        c3.write(f"${it['subtotal']:,.2f}")
                        if c4.button("❌", key=f"del_{i}"): st.session_state.carrito.pop(i); st.rerun()
            with col_der:
                c_docs = db.collection("usuarios").where("id_negocio", "==", negocio_id).where("rol", "==", "cliente").stream()
                dict_clientes = {"Consumidor Final": "final"}
                for c in c_docs: dict_clientes[c.to_dict().get('nombre', 'Sin Nombre')] = c.id
                cliente_sel = st.selectbox("Cliente", list(dict_clientes.keys())); metodo = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Débito", "Crédito", "Fiado"])
                sub_t = sum(it['subtotal'] for it in st.session_state.carrito)
                c_desc, c_rec = st.columns(2); p_desc = c_desc.number_input("Descuento %", 0, 100, 0); p_rec = c_rec.number_input("Recargo %", 0, 100, 0)
                total_f = sub_t - (sub_t * p_desc / 100) + (sub_t * p_rec / 100)
                st.markdown(f"<h1 style='color:#1E88E5;'>Total: ${total_f:,.2f}</h1>", unsafe_allow_html=True)
                if st.button("🚀 REGISTRAR VENTA", use_container_width=True, type="primary"):
                    if st.session_state.carrito:
                        ahora = datetime.now()
                        db.collection("ventas_procesadas").add({"vendedor": vendedor_nom, "id_negocio": negocio_id, "cliente": cliente_sel, "cliente_id": dict_clientes[cliente_sel], "items": st.session_state.carrito, "total": total_f, "metodo": metodo, "fecha_completa": ahora, "fecha_str": ahora.strftime("%d/%m/%Y"), "hora_str": ahora.strftime("%H:%M")})
                        st.session_state.carrito = []; st.success("Venta Exitosa"); st.rerun()
        # ... Resto de pestañas de negocio se mantienen igual ...
        with tabs[1]: # GASTOS
            with st.form("g_form"):
                m = st.number_input("Monto", 0.0); d = st.text_input("Detalle")
                if st.form_submit_button("Guardar Gasto"):
                    db.collection("gastos").add({"monto": m, "detalle": d, "id_negocio": negocio_id, "fecha": datetime.now()})
                    st.success("Gasto guardado")
        with tabs[2]: # HISTORIAL
            h_ref = db.collection("ventas_procesadas").where("id_negocio", "==", negocio_id).order_by("fecha_completa", direction=firestore.Query.DESCENDING).limit(15).stream()
            for h in h_ref:
                hd = h.to_dict(); 
                with st.expander(f"{hd.get('fecha_str')} {hd.get('hora_str')} | {hd.get('cliente')} | ${hd.get('total'):,.2f}"):
                    for i in hd.get('items', []): st.write(f"- {i['cantidad']}x {i['nombre']}")
        with tabs[3]: # CLIENTES
            clis = db.collection("usuarios").where("id_negocio", "==", negocio_id).where("rol", "==", "cliente").stream()
            for c in clis:
                cd = c.to_dict(); v_f = list(db.collection("ventas_procesadas").where("cliente_id", "==", c.id).where("metodo", "==", "Fiado").stream())
                p_f = list(db.collection("pagos_clientes").where("cliente_id", "==", c.id).stream()); saldo = sum(v.to_dict().get('total', 0) for v in v_f) - sum(p.to_dict().get('monto', 0) for p in p_f)
                with st.expander(f"👤 {cd.get('nombre')} | Saldo: ${saldo:,.2f}"):
                    c_i, c_p = st.columns([1.5, 1])
                    with c_i: st.write(f"**DNI:** {cd.get('dni')} | **WA:** {cd.get('tel')}"); st.write(f"📅 **Próximo Pago:** {cd.get('promesa_pago')}")
                    with c_p:
                        m_entrega = st.number_input("Ingresar entrega $", 0.0, key=f"p_{c.id}")
                        if st.button("Registrar Pago", key=f"btn_{c.id}"):
                            if m_entrega > 0:
                                db.collection("pagos_clientes").add({"cliente_id": c.id, "monto": m_entrega, "fecha": datetime.now(), "fecha_str": datetime.now().strftime("%d/%m/%Y"), "hora_str": datetime.now().strftime("%H:%M"), "id_negocio": negocio_id})
                                nueva_p = sumar_un_mes(cd.get('promesa_pago', datetime.now().strftime("%d/%m/%Y"))); db.collection("usuarios").document(c.id).update({"promesa_pago": nueva_p}); st.rerun()

    # ==========================================
    # 5. VISTA CLIENTE (ACTUALIZADA)
    # ==========================================
    elif rol_actual == "cliente":
        c_id = st.session_state['usuario']
        v_f = list(db.collection("ventas_procesadas").where("cliente_id", "==", c_id).where("metodo", "==", "Fiado").stream())
        p_f = list(db.collection("pagos_clientes").where("cliente_id", "==", c_id).stream())
        saldo = sum(v.to_dict().get('total', 0) for v in v_f) - sum(p.to_dict().get('monto', 0) for p in p_f)
        
        st.markdown(f"<h2 style='color:#333;'>Hola {vendedor_nom}, tu saldo actual es:</h2>", unsafe_allow_html=True)
        st.error(f"# ${saldo:,.2f}")
        st.divider()
        
        st.markdown("<h3 style='color:#1E88E5;'>📜 Detalle de tus Compras y Pagos</h3>", unsafe_allow_html=True)
        
        movs = []
        for v in v_f:
            vd = v.to_dict()
            movs.append({
                "dt": vd.get('fecha_completa'), "tipo": "COMPRA",
                "titulo": f"🛒 Compra - {vd.get('fecha_str')} a las {vd.get('hora_str')}",
                "vendedor": vd.get('vendedor', 'Negocio'),
                "total": vd.get('total', 0),
                "items": vd.get('items', [])
            })
        for p in p_f:
            pd = p.to_dict()
            movs.append({
                "dt": pd.get('fecha'), "tipo": "PAGO",
                "titulo": f"✅ Pago Recibido - {pd.get('fecha_str')} a las {pd.get('hora_str')}",
                "vendedor": "Caja",
                "total": pd.get('monto', 0),
                "items": []
            })
        
        # Ordenamos por fecha y hora (lo más nuevo arriba)
        for m in sorted(movs, key=lambda x: x['dt'] if x['dt'] else datetime.min, reverse=True):
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"#### {m['titulo']}")
                    st.caption(f"Atendido por: {m['vendedor']}")
                    
                    if m['tipo'] == "COMPRA":
                        st.markdown("**Productos:**")
                        for i in m['items']:
                            # Calculamos unitario (precio / cantidad)
                            u = i['precio']
                            st.markdown(f"- **{i['cantidad']}** x {i['nombre']} | *Unitario:* ${u:,.2f} | *Subtotal:* **${i['subtotal']:,.2f}**")
                
                with col2:
                    st.write("") # Espacio
                    color = "red" if m['tipo'] == "COMPRA" else "green"
                    signo = "-" if m['tipo'] == "COMPRA" else "+"
                    st.markdown(f"<h3 style='color:{color}; text-align:right;'>{signo} ${m['total']:,.2f}</h3>", unsafe_allow_html=True)
