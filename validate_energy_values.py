#!/usr/bin/env python3
"""Valida y recalcula valores energéticos correctos basados en datos reales OE2 v5.2"""

import pandas as pd
from pathlib import Path

print('='*80)
print('VALIDACION DE VALORES ENERGETICOS - OE2 v5.2')
print('='*80)
print()

# ========== SOLAR ==========
print('[1] SOLAR PV (4,050 kWp):')
solar_paths = [
    Path('data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv'),
    Path('data/interim/oe2/solar/pv_generation_timeseries.csv'),
]

solar_annual_kwh = None
for p in solar_paths:
    if p.exists():
        try:
            df = pd.read_csv(p)
            # Buscar columna numérica
            for col in df.columns:
                if col.lower() not in ['date', 'time', 'timestamp', 'index']:
                    try:
                        total = pd.to_numeric(df[col], errors='coerce').sum()
                        if total > 8000000:  # Debería ser ~8.3M kWh/año
                            solar_annual_kwh = total
                            print(f'  ✓ Encontrado: {p.name}')
                            print(f'    Columna: {col}')
                            print(f'    Anual: {solar_annual_kwh:,.0f} kWh/año')
                            print(f'    Diario: {solar_annual_kwh/365:,.2f} kWh/día')
                            break
                    except:
                        pass
            if solar_annual_kwh:
                break
        except Exception as e:
            continue

if not solar_annual_kwh:
    print(f'  ❌ No encontrado')
    # Valor asumido
    solar_annual_kwh = 8292514
    print(f'    Usando valor estimado: {solar_annual_kwh:,.0f} kWh/año')

print()

# ========== CHARGERS (EV) ==========
print('[2] CHARGERS EV (38 sockets):')
chargers_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')

if chargers_path.exists():
    df = pd.read_csv(chargers_path)
    # Primera columna es timestamp, resto son demandas
    chargers_annual_kwh = 0
    n_sockets = 0
    
    for col in df.columns[1:]:
        try:
            col_sum = pd.to_numeric(df[col], errors='coerce').sum()
            chargers_annual_kwh += col_sum
            n_sockets += 1
        except:
            pass
    
    chargers_daily_avg = chargers_annual_kwh / 365
    
    print(f'  ✓ Encontrado: {chargers_path.name}')
    print(f'    Sockets: {n_sockets}')
    print(f'    Anual: {chargers_annual_kwh:,.0f} kWh/año')
    print(f'    Diario promedio: {chargers_daily_avg:,.2f} kWh/día')
    print(f'    Consumo por socket: {chargers_annual_kwh/n_sockets:,.0f} kWh/año')
else:
    print(f'  ❌ No encontrado')
    # Valor conocido
    chargers_annual_kwh = 565875
    chargers_daily_avg = chargers_annual_kwh / 365
    print(f'    Usando valor v5.2: {chargers_annual_kwh:,.0f} kWh/año')
    print(f'    Diario promedio: {chargers_daily_avg:,.2f} kWh/día')

print()

# ========== MALL ==========
print('[3] MALL DEMAND:')
mall_paths = [
    ('data/oe2/demandamallkwh/demandamallhorakwh.csv', ';'),
    ('data/interim/oe2/demandamallkwh/demandamallhorakwh.csv', ';'),
    ('data/processed/citylearn/iquitos_ev_mall/demandamallkwh/demandamallhorakwh.csv', ','),
]

mall_annual_kwh = None
for path_str, sep in mall_paths:
    p = Path(path_str)
    if p.exists():
        try:
            df = pd.read_csv(p, sep=sep)
            # Buscar columna de demanda
            for col in df.columns:
                if col.lower() not in ['time', 'date', 'timestamp', 'index']:
                    try:
                        # Intentar conve rtir - algunos datos pueden tener formato
                        if isinstance(df[col].iloc[0], str) and ':' in str(df[col].iloc[0]):
                            continue  # Skip time columns
                        total = pd.to_numeric(df[col], errors='coerce').sum()
                        if total > 1000000:  # Debería ser ~37M kWh/año
                            mall_annual_kwh = total
                            print(f'  ✓ Encontrado: {p.name}')
                            print(f'    Columna: {col}')
                            print(f'    Anual: {mall_annual_kwh:,.0f} kWh/año')
                            print(f'    Diario: {mall_annual_kwh/365:,.2f} kWh/día')
                            break
                    except:
                        pass
            if mall_annual_kwh:
                break
        except Exception as e:
            continue

if not mall_annual_kwh:
    print(f'  ? No encontrado en archivos esperados')
    print(f'    Buscando en bess_results.json...')
    try:
        import json
        bess_json = Path('data/processed/citylearn/iquitos_ev_mall/bess_results.json')
        if bess_json.exists():
            with open(bess_json) as f:
                data = json.load(f)
                mall_daily = data.get('mall_demand_kwh_day', 0)
                mall_annual_kwh = mall_daily * 365
                print(f'    ⚠️  Valor de bess_results.json:')
                print(f'      Diario (archivo): {mall_daily:,.2f} kWh/día')
                print(f'      Anual (extrapolado): {mall_annual_kwh:,.0f} kWh/año')
    except:
        pass

if not mall_annual_kwh:
    # Asumiendo demand de 100kW promedio
    mall_annual_kwh = 100 * 24 * 365
    mall_daily_avg = mall_annual_kwh / 365
    print(f'    Usando estimado (100 kW promedio): {mall_annual_kwh:,.0f} kWh/año')
    print(f'    Diario: {mall_daily_avg:,.2f} kWh/día')
else:
    mall_daily_avg = mall_annual_kwh / 365

print()
print('[4] RESUMEN DE VALORES CORRECTOS:')
print()

total_annual = chargers_annual_kwh + mall_annual_kwh
total_daily = total_annual / 365

print(f'ANUAL (kWh/año):')
print(f'  Solar:      {solar_annual_kwh:>15,.0f}')
print(f'  Chargers:   {chargers_annual_kwh:>15,.0f}')
print(f'  Mall:       {mall_annual_kwh:>15,.0f}')
print(f'  -----------')
print(f'  Total:      {total_annual:>15,.0f}')
print()

print(f'DIARIO PROMEDIO (kWh/día):')
print(f'  Solar:      {solar_annual_kwh/365:>15,.2f}')
print(f'  Chargers:   {chargers_daily_avg:>15,.2f}')
print(f'  Mall:       {mall_daily_avg:>15,.2f}')
print(f'  -----------')
print(f'  Total:      {total_daily:>15,.2f}')
print()

print('[5] COMPARACION CON bess_results.json (ACTUAL):')
print()
print(f'❌ ACTUAL:')
print(f'  Solar:      22,719.22 kWh/día  (parece OK)')
print(f'  Chargers:   1,129.41 kWh/día   ← Error: debería ser {chargers_daily_avg:,.2f}')
print(f'  Mall:       33,886.72 kWh/día  ← Verificar contra datos reales')
print(f'  Total:      35,016.13 kWh/día')
print()

print(f'✅ DEBERIA SER:')
print(f'  Solar:      {solar_annual_kwh/365:,.2f} kWh/día')
print(f'  Chargers:   {chargers_daily_avg:,.2f} kWh/día')
print(f'  Mall:       {mall_daily_avg:,.2f} kWh/día')
print(f'  Total:      {total_daily:,.2f} kWh/día')
print()

print('='*80)
