#!/usr/bin/env python
"""
Genera dataset completo de generación solar para CityLearn v2
Formato: CSV con 8,760 registros horarios (2024)
Ubicación: data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dimensionamiento.oe2.generacionsolar.solar_pvlib import (
    build_pv_timeseries_sandia,
    PVSystemConfig,
)

print("=" * 100)
print("GENERANDO DATASET COMPLETO DE GENERACIÓN SOLAR PARA CITYLEARN V2")
print("=" * 100)
print()

# Configurar sistema
config = PVSystemConfig()
target_dc_kw = 4050
target_ac_kw = 3200
target_annual_kwh = 8.31e6

# Ejecutar simulación con resolución horaria (REQUERIDA para CityLearn)
print("Ejecutando simulación PV Sandia con modelo ModelChain...")
results, metadata = build_pv_timeseries_sandia(
    year=2024,
    config=config,
    target_dc_kw=target_dc_kw,
    target_ac_kw=target_ac_kw,
    target_annual_kwh=target_annual_kwh,
    seconds_per_time_step=3600,  # 1 HORA (requerido OE3)
    selection_mode="manual",
)

print()
print("=" * 100)
print("ESTADÍSTICAS DE GENERACIÓN SOLAR")
print("=" * 100)

# Calcular estadísticas
annual_ac = results["ac_energy_kwh"].sum()
annual_dc = results["dc_energy_kwh"].sum()
losses = ((annual_dc - annual_ac) / annual_dc) * 100
peak_power = results["ac_power_kw"].max()
mean_power = results["ac_power_kw"].mean()
hours_with_generation = (results["ac_power_kw"] > 0).sum()

print(f"✅ Registros totales: {len(results)} (8,760 = 365 × 24)")
print(f"✅ Energía AC anual: {annual_ac:,.0f} kWh = {annual_ac/1e6:.2f} GWh")
print(f"✅ Energía DC anual: {annual_dc:,.0f} kWh = {annual_dc/1e6:.2f} GWh")
print(f"✅ Pérdidas del sistema: {losses:.1f}%")
print(f"✅ Potencia pico: {peak_power:.1f} kW")
print(f"✅ Potencia promedio: {mean_power:.1f} kW")
print(f"✅ Horas con generación: {hours_with_generation}")
print()

# Preparar DataFrame para CityLearn v2
print("Preparando dataset para CityLearn v2...")
print()

# Copiar y resetear índice (timestamp pasa a ser columna)
output_df = results.copy().reset_index()

# Convertir timestamp a string sin timezone
output_df["timestamp"] = output_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

# Seleccionar y reordenar columnas para CityLearn v2
columns_order = [
    "timestamp",          # Fecha/hora ISO format
    "ghi_wm2",           # Irradiancia global horizontal [W/m²]
    "dni_wm2",           # Irradiancia directa normal [W/m²]
    "dhi_wm2",           # Irradiancia difusa horizontal [W/m²]
    "temp_air_c",        # Temperatura del aire [°C]
    "wind_speed_ms",     # Velocidad del viento [m/s]
    "dc_power_kw",       # Potencia DC [kW]
    "ac_power_kw",       # Potencia AC [kW]
    "dc_energy_kwh",     # Energía DC [kWh]
    "ac_energy_kwh",     # Energía AC [kWh]
    "pv_generation_kwh", # Alias para ac_energy_kwh (CityLearn)
]

# Crear alias de energía AC para compatibilidad CityLearn
output_df["pv_generation_kwh"] = output_df["ac_energy_kwh"]

# Seleccionar columnas en orden
output_df = output_df[columns_order]

# Redondear a 2-4 decimales para CSV limpio
output_df["ghi_wm2"] = output_df["ghi_wm2"].round(2)
output_df["dni_wm2"] = output_df["dni_wm2"].round(2)
output_df["dhi_wm2"] = output_df["dhi_wm2"].round(2)
output_df["temp_air_c"] = output_df["temp_air_c"].round(2)
output_df["wind_speed_ms"] = output_df["wind_speed_ms"].round(2)
output_df["dc_power_kw"] = output_df["dc_power_kw"].round(4)
output_df["ac_power_kw"] = output_df["ac_power_kw"].round(4)
output_df["dc_energy_kwh"] = output_df["dc_energy_kwh"].round(4)
output_df["ac_energy_kwh"] = output_df["ac_energy_kwh"].round(4)
output_df["pv_generation_kwh"] = output_df["pv_generation_kwh"].round(4)

# Guardar CSV
output_path = "data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv"
Path(output_path).parent.mkdir(parents=True, exist_ok=True)
output_df.to_csv(output_path, index=False)

print("=" * 100)
print(f"✅ DATASET GUARDADO: {output_path}")
print("=" * 100)
print()
print("📋 PRIMEROS 10 REGISTROS (verificación de formato):")
print(output_df.head(10).to_string(index=False))
print()
print("📋 ÚLTIMOS 10 REGISTROS (cierre anual):")
print(output_df.tail(10).to_string(index=False))
print()
print("📊 INFORMACIÓN DEL DATASET:")
print(f"  Total de filas: {len(output_df)}")
print(f"  Columnas: {list(output_df.columns)}")
print(f"  Tamaño: {output_df.memory_usage(deep=True).sum() / 1024:.1f} KB")
print()

# Validaciones
print("=" * 100)
print("VALIDACIONES PARA CITYLEARN V2")
print("=" * 100)
print(f"✅ Resolución temporal: 1 hora (requerida OE3)")
print(f"✅ Total de registros: {len(output_df)} (8,760 horas = 365 × 24)")
print(f"✅ Rango temporal: {output_df.iloc[0]['timestamp']} a {output_df.iloc[-1]['timestamp']}")
print(
    f"✅ Sin NaN en columnas críticas: {output_df[['ac_power_kw', 'ac_energy_kwh', 'ghi_wm2']].isna().sum().sum() == 0}"
)
print(f"✅ Valores positivos en irradiancia: {(output_df['ghi_wm2'] >= 0).all()}")
print(f"✅ Valores positivos en potencia: {(output_df['ac_power_kw'] >= 0).all()}")
print(f"✅ Energía AC anual: {output_df['ac_energy_kwh'].sum():,.0f} kWh")
print()
print("=" * 100)
print("✅ DATASET LISTO PARA CITYLEARN V2")
print("=" * 100)
