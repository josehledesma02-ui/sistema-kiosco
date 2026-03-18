import streamlit as st
import pandas as pd
import plotly.express as px

def mostrar(db):
    st.header("📊 Dashboard Global de la Red")
    
    # 1. Traer todas las ventas de la colección 'ventas_procesadas'
    ventas_ref = db.collection("ventas_procesadas").stream()
    datos = []
    
    for v in ventas_ref:
        d = v.to_dict()
        # Guardamos el ID del documento por si lo necesitamos
        d['id_doc'] = v.id
        datos.append(d)
    
    if not datos:
        st.info("💡 Todavía no hay ventas registradas en 'ventas_procesadas'.")
        return

    df = pd.DataFrame(datos)

    # --- PROCESAMIENTO DE DATOS ---
    # Calculamos el total de cada venta sumando los subtotales de la lista 'items'
    def calcular_total(fila):
        lista_items = fila.get('items', [])
        if isinstance(lista_items, list):
            return sum(item.get('subtotal', 0) for item in lista_items)
        return 0

    df['total_calculado'] = df.apply(calcular_total, axis=1)

    # 2. Métricas Principales en pantalla
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Recaudación Red", f"${df['total_calculado'].sum():,.2f}")
    with c2:
        negocios = df['id_negocio'].nunique() if 'id_negocio' in df.columns else 0
        st.metric("Locales Activos", negocios)
    with c3:
        st.metric("Operaciones", len(df))

    st.divider()

    # 3. Gráfico de Ventas por Negocio
    if 'id_negocio' in df.columns:
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.subheader("📈 Ventas por Local")
            ventas_negocio = df.groupby("id_negocio")["total_calculado"].sum().reset_index()
            fig_neg = px.bar(ventas_negocio, x='id_negocio', y='total_calculado', 
                             labels={'total_calculado':'Pesos ($)', 'id_negocio':'Negocio'},
                             color='total_calculado', color_continuous_scale='Blues')
            st.plotly_chart(fig_neg, use_container_width=True)

        # 4. Gráfico de Productos (Top 10 más vendidos)
        with col_graf2:
            st.subheader("🏆 Lo más vendido")
            all_prods = []
            if 'items' in df.columns:
                for lista in df['items']:
                    if isinstance(lista, list):
                        for i in lista:
                            all_prods.append({
                                "Producto": i.get("nombre", "S/N"),
                                "Cantidad": i.get("cantidad", 0)
                            })
            
            if all_prods:
                df_p = pd.DataFrame(all_prods)
                top = df_p.groupby("Producto")["Cantidad"].sum().sort_values(ascending=False).head(10).reset_index()
                fig_prod = px.bar(top, x="Cantidad", y="Producto", orientation='h', 
                                  color="Cantidad", color_continuous_scale='Viridis')
                st.plotly_chart(fig_prod, use_container_width=True)
            else:
                st.write("No hay detalle de productos disponible.")

    # 5. Tabla de últimas transacciones
    st.subheader("📝 Últimos movimientos de la red")
    if 'id_negocio' in df.columns:
        # Simplificamos la tabla para que sea legible
        df_tabla = df[['id_negocio', 'total_calculado']].copy()
        df_tabla.columns = ['Negocio', 'Monto Total']
        st.dataframe(df_tabla.head(10), use_container_width=True, hide_index=True)
