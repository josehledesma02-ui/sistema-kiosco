import streamlit as st
from datetime import datetime

def renderizar(db, id_negocio):
    # --- MANTENEMOS LA ESTÉTICA AZUL Y DISEÑO LIMPIO ---
    st.markdown("""
        <style>
            .sub-blue {
                background: linear-gradient(90deg, #1E88E5 0%, #64B5F6 100%);
                color: white;
                padding: 10px;
                border-radius: 8px;
                font-size: 20px;
                margin-top: 10px;
                margin-bottom: 15px;
            }
            .cliente-card {
                background-color: #ffffff;
                padding: 15px;
                border-radius: 10px;
                border-left: 5px solid #1E88E5;
                box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
                margin-bottom: 10px;
            }
            /* Estilo para la papelera roja (igual que en ventas) */
            .stButton > button[key^="del_cli_"] {
                border: none !important;
                background: transparent !important;
                color: #FF1744 !important;
                font-size: 22px !important;
                font-weight: bold !important;
                padding: 0 !important;
                margin-top: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

    st.header("👥 Gestión de Clientes")

    # Organizamos en dos pestañas para que sea cómodo
    tab_lista, tab_nuevo = st.tabs(["📋 Lista de Clientes", "➕ Agregar Nuevo"])

    # --- PESTAÑA 1: VER Y ELIMINAR CLIENTES ---
    with tab_lista:
        st.markdown('<div class="sub-blue">Clientes en Base de Datos</div>', unsafe_allow_html=True)
        
        try:
            # Traemos los clientes filtrados por el ID de tu negocio
            clientes_ref = db.collection("clientes").where("id_negocio", "==", id_negocio).stream()
            lista_clientes = []
            for doc in clientes_ref:
                datos = doc.to_dict()
                datos["id_doc"] = doc.id # Guardamos el ID interno de Firebase
                lista_clientes.append(datos)

            if lista_clientes:
                # Ordenar alfabéticamente por nombre
                lista_clientes = sorted(lista_clientes, key=lambda x: x.get('nombre', '').lower())
                
                for cli in lista_clientes:
                    with st.container():
                        # Columnas para Nombre, Teléfono y el botón de borrar
                        c1, c2, c3 = st.columns([3, 2, 0.5])
                        with c1:
                            st.markdown(f"**{cli['nombre']}**")
                            if cli.get('nota'): 
                                st.caption(f"📝 {cli['nota']}")
                        with c2:
                            tel = cli.get('telefono', 'Sin teléfono')
                            st.write(f"📞 {tel if tel else 'Sin teléfono'}")
                        with c3:
                            # La misma papelera roja que usamos en ventas
                            if st.button("🗑️", key=f"del_cli_{cli['id_doc']}"):
                                db.collection("clientes").document(cli['id_doc']).delete()
                                st.success(f"Cliente '{cli['nombre']}' eliminado.")
                                st.rerun()
                        st.divider()
            else:
                st.info("No hay clientes registrados todavía. Podés cargar el primero en la pestaña 'Agregar Nuevo'.")
        
        except Exception as e:
            st.error(f"Error al conectar con la base de datos de clientes: {e}")

    # --- PESTAÑA 2: CARGAR CLIENTE NUEVO ---
    with tab_nuevo:
        st.markdown('<div class="sub-blue">Registrar Nuevo Cliente</div>', unsafe_allow_html=True)
        
        # Usamos un formulario para que se limpie al terminar
        with st.form("form_alta_cliente", clear_on_submit=True):
            nombre_nuevo = st.text_input("Nombre Completo (Obligatorio):").strip()
            tel_nuevo = st.text_input("Teléfono / WhatsApp (Opcional):")
            nota_nueva = st.text_area("Notas o referencias:", placeholder="Ej: Vive al lado de lo de Doña Rosa, pariente de Juan, etc.")
            
            btn_guardar = st.form_submit_button("💾 GUARDAR CLIENTE EN LISTA", use_container_width=True)
            
            if btn_guardar:
                if not nombre_nuevo:
                    st.warning("⚠️ El nombre es necesario para poder elegirlo después en Ventas.")
                elif nombre_nuevo.lower() == "consumidor final":
                    st.error("❌ 'Consumidor Final' ya existe por defecto, elegí otro nombre.")
                else:
                    try:
                        # Estructura del dato para Firebase
                        nuevo_registro = {
                            "id_negocio": id_negocio,
                            "nombre": nombre_nuevo,
                            "telefono": tel_nuevo,
                            "nota": nota_nueva,
                            "fecha_alta": datetime.now().isoformat()
                        }
                        db.collection("clientes").add(nuevo_registro)
                        st.success(f"✅ ¡{nombre_nuevo} se agregó correctamente!")
                        # No hace falta rerun porque el form se limpia solo
                    except Exception as e:
                        st.error(f"No se pudo guardar: {e}")
