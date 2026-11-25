"""
Etapa 4 - Homogeneización (mezcla de variedades en tanque con agitador)
=======================================================================
Planta virtual de zumo de naranja: 1.500.000 L/año (TFG, Palma del Río, Córdoba).

Posición en el diagrama de flujo:
    ... Enfriamiento -> Tanques asépticos -> HOMOGENEIZACIÓN -> Desaireación -> ...

En el TFG la homogeneización NO es de alta presión: consiste en mezclar las tres
variedades de naranja en relación 1/1/1 en un tanque con agitador, para dar al
producto final condiciones estándar de acidez, color y sabor.

Modelo (estado estacionario, fluido incompresible, propiedades constantes)
--------------------------------------------------------------------------
  1. Balance de materia:        m_out = m_in = sum(m_i),  m_i = f_i * m_in
  2. Composición de la mezcla:  x_mezcla = sum(f_i * x_i)    (°Brix, acidez)
  3. Tiempo de residencia:      tau = V_liq / Q
  4. Reynolds del agitador:     Re = rho * N * D^2 / mu
  5. Potencia del agitador:     P = Np * rho * N^3 * D^5
  6. Tiempo de mezcla (turbulento, 95 %):
                                theta = 5,2 * T^1,5 * sqrt(H) / (Np^(1/3) * N * D^2)
     válido si Np^(1/3) * Re >= 6370 (Paul, Atiemo-Obeng y Kresta, 2004).
  7. Calentamiento:             dT = P / (m * cp)    (la agitación se disipa como calor)

Entradas desde la etapa anterior (Tanques asépticos): flujo y temperatura del zumo.
Salidas hacia Desaireación: flujo, temperatura y composición del zumo mezclado.

Notas de integración: NO usa st.set_page_config() (solo va en la página principal
del hub). Guardar en la carpeta pages/ del repositorio.
"""

import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

try:
    import streamlit as st
except ImportError:  # permite probar el modelo sin Streamlit instalado
    st = None

# ------------------------------------------------------------------------------
# Datos de la planta (TFG) y del módulo anterior (Tamizado y Enfriamiento)
# ------------------------------------------------------------------------------
HORAS_DIA = 12.0                       # jornada 6:00-18:00
DIAS_ENVASADO = 100.0                  # 2 días/semana durante todo el año
M_ENVASADO_DIA_KG = 15675.0            # zumo envasado cada día (15.000 L)
M_ENVASADO_DIA_KG_HUB = 18017.24       # zumo tamizado por día de extracción (TFG)
RHO_KG_M3 = M_ENVASADO_DIA_KG / 15000.0 * 1000.0   # 1045 kg/m3
CP = 3.93                              # kJ/(kg·°C), mismo valor que el módulo de enfriamiento
T_ALMACEN_C = -0.5                     # centro del intervalo -1 a 0 °C del TFG
CAPACIDAD_TANQUE_MEZCLA_L_H = 6000.0   # tabla 9 del TFG

M_PLANTA = M_ENVASADO_DIA_KG / HORAS_DIA                 # 1306,25 kg/h
M_HUB = 520.84 * M_ENVASADO_DIA_KG / M_ENVASADO_DIA_KG_HUB  # 453,13 kg/h (base del hub)


# ==============================================================================
# MODELO (función pura: no depende de Streamlit)
# ==============================================================================
def _positivo(**kw):
    for nombre, valor in kw.items():
        if valor is None or valor <= 0:
            raise ValueError(f"'{nombre}' debe ser positivo.")


