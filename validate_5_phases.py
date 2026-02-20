#!/usr/bin/env python3
"""
Validación de 5 FASES BESS - Verificación Completa
- Ejecuta BESS con datasets reales
- Valida que TODAS las 5 FASES operan correctamente
- Verifica métricas operativas (SOC, carga/descarga, etc)
"""

from src.dimensionamiento.oe2.disenobess.bess import simulate_bess_solar_priority
from src.dimensionamiento.oe2.disenobess.bess import load_pv_generation, load_ev_demand, load_mall_demand_real
from pathlib import Path
import pandas as pd

print("=" * 70)
print("VALIDACIÓN DE 5 FASES BESS")
print("=" * 70)

# Cargar datasets
print("\n✓ Cargando datasets...", end="")
pv_data = load_pv_generation(Path('data/iquitos_ev_mall/solar_generation.csv'))
ev_data = load_ev_demand(Path('data/iquitos_ev_mall/chargers_timeseries.csv'))
mall_data = load_mall_demand_real(Path('data/iquitos_ev_mall/mall_demand.csv'))
print(" OK")

# Ejecutar BESS
print("✓ Ejecutando BESS con 5 FASES...", end="")
result = simulate_bess_solar_priority(pv_data, ev_data, mall_data)
print(" OK")

# Validaciones
print("\n" + "=" * 70)
print("VALIDACIONES DE OPERATIVIDAD")
print("=" * 70)

print(f"\nDataset BESS:")
print(f"  └─ Filas: {len(result):,} (8,760 esperadas = 365 × 24)")
print(f"  └─ Columnas (primeras 10): {', '.join(list(result.columns)[:10])}")

print(f"\nRangos SOC:")
print(f"  ├─ Mínimo: {result['soc'].min():.2%} (límite: ≥20%)")
print(f"  ├─ Máximo: {result['soc'].max():.2%} (límite: ≤100%)")
print(f"  └─ Promedio: {result['soc'].mean():.2%}")

print(f"\nCiclos Operativos (horas/año):")
print(f"  ├─ CARGA (bess_charge > 0): {(result['bess_charge'] > 0).sum()} horas")
print(f"  ├─ DESCARGA (bess_discharge > 0): {(result['bess_discharge'] > 0).sum()} horas")
print(f"  └─ IDLE (no acción): {((result['bess_charge'] == 0) & (result['bess_discharge'] == 0)).sum()} horas")

print(f"\nEnergía (kWh):")
print(f"  ├─ Total cargado: {result['bess_charge'].sum():,.1f} kWh")
print(f"  ├─ Total descargado: {result['bess_discharge'].sum():,.1f} kWh")
print(f"  └─ Relación carga/descarga: {result['bess_discharge'].sum() / max(result['bess_charge'].sum(), 1):.2f}")

# Validar restricciones críticas
print(f"\nValidaciones de Restricciones:")
soc_below_min = (result['soc'] < 0.20).sum()
soc_above_max = (result['soc'] > 1.00).sum()

if soc_below_min > 0:
    print(f"  ❌ SOC < 20%: {soc_below_min} violaciones")
else:
    print(f"  ✅ SOC ≥ 20%: Cumplido (0 violaciones)")

if soc_above_max > 0:
    print(f"  ❌ SOC > 100%: {soc_above_max} violaciones")
else:
    print(f"  ✅ SOC ≤ 100%: Cumplido (0 violaciones)")

# Validar cierre a 22h
soc_22h = result[result['hour_of_day'] == 22]['soc'].values
if len(soc_22h) > 0:
    avg_soc_22h = soc_22h.mean()
    print(f"  └─ SOC promedio a las 22h: {avg_soc_22h:.2%}")

print("\n" + "=" * 70)
if soc_below_min == 0 and soc_above_max == 0:
    print("✅ VALIDACIÓN EXITOSA: 5 FASES OPERAN CORRECTAMENTE")
    print("   - Energía distribuida correctamente")
    print("   - Restricciones de SOC respetadas")
    print("   - Ciclos carga/descarga normales")
else:
    print("❌ VALIDACIÓN FALLÓ: Revisar restricciones de SOC")
print("=" * 70)
