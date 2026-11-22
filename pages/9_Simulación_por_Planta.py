import math
import pandas as pd
import streamlit as st

try:
    st.set_page_config(
        page_title="Simulador Integral de Planta - Jugo de Naranja",
        page_icon="🍊",
        layout="wide",
    )
except Exception:
    pass


# ==============================================================================
# 1. UTILIDADES DE FORMATO Y VALIDACIÓN
# ==============================================================================
EPS = 1e-6


def fmt(valor: float, dec: int = 2) -> str:
    """Formato numérico uniforme con separador de miles."""
    return f"{valor:,.{dec}f}"


def inicializar_estado() -> None:
    defaults = {
        # Etapa 1: Selección, Lavado y Extracción
        "p_prod_anual_l": 1_500_000.0,
        "p_dias_campana": 87,
        "p_horas_turno_ext": 8.0,
        "p_densidad_kg_l": 1.045,
        "p_pulpa_ext_pct": 12.0,
        "p_pulpa_com_pct": 8.0,
        "p_rend_sel1_pct": 97.0,
        "p_rend_lavado_pct": 99.5,
        "p_rend_sel2_pct": 99.5,
        "p_rend_ext_pct": 50.0,
        "p_frac_piel_pct": 49.3,
        "p_frac_emulsion_pct": 0.7,
        "p_agua_ext_kg_h": 1000.0,
        "p_num_extractores": 1,
        # Etapa 2: Tamizado y Enfriamiento
        "p_efic_tamiz": 0.85,
        "p_temp_enf_in": 28.0,
        "p_temp_enf_out": 5.0,
        # Etapa 3: Almacenamiento Aséptico
        "p_num_tanques": 12,
        "p_cap_tanque_l": 100_000.0,
        "p_temp_alm_c": -0.5,
        "p_presion_n2_bar": 0.20,
        "p_dias_envasado": 100,
        "p_horas_turno_env": 2.5,  # 15,000 L/día / 2.5 h = 6,000 L/h (nominal pasteurizador)
        "p_dias_max_ret": 365,
        # Etapa 4: Homogeneización
        "p_presion_homog_bar": 150.0,
        "p_efic_homog": 0.85,
        # Etapa 5: Desaireación
        "p_presion_vacio_kpa": 7.0,
        "p_temp_desair_in": 15.0,
        "p_o2_inicial_mgl": 10.0,
        # Etapa 6: Pasteurización
        "p_brix": 11.2,
        "p_temp_past_c": 90.0,
        "p_tiempo_ret_s": 20.0,
        "p_temp_past_out_c": 4.0,
        "p_regen_pct": 0.0,
        "p_vitc_in_mgl": 500.0,
        # Etapa 7 y 8: Envasado Aséptico y Etiquetado
        "p_merma_env_pct": 1.0,
        "p_merma_etiq_pct": 1.5,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def restaurar_defaults() -> None:
    for k in list(st.session_state.keys()):
        if k.startswith("p_"):
            del st.session_state[k]
    inicializar_estado()


# ==============================================================================
# 2. MOTORES DE CÁLCULO ACOPLADOS EN SERIE (ETAPAS 1 A 8)
# ==============================================================================
def calcular_planta(cfg: dict) -> dict:
    densidad_kg_l = cfg["p_densidad_kg_l"]
    densidad_kg_m3 = densidad_kg_l * 1000.0

    # --------------------------------------------------------------------------
    # ETAPA 1: SELECCIÓN, LAVADO Y EXTRACCIÓN
    # --------------------------------------------------------------------------
    horas_anuales_ext = cfg["p_dias_campana"] * cfg["p_horas_turno_ext"]
    m_zumo_comercial_ano = cfg["p_prod_anual_l"] * densidad_kg_l

    rend_tamiz_teorico = (1.0 - cfg["p_pulpa_ext_pct"] / 100.0) / max(
        1e-4, (1.0 - cfg["p_pulpa_com_pct"] / 100.0)
    )
    m_zumo_bruto_ano = m_zumo_comercial_ano / rend_tamiz_teorico

    m_naranja_ext_ano = m_zumo_bruto_ano / (cfg["p_rend_ext_pct"] / 100.0)
    m_piel_semillas_ano = m_naranja_ext_ano * (cfg["p_frac_piel_pct"] / 100.0)
    m_emulsion_pura_ano = m_naranja_ext_ano * (cfg["p_frac_emulsion_pct"] / 100.0)
    m_agua_ext_ano = cfg["p_agua_ext_kg_h"] * cfg["p_num_extractores"] * horas_anuales_ext

    m_ent_sel2_ano = m_naranja_ext_ano / (cfg["p_rend_sel2_pct"] / 100.0)
    m_destrio2_ano = m_ent_sel2_ano - m_naranja_ext_ano

    m_ent_lavado_ano = m_ent_sel2_ano / (cfg["p_rend_lavado_pct"] / 100.0)
    m_merma_lavado_ano = m_ent_lavado_ano - m_ent_sel2_ano

    m_ent_sel1_ano = m_ent_lavado_ano / (cfg["p_rend_sel1_pct"] / 100.0)
    m_destrio1_ano = m_ent_sel1_ano - m_ent_lavado_ano

    zumo_bruto_kg_h = m_zumo_bruto_ano / horas_anuales_ext
    zumo_bruto_l_h = zumo_bruto_kg_h / densidad_kg_l
    emulsion_diluida_kg_h = (m_emulsion_pura_ano + m_agua_ext_ano) / horas_anuales_ext
    subproductos_solidos_kg_h = (
        m_piel_semillas_ano + m_destrio1_ano + m_destrio2_ano + m_merma_lavado_ano
    ) / horas_anuales_ext
    rendimiento_global_fruta_pct = (m_zumo_bruto_ano / m_ent_sel1_ano) * 100.0
    suma_fracciones_ext = (
        cfg["p_rend_ext_pct"] + cfg["p_frac_piel_pct"] + cfg["p_frac_emulsion_pct"]
    )

    etapa_1 = {
        "naranja_recep_kg_h": m_ent_sel1_ano / horas_anuales_ext,
        "naranja_ext_kg_h": m_naranja_ext_ano / horas_anuales_ext,
        "zumo_bruto_kg_h": zumo_bruto_kg_h,
        "zumo_bruto_l_h": zumo_bruto_l_h,
        "emulsion_diluida_kg_h": emulsion_diluida_kg_h,
        "subproductos_solidos_kg_h": subproductos_solidos_kg_h,
        "rendimiento_global_pct": rendimiento_global_fruta_pct,
        "suma_fracciones_ext": suma_fracciones_ext,
        "horas_anuales_ext": horas_anuales_ext,
    }

    # --------------------------------------------------------------------------
    # ETAPA 2: TAMIZADO Y ENFRIAMIENTO (Recibe zumo bruto de Etapa 1)
    # --------------------------------------------------------------------------
    m_jugo_crudo_kg_h = etapa_1["zumo_bruto_kg_h"]
    x_pulpa_in = cfg["p_pulpa_ext_pct"] / 100.0
    efic_tamiz = cfg["p_efic_tamiz"]

    m_pulpa_residuo_kg_h = m_jugo_crudo_kg_h * x_pulpa_in * efic_tamiz
    m_jugo_refinado_kg_h = m_jugo_crudo_kg_h - m_pulpa_residuo_kg_h
    x_pulpa_final = (
        ((x_pulpa_in * m_jugo_crudo_kg_h) - m_pulpa_residuo_kg_h) / m_jugo_refinado_kg_h
        if m_jugo_refinado_kg_h > 0
        else 0.0
    )
    vol_refinado_l_h = m_jugo_refinado_kg_h / densidad_kg_l

    cp_enfriamiento_kj_kgc = 3.93
    q_enfriamiento_1_kw = (
        m_jugo_refinado_kg_h
        * cp_enfriamiento_kj_kgc
        * (cfg["p_temp_enf_in"] - cfg["p_temp_enf_out"])
    ) / 3600.0

    etapa_2 = {
        "m_jugo_crudo_kg_h": m_jugo_crudo_kg_h,
        "m_jugo_refinado_kg_h": m_jugo_refinado_kg_h,
        "vol_refinado_l_h": vol_refinado_l_h,
        "m_pulpa_residuo_kg_h": m_pulpa_residuo_kg_h,
        "x_pulpa_final_pct": x_pulpa_final * 100.0,
        "q_enfriamiento_kw": q_enfriamiento_1_kw,
        "temp_salida_c": cfg["p_temp_enf_out"],
    }

    # --------------------------------------------------------------------------
    # ETAPA 3: ALMACÉN DE TANQUES ASÉPTICOS (Pulmón campaña -> línea aséptica)
    # --------------------------------------------------------------------------
    cap_total_l = cfg["p_num_tanques"] * cfg["p_cap_tanque_l"]
    caudal_entrada_l_dia = etapa_2["vol_refinado_l_h"] * cfg["p_horas_turno_ext"]
    total_producido_campana_l = caudal_entrada_l_dia * cfg["p_dias_campana"]

    dias_env = max(1, cfg["p_dias_envasado"])
    horas_turno_env = max(0.1, cfg["p_horas_turno_env"])
    caudal_salida_l_dia = total_producido_campana_l / dias_env
    caudal_linea_aseptica_l_h = caudal_salida_l_dia / horas_turno_env

    # Simulación anual de inventario (365 días)
    vol_actual = 0.0
    pico_vol = 0.0
    rechazado_l = 0.0
    jornadas_completadas = 0
    historial_tanques = []
    for dia in range(1, 366):
        if dia <= cfg["p_dias_campana"]:
            espacio = max(0.0, cap_total_l - vol_actual)
            ingresado = min(caudal_entrada_l_dia, espacio)
            vol_actual += ingresado
            rechazado_l += caudal_entrada_l_dia - ingresado
        if dia >= 46 and (dia % 7 in (2, 5)) and jornadas_completadas < dias_env:
            if vol_actual >= caudal_salida_l_dia - EPS:
                vol_actual -= caudal_salida_l_dia
                jornadas_completadas += 1
        pico_vol = max(pico_vol, vol_actual)
        historial_tanques.append({"Día": dia, "Inventario (L)": vol_actual})

    # Cálculo CIP por tanque (Anejo 2 TFG)
    vol_dep_l = 0.015 * cfg["p_cap_tanque_l"]
    diam_cip_m = 2.0 * 0.0254
    vol_tub_l = math.pi * (diam_cip_m / 2.0) ** 2 * 22.0 * 1000.0
    vol_sol_cip_l = 1.2 * (vol_dep_l + vol_tub_l)
    naoh_kg = vol_sol_cip_l * 0.01
    hno3_kg = vol_sol_cip_l * 0.008
    caudal_cip_lh = 21_546.82 if cfg["p_cap_tanque_l"] >= 100_000 else 11_000.0
    tiempo_cip_min = (vol_sol_cip_l / caudal_cip_lh) * 60.0

    condiciones_seguras = (-1.0 <= cfg["p_temp_alm_c"] <= 0.0) and (
        0.10 <= cfg["p_presion_n2_bar"] <= 0.50
    )

    etapa_3 = {
        "cap_total_l": cap_total_l,
        "caudal_entrada_l_dia": caudal_entrada_l_dia,
        "caudal_salida_l_dia": caudal_salida_l_dia,
        "caudal_linea_l_h": caudal_linea_aseptica_l_h,
        "pico_ocupacion_l": pico_vol,
        "pico_ocupacion_pct": (pico_vol / cap_total_l * 100.0) if cap_total_l > 0 else 0.0,
        "rechazado_l": rechazado_l,
        "condiciones_seguras": condiciones_seguras,
        "cip_vol_l": vol_sol_cip_l,
        "cip_naoh_kg": naoh_kg,
        "cip_hno3_kg": hno3_kg,
        "cip_tiempo_min": tiempo_cip_min,
        "historial": historial_tanques,
    }

    # --------------------------------------------------------------------------
    # ETAPA 4: HOMOGENEIZACIÓN (Recibe corriente desde Tanques Asépticos)
    # --------------------------------------------------------------------------
    vol_homog_l_h = etapa_3["caudal_linea_l_h"]
    mass_homog_kg_h = vol_homog_l_h * densidad_kg_l
    vol_homog_m3_s = (vol_homog_l_h / 1000.0) / 3600.0
    delta_p_pa = cfg["p_presion_homog_bar"] * 100_000.0

    pot_hidraulica_kw = (vol_homog_m3_s * delta_p_pa) / 1000.0
    pot_electrica_kw = pot_hidraulica_kw / cfg["p_efic_homog"]

    etapa_4 = {
        "vol_flow_l_h": vol_homog_l_h,
        "mass_flow_kg_h": mass_homog_kg_h,
        "pot_hidraulica_kw": pot_hidraulica_kw,
        "pot_electrica_kw": pot_electrica_kw,
    }

    # --------------------------------------------------------------------------
    # ETAPA 5: DESAIREACIÓN (Recibe corriente de Homogeneización)
    # --------------------------------------------------------------------------
    caudal_desair_in_kg_h = etapa_4["mass_flow_kg_h"]
    p_vacio = cfg["p_presion_vacio_kpa"]
    t_desair_in = cfg["p_temp_desair_in"]
    o2_in = cfg["p_o2_inicial_mgl"]

    t_ebull_aprox = 35.0 + (p_vacio * 1.5)
    flashing_inviable = (t_desair_in > t_ebull_aprox) and (p_vacio < 15.0)

    efic_remocion_o2 = min(98.0, max(85.0, 95.0 - (p_vacio - 7.0) * 0.5))
    o2_salida = o2_in * (1.0 - efic_remocion_o2 / 100.0)
    perdida_gases_kg_h = caudal_desair_in_kg_h * 0.0005
    caudal_desair_out_kg_h = caudal_desair_in_kg_h - perdida_gases_kg_h
    vol_desair_out_l_h = caudal_desair_out_kg_h / densidad_kg_l

    vol_util_tanque_l = (caudal_desair_in_kg_h / densidad_kg_m3) * (2.0 / 60.0) * 1000.0
    vol_total_tanque_l = vol_util_tanque_l / 0.35

    etapa_5 = {
        "caudal_out_kg_h": caudal_desair_out_kg_h,
        "vol_out_l_h": vol_desair_out_l_h,
        "o2_salida_mgl": o2_salida,
        "efic_remocion_pct": efic_remocion_o2,
        "vol_tanque_l": vol_total_tanque_l,
        "flashing_inviable": flashing_inviable,
        "temp_out_c": t_desair_in,
    }

    # --------------------------------------------------------------------------
    # ETAPA 6: PASTEURIZACIÓN MULTITUBULAR (Recibe corriente de Desaireación)
    # --------------------------------------------------------------------------
    flujo_past_l_h = etapa_5["vol_out_l_h"]
    flujo_past_m3_s = flujo_past_l_h / (1000.0 * 3600.0)
    flujo_past_kg_s = flujo_past_m3_s * densidad_kg_m3

    frac_solidos = cfg["p_brix"] / 100.0
    cp_zumo_j_kgk = (4.187 * (1.0 - frac_solidos) + 1.424 * frac_solidos) * 1000.0

    t_in_p = etapa_5["temp_out_c"]
    t_past = cfg["p_temp_past_c"]
    t_out_p = cfg["p_temp_past_out_c"]
    t_ret = cfg["p_tiempo_ret_s"]
    eta_reg = cfg["p_regen_pct"] / 100.0

    t_tras_reg = t_in_p + eta_reg * (t_past - t_in_p)
    q_cal_neto_w = flujo_past_kg_s * cp_zumo_j_kgk * (t_past - t_tras_reg)
    entalpia_vapor_j_kg = 500.0 * 4187.0
    flujo_vapor_kg_h = (q_cal_neto_w / entalpia_vapor_j_kg) * 3600.0

    diam_tubo_m = 0.0508
    area_tubo_m2 = (math.pi * (diam_tubo_m ** 2)) / 4.0
    vol_celda_m3 = (6000.0 / (1000.0 * 3600.0)) * 20.0
    long_celda_m = vol_celda_m3 / area_tubo_m2
    vel_tubo_m_s = flujo_past_m3_s / area_tubo_m2

    t_antes_glicol = t_past - eta_reg * (t_past - t_in_p)
    q_enf_neto_w = max(0.0, flujo_past_kg_s * cp_zumo_j_kgk * (t_antes_glicol - t_out_p))
    flujo_glicol_kg_h = (q_enf_neto_w / (3800.0 * 6.0)) * 3600.0

    valor_d_s = 3.0 * (10.0 ** (-(t_past - 80.0) / 7.0))
    reducciones_log = t_ret / valor_d_s
    es_esteril = reducciones_log >= 5.0

    temp_k = t_past + 273.15
    temp_ref_k = 90.0 + 273.15
    k_vitc = 0.0012 * math.exp((-95000.0 / 8.314) * ((1.0 / temp_k) - (1.0 / temp_ref_k)))
    retencion_vitc_pct = 100.0 * math.exp(-k_vitc * t_ret)
    vitc_out_mgl = cfg["p_vitc_in_mgl"] * (retencion_vitc_pct / 100.0)

    etapa_6 = {
        "flujo_vol_out_lh": flujo_past_l_h,
        "flujo_masico_kg_s": flujo_past_kg_s,
        "cp_zumo_j_kgk": cp_zumo_j_kgk,
        "pot_calentamiento_kw": q_cal_neto_w / 1000.0,
        "pot_enfriamiento_kw": q_enf_neto_w / 1000.0,
        "flujo_vapor_kg_h": flujo_vapor_kg_h,
        "flujo_glicol_kg_h": flujo_glicol_kg_h,
        "velocidad_tubo_m_s": vel_tubo_m_s,
        "longitud_celda_m": long_celda_m,
        "reducciones_log": reducciones_log,
        "producto_seguro": es_esteril,
        "alerta_sobrecarga": flujo_past_l_h > 6500.0,
        "retencion_vitc_pct": retencion_vitc_pct,
        "vitc_out_mgl": vitc_out_mgl,
        "temp_out_c": t_out_p,
    }

    # --------------------------------------------------------------------------
    # ETAPA 7: ENVASADO ASÉPTICO (Recibe zumo estéril frío de Pasteurización)
    # --------------------------------------------------------------------------
    flujo_env_lh = etapa_6["flujo_vol_out_lh"]
    merma_env_frac = cfg["p_merma_env_pct"] / 100.0

    botellas_teoricas_h = flujo_env_lh
    botellas_rechazo_env_h = botellas_teoricas_h * merma_env_frac
    botellas_utiles_env_h = math.floor(botellas_teoricas_h - botellas_rechazo_env_h)

    botellas_teoricas_dia = flujo_env_lh * horas_turno_env
    botellas_utiles_env_dia = math.floor(botellas_teoricas_dia * (1.0 - merma_env_frac))

    etapa_7 = {
        "flujo_entrada_lh": flujo_env_lh,
        "botellas_utiles_h": botellas_utiles_env_h,
        "rechazo_env_h": math.ceil(botellas_rechazo_env_h),
        "botellas_utiles_dia": botellas_utiles_env_dia,
    }

    # --------------------------------------------------------------------------
    # ETAPA 8: ETIQUETADO Y CONSOLIDACIÓN LOGÍSTICA (Recibe botellas de Etapa 7)
    # --------------------------------------------------------------------------
    merma_etiq_frac = cfg["p_merma_etiq_pct"] / 100.0

    # Base horaria
    botellas_in_h = etapa_7["botellas_utiles_h"]
    rechazo_etiq_h = botellas_in_h * merma_etiq_frac
    botellas_finales_h = math.floor(botellas_in_h - rechazo_etiq_h)

    # Base jornada de envasado (día)
    botellas_in_dia = etapa_7["botellas_utiles_dia"]
    rechazo_etiq_dia = botellas_in_dia * merma_etiq_frac
    botellas_finales_dia = math.floor(botellas_in_dia - rechazo_etiq_dia)
    bobinas_dia = botellas_in_dia / 90_000.0
    packs_dia = math.floor(botellas_finales_dia / 6)
    palets_dia = math.floor(packs_dia / 32)

    # Base anual (toda la campaña)
    botellas_finales_ano = botellas_finales_dia * dias_env
    packs_ano = math.floor(botellas_finales_ano / 6)
    palets_ano = math.floor(packs_ano / 32)
    bobinas_ano = (botellas_in_dia * dias_env) / 90_000.0

    etapa_8 = {
        "botellas_finales_h": botellas_finales_h,
        "botellas_finales_dia": botellas_finales_dia,
        "rechazo_etiq_dia": math.ceil(rechazo_etiq_dia),
        "bobinas_dia": bobinas_dia,
        "packs_dia": packs_dia,
        "palets_dia": palets_dia,
        "botellas_finales_ano": botellas_finales_ano,
        "packs_ano": packs_ano,
        "palets_ano": palets_ano,
        "bobinas_ano": bobinas_ano,
    }

    return {
        "e1": etapa_1,
        "e2": etapa_2,
        "e3": etapa_3,
        "e4": etapa_4,
        "e5": etapa_5,
        "e6": etapa_6,
        "e7": etapa_7,
        "e8": etapa_8,
    }


# ==============================================================================
# 3. INTERFAZ UNIFICADA STREAMLIT (MODALIDAD DE PLANTA)
# ==============================================================================
inicializar_estado()

st.title("🍊 Simulador Integral de Planta: Producción de Zumo de Naranja")
st.caption(
    "Modalidad de Planta Completa · Balances de materia, energía y logística acoplados en serie"
)

# --- PANEL LATERAL DE PARÁMETROS POR ETAPA ---
with st.sidebar:
    st.header("⚙️ Parámetros de Planta")
    st.button("↺ Restaurar Valores Base", on_click=restaurar_defaults, use_container_width=True)

    with st.expander("1. Selección, Lavado y Extracción", expanded=True):
        st.number_input("Producción objetivo (L/año)", min_value=10000.0, step=50000.0, key="p_prod_anual_l")
        st.number_input("Días de campaña (días/año)", min_value=1, max_value=365, step=1, key="p_dias_campana")
        st.number_input("Horas por turno extracción (h/día)", min_value=1.0, max_value=24.0, step=0.5, key="p_horas_turno_ext")
        st.number_input("Densidad del zumo (kg/L)", min_value=0.900, max_value=1.300, step=0.005, format="%.3f", key="p_densidad_kg_l")
        st.slider("Pulpa salida extractor (%)", 5.0, 25.0, step=0.5, key="p_pulpa_ext_pct")
        st.slider("Pulpa zumo comercial (%)", 1.0, 15.0, step=0.5, key="p_pulpa_com_pct")
        st.slider("Rendimiento 1.ª Selección (%)", 80.0, 100.0, step=0.5, key="p_rend_sel1_pct")
        st.slider("Rendimiento Lavado (%)", 90.0, 100.0, step=0.1, key="p_rend_lavado_pct")
        st.slider("Rendimiento 2.ª Selección (%)", 90.0, 100.0, step=0.1, key="p_rend_sel2_pct")
        st.slider("Rendimiento Extracción Zumo (%)", 30.0, 70.0, step=0.5, key="p_rend_ext_pct")
        st.slider("Fracción piel y semillas (%)", 25.0, 65.0, step=0.1, key="p_frac_piel_pct")
        st.slider("Fracción emulsión aceite (%)", 0.1, 3.0, step=0.1, key="p_frac_emulsion_pct")
        st.number_input("Agua por extractor (kg/h)", min_value=0.0, step=50.0, key="p_agua_ext_kg_h")
        st.number_input("Número de extractores (ud)", min_value=1, max_value=10, step=1, key="p_num_extractores")

    with st.expander("2. Tamizado y Enfriamiento"):
        st.slider("Eficiencia retención tamiz", 0.30, 0.98, step=0.01, key="p_efic_tamiz")
        st.slider("Temp. entrada enfriador (°C)", 15.0, 40.0, step=0.5, key="p_temp_enf_in")
        st.slider("Temp. salida enfriador (°C)", 1.0, 15.0, step=0.5, key="p_temp_enf_out")

    with st.expander("3. Almacenamiento Aséptico"):
        st.number_input("Cantidad de tanques", min_value=1, max_value=50, step=1, key="p_num_tanques")
        st.number_input("Capacidad por tanque (L)", min_value=5000.0, step=5000.0, key="p_cap_tanque_l")
        st.slider("Temp. almacenamiento (°C)", -3.0, 5.0, step=0.1, key="p_temp_alm_c")
        st.slider("Sobrepresión N₂ (bar)", 0.0, 1.0, step=0.05, key="p_presion_n2_bar")
        st.number_input("Días de envasado al año", min_value=1, max_value=365, step=5, key="p_dias_envasado")
        st.number_input("Horas por turno de envasado (h/día)", min_value=0.5, max_value=24.0, step=0.5, key="p_horas_turno_env")

    with st.expander("4. Homogeneización"):
        st.slider("Presión homogeneización (bar)", 100.0, 250.0, step=5.0, key="p_presion_homog_bar")
        st.slider("Eficiencia mecánica equipo", 0.70, 0.95, step=0.01, key="p_efic_homog")

    with st.expander("5. Desaireación"):
        st.slider("Presión de vacío (kPa)", 3.0, 50.0, step=0.5, key="p_presion_vacio_kpa")
        st.slider("Temp. entrada desaireador (°C)", 5.0, 50.0, step=1.0, key="p_temp_desair_in")
        st.slider("Oxígeno disuelto inicial (mg/L)", 5.0, 25.0, step=0.5, key="p_o2_inicial_mgl")

    with st.expander("6. Pasteurización"):
        st.slider("Sólidos solubles (°Brix)", 8.0, 16.0, step=0.2, key="p_brix")
        st.slider("Temp. pasteurización (°C)", 70.0, 105.0, step=1.0, key="p_temp_past_c")
        st.slider("Tiempo de retención (s)", 5.0, 45.0, step=1.0, key="p_tiempo_ret_s")
        st.slider("Temp. salida a envasado (°C)", 2.0, 15.0, step=0.5, key="p_temp_past_out_c")
        st.slider("Recuperación de calor (%)", 0.0, 75.0, step=5.0, key="p_regen_pct")

    with st.expander("7 y 8. Envasado y Etiquetado"):
        st.slider("Merma envasado aséptico (%)", 0.0, 10.0, step=0.5, key="p_merma_env_pct")
        st.slider("Rechazo en etiquetado (%)", 0.0, 5.0, step=0.1, key="p_merma_etiq_pct")

# Ejecutar cálculo integral
cfg = {k: st.session_state[k] for k in st.session_state if k.startswith("p_")}
res = calcular_planta(cfg)
e1, e2, e3, e4, e5, e6, e7, e8 = (
    res["e1"],
    res["e2"],
    res["e3"],
    res["e4"],
    res["e5"],
    res["e6"],
    res["e7"],
    res["e8"],
)

# --- ALERTAS GLOBALES DE CONSISTENCIA ---
if abs(e1["suma_fracciones_ext"] - 100.0) > 0.01:
    st.warning(
        f"⚠️ **Extracción:** Las fracciones de zumo, piel/semillas y emulsión suman "
        f"{fmt(e1['suma_fracciones_ext'])} % (deben sumar 100.00 %)."
    )
if e5["flashing_inviable"]:
    st.error(
        "⚠️ **Desaireación:** Combinación de vacío y temperatura provoca ebullición instantánea (*flashing*)."
    )
if not e6["producto_seguro"]:
    st.error(
        f"⚠️ **Pasteurización:** Reducción microbiana insuficiente ({fmt(e6['reducciones_log'])} log₁₀ < 5.0 log₁₀)."
    )
if e6["alerta_sobrecarga"]:
    st.warning(
        f"⚠️ **Pasteurización:** Caudal de línea ({fmt(e6['flujo_vol_out_lh'])} L/h) supera la capacidad nominal del equipo (6,500 L/h)."
    )

# --- INDICADORES GLOBALES DE PLANTA ---
st.subheader("📊 Indicadores Globales de la Línea de Producción")
g1, g2, g3, g4, g5, g6 = st.columns(6)
g1.metric("Recepción Naranja", f"{fmt(e1['naranja_recep_kg_h'])} kg/h")
g2.metric("Zumo Refinado", f"{fmt(e2['m_jugo_refinado_kg_h'])} kg/h")
g3.metric("Caudal Línea Aséptica", f"{fmt(e3['caudal_linea_l_h'])} L/h")
g4.metric("Carga Térmica Total", f"{fmt(e2['q_enfriamiento_kw'] + e6['pot_calentamiento_kw'] + e6['pot_enfriamiento_kw'])} kW")
g5.metric("Botellas Útiles / Jornada", f"{e8['botellas_finales_dia']:,} uds")
g6.metric("Palets Anuales", f"{e8['palets_ano']:,} palets")

st.markdown("---")

# --- TABLA DE CORRIENTES CONECTADAS ---
st.subheader("🔗 Balance de Corrientes Conectadas entre Etapas")
df_corrientes = pd.DataFrame(
    [
        {"Etapa": "1. Recepción de Naranja", "Flujo Másico (kg/h)": fmt(e1["naranja_recep_kg_h"]), "Flujo Volumétrico (L/h)": "—", "Temp. (°C)": "25.0", "Observación": f"Rendimiento global fruta→zumo: {fmt(e1['rendimiento_global_pct'])} %"},
        {"Etapa": "1. Salida Extracción (Zumo Bruto)", "Flujo Másico (kg/h)": fmt(e1["zumo_bruto_kg_h"]), "Flujo Volumétrico (L/h)": fmt(e1["zumo_bruto_l_h"]), "Temp. (°C)": "28.0", "Observación": f"Pulpa inicial: {fmt(cfg['p_pulpa_ext_pct'], 1)} %"},
        {"Etapa": "2. Salida Tamizado y Enfriamiento", "Flujo Másico (kg/h)": fmt(e2["m_jugo_refinado_kg_h"]), "Flujo Volumétrico (L/h)": fmt(e2["vol_refinado_l_h"]), "Temp. (°C)": fmt(e2["temp_salida_c"], 1), "Observación": f"Pulpa final: {fmt(e2['x_pulpa_final_pct'])} % | Residuo: {fmt(e2['m_pulpa_residuo_kg_h'])} kg/h"},
        {"Etapa": "3. Salida Tanques Asépticos", "Flujo Másico (kg/h)": fmt(e4["mass_flow_kg_h"]), "Flujo Volumétrico (L/h)": fmt(e3["caudal_linea_l_h"]), "Temp. (°C)": fmt(cfg["p_temp_alm_c"], 1), "Observación": f"Pico ocupación: {fmt(e3['pico_ocupacion_pct'], 1)} % ({fmt(e3['pico_ocupacion_l'], 0)} L)"},
        {"Etapa": "4. Salida Homogeneización", "Flujo Másico (kg/h)": fmt(e4["mass_flow_kg_h"]), "Flujo Volumétrico (L/h)": fmt(e4["vol_flow_l_h"]), "Temp. (°C)": fmt(cfg["p_temp_desair_in"], 1), "Observación": f"Presión: {fmt(cfg['p_presion_homog_bar'], 0)} bar | Potencia: {fmt(e4['pot_electrica_kw'])} kW"},
        {"Etapa": "5. Salida Desaireación", "Flujo Másico (kg/h)": fmt(e5["caudal_out_kg_h"]), "Flujo Volumétrico (L/h)": fmt(e5["vol_out_l_h"]), "Temp. (°C)": fmt(e5["temp_out_c"], 1), "Observación": f"O₂ residual: {fmt(e5['o2_salida_mgl'])} mg/L (-{fmt(e5['efic_remocion_pct'], 1)} %)"},
        {"Etapa": "6. Salida Pasteurización", "Flujo Másico (kg/h)": fmt(e6["flujo_masico_kg_s"] * 3600.0), "Flujo Volumétrico (L/h)": fmt(e6["flujo_vol_out_lh"]), "Temp. (°C)": fmt(e6["temp_out_c"], 1), "Observación": f"Inactivación: {fmt(e6['reducciones_log'])} log₁₀ | Vit. C: {fmt(e6['retencion_vitc_pct'], 1)} %"},
        {"Etapa": "7. Salida Envasado Aséptico", "Flujo Másico (kg/h)": "—", "Flujo Volumétrico (L/h)": fmt(e7["flujo_entrada_lh"]), "Temp. (°C)": fmt(e6["temp_out_c"], 1), "Observación": f"{e7['botellas_utiles_h']:,} botellas/h ({e7['botellas_utiles_dia']:,} botellas/jornada)"},
        {"Etapa": "8. Salida Etiquetado y Paletizado", "Flujo Másico (kg/h)": "—", "Flujo Volumétrico (L/h)": "—", "Temp. (°C)": "Ambiente", "Observación": f"{e8['botellas_finales_dia']:,} botellas/jornada → {e8['packs_dia']:,} packs → {e8['palets_dia']:,} palets"},
    ]
)
st.dataframe(df_corrientes, hide_index=True, use_container_width=True)

st.markdown("---")

# --- DESGLOSE UNIFORME POR ETAPA ---
st.subheader("🏭 Resultados Detallados por Sección del Proceso")

with st.container(border=True):
    st.markdown("#### Etapa 1 · Selección, Lavado y Extracción")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Naranja Recepcionada", f"{fmt(e1['naranja_recep_kg_h'])} kg/h")
    c2.metric("Zumo Bruto Obtenido", f"{fmt(e1['zumo_bruto_kg_h'])} kg/h")
    c3.metric("Emulsión + Agua (Aceite)", f"{fmt(e1['emulsion_diluida_kg_h'])} kg/h")
    c4.metric("Subproductos Sólidos", f"{fmt(e1['subproductos_solidos_kg_h'])} kg/h")

with st.container(border=True):
    st.markdown("#### Etapa 2 · Tamizado y Enfriamiento")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Zumo Refinado Salida", f"{fmt(e2['m_jugo_refinado_kg_h'])} kg/h")
    c2.metric("Pulpa Retenida (Residuo)", f"{fmt(e2['m_pulpa_residuo_kg_h'])} kg/h")
    c3.metric("Pulpa Final en Zumo", f"{fmt(e2['x_pulpa_final_pct'])} %")
    c4.metric("Carga Térmica Enfriamiento", f"{fmt(e2['q_enfriamiento_kw'])} kW")

with st.container(border=True):
    st.markdown("#### Etapa 3 · Almacenamiento en Tanques Asépticos")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Capacidad Total Almacén", f"{fmt(e3['cap_total_l'], 0)} L")
    c2.metric("Pico de Ocupación Anual", f"{fmt(e3['pico_ocupacion_pct'], 1)} %", f"{fmt(e3['pico_ocupacion_l'], 0)} L", delta_color="off")
    c3.metric("Caudal a Línea Aséptica", f"{fmt(e3['caudal_linea_l_h'])} L/h")
    c4.metric("Solución CIP por Tanque", f"{fmt(e3['cip_vol_l'])} L", f"NaOH: {fmt(e3['cip_naoh_kg'])} kg | HNO₃: {fmt(e3['cip_hno3_kg'])} kg", delta_color="off")
    df_hist = pd.DataFrame(e3["historial"]).set_index("Día")
    df_hist["Capacidad Máxima (L)"] = e3["cap_total_l"]
    st.line_chart(df_hist)

with st.container(border=True):
    st.markdown("#### Etapa 4 · Homogeneización")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Caudal Volumétrico", f"{fmt(e4['vol_flow_l_h'])} L/h")
    c2.metric("Caudal Másico", f"{fmt(e4['mass_flow_kg_h'])} kg/h")
    c3.metric("Potencia Hidráulica", f"{fmt(e4['pot_hidraulica_kw'])} kW")
    c4.metric("Potencia Eléctrica", f"{fmt(e4['pot_electrica_kw'])} kW")

with st.container(border=True):
    st.markdown("#### Etapa 5 · Desaireación")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Zumo Desaireado Salida", f"{fmt(e5['caudal_out_kg_h'])} kg/h")
    c2.metric("Oxígeno Disuelto Residual", f"{fmt(e5['o2_salida_mgl'])} mg/L", f"-{fmt(e5['efic_remocion_pct'], 1)} %")
    c3.metric("Volumen Tanque Vacío", f"{fmt(e5['vol_tanque_l'], 1)} L")
    c4.metric("Presión de Vacío", f"{fmt(cfg['p_presion_vacio_kpa'], 1)} kPa")

with st.container(border=True):
    st.markdown("#### Etapa 6 · Pasteurización Multitubular")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Potencia Calentamiento", f"{fmt(e6['pot_calentamiento_kw'])} kW", f"Vapor: {fmt(e6['flujo_vapor_kg_h'])} kg/h", delta_color="off")
    c2.metric("Potencia Enfriamiento", f"{fmt(e6['pot_enfriamiento_kw'])} kW", f"Glicol: {fmt(e6['flujo_glicol_kg_h'])} kg/h", delta_color="off")
    c3.metric("Inactivación S. cerevisiae", f"{fmt(e6['reducciones_log'])} log₁₀")
    c4.metric("Retención Vitamina C", f"{fmt(e6['retencion_vitc_pct'])} %", f"{fmt(e6['vitc_out_mgl'], 1)} mg/L", delta_color="off")

with st.container(border=True):
    st.markdown("#### Etapa 7 · Envasado Aséptico (Botellas PET 1 L)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Caudal Recibido", f"{fmt(e7['flujo_entrada_lh'])} L/h")
    c2.metric("Botellas Útiles / Hora", f"{e7['botellas_utiles_h']:,} uds/h")
    c3.metric("Merma Envasado / Hora", f"{e7['rechazo_env_h']:,} uds/h")
    c4.metric("Botellas Útiles / Jornada", f"{e7['botellas_utiles_dia']:,} uds/día")

with st.container(border=True):
    st.markdown("#### Etapa 8 · Etiquetado y Consolidación Logística")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Botellas Finales / Jornada", f"{e8['botellas_finales_dia']:,} uds")
    c2.metric("Packs (6 uds) / Jornada", f"{e8['packs_dia']:,} packs")
    c3.metric("Palets (32 packs) / Jornada", f"{e8['palets_dia']:,} palets")
    c4.metric("Bobinas Etiquetas / Campaña", f"{fmt(e8['bobinas_ano'], 3)} bobinas")
