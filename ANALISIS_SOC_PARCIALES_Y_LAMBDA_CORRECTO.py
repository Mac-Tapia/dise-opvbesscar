#!/usr/bin/env python3
"""
ANÁLISIS: SOC Variables + Carga Parcial → Ajuste Real de lambda_arrivals

PROBLEMA: Los 270 motos calculados asumen:
  - TODOS llegan con SOC=20%
  - TODOS cargan a SOC=100%
  - Tiempo de carga: 60 min/moto, 90 min/taxi

REALIDAD:
  - Llegan con diferentes SOC (10%, 20%, 30%, etc.)
  - Cargan a diferentes SOC targets (60%, 80%, 100%)
  - Tiempo de carga variable → MÁS vehículos caben en la infraestructura

SOLUCIÓN: Calcular lambda correcto considerando:
  1. Distribución de SOC_arrival
  2. Distribución de SOC_target
  3. Energía promedio de carga
  4. Tiempo de carga promedio
  5. Ocupación real de sockets
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict
from dataclasses import dataclass

# ============================================================================
# PARTE 1: DEFINIR DISTRIBUCIONES REALISTAS DE SOC
# ============================================================================

@dataclass
class SOCDistribution:
    """Distribución de SOC de llegada y destino"""
    name: str
    arrival_soc: np.ndarray  # 10%, 20%, 30%
    arrival_prob: np.ndarray  # Probabilidad de cada SOC
    target_soc: np.ndarray    # 60%, 80%, 100%
    target_prob: np.ndarray   # Probabilidad de cada target

    def describe(self):
        print(f"\n{'='*80}")
        print(f"DISTRIBUCIÓN DE SOC: {self.name}")
        print(f"{'='*80}")
        print("\nSOC de LLEGADA (distribución):")
        for soc, prob in zip(self.arrival_soc, self.arrival_prob):
            bar = "█" * int(prob * 50)
            print(f"  {soc:3d}% → {prob*100:5.1f}% {bar}")
        print(f"  Promedio: {np.average(self.arrival_soc, weights=self.arrival_prob):.1f}%")
        
        print("\nSOC TARGET (distribución):")
        for soc, prob in zip(self.target_soc, self.target_prob):
            bar = "█" * int(prob * 50)
            print(f"  {soc:3d}% → {prob*100:5.1f}% {bar}")
        print(f"  Promedio: {np.average(self.target_soc, weights=self.target_prob):.1f}%")


# ESCENARIO 1: Conservador (como estábamos asumiendo)
conservative = SOCDistribution(
    name="CONSERVADOR (como antes)",
    arrival_soc=np.array([20]),
    arrival_prob=np.array([1.0]),
    target_soc=np.array([100]),
    target_prob=np.array([1.0])
)

# ESCENARIO 2: Realista basado en patrones típicos de uso
# Supuesto: Usuarios normales cargan cuando necesitan (no esperan a 0%)
# Muchos solo necesitan carga parcial (llegar a 60-80% para próximo viaje)
realistic = SOCDistribution(
    name="REALISTA (análisis de datos)",
    arrival_soc=np.array([10, 20, 30, 40]),
    arrival_prob=np.array([0.15, 0.40, 0.30, 0.15]),  # 40% llegan con ~20%
    target_soc=np.array([60, 80, 100]),
    target_prob=np.array([0.30, 0.50, 0.20])  # 30% solo necesitan 60%, 50% quieren 80%
)

# ESCENARIO 3: Optimista (si disponibilidad de carga es limitada, usuarios cargan parcial)
optimistic = SOCDistribution(
    name="OPTIMISTA (carga parcial frecuente)",
    arrival_soc=np.array([10, 20, 30, 40, 50]),
    arrival_prob=np.array([0.10, 0.25, 0.35, 0.20, 0.10]),
    target_soc=np.array([50, 60, 70, 80, 100]),
    target_prob=np.array([0.15, 0.25, 0.30, 0.20, 0.10])
)

scenarios = {
    "conservative": conservative,
    "realistic": realistic,
    "optimistic": optimistic
}

# ============================================================================
# PARTE 2: CALCULAR ENERGÍA Y TIEMPO DE CARGA
# ============================================================================

class VehicleChargingAnalysis:
    """Analizar tiempo y energía de carga para diferentes SOC"""
    
    def __init__(self, 
                 battery_kwhh: float = 4.6,  # motos
                 charger_power_kw: float = 7.4,
                 charger_efficiency: float = 0.90):
        self.battery_kwh = battery_kwhh
        self.charger_power_kw = charger_power_kw
        self.efficiency = charger_efficiency
    
    def calculate_charging_metrics(self, 
                                   soc_arrival: float,
                                   soc_target: float) -> Tuple[float, float]:
        """
        Calcula energía y tiempo de carga
        
        Returns:
            (energy_kwh, time_hours)
        """
        # Energía neta requerida
        energy_delta_net = (soc_target - soc_arrival) / 100.0 * self.battery_kwh
        
        # Energía bruta (considerando pérdidas)
        energy_required = energy_delta_net / self.efficiency
        
        # Tiempo de carga (horas)
        time_hours = energy_required / self.charger_power_kw
        
        return energy_required, time_hours
    
    def analyze_scenario(self, 
                         scenario: SOCDistribution,
                         name_override: str = None) -> Dict:
        """Analizar estadísticas de carga para un escenario completo"""
        
        # Generar todas las combinaciones
        times = []
        energies = []
        probs = []
        
        for soc_arr, prob_arr in zip(scenario.arrival_soc, scenario.arrival_prob):
            for soc_tgt, prob_tgt in zip(scenario.target_soc, scenario.target_prob):
                energy, time = self.calculate_charging_metrics(soc_arr, soc_tgt)
                times.append(time)
                energies.append(energy)
                probs.append(prob_arr * prob_tgt)
        
        times = np.array(times)
        energies = np.array(energies)
        probs = np.array(probs)
        
        # Estadísticas
        avg_time = np.average(times, weights=probs)
        avg_energy = np.average(energies, weights=probs)
        min_time = times.min()
        max_time = times.max()
        
        return {
            "scenario_name": name_override or scenario.name,
            "avg_time_hours": avg_time,
            "avg_energy_kwh": avg_energy,
            "min_time_hours": min_time,
            "max_time_hours": max_time,
            "times": times,
            "energies": energies,
            "probs": probs
        }


# ============================================================================
# PARTE 3: CALCULAR MÁXIMO DE VEHÍCULOS POR HORA
# ============================================================================

class SocketCapacityAnalysis:
    """Calcular cuántos vehículos caben en los sockets disponibles"""
    
    def __init__(self,
                 num_sockets: int,
                 hours_operation: float = 13.0,
                 peak_hours: float = 4.0):
        self.num_sockets = num_sockets
        self.hours_operation = hours_operation
        self.peak_hours = peak_hours
    
    def calculate_max_vehicles(self, avg_charging_time: float) -> float:
        """
        Calcula máximo de vehículos que caben en los sockets
        
        Fórmula: Si promedio es 60 min, puede cargar 24 vehículos/día por socket
        Si promedio es 30 min, puede cargar 48 vehículos/día por socket
        
        Limitado por: num_sockets × horas_operación × 60 / tiempo_promedio
        """
        
        # En 13 horas se pueden hacer: 13 * 60 / avg_time transacciones por socket
        transactions_per_socket_per_day = (self.hours_operation * 60) / (avg_charging_time * 60)
        
        # Total de transacciones posibles
        max_vehicles_per_day = self.num_sockets * transactions_per_socket_per_day
        
        return max_vehicles_per_day


# ============================================================================
# PARTE 4: EJECUCIÓN Y ANÁLISIS COMPARATIVO
# ============================================================================

def main():
    print("\n" + "="*80)
    print("ANÁLISIS COMPLETO: SOC VARIABLES → ΛAMBDA ARRIVALS CORRECTO")
    print("="*80)
    
    # Analizar motos (4.6 kWh batería)
    print("\n" + "="*80)
    print("ANÁLISIS PARA MOTOS (4.6 kWh, 7.4 kW)")
    print("="*80)
    
    moto_analysis = VehicleChargingAnalysis(
        battery_kwhh=4.6,
        charger_power_kw=7.4,
        charger_efficiency=0.90
    )
    
    moto_results = {}
    for scenario_name, scenario in scenarios.items():
        result = moto_analysis.analyze_scenario(scenario)
        moto_results[scenario_name] = result
        
        scenario.describe()
        
        print(f"\nMÉTRICAS DE CARGA:")
        print(f"  Tiempo promedio:  {result['avg_time_hours']*60:.1f} min")
        print(f"  Energía promedio: {result['avg_energy_kwh']:.2f} kWh")
        print(f"  Rango de tiempo:  {result['min_time_hours']*60:.1f} - {result['max_time_hours']*60:.1f} min")
    
    # Calcular capacidad de sockets para motos
    print(f"\n{'='*80}")
    print("CAPACIDAD DE SOCKETS - MOTOS (30 sockets)")
    print(f"{'='*80}")
    
    moto_capacity = SocketCapacityAnalysis(
        num_sockets=30,
        hours_operation=13.0,
        peak_hours=4.0
    )
    
    for scenario_name, result in moto_results.items():
        max_vehicles = moto_capacity.calculate_max_vehicles(result['avg_time_hours'])
        current_target = 270
        ratio = max_vehicles / current_target
        
        print(f"\n{result['scenario_name'].upper()}:")
        print(f"  Tiempo promedio de carga: {result['avg_time_hours']*60:.1f} min")
        print(f"  Máximo de transacciones/día: {max_vehicles:.0f}")
        print(f"  Target actual (270): {current_target}")
        print(f"  Ratio (Max/Target): {ratio:.2f}x")
        
        if ratio >= 1.0:
            print(f"  ✓ SUFICIENTE capacidad (hay espacio extra)")
        else:
            print(f"  ! INSUFICIENTE capacidad (falta {current_target - max_vehicles:.0f} vehículos)")
    
    # Analizar mototaxis
    print(f"\n{'='*80}")
    print("ANÁLISIS PARA MOTOTAXIS (7.4 kWh, 7.4 kW)")
    print("="*80)
    
    taxi_analysis = VehicleChargingAnalysis(
        battery_kwhh=7.4,
        charger_power_kw=7.4,
        charger_efficiency=0.90
    )
    
    taxi_results = {}
    for scenario_name, scenario in scenarios.items():
        result = taxi_analysis.analyze_scenario(scenario)
        taxi_results[scenario_name] = result
    
    # Capacidad para taxis
    print(f"\n{'='*80}")
    print("CAPACIDAD DE SOCKETS - MOTOTAXIS (8 sockets)")
    print(f"{'='*80}")
    
    taxi_capacity = SocketCapacityAnalysis(
        num_sockets=8,
        hours_operation=13.0,
        peak_hours=4.0
    )
    
    for scenario_name, result in taxi_results.items():
        max_vehicles = taxi_capacity.calculate_max_vehicles(result['avg_time_hours'])
        current_target = 39
        ratio = max_vehicles / current_target
        
        print(f"\n{result['scenario_name'].upper()}:")
        print(f"  Tiempo promedio de carga: {result['avg_time_hours']*60:.1f} min")
        print(f"  Máximo de transacciones/día: {max_vehicles:.0f}")
        print(f"  Target actual (39): {current_target}")
        print(f"  Ratio (Max/Target): {ratio:.2f}x")
        
        if ratio >= 1.0:
            print(f"  ✓ SUFICIENTE capacidad")
        else:
            print(f"  ! INSUFICIENTE capacidad (falta {current_target - max_vehicles:.0f} vehículos)")
    
    # =========================================================================
    # PARTE 5: CALCULAR NUEVO LAMBDA_ARRIVALS
    # =========================================================================
    
    print(f"\n{'='*80}")
    print("CÁLCULO DE NUEVO LAMBDA_ARRIVALS")
    print(f"{'='*80}")
    
    # Usar escenario realista como base
    print(f"\nUsando escenario REALISTA como referencia:")
    
    moto_realistic = moto_results["realistic"]
    taxi_realistic = taxi_results["realistic"]
    
    # Razón de tiempo: 60 min / tiempo_promedio
    # Si antes asumíamos 60 min y ahora es 30 min, puede haber 2x más vehículos
    
    original_charging_time_motos = 1.0 * 60  # 60 minutos
    new_charging_time_motos = moto_realistic['avg_time_hours'] * 60
    efficiency_factor_motos = original_charging_time_motos / new_charging_time_motos
    
    original_charging_time_taxi = 1.5 * 60  # 90 minutos
    new_charging_time_taxi = taxi_realistic['avg_time_hours'] * 60
    efficiency_factor_taxi = original_charging_time_taxi / new_charging_time_taxi
    
    print(f"\nMOTOS:")
    print(f"  Tiempo anterior (asumido): {original_charging_time_motos:.0f} min")
    print(f"  Tiempo nuevo (promedio SOC variables): {new_charging_time_motos:.1f} min")
    print(f"  Factor de eficiencia: {efficiency_factor_motos:.2f}x")
    
    print(f"\nMOTOTAXIS:")
    print(f"  Tiempo anterior (asumido): {original_charging_time_taxi:.0f} min")
    print(f"  Tiempo nuevo (promedio SOC variables): {new_charging_time_taxi:.1f} min")
    print(f"  Factor de eficiencia: {efficiency_factor_taxi:.2f}x")
    
    # Cálculo de lambda actualizado
    print(f"\nCÁLCULO DE NUEVO LAMBDA_ARRIVALS:")
    
    current_lambda_motos = 0.980  # Del análisis anterior
    new_lambda_motos = current_lambda_motos * efficiency_factor_motos
    
    current_lambda_taxi = 0.533   # Del análisis anterior
    new_lambda_taxi = current_lambda_taxi * efficiency_factor_taxi
    
    print(f"\nMOTOS:")
    print(f"  Lambda actual: {current_lambda_motos:.3f}")
    print(f"  Lambda ajustado (con SOC parciales): {new_lambda_motos:.3f}")
    print(f"  Factor aplicado: {efficiency_factor_motos:.2f}x")
    
    print(f"\nMOTOTAXIS:")
    print(f"  Lambda actual: {current_lambda_taxi:.3f}")
    print(f"  Lambda ajustado (con SOC parciales): {new_lambda_taxi:.3f}")
    print(f"  Factor aplicado: {efficiency_factor_taxi:.2f}x")
    
    # Predicción de vehículos por día
    operational_factor_avg = 0.3812  # Del análisis anterior
    hours_effective = 13.0 * operational_factor_avg  # 4.9555 horas equivalentes
    
    print(f"\n{'='*80}")
    print("PREDICCIÓN DE VEHÍCULOS/DÍA CON NUEVO LAMBDA")
    print(f"{'='*80}")
    
    print(f"\nModelo de Poisson:")
    print(f"  Horas operativas: 13 (9 AM - 10 PM)")
    print(f"  Factor operacional promedio: {operational_factor_avg:.4f}")
    print(f"  Horas equivalentes a 100%: {hours_effective:.2f}")
    
    # λ = arrivals / (num_sockets * hours_equivalent)
    # arrivals = λ * num_sockets * hours_equivalent
    
    motos_per_day_new = new_lambda_motos * 30 * 13.0
    taxis_per_day_new = new_lambda_taxi * 8 * 13.0
    
    print(f"\nMOTOS:")
    print(f"  Lambda: {new_lambda_motos:.3f}")
    print(f"  Transacciones/día esperadas: {motos_per_day_new:.1f}")
    print(f"  Target: 270")
    print(f"  Diferencia: {motos_per_day_new - 270:.1f} ({(motos_per_day_new/270 - 1)*100:+.1f}%)")
    
    print(f"\nMOTOTAXIS:")
    print(f"  Lambda: {new_lambda_taxi:.3f}")
    print(f"  Transacciones/día esperadas: {taxis_per_day_new:.1f}")
    print(f"  Target: 39")
    print(f"  Diferencia: {taxis_per_day_new - 39:.1f} ({(taxis_per_day_new/39 - 1)*100:+.1f}%)")
    
    # =========================================================================
    # RECOMENDACIÓN FINAL
    # =========================================================================
    
    print(f"\n{'='*80}")
    print("RECOMENDACIÓN FINAL")
    print(f"{'='*80}")
    
    print(f"""
