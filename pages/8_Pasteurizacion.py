import math
import json
import http.server
import socketserver
import urllib.parse
import webbrowser
import threading

# Detecta automáticamente si corre en el Hub de GitHub (Streamlit) o en IDLE (Mac)
try:
    import streamlit as st
    EN_STREAMLIT = hasattr(st, "runtime") and st.runtime.exists()
except ImportError:
    st = None
    EN_STREAMLIT = False


# =============================================================================
# 1. MOTOR MATEMÁTICO EN UNIDADES SI (Ejecutable solo e integrable en planta)
# =============================================================================
def simular_pasteurizador(
    flujo_vol_lh: float = 6000.0,
    brix: float = 11.2,
    temp_entrada_c: float = 15.0,
    temp_pasteurizacion_c: float = 90.0,
    tiempo_retencion_s: float = 20.0,
    temp_salida_c: float = 4.0,
    temp_glicol_in_c: float = -4.0,
    eficiencia_regeneracion_pct: float = 0.0,
    vitamina_c_in_mg_l: float = 500.0,
) -> dict:
    """
    Simula el pasteurizador multitubular Gémina JC-P/6500-A en unidades SI.
    Recibe zumo de Desaireación y entrega zumo estéril frío a Envasado Aséptico.
    """
    # 1. Conversión al Sistema Internacional (SI) y propiedades físicas
    densidad_kg_m3 = 1045.0  # 1,045 kg/L = 1045 kg/m³
    flujo_vol_m3_s = flujo_vol_lh / (1000.0 * 3600.0)
    flujo_masico_kg_s = flujo_vol_m3_s * densidad_kg_m3

    fraccion_solidos = brix / 100.0
    cp_zumo_j_kgk = (4.187 * (1.0 - fraccion_solidos) + 1.424 * fraccion_solidos) * 1000.0

    # 2. Balance de energía en calentamiento (SI: Watts = J/s)
    eta_reg = eficiencia_regeneracion_pct / 100.0
    temp_tras_regeneracion_c = temp_entrada_c + eta_reg * (temp_pasteurizacion_c - temp_entrada_c)

    q_calentamiento_total_w = flujo_masico_kg_s * cp_zumo_j_kgk * (temp_pasteurizacion_c - temp_entrada_c)
    q_calentamiento_neto_w = flujo_masico_kg_s * cp_zumo_j_kgk * (temp_pasteurizacion_c - temp_tras_regeneracion_c)

    # Vapor saturado: Hva = 500 kcal/kg = 2.0935e6 J/kg
    entalpia_vapor_j_kg = 500.0 * 4187.0
    flujo_vapor_kg_s = q_calentamiento_neto_w / entalpia_vapor_j_kg
    flujo_vapor_kg_h = flujo_vapor_kg_s * 3600.0

    # 3. Hidrodinámica en la celda de retención (Tubería AISI-304 de 2" = 0.0508 m)
    diametro_tubo_m = 0.0508
    area_transversal_m2 = (math.pi * (diametro_tubo_m ** 2)) / 4.0
    volumen_celda_fijo_m3 = (6000.0 / (1000.0 * 3600.0)) * 20.0
    longitud_celda_m = volumen_celda_fijo_m3 / area_transversal_m2
    velocidad_zumo_m_s = flujo_vol_m3_s / area_transversal_m2

    # 4. Balance de energía en enfriamiento (Agua glicolada a -4 °C)
    temp_antes_glicol_c = temp_pasteurizacion_c - eta_reg * (temp_pasteurizacion_c - temp_entrada_c)
    q_enfriamiento_neto_w = max(
        0.0, flujo_masico_kg_s * cp_zumo_j_kgk * (temp_antes_glicol_c - temp_salida_c)
    )

    cp_glicol_j_kgk = 3800.0
    delta_t_glicol_k = 6.0
    flujo_glicol_kg_s = q_enfriamiento_neto_w / (cp_glicol_j_kgk * delta_t_glicol_k)
    flujo_glicol_kg_h = flujo_glicol_kg_s * 3600.0

    # 5. Cinética de inactivación térmica (Saccharomyces cerevisiae) y Vitamina C
    valor_d_s = 3.0 * (10.0 ** (-(temp_pasteurizacion_c - 80.0) / 7.0))
    reducciones_log = tiempo_retencion_s / valor_d_s
    es_esteril = reducciones_log >= 5.0

    temp_k = temp_pasteurizacion_c + 273.15
    temp_ref_k = 90.0 + 273.15
    k_vit_c = 0.0012 * math.exp((-95000.0 / 8.314) * ((1.0 / temp_k) - (1.0 / temp_ref_k)))
    retencion_vit_c_pct = 100.0 * math.exp(-k_vit_c * tiempo_retencion_s)
    vitamina_c_out_mg_l = vitamina_c_in_mg_l * (retencion_vit_c_pct / 100.0)

    return {
        "flujo_vol_out_lh": round(flujo_vol_lh, 2),
        "flujo_masico_out_kg_s": round(flujo_masico_kg_s, 4),
        "temp_entrada_c": round(temp_entrada_c, 2),
        "temp_tras_regeneracion_c": round(temp_tras_regeneracion_c, 2),
        "temp_pasteurizacion_c": round(temp_pasteurizacion_c, 2),
        "temp_salida_c": round(temp_salida_c, 2),
        "brix_out": round(brix, 2),
        "vitamina_c_out_mg_l": round(vitamina_c_out_mg_l, 2),
        "retencion_vit_c_pct": round(retencion_vit_c_pct, 2),
        "valor_d_s": round(valor_d_s, 4),
        "reducciones_log_levadura": round(reducciones_log, 2),
        "producto_seguro": es_esteril,
        "cp_zumo_j_kgk": round(cp_zumo_j_kgk, 1),
        "potencia_calentamiento_kw": round(q_calentamiento_neto_w / 1000.0, 2),
        "potencia_enfriamiento_kw": round(q_enfriamiento_neto_w / 1000.0, 2),
        "flujo_vapor_kg_h": round(flujo_vapor_kg_h, 2),
        "flujo_glicol_kg_h": round(flujo_glicol_kg_h, 2),
        "velocidad_tubo_m_s": round(velocidad_zumo_m_s, 2),
        "longitud_celda_retencion_m": round(longitud_celda_m, 2),
        "capacidad_max_equipo_lh": 6500.0,
        "alerta_sobrecarga": flujo_vol_lh > 6500.0,
    }


