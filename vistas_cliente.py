import streamlit as st
import pandas as pd

def mostrar_cliente(db, id_negocio, nombre_cliente):
    # 1. BÚSQUEDA DE DATOS (Ficha y Ventas)
    cliente_data = None
    clientes_ref = db.collection("clientes").where("id_negocio", "==", id_negocio).stream()
    for doc in clientes_ref:
        d = doc.to_dict()
        if str(d.get("nombre", "")).lower().strip() == str(nombre_cliente).lower().strip():
            cliente_data = d
            break

    ventas_ref = db.collection("ventas_procesadas")\
        .where("id_negocio", "==", id_negocio)\
        .where("cliente_nombre", "==", nombre_cliente)\
        .where("metodo", "==", "Fiado").stream()
    
    lista_compras = []
    total_deuda = 0
    
    for v in ventas_ref:
        v_dict = v.to_dict()
        total_deuda += v_dict.get("total", 0)
        
        # Extraemos fecha y hora
        fecha_completa = v_dict.get("fecha", "S/F") # Asumimos formato "DD/MM/YYYY HH:MM"
        
        productos = v_dict.get("productos", [])
        for p in productos:
            cant = p.get("cantidad", 0)
            pu = p.get("precio", 0)
            sub = p.get("subtotal", cant * pu)
            
            lista_compras.append({
                "📅 Fecha/Hora": fecha_completa,
                "📦 Producto": p.get("nombre"),
                "🔢 Cant.": cant,
                "💰 P. Unit": f"${pu:,.2f}",
                "💵 Subtotal": sub
            })

    # --- DISEÑO DE LA PANTALLA ---
    st.markdown(f"# 👋 ¡Hola, {nombre_cliente}!")
    
    # Deuda con fuente GRANDE y GRUESA
    st.markdown(f"""
        <div style="background-color: #e1f5fe; padding: 20px; border-radius: 10px; border-left: 8px solid #0288d1;">
            <p style="margin-bottom: 0; color: #0288d1; font-weight: bold;">TU DEUDA TOTAL</p>
            <h1 style="margin-top: 0; font-size: 60px; font-weight: 900; color: #01579b;">
                ${total_deuda:,.2f}
            </h1>
        </div>
    """, unsafe_allow_html=True)

    st.write("") # Espacio
    
    fecha_pago = cliente_data.get("fecha_pago", "No pactada") if cliente_data else "N/A"
    st.info(f"📅 **Tu próxima fecha de pago pactada:** {fecha_pago}")

    # 4. TABLA DETALLADA
    st.markdown("### 🛒 Detalle de tus compras pendientes")
    
    if lista_compras:
        df = pd.DataFrame(lista_compras)
        
        # Mostramos la tabla con diseño limpio
        st.dataframe(
            df,
            column_config={
                "💵 Subtotal": st.column_config.NumberColumn(format="$%.2f"),
                "💰 P. Unit": st.column_config.TextColumn(), # Ya tiene el signo $ arriba
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.success("🎉 ¡No tenés compras pendientes de pago!")

    st.divider()
    st.caption("Si tenés dudas con algún cargo, por favor consultanos en el local.")
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
