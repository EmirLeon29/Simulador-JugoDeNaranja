import math
import json
import http.server
import socketserver
import urllib.parse
import webbrowser
import threading

# =============================================================================
# 1. MOTOR MATEMÁTICO EN UNIDADES SI (Módulo de Desaireación)
# =============================================================================
def simular_desaireacion(
    caudal_entrada_lh: float = 1959.38,
    presion_vacio_kpa: float = 7.0,
    temp_entrada_c: float = 25.0,
    oxigeno_inicial_ppm: float = 10.0,
) -> dict:
    """
    Simula el equipo de desaireación industrial bajo vacío para zumo de naranja.
    """
    # 1. Validaciones físicas de viabilidad
    temp_ebullicion_aprox = 35.0 + (presion_vacio_kpa * 1.5)
    flash_inviable = (temp_entrada_c > temp_ebullicion_aprox) and (presion_vacio_kpa < 15.0)
    error_oxigeno = oxigeno_inicial_ppm <= 0.1

    if flash_inviable or error_oxigeno:
        return {
            "valido": False,
            "error_msg": "❌ Error Físico Inviable: Temperatura muy alta para el nivel de vacío (riesgo de flashing violento) o oxígeno inválido."
        }

    # 2. Balance de materia y eficiencia de desaireación
    eficiencia_remocion = min(98.0, max(85.0, 95.0 - (presion_vacio_kpa - 7.0) * 0.5))
    oxigeno_salida = oxigeno_inicial_ppm * (1.0 - eficiencia_remocion / 100.0)
    
    perdida_gases = caudal_entrada_lh * 0.0005
    caudal_salida = caudal_entrada_lh - perdida_gases

    # 3. Dimensionamiento del estanque (35% de factor de llenado, 2 min de residencia)
    tiempo_residencia_min = 2.0
    densidad_zumo = 1045.0  # kg/m^3
    volumen_util_litros = (caudal_entrada_lh / densidad_zumo) * (tiempo_residencia_min / 60.0) * 1000.0
    volumen_total_litros = volumen_util_litros / 0.35

    return {
        "valido": True,
        "caudal_entrada": round(caudal_entrada_lh, 2),
        "caudal_salida": round(caudal_salida, 2),
        "oxigeno_inicial": round(oxigeno_inicial_ppm, 2),
        "oxigeno_salida": round(oxigeno_salida, 2),
        "eficiencia_remocion": round(eficiencia_remocion, 1),
        "presion_vacio": round(presion_vacio_kpa, 1),
        "temp_entrada": round(temp_entrada_c, 1),
        "volumen_tanque": round(volumen_total_litros, 1),
    }


