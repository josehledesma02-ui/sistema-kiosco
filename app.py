import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os
import urllib.parse

# ==========================================
# 0. CONFIGURACIÓN Y HORA ARGENTINA
# ==========================================
st.set_page_config(page_title="JL Gestión Pro", page_icon="🛍️", layout="wide")

def obtener_hora_argentina():
    zona_ar = pytz.timezone('America/Argentina/Buenos_Aires')
    return datetime.now(zona_ar)

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
        'fecha_pago_cliente': "N/A", 'carrito': [], 'df_proveedor': None
    })

# ==========================================
# 3. LOGIN
# ==========================================
if not st.session_state.autenticado:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        if os.path.exists(IMG_LOGIN): st.image(IMG_LOGIN, use_container_width=True)
        mostrar_titulo()
        neg_in = st.text_input("Negocio").strip().lower()
        u_in = st.text_input("Nombre y Apellido").strip()
        c_in = st.text_input("Contraseña (DNI)", type="password").strip()
        
        if st.button("Ingresar", use_container_width=True, type="primary"):
            query = db.collection("usuarios").where("id_negocio", "==", neg_in).where("nombre", "==", u_in).limit(1).get()
            if query:
                d = query[0].to_dict()
                if str(d.get('password')) == c_in:
                    st.session_state.update({
                        'autenticado': True, 'usuario': query[0].id, 'rol': str(d.get('rol')).strip().lower(),
                        'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre'),
                        'fecha_pago_cliente': d.get('promesa_pago', 'N/A')
                    })
                    st.rerun()
                else: st.error("❌ DNI incorrecto")
            else: st.error("❌ Usuario no encontrado")

