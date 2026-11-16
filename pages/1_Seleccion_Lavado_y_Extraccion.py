"""
Simulador Interactivo de Proceso: Selección, Lavado y Extracción
Planta de Zumo de Naranja (1.500.000 l/año) - versión Streamlit
Ejecutar:  streamlit run app.py
"""

import pandas as pd
import streamlit as st



# ==============================================================================
# 1. LÍNEA BASE DEL PROYECTO
# ==============================================================================
LINEA_BASE = {
    "produccion_anual_l": 1500000.0,
    "dias_campana": 87.0,
    "horas_turno": 8.0,
    "densidad_zumo": 1.045,
    "pulpa_extractor_pct": 12.0,
    "pulpa_comercial_pct": 8.0,
    "rend_sel_1_pct": 97.0,
    "rend_lavado_pct": 99.5,
    "rend_sel_2_pct": 99.5,
    "rend_extraccion_pct": 50.0,
    "frac_piel_semillas_pct": 49.3,
    "frac_emulsion_pct": 0.7,
    "agua_extractor_kg_h": 1000.0,
    "num_extractores": 1.0,
}

ETIQUETAS_PARAMETROS = [
    ("produccion_anual_l", "Producción de Zumo Comercial (l/año)"),
    ("dias_campana", "Días de Campaña Extracción (días/año)"),
    ("horas_turno", "Horas por Turno (h/día)"),
    ("densidad_zumo", "Densidad del Zumo (kg/l)"),
    ("pulpa_extractor_pct", "Pulpa Salida Extractor (%)"),
    ("pulpa_comercial_pct", "Pulpa Zumo Comercial (%)"),
    ("rend_sel_1_pct", "Rendimiento 1.ª Selección (%)"),
    ("rend_lavado_pct", "Rendimiento Lavado (%)"),
    ("rend_sel_2_pct", "Rendimiento 2.ª Selección (%)"),
    ("rend_extraccion_pct", "Rendimiento Extracción Zumo (%)"),
    ("frac_piel_semillas_pct", "Fracción Piel y Semillas (%)"),
    ("frac_emulsion_pct", "Fracción Emulsión Aceite (%)"),
    ("agua_extractor_kg_h", "Agua por extractor (kg/h)"),
    ("num_extractores", "Número de extractores (ud)"),
]


# ==============================================================================
# 2. MOTOR DE CÁLCULO (idéntico al de la versión tkinter)
# ==============================================================================
def resolver_balance(p: dict) -> dict:
    dias = p["dias_campana"]
    horas_dia = p["horas_turno"]
    horas_anuales = dias * horas_dia

    m_zumo_comercial = p["produccion_anual_l"] * p["densidad_zumo"]
    rend_tamiz = (1.0 - p["pulpa_extractor_pct"] / 100.0) / (
        1.0 - p["pulpa_comercial_pct"] / 100.0
    )
    m_zumo_bruto = m_zumo_comercial / rend_tamiz

    # Extracción
    m_naranja_ext = m_zumo_bruto / (p["rend_extraccion_pct"] / 100.0)
    m_piel_semillas = m_naranja_ext * (p["frac_piel_semillas_pct"] / 100.0)
    m_emulsion_pura = m_naranja_ext * (p["frac_emulsion_pct"] / 100.0)
    m_agua_ext = p["agua_extractor_kg_h"] * p["num_extractores"] * horas_anuales

    # 2.ª Selección
    m_ent_sel_2 = m_naranja_ext / (p["rend_sel_2_pct"] / 100.0)
    m_destrio_2 = m_ent_sel_2 - m_naranja_ext

    # Lavado
    m_ent_lavado = m_ent_sel_2 / (p["rend_lavado_pct"] / 100.0)
    m_merma_lavado = m_ent_lavado - m_ent_sel_2

    # 1.ª Selección (Recepción)
    m_ent_sel_1 = m_ent_lavado / (p["rend_sel_1_pct"] / 100.0)
    m_destrio_1 = m_ent_sel_1 - m_ent_lavado

    corrientes_anuales = [
        ("1. Naranja recepcionada (Entrada 1ª Sel.)", m_ent_sel_1),
        ("   -> Destrío 1ª Selección", m_destrio_1),
        ("2. Naranja a Lavado", m_ent_lavado),
        ("   -> Merma / impurezas Lavado", m_merma_lavado),
        ("3. Naranja a 2ª Selección", m_ent_sel_2),
        ("   -> Destrío 2ª Selección", m_destrio_2),
        ("4. Naranja apta (Entrada Extracción)", m_naranja_ext),
        ("   -> Salida Zumo bruto (12% pulpa)", m_zumo_bruto),
        ("   -> Salida Piel y semillas", m_piel_semillas),
        ("   -> Salida Emulsión oleosa pura", m_emulsion_pura),
        ("   -> Agua añadida en extractores", m_agua_ext),
    ]

    tabla = [
        {
            "nombre": nombre,
            "kg_ano": kg_ano,
            "kg_dia": kg_ano / dias,
            "kg_h": kg_ano / horas_anuales,
        }
        for nombre, kg_ano in corrientes_anuales
    ]

    enlaces = {
        "zumo_bruto_kg_h": m_zumo_bruto / horas_anuales,
        "emulsion_diluida_kg_h": (m_emulsion_pura + m_agua_ext) / horas_anuales,
        "subproductos_solidos_kg_h": (
            m_piel_semillas + m_destrio_1 + m_destrio_2 + m_merma_lavado
        )
        / horas_anuales,
        "rendimiento_global_pct": (m_zumo_bruto / m_ent_sel_1) * 100.0,
        "zumo_l_ano": p["produccion_anual_l"],
        "zumo_l_dia": p["produccion_anual_l"] / dias,
        "zumo_l_h": p["produccion_anual_l"] / horas_anuales,
        "zumo_kg_dia": m_zumo_comercial / dias,
        "suma_fracciones_ext_pct": p["rend_extraccion_pct"]
        + p["frac_piel_semillas_pct"]
        + p["frac_emulsion_pct"],
    }
    return {"tabla": tabla, "enlaces": enlaces, "horas_turno": horas_dia}


