"""
Script para transformar el dataset y agregar las columnas esperadas por balance.py
Convierte columnas horarias (kWh) a sus equivalentes en potencia (kW)
"""

import pandas as pd
import numpy as np
from pathlib import Path

def transform_dataset():
    """Transformar dataset para que tenga las columnas esperadas por balance.py"""
    
    print('\n' + '='*80)
    print('TRANSFORMACIÓN DE DATASET PARA BALANCE.PY v5.7')
    print('='*80)
    
    # Load ORIGINAL dataset (not the incomplete transformed one)
    original_path = Path('data/oe2/bess/bess_ano_2024.csv')
    print(f'\n📂 Cargando dataset ORIGINAL: {original_path}')
    
    if not original_path.exists():
        print(f'❌ No encontrado: {original_path}')
        return False
    
    df = pd.read_csv(original_path, index_col=0)  # datetime como index
    print(f'✓ {len(df)} filas × {len(df.columns)} columnas originales')
    
    # Create a copy for transformation
    df_transformed = df.copy()
    
    # Convert kWh to kW (direct mapping since each row is 1 hour)
    # kWh/hora = kW
    print('\n🔄 Generando columnas derivadas...')
    
    # PV Generation
    if 'pv_kwh' in df.columns and 'pv_generation_kw' not in df.columns:
        df_transformed['pv_generation_kw'] = df['pv_kwh']  # Already in kW equivalent
        print('   ✓ pv_generation_kw (from pv_kwh)')
    
    # Demands
    if 'mall_kwh' in df.columns and 'mall_demand_kw' not in df.columns:
        df_transformed['mall_demand_kw'] = df['mall_kwh']
        print('   ✓ mall_demand_kw (from mall_kwh)')
    
    if 'ev_kwh' in df.columns and 'ev_demand_kw' not in df.columns:
        df_transformed['ev_demand_kw'] = df['ev_kwh']
        print('   ✓ ev_demand_kw (from ev_kwh)')
    
    # Total demand  
    if 'load_kwh' in df.columns and 'total_demand_kw' not in df.columns:
        df_transformed['total_demand_kw'] = df['load_kwh']
        print('   ✓ total_demand_kw (from load_kwh)')
    
    # BESS Operations (estas son energías dispatched dentro de cada hora)
    # Para aproximar como potencia, asumimos que se distribuyen uniformemente en la hora
    if 'bess_energy_delivered_hourly_kwh' in df.columns:
        # Usar la energía entregada como potencia (ya que es por hora)
        df_transformed['bess_charge_kw'] = df['bess_energy_stored_hourly_kwh'].fillna(0)
        df_transformed['bess_discharge_kw'] = df['bess_energy_delivered_hourly_kwh'].fillna(0)
        print('   ✓ bess_charge_kw (from bess_energy_stored_hourly_kwh)')
        print('   ✓ bess_discharge_kw (from bess_energy_delivered_hourly_kwh)')
    
    # Demands after BESS (consumos netos del grid)
    if 'ev_demand_after_bess_kwh' in df.columns and 'ev_demand_after_bess_kw' not in df.columns:
        df_transformed['ev_demand_after_bess_kw'] = df['ev_demand_after_bess_kwh']
        print('   ✓ ev_demand_after_bess_kw')
    
    if 'mall_demand_after_bess_kwh' in df.columns and 'mall_demand_after_bess_kw' not in df.columns:
        df_transformed['mall_demand_after_bess_kw'] = df['mall_demand_after_bess_kwh']
        print('   ✓ mall_demand_after_bess_kw')
    
    # Grid Imports/Exports
    if 'grid_import_kwh' in df.columns and 'demand_from_grid_kw' not in df.columns:
        df_transformed['demand_from_grid_kw'] = df['grid_import_kwh']
        print('   ✓ demand_from_grid_kw (from grid_import_kwh)')
    
    if 'grid_export_kwh' in df.columns and 'grid_export_kw' not in df.columns:
        df_transformed['grid_export_kw'] = df['grid_export_kwh']
        print('   ✓ grid_export_kw (from grid_export_kwh)')
    
    # PV to Demand (dispatches)
    if 'pv_to_ev_kwh' in df.columns and 'pv_to_ev_kw' not in df.columns:
        df_transformed['pv_to_ev_kw'] = df['pv_to_ev_kwh']
        print('   ✓ pv_to_ev_kw')
    
    if 'pv_to_bess_kwh' in df.columns and 'pv_to_bess_kw' not in df.columns:
        df_transformed['pv_to_bess_kw'] = df['pv_to_bess_kwh']
        print('   ✓ pv_to_bess_kw')
    
    if 'pv_to_mall_kwh' in df.columns and 'pv_to_mall_kw' not in df.columns:
        df_transformed['pv_to_mall_kw'] = df['pv_to_mall_kwh']
        print('   ✓ pv_to_mall_kw')
    
    # PV Total Dispatch
    if 'pv_to_ev_kw' in df_transformed.columns:
        df_transformed['pv_to_demand_kw'] = (
            df_transformed['pv_to_ev_kw'] + 
            df_transformed['pv_to_mall_kw']
        )
        print('   ✓ pv_to_demand_kw (sum of pv_to_ev + pv_to_mall)')
    
    # BESS SOC (State of Charge)
    if 'soc_percent' in df.columns and 'bess_soc_percent' not in df.columns:
        df_transformed['bess_soc_percent'] = df['soc_percent']
        print('   ✓ bess_soc_percent (from soc_percent)')
    
    if 'soc_kwh' in df.columns and 'bess_soc_kwh' not in df.columns:
        df_transformed['bess_soc_kwh'] = df['soc_kwh']
        print('   ✓ bess_soc_kwh (from soc_kwh)')
    
    # Additional aliases for different naming conventions
    if 'grid_export_kw' in df_transformed.columns and 'pv_to_grid_kw' not in df_transformed.columns:
        df_transformed['pv_to_grid_kw'] = df_transformed['grid_export_kw']
        print('   ✓ pv_to_grid_kw (alias for grid_export_kw)')
    
    # Add columns for demand that comes from grid
    if 'ev_demand_after_bess_kw' in df_transformed.columns and 'ev_from_grid_kw' not in df_transformed.columns:
        # Grid supply to EV = EV demand after BESS sourcing
        df_transformed['ev_from_grid_kw'] = df_transformed['ev_demand_after_bess_kw'].clip(lower=0)
        print('   ✓ ev_from_grid_kw')
    
    if 'mall_demand_after_bess_kw' in df_transformed.columns and 'mall_from_grid_kw' not in df_transformed.columns:
        df_transformed['mall_from_grid_kw'] = df_transformed['mall_demand_after_bess_kw'].clip(lower=0)
        print('   ✓ mall_from_grid_kw')
    
    # CO2 calculations
    if 'co2_avoided_indirect_kg' in df.columns and 'co2_avoided_kg' not in df_transformed.columns:
        df_transformed['co2_avoided_kg'] = df['co2_avoided_indirect_kg']
        print('   ✓ co2_avoided_kg')
    
    # CO2 from grid (estimated: grid_import * 0.4521 kg CO2/kWh)
    if 'grid_import_kwh' in df.columns and 'co2_from_grid_kg' not in df_transformed.columns:
        co2_intensity = 0.4521  # kg CO2/kWh from OSINERGMIN Iquitos mix
        df_transformed['co2_from_grid_kg'] = df['grid_import_kwh'] * co2_intensity
        print('   ✓ co2_from_grid_kg (grid_import * 0.4521 kg CO2/kWh)')
    
    # CO2 from grid to EV
    if 'grid_import_ev_kwh' in df.columns and 'co2_from_grid_ev_kg' not in df_transformed.columns:
        co2_intensity = 0.4521
        df_transformed['co2_from_grid_ev_kg'] = df['grid_import_ev_kwh'] * co2_intensity
        print('   ✓ co2_from_grid_ev_kg')
    
    # CO2 from grid to MALL
    if 'grid_import_mall_kwh' in df.columns and 'co2_from_grid_mall_kg' not in df_transformed.columns:
        co2_intensity = 0.4521
        df_transformed['co2_from_grid_mall_kg'] = df['grid_import_mall_kwh'] * co2_intensity
        print('   ✓ co2_from_grid_mall_kg')
    
    # Save transformed dataset - USING ORIGINAL NAME AND PATH
    output_path = Path('data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_transformed.to_csv(output_path, index=False)
    
    print(f'\n✅ Dataset transformado guardado: {output_path}')
    print(f'   {len(df_transformed)} filas × {len(df_transformed.columns)} columnas (+ {len(df_transformed.columns) - len(df.columns)} derivadas)')
    
    # Validation
    print('\n🔍 Validación de columnas...')
    required_cols = [
        'pv_generation_kw', 'mall_demand_kw', 'ev_demand_kw', 
        'bess_charge_kw', 'bess_discharge_kw', 'soc_percent', 
        'grid_export_kw', 'co2_avoided_indirect_kg', 'tariff_period'
    ]
    
    missing = [col for col in required_cols if col not in df_transformed.columns]
    if missing:
        print(f'   ⚠️  Columnas faltantes: {missing}')
    else:
        print('   ✓ Todas las columnas requeridas presentes')
    
    return output_path

if __name__ == '__main__':
    output = transform_dataset()
    print(f'\n📊 Listo para regenerar gráficas')
