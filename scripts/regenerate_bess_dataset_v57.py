"""
Script para regenerar BESS dataset con nuevas columnas tarifarias HP/HFP v5.7
Integra simulate_bess_ev_exclusive() con datasets de entrada
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dimensionamiento.oe2.disenobess.bess import simulate_bess_ev_exclusive

def load_input_data():
    """Load solar, EV, and mall demand data"""
    data_dir = Path('data/processed/citylearn/iquitos_ev_mall')
    
    # Load solar generation (must be 8760 rows)
    solar_csv = data_dir / 'solar_generation.csv'
    if solar_csv.exists():
        df_solar = pd.read_csv(solar_csv)
        # Use 'energia_kwh' or 'potencia_kw' column
        if 'energia_kwh' in df_solar.columns:
            solar_kw = df_solar['energia_kwh'].values.astype(float)
        elif 'potencia_kw' in df_solar.columns:
            solar_kw = df_solar['potencia_kw'].values.astype(float)
        else:
            solar_kw = df_solar.iloc[:, 4].values.astype(float)  # 5th column
    else:
        print(f"❌ Solar file not found: {solar_csv}")
        return None, None, None
    
    # Load EV demand from current BESS dataset
    bess_csv = data_dir / 'bess_timeseries.csv'
    if bess_csv.exists():
        df_bess = pd.read_csv(bess_csv)
        ev_kw = df_bess['ev_kwh'].values.astype(float)
        mall_kw = df_bess['mall_kwh'].values.astype(float)
    else:
        print(f"❌ BESS file not found: {bess_csv}")
        return None, None, None
    
    # Verify data length
    if len(solar_kw) != 8760:
        print(f"⚠️  Warning: Solar data has {len(solar_kw)} rows, expected 8760")
        solar_kw = solar_kw[:8760]  # Truncate
    
    if len(ev_kw) != 8760:
        print(f"⚠️  Warning: EV data has {len(ev_kw)} rows, expected 8760")
        ev_kw = ev_kw[:8760]
    
    if len(mall_kw) != 8760:
        print(f"⚠️  Warning: Mall data has {len(mall_kw)} rows, expected 8760")
        mall_kw = mall_kw[:8760]
    
    return solar_kw, ev_kw, mall_kw

def regenerate_bess_dataset():
    """Generate BESS timeseries with new tariff columns"""
    
    print('\n' + '='*80)
    print('REGENERANDO DATASET BESS CON COLUMNAS TARIFARIAS v5.7')
    print('='*80)
    
    # Load input data
    print('\n📥 Cargando datos de entrada...')
    solar_kw, ev_kw, mall_kw = load_input_data()
    
    if solar_kw is None:
        print("❌ No se pudieron cargar los datos")
        return False
    
    print(f'   ✓ Solar: {len(solar_kw)} horas')
    print(f'   ✓ EV: {len(ev_kw)} horas')
    print(f'   ✓ Mall: {len(mall_kw)} horas')
    
    # Run BESS simulation with tariff calculations
    print('\n⚙️  Ejecutando simulate_bess_ev_exclusive()...')
    try:
        df_bess_updated, metrics = simulate_bess_ev_exclusive(
            pv_kwh=solar_kw,
            ev_kwh=ev_kw,
            mall_kwh=mall_kw,
            capacity_kwh=2000,
            power_kw=400,
            efficiency=0.95,
            soc_min=0.20,
            soc_max=1.00,
            closing_hour=22,
            year=2024
        )
        
        print(f'   ✓ Simulación exitosa')
        print(f'   ✓ Shape: {df_bess_updated.shape}')
        
        # Check new columns
        tariff_cols = ['tariff_period', 'tariff_rate_soles_kwh', 'cost_savings_hp_soles', 
                      'cost_savings_hfp_soles', 'cost_avoided_by_bess_soles', 
                      'tariff_index_hp_hfp']
        
        print(f'\n   Nuevas columnas tarifarias:')
        for col in tariff_cols:
            if col in df_bess_updated.columns:
                print(f'      ✓ {col}')
            else:
                print(f'      ✗ {col} FALTA')
        
        # Summary statistics
        if 'tariff_period' in df_bess_updated.columns:
            hp_hours = (df_bess_updated['tariff_period'] == 'HP').sum()
            hfp_hours = (df_bess_updated['tariff_period'] == 'HFP').sum()
            print(f'\n   Distribución horaria:')
            print(f'      HP (18-23h): {hp_hours} horas')
            print(f'      HFP (resto): {hfp_hours} horas')
        
        if 'cost_savings_hp_soles' in df_bess_updated.columns:
            total_hp = df_bess_updated['cost_savings_hp_soles'].sum()
            total_hfp = df_bess_updated['cost_savings_hfp_soles'].sum()
            print(f'\n   Ahorros anuales:')
            print(f'      HP: S/. {total_hp:,.2f}')
            print(f'      HFP: S/. {total_hfp:,.2f}')
            print(f'      TOTAL: S/. {total_hp + total_hfp:,.2f}')
        
        # Save updated dataset
        print('\n💾 Guardando dataset actualizado...')
        output_path = Path('data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')
        df_bess_updated.to_csv(output_path, index=False)
        print(f'   ✓ Guardado: {output_path}')
        print(f'   ✓ Tamaño: {output_path.stat().st_size / 1024:.1f} KB')
        
        return True, df_bess_updated
        
    except Exception as e:
        print(f'❌ Error en simulación: {e}')
        import traceback
        traceback.print_exc()
        return False, None

def update_dataset_config():
    """Update dataset_config_v7.json with new column information"""
    
    print('\n' + '='*80)
    print('ACTUALIZANDO CONFIGURACIÓN DE DATASET')
    print('='*80)
    
    config_path = Path('data/iquitos_ev_mall/dataset_config_v7.json')
    
    if not config_path.exists():
        print(f'\n⚠️  Config file not found: {config_path}')
        print('   Creando nueva configuración...')
        config = {
            'version': '7.1',
            'timestamp': pd.Timestamp.now().isoformat(),
            'dataset_type': 'bess_ev_mall_timeseries',
            'rows': 8760,
            'columns': {
                'original': [
                    'pv_kwh', 'ev_kwh', 'mall_kwh', 'load_kwh', 
                    'pv_to_ev_kwh', 'pv_to_bess_kwh', 'pv_to_mall_kwh', 'pv_curtailed_kwh',
                    'bess_charge_kwh', 'bess_discharge_kwh', 'bess_action_kwh', 'bess_mode',
                    'bess_to_ev_kwh', 'bess_to_mall_kwh', 'peak_shaving_kwh', 'bess_total_discharge_kwh',
                    'grid_import_ev_kwh', 'grid_import_mall_kwh', 'grid_import_kwh', 'grid_export_kwh',
                    'soc_percent', 'soc_kwh', 'co2_avoided_indirect_kg', 'cost_savings_hp_soles',
                    'ev_demand_after_bess_kwh', 'mall_demand_after_bess_kwh', 'load_after_bess_kwh'
                ],
                'tariff_new_v57': [
                    'tariff_period', 'tariff_rate_soles_kwh', 'cost_if_grid_import_soles',
                    'cost_avoided_by_bess_soles', 'cost_savings_hp_soles', 'cost_savings_hfp_soles',
                    'tariff_index_hp_hfp'
                ]
            },
            'tariff_rates': {
                'hp_soles_kwh': 0.45,
                'hfp_soles_kwh': 0.28,
                'tariff_difference_soles_kwh': 0.17,
                'hp_factor': 1.607,
                'hp_hours': '18:00-22:59',
                'hfp_hours': '00:00-17:59, 23:00-23:59'
            },
            'hour_counts': {
                'hp_annual': 1825,
                'hfp_annual': 6935,
                'total': 8760
            },
            'expected_savings': {
                'hp_annual_soles': 11432.10,
                'hfp_annual_soles': 58827.06,
                'total_annual_soles': 70259.16
            }
        }
    else:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Update version and timestamp
        config['version'] = '7.1'
        config['timestamp'] = pd.Timestamp.now().isoformat()
        
        # Add tariff configuration if not present
        if 'tariff_rates' not in config:
            config['tariff_rates'] = {
                'hp_soles_kwh': 0.45,
                'hfp_soles_kwh': 0.28,
                'tariff_difference_soles_kwh': 0.17,
                'hp_factor': 1.607,
                'hp_hours': '18:00-22:59',
                'hfp_hours': '00:00-17:59, 23:00-23:59'
            }
        
        if 'columns' not in config:
            config['columns'] = {
                'tariff_new_v57': [
                    'tariff_period', 'tariff_rate_soles_kwh', 'cost_if_grid_import_soles',
                    'cost_avoided_by_bess_soles', 'cost_savings_hp_soles', 'cost_savings_hfp_soles',
                    'tariff_index_hp_hfp'
                ]
            }
        elif 'tariff_new_v57' not in config.get('columns', {}):
            config['columns']['tariff_new_v57'] = [
                'tariff_period', 'tariff_rate_soles_kwh', 'cost_if_grid_import_soles',
                'cost_avoided_by_bess_soles', 'cost_savings_hp_soles', 'cost_savings_hfp_soles',
                'tariff_index_hp_hfp'
            ]
    
    # Save updated config
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f'✓ Config actualizada: {config_path}')
    return config

if __name__ == '__main__':
    # Regenerate BESS dataset
    success, df = regenerate_bess_dataset()
    
    if success:
        # Update configuration
        config = update_dataset_config()
        
        print('\n' + '='*80)
        print('✅ REGENERACIÓN Y ACTUALIZACIÓN COMPLETADA')
        print('='*80)
        print(f'\nDataset actualizado con {len(config["columns"].get("tariff_new_v57", []))} columnas tarifarias')
        print(f'Filas: {len(df)}')
        print(f'Total columnas: {len(df.columns)}')
    else:
        print('\n❌ Error en regeneración')
        sys.exit(1)
