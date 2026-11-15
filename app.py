# -*- coding: utf-8 -*-
"""Simulador de balance de materia - Planta de zumo de naranja (Streamlit)."""

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Balance de materia - Zumo de naranja", layout="wide")

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

# (clave, etiqueta, paso, formato)
ETIQUETAS = [
    ("produccion_anual_l", "Producción zumo comercial (l/año)", 10000.0, "%.2f"),
    ("dias_campana", "Días de campaña extracción (días/año)", 1.0, "%.2f"),
    ("horas_turno", "Horas por turno (h/día)", 1.0, "%.2f"),
    ("densidad_zumo", "Densidad del zumo (kg/l)", 0.001, "%.3f"),
    ("pulpa_extractor_pct", "Pulpa salida extractor (%)", 0.1, "%.2f"),
    ("pulpa_comercial_pct", "Pulpa zumo comercial (%)", 0.1, "%.2f"),
    ("rend_sel_1_pct", "Rendimiento 1.ª Selección (%)", 0.1, "%.2f"),
    ("rend_lavado_pct", "Rendimiento Lavado (%)", 0.1, "%.2f"),
    ("rend_sel_2_pct", "Rendimiento 2.ª Selección (%)", 0.1, "%.2f"),
    ("rend_extraccion_pct", "Rendimiento Extracción Zumo (%)", 0.1, "%.2f"),
    ("frac_piel_semillas_pct", "Fracción Piel y Semillas (%)", 0.1, "%.2f"),
    ("frac_emulsion_pct", "Fracción Emulsión Aceite (%)", 0.1, "%.2f"),
    ("agua_extractor_kg_h", "Agua por extractor (kg/h)", 10.0, "%.2f"),
    ("num_extractores", "Número de extractores (ud)", 1.0, "%.2f"),
]


# ==============================================================================
# 2. MOTOR DE CÁLCULO
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

    # 1.ª Selección
    m_ent_sel_1 = m_ent_lavado / (p["rend_sel_1_pct"] / 100.0)
    m_destrio_1 = m_ent_sel_1 - m_ent_lavado

    pulpa_txt = f"{p['pulpa_extractor_pct']:g}% pulpa"
    corrientes = [
        ("1. Naranja recepcionada (Entrada 1ª Sel.)", m_ent_sel_1, False),
        ("      ↳ Destrío 1ª Selección", m_destrio_1, True),
        ("2. Naranja a Lavado", m_ent_lavado, False),
        ("      ↳ Merma / impurezas Lavado", m_merma_lavado, True),
        ("3. Naranja a 2ª Selección", m_ent_sel_2, False),
        ("      ↳ Destrío 2ª Selección", m_destrio_2, True),
        ("4. Naranja apta (Entrada Extracción)", m_naranja_ext, False),
        (f"      ↳ Salida Zumo bruto ({pulpa_txt})", m_zumo_bruto, True),
        ("      ↳ Salida Piel y semillas", m_piel_semillas, True),
        ("      ↳ Salida Emulsión oleosa pura", m_emulsion_pura, True),
        ("      ↳ Agua añadida en extractores", m_agua_ext, True),
    ]

    tabla = [
        {
            "nombre": nombre,
            "sub": es_sub,
            "kg_ano": kg_ano,
            "kg_dia": kg_ano / dias,
            "kg_h": kg_ano / horas_anuales,
        }
        for nombre, kg_ano, es_sub in corrientes
    ]

    enlaces = {
        "zumo_bruto_kg_h": m_zumo_bruto / horas_anuales,
        "emulsion_diluida_kg_h": (m_emulsion_pura + m_agua_ext) / horas_anuales,
        "subproductos_solidos_kg_h": (
            m_piel_semillas + m_destrio_1 + m_destrio_2 + m_merma_lavado
        ) / horas_anuales,
        "rendimiento_global_pct": (m_zumo_bruto / m_ent_sel_1) * 100.0,
        "suma_fracciones_ext_pct": p["rend_extraccion_pct"]
        + p["frac_piel_semillas_pct"]
        + p["frac_emulsion_pct"],
    }

    return {"tabla": tabla, "enlaces": enlaces}