# =============================================================================
# 2. MODO STREAMLIT (Se activa automáticamente al subirlo a GitHub / pages/)
# =============================================================================
def render_streamlit():
    st.set_page_config(page_title="Pasteurización - Zumo de Naranja", page_icon="🍊", layout="wide")
    st.title("🍊 Módulo de Pasteurización Multitubular (Gémina JC-P/6500-A)")
    st.markdown(
        "**Flujo integrado:** `Desaireación` ➡️ **`Pasteurización`** ➡️ `Envasado Aséptico` | "
        "**Unidades en el Sistema Internacional (SI)**"
    )

    flujo_def = float(st.session_state.get("flujo_desaireacion_lh", 6000.0))
    brix_def = float(st.session_state.get("brix_desaireacion", 11.2))
    tin_def = float(st.session_state.get("temp_desaireacion_c", 15.0))

    with st.sidebar:
        st.header("⚙️ Parámetros de Operación")
        flujo_lh = st.slider("Caudal de zumo (L/h)", 2000.0, 8000.0, flujo_def, 100.0)
        temp_past = st.slider("Temp. Pasteurización (°C)", 70.0, 105.0, 90.0, 1.0)
        tiempo_ret = st.slider("Tiempo de retención (s)", 5.0, 45.0, 20.0, 1.0)
        brix_in = st.slider("Sólidos solubles (°Brix)", 8.0, 16.0, brix_def, 0.2)
        temp_in = st.slider("Temp. Entrada (°C)", 4.0, 30.0, tin_def, 1.0)
        temp_out = st.slider("Temp. Salida a Envasado (°C)", 2.0, 15.0, 4.0, 1.0)
        regeneracion_pct = st.slider("Recuperación de calor (%)", 0.0, 75.0, 0.0, 5.0)

    res = simular_pasteurizador(
        flujo_lh, brix_in, temp_in, temp_past, tiempo_ret, temp_out, -4.0, regeneracion_pct
    )
    caso_base = simular_pasteurizador()

    st.session_state["pasteurizacion_out"] = res
    st.session_state["flujo_pasteurizado_lh"] = res["flujo_vol_out_lh"]
    st.session_state["temp_pasteurizado_c"] = res["temp_salida_c"]
    st.session_state["brix_pasteurizado"] = res["brix_out"]

    if not res["producto_seguro"]:
        st.error(f"⚠️ Alerta microbiológica: {res['reducciones_log_levadura']} log10 (< 5 log10 requerido).")
    elif res["alerta_sobrecarga"]:
        st.warning(f"⚠️ Sobrecarga: Caudal ({flujo_lh} L/h) supera capacidad máxima (6,500 L/h).")
    else:
        st.success(f"✅ Operación estéril validada ({res['reducciones_log_levadura']} log10) y Vitamina C al {res['retencion_vit_c_pct']} %.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Potencia Calentamiento", f"{res['potencia_calentamiento_kw']} kW")
    c2.metric("Potencia Enfriamiento", f"{res['potencia_enfriamiento_kw']} kW")
    c3.metric("Reducción S. cerevisiae", f"{res['reducciones_log_levadura']} log10")
    c4.metric("Retención Vitamina C", f"{res['retencion_vit_c_pct']} %")

    col_izq, col_der = st.columns(2)
    with col_izq:
        st.subheader("📊 Perfil Térmico del Proceso")
        st.line_chart({
            "Temperatura (°C)": [
                temp_in,
                res["temp_tras_regeneracion_c"],
                temp_past,
                temp_past,
                temp_out,
            ]
        })

    with col_der:
        st.subheader("🔬 Sensibilidad: Vitamina C vs Temperatura")
        temps_rango = list(range(70, 106, 5))
        vit_rango = [
            simular_pasteurizador(flujo_lh, brix_in, temp_in, t, tiempo_ret, temp_out, -4.0, regeneracion_pct)["retencion_vit_c_pct"]
            for t in temps_rango
        ]
        st.line_chart(dict(zip(temps_rango, vit_rango)))

    st.subheader("⚖️ Validación contra Caso Base (6000 L/h, 90 °C, 20 s)")
    st.table({
        "Variable": [
            "Flujo másico (SI)",
            "Calor específico Cp (SI)",
            "Potencia calentamiento",
            "Consumo de vapor",
            "Potencia enfriamiento",
            "Caudal agua glicolada (-4 °C)",
            "Velocidad en tubos (Ø 2\")",
            "Longitud celda retención",
            "Reducción S. cerevisiae",
            "Retención Vitamina C",
        ],
        "Caso Base": [
            f"{caso_base['flujo_masico_out_kg_s']} kg/s",
            f"{caso_base['cp_zumo_j_kgk']} J/(kg·K)",
            f"{caso_base['potencia_calentamiento_kw']} kW",
            f"{caso_base['flujo_vapor_kg_h']} kg/h",
            f"{caso_base['potencia_enfriamiento_kw']} kW",
            f"{caso_base['flujo_glicol_kg_h']} kg/h",
            f"{caso_base['velocidad_tubo_m_s']} m/s",
            f"{caso_base['longitud_celda_retencion_m']} m",
            f"{caso_base['reducciones_log_levadura']} log10",
            f"{caso_base['retencion_vit_c_pct']} %",
        ],
        "Simulación Actual": [
            f"{res['flujo_masico_out_kg_s']} kg/s",
            f"{res['cp_zumo_j_kgk']} J/(kg·K)",
            f"{res['potencia_calentamiento_kw']} kW",
            f"{res['flujo_vapor_kg_h']} kg/h",
            f"{res['potencia_enfriamiento_kw']} kW",
            f"{res['flujo_glicol_kg_h']} kg/h",
            f"{res['velocidad_tubo_m_s']} m/s",
            f"{res['longitud_celda_retencion_m']} m",
            f"{res['reducciones_log_levadura']} log10",
            f"{res['retencion_vit_c_pct']} %",
        ],
    })


