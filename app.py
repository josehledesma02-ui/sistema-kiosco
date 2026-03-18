import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os

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
        neg_in = st.text_input("Negocio (Ej: fabricon)").strip().lower()
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
        
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True): 
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    mostrar_titulo()

    # --- VISTA CLIENTE ---
    if rol_u == "cliente":
        c_id = st.session_state.usuario
        v_f = list(db.collection("ventas_procesadas").where("cliente_id", "==", c_id).where("metodo", "==", "Fiado").stream())
        p_f = list(db.collection("pagos_clientes").where("cliente_id", "==", c_id).stream())
        saldo = sum(v.to_dict().get('total', 0) for v in v_f) - sum(p.to_dict().get('monto', 0) for p in p_f)
        
        st.markdown(f"## Hola **{nom_u}**")
        st.error(f"# Tu saldo actual: ${saldo:,.2f}")

        with st.container(border=True):
            st.markdown(f"""
            ### 📝 Nota sobre tu cuenta:
            Usted se ha comprometido a cancelar el total de su deuda el día **{f_pago}**. 
            *   **Si cumple con el pago total:** Se le mantienen los precios originales de compra.
            *   **Si no cumple o deja saldo:** Los valores de los productos se actualizarán automáticamente según el precio de venta actual en el local.
            
            **Por favor, para mantener este beneficio, no deje saldo pendiente.**
            """)

        st.divider()
        st.subheader("📜 Detalle de Movimientos")
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
                        st.caption(f"Atendido por: {d.get('vendedor', 'N/A')}")
                        for i in d.get('items', []):
                            st.markdown(f"<p style='font-size:18px;'>📍 **{i['cantidad']}** x {i['nombre']} <br><span style='font-size:14px; color:grey;'>Unitario: ${i['precio']:,.2f} | Subtotal: ${i['subtotal']:,.2f}</span></p>", unsafe_allow_html=True)
                    with c2: st.markdown(f"<h2 style='color:red; text-align:right;'>- ${d.get('total', 0):,.2f}</h2>", unsafe_allow_html=True)
                else:
                    c1, c2 = st.columns([3, 1])
                    with c1: st.markdown(f"### ✅ Pago Recibido: {d.get('fecha_str')} - {d.get('hora_str')}hs")
                    with c2: st.markdown(f"<h2 style='color:green; text-align:right;'>+ ${d.get('monto', 0):,.2f}</h2>", unsafe_allow_html=True)

    # --- VISTA DUEÑO ---
    elif rol_u == "negocio":
        tabs = st.tabs(["🛒 Ventas", "📉 Gastos", "📜 Historial", "👥 Clientes"])
        
        with tabs[0]: # VENTAS
            st.subheader("Nueva Venta")
            if st.session_state.df_proveedor is None:
                try:
                    st.session_state.df_proveedor = pd.read_csv(URL_PROVEEDOR_CSV)
                except:
                    st.error("Error cargando lista de productos.")
            
            if st.session_state.df_proveedor is not None:
                col1, col2 = st.columns(2)
                with col1:
                    prod_sel = st.selectbox("Producto", st.session_state.df_proveedor['PRODUCTO'].unique())
                    cant = st.number_input("Cantidad", min_value=0.1, value=1.0, step=0.1)
                
                if st.button("Añadir al Carrito"):
                    info = st.session_state.df_proveedor[st.session_state.df_proveedor['PRODUCTO'] == prod_sel].iloc[0]
                    st.session_state.carrito.append({
                        'nombre': prod_sel, 'cantidad': cant, 
                        'precio': float(info['PRECIO']), 'subtotal': float(info['PRECIO']) * cant
                    })
                
                if st.session_state.carrito:
                    st.table(pd.DataFrame(st.session_state.carrito))
                    total_v = sum(i['subtotal'] for i in st.session_state.carrito)
                    st.write(f"### Total: ${total_v:,.2f}")
                    
                    metodo = st.selectbox("Método de Pago", ["Efectivo", "Transferencia", "Fiado"])
                    cliente_id = None
                    if metodo == "Fiado":
                        clis = db.collection("usuarios").where("id_negocio", "==", neg_id).where("rol", "==", "cliente").stream()
                        dict_clis = {c.to_dict()['nombre']: c.id for c in clis}
                        nom_cli = st.selectbox("Seleccionar Cliente", list(dict_clis.keys()))
                        cliente_id = dict_clis[nom_cli]
                    
                    if st.button("Confirmar Venta"):
                        ahora = obtener_hora_argentina()
                        db.collection("ventas_procesadas").add({
                            'id_negocio': neg_id, 'vendedor': nom_u, 'items': st.session_state.carrito,
                            'total': total_v, 'metodo': metodo, 'cliente_id': cliente_id,
                            'fecha_completa': ahora, 'fecha_str': ahora.strftime("%d/%m/%Y"), 'hora_str': ahora.strftime("%H:%M")
                        })
                        st.success("¡Venta registrada con éxito!")
                        st.session_state.carrito = []
                        st.rerun()

        with tabs[1]: # GASTOS
            st.subheader("Registrar Gasto")
            desc_g = st.text_input("Descripción del Gasto")
            monto_g = st.number_input("Monto", min_value=0.0)
            if st.button("Guardar Gasto"):
                ahora = obtener_hora_argentina()
                db.collection("gastos").add({
                    'id_negocio': neg_id, 'descripcion': desc_g, 'monto': monto_g,
                    'fecha_completa': ahora, 'fecha_str': ahora.strftime("%d/%m/%Y")
                })
                st.success("Gasto guardado.")

        with tabs[2]: # HISTORIAL
            st.subheader("Historial de Ventas")
            ventas = db.collection("ventas_procesadas").where("id_negocio", "==", neg_id).order_by("fecha_completa", direction=firestore.Query.DESCENDING).limit(50).stream()
            lista_v = []
            for v in ventas:
                d = v.to_dict()
                lista_v.append([d.get('fecha_str'), d.get('hora_str'), d.get('metodo'), d.get('total')])
            if lista_v:
                st.table(pd.DataFrame(lista_v, columns=["Fecha", "Hora", "Método", "Total"]))
            else:
                st.write("No hay ventas registradas.")

        with tabs[3]: # CLIENTES
            st.subheader("Gestión de Clientes")
            with st.expander("➕ Registrar Nuevo Cliente"):
                nc_nombre = st.text_input("Nombre y Apellido Cliente")
                nc_dni = st.text_input("DNI (Contraseña)")
                nc_pago = st.text_input("Fecha de Pago (DD/MM/AAAA)")
                if st.button("Crear Cliente"):
                    db.collection("usuarios").add({
                        'id_negocio': neg_id, 'nombre': nc_nombre, 'password': nc_dni,
                        'rol': 'cliente', 'promesa_pago': nc_pago
                    })
                    st.success(f"Cliente {nc_nombre} creado.")
