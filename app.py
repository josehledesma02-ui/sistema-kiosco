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
    try:
        # CORREGIDO: Formato oficial de pytz
        zona_ar = pytz.timezone('America/Argentina/Buenos_Aires')
    except:
        zona_ar = pytz.timezone('UTC')
    return datetime.now(zona_ar)

# URL DE TU GOOGLE SHEETS
ID_HOJA = "1-ay_xIqYItwOaXe80VUsEmh4gsANrk9PH72aZcUD54g"
URL_PROVEEDOR_CSV = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/export?format=csv"

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
# 2. 🔒 VISTA CLIENTE (RECUPERADA Y MEJORADA)
# ==========================================
def mostrar_vistas_cliente(nom_u, f_pago, c_id):
    mostrar_cabecera_identidad()
    st.markdown(f"### 👋 Hola, {nom_u}")
    
    # Traemos Ventas Fiadas y Pagos realizados
    v_fiado = list(db.collection("ventas_procesadas").where("cliente_id", "==", c_id).where("metodo", "==", "Fiado").stream())
    p_realizados = list(db.collection("pagos_clientes").where("cliente_id", "==", c_id).stream())
    
    total_deuda = sum(v.to_dict().get('total', 0) for v in v_fiado)
    total_pagado = sum(p.to_dict().get('monto', 0) for p in p_realizados)
    saldo_pendiente = total_deuda - total_pagado

    # Tablero de Control para el Cliente
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.metric("TU SALDO PENDIENTE", f"${saldo_pendiente:,.2f}", delta_color="inverse")
    with col_s2:
        st.info(f"📅 **Próximo Pago:** {f_pago}")

    st.divider()
    
    t_mov, t_det = st.tabs(["📜 Movimientos Recientes", "📦 Detalle de Compras"])
    
    with t_mov:
        st.subheader("Historial de Cuenta")
        # Combinamos ventas y pagos para el historial
        movs = []
        for v in v_fiado: 
            d = v.to_dict()
            movs.append({"fecha": d.get('fecha_str', 'S/F'), "tipo": "COMPRA 🛒", "monto": d.get('total', 0), "raw_f": d.get('fecha_completa')})
        for p in p_realizados:
            d = p.to_dict()
            movs.append({"fecha": d.get('fecha_str', 'S/F'), "tipo": "PAGO ✅", "monto": d.get('monto', 0), "raw_f": d.get('fecha')})
        
        if movs:
            # Ordenar por fecha (asumiendo que raw_f es timestamp)
            movs.sort(key=lambda x: str(x['raw_f']), reverse=True)
            df_movs = pd.DataFrame(movs)[["fecha", "tipo", "monto"]]
            st.table(df_movs)
        else:
            st.write("No hay movimientos registrados aún.")

    with t_det:
        st.subheader("¿Qué compraste?")
        for v in v_fiado:
            d = v.to_dict()
            with st.expander(f"Compra del {d.get('fecha_str')} - Total: ${d.get('total', 0):,.2f}"):
                for item in d.get('items', []):
                    st.write(f"🔹 {item['nombre']} (x{item['cantidad']}) - ${item['subtotal']:,.2f}")

