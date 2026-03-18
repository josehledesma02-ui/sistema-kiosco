import streamlit as st
from modulos_dueno import vender, gastos, historial, clientes, estadisticas # <--- Agregamos este

def mostrar_dueno(db, id_negocio, ahora_ar, nombre_u):
    st.title(f"🏬 Gestión Pro: {id_negocio.upper()}")
    
    # ==========================================
# SECCIÓN DE SOPORTE TÉCNICO (AGREGAR AL FINAL)
# ==========================================
st.markdown("---")
with st.expander("🆘 ¿Tenés algún problema o duda? Reportalo aquí"):
    st.subheader("📩 Centro de Reportes")
    
    # Formulario rápido
    with st.form("form_reporte_error", clear_on_submit=True):
        tipo_fallo = st.selectbox("¿Qué sucede?", [
            "Error Visual", 
            "Error al Cargar Datos", 
            "Lentitud en el Sistema", 
            "Sugerencia de Mejora",
            "Otro"
        ])
        
        detalle = st.text_area("Describí brevemente lo que pasó:", 
                              placeholder="Ej: No se actualiza el precio del alfajor...")
        
        btn_enviar = st.form_submit_button("ENVIAR REPORTE A JL GESTIÓN")

        if btn_enviar:
            if detalle:
                # Datos del reporte
                reporte = {
                    "id_negocio": id_negocio,  # Asegurate de que esta variable llegue a la función
                    "usuario": nombre_real,    # Asegurate de que esta variable llegue a la función
                    "mensaje": detalle,
                    "tipo": tipo_fallo,
                    "fecha": ahora,            # Usar la variable de tiempo que ya tenés
                    "estado": "pendiente"
                }
                
                # Guardar en Firebase
                db.collection("reportes_error").add(reporte)
                
                st.success("✅ ¡Gracias! Tu reporte fue enviado al Administrador.")
                st.balloons() # ¡La animación que te gusta!
            else:
                st.warning("⚠️ Por favor, escribí un detalle para que podamos ayudarte.")
