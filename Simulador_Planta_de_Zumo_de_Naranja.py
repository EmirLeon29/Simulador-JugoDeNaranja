import streamlit as st

# Configuración global de toda la aplicación (solo debe estar en este archivo)
st.set_page_config(
    page_title="Simulador Planta de Zumo de Naranja",
    page_icon="🍊",
    layout="wide",
)

st.title("🍊 Simulador Virtual: Planta Procesadora de Zumo de Naranja")
st.markdown(
    """
    Bienvenido al entorno de simulación de proceso basado en una capacidad nominal de 
    **1,500,000 L/año** de zumo comercial (8 % de pulpa).
    
    Selecciona una etapa del proceso en el **menú de la barra lateral izquierda** para 
    ejecutar los balances de materia y pruebas de sensibilidad:
    """
)

st.markdown("---")

# Resumen de arquitectura del proceso para todo el equipo
col1, col2, col3 = st.columns(3)

with col1:
    st.info(
        "**1. Selección, Lavado y Extracción**\n\n"
        "Cálculo retrógrado desde zumo bruto hasta recepción de fruta, destríos, "
        "piel/semillas y emulsión oleosa."
    )

with col2:
    st.info(
        "**2. Tamizado y Pasteurización**\n\n"
        "Ajuste de contenido de pulpa (12 % a 8 %), tratamiento térmico y balances "
        "de energía."
    )

with col3:
    st.info(
        "**3. Envasado Aséptico y Fin de Línea**\n\n"
        "Discretización de botellas PET (1 L), mermas de línea, formación de packs "
        "y paletización."
    )

st.markdown("---")
st.subheader("Parámetros Base de Diseño (Línea Base del Equipo)")

datos_base = [
    {"Parámetro": "Producción anual de zumo comercial", "Valor": "1,500,000", "Unidad": "L/año"},
    {"Parámetro": "Campaña de extracción", "Valor": "87", "Unidad": "días/año (8 h/día)"},
    {"Parámetro": "Campaña de envasado", "Valor": "100", "Unidad": "días/año (8 h/día)"},
    {"Parámetro": "Densidad del zumo comercial", "Valor": "1.045", "Unidad": "kg/L"},
    {"Parámetro": "Rendimiento global extracción", "Valor": "50.0", "Unidad": "%"},
]
st.dataframe(datos_base, use_container_width=True, hide_index=True)
