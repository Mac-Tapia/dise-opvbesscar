"""
Regenerar dataset BESS con FASE 5 corregida (elif en lugar de if)
Esto garantiza exclusividad: solo FASE 4 O FASE 5, nunca ambas simultáneamente
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Agregar root al path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Usar el dataset existente como punto de partida
DATA_DIR = ROOT / 'data' / 'oe2' / 'bess'
CSV_FILE = DATA_DIR / 'bess_ano_2024.csv'

print("=" * 100)
print("REGENERAR DATASET BESS - CORRECCIÓN FASE 5 (elif)")
print("=" * 100)

# Cargar datos de entrada desde el dataset existente
print("\n🔄 Cargar datos existentes...")
df_old = pd.read_csv(CSV_FILE)

# Extraer datos de entrada del dataset antiguo
pv = df_old['pv_kwh'].values
ev = df_old['ev_kwh'].values
mall = df_old['mall_kwh'].values

print(f"✓ PV anual: {pv.sum():,.0f} kWh")
print(f"✓ EV anual: {ev.sum():,.0f} kWh")
print(f"✓ MALL anual: {mall.sum():,.0f} kWh")

# Importar la función corregida
print("\n📦 Importar función simulate_bess_ev_exclusive (con FASE 5 corregida)...")
from src.dimensionamiento.oe2.disenobess.bess import simulate_bess_ev_exclusive

# Ejecutar simulación con los datos reales
print("\n⚙️  Simular BESS 8,760 horas con fases corregidas...")
try:
    df_new, metrics = simulate_bess_ev_exclusive(
        pv_kwh=pv,
        ev_kwh=ev,
        mall_kwh=mall,
        capacity_kwh=2000.0,
        power_kw=400.0,
        efficiency=0.95,
        soc_min=0.20,
        soc_max=1.00
    )
    print(f"✓ Simulación completada: {len(df_new)} filas generadas")
except Exception as e:
    print(f"❌ ERROR en simulación: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Guardar dataset corregido
print("\n💾 Guardar dataset corregido...")
output_file = DATA_DIR / 'bess_ano_2024_CORREGIDO.csv'
df_new.to_csv(output_file, index=False)
print(f"✓ Guardado: {output_file}")

# VALIDACIÓN RÁPIDA: Verificar que NO hay carga y descarga simultánea
print("\n✅ VALIDACIÓN POST-CORRECCIÓN:")
print("─" * 100)

df_new['simultaneous'] = (df_new['bess_energy_stored_hourly_kwh'] > 0) & (df_new['bess_energy_delivered_hourly_kwh'] > 0)
simultaneous_count = df_new['simultaneous'].sum()

print(f"Filas con carga Y descarga simultánea: {simultaneous_count} / 8760")

if simultaneous_count == 0:
    print("✅ ¡ÉXITO! Exclusividad garantizada - NO hay carga/descarga simultánea")
    print("\nESTADÍSTICAS:")
    print(f"  BESS cargado (total año):     {df_new['bess_energy_stored_hourly_kwh'].sum():>12,.0f} kWh")
    print(f"  BESS descargado (total año):  {df_new['bess_energy_delivered_hourly_kwh'].sum():>12,.0f} kWh")
    print(f"  Grid importado (total año):   {df_new['grid_import_kwh'].sum():>12,.0f} kWh")
    print(f"  SOC min/max:                  {df_new['soc_percent'].min():.1f}% / {df_new['soc_percent'].max():.1f}%")
else:
    print(f"❌ FALLO: Aún hay {simultaneous_count} filas con conflicto")
    print("\nPrimeras 10 conflictos:")
    conflicts = df_new[df_new['simultaneous']].head(10)
    for idx, row in conflicts.iterrows():
        print(f"  {row['datetime']}: stored={row['bess_energy_stored_hourly_kwh']:.2f}, delivered={row['bess_energy_delivered_hourly_kwh']:.2f}")

print("\n" + "=" * 100)
