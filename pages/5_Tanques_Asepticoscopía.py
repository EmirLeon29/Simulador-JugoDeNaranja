"""Página Streamlit - Almacén de tanques asépticos (todo en un solo archivo).

Un único almacén general de zumo de naranja formado por N tanques iguales.
- Parámetros del almacén: en la página principal.
- Operaciones (ingresar, extraer, vaciar/limpiar, temperatura y N2, simulación): en la barra lateral.
Los valores por defecto parten del TFG (Anejo 2) y se pueden modificar, salvo la densidad (fija).
"""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

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
    num_tanques: int = 12
    cap_tanque_l: float = 100_000.0
    caudal_entrada_l_dia: float = 17_241.38
    caudal_salida_l_dia: float = 15_000.0
    dias_envasado_anio: int = 100
    dias_max_retencion: int = 365
    # Temperatura de almacenamiento y rango en el que el zumo no corre riesgo (TFG: -1 a 0 °C)
    temp_operacion_c: float = -0.5
    temp_min_c: float = -1.0
    temp_max_c: float = 0.0
    # Sobrepresión de N2 y rango aceptable (valores supuestos: el TFG no los especifica)
    presion_n2_bar: float = 0.2
    n2_min_bar: float = 0.1
    n2_max_bar: float = 0.5


@dataclass
class Resultado:
    """nivel = 'ok' | 'warning' | 'error'."""
    nivel: str
    mensaje: str
    alertas: List[str] = field(default_factory=list)


def evaluar_temperatura(valor: float, t_min: float, t_max: float) -> Tuple[str, str, str]:
    """Devuelve (nivel, texto corto, texto largo)."""
    if valor < t_min - EPS:
        return ("error", "❄️ Riesgo de congelación",
                f"❄️ {valor:.1f} °C está por debajo de {t_min:.1f} °C: el zumo corre riesgo de congelarse.")
    if valor > t_max + EPS:
        return ("error", "🔥 Riesgo de deterioro",
                f"🔥 {valor:.1f} °C está por encima de {t_max:.1f} °C: el zumo corre riesgo de echarse a perder.")
    return "ok", "✅ Temperatura óptima", f"✅ {valor:.1f} °C: dentro del rango óptimo ({t_min:.1f} a {t_max:.1f} °C)."


def evaluar_n2(valor: float, n_min: float, n_max: float) -> Tuple[str, str, str]:
    """Devuelve (nivel, texto corto, texto largo)."""
    if valor < n_min - EPS:
        return ("error", "⚠️ N₂ bajo: sin atmósfera protectora",
                f"⚠️ {valor:.2f} bar está por debajo de {n_min:.2f} bar: se puede perder la atmósfera protectora "
                "y el zumo corre riesgo de oxidarse o contaminarse.")
    if valor > n_max + EPS:
        return ("warning", "⚠️ N₂ alto: sobrepresión",
                f"⚠️ {valor:.2f} bar está por encima de {n_max:.2f} bar: sobrepresión excesiva para el tanque.")
    return "ok", "✅ N₂ óptimo", f"✅ {valor:.2f} bar: dentro del rango aceptable ({n_min:.2f} a {n_max:.2f} bar)."


def _peor(*niveles: str) -> str:
    return "error" if "error" in niveles else ("warning" if "warning" in niveles else "ok")


