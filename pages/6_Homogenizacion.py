"""
Módulo de Homogeneización - Simulador de Zumo de Naranja
Proyecto: Línea de elaboración de zumo de naranja (1.500.000 litros/año)
Ubicación: Palma del Río, Córdoba
"""

import streamlit as st

def mostrar_homogeneizacion():
    st.title("🎛️ Sección: Homogeneización")
    st.markdown("""
    Esta sección calcula los parámetros de diseño y el balance energético de la etapa de **homogeneización** 
    para la línea de producción de zumo de naranja, evitando la separación de fases (sedimentación del suero).
    """)

    st.sidebar.header("Parámetros de Entrada")
    
    # Parámetros editables para la simulación
    produccion_anual = st.sidebar.number_input("Producción anual (L/año)", value=1_500_000.0, step=50_000.0)
    dias_anio = st.sidebar.number_input("Días de operación al año", value=250, step=5)
    horas_dia = st.sidebar.number_input("Horas de operación al día", value=16.0, step=1.0)
    
    st.sidebar.markdown("---")
    presion_bar = st.sidebar.slider("Presión de homogenización (bar)", min_value=100.0, max_value=250.0, value=150.0, step=5.0)
    eficiencia = st.sidebar.slider("Eficiencia mecánica del equipo", min_value=0.70, max_value=0.95, value=0.85, step=0.01)
    
    # Cálculos principales
    horas_totales = dias_anio * horas_dia
    vol_flow_l_h = produccion_anual / horas_totales
    vol_flow_m3_h = vol_flow_l_h / 1000.0
    vol_flow_m3_s = vol_flow_m3_h / 3600.0
    
    densidad_zumo = 1.04  # kg/L
    mass_flow_kg_h = vol_flow_l_h * densidad_zumo
    
    delta_p_pa = presion_bar * 100_000.0  # 1 bar = 10^5 Pa
    power_hydraulic_w = vol_flow_m3_s * delta_p_pa
    power_hydraulic_kw = power_hydraulic_w / 1000.0
    power_electrical_kw = power_hydraulic_kw / eficiencia

    # Visualización en la interfaz web (Streamlit)
    st.subheader("📊 Resultados del Balance y Diseño")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Caudal Volumétrico", f"{vol_flow_l_h:,.2f} L/h")
    with col2:
        st.metric("Caudal Másico", f"{mass_flow_kg_h:,.2f} kg/h")
    with col3:
        st.metric("Presión de Operación", f"{presion_bar:.1f} bar")

    st.markdown("---")
    st.subheader("⚡ Requerimientos Energéticos")
    
    col4, col5 = st.columns(2)
    with col4:
        st.metric("Potencia Hidráulica Efectiva", f"{power_hydraulic_kw:.2f} kW")
    with col5:
        st.metric("Potencia Eléctrica Instalada", f"{power_electrical_kw:.2f} kW", help=f"Considerando una eficiencia de {eficiencia*100}%")

if __name__ == "__main__":
    mostrar_homogeneizacion()