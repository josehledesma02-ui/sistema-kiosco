import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import os

# ==========================================
# 0. CONFIGURACIÓN INICIAL
# ==========================================
st.set_page_config(page_title="JL Gestión Pro", page_icon="🛍️", layout="wide")

IMG_LOGIN = "logo.png" 
IMG_SIDEBAR = "logo_chico.png"
URL_PROVEEDOR_CSV = "https://docs.google.com/spreadsheets/d/1-ay_xIqYItwOaXe80VUsEmh4gsANrk9PH72aZcUD54g/export?format=csv"

# ==========================================
# 1. CONEXIÓN A FIREBASE (Singleton)
# ==========================================
if not firebase_admin._apps:
    try:
        if "firebase" in st.secrets:
            creds_dict = dict(st.secrets["firebase"])
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(creds_dict)
        else:
            cred = credentials.Certificate("secretos.json")
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"⚠️ Error de conexión: {e}")
        st.stop()

db = firestore.client()

# ==========================================
# 2. GESTIÓN DE ESTADO Y FUNCIONES
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.update({
        'autenticado': False, 'usuario': None, 'rol': None, 
        'id_negocio': None, 'nombre_real': None, 'carrito': [], 
        'ultimo_ticket': None, 'df_proveedor': None
    })

def cargar_datos_proveedor():
    try:
        # Importante: Usar el link de exportación CSV para Sheets
        df = pd.read_csv(URL_PROVEEDOR_CSV)
        # Limpieza de precios si vienen como texto ($1.
