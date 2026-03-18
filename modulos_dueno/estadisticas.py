import streamlit as st
import pandas as pd
import plotly.express as px

def renderizar(db, id_negocio):
    st.subheader("📊 Tablero de Inteligencia de Negocio")
    
    # 1. Traer datos de Firebase
    try:
        ventas_ref = db.collection("ventas_procesadas").where("id_negocio", "==", id_negocio).stream()
        data = [v.to_dict() for v in ventas_ref]
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        return
    
    # Si no hay ninguna venta registrada aún
    if not data:
        st.info("👋 ¡Bienvenido! Aún no hay ventas registradas para generar estadísticas. Realiza tu primera venta para ver los gráficos.")
        return

    # Convertimos a DataFrame de Pandas para procesar
    df = pd.DataFrame(data)
    
    # --- LIMPIEZA Y PREPARACIÓN DE DATOS ---
    if 'fecha_completa' in df.columns:
        df['fecha_completa'] = pd.to_datetime(df['fecha_completa'])
    
    # Aseguramos que existan las columnas numéricas
    if 'total' not in df.columns:
        df['total'] = 0

    # --- KPI PRINCIPALES (TARJETAS) ---
    st.markdown("### 📈 Resumen General")
    c1, c2, c3 = st.columns(3)
    
    total_ventas = df['total'].sum()
    cantidad_op = len(df)
    ticket_promedio = total_ventas / cantidad_op if cantidad_op > 0 else 0
    
    c1.metric("Ventas Totales", f"${total_ventas:,.2f}")
    c2.metric("Cant. Operaciones", cantidad_op)
    c3.metric("Ticket Promedio", f"${ticket_promedio:,.2f}")

    st.divider()

    # --- RANKINGS Y GRÁFICOS ---
    col_izq, col_der = st.columns(2)

    with col_izq:
        # TOP CLIENTES
        st.markdown("### 🏆 Top Clientes (Los que más compran)")
        if "cliente_nombre" in df.columns:
            # Agrupamos por nombre y sumamos el total
            top_clientes = df.groupby("cliente_nombre")["total"].sum().sort_values(ascending=False).head(5)
            if not top_clientes.empty:
                st.bar_chart(top_clientes)
            else:
                st.write("No hay datos de clientes específicos.")
        else:
            st.info("No se encontraron nombres de clientes en el historial.")

        # VENTAS POR HORA
        st.markdown("### 🕒 ¿A qué hora vendés más?")
        if "hora_str" in df.columns:
            # Extraemos la hora (ej: "14:30" -> "14")
            df['hora_eje'] = df['hora_str'].apply(lambda x: x.split(":")[0] if isinstance(x, str) else "00")
            ventas_hora = df.groupby("hora_eje").size()
            st.line_chart(ventas_hora)
        else:
            st.write("Datos de horario no disponibles.")

    with col_der:
        # PRODUCTOS ESTRELLA
        st.markdown("### 📦 Productos más vendidos")
        if "items" in df.columns:
            items_totales = []
            for lista in df['items']:
                if isinstance(lista, list):
                    items_totales.extend(lista)
            
            if items_totales:
                df_items = pd.DataFrame(items_totales)
                if "nombre" in df_items.columns:
                    prod_ranking = df_items.groupby("nombre")["cantidad"].sum().sort_values(ascending=False).head(5)
                    st.table(prod_ranking)
                else:
                    st.write("Los productos no tienen nombres registrados.")
            else:
                st.write("No hay ítems detallados en las ventas.")
        else:
            st.write("Columna de ítems no encontrada.")

        # RANKING VENDEDORES
        st.markdown("### 👷 Desempeño de Empleados")
        if "vendedor" in df.columns:
            vendedores = df.groupby("vendedor")["total"].sum().sort_values(ascending=False)
            st.bar_chart(vendedores)
        else:
            st.write("No hay registros de quién realizó las ventas.")

    st.divider()
    st.caption("💡 Tip: Estos datos se actualizan en tiempo real cada vez que registras una venta.")
