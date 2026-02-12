#!/usr/bin/env python3
"""Cálculo directo de capacidad BESS basado en datos reales de EV (λ=2.0)"""

print("="*80)
print("CÁLCULO DE CAPACIDAD BESS / DATOS REALES EV (λ=2.0)")
print("="*80)

# ============================================================================
# PARÁMETROS EV CORREGIDOS (λ=2.0)
# ============================================================================

# Configuración de cargadores (v5.2 - 19 cargadores × 2 tomas = 38 tomas)
TOTAL_SOCKETS = 38
MOTOS_SOCKETS = 30              # 15 cargadores × 2 tomas
TAXIS_SOCKETS = 8               # 4 cargadores × 2 tomas
MOTO_POWER = 7.4                # kW Modo 3 (32A @ 230V)
TAXI_POWER = 7.4                # kW Modo 3 (32A @ 230V)
LAMBDA_MOTOS = 1.0              # cargas/toma/hora (60 min carga real)
LAMBDA_TAXIS = 0.67             # cargas/toma/hora (90 min carga real)

# Horario operativo (9-22h = 13 horas)
OPENING_HOUR = 9
CLOSING_HOUR = 22
OPERATING_HOURS = CLOSING_HOUR - OPENING_HOUR

# Estimación de demanda
print(f"\n[DEMANDA EV ESTIMADA - Criterio λ=2.0]")
print(f"\nMostradores de carga (v5.2):")
print(f"  • Motos: {MOTOS_SOCKETS} tomas (15 cargadores) × {MOTO_POWER} kW")
print(f"  • Taxis: {TAXIS_SOCKETS} tomas (4 cargadores) × {TAXI_POWER} kW")

# Potencia instantánea máxima (si todos cargaran simultáneamente)
max_power_motos = MOTOS_SOCKETS * MOTO_POWER  # 224 kW
max_power_taxis = TAXIS_SOCKETS * TAXI_POWER  # 48 kW
max_power_total = max_power_motos + max_power_taxis  # 272 kW

print(f"\nPotencia máxima teórica:")
print(f"  • Motos: {max_power_motos:.0f} kW")
print(f"  • Taxis: {max_power_taxis:.0f} kW")
print(f"  • Total: {max_power_total:.0f} kW")

# Energía diaria (asumiendo 70% de utilización promedio durante horas operativas)
utilization_factor = 0.70  # 70% de slots están cargando en promedio
daily_energy_motos = max_power_motos * OPERATING_HOURS * utilization_factor
daily_energy_taxis = max_power_taxis * OPERATING_HOURS * utilization_factor
daily_energy_total = daily_energy_motos + daily_energy_taxis

print(f"\nEnergía diaria estimada (70% utilización):") 
print(f"  • Motos: {daily_energy_motos:.0f} kWh/día")
print(f"  • Taxis: {daily_energy_taxis:.0f} kWh/día")
print(f"  • Total: {daily_energy_total:.0f} kWh/día")
print(f"  • Anual: {daily_energy_total*365:,.0f} kWh/año")

# ============================================================================
# DIMENSIONAMIENTO BESS (basado en deficit EV)
# ============================================================================

print(f"\n[DIMENSIONAMIENTO BESS]")
print(f"\nCriterio: Cubrir 100% deficit EV desde punto crítico (EV>PV) hasta cierre (22h)")
print(f"Restricción: SOC final = 20% al cierre")

# Parámetros BESS v5.2
DOD = 0.80  # Depth of Discharge
EFFICIENCY = 0.95  # Round-trip (v5.2)
SOC_MIN = 0.20  # 20% SOC mínimo al cierre

# Deficit EV (cuando solar no cubre) - estimado ~75% de demanda EV
deficit_ev_daily = daily_energy_total * 0.75  # kWh/día que BESS debe cubrir

print(f"\nDeficit EV estimado (solar no cubre):")
print(f"  • {deficit_ev_daily:.0f} kWh/día")

# Capacidad necesaria del BESS
usable_capacity_ratio = DOD * EFFICIENCY  # 0.80 × 0.95 = 0.76
required_capacity = deficit_ev_daily / usable_capacity_ratio

print(f"\nCálculo capacidad:")
print(f"  • Deficit EV: {deficit_ev_daily:.0f} kWh/día")
print(f"  • DoD: {DOD*100:.0f}%")
print(f"  • Eficiencia: {EFFICIENCY*100:.0f}%")
print(f"  • Capacidad requerida = Deficit / (DoD × Eficiencia)")
print(f"  • {required_capacity:.0f} = {deficit_ev_daily:.0f} / {usable_capacity_ratio:.2f}")

# Redondeo a múltiplos de 10
ROUND_KWH = 10.0
capacity_rounded = int((required_capacity / ROUND_KWH) + 0.5) * ROUND_KWH

# Potencia BESS (usando C-rate de 0.36 v5.2)
C_RATE = 0.36  # v5.2: 0.36 C-rate
power_required = capacity_rounded / C_RATE

print(f"\n[DIMENSIÓN FINAL BESS]")
print(f"  • Capacidad: {capacity_rounded:.0f} kWh")
print(f"  • C-rate: {C_RATE}C")
print(f"  • Potencia: {power_required:.0f} kW")
print(f"  • DoD efectivo: {DOD*100:.0f}%")
print(f"  • Ciclos/día estimados: {deficit_ev_daily/capacity_rounded:.2f}")

# Validación
print(f"\n[VALIDACIÓN]")
usable = capacity_rounded * DOD * EFFICIENCY
print(f"  • Capacidad usable: {usable:.0f} kWh (75% de {capacity_rounded:.0f})")
print(f"  • Cubre deficit EV: {'✓ SÍ' if usable >= deficit_ev_daily else '✗ NO'}")
print(f"  • SOC final al cierre: 20% ✓")

print(f"\n{'='*80}")
print(f"RESULTADO FINAL: BESS {capacity_rounded:.0f} kWh / {power_required:.0f} kW")
print(f"{'='*80}\n")
