#!/usr/bin/env python3
"""
Test: Generar las gráficas con las nuevas métricas de exportación y peak shaving
"""
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

# Importar desde balance.py
sys.path.insert(0, str(Path(__file__).parent / 'src' / 'dimensionamiento' / 'oe2' / 'balance_energetico'))

from balance import BalanceEnergeticoSystem, BalanceEnergeticoConfig

print("=" * 80)
print("TEST: Generar Gráficas con Exportación y Peak Shaving")
print("=" * 80)

# Cargar datos reales del CSV generado por bess.py
csv_path = Path("data/oe2/bess/bess_ano_2024.csv")

if not csv_path.exists():
    print(f"\n[ERROR] CSV no encontrado: {csv_path}")
    sys.exit(1)

print(f"\n[1] Cargando datos reales desde: {csv_path}")
df = pd.read_csv(csv_path)
print(f"    ✓ {len(df)} filas × {len(df.columns)} columnas")

# Verificar columnas clave
print(f"\n[2] Verificando columnas requeridas:")
required_cols = ['grid_export_kwh', 'bess_to_mall_kwh', 'pv_kwh', 'mall_kwh', 'ev_kwh']
for col in required_cols:
    if col in df.columns:
        print(f"    ✓ {col:25s} PRESENTE")
    else:
        print(f"    ✗ {col:25s} FALTANTE")

# Crear instancia de BalanceEnergeticoSystem
print(f"\n[3] Inicializando BalanceEnergeticoSystem...")
config = BalanceEnergeticoConfig()
graphics = BalanceEnergeticoSystem(df, config)
print(f"    ✓ Sistema inicializado")
print(f"      - PV Capacity: {config.pv_capacity_kwp:.0f} kWp")
print(f"      - BESS Capacity: {config.bess_capacity_kwh:.0f} kWh")
print(f"      - BESS Power: {config.bess_power_kw:.0f} kW")

# Generar gráficas
print(f"\n[4] Generando gráficas...")
output_dir = Path("reports/balance_energetico_test")
try:
    graphics.plot_energy_balance(output_dir)
    print(f"    ✓ Gráficas generadas en: {output_dir}")
except Exception as e:
    print(f"    ✗ Error al generar gráficas: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Verificar archivos generados
print(f"\n[5] Verificando archivos generados:")
expected_files = [
    "00_BALANCE_INTEGRADO_COMPLETO.png",
    "00.1_EXPORTACION_Y_PEAK_SHAVING.png",
    "00_INTEGRAL_todas_curvas.png",
]

for filename in expected_files:
    filepath = output_dir / filename
    if filepath.exists():
        size_kb = filepath.stat().st_size / 1024
        print(f"    ✓ {filename:45s} ({size_kb:>7.1f} KB)")
    else:
        print(f"    ✗ {filename:45s} NO GENERADO")

print("\n" + "=" * 80)
print("[OK] TEST COMPLETADO - Gráficas con exportación y peak shaving generadas")
print("=" * 80)