# ==========================================
# 4. INTERFAZ PRINCIPAL
# ==========================================
else:
    neg_id = st.session_state.id_negocio
    nom_u = st.session_state.nombre_real
    rol_u = st.session_state.rol
    f_pago = st.session_state.fecha_pago_cliente
    ahora_ar = obtener_hora_argentina()

    with st.sidebar:
        if os.path.exists(IMG_SIDEBAR): st.image(IMG_SIDEBAR, width=150)
        st.markdown(f"### 👤 {nom_u}")
        st.write(f"🏷️ **Rol:** {rol_u.capitalize()}")
        st.write(f"🏢 **Negocio:** {neg_id.upper()}")
        if rol_u == "cliente":
            st.write(f"📅 **Fecha de pago:** {f_pago}")
            try:
                f_dt = datetime.strptime(f_pago, "%d/%m/%Y").replace(tzinfo=pytz.timezone('America/Argentina/Buenos_Aires'))
                dias = (f_dt - ahora_ar).days
                if dias <= 5:
                    if dias >= 0: st.warning(f"⚠️ Próximo a vencer ({dias} días)")
                    else: st.error("🚨 PAGO VENCIDO")
            except: pass
        if st.button("🔴 Cerrar Sesión"): 
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    mostrar_titulo()

    # --- VISTA CLIENTE ---
    if rol_u == "cliente":
        c_id = st.session_state.usuario
        v_f = list(db.collection("ventas_procesadas").where("cliente_id", "==", c_id).where("metodo", "==", "Fiado").stream())
        p_f = list(db.collection("pagos_clientes").where("cliente_id", "==", c_id).stream())
        saldo = sum(v.to_dict().get('total', 0) for v in v_f) - sum(p.to_dict().get('monto', 0) for p in p_f)
        
        st.error(f"# Tu saldo actual: ${saldo:,.2f}")
        with st.container(border=True):
            st.markdown(f"### 📝 Nota sobre tu cuenta:\nUsted se ha comprometido a cancelar el total de su deuda el día **{f_pago}**.")
            st.markdown("* **Si cumple:** Se mantienen los precios originales.\n* **Si no cumple:** Se actualizarán al precio actual.")

        st.subheader("📜 Detalle de Movimientos")
        movs = []
        for v in v_f: movs.append({"dt": v.to_dict().get('fecha_completa'), "tipo": "C", "d": v.to_dict()})
        for p in p_f: movs.append({"dt": p.to_dict().get('fecha'), "tipo": "P", "d": p.to_dict()})
        movs.sort(key=lambda x: x['dt'] if x['dt'] else datetime.min, reverse=True)

        for m in movs:
            with st.container(border=True):
                d = m['d']
                if m['tipo'] == "C":
                    st.markdown(f"### 🛒 Compra: {d.get('fecha_str')} - {d.get('hora_str')}hs")
                    for i in d.get('items', []): st.write(f"📍 {i['cantidad']} x {i['nombre']} (${i['subtotal']:,.2f})")
                    st.markdown(f"<h2 style='color:red;'>- ${d.get('total'):,.2f}</h2>", unsafe_allow_html=True)
                else:
                    st.markdown(f"### ✅ Pago Recibido: {d.get('fecha_str')} - {d.get('hora_str')}hs")
                    st.markdown(f"<h2 style='color:green;'>+ ${d.get('monto'):,.2f}</h2>", unsafe_allow_html=True)

    # --- VISTA DUEÑO (RECUPERADA) ---
    elif rol_u == "negocio":
        tabs = st.tabs(["🛒 Ventas", "📉 Gastos", "📜 Historial", "👥 Clientes"])
        
        with tabs[0]: # VENTAS
            st.subheader("Nueva Venta")
            if st.session_state.df_proveedor is None:
                st.session_state.df_proveedor = pd.read_csv(URL_PROVEEDOR_CSV)
            
            prod = st.selectbox("Buscar Producto", st.session_state.df_proveedor['PRODUCTO'].unique())
            cant = st.number_input("Cantidad", min_value=0.1, value=1.0)
            if st.button("Agregar al Carrito"):
                row = st.session_state.df_proveedor[st.session_state.df_proveedor['PRODUCTO'] == prod].iloc[0]
                st.session_state.carrito.append({'nombre': prod, 'cantidad': cant, 'precio': row['PRECIO'], 'subtotal': row['PRECIO'] * cant})

            if st.session_state.carrito:
                df_c = pd.DataFrame(st.session_state.carrito)
                st.table(df_c)
                metodo = st.selectbox("Método", ["Efectivo", "Transferencia", "Fiado"])
                cliente_sel = None
                if metodo == "Fiado":
                    clis = db.collection("usuarios").where("id_negocio", "==", neg_id).where("rol", "==", "cliente").stream()
                    nombres_clis = {c.to_dict()['nombre']: c.id for c in clis}
                    cliente_nom = st.selectbox("Seleccionar Cliente", list(nombres_clis.keys()))
                    cliente_sel = nombres_clis[cliente_nom]
                
                if st.button("Finalizar Venta"):
                    ahora = obtener_hora_argentina()
                    total = df_c['subtotal'].sum()
                    db.collection("ventas_procesadas").add({
                        'id_negocio': neg_id, 'total': total, 'metodo': metodo, 
                        'cliente_id': cliente_sel, 'items': st.session_state.carrito,
                        'fecha_completa': ahora, 'fecha_str': ahora.strftime("%d/%m/%Y"), 'hora_str': ahora.strftime("%H:%M")
                    })
                    st.success("Venta Guardada")
                    st.session_state.carrito = []
                    st.rerun()

        with tabs[1]: # GASTOS
            st.subheader("Gastos del Negocio")
            g_desc = st.text_input("Descripción Gasto")
            g_monto = st.number_input("Monto Gasto", min_value=0.0)
            if st.button("Registrar Gasto"):
                ahora = obtener_hora_argentina()
                db.collection("gastos").add({
                    'id_negocio': neg_id, 'descripcion': g_desc, 'monto': g_monto,
                    'fecha_completa': ahora, 'fecha_str': ahora.strftime("%d/%m/%Y")
                })
                st.success("Gasto registrado")

        with tabs[2]: # HISTORIAL
            st.subheader("Movimientos de hoy")
            h_ventas = db.collection("ventas_procesadas").where("id_negocio", "==", neg_id).stream()
            df_h = pd.DataFrame([v.to_dict() for v in h_ventas])
            if not df_h.empty: st.dataframe(df_h[['fecha_str', 'hora_str', 'metodo', 'total']])

        with tabs[3]: # CLIENTES
            st.subheader("Nuevo Cliente")
            nc_nom = st.text_input("Nombre Completo")
            nc_dni = st.text_input("DNI (Será la contraseña)")
            nc_tel = st.text_input("WhatsApp")
            nc_pago = st.text_input("Día de pago (ej: 05/04/2026)")
            if st.button("Crear Cliente"):
                db.collection("usuarios").add({
                    'id_negocio': neg_id, 'nombre': nc_nom, 'password': nc_dni, 
                    'rol': 'cliente', 'tel': nc_tel, 'promesa_pago': nc_pago
                })
                st.success("Cliente creado!")
