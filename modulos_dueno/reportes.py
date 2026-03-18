import streamlit as st
import requests
import base64
from datetime import datetime

def subir_a_imgbb(archivo):
    """Sube la imagen a ImgBB vía API y devuelve la URL pública"""
    # Tu API Key que sacamos de la captura
    api_key = "cb9cd6639ea8380f0eced8666c17177b" 
    
    url = "https://api.imgbb.com/1/upload"
    try:
        # Leemos el contenido del archivo y lo pasamos a base64
        archivo_buscado = archivo.read()
        imagen_base64 = base64.b64encode(archivo_buscado).decode('utf-8')
        
        payload = {
            "key": api_key,
            "image": imagen_base64,
        }
        
        res = requests.post(url, payload)
        if res.status_code == 200:
            return res.json()['data']['url']
        else:
            return None
    except Exception as e:
        st.error(f"Error al procesar la imagen: {e}")
        return None

def renderizar(db, id_negocio, ahora_ar, nombre_u):
    st.markdown("### 🆘 Centro de Reportes y Soporte")
    st.info("Describí el inconveniente. Podés adjuntar capturas de pantalla para ayudarnos a entender mejor.")

    with st.form("form_reporte_pro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tipo = st.selectbox("Categoría", [
                "Error Visual", 
                "Error de Datos (Precios/Stock)", 
                "Falla de Sistema", 
                "Sugerencia"
            ])
        with col2:
            prioridad = st.select_slider("Prioridad", options=["Baja", "Media", "Alta", "Urgente"])

        detalle = st.text_area("Descripción detallada:", 
                              placeholder="Ej: El botón de imprimir ticket no reacciona...")

        # Cargador de fotos
        fotos = st.file_uploader("📸 Adjuntar capturas (Opcional)", 
                                type=['png', 'jpg', 'jpeg'], 
                                accept_multiple_files=True)

        btn_enviar = st.form_submit_button("🚀 ENVIAR REPORTE A JL GESTIÓN", use_container_width=True)

        if btn_enviar:
            if not detalle:
                st.warning("⚠️ Por favor, describí el problema.")
            else:
                urls_imagenes = []
                
                if fotos:
                    with st.spinner("Subiendo imágenes..."):
                        for foto in fotos:
                            link = subir_a_imgbb(foto)
                            if link:
                                urls_imagenes.append(link)

                # Guardamos en Firebase
                try:
                    reporte = {
                        "id_negocio": id_negocio,
                        "usuario": nombre_u,
                        "tipo": tipo,
                        "prioridad": prioridad,
                        "mensaje": detalle,
                        "fecha": ahora_ar.isoformat(),
                        "estado": "pendiente",
                        "links_fotos": urls_imagenes
                    }
                    
                    db.collection("reportes_error").add(reporte)
                    st.success("✅ ¡Reporte enviado! Lo revisaremos pronto.")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

    # Botón de WhatsApp por si las dudas
    st.markdown("---")
    url_wa = f"https://wa.me/549381000000?text=Reporte%20de%20{id_negocio}:%20{detalle[:50]}..."
    st.link_button("📲 Contacto Urgente por WhatsApp", url_wa)
