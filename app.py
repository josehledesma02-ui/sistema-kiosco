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
# 3. LOGIN (NEGOCIO + NOMBRE + DNI)
# ==========================================
if not st.session_state['autenticado']:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        if os.path.exists(IMG_LOGIN): st.image(IMG_LOGIN, use_container_width=True)
        mostrar_titulo()
        
        negocio_input = st.text_input("Negocio (Ej: fabricon)").strip().lower()
        u_input = st.text_input("Nombre y Apellido (Ej: María Molina)").strip()
        c_input = st.text_input("Contraseña (DNI)", type="password").strip()
        
        if st.button("Ingresar", use_container_width=True, type="primary"):
            if negocio_input and u_input and c_input:
                # El ID se forma: "Nombre Apellido negocio"
                id_usuario_compuesto = f"{u_input} {negocio_input}"
                user_ref = db.collection("usuarios").document(id_usuario_compuesto).get()
                
                if user_ref.exists:
                    d = user_ref.to_dict()
                    if str(d.get('password')) == c_input:
                        st.session_state.update({
                            'autenticado': True, 'usuario': id_usuario_compuesto, 
                            'rol': str(d.get('rol')).strip().lower(),
                            'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre'),
                            'id_usuario': id_usuario_compuesto
                        })
                        st.rerun()
                    else: st.error("❌ Contraseña (DNI) incorrecta")
                else: st.error(f"❌ No se encontró '{u_input}' en '{negocio_input}'")
            else: st.warning("⚠️ Completa todos los campos")

