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
        # CORRECCIÓN DEFINITIVA DE ZONA HORARIA
        zona_ar = pytz.timezone('America/Argentina/Buenos_Aires')
    except Exception:
        zona_ar = pytz.timezone('UTC')
    return datetime.now(zona_ar)

# CONFIGURACIÓN DE FUENTES EXTERNAS
ID_HOJA = "1-ay_xIqYItwOaXe80VUsEmh4gsANrk9PH72aZcUD54g"
URL_PROVEEDOR_CSV = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/export?format=csv"

# ARCHIVOS DE IMAGEN
IMG_LOGIN = "logo.png" 
IMG_SIDEBAR = "logo_chico.png"

def mostrar_cabecera_identidad():
    """Muestra el título principal en todas las vistas"""
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
            # Opción local si no hay secrets
            cred = credentials.Certificate("secretos.json")
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"⚠️ Error Crítico de Conexión: {e}")
        st.stop()

db = firestore.client()

# ==========================================
# 2. 🔒 VISTA CLIENTE (COMPLETA Y DETALLADA)
# ==========================================
def mostrar_vistas_cliente(nom_u, f_pago, c_id):
    mostrar_cabecera_identidad()
    
    # Obtener Ventas "Fiado" y Pagos realizados desde Firebase
    v_fiado = list(db.collection("ventas_procesadas").where("cliente_id", "==", c_id).where("metodo", "==", "Fiado").stream())
    p_realizados = list(db.collection("pagos_clientes").where("cliente_id", "==", c_id).stream())
    
    # Cálculos de Saldo
    total_deuda = sum(v.to_dict().get('total', 0) for v in v_fiado)
    total_pagado = sum(p.to_dict().get('monto', 0) for p in p_realizados)
    saldo_pendiente = total_deuda - total_pagado

    # Indicadores visuales para el cliente
    col_izq, col_der = st.columns(2)
    with col_izq:
        st.metric("TU SALDO PENDIENTE", f"${saldo_pendiente:,.2f}", delta_color="inverse")
    with col_der:
        st.info(f"📅 **Tu próxima fecha de pago:** {f_pago}")

    st.divider()
    
    # Pestañas de navegación para el cliente
    tab_movimientos, tab_detalles = st.tabs(["📜 Mis Movimientos", "📦 Detalle de Compras"])
    
    with tab_movimientos:
        st.subheader("Historial de Cuenta")
        movimientos_lista = []
        for venta in v_fiado:
            datos = venta.to_dict()
            movimientos_lista.append({
                "Fecha": datos.get('fecha_str', 'S/F'),
                "Tipo": "Compra 🛒",
                "Monto": datos.get('total', 0),
                "Ref": datos.get('fecha_completa')
            })
        for pago in p_realizados:
            datos = pago.to_dict()
            movimientos_lista.append({
                "Fecha": datos.get('fecha_str', 'S/F'),
                "Tipo": "Pago ✅",
                "Monto": datos.get('monto', 0),
                "Ref": datos.get('fecha')
            })
        
        if movimientos_lista:
            # Ordenar por fecha real
            df_movs = pd.DataFrame(movimientos_lista).sort_values(by="Ref", ascending=False)
            st.table(df_movs[["Fecha", "Tipo", "Monto"]])
        else:
            st.info("Aún no tienes movimientos registrados en tu cuenta.")

    with tab_detalles:
        st.subheader("¿Qué productos llevaste?")
        if not v_fiado:
            st.write("No hay compras detalladas.")
        else:
            for venta in v_fiado:
                datos = venta.to_dict()
                with st.expander(f"Ticket del día {datos.get('fecha_str')} - Total: ${datos.get('total', 0):,.2f}"):
                    for item in datos.get('items', []):
                        st.write(f"🔹 **{item['nombre']}**")
                        st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;Cantidad: {item['cantidad']} | Subtotal: ${item['subtotal']:,.2f}")

