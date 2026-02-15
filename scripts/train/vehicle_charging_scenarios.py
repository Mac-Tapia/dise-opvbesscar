"""
Simulador de escenarios de carga de vehiculos electricos para Iquitos.
Define perfiles realistas de carga segun hora del dia y dia de semana.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
import numpy as np


@dataclass
class VehicleChargingScenario:
    """Escenario de carga de vehiculos para una hora especifica."""
    hour: int
    day_of_week: int
    total_motos: int = 270
    total_mototaxis: int = 39
    motos_demanding_charge: int = 0
    mototaxis_demanding_charge: int = 0
    
    @property
    def total_vehicles(self) -> int:
        """Total de vehiculos demandando carga en esta hora."""
        return self.motos_demanding_charge + self.mototaxis_demanding_charge


# Escenarios predefinidos para diferentes horas del dia
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
    """Simula carga por SOC de vehiculos en cada timestep."""
    
    # CONSTANTES v5.5: Configuracion de sockets por tipo de vehiculo
    SOCKETS_MOTOS = 30          # 30 tomas para motos (15 cargadores x 2 tomas)
    SOCKETS_MOTOTAXIS = 8       # 8 tomas para mototaxis (4 cargadores x 2 tomas)
    TOTAL_SOCKETS = 38          # Total: 19 cargadores x 2 tomas = 38
    
    def __init__(self):
        """Inicializar simulador con distribuciones de SOC realistas.
        
        DISTRIBUCION BASADA EN DATASET REAL (chargers_ev_ano_2024_v3.csv):
        - SOC de llegada: ~0% (todos llegan vacios)
        - SOC alcanzado: distribucion segun capacidad de carga real
        
        MOTOS (soc_current real):
          0-10%: 12.6%, 10-20%: 32.9%, 20-30%: 32.9%, 30-50%: 15.2%
          50-70%: 0.1%, 80-100%: 6.3%
        
        MOTOTAXIS (soc_current real):
          0-10%: 6.7%, 10-20%: 17.6%, 20-30%: 17.7%, 30-50%: 8.2%
          50-70%: 6.1%, 70-80%: 15.6%, 80-100%: 28.1%
        """
        # Distribucion de SOC ALCANZADO para MOTOS (basado en dataset real)
        self.soc_distribution_motos = {
            10: 0.126,   # 12.6% alcanzan 0-10%
            20: 0.329,   # 32.9% alcanzan 10-20%
            30: 0.329,   # 32.9% alcanzan 20-30%
            50: 0.152,   # 15.2% alcanzan 30-50%
            70: 0.001,   # 0.1% alcanzan 50-70%
            80: 0.000,   # 0% alcanzan 70-80%
            100: 0.063,  # 6.3% alcanzan 80-100%
        }
        
        # Distribucion de SOC ALCANZADO para MOTOTAXIS (basado en dataset real)
        self.soc_distribution_mototaxis = {
            10: 0.067,   # 6.7% alcanzan 0-10%
            20: 0.176,   # 17.6% alcanzan 10-20%
            30: 0.177,   # 17.7% alcanzan 20-30%
            50: 0.082,   # 8.2% alcanzan 30-50%
            70: 0.061,   # 6.1% alcanzan 50-70%
            80: 0.156,   # 15.6% alcanzan 70-80%
            100: 0.281,  # 28.1% alcanzan 80-100%
        }
        
        # Alias para compatibilidad (deprecated)
        self.soc_distribution = self.soc_distribution_motos
    
    def simulate_hourly_charge(
        self, 
        scenario: VehicleChargingScenario, 
        available_power_kw: float
    ) -> Dict[str, Any]:
        """
        Simula carga de vehiculos durante una hora.
        
        Args:
            scenario: Escenario de demanda de carga
            available_power_kw: Potencia disponible para carga (kW)
        
        Returns:
            Diccionario con conteos de vehiculos por nivel de carga (SOC de llegada)
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
        
        # Potencia media por vehiculo (7.4 kW por moto, 10 kW por mototaxi)
        moto_power = 7.4  # kW
        mototaxi_power = 10.0  # kW
        
        # Calcular cuantos vehiculos se pueden cargar con potencia disponible
        # LIMITADO POR: demanda, potencia disponible, Y sockets disponibles
        motos_by_power = int(available_power_kw / moto_power) if moto_power > 0 else 0
        motos_can_charge = min(
            scenario.motos_demanding_charge,  # Demanda
            motos_by_power,                   # Potencia
            self.SOCKETS_MOTOS                # Sockets disponibles (30)
        )
        power_left = available_power_kw - (motos_can_charge * moto_power)
        
        mototaxis_by_power = int(power_left / mototaxi_power) if mototaxi_power > 0 else 0
        mototaxis_can_charge = min(
            scenario.mototaxis_demanding_charge,  # Demanda
            mototaxis_by_power,                   # Potencia
            self.SOCKETS_MOTOTAXIS                # Sockets disponibles (8)
        )
        
        # [v5.6 DEBUG] Verificar que hay vehiculos para cargar
        print(f"[VCHARGE-DEBUG] motos_can_charge={motos_can_charge}, mototaxis_can_charge={mototaxis_can_charge}, power={available_power_kw:.1f}, demand_m={scenario.motos_demanding_charge}, demand_t={scenario.mototaxis_demanding_charge}")
        
        # Simular progreso de carga para motos
        # v5.6: Contar por SOC ALCANZADO (distribucion real del dataset)
        for i in range(motos_can_charge):
            # Seleccionar SOC ALCANZADO segun distribucion real de MOTOS
            soc_achieved = np.random.choice(
                list(self.soc_distribution_motos.keys()),
                p=list(self.soc_distribution_motos.values())
            )
            
            # CONTAR POR SOC ALCANZADO (nivel de carga logrado)
            if soc_achieved <= 10:
                result['motos_10_percent_charged'] += 1
            elif soc_achieved <= 20:
                result['motos_20_percent_charged'] += 1
            elif soc_achieved <= 30:
                result['motos_30_percent_charged'] += 1
            elif soc_achieved <= 50:
                result['motos_50_percent_charged'] += 1
            elif soc_achieved <= 70:
                result['motos_70_percent_charged'] += 1
            elif soc_achieved <= 80:
                result['motos_80_percent_charged'] += 1
            else:
                result['motos_100_percent_charged'] += 1
        
        # Simular progreso de carga para mototaxis
        # v5.6: Contar por SOC ALCANZADO (distribucion real del dataset)
        for i in range(mototaxis_can_charge):
            # Seleccionar SOC ALCANZADO segun distribucion real de MOTOTAXIS
            soc_achieved = np.random.choice(
                list(self.soc_distribution_mototaxis.keys()),
                p=list(self.soc_distribution_mototaxis.values())
            )
            
            # CONTAR POR SOC ALCANZADO (nivel de carga logrado)
            if soc_achieved <= 10:
                result['mototaxis_10_percent_charged'] += 1
            elif soc_achieved <= 20:
                result['mototaxis_20_percent_charged'] += 1
            elif soc_achieved <= 30:
                result['mototaxis_30_percent_charged'] += 1
            elif soc_achieved <= 50:
                result['mototaxis_50_percent_charged'] += 1
            elif soc_achieved <= 70:
                result['mototaxis_70_percent_charged'] += 1
            elif soc_achieved <= 80:
                result['mototaxis_80_percent_charged'] += 1
            else:
                result['mototaxis_100_percent_charged'] += 1
        
        # [v5.6 RESULTADO] Retornar conteos TOTALES de vehiculos cargados por SOC
        # Total de cada rango = numero de vehiculos que alcanzaron ese SOC en esta hora
        total_motos = sum([
            result['motos_10_percent_charged'],
            result['motos_20_percent_charged'],
            result['motos_30_percent_charged'],
            result['motos_50_percent_charged'],
            result['motos_70_percent_charged'],
            result['motos_80_percent_charged'],
            result['motos_100_percent_charged'],
        ])
        total_taxis = sum([
            result['mototaxis_10_percent_charged'],
            result['mototaxis_20_percent_charged'],
            result['mototaxis_30_percent_charged'],
            result['mototaxis_50_percent_charged'],
            result['mototaxis_70_percent_charged'],
            result['mototaxis_80_percent_charged'],
            result['mototaxis_100_percent_charged'],
        ])
        
        # [v5.6 DEBUG] Validar: total_motos debe ser igual a motos_can_charge
        if total_motos != motos_can_charge:
            print(f"[WARN] Motos mismatch: cargados={motos_can_charge} vs distribuidos={total_motos}")
        if total_taxis != mototaxis_can_charge:
            print(f"[WARN] Taxis mismatch: cargados={mototaxis_can_charge} vs distribuidos={total_taxis}")
        
        return result
