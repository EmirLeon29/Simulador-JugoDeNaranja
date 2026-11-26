import streamlit as st

# Configuración global de toda la aplicación (solo debe estar en este archivo)
st.set_page_config(
    page_title="Simulador Planta de Jugo de Naranja",
    page_icon="🍊",
    layout="wide",
)

st.title("🍊 Simulador Virtual: Planta Procesadora de Jugo de Naranja")
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
        "Descarte de fruta dañada, higienización superficial y exprimido mecánico para "
        "obtener jugo bruto y subproductos (piel,semillas y aceites)."
    )

with col2:
    st.info(
        "**2. Tamizado y Enfriamiento**\n\n"
        "Filtración para estandarizar el contenido de pulpa (del 12 % al 8 %) y descenso "
        "térmico rápido para frenar la degradación enzimática."
    )

with col3:
    st.info(
        "**3. Tanques Asépticos**\n\n"
        "Almacenamiento intermedio estéril bajo atmósfera controlada para estabilizar el "
        "flujo continuo y evitar la recontaminación microbiológica."
    )
    
col4, col5, col6 = st.columns(3)

with col4:
    st.info(
        "**4. Homogenización**\n\n"
        "Reducción mecánica de partículas a alta presión para dar uniformidad física al jugo "
        "y evitar la separación de fases."
    )

with col5:
    st.info(
        "**5. Desaireación**\n\n"
        "Extracción de oxígeno disuelto al vacío para prevenir la oxidación de la vitamina C, "
        "evitar formación de espuma y conservar el aroma."
    )

with col6:
    st.info(
        "**6. Pasteurización**\n\n"
        "Tratamiento térmico controlado (HTST) e intercambio de calor para inactivar "
        "microorganismos patógenos y enzimas."
    )

colx, col7, col8, coly = st.columns(4)

with col7:
    st.info(
        "**7. Envasado Aséptico**\n\n"
        "Llenado y sellado hermético en ambiente comercialmente estéril sobre botellas "
        "PET (1 L), contabilizando mermas de línea."
    )

with col8:
    st.info(
        "**8. Etiquetado**\n\n"
        "Identificación comercial de unidades, codificación de lote y caducidad, agrupación "
        "en packs y paletización para despacho."
    )

st.markdown("---")
st.subheader("Parámetros Base de Diseño (Línea Base del Equipo)")

datos_base = [
    {"Parámetro": "Producción anual de jugo comercial", "Valor": "1,500,000", "Unidad": "L/año"},
    {"Parámetro": "Campaña de extracción", "Valor": "87", "Unidad": "días/año (8 h/día)"},
    {"Parámetro": "Campaña de envasado", "Valor": "100", "Unidad": "días/año (8 h/día)"},
    {"Parámetro": "Densidad del jugo comercial", "Valor": "1.045", "Unidad": "kg/L"},
    {"Parámetro": "Rendimiento global extracción", "Valor": "50.0", "Unidad": "%"},
]
st.dataframe(datos_base, use_container_width=True, hide_index=True)
