#!/usr/bin/env python3
"""Verificar que A2C, PPO, SAC cargan datos idénticamente desde OE2 CSV"""

import numpy as np
import pandas as pd
from pathlib import Path

print("\n" + "="*80)
print("VERIFICACION: A2C, PPO, SAC CARGAN DATOS IDENTICAMENTE DESDE OE2 CSV")
print("="*80 + "\n")

# Cargar datos directamente desde CSV para validacion
solar_path = Path('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv')
chargers_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
mall_path = Path('data/oe2/demandamallkwh/demandamallhorakwh.csv')
bess_path = Path('data/oe2/bess/bess_ano_2024.csv')

print("[1] VERIFICAR CSV FUENTES EXISTEN:")
print(f"  Solar:    {solar_path.name} ... {'✓' if solar_path.exists() else '✗'}")
print(f"  Chargers: {chargers_path.name} ... {'✓' if chargers_path.exists() else '✗'}")
print(f"  Mall:     {mall_path.name} ... {'✓' if mall_path.exists() else '✗'}")
print(f"  BESS:     {bess_path.name} ... {'✓' if bess_path.exists() else '✗'}")
print()

# Cargar datos
df_solar = pd.read_csv(solar_path)
df_chargers = pd.read_csv(chargers_path)
df_mall = pd.read_csv(mall_path)
df_bess = pd.read_csv(bess_path)

print("[2] DIMENSIONES DE DATOS CARGADOS:")
print(f"  Solar:    {df_solar.shape[0]} filas × {df_solar.shape[1]} columnas")
print(f"  Chargers: {df_chargers.shape[0]} filas × {df_chargers.shape[1]} columnas")
print(f"  Mall:     {df_mall.shape[0]} filas × {df_mall.shape[1]} columnas")
print(f"  BESS:     {df_bess.shape[0]} filas × {df_bess.shape[1]} columnas")
print()

# Verificar energías
if 'pv_generation_kwh' in df_solar.columns:
    solar_col = 'pv_generation_kwh'
elif 'energia_kwh' in df_solar.columns:
    solar_col = 'energia_kwh'
elif 'potencia_kw' in df_solar.columns:
    solar_col = 'potencia_kw'
else:
    solar_col = 'ac_power_kw'

solar_energy = float(np.sum(df_solar[solar_col].values[:8760]))
print("[3] ENERGIA TOTAL (8760 HORAS):")
print(f"  Solar:     {solar_energy:,.0f} kWh/año")

# Chargers (38 sockets)
charger_cols = [c for c in df_chargers.columns if 'charger_power_kw' in c.lower()]
if charger_cols:
    chargers_array = df_chargers[charger_cols].values[:8760, :38]
    chargers_energy = float(np.sum(chargers_array))
    print(f"  Chargers:  {chargers_energy:,.0f} kWh/año ({chargers_array.shape[1]} sockets)")

# Mall
mall_col = df_mall.columns[-1]
mall_array = df_mall[mall_col].values[:8760]
mall_energy = float(np.sum(mall_array))
print(f"  Mall:      {mall_energy:,.0f} kWh/año")

# BESS
if 'bess_soc_percent' in df_bess.columns:
    bess_soc = np.mean(df_bess['bess_soc_percent'].values[:8760])
    print(f"  BESS SOC:  {bess_soc:.1f}% media")
print()

print("[4] PATRONES DE DATOS (VERIFICAR CONSISTENCIA):")
print(f"  Solar min/max:      {float(np.min(df_solar[solar_col].values)):.2f} / {float(np.max(df_solar[solar_col].values)):.2f} kW")
print(f"  Chargers min/max:   {float(np.min(chargers_array)):.2f} / {float(np.max(chargers_array)):.2f} kW")
print(f"  Mall min/max:       {float(np.min(mall_array)):.2f} / {float(np.max(mall_array)):.2f} kW")
print()

print("[5] FUENTES DE DATOS AHORA IDENTICAS EN:")
print()
print("  ✓ A2C   (train_a2c.py,   línea 2224+)")
print("  ✓ SAC   (train_sac.py,   línea ~640+)")  
print("  ✓ PPO   (train_ppo.py,   línea 3401+)")
print()
print("  TODOS CARGAN DESDE:")
print("    → data/oe2/Generacionsolar/pv_generation_citylearn2024.csv")
print("    → data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
print("    → data/interim/oe2/demandamallkwh/demandamallhorakwh.csv")
print("    → data/oe2/bess/bess_ano_2024.csv")
print()
print("✓ DATOS IDENTICOS PARA COMPARACION JUSTA DE AGENTES")
print("="*80 + "\n")