# ==========================================
# 3. 🛠️ VISTA NEGOCIO (DUEÑO)
# ==========================================
def mostrar_vistas_negocio(neg_id, nom_u):
    mostrar_cabecera_identidad()
    ahora_ar = obtener_hora_argentina()
    t1, t2, t3, t4 = st.tabs(["🛒 Ventas", "📉 Gastos", "📜 Historial", "👥 Clientes"])
    
    with t1:
        if 'df_proveedor' not in st.session_state or st.session_state.df_proveedor is None:
            try:
                raw = pd.read_csv(URL_PROVEEDOR_CSV, header=None).fillna("")
                fila_enc = 0
                for i, row in raw.iterrows():
                    if any("producto" in str(x).lower() for x in row.values):
                        fila_enc = i
                        break
                df = pd.read_csv(URL_PROVEEDOR_CSV, skiprows=fila_enc)
                df.columns = [str(c).strip() for c in df.columns]
                c_prod = next((c for c in df.columns if "producto" in c.lower()), df.columns[0])
                c_prec = next((c for c in df.columns if "precio" in c.lower()), df.columns[1])
                df_f = df.rename(columns={c_prod: "Productos", c_prec: "Precio"})
                df_f["Precio"] = pd.to_numeric(df_f["Precio"], errors='coerce').fillna(0)
                st.session_state.df_proveedor = df_f[["Productos", "Precio"]].dropna(subset=["Productos"])
            except:
                st.error("Error al cargar la lista de precios.")
                st.stop()

        df = st.session_state.df_proveedor
        busq = st.text_input("🔍 Buscar producto...", "").lower()
        df_f = df[df['Productos'].astype(str).str.contains(busq, case=False)] if busq else df
        
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1: p_sel = st.selectbox("Producto", df_f['Productos'].unique())
        with c2: cant = st.number_input("Cantidad", 0.1, 100.0, 1.0)
        p_sug = float(df[df['Productos'] == p_sel]['Precio'].values[0])
        with c3: p_final = st.number_input("Precio $", value=p_sug)

        if st.button("➕ AGREGAR", use_container_width=True):
            st.session_state.carrito.append({'nombre': p_sel, 'cantidad': cant, 'precio': p_final, 'subtotal': p_final * cant})

        if st.session_state.carrito:
            st.table(pd.DataFrame(st.session_state.carrito))
            total = sum(i['subtotal'] for i in st.session_state.carrito)
            st.markdown(f"### TOTAL: ${total:,.2f}")
            
            metodo = st.selectbox("Forma de Pago", ["Efectivo", "Transferencia", "Fiado"])
            cli_id, cli_nom = None, "Consumidor Final"
            
            if metodo == "Fiado":
                clis = db.collection("usuarios").where("id_negocio", "==", neg_id).where("rol", "==", "cliente").stream()
                d_clis = {c.to_dict()['nombre']: c.id for c in clis}
                if d_clis:
                    cli_nom = st.selectbox("¿A quién le fiamos?", list(d_clis.keys()))
                    cli_id = d_clis[cli_nom]

            if st.button("🚀 CERRAR VENTA", type="primary", use_container_width=True):
                db.collection("ventas_procesadas").add({
                    'id_negocio': neg_id, 'items': st.session_state.carrito, 'total': total,
                    'metodo': metodo, 'cliente_id': cli_id, 'cliente_nombre': cli_nom,
                    'vendedor': nom_u, 'fecha_completa': ahora_ar,
                    'fecha_str': ahora_ar.strftime("%d/%m/%Y"), 'hora_str': ahora_ar.strftime("%H:%M")
                })
                st.session_state.carrito = []
                st.success("Venta realizada!")
                st.rerun()

    with t2: # GASTOS
        st.subheader("📉 Registrar Gasto")
        desc_g = st.text_input("Concepto")
        monto_g = st.number_input("Monto $", 0.0)
        if st.button("Guardar Gasto"):
            db.collection("gastos").add({'id_negocio': neg_id, 'descripcion': desc_g, 'monto': monto_g, 'fecha_str': ahora_ar.strftime("%d/%m/%Y")})
            st.success("Gasto guardado.")

    with t3: # HISTORIAL NEGOCIO
        st.subheader("Últimos Movimientos")
        vtas = db.collection("ventas_procesadas").where("id_negocio", "==", neg_id).order_by("fecha_completa", direction="DESCENDING").limit(15).stream()
        for v in vtas:
            d = v.to_dict()
            st.write(f"📌 {d['fecha_str']} | {d['cliente_nombre']} | **${d['total']:,.2f}** ({d['metodo']})")

    with t4: # GESTIÓN CLIENTES
        st.subheader("Administrar Clientes")
        with st.form("nuevo_cliente"):
            n_c = st.text_input("Nombre Completo")
            d_c = st.text_input("DNI (será su clave)")
            f_p = st.text_input("Fecha de cobro (Ej: Los 10)")
            if st.form_submit_button("Crear Cliente"):
                db.collection("usuarios").add({'id_negocio': neg_id, 'nombre': n_c, 'password': d_c, 'rol': 'cliente', 'promesa_pago': f_p})
                st.success("Cliente creado!")

# ==========================================
# 4. SISTEMA DE LOGIN Y NAVEGACIÓN
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.update({'autenticado': False, 'usuario': None, 'rol': None, 'id_negocio': None, 'nombre_real': None, 'carrito': [], 'df_proveedor': None})

if not st.session_state.autenticado:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        mostrar_cabecera_identidad()
        neg_in = st.text_input("ID Negocio").strip().lower()
        u_in = st.text_input("Tu Nombre").strip()
        c_in = st.text_input("Contraseña", type="password").strip()
        if st.button("Entrar", use_container_width=True, type="primary"):
            q = db.collection("usuarios").where("id_negocio", "==", neg_in).where("nombre", "==", u_in).limit(1).get()
            if q and str(q[0].to_dict().get('password')) == c_in:
                d = q[0].to_dict()
                st.session_state.update({'autenticado': True, 'usuario': q[0].id, 'rol': str(d.get('rol')).strip().lower(), 'id_negocio': d.get('id_negocio'), 'nombre_real': d.get('nombre'), 'fecha_pago_cliente': d.get('promesa_pago', 'No definida')})
                st.rerun()
            else:
                st.error("Datos incorrectos. Revisá bien.")
else:
    with st.sidebar:
        st.write(f"👤 **{st.session_state.nombre_real}**")
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
            
    if st.session_state.rol == "cliente":
        mostrar_vistas_cliente(st.session_state.nombre_real, st.session_state.fecha_pago_cliente, st.session_state.usuario)
    else:
        mostrar_vistas_negocio(st.session_state.id_negocio, st.session_state.nombre_real)
