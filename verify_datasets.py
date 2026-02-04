#!/usr/bin/env python3
"""Verificar que datasets de BESS y mall demand están cargados correctamente."""

import sys
import json
from pathlib import Path

sys.path.insert(0, 'src')

from iquitos_citylearn.config import load_config, load_paths

cfg = load_config(None)
paths = load_paths(cfg)

print("[DATASET VALIDATION]", flush=True)
print("=" * 70)

# [1] BESS
bess_path = paths.interim_dir / 'oe2' / 'bess' / 'bess_results.json'
print(f"\n[1] BESS Results: {bess_path.exists()}")
if bess_path.exists():
    try:
        b = json.loads(bess_path.read_text())
        cap = b.get('capacity_kwh') or b.get('fixed_capacity_kwh')
        pow = b.get('nominal_power_kw') or b.get('power_rating_kw')
        print(f"    [OK] Capacity: {cap} kWh")
        print(f"    [OK] Power: {pow} kW")
    except Exception as e:
        print(f"    [ERROR] {e}")
else:
    print(f"    [NOT FOUND] {bess_path}")

# [2] Mall demand (hourly)
mall_path = paths.interim_dir / 'oe2' / 'demandamallkwh' / 'demanda_mall_horaria_anual.csv'
print(f"\n[2] Mall Demand (Hourly): {mall_path.exists()}")
if mall_path.exists():
    try:
        import pandas as pd
        # Try with comma separator
        df = pd.read_csv(mall_path, sep=',', decimal='.')
        print(f"    [OK] Rows: {len(df)}")
        print(f"    [OK] Columns: {df.columns.tolist()}")
        kwh_col = [c for c in df.columns if 'kwh' in c.lower()][0]
        total = pd.to_numeric(df[kwh_col], errors='coerce').sum()
        print(f"    [OK] Total kWh: {total:,.0f}")
    except Exception as e:
        print(f"    [ERROR] {str(e)[:100]}")
else:
    print(f"    [NOT FOUND] {mall_path}")

# [3] Mall demand (15-min)
mall_path_15min = paths.interim_dir / 'oe2' / 'demandamall' / 'demanda_mall_kwh.csv'
print(f"\n[3] Mall Demand (15-min): {mall_path_15min.exists()}")
if mall_path_15min.exists():
    try:
        import pandas as pd
        df = pd.read_csv(mall_path_15min, sep=';', decimal='.')
        print(f"    [OK] Rows: {len(df)} (15-minute data)")
        print(f"    [OK] Columns: {df.columns.tolist()}")
        kwh_col = [c for c in df.columns if 'kwh' in c.lower()][0]
        total = pd.to_numeric(df[kwh_col], errors='coerce').sum()
        print(f"    [OK] Total kWh: {total:,.0f}")
    except Exception as e:
        print(f"    [ERROR] {str(e)[:100]}")
else:
    print(f"    [NOT FOUND] {mall_path_15min}")

# [4] Solar
solar_path = paths.interim_dir / 'oe2' / 'solar' / 'pv_generation_timeseries.csv'
print(f"\n[4] Solar Generation: {solar_path.exists()}")
if solar_path.exists():
    try:
        import pandas as pd
        df = pd.read_csv(solar_path)
        print(f"    [OK] Rows: {len(df)} (hourly)")
        print(f"    [OK] Columns: {df.columns.tolist()}")
        # Find generation column
        for col in df.columns:
            if 'kw' in col.lower() or 'kwh' in col.lower():
                total = pd.to_numeric(df[col], errors='coerce').sum()
                print(f"    [OK] Total {col}: {total:,.0f}")
                break
    except Exception as e:
        print(f"    [ERROR] {str(e)[:100]}")
else:
    print(f"    [NOT FOUND] {solar_path}")

# [5] Chargers
chargers_path = paths.interim_dir / 'oe2' / 'chargers' / 'individual_chargers.json'
print(f"\n[5] Individual Chargers: {chargers_path.exists()}")
if chargers_path.exists():
    try:
        c = json.loads(chargers_path.read_text())
        motos = [ch for ch in c if 'moto' in ch.get('charger_type', '').lower() and 'taxi' not in ch.get('charger_type', '').lower()]
        taxis = [ch for ch in c if 'taxi' in ch.get('charger_type', '').lower()]
        print(f"    [OK] Total: {len(c)} chargers")
        print(f"    [OK] Motos: {len(motos)} chargers (Playa_Motos)")
        print(f"    [OK] Mototaxis: {len(taxis)} chargers (Playa_Mototaxis)")
        print(f"    [OK] Total sockets: {len(c) * 4} ({len(c)} chargers x 4 sockets each)")
    except Exception as e:
        print(f"    [ERROR] {str(e)[:100]}")
else:
    print(f"    [NOT FOUND] {chargers_path}")

print("\n" + "=" * 70)
print("[OK] Verification complete\n", flush=True)
