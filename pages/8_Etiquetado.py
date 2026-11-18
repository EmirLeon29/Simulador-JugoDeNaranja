import streamlit as st
import math

st.title("Módulo 10: Etiquetado")
st.markdown("Consumo de insumos y consolidación logística.")

st.subheader("Parámetros de Operación")
col1, col2 = st.columns(2)

with col1:
    botellas_entrantes = st.number_input(
        "Botellas Selladas Entrantes (Desde Envasado)", 
        min_value=0, value=14850, step=100
    )
with col2:
    merma_etiquetado = st.slider(
        "Tasa de rechazo en túnel de etiquetado (%)", 
        min_value=0.0, max_value=5.0, value=1.5, step=0.1
    )

# Balance de etiquetado
rechazo_etiquetado = botellas_entrantes * (merma_etiquetado / 100.0)
botellas_utiles = math.floor(botellas_entrantes - rechazo_etiquetado)
bobinas_consumidas = botellas_entrantes / 90000.0  # Rollos industriales de 90k uds

# Balance de consolidación logística
packs = math.floor(botellas_utiles / 6)
palets = math.floor(packs / 32)

st.markdown("---")
st.subheader("Insumos y Mermas (Etiquetado)")
col_out1, col_out2, col_out3 = st.columns(3)
with col_out1:
    st.metric("Botellas Útiles Finales", f"{botellas_utiles:,}")
with col_out2:
    st.metric("Rechazo Etiquetado (PET)", f"{math.ceil(rechazo_etiquetado):,}")
with col_out3:
    st.metric("Bobinas de Etiquetas", f"{bobinas_consumidas:.3f}")

st.markdown("---")
st.subheader("Consolidación Logística")
col_log1, col_log2 = st.columns(2)
with col_log1:
    st.metric("Packs (6 unidades)", f"{packs:,}")
with col_log2:
    st.metric("Palets Completos (32 packs)", f"{palets:,}")
