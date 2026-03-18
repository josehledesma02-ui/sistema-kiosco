import streamlit as st
from modulos_dueno import vender, gastos, historial, clientes, estadisticas # <--- Agregamos este

def mostrar_dueno(db, id_negocio, ahora_ar, nombre_u):
    st.title(f"🏬 Gestión Pro: {id_negocio.upper()}")
    
    # Agregamos la pestaña "Dashboard" al principio porque al dueño es lo que más le importa
    t1, t2, t3, t4, t5 = st.tabs([
        "📊 Dashboard", "🛒 Vender", "📉 Gastos", "📜 Historial", "👥 Clientes"
    ])

    with t1:
        estadisticas.renderizar(db, id_negocio) # El nuevo módulo
        
    with t2:
        vender.renderizar(db, id_negocio, ahora_ar, nombre_u)
        
    with t3:
        gastos.renderizar(db, id_negocio, ahora_ar)

    with t4:
        historial.renderizar(db, id_negocio)

    with t5:
        clientes.renderizar(db, id_negocio)

    st.divider()
    st.info("💡 **Nota:** Sistema modular JL Gestión v2.0")
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
