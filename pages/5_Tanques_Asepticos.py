"""Página Streamlit - Almacén de tanques asépticos (todo en un solo archivo).

Un único almacén general de zumo de naranja (sin separar por variedad).
Los valores por defecto salen del TFG (Anejo 2) y se pueden modificar en la barra lateral,
salvo la densidad, que es fija en todo el proceso.
"""
import math
from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd
import streamlit as st

# =========================================================================== #
# MODELO
# =========================================================================== #
EPS = 1e-6
DENSIDAD_KG_L = 1.045  # TFG, Anejo 2, Tabla 11. Fija en todo el proceso (no editable).

LIMPIO, ALMACENANDO, SUCIO = "LIMPIO_VACIO", "ALMACENANDO", "SUCIO_CIP"
ESTADOS = {LIMPIO: "Limpio y vacío", ALMACENANDO: "Almacenando", SUCIO: "Sucio (pendiente CIP)"}


@dataclass
class ConfigPlanta:
    num_tanques_grandes: int = 6
    cap_tanque_grande_l: float = 100_000.0
    num_tanques_medianos: int = 12
    cap_tanque_mediano_l: float = 50_000.0
    caudal_entrada_l_dia: float = 17_241.38
    caudal_salida_l_dia: float = 15_000.0
    dias_envasado_anio: int = 100
    temp_operacion_c: float = -0.5
    presion_n2_bar: float = 0.2
    dias_max_retencion: int = 365


@dataclass
class Resultado:
    """nivel = 'ok' | 'warning' | 'error'."""
    nivel: str
    mensaje: str
    alertas: List[str] = field(default_factory=list)


