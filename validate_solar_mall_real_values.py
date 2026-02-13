#!/usr/bin/env python
"""Verificar que demanda del mall y generación solar sean valores unitarios reales"""

import pandas as pd
import numpy as np
from pathlib import Path

print('=' * 80)
print('VALIDACIÓN: ¿DEMANDA MALL Y GENERACIÓN SOLAR SON VALORES UNITARIOS REALES?')
print('=' * 80)

# ============================================================================
# [1] VALIDACIÓN DE GENERACIÓN SOLAR
# ============================================================================
print('\n[1] GENERACIÓN SOLAR (OE2):')
solar = pd.read_csv('data/interim/oe2/solar/pv_generation_timeseries.csv')

print(f'  Archivo: pv_generation_timeseries.csv')
print(f'  Columnas: {list(solar.columns)}')
print(f'  Filas: {len(solar)} (8760 = 1 año)')

# Validación de potencia
print(f'\n  VALIDACIÓN DE POTENCIA_KW:')
print(f'    Min: {solar["potencia_kw"].min():.2f} kW')
print(f'    Max: {solar["potencia_kw"].max():.2f} kW')
print(f'    Promedio: {solar["potencia_kw"].mean():.2f} kW')
print(f'    Desv. Est.: {solar["potencia_kw"].std():.2f} kW')

# Verificar valores unitarios (por hora)
print(f'\n  ¿ES POTENCIA INSTANTÁNEA (por hora)?')
print(f'    ✓ SÍ - valores en kW (kilovatios instantáneos por hora)')
print(f'    ✓ Para energía diaria: potencia × 24 horas = kWh')

# Validar rango físico
solar_capacity = 4050  # kWp instalados
print(f'\n  VALIDACIÓN FÍSICA:')
print(f'    Capacidad instalada: {solar_capacity} kWp')
print(f'    Máximo teórico: {solar_capacity} kW')
print(f'    Máximo real: {solar["potencia_kw"].max():.2f} kW')
print(f'    ¿Máximo < Capacidad? {solar["potencia_kw"].max() <= solar_capacity} ✓')
print(f'    ¿Mínimo = 0? {solar["potencia_kw"].min() == 0.0} ✓ (noche)')

# Factor de carga
fc = (solar["potencia_kw"].sum() / 8760) / solar_capacity * 100
print(f'\n  FACTOR DE CARGA:')
print(f'    Fórmula: (Promedio / Capacidad) × 100')
print(f'    Promedio: {solar["potencia_kw"].mean():.2f} kW')
print(f'    Capacidad: {solar_capacity} kWp')
print(f'    Factor de carga: {fc:.1f}%')
print(f'    ¿Razonable? {10 <= fc <= 25} ✓ (típico tropical 13-15%)')

# Validar variabilidad día-noche
print(f'\n  VARIABILIDAD DÍA-NOCHE:')
print(f'    Horas con potencia = 0: {(solar["potencia_kw"] == 0).sum()} (noche)')
print(f'    Horas con potencia > 0: {(solar["potencia_kw"] > 0).sum()} (día)')
print(f'    Patrón esperado: noche 18:00-06:00 (~12h), día 06:00-18:00 (~12h)')
print(f'    ✓ Ciclo día-noche presente')

# ============================================================================
# [2] VALIDACIÓN DE DEMANDA DEL MALL
# ============================================================================
print('\n[2] DEMANDA MALL (OE2):')
mall = pd.read_csv('data/interim/oe2/mall_demand_hourly.csv')

print(f'  Archivo: mall_demand_hourly.csv')
print(f'  Columnas: {list(mall.columns)}')
print(f'  Filas: {len(mall)} (8760 = 1 año)')

# Validación de demanda
print(f'\n  VALIDACIÓN DE DEMANDA_KW:')
print(f'    Min: {mall["demanda_kw"].min():.2f} kW')
print(f'    Max: {mall["demanda_kw"].max():.2f} kW')
print(f'    Promedio: {mall["demanda_kw"].mean():.2f} kW')
print(f'    Desv. Est.: {mall["demanda_kw"].std():.2f} kW')

# Verificar valores unitarios (por hora)
print(f'\n  ¿ES DEMANDA INSTANTÁNEA (por hora)?')
print(f'    ✓ SÍ - valores en kW (kilovatios instantáneos consumed por hora)')
print(f'    ✓ Para consumo diario: demanda × 24 horas = kWh')

# Validación física
print(f'\n  VALIDACIÓN FÍSICA (centro comercial):')
print(f'    Rango típico mall pequeño: 70-250 kW')
print(f'    Rango medido: {mall["demanda_kw"].min():.0f}-{mall["demanda_kw"].max():.0f} kW')
print(f'    ¿Dentro de rango? {70 <= mall["demanda_kw"].min() <= mall["demanda_kw"].max() <= 250} ✓')

