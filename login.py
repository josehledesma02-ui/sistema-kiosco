import streamlit as st

def mostrar_login(db):
    st.markdown("<h1 style='text-align: center;'>🔐 Ingreso JL Gestión</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("formulario_login"):
            neg_id = st.text_input("ID Negocio").strip().lower()
            user_nm = st.text_input("Usuario")
            pass_wd = st.text_input("Contraseña", type="password")
            boton = st.form_submit_button("INGRESAR", use_container_width=True)
            
            if boton:
                # Buscamos al usuario en Firebase
                u_ref = db.collection("usuarios").where("id_negocio", "==", neg_id).where("nombre", "==", user_nm).limit(1).get()
                
                if u_ref and str(u_ref[0].to_dict().get('password')) == pass_wd:
                    d = u_ref[0].to_dict()
                    # Guardamos todo en la sesión
                    st.session_state.update({
                        'autenticado': True, 
                        'usuario_id': u_ref[0].id,
                        'rol': d.get('rol').lower(), 
                        'nombre_real': d.get('nombre'),
                        'id_negocio': d.get('id_negocio'),
                        'promesa_pago': d.get('promesa_pago', 'N/A')
                    })
                    st.rerun()
                else:
                    st.error("⚠️ Datos incorrectos.")