def calcular_mezcla(
    m_kg_h=M_PLANTA,
    proporciones=(1.0, 1.0, 1.0),
    brix=(11.0, 12.5, 10.0),
    acidez=(0.9, 0.8, 1.1),
    T_in_C=T_ALMACEN_C,
    rho_kg_m3=RHO_KG_M3,
    cp_kJ_kgC=CP,
    T_tanque_m=1.132,
    H_tanque_m=1.914,
    llenado=0.80,
    D_sobre_T=1.0 / 3.0,
    N_rpm=100.0,
    Np=1.3,
    mu_mPa_s=4.0,
    eta_motor=0.85,
    factor_diseno=1.5,
    horas_anuales=HORAS_DIA * DIAS_ENVASADO,
):
    """Mezcla de variedades en un tanque con agitador (régimen turbulento)."""
    _positivo(m_kg_h=m_kg_h, rho_kg_m3=rho_kg_m3, cp_kJ_kgC=cp_kJ_kgC, T_tanque_m=T_tanque_m,
              H_tanque_m=H_tanque_m, D_sobre_T=D_sobre_T, N_rpm=N_rpm, Np=Np,
              mu_mPa_s=mu_mPa_s, eta_motor=eta_motor, factor_diseno=factor_diseno,
              horas_anuales=horas_anuales)
    if not 0 < llenado <= 1:
        raise ValueError("El llenado debe estar en (0, 1].")
    if D_sobre_T >= 1:
        raise ValueError("D/T debe ser menor que 1.")
    if eta_motor > 1:
        raise ValueError("La eficiencia del motor no puede superar 1.")
    if len(proporciones) != len(brix) or len(brix) != len(acidez):
        raise ValueError("Proporciones, °Brix y acidez deben tener la misma longitud.")
    if any(p < 0 for p in proporciones) or sum(proporciones) <= 0:
        raise ValueError("Las proporciones deben ser no negativas y sumar más de cero.")
    if any(a <= 0 for a in acidez):
        raise ValueError("La acidez debe ser positiva.")

    avisos = []
    s = sum(proporciones)
    fr = [p / s for p in proporciones]

    # 1-2. Balance de materia y composición de la mezcla
    m_var = [f * m_kg_h for f in fr]
    q_var_L_h = [m / rho_kg_m3 * 1000.0 for m in m_var]
    brix_mez = sum(f * b for f, b in zip(fr, brix))
    acid_mez = sum(f * a for f, a in zip(fr, acidez))
    ratio_mez = brix_mez / acid_mez
    ratios = [b / a for b, a in zip(brix, acidez)]
    desv_ratio_max = max(abs(r - ratio_mez) for r in ratios)

    # 3. Tanque
    Q_m3_h = m_kg_h / rho_kg_m3
    Q_L_h = Q_m3_h * 1000.0
    H_liq = H_tanque_m * llenado
    V_liq_m3 = math.pi / 4.0 * T_tanque_m ** 2 * H_liq
    tau_h = V_liq_m3 / Q_m3_h
    uso_capacidad = Q_L_h / CAPACIDAD_TANQUE_MEZCLA_L_H
    if uso_capacidad > 1:
        avisos.append("El caudal supera los 6000 L/h del tanque de mezcla del TFG.")

    # 4-6. Agitador
    D = D_sobre_T * T_tanque_m
    N = N_rpm / 60.0
    mu = mu_mPa_s / 1000.0
    Re = rho_kg_m3 * N * D ** 2 / mu
    regimen = Np ** (1.0 / 3.0) * Re
    turbulento = regimen >= 6370.0
    if not turbulento:
        avisos.append("Régimen no turbulento (Np^(1/3)·Re < 6370): el tiempo de mezcla está subestimado.")
    P_W = Np * rho_kg_m3 * N ** 3 * D ** 5
    P_el_W = P_W / eta_motor
    P_inst_W = P_el_W * factor_diseno
    theta_s = 5.2 * T_tanque_m ** 1.5 * math.sqrt(H_liq) / (Np ** (1.0 / 3.0) * N * D ** 2)
    if theta_s > 0.1 * tau_h * 3600.0:
        avisos.append("El tiempo de mezcla supera el 10 % del tiempo de residencia: mezcla insuficiente.")

    # 7. Térmico
    dT = P_W / 1000.0 / (m_kg_h / 3600.0 * cp_kJ_kgC)

    return {
        "m_in_kg_h": m_kg_h, "m_out_kg_h": sum(m_var),
        "fracciones": fr, "m_var_kg_h": m_var, "q_var_L_h": q_var_L_h,
        "brix_mezcla": brix_mez, "acidez_mezcla": acid_mez, "ratio_mezcla": ratio_mez,
        "ratios_var": ratios, "desv_ratio_max": desv_ratio_max,
        "Q_L_h": Q_L_h, "uso_capacidad": uso_capacidad,
        "V_liq_L": V_liq_m3 * 1000.0, "tau_min": tau_h * 60.0, "H_liq_m": H_liq,
        "D_agit_m": D, "Re": Re, "regimen": regimen, "turbulento": turbulento,
        "P_agit_W": P_W, "P_el_W": P_el_W, "P_inst_W": P_inst_W,
        "theta_s": theta_s, "tau_sobre_theta": tau_h * 3600.0 / theta_s,
        "dT_C": dT, "T_in_C": T_in_C, "T_out_C": T_in_C + dT,
        "energia_kWh_anio": P_el_W / 1000.0 * horas_anuales,
        "avisos": avisos,
    }


def barrido_rpm(rpms, **kwargs):
    """Sensibilidad del agitador a la velocidad de giro."""
    kwargs.pop("N_rpm", None)
    return [calcular_mezcla(N_rpm=r, **kwargs) for r in rpms]


