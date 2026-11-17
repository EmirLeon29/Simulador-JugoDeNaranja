"""Interfaz Streamlit - Simulador de tanques asépticos (TFG)."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Permite importar modelo_tanques.py desde la raíz del repo (esta página vive en pages/)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modelo_tanques import VARIEDADES, ConfigPlanta, PlantaTanquesAsepticos, Resultado

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
