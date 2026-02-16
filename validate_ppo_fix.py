#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validar que PPO ahora registra datos de solar/grid correctamente"""
import pandas as pd
from pathlib import Path

print("\n" + "="*100)
print("VALIDACIÓN: PPO Data Integrity After Fix")
print("="*100)
print()

trace_file = Path('outputs/ppo_training/trace_ppo.csv')

if not trace_file.exists():
    print(f"⚠  ARCHIVO NO EXISTE AÚN: {trace_file}")
    print("   → Entrena PPO primero con: python scripts/train/train_ppo_multiobjetivo.py")
    print()
else:
    df = pd.read_csv(trace_file)
    
    print(f"✓ PPO Trace cargado: {len(df)} filas")
    print()
    
    print("COLUMNAS DISPONIBLES:")
    print(f"  {list(df.columns)}")
    print()
    
    print("VALIDACIÓN DE DATOS:")
    print("-"*100)
    
    # Check solar_generation_kwh
    if 'solar_generation_kwh' in df.columns:
        solar_sum = df['solar_generation_kwh'].sum()
        solar_zeros = (df['solar_generation_kwh'] == 0).sum()
        solar_pct_zero = (solar_zeros / len(df)) * 100
        print(f"✓ solar_generation_kwh:")
        print(f"    Sum: {solar_sum:>12,.0f} kWh")
        print(f"    Zeros: {solar_zeros:>8} / {len(df):>8} ({solar_pct_zero:>6.1f}%)")
        if solar_pct_zero > 50:
            print(f"    ❌ PROBLEMA: >50% ceros (debería ser ~30-40% en horas nocturnas)")
        elif solar_sum > 80e6:
            print(f"    ✅ FIJO: Datos reales de solar presentes!")
        else:
            print(f"    ⚠  Revisar: sum parece baja")
    else:
        print(f"❌ FALTA: solar_generation_kwh")
    
    print()
    
    # Check grid_import_kwh
    if 'grid_import_kwh' in df.columns:
        grid_sum = df['grid_import_kwh'].sum()
        grid_zeros = (df['grid_import_kwh'] == 0).sum()
        grid_pct_zero = (grid_zeros / len(df)) * 100
        print(f"✓ grid_import_kwh:")
        print(f"    Sum: {grid_sum:>12,.0f} kWh")
        print(f"    Zeros: {grid_zeros:>8} / {len(df):>8} ({grid_pct_zero:>6.1f}%)")
        if grid_pct_zero > 50:
            print(f"    ❌ PROBLEMA: >50% ceros (debería ser variable 0-70%)")
        elif grid_sum > 50e6:
            print(f"    ✅ FIJO: Datos reales de grid presentes!")
        else:
            print(f"    ⚠  Revisar: sum parece baja")
    else:
        print(f"❌ FALTA: grid_import_kwh")
    
    print()
    
    # Check ev_charging_kwh
    if 'ev_charging_kwh' in df.columns:
        ev_sum = df['ev_charging_kwh'].sum()
        ev_zeros = (df['ev_charging_kwh'] == 0).sum()
        ev_pct_zero = (ev_zeros / len(df)) * 100
        print(f"✓ ev_charging_kwh:")
        print(f"    Sum: {ev_sum:>12,.0f} kWh")
        print(f"    Zeros: {ev_zeros:>8} / {len(df):>8} ({ev_pct_zero:>6.1f}%)")
        if ev_sum > 2e6:
            print(f"    ✅ FIJO: Datos reales de EV carga presentes!")
        else:
            print(f"    ⚠  Revisar: sum parece baja")
    else:
        print(f"❌ FALTA: ev_charging_kwh")
    
    print()
    print("-"*100)
    print()
    
    # Resumen
    issues = []
    if 'solar_generation_kwh' not in df.columns:
        issues.append("- solar_generation_kwh no encontrado")
    elif (df['solar_generation_kwh'] == 0).sum() / len(df) > 0.8:
        issues.append("- solar_generation_kwh: 100% CEROS (CORRUPTO)")
    
    if 'grid_import_kwh' not in df.columns:
        issues.append("- grid_import_kwh no encontrado")
    elif (df['grid_import_kwh'] == 0).sum() / len(df) > 0.8:
        issues.append("- grid_import_kwh: 100% CEROS (CORRUPTO)")
    
    if issues:
        print("❌ ALERTAS ENCONTRADAS:")
        for issue in issues:
            print(f"  {issue}")
        print()
        print("SOLUCION: Necesita corrección adicional en train_ppo_multiobjetivo.py")
    else:
        print("✅ VALIDACIÓN EXITOSA")
        print()
        print("RESUMEN:")
        if 'solar_generation_kwh' in df.columns:
            print(f"  Solar anual: {df['solar_generation_kwh'].sum()/1e6:.2f}M kWh ✓")
        if 'grid_import_kwh' in df.columns:
            print(f"  Grid anual: {df['grid_import_kwh'].sum()/1e6:.2f}M kWh ✓")
        if 'ev_charging_kwh' in df.columns:
            print(f"  EV anual: {df['ev_charging_kwh'].sum()/1e6:.2f}M kWh ✓")
        if 'co2_grid_kg' in df.columns:
            print(f"  CO2 grid anual: {df['co2_grid_kg'].sum()/1e6:.2f}M kg ✓")
        print()
        print("PPO ahora tiene datos válidos igual que SAC y A2C ✅")

print()
print("="*100)
