import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import os

# Configuración del dashboard a pantalla completa
st.set_page_config(
    page_title="Módulo de Desaireación - Zumo de Naranja", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS CON TIPOGRAFÍA INSTITUCIONAL ---
st.markdown("""
    <style>
    /* Tipografía institucional en tamaños grandes */
    .inst-univ {
        font-family: Arial, sans-serif;
        font-size: 28px !important;
        font-weight: bold;
        color: #1b365d;
        margin-bottom: 2px;
        line-height: 1.1;
    }
    .inst-fac {
        font-family: Arial, sans-serif;
        font-size: 22px !important;
        font-weight: bold;
        color: #b38f00;
        margin-top: 2px;
        margin-bottom: 6px;
        line-height: 1.2;
    }
    .mod-title {
        font-family: Arial, sans-serif;
        font-size: 18px !important;
        font-weight: normal;
        color: #888888;
        margin-top: 2px;
    }
    
    /* Estilos generales del cuerpo */
    h2, h3, .stSubheader {
        font-family: Arial, sans-serif;
        font-size: 20px !important;
        font-weight: bold !important;
    }
    p, label, .stCaption {
        font-family: Arial, sans-serif;
        font-size: 15px !important;
    }
    </style>
""", unsafe_allow_html=True)

def cargar_fuente(tamano):
    """Busca fuentes en Windows/Linux o escala la fuente por defecto para garantizar el tamaño"""
    rutas_fuentes = [
        "arialbd.ttf",  # Arial Bold en Windows
        "arial.ttf",    # Arial Regular en Windows
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", # Linux / Streamlit Cloud
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    ]
    for ruta in rutas_fuentes:
        try:
            return ImageFont.truetype(ruta, tamano)
        except:
            continue
    try:
        return ImageFont.load_default(size=tamano)
    except:
        return ImageFont.load_default()

def generar_imagen_dinamica(presion, temperatura):
    """Estampa los valores de presión y temperatura en tamaño equilibrado dentro de los displays verdes"""
    img_path = "image_17.png"
    if not os.path.exists(img_path):
        img_path = "image_17.jpg"
        
    if os.path.exists(img_path):
        img = Image.open(img_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        
        font_numero = cargar_fuente(34)
        font_unidad = cargar_fuente(17)
            
        # Display superior (Presión de Vacío)
        draw.text((552, 368), f"{presion:4.1f}", fill=(15, 25, 15), font=font_numero, anchor="mm")
        draw.text((552, 398), "kPa", fill=(45, 55, 45), font=font_unidad, anchor="mm")
        
        # Display inferior (Temperatura)
        draw.text((553, 466), f"{temperatura:4.1f}", fill=(15, 25, 15), font=font_numero, anchor="mm")
        draw.text((553, 496), "°C", fill=(45, 55, 45), font=font_unidad, anchor="mm")
        
        return img
    else:
        return None

def run_desaireacion(caudal_ext=None, temp_ext=None, oxigeno_ext=None):
    """
    Función principal del módulo. 
    Permite recibir parámetros externos de módulos previos o usar valores interactivos locales.
    Retorna: (caudal_salida, oxigeno_salida) para alimentar al siguiente equipo.
    """
    # --- ENCABEZADO INSTITUCIONAL CON LOGOS AMPLIADOS (180px) ---
    col_head_texto, col_logo1, col_logo2 = st.columns([4.2, 1.4, 1.4], gap="medium")
    
    with col_head_texto:
        st.markdown('<p class="inst-univ">Universidad Nacional Autónoma de México</p>', unsafe_allow_html=True)
        st.markdown('<p class="inst-fac">Facultad de Estudios Superiores Zaragoza</p>', unsafe_allow_html=True)
        st.markdown('<p class="mod-title">Ingeniería Química • Módulo de Desaireación - Zumo de Naranja</p>', unsafe_allow_html=True)
        
    with col_logo1:
        if os.path.exists("logo_unam.png"):
            st.image("logo_unam.png", width=180)
        elif os.path.exists("logo_unam.png.png"):
            st.image("logo_unam.png.png", width=180)
            
    with col_logo2:
        if os.path.exists("logo_fes.png"):
            st.image("logo_fes.png", width=180)
        elif os.path.exists("logo_fes.png.png"):
            st.image("logo_fes.png.png", width=180)
            
    st.markdown("---")
    
    # Diseño de 2 columnas principales (Izquierda: Controles y Cálculos | Derecha: Panel SCADA)
    col_inputs, col_results = st.columns([1.1, 0.9], gap="large")
    
    with col_inputs:
        st.subheader("1. Parámetros de Entrada")
        
        if caudal_ext is not None:
            st.info("🔗 **Conectado al tren de proceso:** Recibiendo caudal de corriente anterior.")
            caudal_entrada = caudal_ext
            st.metric("Caudal de Zumo Recibido (kg/h)", f"{caudal_entrada:.2f}")
        else:
            caudal_entrada = st.number_input("Caudal de Zumo de Entrada (kg/h)", value=1959.38, step=10.0)
            
        presion_vacio = st.slider("Presión de Vacío en la Cámara (kPa)", min_value=3.0, max_value=50.0, value=7.0, step=0.5)
        
        if temp_ext is not None:
            temp_entrada = temp_ext
            st.metric("Temperatura de Entrada Recibida (°C)", f"{temp_entrada:.1f}")
        else:
            temp_entrada = st.slider("Temperatura de Entrada del Zumo (°C)", min_value=10.0, max_value=90.0, value=25.0, step=1.0)
            
        if oxigeno_ext is not None:
            oxigeno_inicial = oxigeno_ext
            st.metric("Oxígeno Disuelto Inicial Recibido (mg/L)", f"{oxigeno_inicial:.2f}")
        else:
            oxigeno_inicial = st.slider("Oxígeno Disuelto Inicial (mg/L o ppm)", min_value=5.0, max_value=25.0, value=10.0, step=0.5)
        
        st.markdown("---")
        
        btn_iniciar = st.button("🚀 Iniciar Simulación y Balance", type="primary", use_container_width=True)
        
        if "simulacion_activa" not in st.session_state:
            st.session_state.simulacion_activa = False
            
        if btn_iniciar or (caudal_ext is not None):
            st.session_state.simulacion_activa = True

        if not st.session_state.simulacion_activa:
            st.info("💡 Configura tus parámetros arriba y haz clic en **'Iniciar Simulación y Balance'** para desplegar los cálculos y la tabla analítica en este espacio.")
            caudal_salida = 1958.40
            oxigeno_salida = 0.50
        else:
            # --- VALIDACIONES FÍSICAS DE VIABILIDAD ---
            temp_ebullicion_aprox = 35.0 + (presion_vacio * 1.5) 
            
            if temp_entrada > temp_ebullicion_aprox and presion_vacio < 15.0:
                st.error(f"❌ **Error Físico Inviable:** Con una presión de vacío de **{presion_vacio:.1f} kPa**, la temperatura de **{temp_entrada:.1f} °C** provocará una ebullición instantánea violenta (*flashing* prematuro).\n\n*Sugerencia:* Disminuye la temperatura de entrada o reduce el nivel de vacío.")
                return 0.0, 0.0
            
            if oxigeno_inicial <= 0.1:
                st.error("❌ **Error Físico Inviable:** El valor de oxígeno disuelto inicial no puede ser cero o negativo.")
                return 0.0, 0.0

            st.success("✅ Simulación calculada exitosamente bajo régimen estacionario.")
            st.markdown("---")

            # 2. Cálculos y Balance de Materia
            st.subheader("2. Cálculos y Balance de Materia")
            
            eficiencia_remocion = min(98.0, max(85.0, 95.0 - (presion_vacio - 7.0) * 0.5))
            oxigeno_salida = oxigeno_inicial * (1 - eficiencia_remocion / 100.0)
            
            perdida_gases = caudal_entrada * 0.0005
            caudal_salida = caudal_entrada - perdida_gases
            
            tiempo_residencia_min = 2.0
            densidad_zumo = 1045.0  # kg/m^3
            volumen_util_litros = (caudal_entrada / densidad_zumo) * (tiempo_residencia_min / 60.0) * 1000.0
            volumen_total_litros = volumen_util_litros / 0.35  # 35% de llenado
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Zumo Salida", f"{caudal_salida:.2f} kg/h")
            m2.metric("O₂ Residual", f"{oxigeno_salida:.2f} mg/L", f"-{eficiencia_remocion:.1f}%")
            m3.metric("Vol. Tanque", f"{volumen_total_litros:.1f} L")

            st.markdown("---")

            # 3. Comportamiento del Sistema / Tabla de Sensibilidad
            st.subheader("3. Comportamiento del Sistema")
            st.caption("Sensibilidad: Presión de Vacío vs. Oxígeno Residual")
            
            lineas_tabla = [
                "| Presión (kPa) | Efic. (%) | O₂ Res. (mg/L) |",
                "| :--- | :--- | :--- |"
            ]
            presiones_sim = [3.0, 5.0, 7.0, 9.0, 12.0, 15.0, 20.0]
            for p in pres
