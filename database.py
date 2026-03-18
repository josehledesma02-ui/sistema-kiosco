import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import pytz
from datetime import datetime

def obtener_hora_argentina():
    try:
        zona_ar = pytz.timezone('America/Argentina/Buenos_Aires')
    except:
        zona_ar = pytz.timezone('UTC')
    return datetime.now(zona_ar)

def conectar_firebase():
    # Evita errores si ya está conectado
    if not firebase_admin._apps:
        try:
            if "firebase" in st.secrets:
                creds_dict = dict(st.secrets["firebase"])
                # Arreglo de la clave privada para Streamlit Cloud
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                cred = credentials.Certificate(creds_dict)
            else:
                # Opción para cuando probás en tu PC
                cred = credentials.Certificate("secretos.json")
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"⚠️ Error de conexión a Base de Datos: {e}")
            st.stop()
    return firestore.client()
