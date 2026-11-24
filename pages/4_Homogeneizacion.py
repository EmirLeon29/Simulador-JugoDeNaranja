"""
Módulo de Homogeneización - Planta virtual de zumo de naranja
=============================================================
Proyecto: Línea de elaboración de zumo de naranja (Palma del Río, Córdoba)

Posición en el diagrama de flujo:
    ... Tamizado -> Enfriamiento -> Tanques asépticos -> HOMOGENEIZACIÓN
        -> Desaireación -> Pasteurización -> Envasado aséptico

Modelo (estado estacionario, fluido incompresible, sin pérdidas de calor):
    1. Balance de masa:         m_out = m_in
    2. Caudal volumétrico:      Q = m / rho
    3. Potencia hidráulica:     P_hid = Q * P1          (P1 = presión de 1.ª etapa)
    4. Potencia eléctrica:      P_el = P_hid / (eta_bomba * eta_motor)
    5. Aumento de temperatura:  dT = P1 / (rho * cp)    (disipación total: cota superior)
    6. Balance de energía:      m * cp * dT = Q * P1    (cierra con P_hid)
    7. Velocidad en la válvula: v = Cd * sqrt(2 * dP / rho)   (Bernoulli)
    8. Altura de la rendija:    h = Q / (v * pi * D_asiento)

Nota para la integración: NO usa st.set_page_config() (solo va en la
página principal del hub). Guardar en la carpeta pages/ del repositorio.
"""

import math
import os

import matplotlib.pyplot as plt

try:
    import streamlit as st
except ImportError:  # permite probar el modelo sin Streamlit instalado
    st = None

# --- Valores de la etapa anterior (Tamizado y Enfriamiento) -------------------
CP_JUGO = 3.93            # kJ/(kg·°C), mismo valor que el módulo de enfriamiento
RHO_JUGO = 1040.0         # kg/m³ (zumo de naranja ~10-12 °Brix)
M_IN_CASO_BASE = 520.84   # kg/h de jugo refinado del caso base (580 · (1 - 0.12·0.85))
T_IN_CASO_BASE = 5.0      # °C a la salida del enfriador


# ==============================================================================
# MODELO (funciones puras: no dependen de Streamlit)
# ==============================================================================
def calcular_homogeneizacion(
    m_in_kg_h=M_IN_CASO_BASE,
    T_in_C=T_IN_CASO_BASE,
    P1_bar=150.0,
    frac_P2=0.10,
    rho_kg_m3=RHO_JUGO,
    cp_kJ_kgC=CP_JUGO,
    eta_bomba=0.85,
    eta_motor=0.92,
    factor_diseno=1.20,
    cd=0.70,
    d_asiento_mm=10.0,
    horas_anuales=4000.0,
):
    """Balance de materia, energía e hidráulica de un homogeneizador de dos etapas."""
    if m_in_kg_h <= 0 or rho_kg_m3 <= 0 or cp_kJ_kgC <= 0:
        raise ValueError("Flujo, densidad y Cp deben ser positivos.")
    if P1_bar <= 0:
        raise ValueError("La presión debe ser positiva.")
    if not 0 <= frac_P2 < 1:
        raise ValueError("La fracción de presión de la 2.ª etapa debe estar en [0, 1).")
    for eta in (eta_bomba, eta_motor):
        if not 0 < eta <= 1:
            raise ValueError("Las eficiencias deben estar en (0, 1].")
    if cd <= 0 or d_asiento_mm <= 0 or horas_anuales <= 0:
        raise ValueError("Cd, diámetro de asiento y horas anuales deben ser positivos.")

    # Presiones (1 bar = 1e5 Pa)
    P1 = P1_bar * 1e5
    P2 = frac_P2 * P1
    dp_etapa1 = P1 - P2   # caída de presión en la válvula de 1.ª etapa
    dp_etapa2 = P2        # caída de presión en la válvula de 2.ª etapa

    # 1-2. Balance de masa y caudal
    m_out = m_in_kg_h
    Q_m3_s = m_in_kg_h / 3600.0 / rho_kg_m3
    Q_L_h = m_in_kg_h / rho_kg_m3 * 1000.0

    # 3-4. Potencias
    P_hid_kW = Q_m3_s * P1 / 1000.0
    P_eje_kW = P_hid_kW / eta_bomba
    P_el_kW = P_eje_kW / eta_motor
    P_instalada_kW = P_el_kW * factor_diseno

    # 5-6. Balance de energía: toda la potencia hidráulica se disipa en las válvulas
    dT = P1 / (rho_kg_m3 * cp_kJ_kgC * 1000.0)
    T_out = T_in_C + dT
    Q_disipado_kW = m_in_kg_h / 3600.0 * cp_kJ_kgC * dT

    # 7-8. Hidráulica de las válvulas (valores indicativos de diseño)
    perimetro = math.pi * d_asiento_mm / 1000.0
    v1 = cd * math.sqrt(2.0 * dp_etapa1 / rho_kg_m3)
    h1_um = Q_m3_s / (v1 * perimetro) * 1e6
    if dp_etapa2 > 0:
        v2 = cd * math.sqrt(2.0 * dp_etapa2 / rho_kg_m3)
        h2_um = Q_m3_s / (v2 * perimetro) * 1e6
    else:
        v2, h2_um = None, None

    # Indicadores anuales
    energia_kWh_anio = P_el_kW * horas_anuales
    volumen_anual_L = Q_L_h * horas_anuales
    kWh_por_m3 = P_el_kW / (Q_L_h / 1000.0)

    return {
        "m_in_kg_h": m_in_kg_h, "m_out_kg_h": m_out,
        "Q_L_h": Q_L_h, "Q_m3_s": Q_m3_s,
        "P1_bar": P1_bar, "P2_bar": P2 / 1e5,
        "P_hid_kW": P_hid_kW, "P_eje_kW": P_eje_kW,
        "P_el_kW": P_el_kW, "P_instalada_kW": P_instalada_kW,
        "dT_C": dT, "T_in_C": T_in_C, "T_out_C": T_out,
        "Q_disipado_kW": Q_disipado_kW,
        "v1_m_s": v1, "h1_um": h1_um, "v2_m_s": v2, "h2_um": h2_um,
        "energia_kWh_anio": energia_kWh_anio,
        "volumen_anual_L": volumen_anual_L,
        "kWh_por_m3": kWh_por_m3,
    }


