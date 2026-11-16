import math

print("Planta Virtual: Fin de Línea")
print("-" * 28)
flujo = float(input("Ingrese el flujo de entrada desde Pasteurización (L/h) [Ej. 15000]: "))
merma_pct = float(input("Ingrese la Tasa de Defectos (%) [Ej. 2.0]: "))

# 1. Fundamento Teórico: Balance y Discretización
botellas_teoricas = flujo
merma_unidades = botellas_teoricas * (merma_pct / 100)

# 2. Uso de math.floor para truncar decimales
botellas_utiles = math.floor(botellas_teoricas - merma_unidades)
packs = math.floor(botellas_utiles / 6)
palets = math.floor(packs / 32)

# 3. Salidas
print("\n--- Resultados de la Simulación ---")
print(f"Flujo ingresado: {flujo} L/h")
print(f"Tasa de merma: {merma_pct} %")
print(f"Botellas PET (1L) Útiles: {botellas_utiles}")
print(f"Botellas Rechazadas (Merma): {math.ceil(merma_unidades)}")
print(f"Packs Producidos (6 uds): {packs}")
print(f"Palets Completos (32 packs): {palets}")
