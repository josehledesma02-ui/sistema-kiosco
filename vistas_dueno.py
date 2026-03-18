import streamlit as st
from modulos_dueno import vender, gastos, historial, clientes, estadisticas, reportes

def mostrar_dueno(db, id_negocio, ahora_ar, nombre_u):
    # 1. VERIFICACIÓN DE NIVEL DE ACCESO
    nivel = st.session_state.get("nivel_acceso", 1)
    es_restringido = True if nivel == 2 else False

    # 2. Título principal
    st.title(f"🏬 Gestión Pro: {id_negocio.upper()}")
    
    # Si está restringido, metemos el aviso de entrada
    if es_restringido:
        st.warning("⚠️ **CUENTA RESTRINGIDA POR FALTA DE PAGO**")
        st.info("Tu acceso ha sido limitado a 'Modo Lectura'. No podrás registrar nuevas ventas ni gastos hasta regularizar la situación con el administrador.")

    # 3. Configuración de 6 Pestañas
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "💰 Vender", "📉 Gastos", "📜 Historial", "👥 Clientes", "📊 Estadísticas", "🆘 Soporte"
    ])
    
    with tab1:
        if es_restringido:
            st.error("🚫 Función de Venta Deshabilitada.")
            st.write("Para volver a vender, por favor realizá el pago del abono mensual.")
        else:
            vender.renderizar(db, id_negocio, ahora_ar, nombre_u)
    
    with tab2:
        if es_restringido:
            st.error("🚫 Función de Gastos Deshabilitada.")
        else:
            gastos.renderizar(db, id_negocio, ahora_ar)
        
    with tab3:
        # El historial lo dejamos que lo vea, para que no diga que no sabe qué vendió
        historial.renderizar(db, id_negocio)
        
    with tab4:
        # Clientes también, por si tiene que cobrar deudas para pagarte a vos
        clientes.renderizar(db, id_negocio)
        
    with tab5:
        # Estadísticas en modo lectura
        estadisticas.renderizar(db, id_negocio)
        
    with tab6:
        # Soporte siempre disponible, pero podés pasarle el estado 'es_restringido' 
        # dentro del módulo si querés bloquear el formulario de envío.
        reportes.renderizar(db, id_negocio, ahora_ar, nombre_u)
