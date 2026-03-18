import streamlit as st

def mostrar(db):
    st.header("🏪 Gestión Agresiva de Negocios")
    
    # 1. Obtener lista de todos los negocios registrados
    negocios_ref = db.collection("usuarios").where("rol", "==", "negocio").stream()
    negocios_dict = {n.to_dict().get('id_negocio'): n.to_dict().get('nombre_real') for n in negocios_ref}
    
    if not negocios_dict:
        st.warning("No se encontraron negocios registrados.")
        return

    # Selector de Negocio
    id_sel = st.selectbox("Seleccioná el negocio a intervenir:", 
                          options=list(negocios_dict.keys()), 
                          format_func=lambda x: f"{x.upper()} - {negocios_dict[x]}")

    if id_sel:
        menu_edit = st.radio("¿Qué querés gestionar?", ["👥 Clientes/Deudas", "📦 Stock de Productos", "🔑 Usuarios/Roles"], horizontal=True)
        st.divider()

        # --- GESTIÓN DE CLIENTES ---
        if menu_edit == "👥 Clientes/Deudas":
            st.subheader(f"Clientes de {id_sel}")
            clientes = db.collection("clientes").where("id_negocio", "==", id_sel).stream()
            for c in clientes:
                c_data = c.to_dict()
                with st.expander(f"👤 {c_data.get('nombre')} - DNI: {c_data.get('dni')}"):
                    with st.form(f"form_cli_{c.id}"):
                        nuevo_nom = st.text_input("Nombre completo", value=c_data.get("nombre"))
                        nuevo_tel = st.text_input("Teléfono", value=c_data.get("telefono"))
                        nueva_fecha = st.text_input("Promesa de Pago", value=c_data.get("fecha_pago"))
                        
                        if st.form_submit_button("💾 GUARDAR CAMBIOS"):
                            db.collection("clientes").document(c.id).update({
                                "nombre": nuevo_nom,
                                "telefono": nuevo_tel,
                                "fecha_pago": nueva_fecha
                            })
                            st.success("Cliente actualizado correctamente.")
                            st.rerun()

        # --- GESTIÓN DE PRODUCTOS ---
        elif menu_edit == "📦 Stock de Productos":
            st.subheader(f"Inventario de {id_sel}")
            prods = db.collection("productos").where("id_negocio", "==", id_sel).stream()
            for p in prods:
                p_data = p.to_dict()
                with st.expander(f"📦 {p_data.get('nombre')} - Stock: {p_data.get('stock')}"):
                    with st.form(f"form_prod_{p.id}"):
                        n_prod = st.text_input("Nombre del producto", value=p_data.get("nombre"))
                        n_stock = st.number_input("Stock actual", value=float(p_data.get("stock", 0)))
                        n_precio = st.number_input("Precio Venta", value=float(p_data.get("precio", 0)))
                        
                        if st.form_submit_button("💾 ACTUALIZAR PRODUCTO"):
                            db.collection("productos").document(p.id).update({
                                "nombre": n_prod,
                                "stock": n_stock,
                                "precio": n_precio
                            })
                            st.success("Producto modificado.")
                            st.rerun()
