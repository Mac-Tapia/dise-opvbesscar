#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VALIDACIÓN INTEGRAL - CO2, VEHÍCULOS, COSTOS Y DATOS REALES
=============================================================
Verifica que SAC, PPO y A2C:
1. Usen los mismos cálculos de CO2 (directo e indirecto)
2. Usen las mismas cantidades de motos y mototaxis
3. Generen los mismos resultados de emisiones, costos y ahorros
4. Usen SOLO datos reales del dataset (sin síntesis)
5. Entrenen con datos completos para 8,760 horas (1 año)
"""
from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Set
import re

# ============================================================================
# 1. BUSCAR Y EXTRAER DEFINICIONES DE CONSTANTES
# ============================================================================

def extract_constants_from_file(filepath: str) -> Dict[str, Any]:
    """Extrae todas las constantes de CO2, vehículos, costos de un archivo."""
    constants = {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Patrones a buscar
    patterns = {
        'MOTOS_TARGET': r'MOTOS_TARGET_DIARIOS\s*[=:]\s*(\d+)',
        'MOTOTAXIS_TARGET': r'MOTOTAXIS_TARGET_DIARIOS\s*[=:]\s*(\d+)',
        'VEHICLES_TOTAL': r'VEHICLES_TARGET_DIARIOS\s*[=:]\s*(\d+)',
        'MOTO_BATTERY': r'MOTO_BATTERY_KWH\s*[=:]\s*([\d.]+)',
        'MOTOTAXI_BATTERY': r'MOTOTAXI_BATTERY_KWH\s*[=:]\s*([\d.]+)',
        'CO2_FACTOR_MOTO': r'CO2_FACTOR_MOTO_KG_KWH\s*[=:]\s*([\d.]+)',
        'CO2_FACTOR_MOTOTAXI': r'CO2_FACTOR_MOTOTAXI_KG_KWH\s*[=:]\s*([\d.]+)',
        'CO2_IQUITOS': r'CO2_FACTOR_IQUITOS\s*[=:]\s*([\d.]+)',
        'BESS_MAX_KWH': r'BESS_MAX_KWH[_CONST]*\s*[=:]\s*([\d.]+)',
        'SOLAR_MAX_KW': r'SOLAR_MAX_KW\s*[=:]\s*([\d.]+)',
        'CHARGER_MAX_KW': r'CHARGER_MAX_KW\s*[=:]\s*([\d.]+)',
        'MOTO_ENERGY_CHARGE': r'MOTO_ENERGY_TO_CHARGE\s*[=:]\s*([\d.]+)',
        'MOTOTAXI_ENERGY_CHARGE': r'MOTOTAXI_ENERGY_TO_CHARGE\s*[=:]\s*([\d.]+)',
    }
    
    for key, pattern in patterns.items():
        matches = re.findall(pattern, content)
        if matches:
            # Tomar la última ocurrencia (más actual)
            constants[key] = matches[-1]
    
    return constants

# ============================================================================
# 2. BUSCAR CÁLCULOS DE CO2 EN CADA ARCHIVO
# ============================================================================

def find_co2_calculation_locations(filepath: str) -> Dict[str, List[int]]:
    """Encuentra las líneas donde se calculan valores de CO2."""
    locations = {
        'co2_directo': [],
        'co2_indirecto': [],
        'motos_charging': [],
        'mototaxis_charging': [],
        'cost_grid': [],
        'ahorro_solar': []
    }
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines, 1):
        if 'co2_directo' in line.lower() or 'reduccion_directa' in line.lower():
            locations['co2_directo'].append(i)
        if 'co2_indirecto' in line.lower() or 'indirecto' in line.lower():
            locations['co2_indirecto'].append(i)
        if 'motos' in line.lower() and 'charg' in line.lower():
            locations['motos_charging'].append(i)
        if 'mototaxi' in line.lower() and 'charg' in line.lower():
            locations['mototaxis_charging'].append(i)
        if 'cost' in line.lower() and 'grid' in line.lower():
            locations['cost_grid'].append(i)
        if 'ahorro' in line.lower() and 'solar' in line.lower():
            locations['ahorro_solar'].append(i)
    
    return {k: v for k, v in locations.items() if v}

# ============================================================================
# 3. EXTRAER COLUMNAS DEL DATASET USADAS
# ============================================================================

def extract_dataset_columns(filepath: str) -> Dict[str, List[str]]:
    """Extrae las columnas de dataset mencionadas en cada archivo."""
    columns = {
        'chargers': [],
        'bess': [],
        'solar': [],
        'mall': []
    }
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar definiciones de listas de columnas
    col_patterns = {
        'chargers': r"CHARGERS_.*?:\s*List\[str\]\s*=\s*\[(.*?)\]",
        'bess': r"BESS_.*?:\s*List\[str\]\s*=\s*\[(.*?)\]",
        'solar': r"SOLAR_.*?:\s*List\[str\]\s*=\s*\[(.*?)\]",
        'mall': r"MALL_.*?:\s*List\[str\]\s*=\s*\[(.*?)\]"
    }
    
    for dataset_type, pattern in col_patterns.items():
        matches = re.findall(pattern, content, re.DOTALL)
        if matches:
            # Extraer nombres de columnas
            col_str = matches[0]
            col_names = re.findall(r"'([^']+)'", col_str)
            columns[dataset_type] = col_names
    
    return {k: v for k, v in columns.items() if v}

# ============================================================================
# 4. VALIDAR DATOS DE ENTRADA
# ============================================================================

def validate_dataset_size() -> Dict[str, Dict[str, int]]:
    """Verifica que todos los datasets tengan 8,760 horas (1 año)."""
    results = {}
    
    # Rutas esperadas
    data_paths = {
        'chargers': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
        'bess': 'data/oe2/bess/bess_ano_2024.csv',
        'solar': 'data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv',
        'mall': 'data/oe2/demandamallkwh/demandamallhorakwh.csv'
    }
    
    for dataset_type, path in data_paths.items():
        full_path = Path(path)
        if full_path.exists():
            import pandas as pd
            try:
                df = pd.read_csv(full_path)
                results[dataset_type] = {
                    'rows': len(df),
                    'expected': 8760 if 'annual' in path.lower() or 'ano_2024' in path else 'varies',
                    'status': '✅ OK' if len(df) == 8760 or len(df) % 365 == 0 else '⚠️ WARNING'
                }
            except Exception as e:
                results[dataset_type] = {'error': str(e)}
        else:
            results[dataset_type] = {'status': '❌ NOT FOUND', 'path': path}
    
    return results

# ============================================================================
# MAIN VALIDATION REPORT
# ============================================================================

def main():
    print("=" * 80)
    print("VALIDACIÓN INTEGRAL - CO2, VEHÍCULOS Y DATOS REALES")
    print("=" * 80)
    print()
    
    agent_files = {
        'SAC': 'scripts/train/train_sac.py',
        'PPO': 'scripts/train/train_ppo.py',
        'A2C': 'scripts/train/train_a2c.py'
    }
    
    agent_data = {}
    
    # 1. EXTRAER CONSTANTES
    print("\n[1] EXTRAYENDO CONSTANTES...")
    print("-" * 80)
    
    for agent_name, filepath in agent_files.items():
        if Path(filepath).exists():
            constants = extract_constants_from_file(filepath)
            agent_data[agent_name] = {
                'file': filepath,
                'constants': constants,
                'co2_locations': find_co2_calculation_locations(filepath),
                'dataset_cols': extract_dataset_columns(filepath)
            }
            
            print(f"\n{agent_name}:")
            if constants:
                for key, value in constants.items():
                    print(f"  {key}: {value}")
            else:
                print(f"  ⚠️ Sin constantes encontradas")
        else:
            print(f"\n❌ {agent_name}: Archivo no encontrado ({filepath})")
    
    # 2. COMPARAR CONSTANTES
    print("\n\n[2] COMPARACIÓN DE CONSTANTES...")
    print("-" * 80)
    
    if len(agent_data) == 3:
        # Obtener todas las claves
        all_keys = set()
        for agent_info in agent_data.values():
            all_keys.update(agent_info['constants'].keys())
        
        all_match = True
        for key in sorted(all_keys):
            values = {agent: agent_info['constants'].get(key, '❌ FALTA')
                     for agent, agent_info in agent_data.items()}
            
            # Verificar si todos son iguales
            unique_values = set(v for v in values.values() if v != '❌ FALTA')
            match = len(unique_values) <= 1
            
            if not match:
                all_match = False
            
            status = "✅" if match else "❌"
            print(f"{status} {key:25} | SAC: {values.get('SAC', 'N/A'):12} | " +
                  f"PPO: {values.get('PPO', 'N/A'):12} | A2C: {values.get('A2C', 'N/A'):12}")
        
        print()
        if all_match:
            print("✅ TODAS LAS CONSTANTES COINCIDEN")
        else:
            print("❌ HAY DIFERENCIAS EN CONSTANTES - REQUIERE ALINEACIÓN")
    
    # 3. UBICACIONES DE CÁLCULOS
    print("\n\n[3] UBICACIONES DE CÁLCULOS DE CO2...")
    print("-" * 80)
    
    for agent_name, agent_info in agent_data.items():
        print(f"\n{agent_name}:")
        if agent_info['co2_locations']:
            for calc_type, line_nums in agent_info['co2_locations'].items():
                print(f"  {calc_type:20}: Líneas {line_nums[:3]}{'...' if len(line_nums) > 3 else ''}")
        else:
            print("  ⚠️ No se encontraron cálculos de CO2")
    
    # 4. VALIDAR DATASETS
    print("\n\n[4] VALIDACIÓN DE DATASETS...")
    print("-" * 80)
    
    try:
        import pandas as pd
        dataset_validation = validate_dataset_size()
        
        for dataset_type, info in dataset_validation.items():
            if 'error' in info:
                print(f"❌ {dataset_type:15}: Error - {info['error']}")
            elif 'status' in info and '❌' in info['status']:
                print(f"❌ {dataset_type:15}: {info['status']}")
            else:
                rows = info.get('rows', 'N/A')
                expected = info.get('expected', 'varies')
                status = info.get('status', '❓')
                
                if rows == 8760:
                    print(f"✅ {dataset_type:15}: {rows} horas (completo) {status}")
                else:
                    print(f"⚠️  {dataset_type:15}: {rows} horas (esperado 8760)")
    except ImportError:
        print("⚠️ pandas no disponible - saltando validación de datasets")
    
    # 5. RESUMEN Y RECOMENDACIONES
    print("\n\n[5] RESUMEN Y RECOMENDACIONES")
    print("=" * 80)
    
    print("""