# ==============================================================================
# 3. INTERFAZ STREAMLIT
# ==============================================================================
def restaurar_base():
    for clave, valor in LINEA_BASE.items():
        st.session_state[clave] = valor


# Valores iniciales (solo la primera vez)
for clave, valor in LINEA_BASE.items():
    st.session_state.setdefault(clave, valor)

st.title("🍊 Balance de materia · Planta de zumo de naranja")
st.caption("Modifica los parámetros operativos en la barra lateral; los resultados se actualizan al instante.")

with st.sidebar:
    st.header("Parámetros operativos")
    params = {}
    for clave, etiqueta, paso, fmt in ETIQUETAS:
        params[clave] = st.number_input(
            etiqueta, key=clave, step=paso, format=fmt
        )
    st.button("↺ Restaurar base", on_click=restaurar_base, use_container_width=True)

# Validaciones
if any(v <= 0 for v in params.values()):
    st.error("Todos los valores deben ser mayores a 0.")
    st.stop()
if params["pulpa_comercial_pct"] > params["pulpa_extractor_pct"]:
    st.error("La pulpa comercial no puede superar la del extractor.")
    st.stop()
if params["pulpa_extractor_pct"] >= 100 or params["pulpa_comercial_pct"] >= 100:
    st.error("Los porcentajes de pulpa deben ser menores al 100%.")
    st.stop()

base_res = resolver_balance(LINEA_BASE)
res = resolver_balance(params)
enl = res["enlaces"]

if abs(enl["suma_fracciones_ext_pct"] - 100.0) > 0.01:
    st.warning(
        f"Las fracciones del extractor suman {enl['suma_fracciones_ext_pct']:.2f}% "
        "(deben sumar 100%)."
    )

# Enlaces con el resto de la planta
st.subheader("Enlaces con el resto de la planta")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Rendimiento global", f"{enl['rendimiento_global_pct']:.2f} %")
c2.metric("Zumo bruto", f"{enl['zumo_bruto_kg_h']:,.2f} kg/h")
c3.metric("Emulsión + Agua", f"{enl['emulsion_diluida_kg_h']:,.2f} kg/h")
c4.metric("Subproductos sólidos", f"{enl['subproductos_solidos_kg_h']:,.2f} kg/h")

# Tabla principal
filas = []
for f, fb in zip(res["tabla"], base_res["tabla"]):
    diff = (f["kg_ano"] - fb["kg_ano"]) / fb["kg_ano"] * 100.0
    filas.append(
        {
            "Corriente / Etapa": f["nombre"],
            "Flujo (kg/año)": f["kg_ano"],
            "Flujo (kg/día)": f["kg_dia"],
            "Flujo (kg/h)": f["kg_h"],
            "Var. vs Base (%)": 0.0 if abs(diff) < 1e-4 else diff,
            "_sub": f["sub"],
        }
    )

df = pd.DataFrame(filas)
es_sub = df.pop("_sub")


def resaltar_principales(fila):
    estilo = "font-weight:bold;background-color:#f4f6f8;color:#111;"
    return [("" if es_sub[fila.name] else estilo)] * len(fila)


styler = (
    df.style.apply(resaltar_principales, axis=1)
    .format(
        {
            "Flujo (kg/año)": "{:,.2f}",
            "Flujo (kg/día)": "{:,.2f}",
            "Flujo (kg/h)": "{:,.2f}",
            "Var. vs Base (%)": "{:+.2f} %",
        }
    )
)

st.subheader("Balance por corriente")
st.dataframe(styler, use_container_width=True, hide_index=True)

st.download_button(
    "⬇ Descargar tabla (CSV)",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="balance_materia.csv",
    mime="text/csv",
)
