"""
Simulador de escenarios de carga de vehículos eléctricos para Iquitos.
Define perfiles realistas de carga según hora del día y día de semana.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
import numpy as np


@dataclass
class VehicleChargingScenario:
    """Escenario de carga de vehículos para una hora específica."""
    hour: int
    day_of_week: int
    total_motos: int = 270
    total_mototaxis: int = 39
    motos_demanding_charge: int = 0
    mototaxis_demanding_charge: int = 0
    
    @property
    def total_vehicles(self) -> int:
        """Total de vehículos demandando carga en esta hora."""
        return self.motos_demanding_charge + self.mototaxis_demanding_charge


# Escenarios predefinidos para diferentes horas del día
SCENARIO_OFF_PEAK = VehicleChargingScenario(
    hour=3, day_of_week=2, total_motos=270, total_mototaxis=39,
    motos_demanding_charge=10, mototaxis_demanding_charge=2
)

SCENARIO_PEAK_AFTERNOON = VehicleChargingScenario(
    hour=14, day_of_week=2, total_motos=270, total_mototaxis=39,
    motos_demanding_charge=80, mototaxis_demanding_charge=20
)

SCENARIO_PEAK_EVENING = VehicleChargingScenario(
    hour=18, day_of_week=2, total_motos=270, total_mototaxis=39,
    motos_demanding_charge=150, mototaxis_demanding_charge=35
)

SCENARIO_EXTREME_PEAK = VehicleChargingScenario(
    hour=19, day_of_week=5, total_motos=270, total_mototaxis=39,
    motos_demanding_charge=200, mototaxis_demanding_charge=39
)


class VehicleChargingSimulator:
    """Simula carga por SOC de vehículos en cada timestep."""
    
    def __init__(self):
        """Inicializar simulador con distribuciones de SOC realistas."""
        # Distribución de SOC de llegada (uniforme 10-80%)
        self.soc_distribution = {
            10: 0.15,   # 15% llegan al 10%
            20: 0.15,   # 15% llegan al 20%
            30: 0.20,   # 20% llegan al 30%
            50: 0.25,   # 25% llegan al 50%
            70: 0.15,   # 15% llegan al 70%
            80: 0.10,   # 10% llegan al 80%
        }
    
    def simulate_hourly_charge(
        self, 
        scenario: VehicleChargingScenario, 
        available_power_kw: float
    ) -> Dict[str, Any]:
        """
        Simula carga de vehículos durante una hora.
        
        Args:
            scenario: Escenario de demanda de carga
            available_power_kw: Potencia disponible para carga (kW)
        
        Returns:
            Diccionario con conteos de vehículos por nivel de carga
        """
        
        result = {
            'motos_10_percent_charged': 0,
            'motos_20_percent_charged': 0,
            'motos_30_percent_charged': 0,
            'motos_50_percent_charged': 0,
            'motos_70_percent_charged': 0,
            'motos_80_percent_charged': 0,
            'motos_100_percent_charged': 0,
            'mototaxis_10_percent_charged': 0,
            'mototaxis_20_percent_charged': 0,
            'mototaxis_30_percent_charged': 0,
            'mototaxis_50_percent_charged': 0,
            'mototaxis_70_percent_charged': 0,
            'mototaxis_80_percent_charged': 0,
            'mototaxis_100_percent_charged': 0,
        }
        
        if scenario.total_vehicles == 0:
            return result
        
        # Potencia media por vehículo (7.4 kW por moto, 10 kW por mototaxi)
        moto_power = 7.4  # kW
        mototaxi_power = 10.0  # kW
        
        # Calcular cuántos vehículos se pueden cargar con potencia disponible
        motos_can_charge = min(
            scenario.motos_demanding_charge,
            int(available_power_kw / moto_power)
        )
        power_left = available_power_kw - (motos_can_charge * moto_power)
        
        mototaxis_can_charge = min(
            scenario.mototaxis_demanding_charge,
            int(power_left / mototaxi_power)
        )
        
        # Simular progreso de carga para motos
        # Usar distribución de SOC para determinar cuánto puede cargar cada vehículo
        for i in range(motos_can_charge):
            # Seleccionar SOC de llegada aleatorio
            soc_arrival = np.random.choice(
                list(self.soc_distribution.keys()),
                p=list(self.soc_distribution.values())
            )
            
            # Simular 1 hora de carga desde ese SOC inicial
            # Batería típica moto: 5-10 kWh, cargador: 7.4 kW = ~0.5 horas a 100%
            charge_gained_pct = min(100 - soc_arrival, 40)  # 40% por hora (simple)
            final_soc = soc_arrival + charge_gained_pct
            
            # Contar por nivel alcanzado
            if final_soc >= 100:
                result['motos_100_percent_charged'] += 1
            elif final_soc >= 80:
                result['motos_80_percent_charged'] += 1
            elif final_soc >= 70:
                result['motos_70_percent_charged'] += 1
            elif final_soc >= 50:
                result['motos_50_percent_charged'] += 1
            elif final_soc >= 30:
                result['motos_30_percent_charged'] += 1
            elif final_soc >= 20:
                result['motos_20_percent_charged'] += 1
            else:
                result['motos_10_percent_charged'] += 1
        
        # Simular progreso de carga para mototaxis (similar pero más rápido)
        for i in range(mototaxis_can_charge):
            soc_arrival = np.random.choice(
                list(self.soc_distribution.keys()),
                p=list(self.soc_distribution.values())
            )
            
            # Mototaxis cargan más rápido (batería mayor, mismo cargador)
            charge_gained_pct = min(100 - soc_arrival, 50)  # 50% por hora
            final_soc = soc_arrival + charge_gained_pct
            
            if final_soc >= 100:
                result['mototaxis_100_percent_charged'] += 1
            elif final_soc >= 80:
                result['mototaxis_80_percent_charged'] += 1
            elif final_soc >= 70:
                result['mototaxis_70_percent_charged'] += 1
            elif final_soc >= 50:
                result['mototaxis_50_percent_charged'] += 1
            elif final_soc >= 30:
                result['mototaxis_30_percent_charged'] += 1
            elif final_soc >= 20:
                result['mototaxis_20_percent_charged'] += 1
            else:
                result['mototaxis_10_percent_charged'] += 1
        
        return result
