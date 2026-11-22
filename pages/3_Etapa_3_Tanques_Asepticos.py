"""Página Streamlit - Almacén de tanques asépticos (todo en un solo archivo).

Un único almacén general de zumo de naranja formado por N tanques iguales.
- Parámetros y condiciones de almacenamiento: en la página principal.
- Operaciones (ingresar, extraer, vaciar/limpiar, simular): en la barra lateral.
Los valores por defecto parten del TFG (Anejo 2); la densidad es fija.
"""
import math
from dataclasses import dataclass, field, replace
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
    # Almacén (cambiarlos reinicia la planta)
    num_tanques: int = 12
    cap_tanque_l: float = 100_000.0
    caudal_entrada_l_dia: float = 17_241.38
    caudal_salida_l_dia: float = 15_000.0
    dias_envasado_anio: int = 100
    dias_max_retencion: int = 365
    # Condiciones de almacenamiento (se aplican en caliente, sin reiniciar)
    temp_operacion_c: float = -0.5
    temp_min_c: float = -1.0     # TFG: -1 a 0 °C (por encima del punto de congelación)
    temp_max_c: float = 0.0
    presion_n2_bar: float = 0.2
    n2_min_bar: float = 0.1      # SUPUESTO: el TFG no da valores de presión
    n2_max_bar: float = 0.5      # SUPUESTO


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
    volumen_actual_l: float = 0.0
    temperatura_c: float = -0.5
    presion_n2_bar: float = 0.2
    estado: str = LIMPIO
    dias_almacenado: int = 0
    riesgo: str = ""  # motivo si el zumo estuvo fuera de condiciones seguras; se borra al vaciar

    @property
    def volumen_disponible_l(self) -> float:
        return self.capacidad_max_l - self.volumen_actual_l

    @property
    def porcentaje_llenado(self) -> float:
        return self.volumen_actual_l / self.capacidad_max_l * 100.0 if self.capacidad_max_l > 0 else 0.0

    def ingresar_zumo(self, litros: float) -> float:
        """Ingresa zumo (a la temperatura del tanque). Devuelve los litros que no cupieron."""
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
            self.riesgo = ""
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
        self.tanques: List[TanqueAseptico] = [
            TanqueAseptico(f"TA-{i:02d}", config.cap_tanque_l,
                           temperatura_c=config.temp_operacion_c, presion_n2_bar=config.presion_n2_bar)
            for i in range(1, config.num_tanques + 1)
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

    def tanques_en_riesgo(self) -> List[TanqueAseptico]:
        return [t for t in self.tanques if t.riesgo and t.volumen_actual_l > EPS]

    # ---- condiciones de almacenamiento ---- #
    def _evaluar_condiciones(self) -> List[Tuple[str, str]]:
        """Devuelve [(motivo corto, mensaje largo)] para cada condición fuera de rango."""
        c = self.config
        fuera = []
        if c.temp_operacion_c < c.temp_min_c - EPS:
            fuera.append(("temperatura baja", f"Temperatura demasiado fría ({c.temp_operacion_c:.1f} °C; "
                                              f"mínimo seguro {c.temp_min_c:.1f} °C)"))
        elif c.temp_operacion_c > c.temp_max_c + EPS:
            fuera.append(("temperatura alta", f"Temperatura demasiado caliente ({c.temp_operacion_c:.1f} °C; "
                                              f"máximo seguro {c.temp_max_c:.1f} °C)"))
        if c.presion_n2_bar < c.n2_min_bar - EPS:
            fuera.append(("N₂ bajo", f"Sobrepresión de N₂ demasiado baja ({c.presion_n2_bar:.2f} bar; "
                                     f"mínimo seguro {c.n2_min_bar:.2f} bar)"))
        elif c.presion_n2_bar > c.n2_max_bar + EPS:
            fuera.append(("N₂ alto", f"Sobrepresión de N₂ demasiado alta ({c.presion_n2_bar:.2f} bar; "
                                     f"máximo seguro {c.n2_max_bar:.2f} bar)"))
        return fuera

    def riesgos_condiciones(self) -> List[str]:
        return [largo for _, largo in self._evaluar_condiciones()]

    def _marcar_riesgo(self) -> None:
        """Marca «en riesgo» los tanques con zumo mientras las condiciones estén fuera de rango."""
        nuevos = [corto for corto, _ in self._evaluar_condiciones()]
        if not nuevos:
            return
        for t in self.tanques:
            if t.volumen_actual_l > EPS:
                previos = [p for p in t.riesgo.split(" + ") if p]
                t.riesgo = " + ".join(previos + [m for m in nuevos if m not in previos])

    def aplicar_condiciones(self, temp: float, t_min: float, t_max: float,
                            n2: float, n2_min: float, n2_max: float) -> Resultado:
        """Cambia temperatura y sobrepresión de N₂ de todos los tanques sin reiniciar el almacén."""
        if t_min > t_max or n2_min > n2_max:
            return Resultado("error", "El mínimo seguro no puede ser mayor que el máximo.")
        c = self.config
        c.temp_operacion_c, c.temp_min_c, c.temp_max_c = temp, t_min, t_max
        c.presion_n2_bar, c.n2_min_bar, c.n2_max_bar = n2, n2_min, n2_max
        for t in self.tanques:
            t.temperatura_c, t.presion_n2_bar = temp, n2
        self._marcar_riesgo()
        if self.riesgos_condiciones():
            n = len(self.tanques_en_riesgo())
            extra = (f"{n} tanque(s) con zumo quedan marcados «En riesgo»." if n
                     else "Todavía no hay zumo almacenado.")
            return Resultado("warning", f"Condiciones aplicadas, pero fuera del rango seguro. {extra}")
        return Resultado("ok", f"Condiciones aplicadas: {temp:.1f} °C y {n2:.2f} bar de N₂, dentro del rango seguro.")

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
    def recibir_zumo(self, litros: float) -> Resultado:
        """El zumo entra a la temperatura de almacenamiento: no se elige en la operación."""
        if litros <= 0:
            return Resultado("warning", "Indica una cantidad mayor que 0.")
        restante = self._ingresar(litros)
        alertas = []
        if self.riesgos_condiciones():
            alertas.append("Las condiciones de almacenamiento están fuera del rango seguro: "
                           "el zumo ingresado corre riesgo de echarse a perder.")
        self._marcar_riesgo()
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
        Las condiciones de almacenamiento son las actuales y se mantienen todo el año.
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
            "condiciones_en_riesgo": sim.riesgos_condiciones(),
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


def mostrar(resultado: Resultado) -> None:
    """Guarda el mensaje para mostrarlo arriba de la página."""
    st.session_state.tanques_flash = resultado


def mostrar_flash() -> None:
    res = st.session_state.pop("tanques_flash", None)
    if res is None:
        return
    for alerta in res.alertas:
        st.warning(f"⚠️ {alerta}")
    {"ok": st.success, "warning": st.warning, "error": st.error}[res.nivel](res.mensaje)


# --------------------------------- sidebar ---------------------------------- #
PANELES = ["⬇️ Ingresar zumo", "⬆️ Extraer zumo", "🧼 Vaciar y limpiar", "📅 Simulación anual"]

with st.sidebar:
    st.header("🎛️ Operaciones")
    st.caption(f"Densidad del zumo: **{DENSIDAD_KG_L:.3f} kg/L**, fija en todo el proceso (TFG, Tabla 11).")
    panel = st.selectbox("Acción", PANELES, key="tanques_panel")
    st.divider()

    # ---- Ingresar ---- #
    if panel == PANELES[0]:
        st.caption(f"Espacio libre: {planta.capacidad_total_l - planta.volumen_total_l:,.0f} L. "
                   f"El zumo entra a la temperatura de los tanques ({config.temp_operacion_c:.1f} °C), "
                   "que se ajusta en la página principal.")
        with st.form("tanques_form_ingreso"):
            litros_in = st.number_input("Litros a ingresar", min_value=0.0, step=100.0,
                                        value=float(config.caudal_entrada_l_dia))
            if st.form_submit_button("Ingresar zumo", type="primary"):
                mostrar(planta.recibir_zumo(float(litros_in)))

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

    # ---- Simulación ---- #
    else:
        st.caption("Simula 365 días (día 1 = 1 de diciembre) sobre un almacén nuevo con los parámetros y "
                   "condiciones actuales. No modifica el estado actual.")
        if st.button("▶️ Ejecutar simulación anual", type="primary"):
            with st.spinner("Simulando..."):
                st.session_state.tanques_simulacion = planta.simular_campana_anual()

# ---------------------------------- página ---------------------------------- #
config = st.session_state.tanques_config
planta = st.session_state.tanques_planta

st.title("🍊 Almacén de tanques asépticos")
flash_slot = st.container()  # los mensajes se escriben aquí al final, ya con todo actualizado

# ---- Parámetros ---- #
st.subheader("⚙️ Parámetros")
col_cond, col_conf = st.columns(2)

with col_cond:
    st.markdown("**Condiciones de almacenamiento** · se aplican al instante a todos los tanques, sin reiniciar")
    with st.form("tanques_form_condiciones"):
        c = config
        f1, f2, f3 = st.columns(3)
        temp = f1.number_input("Temperatura (°C)", step=0.1, format="%.1f", value=float(c.temp_operacion_c),
                               help="TFG: el zumo se almacena a -1 – 0 °C, por encima de su punto de congelación.")
        t_min = f2.number_input("Mínimo seguro (°C)", step=0.1, format="%.1f", value=float(c.temp_min_c),
                                help="Por debajo de este valor el zumo corre riesgo de echarse a perder. TFG: -1 °C.")
        t_max = f3.number_input("Máximo seguro (°C)", step=0.1, format="%.1f", value=float(c.temp_max_c),
                                help="Por encima de este valor el zumo corre riesgo de echarse a perder. TFG: 0 °C.")
        g1, g2, g3 = st.columns(3)
        n2 = g1.number_input("Sobrepresión N₂ (bar)", min_value=0.0, step=0.05, format="%.2f",
                             value=float(c.presion_n2_bar),
                             help="Valor supuesto: el TFG solo indica una atmósfera protectora de N₂ o aire estéril "
                                  "(reduce el oxígeno y evita la contaminación microbiológica), sin dar presiones.")
        n2_min = g2.number_input("Mínimo seguro (bar)", min_value=0.0, step=0.05, format="%.2f",
                                 value=float(c.n2_min_bar),
                                 help="Supuesto. Por debajo, la atmósfera protectora podría no mantenerse.")
        n2_max = g3.number_input("Máximo seguro (bar)", min_value=0.0, step=0.05, format="%.2f",
                                 value=float(c.n2_max_bar),
                                 help="Supuesto. Ajústalo al límite de operación de tus tanques.")
        if st.form_submit_button("Aplicar condiciones", type="primary"):
            mostrar(planta.aplicar_condiciones(float(temp), float(t_min), float(t_max),
                                               float(n2), float(n2_min), float(n2_max)))

    riesgos = planta.riesgos_condiciones()
    if riesgos:
        for r in riesgos:
            st.error(f"⚠️ {r}: el zumo corre riesgo de echarse a perder.")
    else:
        st.success(f"✅ Dentro del rango seguro: {config.temp_operacion_c:.1f} °C "
                   f"(de {config.temp_min_c:.1f} a {config.temp_max_c:.1f} °C) y "
                   f"{config.presion_n2_bar:.2f} bar de N₂ (de {config.n2_min_bar:.2f} a {config.n2_max_bar:.2f} bar).")
    st.caption("Un tanque marcado «En riesgo» sigue marcado hasta que se vacíe, aunque las condiciones vuelvan al rango.")

with col_conf:
    st.markdown("**Configuración del almacén** · al aplicar se reinicia (tanques vacíos)")
    with st.form("tanques_form_config"):
        r1a, r1b = st.columns(2)
        n_t = r1a.number_input("Cantidad de tanques", min_value=1, max_value=200, step=1,
                               value=int(config.num_tanques),
                               help="TFG: 6 tanques de 100 m³ + 12 de 50 m³ (1.200.000 L en total). "
                                    "Por defecto: 12 × 100.000 L, la misma capacidad total.")
        cap_t = r1b.number_input("Capacidad por tanque (L)", min_value=1.0, step=1000.0,
                                 value=float(config.cap_tanque_l), help="TFG, Tablas 41 y 42: 100.000 L o 50.000 L.")
        r2a, r2b = st.columns(2)
        q_in = r2a.number_input("Caudal de entrada (L/día)", min_value=0.0, step=100.0,
                                value=float(config.caudal_entrada_l_dia),
                                help="TFG: 17.241,38 L/día, de lunes a viernes (87 días, 1 dic - 31 mar).")
        q_out = r2b.number_input("Caudal de salida (L/día)", min_value=0.0, step=100.0,
                                 value=float(config.caudal_salida_l_dia), help="TFG: 15.000 L/día de envasado.")
        r3a, r3b = st.columns(2)
        d_env = r3a.number_input("Días de envasado al año", min_value=0, max_value=365, step=1,
                                 value=int(config.dias_envasado_anio), help="TFG: 100 días (2 días por semana).")
        d_ret = r3b.number_input("Retención máxima (días)", min_value=0, max_value=3650, step=1,
                                 value=int(config.dias_max_retencion), help="TFG: no más de un año.")
        if st.form_submit_button("Aplicar y reiniciar almacén", type="primary"):
            reiniciar_planta(replace(  # conserva las condiciones de almacenamiento actuales
                config, num_tanques=int(n_t), cap_tanque_l=float(cap_t),
                caudal_entrada_l_dia=float(q_in), caudal_salida_l_dia=float(q_out),
                dias_envasado_anio=int(d_env), dias_max_retencion=int(d_ret)))
            mostrar(Resultado("ok", "Configuración actualizada y almacén reiniciado."))
            st.rerun()

st.divider()

# ---- Resultados ---- #
m1, m2, m3, m4, m5, m6 = st.columns(6)
en_riesgo = planta.tanques_en_riesgo()
m1.metric("Capacidad total", f"{planta.capacidad_total_l:,.0f} L")
m2.metric("Zumo almacenado", f"{planta.volumen_total_l:,.0f} L")
m3.metric("Ocupación", f"{planta.porcentaje_ocupacion:.1f} %")
m4.metric("Masa almacenada", f"{planta.masa_total_kg:,.0f} kg")
m5.metric("Tanques sucios (CIP)", len(planta.tanques_sucios()))
m6.metric("Tanques en riesgo", len(en_riesgo), f"{sum(t.volumen_actual_l for t in en_riesgo):,.0f} L", delta_color="off")


def calidad(t: TanqueAseptico) -> str:
    if t.volumen_actual_l <= EPS:
        return "—"
    return f"⚠️ En riesgo: {t.riesgo}" if t.riesgo else "OK"


df = pd.DataFrame([{
    "ID": t.id_tanque,
    "Capacidad (L)": t.capacidad_max_l,
    "Volumen (L)": round(t.volumen_actual_l, 2),
    "% Lleno": t.porcentaje_llenado,
    "Estado": ESTADOS[t.estado],
    "Calidad": calidad(t),
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

sim = st.session_state.get("tanques_simulacion")
if sim:
    st.divider()
    st.subheader("📅 Simulación anual (365 días)")
    a, b, c_, d, e = st.columns(5)
    a.metric("Pico de ocupación", f"{sim['pico_ocupacion_l']:,.0f} L", f"{sim['pico_ocupacion_pct']:.1f} %", delta_color="off")
    b.metric("Zumo ingresado", f"{sim['total_ingresado_l']:,.0f} L")
    c_.metric("Zumo envasado", f"{sim['total_envasado_l']:,.0f} L", f"{sim['jornadas_envasado']} jornadas", delta_color="off")
    d.metric("Remanente a fin de año", f"{sim['inventario_final_l']:,.0f} L")
    e.metric(f"Alertas > {config.dias_max_retencion} d", sim["alertas_caducidad"])
    for r in sim["condiciones_en_riesgo"]:
        st.error(f"⚠️ {r}: con estas condiciones el zumo corre riesgo de echarse a perder durante toda la campaña.")
    if sim["total_rechazado_l"] > EPS:
        st.error(f"No cupieron {sim['total_rechazado_l']:,.0f} L: la capacidad del almacén es insuficiente.")
    if sim["jornadas_envasado"] < config.dias_envasado_anio:
        st.info(f"En los 365 días simulados se completaron {sim['jornadas_envasado']} de "
                f"{config.dias_envasado_anio} jornadas de envasado.")
    hist = pd.DataFrame(sim["historial"]).set_index("dia")
    hist = hist.rename(columns={"volumen_l": "Zumo almacenado (L)"})
    hist["Capacidad total (L)"] = sim["capacidad_total_l"]
    st.line_chart(hist)

# Mensajes de la última operación (arriba de la página)
with flash_slot:
    mostrar_flash()

st.markdown("---")
st.markdown(
    """
    Referencias.
    - Gémina Procesos Alimentarios, S.L. Tanques de Proceso [Folleto técnico]; Jumilla, Murcia, España, s.f. https://www.gemina.es (consultado el 21 de noviembre de 2026).

    Integrantes del modulo.
    - Andrés Hernandez Juan Pablo
    """
)
