#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analisis de carga sin control - Motos vs Taxis"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore

BASE_DIR = Path("d:\\diseñopvbesscar")
DATA_DIR = BASE_DIR / "data" / "interim" / "oe2" / "chargers"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# Cargar configuracion
with open(DATA_DIR / "individual_chargers.json", "r", encoding='utf-8') as f:
    chargers: list[dict[str, Any]] = json.load(f)

motos = [c for c in chargers if c["charger_type"] == "moto"]
taxis = [c for c in chargers if c["charger_type"] == "moto_taxi"]

print("=" * 90)
print("REPORTE: CARGA SIN CONTROL - MOTOS vs MOTOTAXIS")
print("=" * 90)
print()
print(f"INFRAESTRUCTURA:")
print(f"  Motos: {len(motos)} cargadores x 4 sockets = {len(motos)*4} sockets a 2 kW")
print(f"  Taxis: {len(taxis)} cargadores x 4 sockets = {len(taxis)*4} sockets a 3 kW")
print(f"  Total: {len(chargers)} cargadores, 128 sockets, 272 kW nominal")
print()

# Cargar perfiles horarios
df_hourly = pd.read_csv(DATA_DIR / "chargers_hourly_profiles.csv")
moto_cols = [c for c in df_hourly.columns if "MOTO_CH_" in c and "TAXI" not in c]
taxi_cols = [c for c in df_hourly.columns if "MOTO_TAXI_CH_" in c]

print(f"  Motos encontradas: {len(moto_cols)} (esperadas 112)")
print(f"  Taxis encontradas: {len(taxi_cols)} (esperadas 16)")
print()

# Sumar demandas
motos_sum = df_hourly[moto_cols].sum(axis=1)
taxis_sum = df_hourly[taxi_cols].sum(axis=1) if len(taxi_cols) > 0 else pd.Series(0.0, index=df_hourly.index)
total_sum = motos_sum + taxis_sum

# Estadisticas
energy_motos: float = float(motos_sum.sum()) * 365
energy_taxis: float = float(taxis_sum.sum()) * 365 if len(taxi_cols) > 0 else 0.0
energy_total: float = float(total_sum.sum()) * 365

pow_motos_avg: float = float(motos_sum.mean())
pow_taxis_avg: float = float(taxis_sum.mean()) if len(taxi_cols) > 0 else 0.0
pow_total_avg: float = float(total_sum.mean())

pow_motos_peak: float = float(motos_sum.max())
pow_taxis_peak: float = float(taxis_sum.max()) if len(taxi_cols) > 0 else 0.0

print("DEMANDA ANUAL (proyectada de perfil 24h):")
print()
print("Motos:")
print(f"  Energia: {energy_motos:,.0f} kWh/ano")
print(f"  Potencia promedio: {pow_motos_avg:.2f} kW")
print(f"  Potencia pico: {pow_motos_peak:.2f} kW")
print(f"  CO2 baseline: {energy_motos * 0.4521 / 1000:.0f} t/ano")
print()

if len(taxi_cols) > 0:
    print("Mototaxis:")
    print(f"  Energia: {energy_taxis:,.0f} kWh/ano")
    print(f"  Potencia promedio: {pow_taxis_avg:.2f} kW")
    print(f"  Potencia pico: {pow_taxis_peak:.2f} kW")
    print(f"  CO2 baseline: {energy_taxis * 0.4521 / 1000:.0f} t/ano")
    print()

print("Total Sistema:")
print(f"  Energia: {energy_total:,.0f} kWh/ano")
print(f"  Potencia promedio: {pow_total_avg:.2f} kW")
total_max: float = float(total_sum.max())
print(f"  Potencia maxima: {total_max:.2f} kW")
print(f"  Utilizacion: {(pow_total_avg / 272) * 100:.1f} pct de 272 kW")
print(f"  CO2 baseline: {energy_total * 0.4521 / 1000:.0f} t/ano (sin optimizacion)")
print()

# Hallazgos
print("=" * 90)
print("HALLAZGOS CLAVE:")
print("=" * 90)
print()

util_motos: float = (pow_motos_avg / (len(motos) * 2.0)) * 100.0

if len(taxi_cols) > 0:
    print(f"1. Diferenciacion:")
    motos_pct: float = (energy_motos / energy_total) * 100.0
    taxis_pct: float = (energy_taxis / energy_total) * 100.0
    print(f"   - Motos: {motos_pct:.1f} pct de energia")
    print(f"   - Taxis: {taxis_pct:.1f} pct de energia")
    print()
    print(f"2. Ocupacion de sockets:")
    util_taxis: float = (pow_taxis_avg / (len(taxis) * 3.0)) * 100.0
    print(f"   - Motos: {util_motos:.1f} pct (bajo - flexible)")
    print(f"   - Taxis: {util_taxis:.1f} pct (alto - critico)")
else:
    print("No se encontraron cargadores de taxis en los datos")
    print(f"Ocupacion motos: {util_motos:.1f} pct")

print()
print(f"3. BESS puede servir {4520 / pow_total_avg:.1f} horas a demanda promedio")
print()

# Guardar CSV
df_export = pd.DataFrame({
    "hour": df_hourly["hour"],
    "motos_kw": motos_sum,
    "taxis_kw": taxis_sum,
    "total_kw": total_sum
})
df_export.to_csv(REPORTS_DIR / "demanda_horaria_motos_taxis.csv", index=False)
print(f"OK: demanda_horaria_motos_taxis.csv guardado")

# Resumen JSON
co2_motos: float = energy_motos * 0.4521 / 1000.0
co2_taxis: float = energy_taxis * 0.4521 / 1000.0
co2_total: float = energy_total * 0.4521 / 1000.0
sys_util: float = (pow_total_avg / 272.0) * 100.0

resumen: dict[str, Any] = {
    "titulo": "Analisis Carga Sin Control Baseline",
    "motos": {
        "chargers": len(motos),
        "sockets": len(motos) * 4,
        "energia_anual_kwh": int(energy_motos),
        "potencia_promedio_kw": round(pow_motos_avg, 2),
        "potencia_pico_kw": round(pow_motos_peak, 2),
        "co2_anual_t": round(co2_motos, 0)
    },
    "taxis": {
        "chargers": len(taxis),
        "sockets": len(taxis) * 4,
        "energia_anual_kwh": int(energy_taxis),
        "potencia_promedio_kw": round(pow_taxis_avg, 2),
        "potencia_pico_kw": round(pow_taxis_peak, 2),
        "co2_anual_t": round(co2_taxis, 0)
    },
    "total": {
        "energia_anual_kwh": int(energy_total),
        "potencia_promedio_kw": round(pow_total_avg, 2),
        "potencia_pico_kw": round(total_max, 2),
        "co2_anual_t": round(co2_total, 0),
        "utilizacion_pct": round(sys_util, 1)
    }
}

with open(REPORTS_DIR / "resumen_carga_baseline.json", "w", encoding='utf-8') as f:
    json.dump(resumen, f, indent=2, ensure_ascii=False)
print(f"OK: resumen_carga_baseline.json guardado")

print()
print("LISTO!")
