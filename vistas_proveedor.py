import streamlit as st
def mostrar_vistas_pendientes():
    st.write("Próximamente...")
# Agregar esto al final de la vista del dueño o en un botón de "Ayuda"
with st.expander("🆘 Reportar un problema técnico"):
    mensaje_error = st.text_area("¿Qué está fallando?", placeholder="Ej: No puedo cargar el stock...")
    tipo_error = st.selectbox("Categoría", ["Error de Carga", "Login", "Stock", "Otros"])
    
    if st.button("Enviar Reporte a Soporte"):
        if mensaje_error:
            nuevo_reporte = {
                "id_negocio": id_negocio,
                "usuario": nombre_real,
                "mensaje": mensaje_error,
                "tipo": tipo_error,
                "fecha": ahora, # Usar la variable 'ahora' que ya tenés
                "estado": "pendiente"
            }
            db.collection("reportes_error").add(nuevo_reporte)
            st.success("✅ Reporte enviado. El administrador lo revisará pronto.")
            st.balloons() # La animación que te gusta
