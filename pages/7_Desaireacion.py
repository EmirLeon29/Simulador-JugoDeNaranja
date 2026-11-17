import math
import json
import http.server
import socketserver
import urllib.parse
import webbrowser
import threading
from io import BytesIO
from urllib.request import urlopen
from PIL import Image, ImageDraw, ImageFont

# =============================================================================
# 1. MOTOR MATEMÁTICO EN UNIDADES SI (Módulo de Desaireación)
# =============================================================================
def simular_desaireacion(
    caudal_entrada_lh: float = 1959.38,
    presion_vacio_kpa: float = 7.0,
    temp_entrada_c: float = 25.0,
    oxigeno_inicial_ppm: float = 10.0,
) -> dict:
    temp_ebullicion_aprox = 35.0 + (presion_vacio_kpa * 1.5)
    flash_inviable = (temp_entrada_c > temp_ebullicion_aprox) and (presion_vacio_kpa < 15.0)
    error_oxigeno = oxigeno_inicial_ppm <= 0.1

    if flash_inviable or error_oxigeno:
        return {
            "valido": False,
            "error_msg": "❌ Error Físico Inviable: Temperatura muy alta para el nivel de vacío (riesgo de flashing violento) o oxígeno inválido."
        }

    eficiencia_remocion = min(98.0, max(85.0, 95.0 - (presion_vacio_kpa - 7.0) * 0.5))
    oxigeno_salida = oxigeno_inicial_ppm * (1.0 - eficiencia_remocion / 100.0)
    
    perdida_gases = caudal_entrada_lh * 0.0005
    caudal_salida = caudal_entrada_lh - perdida_gases

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

