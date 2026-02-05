#!/usr/bin/env python3
"""
VERIFICACIÓN Y CORRECCIÓN DE CÁLCULOS REALES
- Solar 4,050 kWp genera ~4.86 GWh/año
- Grid Iquitos 0.4521 kg CO2/kWh
- Motos: 2,912 total | Consumo: 4 kWh/carga
- Mototaxis: 416 total | Consumo: 6 kWh/carga
"""

import numpy as np

print("=" * 80)
print("VERIFICACIÓN DE CÁLCULOS REALES")
print("=" * 80)
print()

# ============================================================================
# DATOS REALES DEL PROYECTO
# ============================================================================
TOTAL_MOTOS = 2912
TOTAL_MOTOTAXIS = 416
TOTAL_VEHICULOS = TOTAL_MOTOS + TOTAL_MOTOTAXIS

SOLAR_CAPACITY_KWP = 4050
SOLAR_ANNUAL_GENERATION = 4_050 * 1200  # kWh/año (1200 kWh/kWp en Iquitos)
SOLAR_HOURLY_AVG = SOLAR_ANNUAL_GENERATION / 8760

BESS_CAPACITY_KWH = 4520
GRID_CO2_INTENSITY = 0.4521  # kg CO2/kWh

# Consumo por carga
KWH_PER_MOTO_CHARGE = 4.0
KWH_PER_MOTOTAXI_CHARGE = 6.0

# Operación anual
OPERATING_DAYS_PER_YEAR = 365
HOURS_PER_DAY = 24
TOTAL_HOURS_PER_YEAR = OPERATING_DAYS_PER_YEAR * HOURS_PER_DAY

print("[DATOS REALES DEL PROYECTO]")
print("-" * 80)
print(f"Solar (4,050 kWp):")
print(f"  - Generación anual: {SOLAR_ANNUAL_GENERATION:,.0f} kWh = {SOLAR_ANNUAL_GENERATION/1e6:.2f} GWh")
print(f"  - Promedio horario: {SOLAR_HOURLY_AVG:.1f} kWh/h")
print(f"  - Horas/año: {TOTAL_HOURS_PER_YEAR:,}")
print()
print(f"Vehículos:")
print(f"  - Motos: {TOTAL_MOTOS:,}")
print(f"  - Mototaxis: {TOTAL_MOTOTAXIS:,}")
print(f"  - Total: {TOTAL_VEHICULOS:,}")
print()
print(f"Consumo por carga:")
print(f"  - Moto: {KWH_PER_MOTO_CHARGE} kWh")
print(f"  - Mototaxi: {KWH_PER_MOTOTAXI_CHARGE} kWh")
print()

# ============================================================================
# ESCENARIO ACTUAL (SALIDA DE ENTRENAMIENTO)
# ============================================================================
print()
print("[ESCENARIO ACTUAL - UNA HORA (paso 26000)]")
print("-" * 80)

grid_kwh_hour = 130.5
solar_kwh_hour = 86.6
motos_charged_hour = 249141 / TOTAL_HOURS_PER_YEAR  # Acumulado anual / horas
mototaxis_charged_hour = 23727 / TOTAL_HOURS_PER_YEAR

print(f"Grid importado: {grid_kwh_hour} kWh")
print(f"Solar generado: {solar_kwh_hour} kWh")
print(f"Motos cargadas (anual promeديado): {motos_charged_hour:.1f}/h")
print(f"Mototaxis cargados (anual promediado): {mototaxis_charged_hour:.1f}/h")
print()

# ============================================================================
# CÁLCULOS DE CONSISTENCIA
# ============================================================================
print("[CÁLCULOS DE CONSISTENCIA]")
print("-" * 80)

# Energía para motos y mototaxis en la hora
energy_motos_hour = motos_charged_hour * KWH_PER_MOTO_CHARGE
energy_mototaxis_hour = mototaxis_charged_hour * KWH_PER_MOTOTAXI_CHARGE
total_ev_energy_hour = energy_motos_hour + energy_mototaxis_hour

print(f"Energía motos (promediado): {energy_motos_hour:.2f} kWh/h")
print(f"Energía mototaxis (promediado): {energy_mototaxis_hour:.2f} kWh/h")
print(f"Total EV energy: {total_ev_energy_hour:.2f} kWh/h")
print()

# ✅ CHEQUEO 1: Energía cargada vs grid importado
print("✅ CHEQUEO 1: Energía cargada vs grid + solar")
total_energy_available = grid_kwh_hour + solar_kwh_hour
print(f"  - Disponible (grid + solar): {total_energy_available:.1f} kWh")
print(f"  - Usado para EVs: {total_ev_energy_hour:.2f} kWh")
print(f"  - Diferencia: {total_energy_available - total_ev_energy_hour:.1f} kWh (OK si > 0)")
print()

