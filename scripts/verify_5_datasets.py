#!/usr/bin/env python
"""Verificar 5 datasets OE2 reales - Ambas ubicaciones."""
from __future__ import annotations
import json
import pandas as pd

def main():
    print("="*80)
    print("VERIFICACION DE 5 DATASETS OE2 (data/oe2 y data/interim/oe2)")
    print("="*80)
    
    # 1. SOLAR
    try:
        # Ubicación usada en training: data/oe2/
        df = pd.read_csv('data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv')
        ok = "PASS" if len(df) == 8760 else "FAIL"
        print(f"\n1. SOLAR: {len(df)} rows [{ok}]")
        print(f"   Path: data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv")
        print(f"   Columns: {list(df.columns)}")
        # Verificar columna clave
        if 'pv_generation_kwh' in df.columns:
            print(f"   pv_generation_kwh: {float(df['pv_generation_kwh'].sum()):.0f} kWh/año")
    except Exception as e:
        print(f"1. SOLAR: ERROR - {e}")
    
    # 2. CHARGERS CSV
    try:
        df = pd.read_csv('data/oe2/chargers/chargers_real_hourly_2024.csv')
        ok = "PASS" if len(df) == 8760 else "FAIL"
        print(f"\n2. CHARGERS CSV: {len(df)} rows x {len(df.columns)} cols [{ok}]")
        print(f"   Path: data/oe2/chargers/chargers_real_hourly_2024.csv")
        print(f"   First 3: {list(df.columns[:3])}")
        print(f"   Last 3: {list(df.columns[-3:])}")
    except Exception as e:
        print(f"2. CHARGERS CSV: ERROR - {e}")
    
    # 3. BESS (verificar columnas completas)
    try:
        df = pd.read_csv('data/oe2/bess/bess_hourly_dataset_2024.csv')
        ok = "PASS" if len(df) == 8760 else "FAIL"
        print(f"\n3. BESS: {len(df)} rows [{ok}]")
        print(f"   Path: data/oe2/bess/bess_hourly_dataset_2024.csv")
        print(f"   Columns ({len(df.columns)}): {list(df.columns)}")
        # Verificar columnas de flujo
        flow_cols = ['pv_to_ev_kwh', 'grid_to_ev_kwh', 'bess_charge_kwh', 'bess_discharge_kwh', 'soc_percent']
        missing = [c for c in flow_cols if c not in df.columns]
        if missing:
            print(f"   MISSING COLUMNS: {missing}")
        else:
            print(f"   All flow columns present: {flow_cols}")
    except Exception as e:
        print(f"3. BESS: ERROR - {e}")
    
    # 4. MALL
    try:
        df = pd.read_csv('data/oe2/demandamallkwh/demandamallhorakwh.csv', sep=';')
        ok = "PASS" if len(df) >= 8760 else "FAIL"
        print(f"\n4. MALL: {len(df)} rows [{ok}]")
        print(f"   Path: data/oe2/demandamallkwh/demandamallhorakwh.csv")
        print(f"   Columns: {list(df.columns)}")
        # Verificar demanda
        demand_col = df.columns[-1]
        print(f"   {demand_col}: {float(df[demand_col].sum()):.0f} kWh/año")
    except Exception as e:
        print(f"4. MALL: ERROR - {e}")
    
    # 5. CHARGERS JSON (en data/interim/oe2)
    try:
        with open('data/interim/oe2/chargers/individual_chargers.json', 'r', encoding='utf-8') as f:
            chargers = json.load(f)
        total_sockets = sum(c.get('n_sockets', 4) for c in chargers)
        ok = "PASS" if len(chargers) == 32 and total_sockets == 128 else "FAIL"
        print(f"\n5. CHARGERS JSON: {len(chargers)} chargers, {total_sockets} sockets [{ok}]")
        print(f"   Path: data/interim/oe2/chargers/individual_chargers.json")
    except Exception as e:
        print(f"5. CHARGERS JSON: ERROR - {e}")
    
    print("\n" + "="*80)
    print("RESUMEN: Archivos de entrenamiento usan rutas en data/oe2/")
    print("="*80)

if __name__ == "__main__":
    main()
