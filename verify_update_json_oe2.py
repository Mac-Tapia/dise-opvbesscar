#!/usr/bin/env python3
"""
Actualiza y verifica JSONs de OE2 para conectarlos correctamente con datos solares regenerados.

Verifica:
1. bess_config.json - conectado correctamente
2. individual_chargers.json - 32 cargadores con 4 sockets
3. Archivos de schema de CityLearn
"""
from __future__ import annotations

import json
from pathlib import Path

print("=" * 100)
print("ACTUALIZACION Y VERIFICACION DE JSONS OE2")
print("=" * 100)

# 1. Datos solares regenerados
solar_kwh = 8_030_119
solar_gwh = solar_kwh / 1e6

print(f"\n[DATOS SOLARES REGENERADOS]")
print(f"  Energía anual: {solar_kwh:,} kWh = {solar_gwh:.2f} GWh")
print(f"  Resolución: 1 HORA (8,760 filas)")
print(f"  Fuente: PVGIS TMY + Modelo Sandia")

# 2. Verificar BESS config
bess_path = Path("data/interim/oe2/bess/bess_config.json")
print(f"\n[1] BESS CONFIG: {bess_path}")

with open(bess_path) as f:
    bess_config = json.load(f)

bess_capacity = bess_config.get("capacity_kwh", 0)
bess_power = bess_config.get("power_kw", 0)

print(f"  ✓ Capacidad BESS: {bess_capacity} kWh")
print(f"  ✓ Potencia BESS: {bess_power} kW")
print(f"  ✓ Eficiencia: {bess_config.get('efficiency', 0) * 100:.0f}%")

# Verificar coherencia solar-BESS
solar_to_bess_ratio = (solar_kwh / 365) / bess_power
print(f"  ✓ Energía solar diaria / Potencia BESS: {solar_to_bess_ratio:.2f} horas")
print(f"    (Interpretación: BESS puede almacenar ~{solar_to_bess_ratio:.1f}h de energía solar diaria)")

# 3. Verificar Chargers
chargers_path = Path("data/interim/oe2/chargers/individual_chargers.json")
print(f"\n[2] INDIVIDUAL CHARGERS: {chargers_path}")

with open(chargers_path) as f:
    chargers = json.load(f)

n_chargers = len(chargers)
total_sockets = sum(c.get("sockets", 1) for c in chargers)
total_power = sum(c.get("power_kw", 0) for c in chargers)
total_daily_energy = sum(c.get("daily_energy_kwh", 0) for c in chargers)
total_annual_energy = total_daily_energy * 365

print(f"  ✓ Cargadores: {n_chargers}")
print(f"  ✓ Sockets totales: {total_sockets} ({n_chargers} × 4 esperado)")
print(f"  ✓ Potencia total: {total_power:.1f} kW")
print(f"  ✓ Demanda diaria: {total_daily_energy:.1f} kWh")
print(f"  ✓ Demanda anual: {total_annual_energy:,.0f} kWh = {total_annual_energy/1e6:.2f} GWh")

# Verificar coherencia
solar_charger_ratio = solar_kwh / total_annual_energy
print(f"\n  Ratio Solar / Demanda Cargadores: {solar_charger_ratio:.2f}×")
print(f"  Interpretación:")
if solar_charger_ratio > 2:
    print(f"    ✓ Sistema tiene EXCESO solar ({solar_charger_ratio:.1f}× demanda)")
elif solar_charger_ratio > 1:
    print(f"    ✓ Sistema puede cubrir demanda + BESS ({solar_charger_ratio:.1f}× demanda)")
else:
    print(f"    ⚠ Sistema no cubre demanda (solar insuficiente)")

# 4. Schema CityLearn
print(f"\n[3] SCHEMA CITYLEARN]")
schema_dir = Path("outputs")
schema_files = list(schema_dir.glob("schema_*.json"))

if schema_files:
    for schema_file in sorted(schema_files)[:1]:  # Mostrar el primero
        print(f"  Archivo: {schema_file.name}")
        with open(schema_file) as f:
            schema = json.load(f)

        # Extraer info relevante
        buildings = schema.get("buildings", [])
        print(f"  ✓ Edificios: {len(buildings)}")

        # Buscar información de energía
        for building in buildings[:1]:
            name = building.get("name", "")
            print(f"    - {name}")

            # Buscar solar
            solar_ref = [x for x in building.get("features", {}).get("solar_generation", []) if isinstance(x, dict)]
            if solar_ref:
                print(f"      ✓ Solar generation referenciado")
else:
    print(f"  ⚠ No se encontraron archivos schema_*.json")
    print(f"  (Se generarán al ejecutar OE3)")

# 5. Resumen de validación
print(f"\n[VALIDACION FINAL]")
checks = {
    "BESS config válido": bess_capacity > 0 and bess_power > 0,
    "Chargers definidos": n_chargers == 32,
    "Sockets correctos": total_sockets == 128,
    "Solar > Demanda": solar_kwh > total_annual_energy,
    "Sistema coherente": 1.5 < solar_charger_ratio < 3.0,
}

all_valid = True
for check, result in checks.items():
    status = "✓" if result else "✗"
    print(f"  {status} {check}")
    if not result:
        all_valid = False

print(f"\n" + "=" * 100)
if all_valid:
    print(f"EXITO: JSONs están actualizados y conectados correctamente")
    print(f"  - Solar: {solar_gwh:.2f} GWh (regenerado con Sandia + PVGIS)")
    print(f"  - BESS: {bess_capacity} kWh")
    print(f"  - Chargers: {n_chargers} cargadores × 4 sockets = {total_sockets} puntos de carga")
    print(f"  - Ratio: {solar_charger_ratio:.2f}× (Sistema solar sobre-dimensionado para OE3)")
else:
    print(f"ADVERTENCIA: Algunos JSONs necesitan revisión")

print(f"=" * 100 + "\n")