# ==========================================
# 4. INTERFAZ PRINCIPAL
# ==========================================
else:
    negocio_id = st.session_state['id_negocio']
    vendedor_nom = st.session_state['nombre_real'] or st.session_state['usuario']
    rol_actual = st.session_state['rol']

    # --- SIDEBAR (NOTIFICACIONES) ---
    with st.sidebar:
        if os.path.exists(IMG_SIDEBAR): st.image(IMG_SIDEBAR, width=150)
        st.write(f"👤 **{vendedor_nom}**")
        st.divider()
        st.subheader("🔔 Notificaciones")

        if rol_actual == "negocio":
            st.markdown("📅 **Próximos Cobros**")
            clis_ref = db.collection("usuarios").where("id_negocio", "==", negocio_id).where("rol", "==", "cliente").stream()
            hoy = datetime.now()
            for c in clis_ref:
                cd = c.to_dict()
                f_p = cd.get('promesa_pago', '')
                try:
                    f_dt = datetime.strptime(f_p, "%d/%m/%Y")
                    if (f_dt - hoy).days <= 3:
                        v_f = list(db.collection("ventas_procesadas").where("cliente_id", "==", c.id).where("metodo", "==", "Fiado").stream())
                        p_f = list(db.collection("pagos_clientes").where("cliente_id", "==", c.id).stream())
                        saldo = sum(v.to_dict().get('total', 0) for v in v_f) - sum(p.to_dict().get('monto', 0) for p in p_f)
                        if saldo > 0:
                            with st.container(border=True):
                                st.write(f"⚠️ **{cd.get('nombre')}**")
                                st.caption(f"Vence: {f_p} | ${saldo:,.2f}")
                                msg = f"Hola {cd.get('nombre')}, te recuerdo que tu fecha de pago es el {f_p}. Saldo: ${saldo:,.2f}."
                                st.markdown(f"[📲 Avisar](https://wa.me/{cd.get('tel')}?text={urllib.parse.quote(msg)})")
                except: pass

        st.markdown("🚀 **Ofertas**")
        if st.session_state.df_proveedor is not None:
            of = st.session_state.df_proveedor[st.session_state.df_proveedor['Productos'].str.contains('OFERTA|PROMO', case=False, na=False)]
            for _, r in of.head(3).iterrows():
                st.info(f"🏷️ {r['Productos']}\n\n**${r['Precio']:,.2f}**")

        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True): 
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    mostrar_titulo()

    # --- VISTA DUEÑO ---
    if rol_actual == "negocio":
        tabs = st.tabs(["🛒 Ventas", "📉 Gastos", "📜 Historial", "👥 Clientes"])

        with tabs[0]: # VENTAS (BLOQUEADA)
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
                        it['cantidad'] = c2.number_input("Cant", 1, 500, it['cantidad'], key=f"c_{i}", label_visibility="collapsed")
                        it['subtotal'] = it['precio'] * it['cantidad']
                        c3.write(f"${it['subtotal']:,.2f}")
                        if c4.button("❌", key=f"del_{i}"): st.session_state.carrito.pop(i); st.rerun()

            with col_der:
                c_docs = db.collection("usuarios").where("id_negocio", "==", negocio_id).where("rol", "==", "cliente").stream()
                dict_clientes = {"Consumidor Final": "final"}
                for c in c_docs: dict_clientes[c.to_dict().get('nombre', 'Sin Nombre')] = c.id
                cliente_sel = st.selectbox("Cliente", list(dict_clientes.keys()))
                metodo = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Fiado"])
                total_f = sum(it['subtotal'] for it in st.session_state.carrito)
                st.markdown(f"## Total: ${total_f:,.2f}")
                if st.button("🚀 REGISTRAR VENTA", use_container_width=True, type="primary"):
                    if st.session_state.carrito:
                        ahora = datetime.now()
                        db.collection("ventas_procesadas").add({
                            "vendedor": vendedor_nom, "id_negocio": negocio_id, "cliente": cliente_sel,
                            "cliente_id": dict_clientes[cliente_sel], "items": st.session_state.carrito, 
                            "total": total_f, "metodo": metodo, "fecha_completa": ahora, 
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
            h_ref = db.collection("ventas_procesadas").where("id_negocio", "==", negocio_id).order_by("fecha_completa", direction=firestore.Query.DESCENDING).limit(15).stream()
            for h in h_ref:
                hd = h.to_dict()
                with st.expander(f"{hd.get('fecha_str')} {hd.get('hora_str')} | {hd.get('cliente')} | ${hd.get('total'):,.2f}"):
                    for i in hd.get('items', []): st.write(f"- {i['cantidad']}x {i['nombre']}")

        with tabs[3]: # CLIENTES (BLOQUEADA)
            col_reg, col_list = st.columns([1, 2.5])
            with col_reg:
                with st.form("form_nuevo_cliente"):
                    nom_c = st.text_input("Nombre y Apellido")
                    dni_c = st.text_input("DNI")
                    tel_c = st.text_input("WhatsApp")
                    f_pago = st.text_input("Fecha Pago (DD/MM/AAAA)")
                    if st.form_submit_button("Guardar"):
                        u_id = f"{nom_c} {negocio_id}" # Formato: Nombre Apellido negocio
                        db.collection("usuarios").document(u_id).set({
                            "nombre": nom_c, "password": dni_c, "rol": "cliente", 
                            "id_negocio": negocio_id, "dni": dni_c, "tel": tel_c, "promesa_pago": f_pago
                        })
                        st.success("✅ Cliente guardado"); st.rerun()

            with col_list:
                clis = db.collection("usuarios").where("id_negocio", "==", negocio_id).where("rol", "==", "cliente").stream()
                for c in clis:
                    cd = c.to_dict()
                    v_f = list(db.collection("ventas_procesadas").where("cliente_id", "==", c.id).where("metodo", "==", "Fiado").stream())
                    p_f = list(db.collection("pagos_clientes").where("cliente_id", "==", c.id).stream())
                    saldo = sum(v.to_dict().get('total', 0) for v in v_f) - sum(p.to_dict().get('monto', 0) for p in p_f)
                    with st.expander(f"👤 {cd.get('nombre')} | Saldo: ${saldo:,.2f}"):
                        m_entrega = st.number_input("Ingresar entrega $", 0.0, key=f"p_{c.id}")
                        if st.button("Registrar Pago", key=f"btn_{c.id}"):
                            if m_entrega > 0:
                                db.collection("pagos_clientes").add({"cliente_id": c.id, "monto": m_entrega, "fecha": datetime.now(), "fecha_str": datetime.now().strftime("%d/%m/%Y"), "hora_str": datetime.now().strftime("%H:%M"), "id_negocio": negocio_id})
                                nueva_f = sumar_un_mes(cd.get('promesa_pago', '01/01/2026'))
                                db.collection("usuarios").document(c.id).update({"promesa_pago": nueva_f}); st.rerun()

    # --- VISTA CLIENTE (ACTUALIZADA) ---
    elif rol_actual == "cliente":
        c_id = st.session_state['usuario']
        v_f = list(db.collection("ventas_procesadas").where("cliente_id", "==", c_id).where("metodo", "==", "Fiado").stream())
        p_f = list(db.collection("pagos_clientes").where("cliente_id", "==", c_id).stream())
        saldo = sum(v.to_dict().get('total', 0) for v in v_f) - sum(p.to_dict().get('monto', 0) for p in p_f)
        
        st.markdown(f"## Hola **{st.session_state['nombre_real']}**")
        st.error(f"# Tu saldo actual: ${saldo:,.2f}")
        st.divider()

        movs = []
        for v in v_f:
            vd = v.to_dict()
            movs.append({"dt": vd.get('fecha_completa'), "tipo": "C", "d": vd})
        for p in p_f:
            pd = p.to_dict()
            movs.append({"dt": pd.get('fecha'), "tipo": "P", "d": pd})

        movs.sort(key=lambda x: x['dt'] if x['dt'] else datetime.min, reverse=True)

        for m in movs:
            with st.container(border=True):
                d = m['d']
                if m['tipo'] == "C":
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"### 🛒 Compra: {d.get('fecha_str')} - {d.get('hora_str')}hs")
                        st.caption(f"Vendedor: {d.get('vendedor')}")
                        for i in d.get('items', []):
                            st.markdown(f"<p style='font-size:18px;'>📍 **{i['cantidad']}** x {i['nombre']} <br><span style='font-size:14px; color:grey;'>Unitario: ${i['precio']:,.2f} | Subtotal: ${i['subtotal']:,.2f}</span></p>", unsafe_allow_html=True)
                    with c2: st.markdown(f"<h2 style='color:red; text-align:right;'>- ${d.get('total'):,.2f}</h2>", unsafe_allow_html=True)
                else:
                    c1, c2 = st.columns([3, 1])
                    with c1: st.markdown(f"### ✅ Pago Recibido: {d.get('fecha_str')} - {d.get('hora_str')}hs")
                    with c2: st.markdown(f"<h2 style='color:green; text-align:right;'>+ ${d.get('monto'):,.2f}</h2>", unsafe_allow_html=True)