@dataclass
class TanqueAseptico:
    id_tanque: str
    capacidad_max_l: float
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

    def ingresar_zumo(self, litros: float) -> float:
        """Ingresa zumo. Devuelve los litros que no cupieron."""
        if self.estado == SUCIO:
            raise ValueError(f"Tanque {self.id_tanque} requiere limpieza CIP antes de recibir producto.")
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
        self.tanques = [
            TanqueAseptico(f"TA-{i:02d}", c.cap_tanque_l,
                           temperatura_c=c.temp_operacion_c, presion_n2_bar=c.presion_n2_bar)
            for i in range(1, c.num_tanques + 1)
        ]

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

    def condicion_tanque(self, t: TanqueAseptico) -> Tuple[str, str]:
        """Evalúa temperatura y N2 del tanque. Devuelve (nivel, texto corto)."""
        c = self.config
        n_t, corto_t, _ = evaluar_temperatura(t.temperatura_c, c.temp_min_c, c.temp_max_c)
        n_n, corto_n, _ = evaluar_n2(t.presion_n2_bar, c.n2_min_bar, c.n2_max_bar)
        avisos = [txt for niv, txt in ((n_t, corto_t), (n_n, corto_n)) if niv != "ok"]
        return _peor(n_t, n_n), " · ".join(avisos) if avisos else "✅ Óptima"

    # ---- internas ---- #
    def _ingresar(self, litros: float) -> float:
        """Llena primero los tanques ya en uso y luego los limpios. Devuelve el sobrante."""
        restante = litros
        for t in self.tanques:
            if t.estado == ALMACENANDO and t.volumen_disponible_l > 0:
                restante = t.ingresar_zumo(restante)
                if restante <= EPS:
                    return 0.0
        for t in self.tanques:
            if t.estado == LIMPIO:
                restante = t.ingresar_zumo(restante)
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
        c = self.config
        alertas = []
        nivel_t, _, largo_t = evaluar_temperatura(temp_entrada, c.temp_min_c, c.temp_max_c)
        if nivel_t != "ok":
            alertas.append(f"Temperatura de entrada: {largo_t}")
        restante = self._ingresar(litros)
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

    def ajustar_condiciones(self, ids: List[str], temp_c: float, n2_bar: float) -> Resultado:
        """Cambia temperatura y presión de N2 de los tanques indicados (sin vaciarlos)."""
        tanques = self._por_ids(ids)
        if not tanques:
            return Resultado("warning", "Selecciona al menos un tanque.")
        for t in tanques:
            t.temperatura_c = temp_c
            t.presion_n2_bar = n2_bar
        c = self.config
        n_t, _, largo_t = evaluar_temperatura(temp_c, c.temp_min_c, c.temp_max_c)
        n_n, _, largo_n = evaluar_n2(n2_bar, c.n2_min_bar, c.n2_max_bar)
        base = f"Condiciones aplicadas a {len(tanques)} tanque(s): {temp_c:.1f} °C y {n2_bar:.2f} bar."
        nivel = _peor(n_t, n_n)
        if nivel == "ok":
            return Resultado("ok", f"{base} Dentro del rango óptimo.")
        detalle = " ".join(txt for niv, txt in ((n_t, largo_t), (n_n, largo_n)) if niv != "ok")
        if any(t.volumen_actual_l > EPS for t in tanques):
            return Resultado(nivel, f"{base} {detalle} Hay zumo almacenado en estos tanques.")
        return Resultado("warning", f"{base} {detalle} Los tanques están vacíos: corrígelo antes de llenarlos.")

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
                restante = sim._ingresar(cfg.caudal_entrada_l_dia)
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
    st.session_state.tanques_cip_resultado = None


if "tanques_planta" not in st.session_state:
    reiniciar_planta(ConfigPlanta())

config: ConfigPlanta = st.session_state.tanques_config
planta: PlantaTanquesAsepticos = st.session_state.tanques_planta


def aviso(nivel: str, texto: str, destino=st) -> None:
    {"ok": destino.success, "warning": destino.warning, "error": destino.error}[nivel](texto)


def mostrar(resultado: Resultado) -> None:
    """Guarda el mensaje para mostrarlo arriba de la página."""
    st.session_state.tanques_flash = resultado


def mostrar_flash() -> None:
    res = st.session_state.pop("tanques_flash", None)
    if res is None:
        return
    for alerta in res.alertas:
        st.warning(f"⚠️ {alerta}")
    aviso(res.nivel, res.mensaje)


def lista_ids(ids: List[str], maximo: int = 6) -> str:
    return ", ".join(ids[:maximo]) + (f" y {len(ids) - maximo} más" if len(ids) > maximo else "")


# --------------------------------- sidebar ---------------------------------- #
PANELES = ["⬇️ Ingresar zumo", "⬆️ Extraer zumo", "🧼 Vaciar y limpiar", "🌡️ Temperatura y N₂", "📅 Simulación anual"]

