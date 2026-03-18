import streamlit as st
from datetime import datetime
import google.generativeai as genai

def mostrar(db):
    st.subheader("📩 Bandeja de Entrada: Soporte Técnico")
    
    # --- CONFIGURACIÓN DE GÉMINIS ---
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.warning("⚠️ Chat de IA no disponible: Revisá la API Key en Secrets.")

    try:
        reportes_ref = db.collection("reportes_error").where("estado", "==", "pendiente").order_by("fecha", direction="DESCENDING").stream()
        
        hay_reportes = False
        for i, doc in enumerate(reportes_ref):
            hay_reportes = True
            rep = doc.to_dict()
            id_doc = doc.id
            
            # Procesar fecha para mostrar
            f_valor = rep.get("fecha", "")
            f_corta = f_valor[8:10] + "/" + f_valor[5:7] + " " + f_valor[11:16]

            # Semáforo de prioridad
            prio = rep.get("prioridad", "Baja")
            emoji = "🔴" if "Urgent" in prio else "🟠" if "Alta" in prio else "🟡" if "Media" in prio else "🟢"

            with st.expander(f"{emoji} {rep.get('id_negocio').upper()} - {rep.get('tipo')} ({f_corta})"):
                st.write(f"**👤 Usuario:** {rep.get('usuario')}")
                st.info(f"**💬 Mensaje:** {rep.get('mensaje')}")
                
                # Mostrar fotos si hay
                fotos = rep.get("fotos") or []
                if fotos:
                    cols = st.columns(len(fotos) if len(fotos) < 4 else 3)
                    for idx, link in enumerate(fotos):
                        with cols[idx % 3]: st.image(link, use_container_width=True)

                # --- 🤖 CHAT CON GÉMINIS (JL-IA) ---
                st.markdown("---")
                st.markdown("#### 🤖 Consultar a Asistente de IA")
                consulta = st.text_input("José, ¿qué necesitás saber sobre este error?", key=f"ai_{id_doc}")
                
                if consulta:
                    with st.spinner("Analizando reporte..."):
                        # Le envío a la IA el contexto del problema para que sepa de qué hablamos
                        prompt = f"""
                        Contexto del error en el sistema de kioscos:
                        - Negocio: {rep.get('id_negocio')}
                        - Tipo de problema: {rep.get('tipo')}
                        - Mensaje del usuario: {rep.get('mensaje')}
                        - Pregunta de José (Desarrollador): {consulta}
                        
                        Responde de forma técnica y breve para ayudar a solucionar el problema.
                        """
                        respuesta = model.generate_content(prompt)
                        st.chat_message("assistant").write(respuesta.text)

                st.divider()
                # Botones de acción
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Resolver", key=f"res_{id_doc}"):
                        db.collection("reportes_error").document(id_doc).update({
                            "estado": "resuelto",
                            "fecha_resolucion": datetime.now().isoformat()
                        })
                        st.rerun()
                with c2:
                    if st.button("🗑️ Eliminar", key=f"del_{id_doc}"):
                        db.collection("reportes_error").document(id_doc).delete()
                        st.rerun()

        if not hay_reportes:
            st.success("🙌 Todo al día, José. No hay reportes pendientes.")

    except Exception as e:
        st.error(f"Error: {e}")