@dataclass
class TanqueAseptico:
    id_tanque: str
    capacidad_max_l: float
    diametro_int_m: float
    altura_cilindro_m: float
    altura_cono_m: float
    volumen_actual_l: float = 0.0
    temperatura_c: float = -0.5
    presion_n2_bar: float = 0.2
    estado: str = LIMPIO
    dias_almacenado: int = 0

    @property
    def volumen_disponible_l(self) -> float:
        return self.capacidad_max_l - self.volumen_actual_l

    @property
    def porcentaje_llenado(self) -> float:
        return self.volumen_actual_l / self.capacidad_max_l * 100.0 if self.capacidad_max_l > 0 else 0.0

    def ingresar_zumo(self, litros: float, temp_entrada: float) -> float:
        """Ingresa zumo. Devuelve los litros que no cupieron."""
        if self.estado == SUCIO:
            raise ValueError(f"Tanque {self.id_tanque} requiere limpieza CIP antes de recibir producto.")
        self.temperatura_c = temp_entrada
        self.estado = ALMACENANDO
        libre = self.volumen_disponible_l
        if litros <= libre:
            self.volumen_actual_l += litros
            return 0.0
        self.volumen_actual_l = self.capacidad_max_l
        return litros - libre

    def extraer_zumo(self, litros: float) -> float:
        """Extrae zumo. Devuelve los litros extraídos. Si queda vacío pasa a SUCIO_CIP."""
        if litros >= self.volumen_actual_l - EPS:
            extraido = self.volumen_actual_l
            self.volumen_actual_l = 0.0
            self.dias_almacenado = 0
            self.estado = SUCIO
            return extraido
        self.volumen_actual_l -= litros
        return litros

    def vaciar(self) -> float:
        """Vacía el tanque por completo (queda sucio). Devuelve los litros vaciados."""
        if self.estado == LIMPIO:
            return 0.0
        return self.extraer_zumo(self.volumen_actual_l)

    def calcular_y_ejecutar_cip(self, long_tuberia_m: float = 22.0,
                                diam_tuberia_pulg: float = 2.0) -> Dict[str, float]:
        """Limpieza CIP según el Anejo 2 del TFG. El tanque debe estar vacío."""
        if self.volumen_actual_l > EPS:
            raise ValueError(f"Tanque {self.id_tanque} aún tiene producto: vacíalo antes de limpiar.")
        vol_deposito_l = 0.015 * self.capacidad_max_l                      # 1,5 % de la capacidad
        diam_m = diam_tuberia_pulg * 0.0254
        vol_tuberia_l = math.pi * (diam_m / 2.0) ** 2 * long_tuberia_m * 1000.0
        vol_limpieza_l = 1.2 * (vol_deposito_l + vol_tuberia_l)            # coef. de seguridad 1,2
        naoh_kg = vol_limpieza_l * 0.01                                    # NaOH al 1 %
        hno3_kg = vol_limpieza_l * 0.008                                   # HNO3 al 0,8 %
        caudal_cip_lh = 21_546.82 if self.capacidad_max_l >= 100_000 else 11_000.0
        tiempo_min = vol_limpieza_l / caudal_cip_lh * 60.0
        self.estado = LIMPIO
        return {
            "Volumen solución (L)": round(vol_limpieza_l, 2),
            "NaOH 1 % (kg)": round(naoh_kg, 2),
            "HNO3 0,8 % (kg)": round(hno3_kg, 2),
            "Caudal CIP (L/h)": caudal_cip_lh,
            "Tiempo recirculación (min)": round(tiempo_min, 2),
        }


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
                f"TA-G-{i:02d}", c.cap_tanque_grande_l, 4.60, 6.00, 0.85,
                temperatura_c=c.temp_operacion_c, presion_n2_bar=c.presion_n2_bar))
        for i in range(1, c.num_tanques_medianos + 1):
            self.tanques.append(TanqueAseptico(
                f"TA-M-{i:02d}", c.cap_tanque_mediano_l, 3.40, 5.50, 0.45,
                temperatura_c=c.temp_operacion_c, presion_n2_bar=c.presion_n2_bar))

    # ---- consultas ---- #
    @property
    def capacidad_total_l(self) -> float:
        return sum(t.capacidad_max_l for t in self.tanques)

    @property
    def volumen_total_l(self) -> float:
        return sum(t.volumen_actual_l for t in self.tanques)

    @property
    def masa_total_kg(self) -> float:
        return self.volumen_total_l * DENSIDAD_KG_L

    @property
    def porcentaje_ocupacion(self) -> float:
        cap = self.capacidad_total_l
        return self.volumen_total_l / cap * 100.0 if cap > 0 else 0.0

    def tanques_sucios(self) -> List[TanqueAseptico]:
        return [t for t in self.tanques if t.estado == SUCIO]

    # ---- internas ---- #
    def _ingresar(self, litros: float, temp: float) -> float:
        """Llena primero los tanques ya en uso y luego los limpios. Devuelve el sobrante."""
        restante = litros
        for t in self.tanques:
            if t.estado == ALMACENANDO and t.volumen_disponible_l > 0:
                restante = t.ingresar_zumo(restante, temp)
                if restante <= EPS:
                    return 0.0
        for t in self.tanques:
            if t.estado == LIMPIO:
                restante = t.ingresar_zumo(restante, temp)
                if restante <= EPS:
                    return 0.0
        return restante

    def _extraer(self, litros: float) -> None:
        """Extrae del almacén (primero el zumo más antiguo y los tanques más vacíos)."""
        por_extraer = litros
        con_producto = [t for t in self.tanques if t.volumen_actual_l > EPS]
        for t in sorted(con_producto, key=lambda t: (-t.dias_almacenado, t.volumen_actual_l)):
            por_extraer -= t.extraer_zumo(por_extraer)
            if por_extraer <= EPS:
                break

    # ---- operaciones públicas ---- #
    def recibir_zumo(self, litros: float, temp_entrada: float) -> Resultado:
        if litros <= 0:
            return Resultado("warning", "Indica una cantidad mayor que 0.")
        alertas = []
        if not (-1.0 <= temp_entrada <= 0.0):
            alertas.append(f"Temperatura de entrada ({temp_entrada} °C) fuera del rango óptimo (-1,0 a 0,0 °C).")
        restante = self._ingresar(litros, temp_entrada)
        if restante > EPS:
            return Resultado("warning", f"Almacén lleno: se ingresaron {litros - restante:,.2f} L y "
                                        f"{restante:,.2f} L NO cupieron.", alertas)
        return Resultado("ok", f"Ingresados {litros:,.2f} L ({litros * DENSIDAD_KG_L:,.2f} kg). "
                               f"Almacén: {self.volumen_total_l:,.2f} L ({self.porcentaje_ocupacion:.1f} %).", alertas)

    def enviar_a_homogeneizacion(self, litros: float) -> Resultado:
        if litros <= 0:
            return Resultado("warning", "Indica una cantidad mayor que 0.")
        if litros > self.volumen_total_l + EPS:
            return Resultado("error", f"Stock insuficiente. Disponible: {self.volumen_total_l:,.2f} L | "
                                      f"Solicitado: {litros:,.2f} L.")
        self._extraer(litros)
        return Resultado("ok", f"Enviados {litros:,.2f} L ({litros * DENSIDAD_KG_L:,.2f} kg) a Homogeneización. "
                               f"Quedan {self.volumen_total_l:,.2f} L en el almacén ({self.porcentaje_ocupacion:.1f} %).")

    def _por_ids(self, ids: List[str]) -> List[TanqueAseptico]:
        return [t for t in self.tanques if t.id_tanque in set(ids)]

    def vaciar_tanques(self, ids: List[str]) -> float:
        """Vacía los tanques indicados (quedan sucios). Devuelve los litros vaciados."""
        return sum(t.vaciar() for t in self._por_ids(ids))

    def limpiar_tanques(self, ids: List[str], long_tuberia_m: float = 22.0) -> List[Dict]:
        """CIP de los tanques indicados que estén vacíos y sucios. Devuelve una fila por tanque."""
        filas = []
        for t in self._por_ids(ids):
            if t.estado == SUCIO and t.volumen_actual_l <= EPS:
                filas.append({"Tanque": t.id_tanque, **t.calcular_y_ejecutar_cip(long_tuberia_m)})
        return filas

    def simular_campana_anual(self) -> Dict:
        """Simula 365 días (día 1 = 1 de diciembre) sobre una planta NUEVA; no toca el estado actual.

        Ingreso: lunes a viernes durante los primeros 121 días (1 dic - 31 mar).
        Envasado: 2 días por semana desde el día 46 (mediados de enero), hasta cumplir los días anuales.
        """
        sim = PlantaTanquesAsepticos(self.config)
        cfg = self.config
        total_in = total_rechazado = total_out = pico = 0.0
        jornadas = alertas = 0
        historial = []
        for dia in range(1, 366):
            for t in sim.tanques:
                if t.volumen_actual_l > EPS:
                    t.dias_almacenado += 1
                    if t.dias_almacenado > cfg.dias_max_retencion:
                        alertas += 1

            if dia <= 121 and (dia % 7) not in (6, 0):
                restante = sim._ingresar(cfg.caudal_entrada_l_dia, cfg.temp_operacion_c)
                total_in += cfg.caudal_entrada_l_dia - restante
                total_rechazado += restante

            if dia >= 46 and dia % 7 in (2, 5) and jornadas < cfg.dias_envasado_anio:
                if sim.volumen_total_l >= cfg.caudal_salida_l_dia - EPS:
                    sim._extraer(cfg.caudal_salida_l_dia)
                    total_out += cfg.caudal_salida_l_dia
                    jornadas += 1

            sim.limpiar_tanques([t.id_tanque for t in sim.tanques_sucios()])
            pico = max(pico, sim.volumen_total_l)
            historial.append({"dia": dia, "volumen_l": sim.volumen_total_l})

        cap = sim.capacidad_total_l
        return {
            "capacidad_total_l": cap,
            "pico_ocupacion_l": pico,
            "pico_ocupacion_pct": pico / cap * 100 if cap else 0.0,
            "total_ingresado_l": total_in,
            "total_ingresado_kg": total_in * DENSIDAD_KG_L,
            "total_rechazado_l": total_rechazado,
            "total_envasado_l": total_out,
            "jornadas_envasado": jornadas,
            "inventario_final_l": sim.volumen_total_l,
            "alertas_caducidad": alertas,
            "historial": historial,
        }


