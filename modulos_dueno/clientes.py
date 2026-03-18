import streamlit as st
from datetime import datetime

def renderizar(db, id_negocio):
    # --- ESTILOS VISUALES (INTACTOS) ---
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
            .deuda-total {
                font-size: 26px;
                font-weight: bold;
                color: #D32F2F;
                background-color: #FFEBEE;
                padding: 10px;
                border-radius: 8px;
                text-align: center;
            }
            .fecha-pago {
                color: #1E88E5;
                font-weight: bold;
            }
        </style>
    """, unsafe_allow_html=True)

    st.header("👥 Gestión de Clientes y Cuentas")

    tab_lista, tab_nuevo = st.tabs(["📋 Lista de Clientes", "➕ Agregar Nuevo"])

    # --- PESTAÑA 1: LISTA (CORREGIDA PARA QUE MUESTRE TODO) ---
    with tab_lista:
        st.markdown('<div class="sub-blue">Clientes de tu Negocio</div>', unsafe_allow_html=True)
        
        try:
            # Traemos los clientes filtrados por tu negocio
            # Usamos un stream directo para asegurar que lea lo último
            clientes_ref = db.collection("clientes").where("id_negocio", "==", id_negocio).stream()
            
            lista_clientes = []
            for doc in clientes_ref:
                datos = doc.to_dict()
                datos["id_doc"] = doc.id
                lista_clientes.append(datos)

            if lista_clientes:
                # Ordenar por nombre para que sea fácil encontrarlos
                lista_clientes = sorted(lista_clientes, key=lambda x: x.get('nombre', '').lower())
                
                for cli in lista_clientes:
                    # El nombre y DNI se ven primero
                    with st.expander(f"👤 {cli['nombre']} (DNI: {cli.get('dni', 'S/D')})"):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"📞 **WhatsApp:** {cli.get('telefono', 'No asignado')}")
                            f_pago = cli.get('fecha_pago', 'No pactada')
                            st.markdown(f"📅 **Promesa de Pago:** <span class='fecha-pago'>{f_pago}</span>", unsafe_allow_html=True)
                            st.write(f"📝 **Nota:** {cli.get('nota', '-')}")
                        
                        with c2:
                            # Cálculo de deuda filtrado por cliente y negocio
                            ventas_fiado = db.collection("ventas_procesadas")\
                                .where("id_negocio", "==", id_negocio)\
                                .where("cliente_nombre", "==", cli['nombre'])\
                                .where("metodo", "==", "Fiado").stream()
                            
                            total_deuda = sum(v.to_dict().get('total', 0) for v in ventas_fiado)
                            total_f = f"${total_deuda:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
                            
                            st.markdown("💰 **Deuda Actual:**")
                            st.markdown(f"<div class='deuda-total'>{total_f}</div>", unsafe_allow_html=True)

                        # Botón para eliminar cliente
                        if st.button("🗑️ Eliminar Cliente", key=f"del_cli_{cli['id_doc']}"):
                            db.collection("clientes").document(cli['id_doc']).delete()
                            st.success(f"Cliente '{cli['nombre']}' eliminado.")
                            st.rerun()
            else:
                st.info("Aún no hay clientes registrados. Podés cargar uno en la pestaña 'Agregar Nuevo'.")
                
        except Exception as e:
            st.error(f"Error al cargar la lista: {e}")

    # --- PESTAÑA 2: AGREGAR CLIENTE (SIN CAMBIOS) ---
    with tab_nuevo:
        st.markdown('<div class="sub-blue">Registrar Nuevo Cliente y Usuario</div>', unsafe_allow_html=True)
        
        with st.form("form_alta_cliente", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                nombre_nuevo = st.text_input("Nombre y Apellido (Usuario):").strip()
                dni_nuevo = st.text_input("DNI (Contraseña):").strip()
            with col_b:
                tel_nuevo = st.text_input("WhatsApp / Teléfono:")
                fecha_pago = st.date_input("Fecha prometida de pago:", value=None)
            
            nota_nueva = st.text_area("Notas o referencias adicionales:")
            
            st.info("💡 Automáticamente se le asignará el Rol de 'Cliente' y se vinculará a tu negocio.")
            btn_guardar = st.form_submit_button("💾 GUARDAR Y CREAR ACCESO", use_container_width=True)
            
            if btn_guardar:
                if not nombre_nuevo or not dni_nuevo:
                    st.warning("⚠️ Nombre y DNI son obligatorios.")
                else:
                    try:
                        f_pago_str = fecha_pago.strftime("%d/%m/%Y") if fecha_pago else "No definida"
                        
                        # Guardar Cliente
                        db.collection("clientes").add({
                            "id_negocio": id_negocio,
                            "nombre": nombre_nuevo,
                            "dni": dni_nuevo,
                            "telefono": tel_nuevo,
                            "fecha_pago": f_pago_str,
                            "nota": nota_nueva,
                            "fecha_alta": datetime.now().isoformat()
                        })
                        
                        # Guardar Usuario (Rol automático)
                        db.collection("usuarios").add({
                            "id_negocio": id_negocio,
                            "nombre_real": nombre_nuevo,
                            "usuario": nombre_nuevo, 
                            "clave": dni_nuevo,
                            "rol": "cliente",
                            "fecha_creacion": datetime.now().isoformat()
                        })
                        
                        st.success(f"✅ ¡{nombre_nuevo} registrado! Ya puede entrar con su DNI.")
                        # Rerun para que aparezca en la lista inmediatamente
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
