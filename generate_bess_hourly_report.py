"""
Genera reporte horario detallado de BESS con energía en kWh
"""
import pandas as pd
import numpy as np
from pathlib import Path

# Capacidad del BESS
BESS_CAPACITY_KWH = 1700.0

# Cargar datos
csv_path = Path('data/oe2/bess/bess_simulation_hourly.csv')
df = pd.read_csv(csv_path)

# Agregar columna SOC en kWh
df['bess_soc_kwh'] = (df['bess_soc_percent'] / 100.0) * BESS_CAPACITY_KWH

# Agregar columna de hora del día
df['datetime'] = pd.to_datetime(df['datetime'])
df['hour'] = df['datetime'].dt.hour
df['day'] = df['datetime'].dt.day

print('╔' + '═' * 118 + '╗')
print('║' + ' ' * 35 + 'REPORTE HORARIO BESS v5.4 - ENERGÍA EN kWh' + ' ' * 40 + '║')
print('╚' + '═' * 118 + '╝')
print()

# REPORTE DETALLADO DE 24 HORAS (DÍA 1)
print('┌' + '─' * 118 + '┐')
print('│ DÍA 1 (2024-01-01): FLUJOS DE ENERGÍA HORARIOS (kWh)' + ' ' * 63 + '│')
print('├' + '─' * 118 + '┤')
print('│ Hora │ PV Gen │ EV Dem │ Mall Dem │ PV→EV │ PV→BESS │ BESS↑ │ BESS↓ │ BESS→EV │ BESS→Mall │ SOC(%) │ SOC(kWh) │ Modo     │')
print('├' + '─' * 118 + '┤')

for idx, row in df[df['day'] == 1].head(24).iterrows():
    h = int(row['hour'])
    pv_gen = row['pv_generation_kwh']
    ev_dem = row['ev_demand_kwh']
    mall_dem = row['mall_demand_kwh']
    pv_ev = row['pv_to_ev_kwh']
    pv_bess = row['pv_to_bess_kwh']
    bess_ch = row['bess_charge_kwh']
    bess_dch = row['bess_discharge_kwh']
    bess_ev = row['bess_to_ev_kwh']
    bess_mall = row['bess_to_mall_kwh']
    soc_pct = row['bess_soc_percent']
    soc_kwh = row['bess_soc_kwh']
    modo = row['bess_mode']
    
    print(f'│ {h:2d}:00 │ {pv_gen:6.0f} │ {ev_dem:6.1f} │ {mall_dem:8.0f} │ {pv_ev:5.1f} │ {pv_bess:7.1f} │ {bess_ch:5.0f} │ {bess_dch:5.0f} │ {bess_ev:7.1f} │ {bess_mall:9.1f} │ {soc_pct:6.1f}% │ {soc_kwh:8.0f}  │ {modo:8} │')

print('└' + '─' * 118 + '┘')
print()

# RESUMEN DIARIO
print('┌' + '─' * 118 + '┐')
print('│ RESUMEN DIARIO - DÍA 1 (2024-01-01)' + ' ' * 81 + '│')
print('├' + '─' * 118 + '┤')

day1 = df[df['day'] == 1]
pv_gen_day = day1['pv_generation_kwh'].sum()
ev_dem_day = day1['ev_demand_kwh'].sum()
mall_dem_day = day1['mall_demand_kwh'].sum()
pv_to_ev_day = day1['pv_to_ev_kwh'].sum()
pv_to_bess_day = day1['pv_to_bess_kwh'].sum()
pv_to_mall_day = day1['pv_to_mall_kwh'].sum()
bess_charge_day = day1['bess_charge_kwh'].sum()
bess_discharge_day = day1['bess_discharge_kwh'].sum()
bess_to_ev_day = day1['bess_to_ev_kwh'].sum()
bess_to_mall_day = day1['bess_to_mall_kwh'].sum()
soc_inicio = day1.iloc[0]['bess_soc_kwh']
soc_final = day1.iloc[23]['bess_soc_kwh']