# =========================================================================== #
# INTERFAZ
# =========================================================================== #
st.set_page_config(page_title="Tanques Asépticos", page_icon="🍊", layout="wide")


def reiniciar_planta(config: ConfigPlanta) -> None:
    st.session_state.tanques_config = config
    st.session_state.tanques_planta = PlantaTanquesAsepticos(config)
    st.session_state.tanques_simulacion = None


if "tanques_planta" not in st.session_state:
    reiniciar_planta(ConfigPlanta())

config: ConfigPlanta = st.session_state.tanques_config
planta: PlantaTanquesAsepticos = st.session_state.tanques_planta


def mostrar(resultado: Resultado) -> None:
    """Guarda el mensaje para mostrarlo tras el rerun (así tablas y métricas se refrescan)."""
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
    st.header("⚙️ Parámetros del almacén")
    st.caption(f"Densidad del zumo: **{DENSIDAD_KG_L:.3f} kg/L**, fija en todo el proceso (TFG, Tabla 11).")
    with st.form("tanques_form_config"):
        c = config
        n_g = st.number_input("Nº tanques grandes", min_value=0, max_value=100, step=1,
                              value=int(c.num_tanques_grandes), help="TFG: 6 tanques asépticos de 100 m³.")
        cap_g = st.number_input("Capacidad tanque grande (L)", min_value=0.0, step=1000.0,
                                value=float(c.cap_tanque_grande_l), help="TFG, Tabla 41: 100.000 L.")
        n_m = st.number_input("Nº tanques medianos", min_value=0, max_value=100, step=1,
                              value=int(c.num_tanques_medianos), help="TFG: 12 tanques asépticos de 50 m³.")
        cap_m = st.number_input("Capacidad tanque mediano (L)", min_value=0.0, step=1000.0,
                                value=float(c.cap_tanque_mediano_l), help="TFG, Tabla 42: 50.000 L.")
        q_in = st.number_input("Caudal de entrada (L/día)", min_value=0.0, step=100.0,
                               value=float(c.caudal_entrada_l_dia),
                               help="TFG: 17.241,38 L/día, de lunes a viernes (87 días, 1 dic - 31 mar).")
        q_out = st.number_input("Caudal de salida (L/día)", min_value=0.0, step=100.0,
                                value=float(c.caudal_salida_l_dia), help="TFG: 15.000 L/día de envasado.")
        d_env = st.number_input("Días de envasado al año", min_value=0, max_value=365, step=1,
                                value=int(c.dias_envasado_anio), help="TFG: 100 días (2 días por semana).")
        temp = st.number_input("Temperatura de almacenamiento (°C)", step=0.1, format="%.1f",
                               value=float(c.temp_operacion_c),
                               help="TFG: entre -1 y 0 °C. El valor por defecto es el punto medio.")
        n2 = st.number_input("Sobrepresión de N₂ (bar)", min_value=0.0, step=0.05,
                             value=float(c.presion_n2_bar),
                             help="Valor supuesto: el TFG solo indica atmósfera protectora de N₂ o aire estéril.")
        d_ret = st.number_input("Retención máxima (días)", min_value=0, max_value=3650, step=1,
                                value=int(c.dias_max_retencion), help="TFG: no más de un año.")
        if st.form_submit_button("Aplicar y reiniciar almacén", type="primary"):
            reiniciar_planta(ConfigPlanta(
                num_tanques_grandes=int(n_g), cap_tanque_grande_l=float(cap_g),
                num_tanques_medianos=int(n_m), cap_tanque_mediano_l=float(cap_m),
                caudal_entrada_l_dia=float(q_in), caudal_salida_l_dia=float(q_out),
                dias_envasado_anio=int(d_env), temp_operacion_c=float(temp),
                presion_n2_bar=float(n2), dias_max_retencion=int(d_ret)))
            mostrar(Resultado("ok", "Parámetros actualizados y almacén reiniciado."))
            st.rerun()

