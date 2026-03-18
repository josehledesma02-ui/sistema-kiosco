import streamlit as st
from database import conectar_firebase, obtener_hora_argentina
import login
import vistas_dueno
import vistas_cliente

# ==========================================
# 1. CONFIGURACIÓN VISUAL PRO (UI/UX)
# ==========================================
st.set_page_config(
    page_title="JL Gestión Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ... (Tus estilos CSS se mantienen igual, los omito aquí para acortar pero NO los borres) ...

# ==========================================
# 2. INICIALIZACIÓN DE SERVICIOS
# ==========================================
db = conectar_firebase()
ahora = obtener_hora_argentina()

if 'autenticado' not in st.session_state:
    st.session_state.update({
        'autenticado': False,
        'rol': None,
        'usuario_id': None,
        'nombre_real': None,
        'id_negocio': None,
        'nivel_acceso': 1  # <--- Agregamos el nivel por defecto
    })

# ==========================================
# 3. CONTROL DE ACCESO (LOGIN O PANEL)
# ==========================================

if not st.session_state.autenticado:
    with st.container():
        st.markdown("<h2 style='text-align: center;'>🚀 Acceso al Sistema</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            id_neg_input = st.text_input("🆔 ID del Negocio").strip()
            user_input = st.text_input("👤 Usuario").strip()
            pass_input = st.text_input("🔑 Contraseña (DNI)", type="password").strip()
            
            btn_login = st.form_submit_button("INGRESAR", use_container_width=True)
            
            if btn_login:
                if id_neg_input and user_input and pass_input:
                    usuarios_ref = db.collection("usuarios").where("id_negocio", "==", id_neg_input).stream()
                    encontrado = False
                    for doc in usuarios_ref:
                        u = doc.to_dict()
                        nombre_db = str(u.get("nombre_real", "")).lower().strip()
                        usuario_db = str(u.get("usuario", "")).lower().strip()
                        input_cliente = user_input.lower().strip()
                        clave_db = str(u.get("clave", "")).strip()
                        
                        if (input_cliente == nombre_db or input_cliente == usuario_db) and pass_input == clave_db:
                            # --- GUARDAMOS EL NIVEL DE ACCESO AL ENTRAR ---
                            st.session_state.update({
                                'autenticado': True,
                                'rol': u.get("rol"),
                                'usuario_id': doc.id,
                                'nombre_real': u.get("nombre_real"),
                                'id_negocio': id_neg_input,
                                'nivel_acceso': u.get("nivel_acceso", 1) # <--- CAPTURAMOS EL NIVEL DE FIREBASE
                            })
                            encontrado = True
                            st.rerun()
                            break
                    if not encontrado:
                        st.error("❌ Datos incorrectos.")
                else:
                    st.warning("⚠️ Completá todos los campos.")
else:
    # ==========================================
    # 4. FILTRO DE SEGURIDAD (LOS 3 NIVELES)
    # ==========================================
    nivel = st.session_state.get("nivel_acceso", 1)
    
    # --- NIVEL 3: BLOQUEO TOTAL ---
    if nivel == 3:
        st.markdown(f"""
            <div style="background-color:#ff4b4b; padding:30px; border-radius:15px; text-align:center; color:white;">
                <h1>🚫 ACCESO SUSPENDIDO</h1>
                <p style="font-size:20px;">Tu cuenta en <b>{st.session_state.id_negocio.upper()}</b> presenta una deuda pendiente.</p>
                <hr>
                <p>Para rehabilitar el servicio, por favor contactate con <b>José Admin</b>.</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("Cerrar Sesión"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
        st.stop() # DETIENE LA EJECUCIÓN TOTAL DE LA APP

    # --- BARRA LATERAL (SIDEBAR) ---
    with st.sidebar:
        # (Tu código de logo y notificaciones de error se mantiene igual)
        # ... 
        
        # --- NIVEL 1: AVISO DE PAGO PENDIENTE ---
        if nivel == 2:
            st.warning("⚠️ CUENTA RESTRINGIDA")
        elif nivel == 1:
            st.success("✅ CUENTA ACTIVA")

        st.write(f"👤 **{st.session_state.nombre_real}**")
        # ... (Resto del sidebar igual)

    # --- REPARTIDOR DE VISTAS SEGÚN ROL ---
    rol = st.session_state.rol
    
    # --- NIVEL 2: RESTRICCIÓN DE FUNCIONES ---
    # Pasamos el nivel a las vistas para que sepan si deben bloquear botones
    restringido = True if nivel == 2 else False

    if rol == "negocio":
        # Agregamos 'restringido' a la llamada si tu función lo soporta
        vistas_dueno.mostrar_dueno(db, st.session_state.id_negocio, ahora, st.session_state.nombre_real)
        if restringido: st.warning("📢 Estás en modo 'Solo Lectura'. No podrás realizar ventas ni modificaciones.")

    elif rol == "cliente":
        vistas_cliente.mostrar_cliente(db, st.session_state.id_negocio, st.session_state.nombre_real)

    elif rol == "super_admin":
        import vistas_super_admin
        vistas_super_admin.mostrar_super_admin(db, ahora)

    elif rol == "empleado":
        import vistas_empleado
        vistas_empleado.mostrar_empleado(db, st.session_state.id_negocio, ahora)
