import streamlit as st
import math

st.header("Módulo: Envasado Aséptico")
st.markdown("---")

st.subheader("Controles de Operación")
col_input1, col_input2 = st.columns(2)

with col_input1:
    # El flujo debería venir de la etapa 2, pero agregamos un slider para pruebas independientes
    flujo_entrada = st.slider(
        "Flujo de entrada desde Pasteurización (L/h)", 
        min_value=5000, 
        max_value=25000, 
        value=15000, 
        step=100,
        help="Volumen de zumo a envasar."
    )

with col_input2:
    merma_pct = st.slider(
        "Tasa de Defectos (Etiquetado/Sellado) (%)", 
        min_value=0.0, 
        max_value=15.0, 
        value=2.0, 
        step=0.5
    )

# 1. Fundamento Teórico: Balance y Discretización
# Un litro de zumo equivale a un envase PET de 1L
botellas_teoricas = flujo_entrada
merma_unidades = botellas_teoricas * (merma_pct / 100.0)

# 2. Uso de math.floor para truncar decimales en unidades discretas
botellas_utiles = math.floor(botellas_teoricas - merma_unidades)
packs = math.floor(botellas_utiles / 6)
palets = math.floor(packs / 32)

st.markdown("---")
st.subheader("Resultados de Producción en Vivo")

col_res1, col_res2, col_res3, col_res4 = st.columns(4)

with col_res1:
    st.metric(label="Botellas PET (1L) Útiles", value=f"{botellas_utiles:,}")
    
with col_res2:
    st.metric(label="Botellas Rechazadas (Merma)", value=f"{math.ceil(merma_unidades):,}")
    
with col_res3:
    st.metric(label="Packs Producidos (6 uds)", value=f"{packs:,}")
    
with col_res4:
    st.metric(label="Palets Completos (32 packs)", value=f"{palets:,}")

st.info("💡 **Nota de Integración:** Cuando el Módulo 2 esté finalizado, la variable `flujo_entrada` dejará de ser un slider y tomará directamente el valor de salida del pasteurizador.")
