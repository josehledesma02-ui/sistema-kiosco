import streamlit as st
import pandas as pd
import plotly.express as px # Para gráficos lindos

def renderizar(db, id_negocio):
    st.subheader("📊 Tablero de Inteligencia de Negocio")
    
    # 1. Traer TODOS los datos de ventas de este negocio
    ventas_ref = db.collection("ventas_procesadas").where("id_negocio", "==", id_negocio).stream()
    data = [v.to_dict() for v in ventas_ref]
    
    if not data:
        st.warning("Aún no hay ventas suficientes para generar estadísticas.")
        return

    df = pd.DataFrame(data)
    # Convertir fecha a objeto datetime si no lo es
    df['fecha_completa'] = pd.to_datetime(df['fecha_completa'])
    
    # --- FILTROS DE TIEMPO ---
    periodo = st.selectbox("Ver estadísticas de:", ["Hoy", "Esta Semana", "Este Mes", "Todo el historial"])
    # (Aquí podrías filtrar el DF según la fecha)

    # --- KPI PRINCIPALES ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Ventas Totales", f"${df['total'].sum():,.2f}")
    c2.metric("Cant. Operaciones", len(df))
    c3.metric("Ticket Promedio", f"${df['total'].mean():,.2f}")

    st.divider()

    # --- RANKINGS ---
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.markdown("### 🏆 Top Clientes (Los que más compran)")
        top_clientes = df.groupby("cliente_nombre")["total"].sum().sort_values(ascending=False)
        st.table(top_clientes.head(5))

        st.markdown("### 🕒 Ventas por Hora (¿Cuándo se vende más?)")
        # Extraemos la hora de la columna hora_str
        df['hora'] = df['hora_str'].str.split(":").str[0]
        ventas_hora = df.groupby("hora").size()
        st.bar_chart(ventas_hora)

    with col_der:
        st.markdown("### 📦 Productos Estrella")
        # Hay que "explotar" la lista de ítems que está dentro de cada venta
        items_lista = []
        for _, row in df.iterrows():
            for item in row['items']:
                items_lista.append(item)
        
        df_items = pd.DataFrame(items_lista)
        prod_ranking = df_items.groupby("nombre")["cantidad"].sum().sort_values(ascending=False)
        st.table(prod_ranking.head(5))

        st.markdown("### 👷 Ranking de Vendedores")
        vendedores = df.groupby("vendedor")["total"].sum().sort_values(ascending=False)
        st.bar_chart(vendedores)

    st.divider()
    st.markdown("### 🚩 Alerta de Morosos (Clientes atrasados)")
    # Aquí cruzaríamos con la fecha de promesa de pago que pusimos en el alta
    st.info("Esta sección requiere que el cliente tenga cargada su 'Promesa de Pago' en el perfil.")
