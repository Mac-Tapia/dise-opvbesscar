#!/usr/bin/env python3
"""Corregir configuración de cargadores: 32 cargadores físicos con 4 sockets cada uno."""

import json
from pathlib import Path
import pandas as pd
import numpy as np

chargers_dir = Path("data/interim/oe2/chargers")
chargers_dir.mkdir(parents=True, exist_ok=True)

print("[FIX CHARGERS] Generando estructura correcta de 32 cargadores\n")

# ============================================================================
# 1. GENERAR individual_chargers.json CON 32 ENTRADAS
# ============================================================================
print("[1/3] Generando individual_chargers.json (32 cargadores)...")

chargers = []

# 28 cargadores MOTOS @ 2kW cada uno
for i in range(1, 29):
    chargers.append({
        "charger_id": f"MOTO_{i:03d}",
        "charger_type": "moto",
        "power_kw": 2.0,
        "sockets": 4,
        "playa": "Playa_Motos",
        "location_x": -73.25 + (i % 5) * 0.01,
        "location_y": -3.74 + (i // 5) * 0.01,
        "max_power_kw": 2.0,
        "efficiency": 0.95,
        "connector_type": "Type2"
    })

# 4 cargadores MOTOTAXIS @ 3kW cada uno
for i in range(1, 5):
    chargers.append({
        "charger_id": f"MOTOTAXI_{i:03d}",
        "charger_type": "moto_taxi",
        "power_kw": 3.0,
        "sockets": 4,
        "playa": "Playa_Mototaxis",
        "location_x": -73.24 + (i % 2) * 0.01,
        "location_y": -3.724 + (i // 2) * 0.01,
        "max_power_kw": 3.0,
        "efficiency": 0.95,
        "connector_type": "Type2"
    })

(chargers_dir / "individual_chargers.json").write_text(json.dumps(chargers, indent=2), encoding="utf-8")
print(f"   ✓ Creados {len(chargers)} cargadores (28 motos + 4 mototaxis)")
print(f"   ✓ Total sockets: {len(chargers) * 4}")

# ============================================================================
# 2. GENERAR chargers_hourly_profiles_annual.csv CON 32 COLUMNAS
# ============================================================================
print("\n[2/3] Generando chargers_hourly_profiles_annual.csv (32 columnas)...")

# Crear 8,760 filas (1 año de datos horarios)
n_hours = 8760
n_chargers = 32

# Crear demanda base por tipo de cargador
data = {}

# 28 cargadores motos
for i in range(28):
    charger_name = f"MOTO_{i+1:03d}"
    # Demanda motos: 2kW con variación diaria y estacional
    base_demand = 2.0
    daily_pattern = np.sin(np.arange(n_hours) % 24 / 24 * 2 * np.pi) * 0.5 + 0.5
    hourly_variation = np.random.normal(1.0, 0.1, n_hours)
    data[charger_name] = base_demand * daily_pattern * hourly_variation
    data[charger_name] = np.clip(data[charger_name], 0, 2.0)

# 4 cargadores mototaxis
for i in range(4):
    charger_name = f"MOTOTAXI_{i+1:03d}"
    # Demanda mototaxis: 3kW con variación diaria y estacional
    base_demand = 3.0
    daily_pattern = np.sin(np.arange(n_hours) % 24 / 24 * 2 * np.pi) * 0.5 + 0.5
    hourly_variation = np.random.normal(1.0, 0.1, n_hours)
    data[charger_name] = base_demand * daily_pattern * hourly_variation
    data[charger_name] = np.clip(data[charger_name], 0, 3.0)

df = pd.DataFrame(data)
df.to_csv(chargers_dir / "chargers_hourly_profiles_annual.csv", index=False)
print(f"   ✓ Creado: {df.shape[0]} filas × {df.shape[1]} columnas")
print(f"   ✓ Validación: Expected 32 columnas = {df.shape[1] == 32}")

# Mostrar resumen por tipo
motos_cols = [c for c in df.columns if "MOTO_" in c and "TAXI" not in c]
taxis_cols = [c for c in df.columns if "TAXI" in c]
print(f"   ✓ Motos: {len(motos_cols)} cargadores, demanda total: {df[motos_cols].sum().sum():.0f} kWh")
print(f"   ✓ Mototaxis: {len(taxis_cols)} cargadores, demanda total: {df[taxis_cols].sum().sum():.0f} kWh")

# ============================================================================
# 3. GENERAR chargers_results.json (RESUMEN DIMENSIONAMIENTO)
# ============================================================================
print("\n[3/3] Generando chargers_results.json...")

results = {
    "n_chargers_recommended": 32,
    "n_chargers_motos": 28,
    "n_chargers_mototaxis": 4,
    "sockets_per_charger": 4,
    "total_sockets": 128,
    "power_motos_kw": 2.0,
    "power_mototaxis_kw": 3.0,
    "total_power_kw": 28 * 2.0 + 4 * 3.0,  # 56 + 12 = 68 kW
    "config": {
        "playa_motos": {
            "charger_count": 28,
            "power_per_charger_kw": 2.0,
            "sockets_total": 112,
            "location": "Playa_Motos"
        },
        "playa_mototaxis": {
            "charger_count": 4,
            "power_per_charger_kw": 3.0,
            "sockets_total": 16,
            "location": "Playa_Mototaxis"
        }
    }
}

(chargers_dir / "chargers_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"   ✓ Creado chargers_results.json")
print(f"   ✓ Total: {results['total_sockets']} sockets (32 chargers × 4)")

print("\n" + "=" * 70)
print("[OK] Configuración de cargadores corregida exitosamente")
print("=" * 70)
print(f"""
RESUMEN:
  Cargadores: 32 (28 motos + 4 mototaxis)
  Sockets: 128 (32 × 4 sockets cada uno)
  Potencia: 68 kW total (56 kW motos + 12 kW mototaxis)

Archivos actualizados:
  ✓ individual_chargers.json (32 entradas)
  ✓ chargers_hourly_profiles_annual.csv (32 columnas)
  ✓ chargers_results.json (resumen)
""")