# ---------------------------------- cuerpo ---------------------------------- #
st.title("🍊 Almacén de tanques asépticos")
mostrar_flash()

tab_estado, tab_ingreso, tab_salida, tab_limpieza, tab_sim = st.tabs(
    ["📊 Estado", "⬇️ Ingresar zumo", "⬆️ Extraer zumo", "🧼 Vaciar y limpiar", "📅 Simulación anual"]
)

# ---- Estado ---- #
with tab_estado:
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Capacidad total", f"{planta.capacidad_total_l:,.0f} L")
    m2.metric("Zumo almacenado", f"{planta.volumen_total_l:,.0f} L")
    m3.metric("Ocupación", f"{planta.porcentaje_ocupacion:.1f} %")
    m4.metric("Masa almacenada", f"{planta.masa_total_kg:,.0f} kg")
    m5.metric("Tanques sucios (CIP)", len(planta.tanques_sucios()))

    df = pd.DataFrame([{
        "ID": t.id_tanque,
        "Capacidad (L)": t.capacidad_max_l,
        "Volumen (L)": round(t.volumen_actual_l, 2),
        "% Lleno": t.porcentaje_llenado,
        "Estado": ESTADOS[t.estado],
    } for t in planta.tanques])
    st.dataframe(
        df, hide_index=True,
        column_config={"% Lleno": st.column_config.ProgressColumn("% Lleno", min_value=0, max_value=100, format="%.1f")},
    )
    st.subheader("Volumen por tanque (L)")
    st.bar_chart(df.set_index("ID")["Volumen (L)"])