with st.sidebar:
    st.header("🎛️ Panel de control")
    st.caption("Los parámetros del almacén están en la página principal.")
    panel = st.selectbox("Acción", PANELES, key="tanques_panel")
    st.divider()

    # ---- Ingresar ---- #
    if panel == PANELES[0]:
        st.caption(f"Espacio libre: {planta.capacidad_total_l - planta.volumen_total_l:,.0f} L")
        with st.form("tanques_form_ingreso"):
            litros_in = st.number_input("Litros a ingresar", min_value=0.0, step=100.0,
                                        value=float(config.caudal_entrada_l_dia))
            temp_in = st.number_input("Temperatura de entrada del zumo (°C)", step=0.1, format="%.1f",
                                      value=float(config.temp_operacion_c))
            if st.form_submit_button("Ingresar zumo", type="primary"):
                mostrar(planta.recibir_zumo(float(litros_in), float(temp_in)))

    # ---- Extraer ---- #
    elif panel == PANELES[1]:
        st.caption(f"Zumo disponible: {planta.volumen_total_l:,.0f} L. "
                   "La mezcla 1/1/1 de variedades se hace después, en Homogeneización.")
        with st.form("tanques_form_salida"):
            litros_out = st.number_input("Litros a enviar a Homogeneización", min_value=0.0, step=100.0,
                                         value=float(config.caudal_salida_l_dia))
            if st.form_submit_button("Extraer zumo", type="primary"):
                mostrar(planta.enviar_a_homogeneizacion(float(litros_out)))

    # ---- Vaciar y limpiar ---- #
    elif panel == PANELES[2]:
        no_limpios = [t for t in planta.tanques if t.estado != LIMPIO]
        if not no_limpios:
            st.info("Todos los tanques están limpios y vacíos.")
        else:
            st.caption("Un tanque con zumo no se puede limpiar: primero hay que vaciarlo. "
                       "El zumo vaciado se descuenta del almacén.")
            etiquetas = {t.id_tanque: f"{t.id_tanque} · {t.volumen_actual_l:,.0f} L · {ESTADOS[t.estado]}"
                         for t in no_limpios}
            ids = st.multiselect(
                "Tanques a vaciar / limpiar", list(etiquetas), format_func=etiquetas.get,
                default=[t.id_tanque for t in no_limpios if t.estado == SUCIO])
            con_producto = [t for t in no_limpios if t.id_tanque in ids and t.volumen_actual_l > EPS]
            if con_producto:
                litros_perdidos = sum(t.volumen_actual_l for t in con_producto)
                st.warning(f"{len(con_producto)} tanque(s) contienen zumo ({litros_perdidos:,.0f} L), "
                           "que se retirará del almacén.")
                confirmado = st.checkbox("Confirmo que quiero vaciar el contenido de estos tanques")
            else:
                confirmado = True
            long_tub = st.number_input("Longitud de tubería del circuito CIP (m)", min_value=0.0,
                                       step=1.0, value=22.0)
            listo = bool(ids) and confirmado
            if st.button("🗑️ Solo vaciar", disabled=not (listo and con_producto)):
                litros = planta.vaciar_tanques(ids)
                mostrar(Resultado("ok", f"Vaciados {litros:,.2f} L. Los tanques quedan pendientes de limpieza CIP."))
            if st.button("🧼 Vaciar y limpiar (CIP)", type="primary", disabled=not listo):
                litros = planta.vaciar_tanques(ids)
                filas = planta.limpiar_tanques(ids, float(long_tub))
                st.session_state.tanques_cip_resultado = filas
                mostrar(Resultado("ok", f"Vaciados {litros:,.2f} L y limpiados {len(filas)} tanque(s)."))

    # ---- Temperatura y N2 ---- #
    elif panel == PANELES[3]:
        st.caption("Cambia las condiciones de los tanques elegidos sin vaciarlos. El zumo debe mantenerse "
                   "dentro del rango óptimo todo el tiempo; si te sales, se avisa del riesgo.")
        etiquetas = {t.id_tanque: f"{t.id_tanque} · {t.temperatura_c:.1f} °C · {t.presion_n2_bar:.2f} bar"
                     for t in planta.tanques}
        ids_c = st.multiselect("Tanques", list(etiquetas), format_func=etiquetas.get,
                               default=list(etiquetas))
        nueva_t = st.number_input("Temperatura (°C)", step=0.1, format="%.1f",
                                  value=float(config.temp_operacion_c))
        nivel_t, _, largo_t = evaluar_temperatura(float(nueva_t), config.temp_min_c, config.temp_max_c)
        aviso(nivel_t, largo_t)
        nuevo_n2 = st.number_input("Sobrepresión de N₂ (bar)", min_value=0.0, step=0.05, format="%.2f",
                                   value=float(config.presion_n2_bar))
        nivel_n, _, largo_n = evaluar_n2(float(nuevo_n2), config.n2_min_bar, config.n2_max_bar)
        aviso(nivel_n, largo_n)
        if st.button("Aplicar a los tanques seleccionados", type="primary", disabled=not ids_c):
            mostrar(planta.ajustar_condiciones(ids_c, float(nueva_t), float(nuevo_n2)))

    # ---- Simulación ---- #
    else:
        st.caption("Simula 365 días (día 1 = 1 de diciembre) sobre un almacén nuevo con los parámetros actuales. "
                   "No modifica el estado actual.")
        if st.button("▶️ Ejecutar simulación anual", type="primary"):
            with st.spinner("Simulando..."):
                st.session_state.tanques_simulacion = planta.simular_campana_anual()