print('│ GENERACIÓN SOLAR' + ' ' * 102 + '│')
print(f'│   Total PV generado: {pv_gen_day:10,.1f} kWh' + ' ' * 87 + '│')
print('│ ' + ' ' * 116 + '│')
print('│ DEMANDA CARGAS' + ' ' * 103 + '│')
print(f'│   Total EV demand:   {ev_dem_day:10,.1f} kWh' + ' ' * 87 + '│')
print(f'│   Total Mall demand: {mall_dem_day:10,.1f} kWh' + ' ' * 87 + '│')
print('│ ' + ' ' * 116 + '│')
print('│ DISTRIBUCIÓN PV' + ' ' * 102 + '│')
print(f'│   PV → EV directo:   {pv_to_ev_day:10,.1f} kWh  ({100*pv_to_ev_day/ev_dem_day if ev_dem_day > 0 else 0:5.1f}% de EV)' + ' ' * 64 + '│')
print(f'│   PV → BESS:         {pv_to_bess_day:10,.1f} kWh  ({100*pv_to_bess_day/pv_gen_day if pv_gen_day > 0 else 0:5.1f}% de PV)' + ' ' * 64 + '│')
print(f'│   PV → MALL directo: {pv_to_mall_day:10,.1f} kWh  ({100*pv_to_mall_day/mall_dem_day if mall_dem_day > 0 else 0:5.1f}% de Mall)' + ' ' * 64 + '│')
print('│ ' + ' ' * 116 + '│')
print('│ OPERACIÓN BESS' + ' ' * 103 + '│')
print(f'│   Total CARGADO:     {bess_charge_day:10,.1f} kWh' + ' ' * 87 + '│')
print(f'│   Total DESCARGADO:  {bess_discharge_day:10,.1f} kWh' + ' ' * 87 + '│')
print(f'│   Ratio carga/carga: {bess_discharge_day/bess_charge_day if bess_charge_day > 0 else 0:6.2f} (eficiencia ≈ 95%)' + ' ' * 68 + '│')
print('│ ' + ' ' * 116 + '│')
print('│ DISTRIBUCIÓN BESS' + ' ' * 100 + '│')
print(f'│   BESS → EV:         {bess_to_ev_day:10,.1f} kWh  ({100*bess_to_ev_day/ev_dem_day if ev_dem_day > 0 else 0:5.1f}% de EV)' + ' ' * 64 + '│')
print(f'│   BESS → MALL:       {bess_to_mall_day:10,.1f} kWh  ({100*bess_to_mall_day/mall_dem_day if mall_dem_day > 0 else 0:5.1f}% de Mall)' + ' ' * 64 + '│')
print('│ ' + ' ' * 116 + '│')
print('│ ESTADO ENERGÉTICO BESS' + ' ' * 94 + '│')
print(f'│   SOC inicio del día: {soc_inicio:10,.0f} kWh  ({100*soc_inicio/BESS_CAPACITY_KWH:5.1f}%)' + ' ' * 78 + '│')
print(f'│   SOC final del día:  {soc_final:10,.0f} kWh  ({100*soc_final/BESS_CAPACITY_KWH:5.1f}%)' + ' ' * 78 + '│')
print(f'│   Variación SOC:      {soc_final - soc_inicio:10,.0f} kWh  ({100*(soc_final - soc_inicio)/BESS_CAPACITY_KWH:5.1f}%)' + ' ' * 78 + '│')
print('│ ' + ' ' * 116 + '│')
print('│ COBERTURA ENERGÉTICA' + ' ' * 96 + '│')
ev_coverage = (pv_to_ev_day + bess_to_ev_day) / ev_dem_day * 100 if ev_dem_day > 0 else 0
mall_coverage = (pv_to_mall_day + bess_to_mall_day) / mall_dem_day * 100 if mall_dem_day > 0 else 0
print(f'│   EV cubierto:        {pv_to_ev_day + bess_to_ev_day:10,.1f} / {ev_dem_day:10,.1f} kWh  ({ev_coverage:5.1f}%)' + ' ' * 69 + '│')
print(f'│   MALL cubierto:      {pv_to_mall_day + bess_to_mall_day:10,.1f} / {mall_dem_day:10,.1f} kWh  ({mall_coverage:5.1f}%)' + ' ' * 69 + '│')
print('└' + '─' * 118 + '┘')
print()

# RESUMEN ANUAL
print('┌' + '─' * 118 + '┐')
print('│ RESUMEN ANUAL - 2024 (8,760 horas)' + ' ' * 81 + '│')
print('├' + '─' * 118 + '┤')

pv_gen_year = df['pv_generation_kwh'].sum()
ev_dem_year = df['ev_demand_kwh'].sum()
mall_dem_year = df['mall_demand_kwh'].sum()
pv_to_ev_year = df['pv_to_ev_kwh'].sum()
pv_to_bess_year = df['pv_to_bess_kwh'].sum()
pv_to_mall_year = df['pv_to_mall_kwh'].sum()
bess_charge_year = df['bess_charge_kwh'].sum()
bess_discharge_year = df['bess_discharge_kwh'].sum()
bess_to_ev_year = df['bess_to_ev_kwh'].sum()
bess_to_mall_year = df['bess_to_mall_kwh'].sum()

