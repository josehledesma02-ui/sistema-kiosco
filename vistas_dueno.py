import streamlit as st
import pandas as pd

# Configuración del Google Sheets
ID_HOJA = "1-ay_xIqYItwOaXe80VUsEmh4gsANrk9PH72aZcUD54g"
URL_PROVEEDOR_CSV = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/export?format=csv"

def mostrar_dueno(db, id_negocio, ahora_ar, nombre_u):
    st.markdown(f"## 🛠️ Panel de Control: {id_negocio.upper()}")
    
    t1, t2, t3, t4 = st.tabs(["🛒 Nueva Venta", "📉 Gastos", "📜 Historial", "👥 Clientes"])

    with t1:
        # --- Lógica de Inventario ---
        if 'df_proveedor' not in st.session_state or st.session_state.df_proveedor is None:
            try:
                df = pd.read_csv(URL_PROVEEDOR_CSV) # Simplificado para el ejemplo
                st.session_state.df_proveedor = df
            except:
                st.error("No se pudo cargar la lista de precios.")
        
        # --- Interfaz de Carrito (Resumen) ---
        st.write("Seleccioná productos y registrá la venta aquí.")
        # (Aquí va el código del buscador y botones que ya teníamos)

    with t2:
        st.subheader("Registro de Gastos")
        desc = st.text_input("Concepto")
        monto = st.number_input("Monto $", min_value=0.0)
        if st.button("Guardar Gasto"):
            db.collection("gastos").add({
                'id_negocio': id_negocio, 'descripcion': desc, 
                'monto': monto, 'fecha': ahora_ar
            })
            st.success("Gasto registrado")

    with t3:
        st.subheader("Últimos movimientos")
        # Consulta rápida a Firebase para ver ventas

    with t4:
        st.subheader("Alta de Clientes")
        # Formulario para crear nuevos clientes

    # --- LA NOTA INVISIBLE (Que ahora es fija) ---
    st.markdown("---")
    st.info("💡 **Nota del Sistema:** Recordá que los precios se sincronizan con Google Sheets. Si hay errores de precio, revisá la planilla online.")
