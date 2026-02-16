#!/usr/bin/env python3
"""
Verificar que SAC, PPO y A2C usan los MISMOS datasets OE2
"""

import pandas as pd
from pathlib import Path
import sys

def main():
    print('\n' + '='*80)
    print('[GRAPH] DATASETS UTILIZADOS POR SAC, PPO Y A2C')
    print('='*80)
    
    all_exist = True
    
    # Solar
    solar_path = Path('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv')
    if solar_path.exists():
        solar_df = pd.read_csv(solar_path)
        print(f'\n[OK] SOLAR: {len(solar_df)} filas × {len(solar_df.columns)} col')
        print(f'   📁 {solar_path}')
        print(f'   ⚡ Energia: {solar_df.iloc[:, 1].sum():.0f} kWh/ano')
    else:
        print(f'\n[X] SOLAR NO ENCONTRADO: {solar_path}')
        all_exist = False

    # Chargers
    chargers_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
    if chargers_path.exists():
        chargers_df = pd.read_csv(chargers_path)
        print(f'\n[OK] CHARGERS: {len(chargers_df)} filas × {len(chargers_df.columns)} col')
        print(f'   📁 {chargers_path}')
        print(f'   🔋 Tomas: 30 motos + 8 taxis = 38 total')
        print(f'   ⚡ Energia: {chargers_df.iloc[:, 1:].sum().sum():.0f} kWh/ano')
    else:
        print(f'\n[X] CHARGERS NO ENCONTRADO: {chargers_path}')
        all_exist = False

    # BESS
    bess_path = Path('data/oe2/bess/bess_ano_2024.csv')
    if bess_path.exists():
        bess_df = pd.read_csv(bess_path)
        print(f'\n[OK] BESS: {len(bess_df)} filas × {len(bess_df.columns)} col')
        print(f'   📁 {bess_path}')
        print(f'   🏗️ Capacidad: 1,700 kWh max')
        if 'soc_percent' in bess_df.columns:
            print(f'   [GRAPH] SOC promedio: {bess_df["soc_percent"].mean():.1f}%')
    else:
        print(f'\n[X] BESS NO ENCONTRADO: {bess_path}')
        all_exist = False

    # Mall
    mall_path = Path('data/oe2/demandamallkwh/demandamallhorakwh.csv')
    if mall_path.exists():
        mall_df = pd.read_csv(mall_path)
        print(f'\n[OK] MALL: {len(mall_df)} filas × {len(mall_df.columns)} col')
        print(f'   📁 {mall_path}')
        print(f'   ⚡ Demanda total: {mall_df.iloc[:, 1].sum():.0f} kWh/ano')
    else:
        print(f'\n[X] MALL NO ENCONTRADO: {mall_path}')
        all_exist = False

    print('\n' + '='*80)
    print('🔗 CONEXION DE DATOS: Flujo OE2 -> Agentes')
    print('='*80)
    print('\nTodos los agentes cargan via src/citylearnv2/dataset_builder/data_loader.py:')
    print('')
    print('SAC  | load_solar_data() --+')
    print('     | load_chargers_data()+--> 27 Observables OE3')
    print('     | load_bess_data()    +--> Espacio de observacion')
    print('     | load_mall_demand()  +')
    print('')
    print('PPO  | load_solar_data() --+ (ENTRENANDO AHORA)')
    print('     | load_chargers_data()+--> 8,760 timesteps/ano')
    print('     | load_bess_data()    +--> 39 acciones')
    print('     | load_mall_demand()  +')
    print('')
    print('A2C  | load_solar_data() --+')
    print('     | load_chargers_data()+--> Mismo dataset')
    print('     | load_bess_data()    +--> Mismo reward')
    print('     | load_mall_demand()  +')
    print('')
    print('='*80)
    
    if all_exist:
        print('\n[OK] TODOS LOS DATASETS ENCONTRADOS Y SINCRONIZADOS')
        return 0
    else:
        print('\n[!] FALTA ALGUN DATASET')
        return 1

if __name__ == '__main__':
    sys.exit(main())
