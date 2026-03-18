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
                padding: 20px;
                border-radius: 12px;
                border-left: 6px solid #1E88E5;
                box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
                margin-bottom: 15px;
            }
            .deuda-total {
                font-size: 24px;
                font-weight: bold;
                color: #D32F2F;
            }
        </style>
    """, unsafe_allow_html=True)

    st.header("👥 Gestión de Clientes y Cuentas")

    tab_lista, tab_nuevo = st.tabs(["📋 Lista de Clientes", "➕ Agregar Nuevo"])

    # --- PESTAÑA 1: LISTA Y DETALLE DE CUENTA CORRIENTE ---
    with tab_lista:
        st.markdown('<div class="sub-blue">Clientes Registrados</div>', unsafe_allow_html=True)
        
        try:
            clientes_ref = db.collection("clientes").where("id_negocio", "==", id_negocio).stream()
            lista_clientes = []
            for doc in clientes_ref:
                datos = doc.to_dict()
                datos["id_doc"] = doc.id
                lista_clientes.append(datos)

            if lista_clientes:
                lista_clientes = sorted(lista_clientes, key=lambda x: x.get('nombre', '').lower())
                
                for cli in lista_clientes:
                    # Usamos un expander para que no ocupe espacio y solo se vea el detalle al clickear
                    with st.expander(f"👤 {cli['nombre']} - Ver Detalle"):
                        st.markdown(f"### Detalle de: {cli['nombre']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"🆔 **DNI (Contraseña):** {cli.get('dni', 'No cargado')}")
                            st.write(f"📞 **WhatsApp:** {cli.get('telefono', 'Sin asignar')}")
                        with col2:
                            # Aquí consultamos la deuda en tiempo real (Sumamos las ventas con método "Fiado" de este cliente)
                            ventas_fiado = db.collection("ventas_procesadas")\
                                .where("id_negocio", "==", id_negocio)\
                                .where("cliente_nombre", "==", cli['nombre'])\
                                .where("metodo", "==", "Fiado").stream()
                            
                            total_deuda = sum(v.to_dict().get('total', 0) for v in ventas_fiado)
                            total_f = f"${total_deuda:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
                            
                            st.markdown(f"💰 **Deuda Total:**")
                            st.markdown(f"<p class='deuda-total'>{total_f}</p>", unsafe_allow_html=True)

                        st.info(f"📝 **Referencia:** {cli.get('nota', 'Sin notas adicionales')}")
                        
                        # Botón para borrar cliente (Solo si no tiene deuda, o advertir)
                        if st.button("🗑️ Eliminar Cliente", key=f"del_cli_{cli['id_doc']}"):
                            db.collection("clientes").document(cli['id_doc']).delete()
                            # También podrías borrar su usuario de la tabla usuarios si lo deseas
                            st.success(f"Cliente '{cli['nombre']}' eliminado del sistema.")
                            st.rerun()
            else:
                st.info("No hay clientes registrados.")
        except Exception as e:
            st.error(f"Error: {e}")

    # --- PESTAÑA 2: AGREGAR CLIENTE Y CREAR USUARIO AUTOMÁTICO ---
    with tab_nuevo:
        st.markdown('<div class="sub-blue">Registrar Nuevo Cliente y Crear Acceso</div>', unsafe_allow_html=True)
        
        with st.form("form_alta_cliente", clear_on_submit=True):
            nombre_nuevo = st.text_input("Nombre y Apellido (Será su Usuario):").strip()
            dni_nuevo = st.text_input("DNI (Será su Contraseña):").strip()
            tel_nuevo = st.text_input("WhatsApp / Teléfono:")
            nota_nueva = st.text_area("Notas o referencias:")
            
            st.caption("⚠️ Al guardar, el cliente podrá entrar con su Nombre y DNI a ver su cuenta.")
            btn_guardar = st.form_submit_button("💾 GUARDAR Y CREAR USUARIO", use_container_width=True)
            
            if btn_guardar:
                if not nombre_nuevo or not dni_nuevo:
                    st.warning("⚠️ El Nombre y el DNI son obligatorios para crear el acceso.")
                else:
                    try:
                        # 1. Creamos el perfil del Cliente
                        nuevo_cliente = {
                            "id_negocio": id_negocio,
                            "nombre": nombre_nuevo,
                            "dni": dni_nuevo,
                            "telefono": tel_nuevo,
                            "nota": nota_nueva,
                            "fecha_alta": datetime.now().isoformat()
                        }
                        db.collection("clientes").add(nuevo_cliente)
                        
                        # 2. Creamos el Usuario para que pueda iniciar sesión
                        # Importante: El 'rol' debe ser 'cliente'
                        nuevo_usuario = {
                            "id_negocio": id_negocio,
                            "nombre_real": nombre_nuevo,
                            "usuario": nombre_nuevo, 
                            "clave": dni_nuevo,
                            "rol": "cliente",
                            "fecha_creacion": datetime.now().isoformat()
                        }
                        db.collection("usuarios").add(nuevo_usuario)
                        
                        st.success(f"✅ ¡{nombre_nuevo} registrado! Usuario y contraseña creados.")
                    except Exception as e:
                        st.error(f"No se pudo guardar: {e}")
