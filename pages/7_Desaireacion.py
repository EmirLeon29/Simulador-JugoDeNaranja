from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Rutas: la app se lanza desde la raíz del repo (streamlit run app.py), pero
# este archivo vive en pages/. Buscamos los recursos en la raíz y en pages/.
# ---------------------------------------------------------------------------
PAGE_DIR = Path(__file__).resolve().parent
ROOT_DIR = PAGE_DIR.parent


def buscar_recurso(*nombres):
    """Devuelve la primera ruta existente entre raíz, pages/ y assets/."""
    for nombre in nombres:
        for carpeta in (ROOT_DIR, PAGE_DIR, ROOT_DIR / "assets"):
            ruta = carpeta / nombre
            if ruta.exists():
                return ruta
    return None


# En páginas de una app multipágina, set_page_config debe ser el primer comando st.
st.set_page_config(
    page_title="Módulo de Desaireación - Zumo de Naranja",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #111111; }
    .inst-univ { font-family: Arial, sans-serif; font-size: 28px !important;
        font-weight: bold; color: #1b365d; margin-bottom: 2px; line-height: 1.1; }
    .inst-fac { font-family: Arial, sans-serif; font-size: 22px !important;
        font-weight: bold; color: #b38f00; margin-top: 2px; margin-bottom: 6px; line-height: 1.2; }
    .mod-title { font-family: Arial, sans-serif; font-size: 18px !important;
        font-weight: normal; color: #555555; margin-top: 2px; }
    h2, h3, .stSubheader { font-family: Arial, sans-serif; font-size: 20px !important;
        font-weight: bold !important; color: #1b365d !important; }
    p, label, .stCaption { font-family: Arial, sans-serif; font-size: 15px !important; }
    </style>
""", unsafe_allow_html=True)


def cargar_fuente(tamano):
    """arial.ttf no existe en Streamlit Cloud (Linux): probamos alternativas."""
    for nombre in ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(nombre, tamano)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=tamano)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


@st.cache_data(show_spinner=False)
def _cargar_base(ruta):
    return Image.open(ruta).convert("RGB")


def generar_imagen_dinamica(presion, temperatura):
    """Estampa presión y temperatura centradas en los displays de la imagen."""
    ruta = buscar_recurso("image_17.png", "image_17.jpg")
    if ruta is None:
        return None

    img = _cargar_base(str(ruta)).copy()
    draw = ImageDraw.Draw(img)
    font_numero = cargar_fuente(28)
    font_unidad = cargar_fuente(15)

    draw.text((552, 370), f"{presion:4.1f}", fill=(20, 20, 20), font=font_numero, anchor="mm")
    draw.text((552, 397), "kPa", fill=(70, 70, 70), font=font_unidad, anchor="mm")
    draw.text((553, 468), f"{temperatura:4.1f}", fill=(20, 20, 20), font=font_numero, anchor="mm")
    draw.text((553, 495), "°C", fill=(70, 70, 70), font=font_unidad, anchor="mm")
    return img


def run_desaireacion(caudal_ext=None, temp_ext=None, oxigeno_ext=None):
    """
    Módulo de desaireación.
    Si recibe parámetros externos (de la página anterior) los usa; si no, usa controles locales.
    Retorna (caudal_salida, oxigeno_salida).
    """
    # --- ENCABEZADO ---
    col_head, col_logo1, col_logo2 = st.columns([4.2, 1.4, 1.4], gap="medium")
    with col_head:
        st.markdown('<p class="inst-univ">Universidad Nacional Autónoma de México</p>', unsafe_allow_html=True)
        st.markdown('<p class="inst-fac">Facultad de Estudios Superiores Zaragoza</p>', unsafe_allow_html=True)
        st.markdown('<p class="mod-title">Ingeniería Química • Módulo de Desaireación - Zumo de Naranja</p>', unsafe_allow_html=True)
    with col_logo1:
        logo = buscar_recurso("logo_unam.png", "logo_unam.png.png")
        if logo:
            st.image(str(logo), width=180)
    with col_logo2:
        logo = buscar_recurso("logo_fes.png", "logo_fes.png.png")
        if logo:
            st.image(str(logo), width=180)

    st.markdown("---")

    if "simulacion_activa_desaireacion" not in st.session_state:
        st.session_state.simulacion_activa_desaireacion = False

    caudal_salida, oxigeno_salida = 1958.40, 0.50

    col_inputs, col_results = st.columns([1.1, 0.9], gap="large")

    with col_inputs:
        st.subheader("1. Parámetros de Entrada")

        if caudal_ext is not None:
            st.info("🔗 **Conectado al tren de proceso:** recibiendo caudal de la corriente anterior.")
            caudal_entrada = caudal_ext
            st.metric("Caudal de Zumo Recibido (kg/h)", f"{caudal_entrada:.2f}")
        else:
            caudal_entrada = st.number_input("Caudal de Zumo de Entrada (kg/h)", value=1959.38, step=10.0)

        presion_vacio = st.slider("Presión de Vacío en la Cámara (kPa)", 3.0, 50.0, 7.0, 0.5)

        if temp_ext is not None:
            temp_entrada = temp_ext
            st.metric("Temperatura de Entrada Recibida (°C)", f"{temp_entrada:.1f}")
        else:
            temp_entrada = st.slider("Temperatura de Entrada del Zumo (°C)", 10.0, 90.0, 25.0, 1.0)

        if oxigeno_ext is not None:
            oxigeno_inicial = oxigeno_ext
            st.metric("Oxígeno Disuelto Inicial Recibido (mg/L)", f"{oxigeno_inicial:.2f}")
        else:
            oxigeno_inicial = st.slider("Oxígeno Disuelto Inicial (mg/L o ppm)", 5.0, 25.0, 10.0, 0.5)

        st.markdown("---")
        btn_iniciar = st.button("🚀 Iniciar Simulación y Balance", type="primary", use_container_width=True)

        if btn_iniciar or caudal_ext is not None:
            st.session_state.simulacion_activa_desaireacion = True

        if not st.session_state.simulacion_activa_desaireacion:
            st.info("💡 Configura los parámetros y haz clic en **'Iniciar Simulación y Balance'** para ver los cálculos.")
        else:
            # --- VALIDACIONES FÍSICAS ---
            temp_ebullicion_aprox = 35.0 + (presion_vacio * 1.5)

            if temp_entrada > temp_ebullicion_aprox and presion_vacio < 15.0:
                st.error(
                    f"❌ **Error Físico Inviable:** con **{presion_vacio:.1f} kPa**, la temperatura de "
                    f"**{temp_entrada:.1f} °C** provocará ebullición instantánea violenta (*flashing* prematuro).\n\n"
                    "*Sugerencia:* disminuye la temperatura de entrada o reduce el nivel de vacío."
                )
                return 0.0, 0.0

            if oxigeno_inicial <= 0.1:
                st.error("❌ **Error Físico Inviable:** el oxígeno disuelto inicial no puede ser cero o negativo.")
                return 0.0, 0.0

            st.success("✅ Simulación calculada exitosamente bajo régimen estacionario.")
            st.markdown("---")

            # --- 2. BALANCE DE MATERIA ---
            st.subheader("2. Cálculos y Balance de Materia")

            eficiencia = min(98.0, max(85.0, 95.0 - (presion_vacio - 7.0) * 0.5))
            oxigeno_salida = oxigeno_inicial * (1 - eficiencia / 100.0)

            perdida_gases = caudal_entrada * 0.0005
            caudal_salida = caudal_entrada - perdida_gases

            tiempo_residencia_min = 2.0
            densidad_zumo = 1045.0  # kg/m³
            vol_util_L = (caudal_entrada / densidad_zumo) * (tiempo_residencia_min / 60.0) * 1000.0
            vol_total_L = vol_util_L / 0.35  # 35 % de llenado

            m1, m2, m3 = st.columns(3)
            m1.metric("Zumo Salida", f"{caudal_salida:.2f} kg/h")
            m2.metric("O₂ Residual", f"{oxigeno_salida:.2f} mg/L", f"-{eficiencia:.1f}%")
            m3.metric("Vol. Tanque", f"{vol_total_L:.1f} L")

            st.markdown("---")

            # --- 3. SENSIBILIDAD ---
            st.subheader("3. Comportamiento del Sistema")
            st.caption("Sensibilidad: Presión de Vacío vs. Oxígeno Residual")

            filas = ["| Presión (kPa) | Efic. (%) | O₂ Res. (mg/L) |", "| :--- | :--- | :--- |"]
            for p in (3.0, 5.0, 7.0, 9.0, 12.0, 15.0, 20.0):
                ef = min(98.0, max(85.0, 95.0 - (p - 7.0) * 0.5))
                filas.append(f"| {p:.1f} | {ef:.1f}% | {oxigeno_inicial * (1 - ef / 100.0):.2f} |")
            st.markdown("\n".join(filas))

            # Guardar resultados para que la siguiente página los lea
            st.session_state["desaireacion_caudal_salida"] = caudal_salida
            st.session_state["desaireacion_o2_salida"] = oxigeno_salida
            st.session_state["desaireacion_temp_salida"] = temp_entrada

    with col_results:
        st.subheader("Panel SCADA - Vista en Vivo del Equipo")
        img = generar_imagen_dinamica(presion_vacio, temp_entrada)
        if img:
            st.image(
                img,
                caption=f"Telemetría Activa | Vacío: {presion_vacio:.1f} kPa | Temp: {temp_entrada:.1f} °C",
                use_container_width=True,
            )
        else:
            st.warning("⚠️ No se encontró image_17.png en la carpeta del proyecto.")

    return caudal_salida, oxigeno_salida


# En una app multipágina Streamlit ejecuta este archivo directamente, sin guard de __main__.
# Si la página anterior guardó su salida en session_state, se usa automáticamente.
# (Ajusta los nombres de las claves a los que usen tus compañeros.)
run_desaireacion(
    caudal_ext=st.session_state.get("tamizado_caudal_salida"),
    temp_ext=st.session_state.get("tamizado_temp_salida"),
    oxigeno_ext=st.session_state.get("tamizado_o2_salida"),
)
