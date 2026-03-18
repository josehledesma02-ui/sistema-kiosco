import streamlit as st
from datetime import datetime

def renderizar(db, id_negocio, ahora_ar, nombre_u):
    st.markdown("""
        <style>
            .header-reporte {
                background-color: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                border-left: 5px solid #FF4B4B;
                margin-bottom: 20px;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="header-reporte"><h2>📩 Centro de Reportes</h2>'
                '<p>Describí el inconveniente para que el equipo técnico de <b>JL GESTIÓN</b> pueda ayudarte.</p></div>', 
                unsafe_allow_html=True)

    with st.form("form_reporte_completo", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            tipo = st.selectbox("¿Qué tipo de problema tenés?", [
                "Error Visual (Cosas que se ven mal)", 
                "Error de Datos (Precios o stock incorrectos)", 
                "Error de Sistema (Botones que no funcionan)",
                "Sugerencia / Nueva Función",
                "Otro"
            ])
            
        with col2:
            prioridad = st.select_slider("Prioridad del problema", 
                                       options=["Baja", "Media", "Alta", "Urgente"])

        detalle = st.text_area("Describí el problema detalladamente:", 
                              placeholder="Ej: Cuando intento vaciar el carrito, el botón no responde y queda la pantalla en blanco.")

        # --- SECCIÓN DE ADJUNTOS ---
        st.write("🖼️ **Adjuntar evidencia (Fotos o Videos)**")
        archivos = st.file_uploader("Arrastrá tus capturas aquí", 
                                  type=['png', 'jpg', 'jpeg', 'mp4', 'mov'], 
                                  accept_multiple_files=True)

        enviar = st.form_submit_button("🚀 ENVIAR REPORTE A JL GESTIÓN", use_container_width=True)

        if enviar:
            if not detalle:
                st.warning("⚠️ Por favor, describí el problema para poder ayudarte.")
            else:
                try:
                    # Aquí preparamos los datos
                    reporte_data = {
                        "id_negocio": id_negocio,
                        "usuario": nombre_u,
                        "tipo": tipo,
                        "prioridad": prioridad,
                        "mensaje": detalle,
                        "fecha": ahora_ar.isoformat(),
                        "estado": "pendiente",
                        "tiene_adjuntos": True if archivos else False
                    }
                    
                    # Guardamos en la colección de Firebase
                    db.collection("reportes_error").add(reporte_data)
                    
                    st.success("✅ ¡Reporte enviado con éxito! El equipo de JL Gestión lo revisará a la brevedad.")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Error al enviar: {e}")
