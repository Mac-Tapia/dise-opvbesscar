#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis rápido: Carga sin control - Motos vs Mototaxis
Genera reporte de demanda horaria y patrones de carga
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore

BASE_DIR = Path("d:\\diseñopvbesscar")
DATA_DIR = BASE_DIR / "data" / "interim" / "oe2" / "chargers"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# Cargar configuración
with open(DATA_DIR / "individual_chargers.json", "r") as f:
    chargers: list[dict[str, Any]] = json.load(f)

motos = [c for c in chargers if c["charger_type"] == "moto"]
taxis = [c for c in chargers if c["charger_type"] == "moto_taxi"]

print("=" * 90)
print("REPORTE: CARGA SIN CONTROL - MOTOS vs MOTOTAXIS")
print("=" * 90)
print()
print(f"INFRAESTRUCTURA:")
print(f"  Motos: {len(motos)} cargadores × 4 sockets = {len(motos)*4} sockets @ 2 kW")
print(f"  Taxis: {len(taxis)} cargadores × 4 sockets = {len(taxis)*4} sockets @ 3 kW")
print(f"  Total: {len(chargers)} cargadores, 128 sockets, 272 kW nominal")
print()

# Cargar perfiles horarios
df_hourly = pd.read_csv(DATA_DIR / "chargers_hourly_profiles.csv")
moto_cols = [c for c in df_hourly.columns if "MOTO_CH_" in c and "TAXI" not in c]
taxi_cols = [c for c in df_hourly.columns if "MOTO_TAXI_CH_" in c]

df_hourly["motos_kw"] = df_hourly[moto_cols].sum(axis=1)
df_hourly["taxis_kw"] = df_hourly[taxi_cols].sum(axis=1)
df_hourly["total_kw"] = df_hourly["motos_kw"] + df_hourly["taxis_kw"]

# Escalar a anual (365 días)
energy_motos_kwh: float = float(df_hourly["motos_kw"].sum()) * 365
energy_taxis_kwh: float = float(df_hourly["taxis_kw"].sum()) * 365
energy_total_kwh: float = float(df_hourly["total_kw"].sum()) * 365

pow_motos_avg: float = float(df_hourly["motos_kw"].mean())
pow_taxis_avg: float = float(df_hourly["taxis_kw"].mean())
pow_total_avg: float = float(df_hourly["total_kw"].mean())

pow_motos_peak: float = float(df_hourly["motos_kw"].max())
pow_taxis_peak: float = float(df_hourly["taxis_kw"].max())

hour_peak_motos: int = int(df_hourly.loc[df_hourly["motos_kw"].idxmax(), "hour"])  # type: ignore
hour_peak_taxis: int = int(df_hourly.loc[df_hourly["taxis_kw"].idxmax(), "hour"])  # type: ignore

util_motos: float = (pow_motos_avg / (len(motos) * 2.0)) * 100
util_taxis: float = (pow_taxis_avg / (len(taxis) * 3.0)) * 100

print("DEMANDA ANUAL (proyectada de perfil 24h):")
print()
print("Motos:")
print(f"  Energía: {energy_motos_kwh:,.0f} kWh/año")
print(f"  Potencia promedio: {pow_motos_avg:.2f} kW")
print(f"  Potencia pico: {pow_motos_peak:.2f} kW (hora {hour_peak_motos})")
print(f"  Utilización promedio: {util_motos:.1f}%")
print(f"  CO₂ baseline: {energy_motos_kwh * 0.4521 / 1000:.0f} t/año")
print()
print("Mototaxis:")
print(f"  Energía: {energy_taxis_kwh:,.0f} kWh/año")
print(f"  Potencia promedio: {pow_taxis_avg:.2f} kW")
print(f"  Potencia pico: {pow_taxis_peak:.2f} kW (hora {hour_peak_taxis})")
print(f"  Utilización promedio: {util_taxis:.1f}%")
print(f"  CO₂ baseline: {energy_taxis_kwh * 0.4521 / 1000:.0f} t/año")
print()
print("Total Sistema:")
print(f"  Energía: {energy_total_kwh:,.0f} kWh/año")
print(f"  Potencia promedio: {pow_total_avg:.2f} kW")
total_max: float = float(df_hourly["total_kw"].max())
print(f"  Potencia máxima: {total_max:.2f} kW")
print(f"  Utilización: {(pow_total_avg / 272) * 100:.1f}% de 272 kW")
print(f"  CO₂ baseline: {energy_total_kwh * 0.4521 / 1000:.0f} t/año (sin optimización)")
print()