# ---- Ingreso ---- #
with tab_ingreso:
    st.caption(f"Espacio libre en el almacén: {planta.capacidad_total_l - planta.volumen_total_l:,.0f} L")
    with st.form("tanques_form_ingreso"):
        litros_in = st.number_input("Litros a ingresar", min_value=0.0, step=100.0,
                                    value=float(config.caudal_entrada_l_dia))
        temp_in = st.number_input("Temperatura de entrada (°C)", step=0.1, format="%.1f",
                                  value=float(config.temp_operacion_c))
        if st.form_submit_button("Ingresar zumo", type="primary"):
            mostrar(planta.recibir_zumo(float(litros_in), float(temp_in)))
            st.rerun()

# ---- Salida ---- #
with tab_salida:
    st.caption(f"Zumo disponible en el almacén: {planta.volumen_total_l:,.0f} L. "
               "La mezcla 1/1/1 de variedades se hace después, en Homogeneización.")
    with st.form("tanques_form_salida"):
        litros_out = st.number_input("Litros a enviar a Homogeneización", min_value=0.0, step=100.0,
                                     value=float(config.caudal_salida_l_dia))
        if st.form_submit_button("Extraer zumo", type="primary"):
            mostrar(planta.enviar_a_homogeneizacion(float(litros_out)))
            st.rerun()

