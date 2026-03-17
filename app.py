import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import os

# ==========================================
# 0. CONFIGURACIÓN VISUAL Y DE PÁGINA
# ==========================================
st.set_page_config(page_title="JL Gestión Pro", page_icon="🛍️", layout="wide")

# Archivos y URLs
ID_HOJA = "1-ay_xIqYItwOaXe80VUsEmh4gsANrk9PH72aZcUD54g"
URL_PROVEEDOR_CSV = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/export?format=csv"
IMG_LOGIN = "logo.png" 
IMG_SIDEBAR = "logo_chico.png"

# Estilo para el Título Principal
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
        st.error(f"⚠️ Error de conexión a Base de Datos: {e}")
        st.stop()

db = firestore.client()

# ==========================================
# 2. MOTOR DE DATOS Y ESTADO DE SESIÓN
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.update({
        'autenticado': False, 
        'usuario': None, 
        'rol': None, 
        'id_negocio': None, 
        'nombre_real': None,
        'carrito': [], 
        'df_proveedor': None,
        'nuevo_cliente_mode': False  #
    })

def limpiar_precio_final(valor):
    """ Maneja formato americano: 1,500.00 -> 1500.00 """
    if pd.isna(valor) or str(valor).strip() == "": return 0.0
    s = str(valor).strip().replace('$', '').replace(' ', '').replace(',', '')
    try: return float(s)
    except: return 0.0

def cargar_datos_proveedor(silencioso=True):
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
            if not silencioso: st.toast("✅ Lista de precios sincronizada", icon="🔄")
    except Exception as e: st.error(f"⚠️ Error al conectar con Google Sheets: {e}")

if st.session_state.df_proveedor is None:
    cargar_datos_proveedor()

# ==========================================
# 3. INTERFAZ DE LOGIN
# ==========================================
if not st.session_state['autenticado']:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        if os.path.exists(IMG_LOGIN):
            st.image(IMG_LOGIN, use_container_width=True)
        mostrar_titulo()
        
        u_input = st.text_input("Usuario").strip().lower()
        c_input = st.text_input("Contraseña", type="password").strip()
        
        if st.button("Ingresar al Sistema", use_container_width=True, type="primary"):
            user_ref = db.collection("usuarios").document(u_input).get()
            if user_ref.exists and str(user_ref.to_dict().get('password')) == c_input:
                d = user_ref.to_dict()
                st.session_state.update({
                    'autenticado': True, 'usuario': u_input, 'rol': d.get('rol'), 
                    'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre')
                })
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")

