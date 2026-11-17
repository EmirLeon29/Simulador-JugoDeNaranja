"""Página Streamlit - Simulador de tanques asépticos (todo en un solo archivo).

Contiene el modelo (clases y cálculos) y la interfaz. Va en pages/.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

# =========================================================================== #
# MODELO
# =========================================================================== #
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

VARIEDADES: List[str] = ["Washington Navel", "Salustiana", "Navelate"]
EPS = 1e-6


# --------------------------------------------------------------------------- #
# Configuración y resultados
# --------------------------------------------------------------------------- #
@dataclass
class ConfigPlanta:
    num_tanques_grandes: int = 6
    cap_tanque_grande_l: float = 100_000.0
    num_tanques_medianos: int = 12
    cap_tanque_mediano_l: float = 50_000.0
    densidad_kg_l: float = 1.045
    caudal_entrada_l_dia: float = 17_241.38
    caudal_salida_l_dia: float = 15_000.0
    dias_envasado_anio: int = 100
    temp_operacion_c: float = -0.5
    presion_n2_bar: float = 0.2
    dias_max_retencion: int = 365


@dataclass
class Resultado:
    """Resultado de una operación: nivel = 'ok' | 'warning' | 'error'."""
    nivel: str
    mensaje: str
    alertas: List[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Tanque
# --------------------------------------------------------------------------- #
@dataclass
class TanqueAseptico:
    id_tanque: str
    capacidad_max_l: float
    diametro_int_m: float
    altura_cilindro_m: float
    altura_cono_m: float
    variedad: Optional[str] = None
    volumen_actual_l: float = 0.0
    temperatura_c: float = -0.5
    presion_n2_bar: float = 0.2
    estado: str = "LIMPIO_VACIO"  # LIMPIO_VACIO, ALMACENANDO, SUCIO_CIP
    dias_almacenado: int = 0

    @property
    def volumen_disponible_l(self) -> float:
        return self.capacidad_max_l - self.volumen_actual_l

    @property
    def porcentaje_llenado(self) -> float:
        if self.capacidad_max_l <= 0:
            return 0.0
        return self.volumen_actual_l / self.capacidad_max_l * 100.0

    def masa_actual_kg(self, densidad_kg_l: float) -> float:
        return self.volumen_actual_l * densidad_kg_l

    def ingresar_zumo(self, litros: float, variedad: str, temp_entrada: float) -> float:
        """Ingresa zumo al tanque. Devuelve los litros que no cupieron (excedente)."""
        if self.estado == "SUCIO_CIP":
            raise ValueError(f"Tanque {self.id_tanque} requiere limpieza CIP antes de recibir producto.")
        if self.variedad is not None and self.variedad != variedad:
            raise ValueError(f"Tanque {self.id_tanque} contiene {self.variedad}; no mezclar con {variedad}.")

        self.variedad = variedad
        self.temperatura_c = temp_entrada
        self.estado = "ALMACENANDO"

        if litros <= self.volumen_disponible_l:
            self.volumen_actual_l += litros
            return 0.0
        excedente = litros - self.volumen_disponible_l
        self.volumen_actual_l = self.capacidad_max_l
        return excedente

    def extraer_zumo(self, litros: float) -> float:
        """Extrae zumo hacia homogeneización. Devuelve los litros extraídos."""
        if litros >= self.volumen_actual_l:
            extraido = self.volumen_actual_l
            self.volumen_actual_l = 0.0
            self.variedad = None
            self.dias_almacenado = 0
            self.estado = "SUCIO_CIP"
            return extraido
        self.volumen_actual_l -= litros
        return litros

    def calcular_y_ejecutar_cip(self, long_tuberia_m: float = 22.0,
                                diam_tuberia_pulg: float = 2.0) -> Dict[str, float]:
        """Calcula requerimientos de limpieza CIP según metodología del Anejo 2 del TFG."""
        vol_deposito_l = 0.015 * self.capacidad_max_l  # 1.5 % de la capacidad nominal
        diam_m = diam_tuberia_pulg * 0.0254
        vol_tuberia_l = math.pi * (diam_m / 2.0) ** 2 * long_tuberia_m * 1000.0
        vol_limpieza_l = 1.2 * (vol_deposito_l + vol_tuberia_l)  # factor de seguridad 1.2

        naoh_kg = vol_limpieza_l * 0.01    # NaOH 1 %
        hno3_kg = vol_limpieza_l * 0.008   # HNO3 0.8 %

        caudal_cip_lh = 21_546.82 if self.capacidad_max_l >= 100_000 else 11_000.0
        tiempo_min = vol_limpieza_l / caudal_cip_lh * 60.0

        self.estado = "LIMPIO_VACIO"
        return {
            "volumen_cip_l": round(vol_limpieza_l, 2),
            "naoh_1_pct_kg": round(naoh_kg, 2),
            "hno3_08_pct_kg": round(hno3_kg, 2),
            "caudal_cip_lh": caudal_cip_lh,
            "tiempo_recirculacion_min": round(tiempo_min, 2),
        }


# --------------------------------------------------------------------------- #
# Planta
# --------------------------------------------------------------------------- #
class PlantaTanquesAsepticos:
    def __init__(self, config: ConfigPlanta):
        self.config = config
        self.tanques: List[TanqueAseptico] = []
        self._construir_parque_tanques()

    def _construir_parque_tanques(self) -> None:
        c = self.config
        self.tanques.clear()
        for i in range(1, c.num_tanques_grandes + 1):
            self.tanques.append(TanqueAseptico(
                id_tanque=f"TA-G-{i:02d}", capacidad_max_l=c.cap_tanque_grande_l,
                diametro_int_m=4.60, altura_cilindro_m=6.00, altura_cono_m=0.85,
                temperatura_c=c.temp_operacion_c, presion_n2_bar=c.presion_n2_bar))
        for i in range(1, c.num_tanques_medianos + 1):
            self.tanques.append(TanqueAseptico(
                id_tanque=f"TA-M-{i:02d}", capacidad_max_l=c.cap_tanque_mediano_l,
                diametro_int_m=3.40, altura_cilindro_m=5.50, altura_cono_m=0.45,
                temperatura_c=c.temp_operacion_c, presion_n2_bar=c.presion_n2_bar))

    # ---- consultas ------------------------------------------------------- #
    @property
    def capacidad_total_l(self) -> float:
        return sum(t.capacidad_max_l for t in self.tanques)

    @property
    def volumen_total_l(self) -> float:
        return sum(t.volumen_actual_l for t in self.tanques)

    def inventario_por_variedad(self) -> Dict[str, float]:
        inv = {v: 0.0 for v in VARIEDADES}
        for t in self.tanques:
            if t.variedad in inv:
                inv[t.variedad] += t.volumen_actual_l
        return inv

    def tanques_sucios(self) -> List[TanqueAseptico]:
        return [t for t in self.tanques if t.estado == "SUCIO_CIP"]

    # ---- operaciones internas ------------------------------------------- #
    def _ingresar(self, variedad: str, litros: float, temp: float) -> float:
        """Llena primero tanques de la misma variedad y luego tanques limpios. Devuelve el sobrante."""
        restante = litros
        for t in self.tanques:
            if t.variedad == variedad and t.volumen_disponible_l > 0 and t.estado != "SUCIO_CIP":
                restante = t.ingresar_zumo(restante, variedad, temp)
                if restante <= EPS:
                    return 0.0
        for t in self.tanques:
            if t.estado == "LIMPIO_VACIO":
                restante = t.ingresar_zumo(restante, variedad, temp)
                if restante <= EPS:
                    return 0.0
        return restante

    def _extraer_mezcla(self, litros_totales: float) -> None:
        """Extrae en proporción 1/1/1 (se asume que ya se comprobó el stock)."""
        por_var = litros_totales / len(VARIEDADES)
        for var in VARIEDADES:
            por_extraer = por_var
            for t in self.tanques:
                if t.variedad == var and t.volumen_actual_l > 0:
                    por_extraer -= t.extraer_zumo(por_extraer)
                    if por_extraer <= EPS:
                        break

    # ---- operaciones públicas ------------------------------------------- #
    def recibir_zumo(self, variedad: str, litros: float, temp_entrada: float) -> Resultado:
        alertas = []
        if not (-1.0 <= temp_entrada <= 0.0):
            alertas.append(f"Temperatura de entrada ({temp_entrada} °C) fuera del rango óptimo (-1.0 a 0.0 °C).")

        restante = self._ingresar(variedad, litros, temp_entrada)
        masa_kg = litros * self.config.densidad_kg_l
        if restante > EPS:
            return Resultado("error",
                             f"Se ingresaron {litros - restante:,.2f} L, pero {restante:,.2f} L NO cupieron.",
                             alertas)
        return Resultado("ok", f"Ingresados {litros:,.2f} L ({masa_kg:,.2f} kg) de {variedad}.", alertas)

    def enviar_a_homogeneizacion(self, litros_totales: float) -> Resultado:
        por_var = litros_totales / len(VARIEDADES)
        for var, disponible in self.inventario_por_variedad().items():
            if disponible < por_var - EPS:
                return Resultado("error",
                                 f"BLOQUEO DE ENVASADO: stock insuficiente de '{var}'. "
                                 f"Disponible: {disponible:,.2f} L | Requerido: {por_var:,.2f} L.")
        self._extraer_mezcla(litros_totales)
        masa_kg = litros_totales * self.config.densidad_kg_l
        return Resultado("ok", f"Enviados {litros_totales:,.2f} L ({masa_kg:,.2f} kg) a Homogeneización "
                               f"({por_var:,.2f} L de cada variedad).")

    def ejecutar_cip_sucios(self, long_tuberia_m: float = 22.0) -> List[Dict]:
        """Limpia todos los tanques sucios. Devuelve una fila por tanque."""
        filas = []
        for t in self.tanques_sucios():
            res = t.calcular_y_ejecutar_cip(long_tuberia_m=long_tuberia_m)
            filas.append({"tanque": t.id_tanque, **res})
        return filas

    def simular_campana_anual(self) -> Dict:
        """Simula 365 días sobre una planta NUEVA (no modifica el estado actual).

        Calendario (día 1 = 1 de diciembre): ingreso L-V durante los primeros 121 días;
        envasado 2 días/semana desde el día 46 hasta cumplir `dias_envasado_anio`.
        Devuelve un dict con los totales y el historial diario.
        """
        sim = PlantaTanquesAsepticos(self.config)
        cfg = self.config
        total_ingresado = total_envasado = pico = 0.0
        dias_envasado = alertas_caducidad = 0
        historial = []

        for dia in range(1, 366):
            for t in sim.tanques:
                if t.volumen_actual_l > 0:
                    t.dias_almacenado += 1
                    if t.dias_almacenado > cfg.dias_max_retencion:
                        alertas_caducidad += 1

            # 1. Ingreso
            es_dia_habil = (dia % 7) not in (6, 0)
            if dia <= 121 and es_dia_habil:
                if dia < 15:
                    var_hoy = "Washington Navel"
                elif dia < 46:
                    var_hoy = "Washington Navel" if dia % 2 == 0 else "Salustiana"
                else:
                    activas = VARIEDADES if dia <= 90 else ["Salustiana", "Navelate"]
                    var_hoy = activas[dia % len(activas)]
                restante = sim._ingresar(var_hoy, cfg.caudal_entrada_l_dia, cfg.temp_operacion_c)
                total_ingresado += cfg.caudal_entrada_l_dia - restante

            # 2. Envasado
            if dia >= 46 and dia % 7 in (2, 5) and dias_envasado < cfg.dias_envasado_anio:
                req_var = cfg.caudal_salida_l_dia / len(VARIEDADES)
                if all(v >= req_var for v in sim.inventario_por_variedad().values()):
                    sim._extraer_mezcla(cfg.caudal_salida_l_dia)
                    total_envasado += cfg.caudal_salida_l_dia
                    dias_envasado += 1

            # 3. CIP automático
            sim.ejecutar_cip_sucios()

            total = sim.volumen_total_l
            pico = max(pico, total)
            historial.append({"dia": dia, "total_l": total, **sim.inventario_por_variedad()})

        return {
            "capacidad_total_l": sim.capacidad_total_l,
            "pico_ocupacion_l": pico,
            "pico_ocupacion_pct": pico / sim.capacidad_total_l * 100 if sim.capacidad_total_l else 0.0,
            "total_ingresado_l": total_ingresado,
            "total_ingresado_kg": total_ingresado * cfg.densidad_kg_l,
            "total_envasado_l": total_envasado,
            "jornadas_envasado": dias_envasado,
            "inventario_final": sim.inventario_por_variedad(),
            "alertas_caducidad": alertas_caducidad,
            "historial": historial,
        }


# =========================================================================== #
# INTERFAZ
# =========================================================================== #
st.set_page_config(page_title="Tanques Asépticos", page_icon="🍊", layout="wide")


# ----------------------------- estado de sesión ----------------------------- #
def reiniciar_planta(config: ConfigPlanta) -> None:
    st.session_state.tanques_config = config
    st.session_state.tanques_planta = PlantaTanquesAsepticos(config)
    st.session_state.tanques_simulacion = None


if "tanques_planta" not in st.session_state:
    reiniciar_planta(ConfigPlanta())

config: ConfigPlanta = st.session_state.tanques_config
planta: PlantaTanquesAsepticos = st.session_state.tanques_planta


def mostrar(resultado) -> None:
    """Guarda el mensaje para mostrarlo tras el rerun (así las tablas se refrescan)."""
    st.session_state.tanques_flash = resultado


def mostrar_flash() -> None:
    res = st.session_state.pop("tanques_flash", None)
    if res is None:
        return
    for alerta in res.alertas:
        st.warning(f"⚠️ {alerta}")
    {"ok": st.success, "warning": st.warning, "error": st.error}[res.nivel](res.mensaje)


# --------------------------------- sidebar ---------------------------------- #
with st.sidebar:
    st.header("⚙️ Parámetros de la planta")
    with st.form("form_config"):
        c = config
        n_g = st.number_input("Nº tanques grandes", 0, 100, c.num_tanques_grandes)
        cap_g = st.number_input("Capacidad tanque grande (L)", 0.0, value=c.cap_tanque_grande_l, step=1000.0)
        n_m = st.number_input("Nº tanques medianos", 0, 100, c.num_tanques_medianos)
        cap_m = st.number_input("Capacidad tanque mediano (L)", 0.0, value=c.cap_tanque_mediano_l, step=1000.0)
        dens = st.number_input("Densidad zumo (kg/L)", 0.0, value=c.densidad_kg_l, step=0.001, format="%.3f")
        q_in = st.number_input("Caudal entrada (L/día)", 0.0, value=c.caudal_entrada_l_dia, step=100.0)
        q_out = st.number_input("Caudal salida (L/día)", 0.0, value=c.caudal_salida_l_dia, step=100.0)
        d_env = st.number_input("Días de envasado al año", 0, 365, c.dias_envasado_anio)
        temp = st.number_input("Temperatura almacenamiento (°C)", value=c.temp_operacion_c, step=0.1)
        n2 = st.number_input("Sobrepresión N₂ (bar)", 0.0, value=c.presion_n2_bar, step=0.05)
        d_ret = st.number_input("Retención máxima (días)", 0, 3650, c.dias_max_retencion)
        if st.form_submit_button("Aplicar y reiniciar planta", type="primary"):
            reiniciar_planta(ConfigPlanta(n_g, cap_g, n_m, cap_m, dens, q_in, q_out, d_env, temp, n2, d_ret))
            mostrar(Resultado("ok", "Parámetros actualizados y planta reiniciada."))
            st.rerun()

# ---------------------------------- cuerpo ---------------------------------- #
st.title("🍊 Etapa de Tanques Asépticos")
mostrar_flash()

tab_estado, tab_ingreso, tab_salida, tab_cip, tab_sim = st.tabs(
    ["📊 Estado", "⬇️ Ingresar zumo", "⬆️ Extraer mezcla 1/1/1", "🧼 Limpieza CIP", "📅 Simulación anual"]
)

# ---- Estado ---- #
with tab_estado:
    vol = planta.volumen_total_l
    cap = planta.capacidad_total_l
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Capacidad total", f"{cap:,.0f} L")
    m2.metric("Volumen almacenado", f"{vol:,.0f} L")
    m3.metric("Ocupación", f"{vol / cap * 100 if cap else 0:.1f} %")
    m4.metric("Tanques sucios (CIP)", len(planta.tanques_sucios()))

    df = pd.DataFrame([{
        "ID": t.id_tanque, "Capacidad (L)": t.capacidad_max_l, "Volumen (L)": round(t.volumen_actual_l, 2),
        "% Lleno": t.porcentaje_llenado, "Variedad": t.variedad or "---", "Estado": t.estado,
        "Días almacenado": t.dias_almacenado,
    } for t in planta.tanques])
    st.dataframe(
        df, hide_index=True, use_container_width=True,
        column_config={"% Lleno": st.column_config.ProgressColumn("% Lleno", min_value=0, max_value=100, format="%.1f%%")},
    )

    st.subheader("Inventario por variedad (L)")
    inv = pd.Series(planta.inventario_por_variedad(), name="Litros")
    st.bar_chart(inv)

# ---- Ingreso ---- #
with tab_ingreso:
    with st.form("form_ingreso"):
        variedad = st.selectbox("Variedad de naranja", VARIEDADES)
        litros = st.number_input("Litros a ingresar", 0.0, value=float(config.caudal_entrada_l_dia), step=100.0)
        t_in = st.number_input("Temperatura de entrada (°C)", value=float(config.temp_operacion_c), step=0.1)
        if st.form_submit_button("Ingresar lote", type="primary"):
            mostrar(planta.recibir_zumo(variedad, litros, t_in))
            st.rerun()

# ---- Salida ---- #
with tab_salida:
    with st.form("form_salida"):
        litros_out = st.number_input("Litros totales a enviar a Homogeneización", 0.0,
                                     value=float(config.caudal_salida_l_dia), step=100.0)
        if st.form_submit_button("Extraer mezcla", type="primary"):
            mostrar(planta.enviar_a_homogeneizacion(litros_out))
            st.rerun()

# ---- CIP ---- #
with tab_cip:
    sucios = planta.tanques_sucios()
    if not sucios:
        st.info("No hay tanques pendientes de limpieza CIP.")
    else:
        st.write("Pendientes: " + ", ".join(t.id_tanque for t in sucios))
        long_tub = st.number_input("Longitud de tubería del circuito CIP (m)", 0.0, value=22.0, step=1.0)
        if st.button("Ejecutar CIP en todos los tanques sucios", type="primary"):
            st.session_state.tanques_cip_resultado = planta.ejecutar_cip_sucios(long_tub)
            st.rerun()
    if st.session_state.get("tanques_cip_resultado"):
        st.success("Limpieza CIP completada")
        st.dataframe(pd.DataFrame(st.session_state.pop("tanques_cip_resultado")), hide_index=True, use_container_width=True)

# ---- Simulación ---- #
with tab_sim:
    st.caption("Simula 365 días (día 1 = 1 de diciembre) sobre una planta nueva; no modifica el estado actual.")
    if st.button("▶️ Ejecutar simulación anual", type="primary"):
        with st.spinner("Simulando..."):
            st.session_state.tanques_simulacion = planta.simular_campana_anual()

    sim = st.session_state.get("tanques_simulacion")
    if sim:
        a, b, c_, d = st.columns(4)
        a.metric("Pico de ocupación", f"{sim['pico_ocupacion_l']:,.0f} L", f"{sim['pico_ocupacion_pct']:.1f} %", delta_color="off")
        b.metric("Zumo ingresado", f"{sim['total_ingresado_l']:,.0f} L")
        c_.metric("Zumo envasado", f"{sim['total_envasado_l']:,.0f} L", f"{sim['jornadas_envasado']} jornadas", delta_color="off")
        d.metric(f"Alertas > {config.dias_max_retencion} d", sim["alertas_caducidad"])

        hist = pd.DataFrame(sim["historial"]).set_index("dia")
        st.subheader("Evolución del inventario por variedad (L)")
        st.area_chart(hist[VARIEDADES])
        st.subheader("Inventario remanente a fin de año (L)")
        st.dataframe(pd.DataFrame([sim["inventario_final"]]).round(2), hide_index=True)