# ---- Vaciar y limpiar ---- #
with tab_limpieza:
    if st.session_state.get("tanques_cip_resultado"):
        st.success("Limpieza CIP completada")
        st.dataframe(pd.DataFrame(st.session_state.pop("tanques_cip_resultado")), hide_index=True)

    no_limpios = [t for t in planta.tanques if t.estado != LIMPIO]
    if not no_limpios:
        st.info("Todos los tanques están limpios y vacíos.")
    else:
        st.write("Un tanque con zumo no se puede limpiar: primero hay que vaciarlo. "
                 "El zumo vaciado se descuenta del almacén.")
        etiquetas = {t.id_tanque: f"{t.id_tanque} · {t.volumen_actual_l:,.0f} L · {ESTADOS[t.estado]}"
                     for t in no_limpios}
        ids = st.multiselect(
            "Tanques a vaciar / limpiar", list(etiquetas), format_func=etiquetas.get,
            default=[t.id_tanque for t in no_limpios if t.estado == SUCIO])
        con_producto = [t for t in no_limpios if t.id_tanque in ids and t.volumen_actual_l > EPS]
        if con_producto:
            litros_perdidos = sum(t.volumen_actual_l for t in con_producto)
            st.warning(f"{len(con_producto)} tanque(s) seleccionado(s) contienen zumo ({litros_perdidos:,.0f} L), "
                       "que se retirará del almacén.")
            confirmado = st.checkbox("Confirmo que quiero vaciar el contenido de estos tanques")
        else:
            confirmado = True
        long_tub = st.number_input("Longitud de tubería del circuito CIP (m)", min_value=0.0, step=1.0, value=22.0)
        listo = bool(ids) and confirmado
        b1, b2 = st.columns(2)
        if b1.button("🗑️ Solo vaciar", disabled=not (listo and con_producto)):
            litros = planta.vaciar_tanques(ids)
            mostrar(Resultado("ok", f"Vaciados {litros:,.2f} L. Los tanques quedan pendientes de limpieza CIP."))
            st.rerun()
        if b2.button("🧼 Vaciar y limpiar (CIP)", type="primary", disabled=not listo):
            litros = planta.vaciar_tanques(ids)
            filas = planta.limpiar_tanques(ids, float(long_tub))
            st.session_state.tanques_cip_resultado = filas
            mostrar(Resultado("ok", f"Vaciados {litros:,.2f} L y limpiados {len(filas)} tanque(s)."))
            st.rerun()

# ---- Simulación ---- #
with tab_sim:
    st.caption("Simula 365 días (día 1 = 1 de diciembre) sobre un almacén nuevo; no modifica el estado actual.")
    if st.button("▶️ Ejecutar simulación anual", type="primary"):
        with st.spinner("Simulando..."):
            st.session_state.tanques_simulacion = planta.simular_campana_anual()

    sim = st.session_state.get("tanques_simulacion")
    if sim:
        a, b, c_, d, e = st.columns(5)
        a.metric("Pico de ocupación", f"{sim['pico_ocupacion_l']:,.0f} L", f"{sim['pico_ocupacion_pct']:.1f} %", delta_color="off")
        b.metric("Zumo ingresado", f"{sim['total_ingresado_l']:,.0f} L")
        c_.metric("Zumo envasado", f"{sim['total_envasado_l']:,.0f} L", f"{sim['jornadas_envasado']} jornadas", delta_color="off")
        d.metric("Remanente a fin de año", f"{sim['inventario_final_l']:,.0f} L")
        e.metric(f"Alertas > {config.dias_max_retencion} d", sim["alertas_caducidad"])
        if sim["total_rechazado_l"] > EPS:
            st.error(f"No cupieron {sim['total_rechazado_l']:,.0f} L: la capacidad del almacén es insuficiente.")
        if sim["jornadas_envasado"] < config.dias_envasado_anio:
            st.info(f"En los 365 días simulados se completaron {sim['jornadas_envasado']} de "
                    f"{config.dias_envasado_anio} jornadas de envasado.")

        hist = pd.DataFrame(sim["historial"]).set_index("dia")
        hist = hist.rename(columns={"volumen_l": "Zumo almacenado (L)"})
        hist["Capacidad total (L)"] = sim["capacidad_total_l"]
        st.subheader("Evolución del almacén (L)")
        st.line_chart(hist)