# Hallazgos
print("=" * 90)
print("HALLAZGOS CLAVE:")
print("=" * 90)
print()
print("1. Diferenciación Motos vs Taxis:")
print(f"   - Motos: {(energy_motos_kwh / energy_total_kwh) * 100:.1f}% energía (7× más sockets pero demanda {energy_motos_kwh / energy_taxis_kwh:.1f}×)")
print(f"   - Taxis: {(energy_taxis_kwh / energy_total_kwh) * 100:.1f}% energía")
print()
print("2. Factor de Ocupación:")
print(f"   - Motos: {util_motos:.1f}% (BAJO - flexible para desplazar)")
print(f"   - Taxis: {util_taxis:.1f}% (ALTO - crítico, requiere respuesta rápida)")
print()
print("3. Implicaciones para Control RL:")
print(f"   - Garantizar taxis (necesario): {pow_taxis_peak:.1f} kW pico")
print(f"   - Flexibilidad en motos: {pow_motos_peak:.1f} kW (puede diferirse)")
print(f"   - BESS (4,520 kWh) puede servir {4520 / pow_total_avg:.1f}h @ demanda promedio")
print()

# Datos detallados por hora
print("=" * 90)
print("DEMANDA DETALLADA POR HORA:")
print("=" * 90)
print(f"{'Hora':>4} | {'Motos (kW)':>12} | {'Taxis (kW)':>12} | {'Total (kW)':>12} | {'% Sistema':>10}")
print("-" * 70)

for idx, row in df_hourly.iterrows():
    hour_val: int = int(row['hour'])
    motos_val: float = float(row['motos_kw'])
    taxis_val: float = float(row['taxis_kw'])
    total_val: float = float(row['total_kw'])
    pct_val: float = (total_val / 272.0) * 100.0
    print(f"{hour_val:02d}:00 | {motos_val:>12.2f} | {taxis_val:>12.2f} | {total_val:>12.2f} | {pct_val:>9.1f}%")

print()

# Guardar CSV
df_export = df_hourly[["hour", "motos_kw", "taxis_kw", "total_kw"]].copy()
df_export.to_csv(REPORTS_DIR / "demanda_horaria_motos_taxis.csv", index=False)
print(f"✓ Datos guardados: demanda_horaria_motos_taxis.csv")

# Guardar JSON con resumen
total_max_float: float = float(df_hourly["total_kw"].max())
motos_pct: float = (energy_motos_kwh / energy_total_kwh) * 100.0
taxis_pct: float = (energy_taxis_kwh / energy_total_kwh) * 100.0
sys_util: float = (pow_total_avg / 272.0) * 100.0

resumen: dict[str, Any] = {
    "titulo": "Análisis de Carga Sin Control - Baseline",
    "infraestructura": {
        "motos": {"chargers": len(motos), "sockets": len(motos)*4, "potencia_kw": float(len(motos)*2.0)},
        "taxis": {"chargers": len(taxis), "sockets": len(taxis)*4, "potencia_kw": float(len(taxis)*3.0)},
        "total": {"chargers": len(chargers), "sockets": 128, "potencia_kw": 272.0}
    },
    "energia_anual_kwh": {
        "motos": int(energy_motos_kwh),
        "taxis": int(energy_taxis_kwh),
        "total": int(energy_total_kwh)
    },
    "potencia_promedio_kw": {
        "motos": round(pow_motos_avg, 2),
        "taxis": round(pow_taxis_avg, 2),
        "total": round(pow_total_avg, 2)
    },
    "potencia_pico_kw": {
        "motos": {"valor": round(pow_motos_peak, 2), "hora": int(hour_peak_motos)},
        "taxis": {"valor": round(pow_taxis_peak, 2), "hora": int(hour_peak_taxis)},
        "total": round(total_max_float, 2)
    },
    "utilizacion_pct": {
        "motos": round(util_motos, 1),
        "taxis": round(util_taxis, 1),
        "sistema": round(sys_util, 1)
    },
    "co2_t_anual": {
        "motos": int(energy_motos_kwh * 0.4521 / 1000.0),
        "taxis": int(energy_taxis_kwh * 0.4521 / 1000.0),
        "total": int(energy_total_kwh * 0.4521 / 1000.0),
        "nota": "Factor: 0.4521 kg CO2/kWh (grid Iquitos - generación térmica)"
    }
}

with open(REPORTS_DIR / "resumen_carga_baseline.json", "w") as f:
    json.dump(resumen, f, indent=2)
print(f"✓ Resumen guardado: resumen_carga_baseline.json")

print()
print("✅ Análisis completado")
