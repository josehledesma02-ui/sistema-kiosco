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
                    'autenticado': True, 'usuario': u_input, 'rol': d.get('rol'), 
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

    with st.sidebar:
        if os.path.exists(IMG_SIDEBAR): st.image(IMG_SIDEBAR, width=150)
        st.write(f"👤 **{vendedor_nom}**")
        if st.button("🔴 Cerrar Sesión", use_container_width=True): 
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    mostrar_titulo()
    tabs = st.tabs(["🛒 Ventas", "📉 Gastos", "📜 Historial", "👥 Clientes"])

    with tabs[0]: # PESTAÑA VENTAS (CON PORCENTAJES)
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
                        it['cantidad'] = nueva_cant
                        it['subtotal'] = it['precio'] * it['cantidad']
                        st.rerun()
                    c3.write(f"${it['subtotal']:,.2f}")
                    if c4.button("❌", key=f"del_{i}"): st.session_state.carrito.pop(i); st.rerun()

        with col_der:
            st.markdown("### 📋 Datos de Cobro")
            c_docs = db.collection("usuarios").where("id_negocio", "==", negocio_id).where("rol", "==", "cliente").stream()
            dict_clientes = {"Consumidor Final": "final"}
            for c in c_docs:
                cd = c.to_dict(); dict_clientes[cd.get('nombre', 'Sin Nombre')] = c.id
            cliente_sel = st.selectbox("Cliente", list(dict_clientes.keys()))
            
            metodo = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Débito", "Crédito", "Fiado"])
            
            info_pago = ""
            if metodo == "Transferencia":
                info_pago = st.text_input("Cuenta") 
            
            st.divider()
            sub_t = sum(it['subtotal'] for it in st.session_state.carrito)
            
            c_desc, c_rec = st.columns(2)
            p_desc = c_desc.number_input("Descuento %", 0, 100, 0) # PORCENTAJE
            p_rec = c_rec.number_input("Recargo %", 0, 100, 0)    # PORCENTAJE
            
            # CÁLCULO FINAL
            monto_descuento = (sub_t * p_desc) / 100
            monto_recargo = (sub_t * p_rec) / 100
            total_f = sub_t - monto_descuento + monto_recargo

            st.markdown(f"<div style='background:#f0f2f6;padding:20px;border-radius:10px;text-align:center;border:2px solid #1E88E5'><p style='margin:0'>TOTAL CON DESC/REC</p><h1 style='color:#1E88E5;margin:0'>${total_f:,.2f}</h1><small>Subtotal: ${sub_t:,.2f}</small></div>", unsafe_allow_html=True)
            
            if st.button("🚀 REGISTRAR VENTA", use_container_width=True, type="primary"):
                if st.session_state.carrito:
                    ahora = datetime.now()
                    db.collection("ventas_procesadas").add({
                        "vendedor": vendedor_nom, "id_negocio": negocio_id, "cliente": cliente_sel,
                        "cliente_id": dict_clientes[cliente_sel], "items": st.session_state.carrito, 
                        "total": total_f, "metodo": metodo, "info_pago": info_pago,
                        "p_descuento": p_desc, "p_recargo": p_rec,
                        "fecha_completa": ahora, "fecha_str": ahora.strftime("%d/%m/%Y"), "hora_str": ahora.strftime("%H:%M")
                    })
                    st.session_state.carrito = []; st.success("Venta Exitosa"); st.rerun()

    with tabs[3]: # PESTAÑA CLIENTES (CONSERVADA)
        col_reg, col_list = st.columns([1, 2])
        with col_reg:
            st.subheader("➕ Nuevo Cliente")
            with st.form("form_nuevo_cliente"):
                nom_c = st.text_input("Nombre y Apellido")
                dni_c = st.text_input("DNI (Su contraseña)")
                tel_c = st.text_input("WhatsApp")
                f_pago = st.text_input("Acuerdo de pago (Ej: Los 05)")
                if st.form_submit_button("Guardar Cliente"):
                    if nom_c and dni_c:
                        u_id = f"{nom_c.lower().replace(' ', '')}_{negocio_id}"
                        db.collection("usuarios").document(u_id).set({
                            "nombre": nom_c, "password": dni_c, "rol": "cliente",
                            "id_negocio": negocio_id, "dni": dni_c, "tel": tel_c,
                            "fecha_acuerdo_pago": f_pago
                        })
                        st.success(f"✅ Cliente guardado"); st.rerun()
        
        with col_list:
            st.subheader("👥 Estado de Deudas")
            clis = db.collection("usuarios").where("id_negocio", "==", negocio_id).where("rol", "==", "cliente").stream()
            for c in clis:
                cd = c.to_dict()
                v_f = db.collection("ventas_procesadas").where("cliente_id", "==", c.id).where("metodo", "==", "Fiado").stream()
                lista_v = [v for v in v_f]
                deuda = sum(v.to_dict().get('total', 0) for v in lista_v)
                
                with st.expander(f"👤 {cd.get('nombre')} | 💰 Deuda: ${deuda:,.2f}"):
                    st.write(f"**DNI:** {cd.get('dni', '---')} | **WhatsApp:** {cd.get('tel', '-')}")
                    st.write(f"**Acuerdo:** {cd.get('fecha_acuerdo_pago', '-')}")
                    if deuda > 0:
                        if st.button(f"✅ Liquidar Deuda (${deuda:,.2f})", key=f"p_{c.id}"):
                            for v in lista_v:
                                db.collection("ventas_procesadas").document(v.id).update({"metodo": "Pagado (Antes Fiado)"})
                            st.rerun()

    with tabs[1]: # GASTOS
        st.subheader("Gastos")
        with st.form("g_form"):
            m = st.number_input("Monto", 0.0); d = st.text_input("Detalle")
            if st.form_submit_button("Guardar"):
                db.collection("gastos").add({"monto": m, "detalle": d, "id_negocio": negocio_id, "fecha": datetime.now()})
                st.success("Gasto guardado")

    with tabs[2]: # HISTORIAL
        st.subheader("Historial")
        h_ref = db.collection("ventas_procesadas").where("id_negocio", "==", negocio_id).order_by("fecha_completa", direction=firestore.Query.DESCENDING).limit(10).stream()
        for h in h_ref:
            hd = h.to_dict()
            with st.expander(f"{hd['fecha_str']} | {hd['cliente']} | ${hd['total']:,.2f}"):
                for i in hd['items']: st.write(f"- {i['cantidad']}x {i['nombre']}")
