import streamlit as st
import pandas as pd
import plotly.express as px

def mostrar(db):
    st.header("📊 Dashboard Global de la Red")
    
    # Traer todas las ventas de la base de datos
    ventas_ref = db.collection("ventas_procesadas").stream()
    datos = [v.to_dict() for v in ventas_ref]
    
    if not datos:
        st.info("Aún no hay ventas procesadas en la red para mostrar estadísticas.")
        return

    df = pd.DataFrame(datos)
    # Convertir total a numérico por seguridad
    df['total'] = pd.to_numeric(df['total'], errors='coerce')

    # Métricas arriba
    c1, c2, c3 = st.columns(3)
    c1.metric("Recaudación Total Red", f"${df['total'].sum():,.2f}")
    c2.metric("Negocios con Ventas", df['id_negocio'].nunique())
    c3.metric("Ventas Procesadas", len(df))

    # Gráfico 1: Ventas por Negocio
    st.subheader("📈 Facturación por Local")
    ventas_negocio = df.groupby("id_negocio")["total"].sum().reset_index()
    fig_neg = px.pie(ventas_negocio, values='total', names='id_negocio', hole=0.4, title="Reparto de Ventas")
    st.plotly_chart(fig_neg, use_container_width=True)

    # Gráfico 2: Los más vendidos (Top 10)
    st.subheader("🏆 Productos Estrella en la Red")
    all_prods = []
    for prods_lista in df['productos']:
        for p in prods_lista:
            all_prods.append({"Producto": p.get("nombre"), "Cantidad": p.get("cantidad")})
    
    df_p = pd.DataFrame(all_prods)
    top_prods = df_p.groupby("Producto")["Cantidad"].sum().sort_values(ascending=False).head(10).reset_index()
    fig_prod = px.bar(top_prods, x="Cantidad", y="Producto", orientation='h', color="Cantidad")
    st.plotly_chart(fig_prod, use_container_width=True)
