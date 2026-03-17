import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import os

# ==========================================
# 0. CONFIGURACIÓN INICIAL
# ==========================================
st.set_page_config(page_title="JL Gestión Pro", page_icon="🛍️", layout="wide")

ID_HOJA = "1-ay_xIqYItwOaXe80VUsEmh4gsANrk9PH72aZcUD54g"
URL_PROVEEDOR_CSV = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/export?format=csv"
IMG_LOGIN = "logo.png" 
IMG_SIDEBAR = "logo_chico.png"

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
# 2. MOTOR DE DATOS - LIMPIEZA FINAL
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.update({
        'autenticado': False, 'usuario': None, 'rol': None, 
        'id_negocio': None, 'nombre_real': None,
        'carrito': [], 'df_proveedor': None
    })

def limpiar_precio_final(valor):
    """ Mantiene el formato americano: Quita comas, deja puntos. """
    if pd.isna(valor) or str(valor).strip() == "": 
        return 0.0
    s = str(valor).strip().replace('$', '').replace(' ', '')
    try:
        s = s.replace(',', '') # Quita separador de miles americano
        return float(s)
    except:
        return 0.0

def cargar_datos_proveedor(silencioso=True):
    try:
        df = pd.read_csv(URL_PROVEEDOR_CSV, header=1)
        df.columns = df.columns.astype(str).str.strip()
        
        col_prod = [c for c in df.columns if any(kw in c.lower() for kw in ['producto', 'articulo', 'descrip'])]
        col_prec = [c for c in df.columns if any(kw in c.lower() for kw in ['precio', 'venta', 'valor'])]
        
        if col_prod and col_prec:
            df = df.rename(columns={col_prod[0]: 'Productos', col_prec[0]: 'Precio_Raw'})
            df['Precio'] = df['Precio_Raw'].apply(limpiar_precio_final)
            
            # FILTRO DE SEGURIDAD: Solo productos con nombre y precio mayor a 0
            df = df.dropna(subset=['Productos'])
            df = df[(df['Productos'] != "") & (df['Precio'] > 0)]
            
            st.session_state.df_proveedor = df
            if not silencioso:
                st.toast("✅ Lista actualizada", icon="🔄")
        else:
            st.error("⚠️ No se encontraron las columnas correctas en el Excel.")
    except Exception as e:
        st.error(f"⚠️ Error al leer el Excel: {e}")

if st.session_state.df_proveedor is None:
    cargar_datos_proveedor(silencioso=True)

# ==========================================
# 3. LÓGICA DE CARRITO
# ==========================================
def agregar_al_carrito(nombre, precio):
    for item in st.session_state.carrito:
        if item['nombre'] == nombre:
            item['cantidad'] += 1
            item['subtotal'] = item['cantidad'] * item['precio']
            return
    st.session_state.carrito.append({
        'nombre': nombre, 'precio': precio, 
        'cantidad': 1, 'subtotal': precio
    })

def cerrar_sesion():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ==========================================
# 4. INTERFAZ (Ventas, Gastos, Historial)
# ==========================================
if not st.session_state['autenticado']:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        if os.path.exists(IMG_LOGIN): st.image(IMG_LOGIN, use_container_width=True)
        u_input = st.text_input("Usuario").strip().lower()
        c_input = st.text_input("Contraseña", type="password").strip()
        if st.button("Ingresar", use_container_width=True, type="primary"):
            user_ref = db.collection("usuarios").document(u_input).get()
            if user_ref.exists and str(user_ref.to_dict().get('password')) == c_input:
                d = user_ref.to_dict()
                st.session_state.update({
                    'autenticado': True, 'usuario': u_input, 'rol': d.get('rol'), 
                    'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre')
                })
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
else:
    negocio_id = st.session_state['id_negocio']
    vendedor = st.session_state['nombre_real'] or st.session_state['usuario']

    with st.sidebar:
        if os.path.exists(IMG_SIDEBAR): st.image(IMG_SIDEBAR, width=120)
        st.write(f"👤 **{vendedor}**")
        if st.button("🔄 Sincronizar Excel"): 
            cargar_datos_proveedor(silencioso=False)
            st.rerun()
        st.divider()
        if st.button("🔴 Salir", use_container_width=True): cerrar_sesion()

    tabs = st.tabs(["🛒 Ventas", "📉 Gastos", "📜 Historial"])

    with tabs[0]:
        col_izq, col_der = st.columns([1.6, 1])
        with col_izq:
            busqueda = st.text_input("🔍 Buscar producto...", placeholder="Escribe el nombre...")
            if busqueda and st.session_state.df_proveedor is not None:
                df = st.session_state.df_proveedor
                res = df[df['Productos'].str.contains(busqueda, case=False, na=False)]
                if not res.empty:
                    for _, fila in res.head(8).iterrows():
                        n, p = fila['Productos'], fila['Precio']
                        if st.button(f"➕ {n} | ${p:,.2f}", key=f"btn_{n}"):
                            agregar_al_carrito(n, p)
                            st.toast(f"Añadido: {n}")
            
            st.divider()
            if st.session_state.carrito:
                for i, it in enumerate(st.session_state.carrito):
                    with st.container():
                        c1, c2, c3, c4 = st.columns([3, 1, 1, 0.5])
                        c1.write(f"**{it['nombre']}**")
                        nueva_cant = c2.number_input("Cant", 1, 500, it['cantidad'], key=f"v_{i}", label_visibility="collapsed")
                        if nueva_cant != it['cantidad']:
                            it['cantidad'] = nueva_cant
                            it['subtotal'] = it['precio'] * it['cantidad']
                            st.rerun()
                        c3.write(f"${it['subtotal']:,.2f}")
                        if c4.button("❌", key=f"del_{i}"):
                            st.session_state.carrito.pop(i)
                            st.rerun()

        with col_der:
            total_v = sum(it['subtotal'] for it in st.session_state.carrito)
            st.markdown(f"<div style='background:#f9f9f9;padding:20px;border-radius:10px;text-align:center;border:1px solid #ddd'><p style='margin:0'>TOTAL A COBRAR</p><h1 style='color:#2e7d32;margin:0'>${total_v:,.2f}</h1></div>", unsafe_allow_html=True)
            pago = st.selectbox("Método", ["Efectivo", "Transferencia", "Débito", "Fiado"])
            if st.button("✅ REGISTRAR VENTA", use_container_width=True, type="primary"):
                if st.session_state.carrito:
                    db.collection("ventas_procesadas").add({
                        "vendedor": vendedor, "id_negocio": negocio_id, 
                        "items": st.session_state.carrito, "total": total_v, 
                        "metodo": pago, "fecha": datetime.now()
                    })
                    st.success("¡Venta Exitosa!")
                    st.session_state.carrito = []
                    st.rerun()

    with tabs[1]:
        st.subheader("Registrar Gasto")
        m = st.number_input("Monto $", 0.0)
        d = st.text_input("Detalle del gasto")
        if st.button("Guardar Gasto"):
            db.collection("gastos").add({"monto": m, "detalle": d, "fecha": datetime.now(), "id_negocio": negocio_id, "vendedor": vendedor})
            st.success("Gasto registrado")

    with tabs[2]:
        st.subheader("Últimos movimientos")
        v_ref = db.collection("ventas_procesadas").where("id_negocio", "==", negocio_id).order_by("fecha", direction=firestore.Query.DESCENDING).limit(10).stream()
        for v in v_ref:
            d = v.to_dict()
            st.write(f"⏱️ {d['fecha'].strftime('%H:%M')} | **${d['total']:,.2f}** | {d['metodo']}")
