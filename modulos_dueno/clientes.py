import streamlit as st
from datetime import datetime

def renderizar(db, id_negocio):
    # --- ESTILOS VISUALES (MANTENEMOS TODO IGUAL) ---
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
                border: 1px solid #FFCDD2;
            }
            .fecha-pago {
                color: #1E88E5;
                font-weight: bold;
            }
            .ticket-info {
                font-size: 14px;
                background-color: #f1f3f4;
                padding: 8px;
                border-radius: 5px;
                margin-bottom: 5px;
                border-left: 3px solid #1E88E5;
            }
        </style>
    """, unsafe_allow_html=True)

    st.header("👥 Gestión de Clientes y Cuentas")

    tab_lista, tab_nuevo = st.tabs(["📋 Lista de Clientes", "➕ Agregar Nuevo"])

    # --- PESTAÑA 1: LISTA, DETALLE E HISTORIAL ---
    with tab_lista:
        st.markdown('<div class="sub-blue">Clientes de tu Negocio</div>', unsafe_allow_html=True)
        
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
                    with st.expander(f"👤 {cli['nombre']} (DNI: {cli.get('dni', 'S/D')})"):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"📞 **WhatsApp:** {cli.get('telefono', 'No asignado')}")
                            f_pago = cli.get('fecha_pago', 'No pactada')
                            st.markdown(f"📅 **Promesa de Pago:** <span class='fecha-pago'>{f_pago}</span>", unsafe_allow_html=True)
                            st.write(f"📝 **Nota:** {cli.get('nota', '-')}")
                        
                        with c2:
                            # --- BUSCAR TODAS LAS VENTAS AL FIADO DE ESTE CLIENTE ---
                            ventas_query = db.collection("ventas_procesadas")\
                                .where("id_negocio", "==", id_negocio)\
                                .where("cliente_nombre", "==", cli['nombre'])\
                                .where("metodo", "==", "Fiado").stream()
                            
                            historial_ventas = []
                            total_deuda = 0
                            for v in ventas_query:
                                v_data = v.to_dict()
                                historial_ventas.append(v_data)
                                total_deuda += v_data.get('total', 0)

                            total_f = f"${total_deuda:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
                            st.markdown("💰 **Deuda Actual:**")
                            st.markdown(f"<div class='deuda-total'>{total_f}</div>", unsafe_allow_html=True)

                        # --- NUEVA SECCIÓN: DETALLE DE COMPRAS ---
                        st.markdown("#### 📜 Detalle de Compras (Fiado)")
                        if historial_ventas:
                            # Ordenamos las ventas por fecha (la más nueva arriba)
                            historial_ventas = sorted(historial_ventas, key=lambda x: x.get('fecha', ''), reverse=True)
                            
                            for venta in historial_ventas:
                                try:
                                    # Formatear la fecha para que se entienda bien
                                    fecha_dt = datetime.fromisoformat(venta['fecha'])
                                    fecha_f = fecha_dt.strftime("%d/%m/%Y - %H:%M")
                                except:
                                    fecha_f = venta.get('fecha', 'S/F')

                                v_total_f = f"${venta['total']:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
                                
                                with st.container():
                                    st.markdown(f"<div class='ticket-info'>📅 <b>{fecha_f}</b> | Total: <b>{v_total_f}</b></div>", unsafe_allow_html=True)
                                    # Listar los productos de esta venta
                                    items = venta.get('items', [])
                                    for item in items:
                                        st.write(f"▪️ {item['cantidad']}x {item['nombre']} (${item['precio']:,.2f})")
                        else:
                            st.write("No hay ventas registradas al fiado para este cliente.")

                        st.divider()

                        # --- SECCIÓN DE EDICIÓN (MANTENIDA) ---
                        if st.checkbox("📝 Editar WhatsApp, Fecha o Nota", key=f"edit_mode_{cli['id_doc']}"):
                            nuevo_tel = st.text_input("Nuevo WhatsApp:", value=cli.get('telefono', ''), key=f"t_{cli['id_doc']}")
                            try:
                                fecha_val = datetime.strptime(cli.get('fecha_pago', ''), "%d/%m/%Y")
                            except:
                                fecha_val = datetime.now()
                            nueva_fecha = st.date_input("Nueva Fecha de Pago:", value=fecha_val, key=f"f_{cli['id_doc']}")
                            nueva_nota = st.text_area("Nueva Nota:", value=cli.get('nota', ''), key=f"n_{cli['id_doc']}")
                            
                            if st.button("💾 Actualizar Datos", key=f"btn_upd_{cli['id_doc']}", use_container_width=True):
                                f_str = nueva_fecha.strftime("%d/%m/%Y")
                                db.collection("clientes").document(cli['id_doc']).update({
                                    "telefono": nuevo_tel,
                                    "fecha_pago": f_str,
                                    "nota": nueva_nota
                                })
                                st.success("Datos actualizados.")
                                st.rerun()

                        # --- BOTÓN ELIMINAR (MANTENIDO) ---
                        if st.button("🗑️ Eliminar Cliente", key=f"del_cli_{cli['id_doc']}"):
                            db.collection("clientes").document(cli['id_doc']).delete()
                            st.success(f"Cliente eliminado.")
                            st.rerun()
            else:
                st.info("No hay clientes registrados.")
        except Exception as e:
            st.error(f"Error al cargar: {e}")

    # --- PESTAÑA 2: AGREGAR CLIENTE (INTACTA) ---
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
            btn_guardar = st.form_submit_button("💾 GUARDAR Y CREAR ACCESO", use_container_width=True)
            if btn_guardar:
                if not nombre_nuevo or not dni_nuevo:
                    st.warning("⚠️ Nombre y DNI son obligatorios.")
                else:
                    try:
                        f_pago_str = fecha_pago.strftime("%d/%m/%Y") if fecha_pago else "No definida"
                        db.collection("clientes").add({
                            "id_negocio": id_negocio,
                            "nombre": nombre_nuevo,
                            "dni": dni_nuevo,
                            "telefono": tel_nuevo,
                            "fecha_pago": f_pago_str,
                            "nota": nota_nueva,
                            "fecha_alta": datetime.now().isoformat()
                        })
                        db.collection("usuarios").add({
                            "id_negocio": id_negocio,
                            "nombre_real": nombre_nuevo,
                            "usuario": nombre_nuevo, 
                            "clave": dni_nuevo,
                            "rol": "cliente",
                            "fecha_creacion": datetime.now().isoformat()
                        })
                        st.success(f"✅ ¡Registrado!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
