import streamlit as st
import requests
import base64
from datetime import datetime

def subir_a_imgbb(archivo):
    """Sube la imagen a ImgBB vía API y devuelve la URL pública"""
    api_key = "cb9cd6639ea8380f0eced8666c17177b" 
    url = "https://api.imgbb.com/1/upload"
    try:
        archivo_buscado = archivo.read()
        imagen_base64 = base64.b64encode(archivo_buscado).decode('utf-8')
        payload = {"key": api_key, "image": imagen_base64}
        res = requests.post(url, payload)
        if res.status_code == 200:
            return res.json()['data']['url']
        return None
    except Exception as e:
        st.error(f"Error al procesar la imagen: {e}")
        return None

def renderizar(db, id_negocio, ahora_ar, nombre_u):
    # --- SECCIÓN DE NOTIFICACIONES (Tilde Verde) ---
    try:
        # Buscamos si hay reportes resueltos para este negocio
        resueltos = db.collection("reportes_error")\
                      .where("id_negocio", "==", id_negocio)\
                      .where("estado", "==", "resuelto")\
                      .limit(3).stream()
        
        for res in resueltos:
            datos = res.to_dict()
            with st.status(f"✅ JL Gestión solucionó: {datos.get('tipo')}", expanded=False):
                st.write(f"Tu reporte del {datos.get('fecha')[:10]} ha sido marcado como resuelto.")
                if st.button("Entendido / Borrar aviso", key=f"ok_{res.id}"):
                    db.collection("reportes_error").document(res.id).delete()
                    st.rerun()
    except:
        pass

    st.markdown("### 🆘 Centro de Reportes y Soporte")
    st.info("Describí el inconveniente. Podés adjuntar capturas de pantalla.")

    with st.form("form_reporte_pro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tipo = st.selectbox("Categoría", ["Error Visual", "Error de Datos", "Falla de Sistema", "Sugerencia"])
        with col2:
            prioridad = st.select_slider("Prioridad", options=["Baja", "Media", "Alta", "Urgente"])

        detalle = st.text_area("Descripción detallada:", placeholder="Ej: El botón de imprimir ticket no reacciona...")
        fotos = st.file_uploader("📸 Adjuntar capturas (Opcional)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

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
                            if link: urls_imagenes.append(link)

                try:
                    reporte = {
                        "id_negocio": id_negocio,
                        "usuario": nombre_u,
                        "tipo": tipo,
                        "prioridad": prioridad,
                        "mensaje": detalle,
                        "fecha": ahora_ar.isoformat(),
                        "estado": "pendiente",
                        "fotos": urls_imagenes # Guardamos como 'fotos' para el historial
                    }
                    
                    db.collection("reportes_error").add(reporte)
                    st.success("✅ ¡Reporte enviado! Lo revisaremos pronto.")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

    st.markdown("---")
    url_wa = f"https://wa.me/543865379027?text=Hola,%20soy%20{nombre_u}%20de%20{id_negocio}.%20Envié%20un%20reporte%20por:"
    st.link_button("📲 Contacto Urgente por WhatsApp", url_wa)