# ✅ CHEQUEO 2: Capacidad máxima diaria
max_motos_per_day = TOTAL_MOTOS / 1  # Máx cargas/día
max_mototaxis_per_day = TOTAL_MOTOTAXIS / 1
max_energy_per_day = (max_motos_per_day * KWH_PER_MOTO_CHARGE +
                       max_mototaxis_per_day * KWH_PER_MOTOTAXI_CHARGE)

print("✅ CHEQUEO 2: Capacidad máxima (si todos se cargaran 1x/día)")
print(f"  - Max motos/día: {max_motos_per_day:,.0f}")
print(f"  - Max mototaxis/día: {max_mototaxis_per_day:,.0f}")
print(f"  - Energía requerida: {max_energy_per_day:,.0f} kWh/día")
print(f"  - Disponible (24h): {(grid_kwh_hour + solar_kwh_hour) * 24:.0f} kWh/día")
print()

# ✅ CHEQUEO 3: CO2 evitado proporcional a solar
co2_intensity = GRID_CO2_INTENSITY
co2_avoided_indirect = solar_kwh_hour * co2_intensity

print("✅ CHEQUEO 3: CO₂ indirecto (solar evita grid)")
print(f"  - Solar: {solar_kwh_hour:.1f} kWh")
print(f"  - CO₂ intensidad grid: {co2_intensity} kg/kWh")
print(f"  - CO₂ evitado: {co2_avoided_indirect:.2f} kg")
print(f"  - Reportado en entrenamiento: 7.5 kg")
print(f"  ✓ CONSISTENTE" if abs(co2_avoided_indirect - 7.5) < 2 else f"  ✗ INCONSISTENTE")
print()

# ============================================================================
# PROBLEMA IDENTIFICADO
# ============================================================================
print()
print("[PROBLEMA IDENTIFICADO]")
print("=" * 80)

print()
print("El entrenamiento muestra:")
print(f"  - Motos anuales: {249141:,} (promedio {249141/365:.0f}/día)")
print(f"  - Mototaxis anuales: {23727:,} (promedio {23727/365:.0f}/día)")
print()
print("Realidad del proyecto:")
print(f"  - Motos disponibles: {TOTAL_MOTOS:,}")
print(f"  - Mototaxis disponibles: {TOTAL_MOTOTAXIS:,}")
print()
print("❌ PROBLEMA: El modelo carga TODOS los motos ({}/día) en apenas 1 hora promediado".format(TOTAL_MOTOS))
print("   Eso NO ES REALISTA - debería estar distribuido en el día (9AM-10PM = 13 horas)")
print()

# ============================================================================
# CORRECCIONES NECESARIAS
# ============================================================================
print()
print("[CORRECCIONES NECESARIAS]")
print("=" * 80)
print()
print("1. ACTIVAR PERFIL DE CARGA HORARIO (curva 9AM-10PM)")
print("   - Actualmente: carga uniforme 24h")
print("   - Debe ser: solo 9AM a 10PM (13 horas)")
print("   - Pico al mediodía (12-2PM)")
print()
print("2. LIMITAR MOTOS/MOTOTAXIS POR HORA")
print("   - Max motos/h: {} / 13h = {:.0f}/h".format(TOTAL_MOTOS, TOTAL_MOTOS/13))
print("   - Max mototaxis/h: {} / 13h = {:.0f}/h".format(TOTAL_MOTOTAXIS, TOTAL_MOTOTAXIS/13))
print()
print("3. DISTANCIA ENTRE CARGAS")
print("   - Autonomía moto: ~50km → requiere carga cada ~50km")
print("   - Autonomía mototaxi: ~40km → requiere carga cada ~40km")
print("   - Distancia típica diaria: 60-80km")
print("   - Cargas/día realistas: 1-2 por vehículo")
print()
print("4. ENERGÍA DIARIA TOTAL")
energy_per_day_realistic = (
    (TOTAL_MOTOS * 1.5) * KWH_PER_MOTO_CHARGE +  # 1.5 cargas/día promedio
    (TOTAL_MOTOTAXIS * 1.5) * KWH_PER_MOTOTAXI_CHARGE
)
print(f"   - Estimada: {energy_per_day_realistic:,.0f} kWh/día")
print(f"   - Disponible (24h × {grid_kwh_hour + solar_kwh_hour}): {(grid_kwh_hour + solar_kwh_hour)*24:,.0f} kWh/día")
print(f"   - ✓ Suficiente" if energy_per_day_realistic < (grid_kwh_hour + solar_kwh_hour)*24 else "   - ✗ Insuficiente")
print()

print()
print("=" * 80)
print("CONCLUSIÓN: El sistema necesita perfil horario realista")
print("=" * 80)