def validar(p: dict) -> list:
    errores = []
    for clave, etiqueta in ETIQUETAS_PARAMETROS:
        if p[clave] <= 0:
            errores.append(f"'{etiqueta}' debe ser mayor que 0.")
    if p["pulpa_extractor_pct"] >= 100 or p["pulpa_comercial_pct"] >= 100:
        errores.append("Los porcentajes de pulpa deben ser menores al 100 %.")
    if p["pulpa_comercial_pct"] > p["pulpa_extractor_pct"]:
        errores.append(
            "La pulpa comercial no puede ser mayor que la pulpa a la salida del extractor."
        )
    return errores


def fmt(x: float, dec: int = 2) -> str:
    """Formato español: 1.234.567,89"""
    s = f"{x:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


# ==============================================================================
# 3. INTERFAZ STREAMLIT
# ==============================================================================
# Estado inicial de los parámetros
for k, v in LINEA_BASE.items():
    st.session_state.setdefault(k, v)


def restaurar_base():
    for k, v in LINEA_BASE.items():
        st.session_state[k] = v


st.title("🍊 Simulador de Proceso: Selección, Lavado y Extracción")
st.caption("Planta de Zumo de Naranja · Balance de materia")

# --- Barra lateral: parámetros editables ---
with st.sidebar:
    st.header("Parámetros Operativos")
    params = {}
    for clave, etiqueta in ETIQUETAS_PARAMETROS:
        params[clave] = st.number_input(
            etiqueta, key=clave, format="%g", step=None
        )
    st.button("↺ Restaurar Línea Base", on_click=restaurar_base, use_container_width=True)

errores = validar(params)
if errores:
    for e in errores:
        st.error(e)
    st.stop()

base = resolver_balance(LINEA_BASE)
res = resolver_balance(params)
enl = res["enlaces"]

# Alerta de cierre de balance en extracción
suma_ext = enl["suma_fracciones_ext_pct"]
if abs(suma_ext - 100.0) > 0.01:
    st.warning(
        f"⚠ Aviso de balance: Extracción + Piel/Semillas + Emulsión suman "
        f"{fmt(suma_ext)} % (debe ser 100,00 %)."
    )

tab1, tab2 = st.tabs(
    ["1. Balance de Corrientes y Variación", "2. Simulación Acumulada por Turno"]
)

# --- Pestaña 1 ---
with tab1:
    filas = []
    for f, fb in zip(res["tabla"], base["tabla"]):
        diff = (f["kg_ano"] - fb["kg_ano"]) / fb["kg_ano"] * 100.0
        filas.append(
            {
                "Corriente / Etapa del Proceso": f["nombre"],
                "Flujo (kg/año)": fmt(f["kg_ano"]),
                "Flujo (kg/día)": fmt(f["kg_dia"]),
                "Flujo (kg/h)": fmt(f["kg_h"]),
                "Var. vs Base": "0,00 %" if abs(diff) < 1e-4 else f"{diff:+.2f} %".replace(".", ","),
            }
        )
    st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)

    st.subheader("Producción de Zumo Comercial")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Anual (l/año)", fmt(enl["zumo_l_ano"]))
    c2.metric("Diaria (l/día)", fmt(enl["zumo_l_dia"]))
    c3.metric("Horaria (l/h)", fmt(enl["zumo_l_h"]))
    c4.metric("Diaria masa (kg/día)", fmt(enl["zumo_kg_dia"]))

    st.subheader("Puntos de Enlace con el Resto de la Planta")
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Rendimiento global fruta → zumo bruto", f"{fmt(enl['rendimiento_global_pct'])} %")
    e2.metric("A Tamizado/Pasteurización (kg/h)", fmt(enl["zumo_bruto_kg_h"]))
    e3.metric("A Línea Aceite: Emulsión + Agua (kg/h)", fmt(enl["emulsion_diluida_kg_h"]))
    e4.metric("A Subproductos Sólidos (kg/h)", fmt(enl["subproductos_solidos_kg_h"]))

# --- Pestaña 2 ---
with tab2:
    t = res["tabla"]
    h_recep = t[0]["kg_h"]
    h_destrios = t[1]["kg_h"] + t[3]["kg_h"] + t[5]["kg_h"]
    h_ext = t[6]["kg_h"]
    h_zumo = t[7]["kg_h"]
    h_piel = t[8]["kg_h"]
    h_emul_dil = t[9]["kg_h"] + t[10]["kg_h"]

    filas_turno = []
    for h in range(1, int(res["horas_turno"]) + 1):
        filas_turno.append(
            {
                "Tiempo": f"Hora {h}",
                "Recepción Acum. (kg)": fmt(h_recep * h),
                "Destríos/Merma (kg)": fmt(h_destrios * h),
                "A Extracción (kg)": fmt(h_ext * h),
                "Zumo Bruto 12% (kg)": fmt(h_zumo * h),
                "Piel/Semillas (kg)": fmt(h_piel * h),
                "Emulsión+Agua (kg)": fmt(h_emul_dil * h),
            }
        )
    st.dataframe(pd.DataFrame(filas_turno), hide_index=True, use_container_width=True)