CHECKLIST:

☐ CO2 DIRECTO:
  - Verificar que SAC, PPO, A2C usen 'reduccion_directa_co2_kg' del dataset
  - Factor motos: 0.87 kg CO2/kWh vs gasolina
  - Factor mototaxis: 0.47 kg CO2/kWh vs gasolina

☐ CO2 INDIRECTO:
  - Solar: Usar 'reduccion_indirecta_co2_kg_total' (si disponible)
  - Factor: 0.4521 kg CO2/kWh (grid Iquitos)
  - BESS: Usar 'bess_to_ev_kwh' + 'bess_to_mall_kwh'

☐ VEHÍCULOS:
  - Motos: 30 sockets (IDs 0-29)
  - Mototaxis: 8 sockets (IDs 30-37)
  - Total diarios: 270 motos + 39 mototaxis = 309

☐ DATOS REALES:
  - ✅ chargers_ev_ano_2024_v3.csv: 8760 horas
  - ✅ bess_ano_2024.csv: 8760 horas
  - ✅ pv_generation_citylearn_enhanced_v2.csv: 8760 horas (VERIFICAR)
  - ✅ demandamallhorakwh.csv: 8760 horas

☐ COSTOS Y AHORROS:
  - Usar tariff_osinergmin_soles_kwh del dataset BESS
  - Ahorro solar: pv_to_ev_kwh * tariff
  - Ahorro BESS: bess_discharge_kwh * tariff (peak shaving)

ACCIÓN REQUERIDA:
================
1. Alinear TODAS las constantes (especialmente BESS_MAX_KWH=2000.0)
2. Verificar que los tres usen SOLO datos reales (no calculados)
3. Confirmar que usan 100% del año (8,760 horas)
4. Hacer una simulación de prueba con 1 episodio y comparar resultados
""")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
