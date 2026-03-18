import streamlit as st
import pandas as pd
from datetime import datetime

def mostrar(db):
    st.header("🏪 Gestión Agresiva y Edición Total")
    
    # 1. --- RECOLECCIÓN DE DATOS PARA EL MONITOR Y SELECTOR ---
    negocios_ref = db.collection("usuarios").stream()
    negocios_dict = {}
    datos_monitor = []

    for n in negocios_ref:
        data = n.to_dict()
        id_n = data.get('id_negocio', 'sin_id')
        nombre = data.get('nombre_negocio', data.get('nombre_real', 'Sin Nombre'))
        
        # Guardamos para el selector de siempre
        negocios_dict[id_n] = {"nombre": nombre, "doc_id": n.id, "datos": data}
        
        # Guardamos para la nueva tabla de control de pagos
        datos_monitor.append({
            "Negocio": nombre,
            "ID": id_n,
            "Teléfono": data.get("telefono", "S/D"),
            "Promesa Pago": data.get("fecha_promesa_pago", "S/D"),
            "Estado": "✅ ACTIVO" if data.get("rol") == "negocio" else "⚠️ REVISAR"
        })

    # 2. --- NUEVO SUBMÓDULO: CONTROL DE NEGOCIOS DADOS DE ALTA ---
    with st.expander("📊 MONITOR DE COBROS Y NEGOCIOS ACTIVOS", expanded=False):
        if datos_monitor:
            df = pd.DataFrame(datos_monitor)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption("Usa esta tabla para controlar quién tiene pendiente el pago según la fecha promesa.")
        else:
            st.warning("No hay negocios para mostrar.")

    st.divider()

    # 3. --- SELECTOR DE NEGOCIO (EL QUE YA TENÍAS) ---
    if not negocios_dict:
        st.warning("No hay negocios registrados.")
        return

    id_sel = st.selectbox("Seleccioná el negocio para MODIFICAR:", 
                          options=list(negocios_dict.keys()), 
                          format_func=lambda x: f"{x.upper()} - {negocios_dict[x]['nombre']}")

    if id_sel:
        info_actual = negocios_dict[id_sel]['datos']
        doc_id_firebase = negocios_dict[id_sel]['doc_id']

        # Agregamos la pestaña 'Empleados' al final de tus 3 originales
        tab1, tab2, tab3, tab4 = st.tabs(["⚙️ Datos del Negocio", "📦 Stock/Precios", "👥 Clientes", "👤 Empleados"])

        # --- TAB 1: DATOS DEL NEGOCIO (TU CÓDIGO ORIGINAL) ---
        with tab1:
            st.subheader(f"Editar Perfil de {id_sel}")
            with st.form(f"form_edicion_{id_sel}"):
                c1, c2 = st.columns(2)
                with c1:
                    new_n_local = st.text_input("Nombre del Negocio", value=info_actual.get("nombre_negocio", ""))
                    new_dir = st.text_input("Dirección", value=info_actual.get("direccion", ""))
                    new_loc = st.text_input("Localidad", value=info_actual.get("localidad", ""))
                with c2:
                    new_tel = st.text_input("Teléfono Dueño", value=info_actual.get("telefono", ""))
                    new_pago = st.text_input("Fecha Promesa Pago", value=info_actual.get("fecha_promesa_pago", ""))
                    new_rol = st.selectbox("Rol del Usuario", ["negocio", "super_admin", "empleado"], 
                                           index=["negocio", "super_admin", "empleado"].index(info_actual.get("rol", "negocio")))
                
                if st.form_submit_button("💾 APLICAR CAMBIOS GLOBALES"):
                    db.collection("usuarios").document(doc_id_firebase).update({
                        "nombre_negocio": new_n_local,
                        "direccion": new_dir,
                        "localidad": new_loc,
                        "telefono": new_tel,
                        "fecha_promesa_pago": new_pago,
                        "rol": new_rol
                    })
                    st.success("¡Datos del negocio actualizados!")
                    st.rerun()

        # --- TAB 2: STOCK (TU CÓDIGO ORIGINAL) ---
        with tab2:
            st.write("Aquí podés corregir el inventario de este local.")
            prods = db.collection("productos").where("id_negocio", "==", id_sel).stream()
            for p in prods:
                p_data = p.to_dict()
                with st.expander(f"Producto: {p_data.get('nombre')}"):
                    new_stk = st.number_input("Stock", value=float(p_data.get("stock", 0)), key=f"stk_{p.id}")
                    if st.button("Actualizar Stock", key=f"btn_stk_{p.id}"):
                        db.collection("productos").document(p.id).update({"stock": new_stk})
                        st.success("Stock corregido.")

        # --- TAB 3: CLIENTES (TU CÓDIGO ORIGINAL) ---
        with tab3:
            st.write("Edición de deudas y nombres de clientes.")
            clientes = db.collection("clientes").where("id_negocio", "==", id_sel).stream()
            for c in clientes:
                c_data = c.to_dict()
                with st.expander(f"Cliente: {c_data.get('nombre')}"):
                    new_deuda = st.number_input("Deuda ($)", value=float(c_data.get("deuda", 0)), key=f"deu_{c.id}")
                    if st.button("Corregir Deuda", key=f"btn_deu_{c.id}"):
                        db.collection("clientes").document(c.id).update({"deuda": new_deuda})
                        st.success("Deuda actualizada.")

        # --- TAB 4: EMPLEADOS (LO NUEVO) ---
        with tab4:
            st.subheader(f"👥 Gestión de Personal - {id_sel}")
            
            # Formulario rápido para alta
            with st.expander("➕ Dar de alta nuevo empleado para este negocio"):
                with st.form("alta_empleado"):
                    e_nom = st.text_input("Nombre Completo")
                    e_dni = st.text_input("DNI")
                    e_puesto = st.selectbox("Puesto", ["Cajero", "Vendedor", "Repositor", "Encargado"])
                    if st.form_submit_button("Guardar Empleado"):
                        if e_nom:
                            db.collection("empleados").add({
                                "nombre": e_nom,
                                "dni": e_dni,
                                "puesto": e_puesto,
                                "id_negocio": id_sel,
                                "fecha_alta": datetime.now().strftime("%d/%m/%Y")
                            })
                            st.success("Empleado registrado.")
                            st.rerun()

            # Listado de empleados
            st.write("---")
            lista_emp = db.collection("empleados").where("id_negocio", "==", id_sel).stream()
            for emp in lista_emp:
                ed = emp.to_dict()
                col_e, col_b = st.columns([3, 1])
                col_e.write(f"**{ed.get('nombre')}** ({ed.get('puesto')}) - DNI: {ed.get('dni')}")
                if col_b.button("🗑️", key=f"del_{emp.id}"):
                    db.collection("empleados").document(emp.id).delete()
                    st.success("Eliminado")
                    st.rerun()
