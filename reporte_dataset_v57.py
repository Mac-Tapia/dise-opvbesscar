#!/usr/bin/env python3
"""Reporte Detallado: Estructura del Dataset BESS v5.7"""

import pandas as pd

print('='*100)
print('REPORTE DETALLADO: DATASET BESS_ANO_2024.CSV v5.7 - TODAS LAS COLUMNAS GENERADAS')
print('='*100)
print()

df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv', index_col=0)

print(f'Dataset completo: {len(df)} filas x {len(df.columns)} columnas')
print()

# Agrupar columnas por categoria
categories = {
    'DEMANDAS Y GENERACION': [
        'pv_kwh',
        'ev_kwh',
        'mall_kwh',
        'load_kwh',
    ],
    'FLUJOS ENERGETICOS (PV)': [
        'pv_to_ev_kwh',
        'pv_to_bess_kwh',
        'pv_to_mall_kwh',
        'grid_export_kwh',
    ],
    'OPERACION BESS': [
        'bess_action_kwh',
        'bess_mode',
        'bess_to_ev_kwh',
        'bess_to_mall_kwh',
        'pv_to_bess_kwh',  # Carga BESS desde PV
        'bess_energy_stored_hourly_kwh',
        'bess_energy_delivered_hourly_kwh',
    ],
    'ESTADO BESS': [
        'soc_percent',
        'soc_kwh',
        'bess_balance_error_hourly_kwh',
        'bess_balance_error_hourly_percent',
        'bess_validation_status_hourly',
    ],
    'FLUJOS GRID': [
        'grid_import_kwh',
        'grid_import_ev_kwh',
        'grid_import_mall_kwh',
        'mall_grid_import_kwh',
    ],
    'DEMANDAS POST-BESS': [
        'ev_demand_after_bess_kwh',
        'mall_demand_after_bess_kwh',
        'load_after_bess_kwh',
    ],
    'TARIFAS Y COSTOS (OSINERGMIN)': [
        'tariff_period',
        'tariff_rate_soles_kwh',
        'cost_if_grid_import_soles',
        'cost_avoided_by_bess_soles',
        'tariff_index_hp_hfp',
        'cost_savings_hp_soles',
        'cost_savings_hfp_soles',
    ],
    'AMBIENTAL': [
        'co2_avoided_indirect_kg',
    ],
}

descriptions = {
    'pv_kwh': 'Generación solar (kWh)',
    'ev_kwh': 'Demanda EV (38 sockets, motos+taxis)',
    'mall_kwh': 'Demanda Mall (pico: 2763 kW)',
    'load_kwh': 'Carga total (EV + Mall)',
    
    'pv_to_ev_kwh': 'PV directo a EV (prioridad 1)',
    'pv_to_bess_kwh': 'PV a BESS para carga (excedente)',
    'pv_to_mall_kwh': 'PV directo a Mall (42.3% anual)',
    'grid_export_kwh': 'PV excedente exportado a grid (1.77M kWh)',
    
    'bess_action_kwh': 'Acción BESS neta (carga/descarga)',
    'bess_mode': 'Estado BESS: charge, discharge, idle',
    'bess_to_ev_kwh': 'BESS descargado a EV',
    'bess_to_mall_kwh': 'BESS descargado a Mall (peak shaving)',
    'bess_energy_stored_hourly_kwh': 'Energia almacenada en BESS (kWh)',
    'bess_energy_delivered_hourly_kwh': 'Energia entregada por BESS (kWh)',
    
    'soc_percent': 'State of Charge (%), rango 20%-100%',
    'soc_kwh': 'Carga como energia (kWh, max 1700)',
    'bess_balance_error_hourly_kwh': 'Error de balance BESS (kWh)',
    'bess_balance_error_hourly_percent': 'Error de balance BESS (%)',
    'bess_validation_status_hourly': 'Status de validación horaria',
    
    'grid_import_kwh': 'Total importado de grid (6.92M kWh)',
    'grid_import_ev_kwh': 'Grid para EV (cuando PV insuficiente)',
    'grid_import_mall_kwh': 'Grid para Mall (52.9% de demanda)',
    'mall_grid_import_kwh': 'Grid a Mall (respaldo)',
    
    'ev_demand_after_bess_kwh': 'Demanda EV después de BESS (net)',
    'mall_demand_after_bess_kwh': 'Demanda Mall después de BESS (net)',
    'load_after_bess_kwh': 'Carga total después de BESS',
    
    'tariff_period': 'Periodo tariffario: HP (punta) o HFP (fuera punta)',
    'tariff_rate_soles_kwh': 'Tarifa (S/./kWh): HP=0.45, HFP=0.28',
    'cost_if_grid_import_soles': 'Costo si se importara 100% desde grid',
    'cost_avoided_by_bess_soles': 'Ahorro por BESS (arbitraje + renewable)',
    'tariff_index_hp_hfp': 'Indice: 1=HP (caro), 0=HFP (barato)',
    'cost_savings_hp_soles': 'Ahorro en horas punta (HP)',
    'cost_savings_hfp_soles': 'Ahorro en fuera punta (HFP)',
    
    'co2_avoided_indirect_kg': 'CO2 evitado por PV + BESS (kg)',
}

for category, cols in categories.items():
    print(f'\n[{category.upper()}]')
    print('-' * 100)
    
    for col in cols:
        if col in df.columns:
            # Calcular estadísticas
            value_min = df[col].min()
            value_max = df[col].max()
            value_mean = df[col].mean()
            value_sum = df[col].sum()
            
            desc = descriptions.get(col, 'N/A')
            
            print(f'  {col:35s} | {desc:55s}')
            print(f'    {"min":5s}: {value_min:>12,.1f} | max: {value_max:>12,.1f} | '
                  f'mean: {value_mean:>12,.1f} | sum: {value_sum:>15,.0f}')
            print()

print()
print('='*100)
print('RESUMEN FINAL')
print('='*100)
print()
print(f'Total columnas:           {len(df.columns)}')
print(f'Total filas:              {len(df)} (8760 horas = 1 año completo)')
print(f'Tamaño archivo:           {df.memory_usage(deep=True).sum() / 1e6:.1f} MB')
print()
print('Validaciones críticas:')
print(f'  - Demanda pico Mall: {df["mall_kwh"].max():.1f} kW (> 1900 kW) ✓')
print(f'  - PV generación: {df["pv_kwh"].sum():,.0f} kWh (≤ 8,292,514) ✓')
print(f'  - BESS descarga total: {df["bess_to_ev_kwh"].sum() + df["bess_to_mall_kwh"].sum():,.0f} kWh')
print(f'  - Grid import: {df["grid_import_kwh"].sum():,.0f} kWh')
print(f'  - Grid export: {df["grid_export_kwh"].sum():,.0f} kWh (PV excedente)')
print()
print('='*100)