def barrido_presion(presiones_bar, **kwargs):
    """Análisis de sensibilidad: resultados para una lista de presiones."""
    kwargs.pop("P1_bar", None)
    return [calcular_homogeneizacion(P1_bar=p, **kwargs) for p in presiones_bar]


# ==============================================================================
# INTERFAZ STREAMLIT
# ==============================================================================
def mostrar_homogeneizacion():
    st.title("🎛️ Sección: Homogeneización")
    st.markdown(
        "Calcula el balance de materia y energía y los parámetros de diseño de la "
        "**homogeneización de dos etapas** del zumo de naranja, que reduce el tamaño de "
        "partícula de la pulpa fina para mejorar la estabilidad de la turbidez (*cloud*) "
        "y evitar la sedimentación. Recibe el zumo ya tamizado y enfriado, y entrega "
        "hacia **Desaireación**."
    )

    # ---- Entradas -------------------------------------------------------------
    st.sidebar.header("Entradas desde la etapa anterior")
    m_in = st.sidebar.slider("Flujo de jugo refinado ṁ_in [kg/h]", 100.0, 1000.0, M_IN_CASO_BASE, 10.0)
    T_in = st.sidebar.slider("Temperatura de entrada [°C]", 0.0, 20.0, T_IN_CASO_BASE, 0.5)

    st.sidebar.header("Parámetros del homogeneizador")
    P1 = st.sidebar.slider("Presión de 1.ª etapa [bar]", 100.0, 250.0, 150.0, 5.0)
    frac_P2 = st.sidebar.slider("Presión de 2.ª etapa [% de la 1.ª]", 0.0, 20.0, 10.0, 1.0) / 100.0
    eta_bomba = st.sidebar.slider("Eficiencia de bomba (hidráulica + mecánica)", 0.70, 0.95, 0.85, 0.01)
    eta_motor = st.sidebar.slider("Eficiencia del motor", 0.85, 0.97, 0.92, 0.01)
    factor = st.sidebar.slider("Factor de diseño (capacidad instalada)", 1.00, 1.50, 1.20, 0.05)

    st.sidebar.header("Propiedades del zumo")
    rho = st.sidebar.number_input("Densidad [kg/m³]", value=RHO_JUGO, step=5.0)
    cp = st.sidebar.number_input("Cp [kJ/(kg·°C)]", value=CP_JUGO, step=0.05)

    st.sidebar.header("Válvula (indicativo)")
    cd = st.sidebar.slider("Coeficiente de descarga Cd", 0.50, 0.95, 0.70, 0.01)
    d_asiento = st.sidebar.number_input("Diámetro del asiento [mm]", value=10.0, step=1.0, min_value=1.0)

    st.sidebar.header("Operación")
    dias = st.sidebar.number_input("Días de operación al año", value=250.0, step=5.0, min_value=1.0)
    horas = st.sidebar.number_input("Horas de operación al día", value=16.0, step=1.0, min_value=1.0)

    try:
        r = calcular_homogeneizacion(
            m_in, T_in, P1, frac_P2, rho, cp, eta_bomba, eta_motor,
            factor, cd, d_asiento, dias * horas,
        )
    except ValueError as e:
        st.error(str(e))
        return

    # ---- Imagen opcional del equipo (robusta ante ausencia del archivo) ----------
    ruta_img = os.path.join("img", "homogeneizador.png")
    if os.path.exists(ruta_img):
        st.image(ruta_img, caption="Homogeneizador de alta presión de dos etapas", width=360)
    else:
        st.info("Coloca la imagen del equipo en la ruta: img/homogeneizador.png")

    # ---- Resultados ---------------------------------------------------------------
    st.subheader("1. Balance de materia")
    c1, c2, c3 = st.columns(3)
    c1.metric("Flujo de entrada", f"{r['m_in_kg_h']:,.2f} kg/h")
    c2.metric("Flujo de salida", f"{r['m_out_kg_h']:,.2f} kg/h")
    c3.metric("Caudal volumétrico", f"{r['Q_L_h']:,.1f} L/h")

    st.subheader("2. Energía y temperatura")
    c4, c5, c6, c7 = st.columns(4)
    c4.metric("Potencia hidráulica", f"{r['P_hid_kW']:.2f} kW")
    c5.metric("Potencia eléctrica", f"{r['P_el_kW']:.2f} kW")
    c6.metric("Potencia instalada", f"{r['P_instalada_kW']:.2f} kW", help=f"Con factor de diseño {factor:.2f}")
    c7.metric("Temperatura de salida", f"{r['T_out_C']:.2f} °C", delta=f"+{r['dT_C']:.2f} °C")

    st.subheader("3. Válvula (indicativo)")
    c8, c9, c10 = st.columns(3)
    c8.metric("Velocidad en rendija, 1.ª etapa", f"{r['v1_m_s']:.0f} m/s")
    c9.metric("Altura de rendija, 1.ª etapa", f"{r['h1_um']:.0f} µm")
    if r["h2_um"] is not None:
        c10.metric("Altura de rendija, 2.ª etapa", f"{r['h2_um']:.0f} µm")

    st.subheader("4. Indicadores anuales")
    c11, c12 = st.columns(2)
    c11.metric("Consumo eléctrico", f"{r['energia_kWh_anio']:,.0f} kWh/año")
    c12.metric("Energía específica", f"{r['kWh_por_m3']:.2f} kWh/m³")

    st.success(
        f"Entrega a Desaireación: {r['m_out_kg_h']:,.2f} kg/h de zumo homogeneizado a {r['T_out_C']:.2f} °C."
    )

    # ---- Gráficas de sensibilidad -------------------------------------------------
    st.subheader("📊 Sensibilidad a la presión de homogeneización")
    presiones = list(range(100, 251, 10))
    barrido = barrido_presion(
        presiones, m_in_kg_h=m_in, T_in_C=T_in, frac_P2=frac_P2, rho_kg_m3=rho,
        cp_kJ_kgC=cp, eta_bomba=eta_bomba, eta_motor=eta_motor, factor_diseno=factor,
        cd=cd, d_asiento_mm=d_asiento, horas_anuales=dias * horas,
    )
    g1, g2 = st.columns(2)
    with g1:
        fig, ax = plt.subplots(figsize=(5, 3.6))
        ax.plot(presiones, [b["P_el_kW"] for b in barrido], color="#E8602C", lw=2)
        ax.scatter([P1], [r["P_el_kW"]], color="#1F6FEB", zorder=3, label="Punto de operación")
        ax.set_xlabel("Presión de 1.ª etapa [bar]")
        ax.set_ylabel("Potencia eléctrica [kW]")
        ax.set_title("Potencia vs presión")
        ax.legend()
        st.pyplot(fig)
    with g2:
        fig, ax = plt.subplots(figsize=(5, 3.6))
        ax.plot(presiones, [b["T_out_C"] for b in barrido], color="#E8602C", lw=2)
        ax.scatter([P1], [r["T_out_C"]], color="#1F6FEB", zorder=3, label="Punto de operación")
        ax.set_xlabel("Presión de 1.ª etapa [bar]")
        ax.set_ylabel("Temperatura de salida [°C]")
        ax.set_title("Temperatura de salida vs presión")
        ax.legend()
        st.pyplot(fig)

    with st.expander("Supuestos del modelo"):
        st.markdown(
            "- Estado estacionario, fluido incompresible, propiedades constantes.\n"
            "- Toda la potencia hidráulica se disipa como calor en el fluido "
            "(ΔT es una **cota superior**); sin pérdidas de calor al ambiente.\n"
            "- Las pérdidas de bomba y motor no calientan el zumo.\n"
            "- La 2.ª etapa trabaja a una fracción de la presión de la 1.ª; la caída de "
            "presión total sigue siendo P1.\n"
            "- Velocidad y altura de rendija: Bernoulli con Cd supuesto; son valores indicativos."
        )


if __name__ == "__main__":
    if st is None:
        raise SystemExit("Instala Streamlit para ejecutar la interfaz: pip install streamlit")
    mostrar_homogeneizacion()