print('│ GENERACIÓN' + ' ' * 107 + '│')
print(f'│   PV generado:       {pv_gen_year:12,.1f} kWh = {pv_gen_year/1e6:8.2f} MWh' + ' ' * 77 + '│')
print('│ ' + ' ' * 116 + '│')
print('│ DEMANDA' + ' ' * 110 + '│')
print(f'│   EV demand (9-22h): {ev_dem_year:12,.1f} kWh = {ev_dem_year/1e6:8.2f} MWh' + ' ' * 77 + '│')
print(f'│   MALL demand:       {mall_dem_year:12,.1f} kWh = {mall_dem_year/1e6:8.2f} MWh' + ' ' * 77 + '│')
print('│ ' + ' ' * 116 + '│')
print('│ DISTRIBUCIÓN PV' + ' ' * 102 + '│')
print(f'│   PV → EV directo:   {pv_to_ev_year:12,.1f} kWh = {pv_to_ev_year/1e6:8.2f} MWh  ({100*pv_to_ev_year/ev_dem_year:5.1f}%)' + ' ' * 67 + '│')
print(f'│   PV → BESS carga:   {pv_to_bess_year:12,.1f} kWh = {pv_to_bess_year/1e6:8.2f} MWh  ({100*pv_to_bess_year/pv_gen_year:5.1f}%)' + ' ' * 67 + '│')
print(f'│   PV → MALL directo: {pv_to_mall_year:12,.1f} kWh = {pv_to_mall_year/1e6:8.2f} MWh  ({100*pv_to_mall_year/mall_dem_year:5.1f}%)' + ' ' * 67 + '│')
print('│ ' + ' ' * 116 + '│')
print('│ OPERACIÓN BESS' + ' ' * 103 + '│')
print(f'│   Total cargado:     {bess_charge_year:12,.1f} kWh = {bess_charge_year/1e6:8.2f} MWh' + ' ' * 77 + '│')
print(f'│   Total descargado:  {bess_discharge_year:12,.1f} kWh = {bess_discharge_year/1e6:8.2f} MWh' + ' ' * 77 + '│')
print(f'│   Ciclos/año:        {bess_discharge_year/BESS_CAPACITY_KWH:12,.2f}  (típico: 0.33-1.5 en sistemas solares)' + ' ' * 62 + '│')
print('│ ' + ' ' * 116 + '│')
print('│ DISTRIBUCIÓN BESS' + ' ' * 100 + '│')
print(f'│   BESS → EV:         {bess_to_ev_year:12,.1f} kWh = {bess_to_ev_year/1e6:8.2f} MWh  ({100*bess_to_ev_year/ev_dem_year:5.1f}%)' + ' ' * 67 + '│')
print(f'│   BESS → MALL:       {bess_to_mall_year:12,.1f} kWh = {bess_to_mall_year/1e6:8.2f} MWh  ({100*bess_to_mall_year/mall_dem_year:5.1f}%)' + ' ' * 67 + '│')
print('│ ' + ' ' * 116 + '│')
print('│ COBERTURA ENERGÉTICA ANUAL' + ' ' * 91 + '│')
ev_coverage_year = (pv_to_ev_year + bess_to_ev_year) / ev_dem_year * 100 if ev_dem_year > 0 else 0
mall_coverage_year = (pv_to_mall_year + bess_to_mall_year) / mall_dem_year * 100 if mall_dem_year > 0 else 0
print(f'│   EV cobertura:      {pv_to_ev_year + bess_to_ev_year:12,.1f} / {ev_dem_year:12,.1f} kWh  ({ev_coverage_year:5.1f}%)' + ' ' * 61 + '│')
print(f'│   MALL cobertura:    {pv_to_mall_year + bess_to_mall_year:12,.1f} / {mall_dem_year:12,.1f} kWh  ({mall_coverage_year:5.1f}%)' + ' ' * 61 + '│')
print('└' + '─' * 118 + '┘')
print()

# Guardar CSV mejorado con columna SOC en kWh
output_path = Path('data/oe2/bess/bess_simulation_hourly_with_soc_kwh.csv')
df.to_csv(output_path, index=False)
print(f'✓ Archivo generado: {output_path}')
print(f'  Columna agregada: bess_soc_kwh (energía almacenada en kWh)')
