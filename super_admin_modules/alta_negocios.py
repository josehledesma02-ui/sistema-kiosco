import streamlit as st

def mostrar(db, ahora):
    st.header("🆕 Registrar Nuevo Negocio")
    st.info("Desde aquí das de alta un nuevo local y su cuenta de dueño.")

    with st.form("form_alta_completo", clear_on_submit=True):
        # --- SECCIÓN 1: DATOS DEL LOCAL ---
        st.subheader("🏢 Información del Comercio")
        c1, c2 = st.columns(2)
        with c1:
            nombre_local = st.text_input("Nombre del Negocio", placeholder="Ej: Despensa La Nueva")
            id_negocio = st.text_input("ID de Acceso (Único y sin espacios)", placeholder="ej: lanueva").lower().strip()
            rubro = st.selectbox("Rubro", ["Kiosco", "Almacén", "Despensa", "Carnicería", "Verdulería", "Pollería", "Otro"])
        with c2:
            localidad = st.text_input("Localidad", placeholder="Ej: San Miguel de Tucumán")
            direccion = st.text_input("Dirección del Local", placeholder="Ej: Av. Alem 1234")

        st.divider()

        # --- SECCIÓN 2: DATOS DEL DUEÑO ---
        st.subheader("👤 Datos del Dueño / Encargado")
        c3, c4 = st.columns(2)
        with c3:
            nombre_dueno = st.text_input("Nombre y Apellido")
            usuario_acceso = st.text_input("Nombre de Usuario (Login)", placeholder="Ej: juan_perez")
            dni_clave = st.text_input("DNI (Será su contraseña)")
        with c4:
            telefono = st.text_input("Teléfono / WhatsApp")
            # Agregamos la fecha de promesa de pago
            fecha_promesa = st.date_input("Fecha Promesa de Pago Suscripción")
            monto_acordado = st.number_input("Monto de Suscripción Acordado ($)", min_value=0, step=500)

        st.divider()
        
        btn_crear = st.form_submit_button("✅ DAR DE ALTA NEGOCIO")

        if btn_crear:
            # Validaciones básicas
            if not id_negocio or not usuario_acceso or not dni_clave:
                st.error("⚠️ El ID, Usuario y DNI son obligatorios para que el cliente pueda entrar.")
            else:
                # Verificar si el ID ya existe
                check = db.collection("usuarios").where("id_negocio", "==", id_negocio).limit(1).get()
                
                if len(check) > 0:
                    st.warning(f"El ID '{id_negocio}' ya existe. Por favor, usá otro diferente.")
                else:
                    # Preparar el documento
                    data_nuevo = {
                        "id_negocio": id_negocio,
                        "nombre_negocio": nombre_local,
                        "rubro": rubro,
                        "localidad": localidad,
                        "direccion": direccion,
                        "nombre_real": nombre_dueno,
                        "usuario": usuario_acceso,
                        "clave": dni_clave,
                        "telefono": telefono,
                        "rol": "negocio",
                        "fecha_alta": ahora,
                        "fecha_promesa_pago": str(fecha_promesa),
                        "monto_suscripcion": monto_acordado,
                        "estado": "activo"
                    }
                    
                    # Guardar en Firebase
                    db.collection("usuarios").add(data_nuevo)
                    
                    st.success(f"¡El negocio '{nombre_local}' ha sido activado!")
                    st.balloons()
                    
                    # Mostrar resumen para pasarle al cliente
                    st.info(f"**Datos para el cliente:**\n\n* **ID Negocio:** {id_negocio}\n* **Usuario:** {usuario_acceso}\n* **Clave:** {dni_clave}")