# ==============================================================================
# GRÁFICAS (se usan en la interfaz y para las figuras del artículo)
# ==============================================================================
def figura_variedades(res):
    nombres = ["Variedad A", "Variedad B", "Variedad C", "Mezcla"]
    valores = list(res["ratios_var"]) + [res["ratio_mezcla"]]
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    barras = ax.bar(nombres, valores, color=["#FFB066", "#FFB066", "#FFB066", "#1F6FEB"])
    for b, v in zip(barras, valores):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.2, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_ylabel("Relación °Brix / acidez")
    ax.set_title("Estandarización por mezcla")
    ax.set_ylim(0, max(valores) * 1.2)
    fig.tight_layout()
    return fig


def figura_agitador(rpms, barrido, N_actual, res):
    fig, ax = plt.subplots(figsize=(6.0, 3.6))
    ax.plot(rpms, [b["P_agit_W"] for b in barrido], color="#E8602C", lw=2)
    ax.scatter([N_actual], [res["P_agit_W"]], color="#1F6FEB", zorder=3)
    ax.set_xlabel("Velocidad del agitador [rpm]")
    ax.set_ylabel("Potencia en el eje [W]", color="#E8602C")
    ax.grid(alpha=0.25)
    ax2 = ax.twinx()
    ax2.plot(rpms, [b["theta_s"] for b in barrido], color="#1F6FEB", lw=2, ls="--")
    ax2.set_ylabel("Tiempo de mezcla 95 % [s]", color="#1F6FEB")
    ax.set_title("Agitador: potencia y tiempo de mezcla")
    fig.tight_layout()
    return fig