def generar_imagen_scada_bytes(presion: float, temperatura: float) -> bytes:
    """Descarga la imagen del equipo directamente desde GitHub y estampa la telemetría"""
    url_imagen = "https://raw.githubusercontent.com/EmirLeon29/Simulador-JugoDeNaranja/main/pages/image_17.png"
    try:
        with urlopen(url_imagen) as response:
            img_data = response.read()
        img = Image.open(BytesIO(img_data)).convert("RGB")
        draw = ImageDraw.Draw(img)
        try:
            font_numero = ImageFont.truetype("arial.ttf", 28)
            font_unidad = ImageFont.truetype("arial.ttf", 15)
        except:
            font_numero = ImageFont.load_default()
            font_unidad = ImageFont.load_default()
            
        draw.text((552, 370), f"{presion:4.1f}", fill=(20, 20, 20), font=font_numero, anchor="mm")
        draw.text((552, 397), "kPa", fill=(70, 70, 70), font=font_unidad, anchor="mm")
        
        draw.text((553, 468), f"{temperatura:4.1f}", fill=(20, 20, 20), font=font_numero, anchor="mm")
        draw.text((553, 495), "°C", fill=(70, 70, 70), font=font_unidad, anchor="mm")
        
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        # Imagen de respaldo por si no hay internet al momento de correrlo
        img = Image.new("RGB", (600, 800), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        draw.text((30, 50), f"Error cargando imagen web: {e}", fill=(255, 0, 0))
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


# =============================================================================
# 2. INTERFAZ HTML/JS LOCAL (SCADA + AZUL CERÚLEO + ENLACES WEB DIRECTOS)
# =============================================================================
HTML_PAGINA = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Módulo de Desaireación - Zumo de Naranja</title>
    <style>
        body { font-family: Arial, sans-serif; background: #FFFFFF; margin: 0; padding: 0; color: #111111; }
        .header-banner {
            background-color: #0092B2;
            color: white;
            padding: 20px 35px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .inst-univ { font-family: Arial, sans-serif; font-size: 26px; font-weight: bold; margin: 0; color: white; }
        .inst-fac { font-family: Arial, sans-serif; font-size: 20px; font-weight: bold; margin: 4px 0; color: #fef08a; }
        .mod-title { font-family: Arial, sans-serif; font-size: 16px; margin: 0; color: #e0f2fe; }
        
        .logos-container { display: flex; gap: 20px; align-items: center; background: white; padding: 10px 18px; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.15); }
        .logo-img { height: 75px; width: auto; object-fit: contain; }

        .main-container { padding: 30px; display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 30px; max-width: 1600px; margin: auto; }
        .card { background: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 12px rgba(0,0,0,0.03); }
        
        h3 { color: #0092B2; font-family: Arial, sans-serif; font-size: 20px; margin-top: 0; }
        .slider-group { margin-bottom: 18px; }
        .slider-group label { display: flex; justify-content: space-between; font-weight: bold; font-size: 15px; margin-bottom: 6px; color: #1e293b; }
        .slider-group input[type=range] { width: 100%; accent-color: #0092B2; height: 6px; }
        
        .kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 20px; }
        .kpi { background: #f0f9ff; border-left: 5px solid #0092B2; padding: 15px; border-radius: 8px; }
        .kpi .titulo { font-size: 13px; color: #475569; font-weight: bold; }
        .kpi .valor { font-size: 20px; font-weight: bold; color: #0092B2; margin-top: 5px; }
        
        .alerta { padding: 14px; border-radius: 8px; font-weight: bold; font-size: 15px; margin-bottom: 20px; text-align: center; }
        .seguro { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
        .peligro { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }
        th, td { border: 1px solid #cbd5e1; padding: 10px; text-align: center; }
        th { background: #e0f2fe; color: #0092B2; font-weight: bold; }
        
        .scada-viewer { text-align: center; }
        .scada-viewer img { max-width: 100%; height: auto; border-radius: 8px; border: 1px solid #cbd5e1; box-shadow: 0 4px 8px rgba(0,0,0,0.05); }
    </style>
</head>
<body>
    <div class="header-banner">
        <div>
            <p class="inst-univ">Universidad Nacional Autónoma de México</p>
            <p class="inst-fac">Facultad de Estudios Superiores Zaragoza</p>
            <p class="mod-title">Ingeniería Química • Módulo de Desaireación - Zumo de Naranja</p>
        </div>
        <div class="logos-container">
            <!-- Enlaces web directos a los escudos en GitHub -->
            <img src="https://raw.githubusercontent.com/EmirLeon29/Simulador-JugoDeNaranja/main/pages/logo_unam.png" class="logo-img" alt="Logo UNAM">
            <img src="https://raw.githubusercontent.com/EmirLeon29/Simulador-JugoDeNaranja/main/pages/logo_fes.png" class="logo-img" alt="Logo FES Zaragoza">
        </div>
    </div>

    <div class="main-container">
        <div class="card">
            <h3>1. Parámetros de Entrada</h3>
            <div class="slider-group">
                <label><span>Caudal de Zumo de Entrada (kg/h):</span> <span id="val_caudal">1959.38</span></label>
                <input type="range" id="caudal" min="500" max="5000" step="10.0" value="1959.38" oninput="actualizar()">
            </div>
            <div class="slider-group">
                <label><span>Presión de Vacío en la Cámara (kPa):</span> <span id="val_presion">7.0</span></label>
                <input type="range" id="presion" min="3.0" max="50.0" step="0.5" value="7.0" oninput="actualizar()">
            </div>
            <div class="slider-group">
                <label><span>Temperatura de Entrada del Zumo (°C):</span> <span id="val_temp">25.0</span></label>
                <input type="range" id="temp" min="10.0" max="90.0" step="1.0" value="25.0" oninput="actualizar()">
            </div>
            <div class="slider-group">
                <label><span>Oxígeno Disuelto Inicial (mg/L o ppm):</span> <span id="val_o2">10.0</span></label>
                <input type="range" id="o2" min="5.0" max="25.0" step="0.5" value="10.0" oninput="actualizar()">
            </div>

            <div id="estado_alerta" class="alerta seguro">✅ Simulación calculada exitosamente bajo régimen estacionario.</div>

            <h3>2. Cálculos y Balance de Materia</h3>
            <div class="kpis">
                <div class="kpi"><div class="titulo">Zumo Salida</div><div class="valor" id="kpi_zumo">-</div></div>
                <div class="kpi"><div class="titulo">O₂ Residual</div><div class="valor" id="kpi_o2res">-</div></div>
                <div class="kpi"><div class="titulo">Vol. Tanque</div><div class="valor" id="kpi_vol">-</div></div>
            </div>

            <h3 style="margin-top: 30px;">3. Comportamiento del Sistema</h3>
            <table>
                <thead>
                    <tr><th>Presión (kPa)</th><th>Eficiencia (%)</th><th>O₂ Residual (mg/L)</th></tr>
                </thead>
                <tbody id="tabla_sensibilidad">
                </tbody>
            </table>
        </div>

        <div class="card scada-viewer">
            <h3>Panel SCADA - Vista en Vivo del Equipo</h3>
            <p style="font-size: 13px; color: #64748b; margin-bottom: 15px;" id="caption_scada">Telemetría Activa</p>
            <img id="scada_img" src="/scada.png?presion=7.0&temp=25.0" alt="Panel SCADA">
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

            document.getElementById('scada_img').src = `/scada.png?presion=${presion}&temp=${temp}`;
            document.getElementById('caption_scada').innerText = `Telemetría Activa | Vacío: ${presion.toFixed(1)} kPa | Temp: ${temp.toFixed(1)} °C`;

            const resp = await fetch(`/simular?caudal=${caudal}&presion=${presion}&temp=${temp}&o2=${o2}`);
            const data = await resp.json();

            const alerta = document.getElementById('estado_alerta');
            if (!data.actual.valido) {
                alerta.className = "alerta peligro";
                alerta.innerText = data.actual.error_msg;
                return;
            } else {
                alerta.className = "alerta seguro";
                alerta.innerText = "✅ Simulación calculada exitosamente bajo régimen estacionario.";
            }

            const r = data.actual;
            document.getElementById('kpi_zumo').innerText = r.caudal_salida.toFixed(2) + " kg/h";
            document.getElementById('kpi_o2res').innerText = r.oxigeno_salida.toFixed(2) + " mg/L";
            document.getElementById('kpi_vol').innerText = r.volumen_tanque.toFixed(1) + " L";

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
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGINA.encode("utf-8"))

        elif path == "/scada.png":
            presion = float(qs.get("presion", [7.0])[0])
            temp = float(qs.get("temp", [25.0])[0])
            png_bytes = generar_imagen_scada_bytes(presion, temp)
            self.send_response(200)
            self.send_header("Content-type", "image/png")
            self.end_headers()
            self.wfile.write(png_bytes)

        elif path == "/simular":
            caudal = float(qs.get("caudal", [1959.38])[0])
            presion = float(qs.get("presion", [7.0])[0])
            temp = float(qs.get("temp", [25.0])[0])
            o2 = float(qs.get("o2", [10.0])[0])

            actual = simular_desaireacion(caudal, presion, temp, o2)
            
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
        else:
            self.send_error(404, "No encontrado")


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
