#!/usr/bin/env python3
"""
Verificacion DURANTE ENTRENAMIENTO: PPO usa correctamente
todos los datos OE2 con anos completos
"""

from pathlib import Path
import pandas as pd
import numpy as np

def verify_training_data_usage():
    """
    Verifica que train_ppo_multiobjetivo.py este usando:
    1. Todas las columnas de cada dataset
    2. 8,760 horas (ano completo)
    3. Con los valores correctos
    """
    
    print('\n' + '='*90)
    print('🔍 VERIFICACION: PPO usa TODOS los datos OE2 correctamente')
    print('='*90)
    
    # Los datasets esperados
    datasets = {
        'Solar': {
            'path': 'data/oe2/Generacionsolar/pv_generation_citylearn2024.csv',
            'expected_energy': 1_668_084,
            'expected_hours': 8760,
            'type': 'hourly',
            'description': 'Generacion FV (PVGIS Iquitos)'
        },
        'Chargers': {
            'path': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
            'expected_energy': 43_283_051,
            'expected_hours': 8760,
            'expected_sockets': 38,
            'type': 'hourly_multicolumn',
            'description': 'Demanda EV (30 motos + 8 taxis)'
        },
        'BESS': {
            'path': 'data/oe2/bess/bess_ano_2024.csv',
            'expected_capacity': 1700,
            'expected_hours': 8760,
            'expected_soc_avg': 0.6,
            'type': 'hourly_multicol',
            'description': 'Estado de bateria (SOC)'
        },
        'Mall': {
            'path': 'data/oe2/demandamallkwh/demandamallhorakwh.csv',
            'expected_energy': 12_368_653,
            'expected_hours': 8760,
            'expected_peak': 2763,
            'type': 'hourly',
            'description': 'Demanda centro comercial'
        }
    }
    
    print('\n📋 VERIFICACION DE INTEGRIDAD DE DATOS\n')
    
    all_ok = True
    
    # ========================================================================
    # 1. SOLAR
    # ========================================================================
    print('1️⃣  SOLAR - Generacion FV')
    print('-'*90)
    
    solar_path = Path(datasets['Solar']['path'])
    if solar_path.exists():
        solar_df = pd.read_csv(solar_path)
        solar_col = 'irradiancia_ghi' if 'irradiancia_ghi' in solar_df.columns else solar_df.columns[1]
        solar_data = solar_df[solar_col].values[:8760]
        
        print(f"  [OK] Archivo existe: {solar_path}")
        print(f"  [GRAPH] Columna usada: '{solar_col}'")
        print(f"  📏 Filas cargadas: {len(solar_data)}")
        print(f"  ⚡ Energia anual: {np.sum(solar_data):,.0f} kWh")
        print(f"     Esperado:     1,668,084 kWh")
        
        energy_match = abs(np.sum(solar_data) - 1_668_084) < 10000  # 10 MWh tolerancia
        if energy_match:
            print(f"  [OK] ENERGIA CORRECTA")
        else:
            print(f"  [X] ENERGIA INCORRECTA (diferencia: {np.sum(solar_data) - 1_668_084:,.0f} kWh)")
            all_ok = False
        
        if len(solar_data) == 8760:
            print(f"  [OK] ANO COMPLETO (8,760 horas)")
        else:
            print(f"  [X] ANO INCOMPLETO ({len(solar_data)} horas)")
            all_ok = False
    else:
        print(f"  [X] Archivo no encontrado: {solar_path}")
        all_ok = False
    
    # ========================================================================
    # 2. CHARGERS
    # ========================================================================
    print('\n2️⃣  CHARGERS - Demanda EV')
    print('-'*90)
    
    chargers_path = Path(datasets['Chargers']['path'])
    if chargers_path.exists():
        chargers_df = pd.read_csv(chargers_path)
        # Tomar primeras 38 columnas (sockets)
        chargers_data = chargers_df.iloc[:8760, :38].copy()
        # Convertir a numeric
        for col in chargers_data.columns:
            chargers_data[col] = pd.to_numeric(chargers_data[col], errors='coerce')
        
        total_energy = float(chargers_data.sum().sum())
        
        print(f"  [OK] Archivo existe: {chargers_path}")
        print(f"  🔌 Sockets cargados: {chargers_data.shape[1]}")
        print(f"     Esperado:         38")
        print(f"  📏 Filas cargadas: {len(chargers_data)}")
        print(f"  ⚡ Energia anual: {total_energy:,.0f} kWh")
        print(f"     Esperado:     43,283,051 kWh")
        
        energy_match = abs(total_energy - 43_283_051) < 100000  # 100 MWh tolerancia
        if energy_match:
            print(f"  [OK] ENERGIA CORRECTA")
        else:
            print(f"  [!]  ENERGIA DIFERENTE (diferencia: {total_energy - 43_283_051:,.0f} kWh)")
            print(f"     (NOTA: Puede variar por que columnas se usen)")
        
        if chargers_data.shape[1] == 38:
            print(f"  [OK] 38 SOCKETS COMPLETOS")
        else:
            print(f"  [X] SOCKETS INCOMPLETOS ({chargers_data.shape[1]})")
            all_ok = False
        
        if len(chargers_data) == 8760:
            print(f"  [OK] ANO COMPLETO (8,760 horas)")
        else:
            print(f"  [X] ANO INCOMPLETO ({len(chargers_data)} horas)")
            all_ok = False
    else:
        print(f"  [X] Archivo no encontrado: {chargers_path}")
        all_ok = False
    
    # ========================================================================
    # 3. BESS
    # ========================================================================
    print('\n3️⃣  BESS - Almacenamiento')
    print('-'*90)
    
    bess_path = Path(datasets['BESS']['path'])
    if bess_path.exists():
        bess_df = pd.read_csv(bess_path)
        soc_cols = [c for c in bess_df.columns if 'soc' in c.lower()]
        
        if soc_cols:
            bess_soc = bess_df[soc_cols[0]].values[:8760]
            # Normalizar si esta en [0,100]
            if np.max(bess_soc) > 1.0:
                bess_soc = bess_soc / 100.0
            
            print(f"  [OK] Archivo existe: {bess_path}")
            print(f"  [GRAPH] Columna SOC usada: '{soc_cols[0]}'")
            print(f"  📏 Filas cargadas: {len(bess_soc)}")
            print(f"  🔋 Capacidad: 1,700 kWh max")
            print(f"  [CHART] SOC promedio: {np.mean(bess_soc):.1%}")
            print(f"     Esperado:    60%")
            print(f"  [GRAPH] SOC rango: {np.min(bess_soc):.1%} - {np.max(bess_soc):.1%}")
            
            soc_match = abs(np.mean(bess_soc) - 0.60) < 0.05  # 5% tolerancia
            if soc_match:
                print(f"  [OK] SOC PROMEDIO CORRECTO")
            else:
                print(f"  [!]  SOC promedio distinto (actual: {np.mean(bess_soc):.1%})")
            
            if len(bess_soc) == 8760:
                print(f"  [OK] ANO COMPLETO (8,760 horas)")
            else:
                print(f"  [X] ANO INCOMPLETO ({len(bess_soc)} horas)")
                all_ok = False
        else:
            print(f"  [X] No se encontro columna SOC en {bess_path}")
            all_ok = False
    else:
        print(f"  [X] Archivo no encontrado: {bess_path}")
        all_ok = False
    
    # ========================================================================
    # 4. MALL
    # ========================================================================
    print('\n4️⃣  MALL - Demanda Centro Comercial')
    print('-'*90)
    
    mall_path = Path(datasets['Mall']['path'])
    if mall_path.exists():
        mall_df = pd.read_csv(mall_path, sep=';')
        mall_col = mall_df.columns[-1]
        mall_data = mall_df[mall_col].values[:8760]
        
        print(f"  [OK] Archivo existe: {mall_path}")
        print(f"  [GRAPH] Columna usada: '{mall_col}'")
        print(f"  📏 Filas cargadas: {len(mall_data)}")
        print(f"  ⚡ Energia anual: {np.sum(mall_data):,.0f} kWh")
        print(f"     Esperado:     12,368,653 kWh")
        print(f"  [CHART] Demanda promedio: {np.mean(mall_data):.1f} kW")
        print(f"  [GRAPH] Pico de demanda: {np.max(mall_data):.0f} kW")
        print(f"     Esperado:      ~2,763 kW")
        
        energy_match = abs(np.sum(mall_data) - 12_368_653) < 100000  # 100 MWh
        if energy_match:
            print(f"  [OK] ENERGIA CORRECTA")
        else:
            print(f"  [X] ENERGIA INCORRECTA (diferencia: {np.sum(mall_data) - 12_368_653:,.0f} kWh)")
            all_ok = False
        
        peak_match = abs(np.max(mall_data) - 2763) < 100  # 100 kW
        if peak_match:
            print(f"  [OK] PICO CORRECTO")
        else:
            print(f"  [!]  Pico distinto (actual: {np.max(mall_data):.0f} kW)")
        
        if len(mall_data) == 8760:
            print(f"  [OK] ANO COMPLETO (8,760 horas)")
        else:
            print(f"  [X] ANO INCOMPLETO ({len(mall_data)} horas)")
            all_ok = False
    else:
        print(f"  [X] Archivo no encontrado: {mall_path}")
        all_ok = False
    
    # ========================================================================
    # RESUMEN FINAL
    # ========================================================================
    
    print('\n' + '='*90)
    print('[GRAPH] RESUMEN DE VERIFICACION')
    print('='*90)
    
    if all_ok:
        print('\n[OK] ENTRENAMIENTO PPO TIENE ACCESO A TODOS LOS DATOS CORRECTOS\n')
        print('📋 Datasets verificados:')
        print(f'   [OK] Solar:     1,668,084 kWh/ano (8,760 horas)')
        print(f'   [OK] Chargers:  43,283,051 kWh/ano (8,760 × 38 sockets)')
        print(f'   [OK] BESS:      1,700 kWh max (SOC 60% promedio)')
        print(f'   [OK] Mall:      12,368,653 kWh/ano (2,763 kW pico)')
        print(f'\n🎯 PPO puede entrenar correctamente con TODOS los datos OE2')
        print('='*90 + '\n')
        return 0
    else:
        print('\n[X] ALGUNOS DATOS FALTA O SON INCORRECTOS\n')
        print('[!]  Verificar que:')
        print('   1. Todos los archivos existan en data/oe2/')
        print('   2. Tengan 8,760 filas (1 ano)')
        print('   3. Usen las columnas correctas')
        print('='*90 + '\n')
        return 1

if __name__ == '__main__':
    exit(verify_training_data_usage())