# ==========================================
# 3. 🛠️ VISTA NEGOCIO (DUEÑO)
# ==========================================
def mostrar_vistas_negocio(neg_id, nom_u):
    mostrar_cabecera_identidad()
    ahora_ar = obtener_hora_argentina()
    
    t1, t2, t3, t4 = st.tabs(["🛒 Nueva Venta", "📉 Gastos", "📜 Historial", "👥 Gestión Clientes"])
    
    with t1:
        # Carga de Inventario desde Google Sheets
        if 'df_proveedor' not in st.session_state or st.session_state.df_proveedor is None:
            try:
                raw = pd.read_csv(URL_PROVEEDOR_CSV, header=None).fillna("")
                fila_encabezado = 0
                for i, row in raw.iterrows():
                    if any("producto" in str(x).lower() for x in row.values):
                        fila_encabezado = i
                        break
                df_base = pd.read_csv(URL_PROVEEDOR_CSV, skiprows=fila_encabezado)
                df_base.columns = [str(c).strip() for c in df_base.columns]
                
                col_nombre = next((c for c in df_base.columns if "producto" in c.lower()), df_base.columns[0])
                col_precio = next((c for c in df_base.columns if "precio" in c.lower()), df_base.columns[1])
                
                df_final = df_base.rename(columns={col_nombre: "Productos", col_precio: "Precio"})
                df_final["Precio"] = pd.to_numeric(df_final["Precio"], errors='coerce').fillna(0)
                st.session_state.df_proveedor = df_final[["Productos", "Precio"]].dropna(subset=["Productos"])
            except Exception as e:
                st.error(f"Error al conectar con la lista de precios: {e}")
                st.stop()

        # Interfaz de Venta
        df_inv = st.session_state.df_proveedor
        busqueda = st.text_input("🔍 Buscar producto...", "").lower()
        
        filtro = df_inv[df_inv['Productos'].astype(str).str.contains(busqueda, case=False)] if busqueda else df_inv
        
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            prod_seleccionado = st.selectbox("Producto", filtro['Productos'].unique())
        with c2:
            cantidad = st.number_input("Cantidad", min_value=0.1, max_value=1000.0, value=1.0, step=0.5)
        
        precio_sugerido = float(df_inv[df_inv['Productos'] == prod_seleccionado]['Precio'].values[0])
        with c3:
            precio_venta = st.number_input("Precio Unitario $", value=precio_sugerido)

        if st.button("➕ AGREGAR AL CARRITO", use_container_width=True):
            st.session_state.carrito.append({
                'nombre': prod_seleccionado,
                'cantidad': cantidad,
                'precio': precio_venta,
                'subtotal': precio_venta * cantidad
            })
            st.toast("Producto agregado")

        if st.session_state.carrito:
            st.markdown("### 🛒 Detalle del Pedido")
            df_carrito = pd.DataFrame(st.session_state.carrito)
            st.table(df_carrito)
            
            total_pedido = df_carrito['subtotal'].sum()
            
            # Descuentos y Recargos
            col_d, col_r = st.columns(2)
            p_desc = col_d.number_input("% Descuento", 0, 100, 0)
            p_reca = col_r.number_input("% Recargo", 0, 100, 0)
            
            total_final = total_pedido * (1 - p_desc/100) * (1 + p_reca/100)
            st.markdown(f"## TOTAL A COBRAR: ${total_final:,.2f}")
            
            metodo_pago = st.selectbox("Forma de Pago", ["Efectivo", "Transferencia", "Fiado"])
            
            cliente_id_vinculado = None
            cliente_nombre_vinculado = "Consumidor Final"
            
            if metodo_pago == "Fiado":
                clientes_db = db.collection("usuarios").where("id_negocio", "==", neg_id).where("rol", "==", "cliente").stream()
                lista_clientes = {c.to_dict()['nombre']: c.id for c in clientes_db}
                if lista_clientes:
                    cliente_nombre_vinculado = st.selectbox("Seleccionar Cliente para Deuda", list(lista_clientes.keys()))
                    cliente_id_vinculado = lista_clientes[cliente_nombre_vinculado]
                else:
                    st.warning("No tienes clientes registrados para fiar.")

            if st.button("🚀 CONFIRMAR VENTA", type="primary", use_container_width=True):
                nueva_venta = {
                    'id_negocio': neg_id,
                    'items': st.session_state.carrito,
                    'total': total_final,
                    'metodo': metodo_pago,
                    'cliente_id': cliente_id_vinculado,
                    'cliente_nombre': cliente_nombre_vinculado,
                    'vendedor': nom_u,
                    'fecha_completa': ahora_ar,
                    'fecha_str': ahora_ar.strftime("%d/%m/%Y"),
                    'hora_str': ahora_ar.strftime("%H:%M")
                }
                db.collection("ventas_procesadas").add(nueva_venta)
                st.session_state.carrito = []
                st.success("¡Venta registrada con éxito!")
                st.rerun()

    with t2:
        st.subheader("📉 Registro de Gastos Diarios")
        gasto_desc = st.text_input("Concepto del gasto (ej: Luz, Alquiler, Proveedor)")
        gasto_monto = st.number_input("Importe $", min_value=0.0)
        if st.button("Registrar Gasto"):
            db.collection("gastos").add({
                'id_negocio': neg_id,
                'descripcion': gasto_desc,
                'monto': gasto_monto,
                'fecha_str': ahora_ar.strftime("%d/%m/%Y"),
                'fecha_completa': ahora_ar
            })
            st.success("Gasto guardado")

    with t3:
        st.subheader("📜 Historial de Ventas")
        ventas_recientes = db.collection("ventas_procesadas").where("id_negocio", "==", neg_id).order_by("fecha_completa", direction="DESCENDING").limit(20).stream()
        for v in ventas_recientes:
            d = v.to_dict()
            st.write(f"✅ **{d['fecha_str']} {d['hora_str']}** - {d['cliente_nombre']} - Total: **${d['total']:,.2f}** ({d['metodo']})")

    with t4:
        st.subheader("👥 Registro de Clientes Nuevos")
        with st.form("form_nuevo_cliente"):
            nombre_cliente = st.text_input("Nombre Completo")
            dni_cliente = st.text_input("DNI (se usará como contraseña)")
            cobro_cliente = st.text_input("Día de cobro o Promesa de pago")
            if st.form_submit_button("Guardar Cliente"):
                db.collection("usuarios").add({
                    'id_negocio': neg_id,
                    'nombre': nombre_cliente,
                    'password': dni_cliente,
                    'rol': 'cliente',
                    'promesa_pago': cobro_cliente
                })
                st.success(f"Cliente {nombre_cliente} dado de alta.")

    # --- NOTA FINAL IMPORTANTE (RESTABLECIDA) ---
    st.markdown("---")
    st.info("💡 **Nota del Sistema:** Los precios se sincronizan automáticamente con la planilla de Google. Para cambios masivos, edite el archivo Sheets y reinicie la app.")