# =============================================================================
# 3. MODO NAVEGADOR LOCAL (Se activa al correr Run Module / F5 desde IDLE)
# =============================================================================
HTML_PAGINA = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Simulador de Pasteurización - Planta de Zumo de Naranja</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; color: #2c3e50; }
        .header { background: linear-gradient(135deg, #e67e22, #d35400); color: white; padding: 18px 25px; border-radius: 12px; margin-bottom: 20px; }
        .header h1 { margin: 0; font-size: 22px; }
        .header p { margin: 5px 0 0; opacity: 0.92; font-size: 13px; }
        .grid { display: grid; grid-template-columns: 350px 1fr; gap: 20px; }
        .card { background: white; padding: 18px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
        .slider-group { margin-bottom: 12px; }
        .slider-group label { display: flex; justify-content: space-between; font-weight: 600; font-size: 13px; margin-bottom: 4px; }
        .slider-group input[type=range] { width: 100%; accent-color: #e67e22; }
        .btn-base { width: 100%; background: #2c3e50; color: white; border: none; padding: 10px; border-radius: 8px; font-weight: 600; cursor: pointer; margin-top: 6px; }
        .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
        .kpi { background: #fff8f2; border-left: 4px solid #e67e22; padding: 12px; border-radius: 8px; }
        .kpi .titulo { font-size: 12px; color: #7f8c8d; font-weight: 600; }
        .kpi .valor { font-size: 19px; font-weight: 700; margin-top: 4px; }
        .alerta { padding: 10px 14px; border-radius: 8px; font-weight: 600; font-size: 13px; margin-bottom: 14px; }
        .seguro { background: #d4edda; color: #155724; }
        .peligro { background: #f8d7da; color: #721c24; }
        .charts { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .io-box { margin-top: 14px; background: #eef2f7; padding: 12px; border-radius: 8px; font-size: 13px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🍊 Módulo de Pasteurización Multitubular (Gémina JC-P/6500-A)</h1>
        <p>Integración: <b>Desaireación</b> ➔ <b>Pasteurización</b> ➔ <b>Envasado Aséptico</b> | Unidades SI validadas</p>
    </div>
    <div class="grid">
        <div class="card">
            <h3 style="margin-top:0;">⚙️ Variables de Entrada (Sliders)</h3>
            <div class="slider-group">
                <label><span>Caudal Zumo (L/h):</span> <span id="val_flujo">6000</span></label>
                <input type="range" id="flujo" min="2000" max="8000" step="100" value="6000" oninput="actualizar()">
            </div>
            <div class="slider-group">
                <label><span>Temp. Pasteurización (°C):</span> <span id="val_tpast">90</span></label>
                <input type="range" id="tpast" min="70" max="105" step="1" value="90" oninput="actualizar()">
            </div>
            <div class="slider-group">
                <label><span>Tiempo de Retención (s):</span> <span id="val_tret">20</span></label>
                <input type="range" id="tret" min="5" max="45" step="1" value="20" oninput="actualizar()">
            </div>
            <div class="slider-group">
                <label><span>Sólidos Solubles (°Brix):</span> <span id="val_brix">11.2</span></label>
                <input type="range" id="brix" min="8.0" max="16.0" step="0.2" value="11.2" oninput="actualizar()">
            </div>
            <div class="slider-group">
                <label><span>Temp. Entrada (°C):</span> <span id="val_tin">15</span></label>
                <input type="range" id="tin" min="4" max="30" step="1" value="15" oninput="actualizar()">
            </div>
            <div class="slider-group">
                <label><span>Temp. Salida (°C):</span> <span id="val_tout">4</span></label>
                <input type="range" id="tout" min="2" max="15" step="1" value="4" oninput="actualizar()">
            </div>
            <button class="btn-base" onclick="restaurarCasoBase()">🔄 Restaurar Caso Base (Planta Córdoba)</button>
            <div class="io-box" id="io_info"></div>
        </div>
        <div>
            <div id="estado_alerta" class="alerta seguro"></div>
            <div class="kpis">
                <div class="kpi"><div class="titulo">Calentamiento</div><div class="valor" id="kpi_qcal">-</div></div>
                <div class="kpi"><div class="titulo">Enfriamiento</div><div class="valor" id="kpi_qenf">-</div></div>
                <div class="kpi"><div class="titulo">Reducción S. cerevisiae</div><div class="valor" id="kpi_log">-</div></div>
                <div class="kpi"><div class="titulo">Retención Vitamina C</div><div class="valor" id="kpi_vitc">-</div></div>
            </div>
            <div class="charts">
                <div class="card">
                    <h4 style="margin-top:0;">📈 Perfil Térmico en el Intercambiador</h4>
                    <canvas id="graficaPerfil"></canvas>
                </div>
                <div class="card">
                    <h4 style="margin-top:0;">🔬 Sensibilidad: Vitamina C vs Temperatura</h4>
                    <canvas id="graficaSensibilidad"></canvas>
                </div>
            </div>
        </div>
    </div>
    <script>
        let chartPerfil = null, chartSens = null;
        function restaurarCasoBase() {
            document.getElementById('flujo').value = 6000;
            document.getElementById('tpast').value = 90;
            document.getElementById('tret').value = 20;
            document.getElementById('brix').value = 11.2;
            document.getElementById('tin').value = 15;
            document.getElementById('tout').value = 4;
            actualizar();
        }
        async function actualizar() {
            const flujo = parseFloat(document.getElementById('flujo').value);
            const tpast = parseFloat(document.getElementById('tpast').value);
            const tret = parseFloat(document.getElementById('tret').value);
            const brix = parseFloat(document.getElementById('brix').value);
            const tin = parseFloat(document.getElementById('tin').value);
            const tout = parseFloat(document.getElementById('tout').value);

            document.getElementById('val_flujo').innerText = flujo;
            document.getElementById('val_tpast').innerText = tpast;
            document.getElementById('val_tret').innerText = tret;
            document.getElementById('val_brix').innerText = brix;
            document.getElementById('val_tin').innerText = tin;
            document.getElementById('val_tout').innerText = tout;

            const resp = await fetch(`/simular?flujo=${flujo}&tpast=${tpast}&tret=${tret}&brix=${brix}&tin=${tin}&tout=${tout}`);
            const data = await resp.json();
            const r = data.actual;

            document.getElementById('kpi_qcal').innerText = r.potencia_calentamiento_kw + " kW";
            document.getElementById('kpi_qenf').innerText = r.potencia_enfriamiento_kw + " kW";
            document.getElementById('kpi_log').innerText = r.reducciones_log_levadura + " log10";
            document.getElementById('kpi_vitc').innerText = r.retencion_vit_c_pct + " %";

            const alerta = document.getElementById('estado_alerta');
            if (!r.producto_seguro) {
                alerta.className = "alerta peligro";
                alerta.innerText = "⚠️ ALERTA MICROBIOLÓGICA: Reducción < 5 log10. Sube la temperatura (>80 °C) o el tiempo.";
            } else if (r.alerta_sobrecarga) {
                alerta.className = "alerta peligro";
                alerta.innerText = "⚠️ SOBRECARGA DE EQUIPO: El caudal supera los 6,500 L/h del pasteurizador Gémina.";
            } else {
                alerta.className = "alerta seguro";
                alerta.innerText = "✅ OPERACIÓN ÓPTIMA Y ESTÉRIL: Cumple inactivación de S. cerevisiae y capacidad nominal.";
            }

            document.getElementById('io_info').innerHTML = `
                <b>🔗 Salidas hacia Envasado Aséptico (SI):</b><br>
                • Flujo másico: <b>${r.flujo_masico_out_kg_s} kg/s</b><br>
                • Cp del zumo: <b>${r.cp_zumo_j_kgk} J/(kg·K)</b><br>
                • Vapor requerido: <b>${r.flujo_vapor_kg_h} kg/h</b><br>
                • Agua glicolada (-4 °C): <b>${r.flujo_glicol_kg_h} kg/h</b><br>
                • Vitamina C final: <b>${r.vitamina_c_out_mg_l} mg/L</b>
            `;

            const etapas = ["Entrada", "Calentamiento", `Retención (${tret} s)`, "Enfriamiento"];
            const temps = [tin, tpast, tpast, tout];
            if (!chartPerfil) {
                chartPerfil = new Chart(document.getElementById('graficaPerfil'), {
                    type: 'line',
                    data: { labels: etapas, datasets: [{ label: 'Temperatura (°C)', data: temps, borderColor: '#e67e22', backgroundColor: 'rgba(230,126,34,0.15)', fill: true, tension: 0.2 }] },
                    options: { scales: { y: { min: 0, max: 110 } } }
                });
            } else {
                chartPerfil.data.labels = etapas;
                chartPerfil.data.datasets[0].data = temps;
                chartPerfil.update();
            }

            if (!chartSens) {
                chartSens = new Chart(document.getElementById('graficaSensibilidad'), {
                    type: 'line',
                    data: { labels: data.curva_temps, datasets: [{ label: 'Vitamina C Retenida (%)', data: data.curva_vitc, borderColor: '#27ae60', backgroundColor: 'rgba(39,174,96,0.15)', fill: true, tension: 0.3 }] },
                    options: { scales: { y: { min: 80, max: 100 } } }
                });
            } else {
                chartSens.data.datasets[0].data = data.curva_vitc;
                chartSens.update();
            }
        }
        window.onload = actualizar;
    </script>
</body>
</html>
"""


class ManejadorSimulador(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGINA.encode("utf-8"))
        elif parsed.path == "/simular":
            qs = urllib.parse.parse_qs(parsed.query)
            flujo = float(qs.get("flujo", [6000])[0])
            tpast = float(qs.get("tpast", [90])[0])
            tret = float(qs.get("tret", [20])[0])
            brix = float(qs.get("brix", [11.2])[0])
            tin = float(qs.get("tin", [15])[0])
            tout = float(qs.get("tout", [4])[0])

            actual = simular_pasteurizador(flujo, brix, tin, tpast, tret, tout)
            curva_temps = list(range(70, 106, 5))
            curva_vitc = [
                simular_pasteurizador(flujo, brix, tin, t, tret, tout)["retencion_vit_c_pct"]
                for t in curva_temps
            ]
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps({"actual": actual, "curva_temps": curva_temps, "curva_vitc": curva_vitc}).encode("utf-8")
            )


def iniciar_modo_local():
    resultado_base = simular_pasteurizador()
    print("=== RESULTADOS DEL CASO BASE (PLANTA ZUMO DE NARANJA) ===")
    for clave, valor in resultado_base.items():
        print(f"{clave}: {valor}")

    socketserver.TCPServer.allow_reuse_address = True
    for puerto in range(8050, 8065):
        try:
            servidor = socketserver.TCPServer(("", puerto), ManejadorSimulador)
            url = f"http://localhost:{puerto}"
            print(f"\n=== SIMULADOR WEB ACTIVO EN: {url} ===")
            print("Abriendo automáticamente tu navegador web...")
            threading.Timer(0.8, lambda u=url: webbrowser.open(u)).start()
            servidor.serve_forever()
            break
        except OSError:
            continue


if EN_STREAMLIT:
    render_streamlit()
elif __name__ == "__main__":
    iniciar_modo_local()