# ==========================================
# 4. INTERFAZ PRINCIPAL (POST-LOGIN)
# ==========================================
else:
    negocio_id = st.session_state['id_negocio']
    vendedor = st.session_state['nombre_real'] or st.session_state['usuario']

    # BARRA LATERAL (SIDEBAR)
    with st.sidebar:
        if os.path.exists(IMG_SIDEBAR):
            st.image(IMG_SIDEBAR, width=150)
        st.markdown(f"### 👤 {vendedor}")
        st.caption(f"ID Negocio: {negocio_id.upper()}")
        
        if st.button("🔄 Sincronizar Excel", use_container_width=True): 
            cargar_datos_proveedor(silencioso=False)
            st.rerun()
        
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True): 
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    # CUERPO PRINCIPAL
    mostrar_titulo()
    tabs = st.tabs(["🛒 Ventas", "📉 Gastos", "📜 Historial"])

    # --- PESTAÑA VENTAS ---
    with tabs[0]:
        col_izq, col_der = st.columns([1.6, 1])
        
        with col_izq:
            busqueda = st.text_input("🔍 Buscar producto...", placeholder="Ej: Fideo, Yerba...")
            if busqueda and st.session_state.df_proveedor is not None:
                df = st.session_state.df_proveedor
                res = df[df['Productos'].str.contains(busqueda, case=False, na=False)]
                if not res.empty:
                    for _, fila in res.head(8).iterrows():
                        n, p = fila['Productos'], fila['Precio']
                        if st.button(f"➕ {n} | ${p:,.2f}", key=f"btn_{n}"):
                            # Agregar al carrito
                            found = False
                            for item in st.session_state.carrito:
                                if item['nombre'] == n:
                                    item['cantidad'] += 1
                                    item['subtotal'] = item['cantidad'] * item['precio']
                                    found = True
                                    break
                            if not found:
                                st.session_state.carrito.append({'nombre': n, 'precio': p, 'cantidad': 1, 'subtotal': p})
                            st.toast(f"Añadido: {n}")

            st.divider()
            st.subheader("Carrito de Compras")
            if st.session_state.carrito:
                for i, it in enumerate(st.session_state.carrito):
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 0.5])
                    c1.write(f"**{it['nombre']}**")
                    nueva_cant = c2.number_input("Cant", 1, 500, it['cantidad'], key=f"cant_{i}", label_visibility="collapsed")
                    if nueva_cant != it['cantidad']:
                        it['cantidad'] = nueva_cant
                        it['subtotal'] = it['precio'] * it['cantidad']
                        st.rerun()
                    c3.write(f"${it['subtotal']:,.2f}")
                    if c4.button("❌", key=f"del_{i}"):
                        st.session_state.carrito.pop(i)
                        st.rerun()
            else:
                st.info("El carrito está vacío.")

        with col_der:
            st.markdown("### 📋 Datos de Venta")
            
            # Gestión de Clientes
            clientes_ref = db.collection("clientes").where("id_negocio", "==", negocio_id).stream()
            lista_clientes = ["Consumidor Final"] + [c.to_dict().get('nombre') for c in clientes_ref]
            
            col_sel, col_add = st.columns([2, 1])
            cliente_sel = col_sel.selectbox("Cliente", lista_clientes)
            if col_add.button("➕ Nuevo"): st.session_state.nuevo_cliente_mode = True

            if st.session_state.nuevo_cliente_mode:
                with st.container(border=True):
                    n_cliente = st.text_input("Nombre del nuevo cliente")
                    if st.button("Guardar Cliente"):
                        if n_cliente:
                            db.collection("clientes").add({"nombre": n_cliente, "id_negocio": negocio_id})
                            st.session_state.nuevo_cliente_mode = False
                            st.success("Cliente creado")
                            st.rerun()

            # Método de Pago
            metodo = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Débito", "Crédito", "Fiado"])
            info_pago = ""
            if metodo == "Transferencia":
                info_pago = st.text_input("¿A qué cuenta?", placeholder="Ej: Mercado Pago Juani")

            st.divider()
            
            # Recargos y Descuentos
            c_rec, c_desc = st.columns(2)
            p_recargo = c_rec.number_input("Recargo %", 0.0, 100.0, 0.0, step=1.0)
            p_descuento = c_desc.number_input("Descuento %", 0.0, 100.0, 0.0, step=1.0)

            # Cálculos Finales
            subtotal_p = sum(it['subtotal'] for it in st.session_state.carrito)
            monto_rec = subtotal_p * (p_recargo / 100)
            monto_des = subtotal_p * (p_descuento / 100)
            total_neto = subtotal_p + monto_rec - monto_des

            if p_recargo > 0 or p_descuento > 0:
                st.caption(f"Subtotal: ${subtotal_p:,.2f}")
            
            st.markdown(f"""
                <div style='background:#f0f2f6;padding:20px;border-radius:10px;text-align:center;border:2px solid #1E88E5'>
                    <p style='margin:0; font-size: 1.2rem;'>TOTAL A COBRAR</p>
                    <h1 style='color:#1E88E5;margin:0'>${total_neto:,.2f}</h1>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚀 REGISTRAR VENTA", use_container_width=True, type="primary"):
                if st.session_state.carrito:
                    ahora = datetime.now()
                    db.collection("ventas_procesadas").add({
                        "vendedor": vendedor, "id_negocio": negocio_id, "cliente": cliente_sel,
                        "items": st.session_state.carrito, "total": total_neto, "metodo": metodo,
                        "detalle_pago": info_pago, "recargo_p": p_recargo, "descuento_p": p_descuento,
                        "fecha_completa": ahora, "fecha_str": ahora.strftime("%d/%m/%Y"), "hora_str": ahora.strftime("%H:%M")
                    })
                    st.success("✅ Venta registrada con éxito")
                    st.session_state.carrito = []
                    st.rerun()
                else:
                    st.error("El carrito está vacío")

    # --- PESTAÑA GASTOS ---
    with tabs[1]:
        st.subheader("Registrar Gasto de Caja")
        with st.form("gasto_form", clear_on_submit=True):
            m_gasto = st.number_input("Monto en $", min_value=0.0)
            d_gasto = st.text_input("Concepto / Detalle")
            if st.form_submit_button("Guardar Gasto"):
                db.collection("gastos").add({
                    "monto": m_gasto, "detalle": d_gasto, "vendedor": vendedor,
                    "id_negocio": negocio_id, "fecha": datetime.now()
                })
                st.success("Gasto guardado")

    # --- PESTAÑA HISTORIAL ---
    with tabs[2]:
        st.subheader("Historial Reciente")
        try:
            v_ref = db.collection("ventas_procesadas").where("id_negocio", "==", negocio_id).order_by("fecha_completa", direction=firestore.Query.DESCENDING).limit(15).stream()
            for v in v_ref:
                d = v.to_dict()
                with st.expander(f"🛒 {d['fecha_str']} {d['hora_str']} | {d['cliente']} | ${d['total']:,.2f}"):
                    st.write(f"**Vendedor:** {d['vendedor']} | **Pago:** {d['metodo']}")
                    if d['detalle_pago']: st.info(f"Cuenta: {d['detalle_pago']}")
                    st.write("**Productos:**")
                    for it in d['items']:
                        st.write(f"- {it['cantidad']}x {it['nombre']} (${it['subtotal']:,.2f})")
                    if d.get('recargo_p', 0) > 0: st.write(f"📈 Recargo: {d['recargo_p']}%")
                    if d.get('descuento_p', 0) > 0: st.write(f"📉 Descuento: {d['descuento_p']}%")
        except:
            st.info("Configura el índice en Firebase para ver el historial ordenado.")
