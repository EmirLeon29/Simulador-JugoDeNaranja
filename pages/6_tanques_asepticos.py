import math
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class TanqueAseptico:
    id_tanque: str
    capacidad_max_l: float
    diametro_int_m: float
    altura_cilindro_m: float
    variedad: Optional[str] = None
    volumen_actual_l: float = 0.0
    temperatura_c: float = 0.0
    presion_n2_bar: float = 0.2
    estado: str = "LIMPIO_VACIO"  # Estados: LIMPIO_VACIO, LLENANDO, ALMACENANDO, VACIANDO, SUCIO_CIP
    dias_almacenado: int = 0

    @property
    def porcentaje_llenado(self) -> float:
        return (self.volumen_actual_l / self.capacidad_max_l) * 100

    @property
    def volumen_disponible_l(self) -> float:
        return self.capacidad_max_l - self.volumen_actual_l

    def ingresar_zumo(self, litros: float, variedad: str, temp_entrada: float) -> float:
        """Ingresa zumo al tanque. Retorna los litros que NO cupieron (rebose/excedente)."""
        if self.estado == "SUCIO_CIP":
            raise ValueError(f"El tanque {self.id_tanque} requiere limpieza CIP antes de usarse.")
        
        if self.variedad is not None and self.variedad != variedad:
            raise ValueError(f"El tanque {self.id_tanque} ya contiene {self.variedad}, no mezclar con {variedad}.")

        if not (-1.0 <= temp_entrada <= 0.5):
            print(f"[ALERTA TÉRMICA] Tanque {self.id_tanque}: Temperatura de entrada ({temp_entrada}°C) fuera de rango (-1 a 0°C).")

        self.variedad = variedad
        self.temperatura_c = temp_entrada
        self.estado = "ALMACENANDO"

        if litros <= self.volumen_disponible_l:
            self.volumen_actual_l += litros
            return 0.0
        else:
            ingresado = self.volumen_disponible_l
            excedente = litros - ingresado
            self.volumen_actual_l = self.capacidad_max_l
            return excedente

    def extraer_zumo(self, litros: float) -> float:
        """Extrae zumo hacia homogeneización. Retorna los litros efectivamente extraídos."""
        if litros >= self.volumen_actual_l:
            extraido = self.volumen_actual_l
            self.volumen_actual_l = 0.0
            self.variedad = None
            self.dias_almacenado = 0
            self.estado = "SUCIO_CIP"  # Al vaciarse por completo, pasa a requerir CIP
            return extraido
        else:
            self.volumen_actual_l -= litros
            return litros

    def ejecutar_cip(self) -> dict:
        """Calcula parámetros de limpieza CIP según el Anejo 2 del proyecto."""
        volumen_dep_l = 0.015 * self.capacidad_max_l  # 1.5% capacidad nominal
        volumen_tuberia_l = 44.59  # Línea estándar 2" y 22m
        volumen_limpieza_l = 1.2 * (volumen_dep_l + volumen_tuberia_l)
        
        self.estado = "LIMPIO_VACIO"
        return {
            "tanque": self.id_tanque,
            "volumen_solucion_cip_l": round(volumen_limpieza_l, 2),
            "naoh_1_porciento_kg": round(volumen_limpieza_l * 0.01, 2),
            "hno3_08_porciento_kg": round(volumen_limpieza_l * 0.008, 2)
        }


class ParqueTanquesAsepticos:
    def __init__(self):
        self.tanques: List[TanqueAseptico] = []
        self._inicializar_planta()

    def _inicializar_planta(self):
        # 6 tanques de 100,000 L (100 m3)
        for i in range(1, 7):
            self.tanques.append(
                TanqueAseptico(f"TA-100-{i:02d}", 100000.0, 4.60, 6.00)
            )
        # 12 tanques de 50,000 L (50 m3)
        for i in range(1, 13):
            self.tanques.append(
                TanqueAseptico(f"TA-50-{i:02d}", 50000.0, 3.40, 5.50)
            )

    def inventario_por_variedad(self) -> dict:
        inventario = {"Washington Navel": 0.0, "Salustiana": 0.0, "Navelate": 0.0}
        for t in self.tanques:
            if t.variedad in inventario:
                inventario[t.variedad] += t.volumen_actual_l
        return inventario

    def recibir_produccion_diaria(self, variedad: str, litros: float = 17241.38):
        """Distribuye la producción diaria entre los tanques disponibles de esa variedad o vacíos."""
        restante = litros
        # 1. Buscar tanques que ya tengan esa variedad y espacio disponible
        for t in self.tanques:
            if t.variedad == variedad and t.volumen_disponible_l > 0 and t.estado != "SUCIO_CIP":
                restante = t.ingresar_zumo(restante, variedad, temp_entrada=-0.5)
                if restante == 0:
                    return

        # 2. Si aún queda zumo, abrir un tanque vacío y limpio
        for t in self.tanques:
            if t.estado == "LIMPIO_VACIO":
                restante = t.ingresar_zumo(restante, variedad, temp_entrada=-0.5)
                if restante == 0:
                    return

        if restante > 0:
            print(f"[ERROR CRÍTICO] Capacidad máxima superada. Quedaron {restante:.2f} L sin almacenar.")

    def enviar_a_homogeneizacion(self, litros_totales: float = 15000.0):
        """Extrae zumo en proporción 1/1/1 de las tres variedades."""
        litros_por_variedad = litros_totales / 3.0
        inv = self.inventario_por_variedad()

        for var, disponible in inv.items():
            if disponible < litros_por_variedad:
                print(f"[BLOQUEO ENVASADO] Stock insuficiente de {var} ({disponible:.2f} L < {litros_por_variedad:.2f} L).")
                return False

        for var in inv.keys():
            por_extraer = litros_por_variedad
            for t in self.tanques:
                if t.variedad == var and t.volumen_actual_l > 0:
                    extraido = t.extraer_zumo(por_extraer)
                    por_extraer -= extraido
                    if por_extraer <= 0:
                        break
        return True


# --- EJEMPLO DE PRUEBA RÁPIDA ---
if __name__ == "__main__":
    planta = ParqueTanquesAsepticos()
    print(f"Total tanques inicializados: {len(planta.tanques)}")
    
    # Simulamos 3 días de extracción de Washington Navel (diciembre)
    for dia in range(1, 4):
        planta.recibir_produccion_diaria("Washington Navel")
        
    print("Inventario tras 3 días de diciembre:", planta.inventario_por_variedad())
    
    # Intentamos envasar antes de tener las 3 variedades
    planta.enviar_a_homogeneizacion()