# ==========================================
# 4. LOGIN Y PANEL LATERAL (RESTABLECIDO)
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.update({
        'autenticado': False, 'usuario': None, 'rol': None, 
        'id_negocio': None, 'nombre_real': None, 'carrito': [], 
        'df_proveedor': None, 'fecha_pago_cliente': None
    })

if not st.session_state.autenticado:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        if os.path.exists(IMG_LOGIN): 
            st.image(IMG_LOGIN, use_container_width=True)
        mostrar_cabecera_identidad()
        neg_input = st.text_input("ID Negocio").strip().lower()
        user_input = st.text_input("Nombre de Usuario").strip()
        pass_input = st.text_input("Contraseña", type="password").strip()
        
        if st.button("INGRESAR", use_container_width=True, type="primary"):
            user_query = db.collection("usuarios").where("id_negocio", "==", neg_input).where("nombre", "==", user_input).limit(1).get()
            if user_query and str(user_query[0].to_dict().get('password')) == pass_input:
                user_data = user_query[0].to_dict()
                st.session_state.update({
                    'autenticado': True,
                    'usuario': user_query[0].id,
                    'rol': str(user_data.get('rol')).strip().lower(),
                    'id_negocio': user_data.get('id_negocio'),
                    'nombre_real': user_data.get('nombre'),
                    'fecha_pago_cliente': user_data.get('promesa_pago', 'No especificada')
                })
                st.rerun()
            else:
                st.error("❌ Los datos ingresados son incorrectos.")
else:
    # --- PANEL IZQUIERDO (SIDEBAR) ---
    with st.sidebar:
        if os.path.exists(IMG_SIDEBAR): 
            st.image(IMG_SIDEBAR, width=150)
        
        st.markdown(f"### Bienvenido,\n**{st.session_state.nombre_real}**")
        st.write(f"🏢 Negocio: **{st.session_state.id_negocio.upper()}**")
        
        if st.session_state.rol == "negocio":
            st.success("⚙️ MODO ADMINISTRADOR")
        else:
            st.info("👤 MODO CLIENTE")
            st.write(f"📅 Pago pactado: {st.session_state.fecha_pago_cliente}")
            
        st.divider()
        if st.button("🔴 Cerrar Sesión", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    # --------------------------------

    # CONTROL DE VISTAS SEGÚN ROL
    if st.session_state.rol == "cliente":
        mostrar_vistas_cliente(st.session_state.nombre_real, st.session_state.fecha_pago_cliente, st.session_state.usuario)
    else:
        mostrar_vistas_negocio(st.session_state.id_negocio, st.session_state.nombre_real)