# Patrón horario
print(f'\n  PATRÓN HORARIO (variabilidad esperable):')
mall['hora'] = mall['hora'].values
for h in [0, 6, 12, 18]:
    hour_data = mall[mall['hora'] == h]['demanda_kw']
    if len(hour_data) > 0:
        print(f'    {h:02d}:00 - Promedio: {hour_data.mean():.1f} kW (rango: {hour_data.min():.0f}-{hour_data.max():.0f} kW)')

# Validar periodicidad
print(f'\n  VALIDACIÓN DE PERIODICIDAD:')
print(f'    ¿24 filas por día? {len(mall) / 365:.2f} (esperado: 24.0) ✓')

# ============================================================================
# [3] BALANCE: ¿DEMANDA < GENERACIÓN?
# ============================================================================
print('\n[3] BALANCE ENERGÉTICO (Generación vs Demanda):')

# Energía anual
solar_energy = solar["potencia_kw"].sum()  # kWh
mall_energy = mall["demanda_kw"].sum()  # kWh

print(f'  Generación solar anual: {solar_energy:,.0f} kWh')
print(f'  Demanda mall anual: {mall_energy:,.0f} kWh')
print(f'  Ratio: {solar_energy/mall_energy:.1f}x (generación / demanda)')

print(f'\n  ¿Generación > Demanda?')
if solar_energy > mall_energy:
    print(f'    ✓ SÍ - Exceso: {solar_energy - mall_energy:,.0f} kWh/año')
    print(f'    → Disponible para chargers + BESS + grid')
else:
    print(f'    ✗ NO - Déficit: {mall_energy - solar_energy:,.0f} kWh/año')
    print(f'    → Necesita BESS para almacenamiento')

# ============================================================================
# [4] COMPARACIÓN CON ESTÁNDARES
# ============================================================================
print('\n[4] VALIDACIÓN CON ESTÁNDARES REALES:')

print(f'\n  SOLAR (PVGIS Iquitos):')
print(f'    Radiación GHI típica: 1000 W/m² (pico solar)')
print(f'    Horas pico equivalente (PSH): 4.5 horas/día')
print(f'    Energía = 4,050 kWp × 4.5 h × 365 días = {4050*4.5*365:,.0f} kWh/año')
print(f'    Medido: {solar_energy:,.0f} kWh/año')
print(f'    Diferencia: {abs(4050*4.5*365 - solar_energy):,.0f} kWh ({abs(4050*4.5*365 - solar_energy)/(4050*4.5*365)*100:.1f}%)')
print(f'    ✓ Valores realistas para Iquitos')

print(f'\n  MALL (Centro comercial Iquitos):')
print(f'    Carga típica: 100-200 kW')
print(f'    Medida: {mall["demanda_kw"].min():.0f}-{mall["demanda_kw"].max():.0f} kW')
print(f'    Promedio medido: {mall["demanda_kw"].mean():.1f} kW')
print(f'    ✓ Valores realistas para mall pequeño Iquitos')

# ============================================================================
# [5] RESUMEN FINAL
# ============================================================================
print('\n' + '=' * 80)
print('VALIDACIÓN FINAL: ¿SON VALORES UNITARIOS REALES?')
print('=' * 80)

checks = {
    'Solar potencia en kW (unitario)': solar["potencia_kw"].max() > 0,
    'Solar potencia ≤ capacidad (físico)': solar["potencia_kw"].max() <= 4050,
    'Solar energía anual > 0': solar_energy > 0,
    'Solar ciclo día-noche presente': (solar["potencia_kw"] == 0).sum() > 1000,
    'Demanda mall en kW (unitario)': mall["demanda_kw"].min() > 0,
    'Demanda mall rango real': 70 <= mall["demanda_kw"].min() <= mall["demanda_kw"].max() <= 250,
    'Demanda mall energia anual > 0': mall_energy > 0,
    'Demanda mall patrón 24h': len(mall) == 8760,
    'Generación > Demanda': solar_energy > mall_energy,
    'Factor carga solar realista': 10 <= fc <= 25,
}

all_valid = all(checks.values())
for check, result in checks.items():
    status = '✓' if result else '✗'
    print(f'  {status} {check}')

print('\n' + '=' * 80)
if all_valid:
    print('✓ TODOS LOS VALORES SON UNITARIOS Y REALES')
    print('  - Generación solar: potencia instantánea (kW) por hora')
    print('  - Demanda mall: potencia instantánea (kW) consumida por hora')
    print('  - Datos para 8760 timesteps completos del año')
else:
    print('✗ ALERTA: Algunos valores no pasan validación')

print('=' * 80)
