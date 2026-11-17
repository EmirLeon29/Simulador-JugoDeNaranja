"""
Simulador Interactivo de Proceso: Selección, Lavado y Extracción
Planta de Jugo de Naranja (1.500.000 l/año) - versión Streamlit
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
    ("produccion_anual_l", "Producción de Jugo Comercial (l/año)"),
    ("dias_campana", "Días de Campaña Extracción (días/año)"),
    ("horas_turno", "Horas por Turno (h/día)"),
    ("densidad_zumo", "Densidad del Jugo (kg/l)"),
    ("pulpa_extractor_pct", "Pulpa Salida Extractor (%)"),
    ("pulpa_comercial_pct", "Pulpa Jugo Comercial (%)"),
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
        ("   -> Salida Jugo bruto (12% pulpa)", m_zumo_bruto),
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
st.caption("Planta de Jugo de Naranja · Balance de materia")

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

tab1, tab2, tab3 = st.tabs(
    ["1. Balance de Corrientes y Variación", "2. Simulación Acumulada por Turno", "3. Articulo"]
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

    st.subheader("Producción de Jugo Comercial")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Anual (l/año)", fmt(enl["zumo_l_ano"]))
    c2.metric("Diaria (l/día)", fmt(enl["zumo_l_dia"]))
    c3.metric("Horaria (l/h)", fmt(enl["zumo_l_h"]))
    c4.metric("Diaria masa (kg/día)", fmt(enl["zumo_kg_dia"]))

    st.subheader("Puntos de Enlace con el Resto de la Planta")
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Rendimiento global fruta → jugo bruto", f"{fmt(enl['rendimiento_global_pct'])} %")
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
                "Jugo Bruto 12% (kg)": fmt(h_zumo * h),
                "Piel/Semillas (kg)": fmt(h_piel * h),
                "Emulsión+Agua (kg)": fmt(h_emul_dil * h),
            }
        )
    st.dataframe(pd.DataFrame(filas_turno), hide_index=True, use_container_width=True)


# --- Pestaña 3 ---
with tab3:
    st.markdown("<h3 style='text-align: center;'>Seleccion, Lavado y Extracción</h3>", unsafe_allow_html=True)
    st.markdown(" ")
    st.markdown("**Selección y Clasificación.** Esta operación preliminar tiene como objetivo garantizar la homogeneidad de la materia prima y evitar la contaminación de los lotes. El proceso inicia con una inspección visual y manual sobre bandas transportadoras de rodillos los cuales hacen girar la fruta para exponer toda su superficie con el fin de descartar naranjas podridas, dañadas mecánicamente o inmaduras. Posteriormente, la fruta pasa por clasificadores mecánicos (de rodillos divergentes o tambores perforados) que la agrupan por tamaño, asegurando que cada pieza se ajuste a las dimensiones exactas de los equipos de extracción. ")
    col1, col2, col3 = st.columns([3, 2, 3])

        with col2:
            st.image("images/lavadodenaranja.webp", use_container_width=True)
    
    st.markdown(" ")
    st.markdown("**Lavado y Desinfección.** Para eliminar residuos de tierra, ceras, pesticidas y reducir la carga microbiana de la cáscara, la naranja se somete a un tratamiento combinado de acción física y química. Primero, ingresa a tinas de inmersión con agitación por inyección de aire que ablandan y desprenden la suciedad adherida. A continuación, avanza por túneles de lavado donde cepillos rotatorios de cerdas suaves (polipropileno o nylon) y aspersores de agua a presión limpian la epidermis sin dañarla. Simultáneamente, se aplican soluciones desinfectantes a base de hipoclorito de sodio o dióxido de cloro bajo parámetros controlados de concentración y tiempo de contacto, garantizando la inocuidad antes del exprimido.")
    st.markdown(" ")
    st.markdown("**Extracción.** En esta etapa se separa la fase líquida (jugo y pulpa) de los componentes sólidos estructurales del fruto. Utilizando sistemas de extracción rotatoria, la naranja es seccionada por la mitad mediante cuchillas estacionarias y cada hemisferio es presionado contra cabezales giratorios acanalados que giran a velocidades controladas. Este diseño reproduce el principio del exprimido manual a nivel industrial, permitiendo regular la presión ejercida para obtener un alto rendimiento de jugo sin exprimir en exceso el albedo o el flavedo, evitando así el amargor y el exceso de aceites esenciales en el producto.")
    st.markdown(" ")
    st.markdown("<h3 style='text-align: center;'>Proceso de Simulación</h3>", unsafe_allow_html=True)
    st.markdown("Para realizar la simulación de estos pasos unitarios se utilizó principalmente la bibliografía “Diseño y Dimensionamiento De Una Línea de Elaboración de Zumo De Naranja Con Capacidad De 1,500,000 litros/año En Palma Del Río, Córdoba” siendo una tesis de la universidad politécnica de madrid, en la cual nos plantea el proceso para producir jugo de naranja, además de utilizar este documento para realizar los cálculos de la selección, lavado y extracción se optó por el uso de dos principales uso de IA´s “Gemini IA y Claude”.")
    st.markdown("Se utilizaron las siguientes fórmulas:")

    with st.container(border=True):
        st.markdown("**Horas anuales de operación:**")
        st.latex(r"H_{\text{anuales}} = D_{\text{campaña}} \times H_{\text{turno}}")
    with st.container(border=True):
        st.markdown("**Producción volumétrica diaria y horaria de zumo comercial:**")
        st.latex(r"V_{\text{día}} = \frac{V_{\text{anual}}}{D_{\text{campaña}}}")
        st.latex(r"V_{\text{h}} = \frac{V_{\text{anual}}}{D_{\text{anuales}}}")
    with st.container(border=True):
        st.markdown("**Flujo másico de zumo comercial (anual y diario):**")
        st.latex(r"m_{\text{jugo comercial}} = V_{\text{anual}} \times \rho")
        st.latex(r"m_{\text{jugo, día}} = \frac{m_{\text{jugo comercial}}}{D_{\text{campaña}}}")
    with st.container(border=True):
        st.markdown("**Rendimiento másico del tamizado:**")
        st.latex(r"\eta_{\text{tamiz}} = \frac{1 - \frac{\%\text{Pulpa}_{\text{extractor}}}{100}}{1 - \frac{\%\text{Pulpa}_{\text{comercial}}}{100}}") 
    with st.container(border=True):
        st.markdown("**Masa anual de jugo bruto a la salida del extractor:**")
        st.latex(r"m_{\text{jugo bruto}} = \frac{m_{\text{jugo comercial}}}{\eta_{\text{tamiz}}}") 
    with st.container(border=True):
        st.markdown("**Naranja apta requerida a la entrada de extracción:**")
        st.latex(r"m_{\text{naranja ext}} = \frac{m_{\text{jugo bruto}}}{\eta_{\text{ext}} / 100}") 
    with st.container(border=True):
        st.markdown("**Subproducto sólido (piel, segmentos del fruto y semillas):**")
        st.latex(r"m_{\text{piel y semillas}} = m_{\text{naranja ext}} \times \left(\frac{f_{\text{piel y semillas}}}{100}\right)")
    with st.container(border=True):
        st.markdown("**Agua auxiliar añadida en los extractores:**")
        st.latex(r"m_{\text{agua ext}} = \dot{m}_{\text{agua/extractor}} \times N_{\text{extractores}} \times H_{\text{anuales}}") 
    with st.container(border=True):
        st.markdown("**Verificación de cierre de balance de la fruta en extracción:**")
        st.latex(r"\Sigma_{\text{ext}} = \eta_{\text{ext}} + f_{\text{piel y semillas}} + f_{\text{emulsión}} = 100\%")
    with st.container(border=True):
        st.markdown("**Lavado:**")
        st.latex(r"m_{\text{ent lavado}} = \frac{m_{\text{ent sel 2}}}{\eta_{\text{lavado}} / 100}") 
    with st.container(border=True):
        st.markdown("**Flujos másicos diario y horario:**")
        st.latex(r"\dot{m}_{i,\text{día}} = \frac{m_{i,\text{año}}}{D_{\text{campaña}}}")
        st.latex(r"\dot{m}_{i,\text{h}} = \frac{m_{i,\text{año}}}{H_{\text{anuales}}}")
    with st.container(border=True):
        st.markdown("**Rendimiento global de fruta recepcionada a jugo bruto:**")
        st.latex(r"\eta_{\text{global}} = \left(\frac{m_{\text{jugo bruto}}}{m_{\text{recepción}}}\right) \times 100")
    with st.container(border=True):
        st.markdown("**Caudales horarios de enlace con el resto de la planta:**")
        st.latex(r"\dot{m}_{\text{jugo bruto, h}} = \frac{m_{\text{jugo bruto}}}{H_{\text{anuales}}}") 
        st.latex(r"\dot{m}_{\text{emulsión diluida, h}} = \frac{m_{\text{emulsión pura}} + m_{\text{agua ext}}}{H_{\text{anuales}}}") 
        st.latex(r"\dot{m}_{\text{subproductos sólidos, h}} = \frac{m_{\text{piel y semillas}} + m_{\text{destrío 1}} + m_{\text{destrío 2}} + m_{\text{merma lavado}}}{H_{\text{anuales}}}")
    with st.container(border=True):
        st.markdown("**Simulación acumulada hora a hora en un turno:**")
        st.latex(r"M_{i,\text{acum}}(h) = \dot{m}_{i,\text{h}} \times h")
        
    st.markdown(" ")
    st.markdown("<h3 style='text-align: center;'>Prompts utilizados para la Inteligencia Artificial</h3>", unsafe_allow_html=True)
    st.markdown("En donde para la ia de Gemini IA se le dio el siguiente prompt.")
    st.markdown("“Buen dia, señorita gemini ia, requiero de su ayuda para mi siguiente proyecto, necesito realizar un código en python de las operaciones de la Selección, Lavado y Extracción del proceso de jugo de naranja, necesito que este código pueda modificar unas variables de entrada que sean Producción de Jugo Comercial en litros/año, Días de Campaña Extracción en días/año, Horas por Turno en horas/día, Densidad del Jugo en kilogramos/litros, Pulpa Salida Extractor (%), Pulpa Jugo Comercial (%), Rendimiento por Sección (%), Rendimiento Lavado (%), Fracción Piel y Semillas (%), Fracción Emulsión Aceite (%), Agua por extractor (kg/h), Número de extractores (ud), recuerda que este código lo debo de correr en local en la app de Visual Code Studio para verificar y modificar el código en lo que requiera.”")
    st.markdown("Y mientras para el uso que se le dio a la IA de Claude se realizó el siguientes prompts, en donde uno se usó para la crear la página web mientras que el otros para los ajustes necesarios para hacerla funcionar.")
    st.markdown("“Hola Claude tengo unos código listos para ejecutar en una página web, pero me puedes ayudar a crear los archivos necesarios para crear y ejecutar la página por medio de un link, ajustarlos para funcionar con la librería biblioteca Streamlit, y en github, por favor y gracias”")
    st.markdown("“Hola, Claude deidad, necesito que adaptes este código  para poder integrarlo a la biblioteca de Streamlit, adjuntando el código hecho por gemini y modificado por los miembros del equipo”")

st.markdown("---")
st.markdown(
    """
    Referencias.
    - Viancos San Martín, F. (2022). Diseño y dimensionamiento de una línea de elaboración de zumo de naranja con capacidad de 1.500.000 litros/año en Palma del Río, Córdoba [Trabajo Fin de Grado, Universidad Politécnica de Madrid].
    - Operaciones preliminares de acondicionamiento: Fellows, 2017; Ibarz & Barbosa-Cánovas, 2005.
    - Funcionamiento de extractores rotatorios tipo Brown y control de aceites esenciales: Bates et al., 2001; Kimball, 1999. 
    """
)