# =============================================================================
# 2. MODO NAVEGADOR WEB LOCAL (Interfaz Gráfica SCADA Integrada)
# =============================================================================
HTML_PAGINA = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Módulo de Desaireación - Zumo de Naranja</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; background: #FFFFFF; margin: 0; padding: 20px; color: #111111; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 15px; margin-bottom: 20px; }
        .inst-univ { font-size: 24px; font-weight: bold; color: #1b365d; margin: 0; }
        .inst-fac { font-size: 18px; font-weight: bold; color: #b38f00; margin: 2px 0; }
        .mod-title { font-size: 15px; color: #555555; margin: 0; }
        .logos { display: flex; gap: 15px; }
        .grid { display: grid; grid-template-columns: 1fr 1.1fr; gap: 30px; }
        .card { background: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
        .slider-group { margin-bottom: 15px; }
        .slider-group label { display: flex; justify-content: space-between; font-weight: bold; font-size: 14px; margin-bottom: 5px; }
        .slider-group input[type=range] { width: 100%; accent-color: #1b365d; }
        .kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 15px; }
        .kpi { background: #f8fafc; border-left: 4px solid #1b365d; padding: 10px; border-radius: 6px; }
        .kpi .titulo { font-size: 12px; color: #64748b; font-weight: bold; }
        .kpi .valor { font-size: 16px; font-weight: bold; color: #1b365d; margin-top: 3px; }
        .alerta { padding: 12px; border-radius: 8px; font-weight: bold; font-size: 14px; margin-bottom: 15px; }
        .seguro { background: #dcfce7; color: #166534; }
        .peligro { background: #fee2e2; color: #991b1b; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }
        th, td { border: 1px solid #cbd5e1; padding: 8px; text-align: center; }
        th { background: #f1f5f9; color: #1b365d; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <p class="inst-univ">Universidad Nacional Autónoma de México</p>
            <p class="inst-fac">Facultad de Estudios Superiores Zaragoza</p>
            <p class="mod-title">Ingeniería Química • Módulo de Desaireación - Zumo de Naranja</p>
        </div>
        <div class="logos">
            <h3 style="color:#b38f00; margin:auto;">[ UNAM / FES ZARAGOZA ]</h3>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <h3 style="margin-top:0; color:#1b365d;">1. Parámetros de Entrada</h3>
            <div class="slider-group">
                <label><span>Caudal de Zumo Entrada (kg/h):</span> <span id="val_caudal">1959.38</span></label>
                <input type="range" id="caudal" min="500" max="5000" step="10.0" value="1959.38" oninput="actualizar()">
            </div>
            <div class="slider-group">
                <label><span>Presión de Vacío (kPa):</span> <span id="val_presion">7.0</span></label>
                <input type="range" id="presion" min="3.0" max="50.0" step="0.5" value="7.0" oninput="actualizar()">
            </div>
            <div class="slider-group">
                <label><span>Temperatura de Entrada (°C):</span> <span id="val_temp">25.0</span></label>
                <input type="range" id="temp" min="10.0" max="90.0" step="1.0" value="25.0" oninput="actualizar()">
            </div>
            <div class="slider-group">
                <label><span>Oxígeno Inicial (mg/L):</span> <span id="val_o2">10.0</span></label>
                <input type="range" id="o2" min="5.0" max="25.0" step="0.5" value="10.0" oninput="actualizar()">
            </div>

            <div id="estado_alerta" class="alerta seguro">Estado Operativo Normal</div>

            <h3 style="color:#1b365d; margin-top:20px;">2. Cálculos y Balance de Materia</h3>
            <div class="kpis">
                <div class="kpi"><div class="titulo">Zumo Salida</div><div class="valor" id="kpi_zumo">-</div></div>
                <div class="kpi"><div class="titulo">O₂ Residual</div><div class="valor" id="kpi_o2res">-</div></div>
                <div class="kpi"><div class="titulo">Vol. Tanque</div><div class="valor" id="kpi_vol">-</div></div>
            </div>
        </div>

        <div class="card">
            <h3 style="margin-top:0; color:#1b365d;">3. Comportamiento del Sistema (Sensibilidad)</h3>
            <p style="font-size:13px; color:#64748b;">Relación analítica entre la Presión de Vacío y el Oxígeno Residual:</p>
            <table>
                <thead>
                    <tr><th>Presión (kPa)</th><th>Eficiencia (%)</th><th>O₂ Residual (mg/L)</th></tr>
                </thead>
                <tbody id="tabla_sensibilidad">
                </tbody>
            </table>
        </div>
    </div>

    <script>
        async function actualizar() {
            const caudal = parseFloat(document.getElementById('caudal').value);
            const presion = parseFloat(document.getElementById('presion').value);
            const temp = parseFloat(document.getElementById('temp').value);
            const o2 = parseFloat(document.getElementById('o2').value);

            document.getElementById('val_caudal').innerText = caudal.toFixed(2);
            document.getElementById('val_presion').innerText = presion.toFixed(1);
            document.getElementById('val_temp').innerText = temp.toFixed(1);
            document.getElementById('val_o2').innerText = o2.toFixed(1);

            const resp = await fetch(`/simular?caudal=${caudal}&presion=${presion}&temp=${temp}&o2=${o2}`);
            const data = await resp.json();

            const alerta = document.getElementById('estado_alerta');
            if (!data.actual.valido) {
                alerta.className = "alerta peligro";
                alerta.innerText = data.actual.error_msg;
                document.getElementById('kpi_zumo').innerText = "N/A";
                document.getElementById('kpi_o2res').innerText = "N/A";
                document.getElementById('kpi_vol').innerText = "N/A";
                return;
            } else {
                alerta.className = "alerta seguro";
                alerta.innerText = "✅ Simulación calculada exitosamente bajo régimen estacionario.";
            }

            const r = data.actual;
            document.getElementById('kpi_zumo').innerText = r.caudal_salida + " kg/h";
            document.getElementById('kpi_o2res').innerText = r.oxigeno_salida + " mg/L";
            document.getElementById('kpi_vol').innerText = r.volumen_tanque + " L";

            let filas = "";
            data.tabla.forEach(row => {
                filas += `<tr><td>${row.p.toFixed(1)}</td><td>${row.ef.toFixed(1)}%</td><td>${row.o2.toFixed(2)}</td></tr>`;
            });
            document.getElementById('tabla_sensibilidad').innerHTML = filas;
        }
        window.onload = actualizar;
    </script>
</body>
</html>
"""


class ManejadorDesaireacion(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Oculta logs innecesarios en consola

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGINA.encode("utf-8"))
        elif parsed.path == "/simular":
            qs = urllib.parse.parse_qs(parsed.query)
            caudal = float(qs.get("caudal", [1959.38])[0])
            presion = float(qs.get("presion", [7.0])[0])
            temp = float(qs.get("temp", [25.0])[0])
            o2 = float(qs.get("o2", [10.0])[0])

            actual = simular_desaireacion(caudal, presion, temp, o2)
            
            # Tabla de sensibilidad
            tabla = []
            presiones_sim = [3.0, 5.0, 7.0, 9.0, 12.0, 15.0, 20.0]
            for p in presiones_sim:
                ef = min(98.0, max(85.0, 95.0 - (p - 7.0) * 0.5))
                o2_res = o2 * (1.0 - ef / 100.0)
                tabla.append({"p": p, "ef": ef, "o2": o2_res})

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps({"actual": actual, "tabla": tabla}).encode("utf-8")
            )


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    for puerto in range(8070, 8085):
        try:
            servidor = socketserver.TCPServer(("", puerto), ManejadorDesaireacion)
            url = f"http://localhost:{puerto}"
            print(f"\n=== MÓDULO DE DESAIREACIÓN ACTIVO EN: {url} ===")
            print("Abriendo automáticamente tu navegador web...")
            threading.Timer(0.8, lambda u=url: webbrowser.open(u)).start()
            servidor.serve_forever()
            break
        except OSError:
            continue