# ==============================================================================
# INTERFAZ STREAMLIT
# ==============================================================================
def mostrar_homogeneizacion():
    st.title("🎛️ Etapa 4: Homogeneización")
    st.markdown(
        "Calcula el diseño y la operación del **tanque de mezcla con agitador** donde se "
        "homogeneizan las tres variedades de naranja (relación 1/1/1) para dar al zumo "
        "condiciones estándar de acidez, color y sabor. Recibe el zumo de los **tanques "
        "asépticos** y lo entrega a **Desaireación**."
    )

    # ---- Entradas desde la etapa anterior -----------------------------------------
    st.sidebar.header("Entradas desde Tanques asépticos")
    base = st.sidebar.radio(
        "Base de cálculo",
        ["Planta (TFG, 1,5 millones L/año)", "Hub del equipo (1000 kg/h de fruta)"],
    )
    es_planta = base.startswith("Planta")
    k = "p" if es_planta else "h"
    m_in = st.sidebar.slider(
        "Flujo de zumo ṁ_in [kg/h]", 100.0, 3000.0,
        float(M_PLANTA if es_planta else M_HUB), 10.0, key=f"m{k}",
    )
    T_in = st.sidebar.slider("Temperatura de entrada [°C]", -2.0, 10.0, T_ALMACEN_C, 0.5)

    st.sidebar.header("Variedades de naranja")
    brix, acidez, props = [], [], []
    for i, (b0, a0) in enumerate([(11.0, 0.9), (12.5, 0.8), (10.0, 1.1)]):
        nombre = "ABC"[i]
        props.append(st.sidebar.number_input(f"Proporción variedad {nombre}", value=1.0, min_value=0.0, step=0.1, key=f"p{i}"))
        brix.append(st.sidebar.number_input(f"°Brix variedad {nombre} (ilustrativo)", value=b0, step=0.5, key=f"b{i}"))
        acidez.append(st.sidebar.number_input(f"Acidez variedad {nombre} [g/100 mL] (ilustrativo)", value=a0, min_value=0.1, step=0.1, key=f"a{i}"))

    st.sidebar.header("Tanque de mezcla y agitador")
    T_m = st.sidebar.number_input("Diámetro del tanque T [m]", value=1.132, min_value=0.3, step=0.05)
    H_m = st.sidebar.number_input("Altura del tanque [m]", value=1.914, min_value=0.3, step=0.05)
    llenado = st.sidebar.slider("Nivel de llenado del tanque", 0.50, 1.00, 0.80, 0.05)
    DT = st.sidebar.slider("Relación D/T del agitador", 0.25, 0.60, 0.33, 0.01)
    rpm = st.sidebar.slider("Velocidad del agitador [rpm]", 30.0, 300.0, 100.0, 5.0)
    Np = st.sidebar.number_input("Número de potencia Np", value=1.3, min_value=0.1, step=0.1)
    mu = st.sidebar.number_input("Viscosidad del zumo [mPa·s]", value=4.0, min_value=0.5, step=0.5)
    eta_m = st.sidebar.slider("Eficiencia del motor", 0.60, 0.95, 0.85, 0.01)

    try:
        r = calcular_mezcla(
            m_kg_h=m_in, proporciones=tuple(props), brix=tuple(brix), acidez=tuple(acidez),
            T_in_C=T_in, T_tanque_m=T_m, H_tanque_m=H_m, llenado=llenado, D_sobre_T=DT,
            N_rpm=rpm, Np=Np, mu_mPa_s=mu, eta_motor=eta_m,
        )
    except ValueError as e:
        st.error(str(e))
        return

    for aviso in r["avisos"]:
        st.warning(aviso)

    # ---- Imagen opcional del equipo (robusta ante ausencia del archivo) -----------------
    ruta_img = os.path.join("img", "tanque_mezcla.png")
    if os.path.exists(ruta_img):
        st.image(ruta_img, caption="Tanque de mezcla con agitador", width=300)
    else:
        st.info(f"Coloca la imagen del equipo en la ruta: {ruta_img}")

    # ---- Resultados ---------------------------------------------------------------------
    st.subheader("1. Balance de materia")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Flujo de entrada", f"{r['m_in_kg_h']:,.2f} kg/h")
    c2.metric("Flujo de salida", f"{r['m_out_kg_h']:,.2f} kg/h")
    c3.metric("Caudal volumétrico", f"{r['Q_L_h']:,.0f} L/h", help=f"{r['uso_capacidad']:.1%} de los 6000 L/h del tanque")
    c4.metric("Caudal por variedad", f"{r['q_var_L_h'][0]:,.1f} L/h")

    st.subheader("2. Composición de la mezcla")
    c5, c6, c7 = st.columns(3)
    c5.metric("°Brix de la mezcla", f"{r['brix_mezcla']:.2f}")
    c6.metric("Acidez de la mezcla", f"{r['acidez_mezcla']:.2f} g/100 mL")
    c7.metric("Relación °Brix/acidez", f"{r['ratio_mezcla']:.1f}")

    st.subheader("3. Tanque y agitador")
    c8, c9, c10, c11 = st.columns(4)
    c8.metric("Volumen de líquido", f"{r['V_liq_L']:,.0f} L")
    c9.metric("Tiempo de residencia", f"{r['tau_min']:.0f} min")
    c10.metric("Tiempo de mezcla (95 %)", f"{r['theta_s']:.0f} s")
    c11.metric("Régimen", "Turbulento" if r["turbulento"] else "No turbulento", help=f"Re = {r['Re']:,.0f}")

    st.subheader("⚡ Requerimientos energéticos")
    c12, c13, c14, c15 = st.columns(4)
    c12.metric("Potencia en el eje", f"{r['P_agit_W']:.0f} W")
    c13.metric("Potencia eléctrica", f"{r['P_el_W']:.0f} W")
    c14.metric("Potencia instalada", f"{r['P_inst_W']:.0f} W", help="Con factor de diseño 1,5")
    c15.metric("Temperatura de salida", f"{r['T_out_C']:.2f} °C", delta=f"+{r['dT_C']:.3f} °C")

    st.success(
        f"Entrega a Desaireación: {r['m_out_kg_h']:,.2f} kg/h de zumo mezclado a "
        f"{r['T_out_C']:.2f} °C, {r['brix_mezcla']:.2f} °Brix."
    )

    # ---- Gráficas -------------------------------------------------------------------------
    st.subheader("📊 Gráficas de resultados")
    rpms = list(range(40, 201, 10))
    barrido = barrido_rpm(
        rpms, m_kg_h=m_in, proporciones=tuple(props), brix=tuple(brix), acidez=tuple(acidez),
        T_in_C=T_in, T_tanque_m=T_m, H_tanque_m=H_m, llenado=llenado, D_sobre_T=DT,
        Np=Np, mu_mPa_s=mu, eta_motor=eta_m,
    )
    g1, g2 = st.columns(2)
    with g1:
        st.pyplot(figura_variedades(r))
    with g2:
        st.pyplot(figura_agitador(rpms, barrido, rpm, r))

    with st.expander("Supuestos del modelo"):
        st.markdown(
            "- Estado estacionario, fluido incompresible y propiedades constantes "
            "(ρ = 1045 kg/m³, cp = 3,93 kJ/(kg·°C)).\n"
            "- Las tres variedades llegan simultáneamente y la mezcla es lineal (promedio ponderado).\n"
            "- Dimensiones del tanque de mezcla: interpretación de la tabla 9 del TFG "
            "(1,132 m de diámetro y 1,914 m de altura).\n"
            "- Np, viscosidad y relación D/T son supuestos típicos; contrastar con la ficha del equipo.\n"
            "- °Brix y acidez de las variedades son **valores ilustrativos**: sustituir por los "
            "medidos en recepción.\n"
            "- Toda la potencia del agitador se disipa como calor en el zumo.\n"
            "- Tiempo de mezcla: correlación para régimen turbulento; se avisa si no se cumple."
        )


if __name__ == "__main__":
    if st is None:
        raise SystemExit("Instala Streamlit para ejecutar la interfaz: pip install streamlit")
    mostrar_homogeneizacion()
