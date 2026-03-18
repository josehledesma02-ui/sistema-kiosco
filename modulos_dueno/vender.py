import streamlit as st
import pandas as pd

def cargar_productos(db, id_negocio):
    try:
        # 1. Intentamos traer la colección de productos de este negocio
        productos_ref = db.collection("productos").where("id_negocio", "==", id_negocio).stream()
        lista_prod = [p.to_dict() for p in productos_ref]

        if not lista_prod:
            # Si la lista está vacía, devolvemos un DataFrame de ejemplo para que no explote
            st.warning("⚠️ No se encontraron productos en la base de datos.")
            return pd.DataFrame(columns=["nombre", "precio", "categoria", "stock"])

        df = pd.DataFrame(lista_prod)
        
        # 2. Limpieza de seguridad: Aseguramos que 'precio' sea número
        if 'precio' in df.columns:
            df['precio'] = pd.to_numeric(df['precio'], errors='coerce').fillna(0)
        else:
            df['precio'] = 0
            
        return df

    except Exception as e:
        st.error(f"❌ Error crítico al conectar con la lista de precios: {e}")
        # Devolvemos un DataFrame vacío para que el resto del código no de KeyError
        return pd.DataFrame(columns=["nombre", "precio", "categoria", "stock"])
