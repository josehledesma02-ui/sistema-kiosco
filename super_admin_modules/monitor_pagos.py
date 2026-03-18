import streamlit as st
import pandas as pd
from datetime import datetime

def mostrar(db):
    st.header("📈 Monitor de Cobros y Control de Acceso")
    st.markdown("Desde aquí controlás la 'salud' financiera de tus clientes y aplicás restricciones.")

    # 1. --- OBTENER DATOS DE NEGOCIOS ---
    negocios_ref = db.collection("usuarios").where("rol", "==", "negocio").stream()
    
    hoy = datetime.now()
    
    for n in negocios_ref:
        data = n.to_dict()
        doc_id = n.id
        id_negocio = data.get("id_negocio", "S/ID")
        nombre = data.get("nombre_negocio", "Sin Nombre")
        promesa = data.get("fecha_promesa_pago", "")
        nivel_actual = data.get("nivel_acceso", 1) # 1: Normal, 2: Restringido, 3: Bloqueado
        
        # Lógica de color según nivel
        color = "🟢" if nivel_actual == 1 else "🟡" if nivel_actual == 2 else "🔴"
        
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 2, 3])
            
            with col1:
                st.markdown(f"### {color} {nombre}")
                st.caption(f"ID: {id_negocio} | Tel: {data.get('telefono', 'S/D')}")
            
            with col2:
                st.write(f"**Vencimiento:** {promesa if promesa else 'No seteada'}")
                # Alerta visual si ya pasó la fecha
                if promesa:
                    try:
                        fecha_p = datetime.strptime(promesa, "%d/%m/%Y")
                        if hoy > fecha_p and nivel_actual == 1:
                            st.warning("⚠️ ¡FECHA VENCIDA!")
                    except:
                        st.error("Formato fecha incorrecto (usar DD/MM/YYYY)")

            with col3:
                st.write("**Acciones de Control:**")
                c1, c2, c3 = st.columns(3)
                
                # NIVEL 1: AVISO (Normal pero con cartel)
                if c1.button("🔔 Aviso", key=f"aviso_{id_negocio}", help="Muestra cartel de pago pendiente"):
                    db.collection("usuarios").document(doc_id).update({"nivel_acceso": 1})
                    st.toast(f"Aviso activado para {nombre}")
                    st.rerun()

                # NIVEL 2: RESTRINGIDO (No puede vender)
                if c2.button("⚠️ Restringir", key=f"restr_{id_negocio}", help="Bloquea carga de ventas"):
                    db.collection("usuarios").document(doc_id).update({"nivel_acceso": 2})
                    st.toast(f"Funciones restringidas para {nombre}")
                    st.rerun()

                # NIVEL 3: BLOQUEO TOTAL
                if c3.button("🚫 Bloquear", key=f"block_{id_negocio}", help="Corta el acceso total"):
                    db.collection("usuarios").document(doc_id).update({"nivel_acceso": 3})
                    st.toast(f"Acceso BLOQUEADO para {nombre}")
                    st.rerun()

    st.divider()
    st.info("""
    **Guía de Niveles:**
    - **Nivel 1 (Aviso):** El cliente usa todo, pero ve un recordatorio de pago.
    - **Nivel 2 (Restringido):** Puede ver stock y precios, pero los botones de 'Cerrar Venta' están deshabilitados.
    - **Nivel 3 (Bloqueado):** Al intentar entrar, el sistema lo expulsa con un aviso legal.
    """)
