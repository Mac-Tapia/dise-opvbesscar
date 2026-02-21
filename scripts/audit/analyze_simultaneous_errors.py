"""
ANÁLISIS PROFUNDO DE ERRORES BESS
Investigar por qué ocurren cargas y descargas simultáneas
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
CSV_FILE = ROOT / 'data' / 'oe2' / 'bess' / 'bess_ano_2024.csv'

print("=" * 100)
print("ANÁLISIS DETALLADO DE ERRORES SIMULTÁNEOS")
print("=" * 100)

df = pd.read_csv(CSV_FILE)
df['datetime'] = pd.to_datetime(df['datetime'])
df['hour'] = df['datetime'].dt.hour

# ENCONTRAR HORAS CON CARGA Y DESCARGA SIMULTÁNEAS
df['has_simultaneous'] = (df['bess_energy_stored_hourly_kwh'] > 0) & (df['bess_energy_delivered_hourly_kwh'] > 0)
simultaneous_rows = df[df['has_simultaneous']]

print(f"\n📊 ESTADÍSTICAS DE CARGA/DESCARGA SIMULTÁNEAS:")
print(f"Total filas con error: {len(simultaneous_rows)} / 8760 ({len(simultaneous_rows)/8760*100:.1f}%)")

if len(simultaneous_rows) > 0:
    print(f"\n🔍 ANÁLISIS DE PRIMERAS 20 FILAS CON ERROR:")
    print("─" * 140)
    print(f"{'DateTime':<25} {'Hour':<6} {'PV':<8} {'EV':<8} {'MALL':<8} {'BESS Stored':<12} {'BESS Del':<12} {'SOC%':<7} {'bess_mode':<12}")
    print("─" * 140)
    
    for idx, row in simultaneous_rows.head(20).iterrows():
        print(f"{str(row['datetime']):<25} {row['hour']:<6.0f} {row['pv_kwh']:<8.1f} "
              f"{row['ev_kwh']:<8.1f} {row['mall_kwh']:<8.1f} {row['bess_energy_stored_hourly_kwh']:<12.2f} "
              f"{row['bess_energy_delivered_hourly_kwh']:<12.2f} {row['soc_percent']:<7.1f} {row['bess_mode']:<12}")

# ANALIZAR POR FASE
print(f"\n📈 DISTRIBUCIÓN DE ERRORES POR HORA DEL DÍA:")
print("─" * 100)

errors_per_hour = simultaneous_rows.groupby('hour').size()
for h in range(24):
    count = errors_per_hour.get(h, 0)
    pct = count / (8760/24) * 100 if count > 0 else 0
    bar = "█" * int(pct / 2)
    print(f"Hora {h:2d}: {count:4d} errores ({pct:5.1f}%) {bar}")

# ANALIZAR COLUMNAS DERIVADAS SOSPECHOSAS
print(f"\n🔍 VERIFICAR LÓGICA DE COLUMNAS DERIVADAS:")
print("─" * 100)

print("\nPrimera fila con error (Fila 37):")
error_row = df.iloc[37]
print(f"datetime:                      {error_row['datetime']}")
print(f"pv_kwh:                        {error_row['pv_kwh']:.2f}")
print(f"ev_kwh:                        {error_row['ev_kwh']:.2f}")
print(f"mall_kwh:                      {error_row['mall_kwh']:.2f}")
print(f"load_kwh (ev+mall):            {error_row['load_kwh']:.2f}")
print(f"")
print(f"pv_to_ev_kwh:                  {error_row['pv_to_ev_kwh']:.2f}")
print(f"pv_to_bess_kwh:                {error_row['pv_to_bess_kwh']:.2f}")
print(f"pv_to_mall_kwh:                {error_row['pv_to_mall_kwh']:.2f}")
print(f"grid_export_kwh:               {error_row['grid_export_kwh']:.2f}")
print(f"PV distribución (debería sumar a PV total):")
pv_dist = error_row['pv_to_ev_kwh'] + error_row['pv_to_bess_kwh'] + error_row['pv_to_mall_kwh'] + error_row['grid_export_kwh']
print(f"  pv_to_ev + pv_to_bess + pv_to_mall + grid_export = {pv_dist:.2f} (esperado: {error_row['pv_kwh']:.2f})")
print(f"")
print(f"bess_to_ev_kwh:                {error_row['bess_to_ev_kwh']:.2f}")
print(f"bess_to_mall_kwh:              {error_row['bess_to_mall_kwh']:.2f}")
print(f"bess_energy_stored_hourly:     {error_row['bess_energy_stored_hourly_kwh']:.2f}")
print(f"bess_energy_delivered_hourly:  {error_row['bess_energy_delivered_hourly_kwh']:.2f}")
print(f"")
print(f"grid_import_ev_kwh:            {error_row['grid_import_ev_kwh']:.2f}")
print(f"grid_import_mall_kwh:          {error_row['grid_import_mall_kwh']:.2f}")
print(f"grid_import_kwh:               {error_row['grid_import_kwh']:.2f}")
print(f"soc_percent:                   {error_row['soc_percent']:.2f}%")
print(f"bess_mode:                     {error_row['bess_mode']}")

# BUSCAR PATRÓN: ¿Las columnas STORED y DELIVERED son incorrectas?
print(f"\n🤔 HIPÓTESIS: ¿Columnas bess_energy_* están intercambiadas o mal calculadas?")
print("─" * 100)

# Comparar con bess_to_ev y bess_to_mall que son los flujos reales
print(f"\nSuma de bess_to_ev + bess_to_mall debería = bess_energy_delivered:")
df['bess_delivered_from_flows'] = df['bess_to_ev_kwh'] + df['bess_to_mall_kwh']
mismatch_delivered = abs(df['bess_delivered_from_flows'] - df['bess_energy_delivered_hourly_kwh']) > 0.01
print(f"Filas donde NO coinciden: {mismatch_delivered.sum()} / {len(df)}")

if mismatch_delivered.sum() > 0:
    print(f"\nPrimeras 5 filas con mismatch:")
    for idx, row in df[mismatch_delivered].head(5).iterrows():
        print(f"  {row['datetime']}: delivered_flows={row['bess_delivered_from_flows']:.2f}, "
              f"energy_delivered={row['bess_energy_delivered_hourly_kwh']:.2f}")

# RASTREAR EL SOC
print(f"\n📊 ANÁLISIS DE EVOLUCIÓN SOC - PRIMERAS 24 HORAS:")
print("─" * 100)
day1 = df[df['datetime'].dt.day == 1]
print(f"{'Hour':<6} {'SOC%':<8} {'Stored':<10} {'Delivered':<10} {'SOC Change Expected':<20} {'SOC Change Actual':<20}")
print("─" * 100)

for i, (idx, row) in enumerate(day1.iterrows()):
    if i == 0:
        prev_soc = 80.0
    else:
        prev_row = day1.iloc[i-1]
        prev_soc = prev_row['soc_percent']
    
    stored = row['bess_energy_stored_hourly_kwh']
    delivered = row['bess_energy_delivered_hourly_kwh']
    soc_expected_change = (stored - delivered) / 2000 * 100  # 2000 kWh capacity
    actual_soc_change = row['soc_percent'] - prev_soc
    
    print(f"{row['hour']:<6.0f} {row['soc_percent']:<8.1f} {stored:<10.2f} {delivered:<10.2f} "
          f"{soc_expected_change:<20.4f} {actual_soc_change:<20.4f}")

print("\n" + "=" * 100)
print("⚠️  CONCLUSIÓN PRELIMINAR: Revisar función simulate_bess_ev_exclusive en bess.py")
print("   Los problemas sugieren que la lógica de fases no está validando:")
print("   - Exclusividad: BESS no puede cargar Y descargar en la misma hora")
print("   - Consistencia SOC: Los cambios de energía no coinciden con evolución SOC")
print("=" * 100)
