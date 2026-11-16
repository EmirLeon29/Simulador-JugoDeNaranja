"""
Módulo de Homogeneización 
Proyecto: Línea de elaboración de zumo de naranja (1.500.000 litros/año)
Ubicación: Palma del Río, Córdoba
"""

from dataclasses import dataclass

@dataclass
class PlantParameters:
    annual_production_liters: float = 1_500_000.0  # L/año
    operating_days_per_year: int = 250             # días/año
    operating_hours_per_day: float = 16.0          # horas/día
    juice_density: float = 1.04                    # kg/L (zumo de naranja a 11-12 ºBrix)

@dataclass
class HomogenizationParameters:
    pressure_bar: float = 150.0                    # Presión de homogenización (típica 100 - 200 bar)
    efficiency: float = 0.85                       # Eficiencia mecánica del motor/émbolos (85%)
    valve_stages: int = 2                          # Número de etapas de homogenización (habitualmente 2)


class HomogenizationProcess:
    """
    Clase para el diseño y dimensionamiento de la etapa de homogenización.
    Reduce el tamaño de partícula de la pulpa en suspensión y previene la 
    separación de fases (sedimentación del suero) en el zumo de naranja.
    """
    def __init__(self, plant: PlantParameters, homo: HomogenizationParameters):
        self.plant = plant
        self.homo = homo

    def run_design_calculations(self):
        # 1. Cálculo de tiempos de operación anuales
        total_hours = self.plant.operating_days_per_year * self.plant.operating_hours_per_day
        
        # 2. Caudales volumétricos y másicos
        vol_flow_l_h = self.plant.annual_production_liters / total_hours
        vol_flow_m3_h = vol_flow_l_h / 1000.0
        vol_flow_m3_s = vol_flow_m3_h / 3600.0
        mass_flow_kg_h = vol_flow_l_h * self.plant.juice_density
        
        # 3. Requerimientos energéticos y de potencia
        # Ecuación de potencia hidráulica: P_h = Q * ΔP
        delta_p_pa = self.homo.pressure_bar * 100_000.0  # Conversión de bar a Pa (1 bar = 10^5 Pa)
        power_hydraulic_w = vol_flow_m3_s * delta_p_pa
        power_hydraulic_kw = power_hydraulic_w / 1000.0
        
        # Potencia eléctrica considerando pérdidas mecánicas en el equipo
        power_electrical_kw = power_hydraulic_kw / self.homo.efficiency

        print("============================================================")
        print(" MEMORIA TÉCNICA: ETAPA DE HOMOGENIZACIÓN")
        print(" Planta: Zumo de Naranja (1.500.000 L/año) - Palma del Río")
        print("============================================================")
        print(f" 1. PARÁMETROS DE FLUJO")
        print(f"   - Producción anual: {self.plant.annual_production_liters:,.0f} L/año")
        print(f"   - Régimen de trabajo: {self.plant.operating_days_per_year} días/año y {self.plant.operating_hours_per_day} h/día")
        print(f"   - Caudal volumétrico de diseño: {vol_flow_l_h:.2f} L/h ({vol_flow_m3_h:.3f} m³/h)")
        print(f"   - Caudal másico: {mass_flow_kg_h:.2f} kg/h (Densidad: {self.plant.juice_density} kg/L)")
        print("------------------------------------------------------------")
        print(f" 2. ESPECIFICACIONES DEL HOMOGENEIZADOR")
        print(f"   - Etapas de homogenización: {self.homo.valve_stages} etapas")
        print(f"   - Presión de trabajo aplicada: {self.homo.pressure_bar} bar")
        print("------------------------------------------------------------")
        print(f" 3. BALANCE DE POTENCIA")
        print(f"   - Potencia hidráulica efectiva: {power_hydraulic_kw:.2f} kW")
        print(f"   - Eficiencia mecánica asumida: {self.homo.efficiency * 100}%")
        print(f"   - Potencia eléctrica instalada requerida: {power_electrical_kw:.2f} kW")
        print("============================================================")
        
        return {
            "vol_flow_l_h": vol_flow_l_h,
            "power_hydraulic_kw": power_hydraulic_kw,
            "power_electrical_kw": power_electrical_kw
        }

if __name__ == "__main__":
    plant = PlantParameters()
    homo = HomogenizationParameters(pressure_bar=150.0, efficiency=0.85, valve_stages=2)
    
    homogenization_project = HomogenizationProcess(plant, homo)
    homogenization_project.run_design_calculations()