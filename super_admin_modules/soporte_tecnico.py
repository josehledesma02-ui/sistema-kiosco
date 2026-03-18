import streamlit as st

def mostrar(db):
    st.header("🛠️ Consola de Soporte Técnico")
    
    st.markdown("""
    ### 👨‍💻 Instrucciones de Soporte:
    1. Si un negocio reporta un error, pediles una captura o el texto del error.
    2. Pegalo abajo para analizarlo.
    3. Si necesitás modificar el código, recordá hacerlo en GitHub y sincronizar.
    """)

    error_input = st.text_area("Pegar Log de Error aquí:", height=150, placeholder="Traceback (most recent call last)...")
    
    if st.button("🧠 Analizar con IA"):
        if error_input:
            st.info("Enviando reporte a Gemini para diagnóstico...")
            # Aquí irá la conexión con mi API más adelante
            st.write("🤖 **Sugerencia inicial:** Revisá si el campo 'id_negocio' está bien escrito en la colección 'productos'.")
        else:
            st.warning("Pegá un error para analizar.")

    st.divider()
    st.subheader("🔐 Accesos Directos de Emergencia")
    if st.button("Limpiar Caché del Sistema"):
        st.cache_data.clear()
        st.success("Caché limpiada. Los datos se recargarán desde Firebase.")