# ---------------------------------- página ---------------------------------- #
# Los controles de la barra lateral ya se ejecutaron, así que aquí todo se muestra actualizado.
config = st.session_state.tanques_config
planta = st.session_state.tanques_planta

st.title("🍊 Almacén de tanques asépticos")
mostrar_flash()

# ---- Alertas de condiciones (temperatura / N2) ---- #
con_zumo = [(t, planta.condicion_tanque(t)) for t in planta.tanques if t.volumen_actual_l > EPS]
en_riesgo = [t.id_tanque for t, (n, _) in con_zumo if n == "error"]
en_aviso = [t.id_tanque for t, (n, _) in con_zumo if n == "warning"]
vacios_fuera = [t.id_tanque for t in planta.tanques
                if t.volumen_actual_l <= EPS and planta.condicion_tanque(t)[0] != "ok"]
if en_riesgo:
    st.error(f"🚨 Zumo en riesgo en {len(en_riesgo)} tanque(s): {lista_ids(en_riesgo)}. "
             "Revisa su temperatura y su N₂ en la tabla de abajo o en el panel 🌡️ del lateral.")
if en_aviso:
    st.warning(f"⚠️ Presión de N₂ fuera de rango en {len(en_aviso)} tanque(s) con zumo: {lista_ids(en_aviso)}.")
if vacios_fuera:
    st.info(f"Hay {len(vacios_fuera)} tanque(s) vacío(s) con condiciones fuera de rango: "
            f"{lista_ids(vacios_fuera)}. Corrígelos antes de llenarlos.")