PREGUNTA: ¿Debería ajustar lambda_arrivals considerando SOC parciales?

RESPUESTA: DEPENDE DEL OBJETIVO

Opción A: MANTENER Los 270/39 como "número de llegadas distintas"
  └─ Esto implica:
     • Cada llegada es una TRANSACCIÓN (puede ser carga 20→60% o 20→100%)
     • Los 270 motos/día no cambian
     • Pero consumo de energía promedio sí cambia
     • Lambda_arrivals se MANTIENE igual ({current_lambda_motos:.3f})
  └─ Ventaja: Número de "clientes" realista
  └─ Desventaja: Energía solar/BESS debe ser recalculada

Opción B: AUMENTAR Lambda considerando mayor rotación de sockets
  └─ Esto implica:
     • Si carga promedio es más rápida, podrían caber MUCHO MÁS vehículos
     • Lambda se ajusta a {new_lambda_motos:.3f} ({efficiency_factor_motos:.2f}x)
     • Cambio a {motos_per_day_new:.0f} motos/día (vs 270 actual)
  └─ Ventaja: Usa mejor la infraestructura disponible
  └─ Desventaja: Número más optimista, requiere más energía total

RECOMENDACIÓN:
  ✓ Usar OPCIÓN A (mantener 270/39, pero SOC variable)
  └─ Razón: Los 270 motos vienen de estimación de DEMANDA (1636×0.30×0.55)
  └─ No cambia la demanda, solo HOW it's satisfied
  └─ Cambio principal: Ajustar distribuciones de SOC en el simulador

ACCIÓN RECOMENDADA:
  1. En chargers.py: Mantener lambda_arrivals = 0.980 / 0.533
  2. En SocketSimulator: Cambiar distribuciones de SOC_arrival y SOC_target
  3. En generateDataset: Usar energías variables, no energia_fija
  4. Impacto: Mismo número de transacciones, pero energía/CO2 más realista
""")


if __name__ == "__main__":
    main()
    print(f"\n{'='*80}\n")