# ---- Parámetros ---- #
with st.container(border=True):
    st.subheader("⚙️ Parámetros del almacén")
    st.caption(f"Densidad del zumo fija en todo el proceso: **{DENSIDAD_KG_L:.3f} kg/L** (TFG, Tabla 11). "
               "Los cambios se aplican al pulsar «Aplicar y reiniciar almacén», que deja los tanques vacíos.")
    c = config
    a1, a2, a3, a4 = st.columns(4)
    n_t = a1.number_input("Cantidad de tanques", min_value=1, max_value=200, step=1, value=int(c.num_tanques),
                          help="TFG: 6 tanques de 100 m³ + 12 de 50 m³ (1.200.000 L en total). "
                               "Por defecto: 12 × 100.000 L, la misma capacidad total.")
    cap_t = a2.number_input("Capacidad por tanque (L)", min_value=1.0, step=1000.0, value=float(c.cap_tanque_l),
                            help="TFG, Tablas 41 y 42: 100.000 L o 50.000 L.")
    q_in = a3.number_input("Caudal de entrada (L/día)", min_value=0.0, step=100.0,
                           value=float(c.caudal_entrada_l_dia),
                           help="TFG: 17.241,38 L/día, de lunes a viernes (87 días, 1 dic - 31 mar).")
    q_out = a4.number_input("Caudal de salida (L/día)", min_value=0.0, step=100.0,
                            value=float(c.caudal_salida_l_dia), help="TFG: 15.000 L/día de envasado.")
    b1, b2, _b3, _b4 = st.columns(4)
    d_env = b1.number_input("Días de envasado al año", min_value=0, max_value=365, step=1,
                            value=int(c.dias_envasado_anio), help="TFG: 100 días (2 días por semana).")
    d_ret = b2.number_input("Retención máxima (días)", min_value=0, max_value=3650, step=1,
                            value=int(c.dias_max_retencion), help="TFG: no más de un año.")

    st.markdown("**Temperatura de almacenamiento**")
    t1, t2, t3 = st.columns(3)
    temp = t1.number_input("Temperatura (°C)", step=0.1, format="%.1f", value=float(c.temp_operacion_c),
                           help="TFG: entre -1 y 0 °C. El valor por defecto es el punto medio.")
    t_min = t2.number_input("Mínima sin riesgo (°C)", step=0.1, format="%.1f", value=float(c.temp_min_c),
                            help="Por debajo de este valor el zumo corre riesgo de congelarse. TFG: -1 °C.")
    t_max = t3.number_input("Máxima sin riesgo (°C)", step=0.1, format="%.1f", value=float(c.temp_max_c),
                            help="Por encima de este valor el zumo corre riesgo de echarse a perder. TFG: 0 °C.")
    nivel_t, _, largo_t = evaluar_temperatura(float(temp), float(t_min), float(t_max))
    aviso(nivel_t, largo_t)

    st.markdown("**Sobrepresión de N₂**")
    n1, n2c, n3 = st.columns(3)
    n2 = n1.number_input("Sobrepresión (bar)", min_value=0.0, step=0.05, format="%.2f",
                         value=float(c.presion_n2_bar),
                         help="El TFG solo indica atmósfera protectora de N₂ o aire estéril, sin valor numérico.")
    n_min = n2c.number_input("Mínima aceptable (bar)", min_value=0.0, step=0.05, format="%.2f",
                             value=float(c.n2_min_bar), help="Valor supuesto: ajústalo según tu criterio de diseño.")
    n_max = n3.number_input("Máxima aceptable (bar)", min_value=0.0, step=0.05, format="%.2f",
                            value=float(c.n2_max_bar), help="Valor supuesto: ajústalo según tu criterio de diseño.")
    nivel_n, _, largo_n = evaluar_n2(float(n2), float(n_min), float(n_max))
    aviso(nivel_n, largo_n)

    if st.button("Aplicar y reiniciar almacén", type="primary"):
        if t_min > t_max or n_min > n_max:
            st.error("El mínimo no puede ser mayor que el máximo (temperatura o N₂). No se aplicaron los cambios.")
        else:
            reiniciar_planta(ConfigPlanta(
                num_tanques=int(n_t), cap_tanque_l=float(cap_t),
                caudal_entrada_l_dia=float(q_in), caudal_salida_l_dia=float(q_out),
                dias_envasado_anio=int(d_env), dias_max_retencion=int(d_ret),
                temp_operacion_c=float(temp), temp_min_c=float(t_min), temp_max_c=float(t_max),
                presion_n2_bar=float(n2), n2_min_bar=float(n_min), n2_max_bar=float(n_max)))
            mostrar(Resultado("ok", "Parámetros actualizados y almacén reiniciado."))
            st.rerun()

# ---- Estado ---- #
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
    "Temp. (°C)": t.temperatura_c,
    "N₂ (bar)": t.presion_n2_bar,
    "Estado": ESTADOS[t.estado],
    "Condición": planta.condicion_tanque(t)[1],
} for t in planta.tanques])
st.subheader("Estado de los tanques")
st.dataframe(
    df, hide_index=True,
    column_config={"% Lleno": st.column_config.ProgressColumn("% Lleno", min_value=0, max_value=100, format="%.1f")},
)
st.subheader("Volumen por tanque (L)")
st.bar_chart(df.set_index("ID")["Volumen (L)"])

cip = st.session_state.get("tanques_cip_resultado")
if cip:
    st.subheader("Última limpieza CIP")
    st.dataframe(pd.DataFrame(cip), hide_index=True)

# ---- Simulación ---- #
sim = st.session_state.get("tanques_simulacion")
if sim:
    st.divider()
    st.subheader("📅 Simulación anual (365 días)")
    s_t, _, s_largo_t = evaluar_temperatura(config.temp_operacion_c, config.temp_min_c, config.temp_max_c)
    s_n, _, s_largo_n = evaluar_n2(config.presion_n2_bar, config.n2_min_bar, config.n2_max_bar)
    if s_t != "ok" or s_n != "ok":
        detalle = " ".join(txt for niv, txt in ((s_t, s_largo_t), (s_n, s_largo_n)) if niv != "ok")
        st.error(f"Con los parámetros actuales el zumo estaría en riesgo: {detalle} "
                 "(la simulación no modela el deterioro, solo lo señala).")
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
    st.line_chart(hist)
