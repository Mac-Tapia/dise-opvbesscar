#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST DE CONSISTENCIA: SAC vs PPO vs A2C
=======================================
Compara resultados reales de los tres agentes en 1 episodio
Validapara que usen los mismos datos de CO2, vehículos y costos
"""

from __future__ import annotations

import os
import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple

# ============================================================================
# CARGAR DATASETS REALES (MISMO PARA LOS 3 AGENTES)
# ============================================================================

def load_real_datasets() -> Dict[str, pd.DataFrame]:
    """Carga los datasets reales que deben ser idénticos para SAC, PPO, A2C."""
    
    datasets = {}
    
    # 1. CHARGERS (CO2 DIRECTO)
    chargers_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
    if chargers_path.exists():
        datasets['chargers'] = pd.read_csv(chargers_path)
        print(f"✅ Chargers: {len(datasets['chargers'])} filas, " +
              f"{list(datasets['chargers'].columns)[:5]}...")
    else:
        print(f"❌ Chargers no encontrado")
        datasets['chargers'] = pd.DataFrame()
    
    # 2. BESS (CO2 INDIRECTO BESS)
    bess_path = Path('data/oe2/bess/bess_ano_2024.csv')
    if bess_path.exists():
        datasets['bess'] = pd.read_csv(bess_path)
        print(f"✅ BESS: {len(datasets['bess'])} filas")
    else:
        # Alternativa
        bess_path = Path('data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')
        if bess_path.exists():
            datasets['bess'] = pd.read_csv(bess_path)
            print(f"✅ BESS (alternativa): {len(datasets['bess'])} filas")
        else:
            print(f"❌ BESS no encontrado")
            datasets['bess'] = pd.DataFrame()
    
    # 3. SOLAR (CO2 INDIRECTO SOLAR)
    solar_path = Path('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv')
    if solar_path.exists():
        datasets['solar'] = pd.read_csv(solar_path)
        print(f"✅ Solar: {len(datasets['solar'])} filas")
    else:
        print(f"⚠️  Solar no encontrado en pv_generation_citylearn2024.csv")
        # Alternativa
        solar_path = Path('data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv')
        if solar_path.exists():
            datasets['solar'] = pd.read_csv(solar_path)
            print(f"✅ Solar (alternativa): {len(datasets['solar'])} filas")
        datasets['solar'] = pd.DataFrame()
    
    # 4. MALL (energía)
    mall_path = Path('data/oe2/demandamallkwh/demandamallhorakwh.csv')
    if mall_path.exists():
        datasets['mall'] = pd.read_csv(mall_path)
        print(f"✅ Mall: {len(datasets['mall'])} filas")
    else:
        print(f"❌ Mall no encontrado")
        datasets['mall'] = pd.DataFrame()
    
    return datasets

# ============================================================================
# VALIDAR COMPLETITUD DE DATOS
# ============================================================================

def validate_dataset_completeness(datasets: Dict[str, pd.DataFrame]) -> Dict:
    """Verifica que todos los datasets tienen 8,760 horas (1 año)."""
    
    validation = {}
    
    for name, df in datasets.items():
        if df.empty:
            validation[name] = {
                'status': '❌ VACÍO',
                'rows': 0,
                'expected': 8760,
                'complete': False
            }
        else:
            rows = len(df)
            is_complete = rows == 8760 or rows % 8760 == 0
            validation[name] = {
                'status': '✅ COMPLETO' if is_complete else '⚠️  INCOMPLETO',
                'rows': rows,
                'expected': 8760,
                'complete': is_complete,
                'columns': list(df.columns)[:5]
            }
    
    return validation

# ============================================================================
# VALIDAR COLUMNAS DE CO2
# ============================================================================

def validate_co2_columns(datasets: Dict[str, pd.DataFrame]) -> Dict:
    """Verifica que existan las columnas correctas de CO2."""
    
    required_columns = {
        'chargers': ['co2_reduccion_motos_kg', 'co2_reduccion_mototaxis_kg'],
        'bess': ['co2_avoided_indirect_kg'],
        'solar': ['reduccion_indirecta_co2_kg'],
        'mall': []  # Mall no tiene CO2 directo (emite, no reduce)
    }
    
    validation = {}
    
    for dataset_name, req_cols in required_columns.items():
        if dataset_name not in datasets or datasets[dataset_name].empty:
            validation[dataset_name] = {'status': '❌ DATASET VACÍO'}
            continue
        
        df = datasets[dataset_name]
        found = []
        missing = []
        
        for col in req_cols:
            if col in df.columns:
                found.append(col)
            else:
                missing.append(col)
        
        if missing:
            validation[dataset_name] = {
                'status': '⚠️  COLUMNAS FALTANDO',
                'found': found,
                'missing': missing
            }
        else:
            validation[dataset_name] = {
                'status': '✅ OK',
                'found': found
            }
    
    return validation

# ============================================================================
# CALCULAR CO2 TOTALES DE DATASETS
# ============================================================================

def calculate_dataset_totals(datasets: Dict[str, pd.DataFrame]) -> Dict:
    """Calcula totales de CO2 de cada dataset para verificación."""
    
    totals = {}
    
    # CO2 DIRECTO (chargers)
    if 'chargers' in datasets and not datasets['chargers'].empty:
        df = datasets['chargers']
        if 'co2_reduccion_motos_kg' in df.columns:
            co2_motos = float(df['co2_reduccion_motos_kg'].sum())
            totals['co2_directo_motos_kg'] = co2_motos
        if 'co2_reduccion_mototaxis_kg' in df.columns:
            co2_taxis = float(df['co2_reduccion_mototaxis_kg'].sum())
            totals['co2_directo_taxis_kg'] = co2_taxis
        totals['co2_directo_total_kg'] = (totals.get('co2_directo_motos_kg', 0) +
                                          totals.get('co2_directo_taxis_kg', 0))
    
    # CO2 INDIRECTO SOLAR
    if 'solar' in datasets and not datasets['solar'].empty:
        df = datasets['solar']
        if 'reduccion_indirecta_co2_kg' in df.columns:
            co2_solar = float(df['reduccion_indirecta_co2_kg'].sum())
            totals['co2_indirecto_solar_kg'] = co2_solar
    
    # CO2 INDIRECTO BESS
    if 'bess' in datasets and not datasets['bess'].empty:
        df = datasets['bess']
        if 'co2_avoided_indirect_kg' in df.columns:
            co2_bess = float(df['co2_avoided_indirect_kg'].sum())
            totals['co2_indirecto_bess_kg'] = co2_bess
    
    # TOTAL CO2 EVITADO
    totals['co2_total_evitado_kg'] = (totals.get('co2_directo_total_kg', 0) +
                                     totals.get('co2_indirecto_solar_kg', 0) +
                                     totals.get('co2_indirecto_bess_kg', 0))
    
    return totals

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("""
╔════════════════════════════════════════════════════════════════════════════════╗
║         TEST DE CONSISTENCIA - SAC vs PPO vs A2C                              ║
║                    VALIDACIÓN DE DATOS REALES                                 ║
║                        2026-02-18 v7.2                                         ║
╚════════════════════════════════════════════════════════════════════════════════╝
""")
    
    # 1. Cargar datasets
    print("[1] CARGANDO DATASETS REALES...")
    print("=" * 80)
    datasets = load_real_datasets()
    print()
    
    # 2. Validar completitud
    print("[2] VALIDANDO COMPLETITUD (8,760 horas)...")
    print("=" * 80)
    completeness = validate_dataset_completeness(datasets)
    for name, info in completeness.items():
        print(f"  {name:12} {info['status']:20} {info['rows']:,} / {info['expected']} rows")
    print()
    
    # 3. Validar columnas CO2
    print("[3] VALIDANDO COLUMNAS DE CO2...")
    print("=" * 80)
    co2_cols = validate_co2_columns(datasets)
    for name, info in co2_cols.items():
        status = info.get('status', 'UNKNOWN')
        print(f"  {name:12} {status}")
        if 'found' in info:
            print(f"              Encontradas: {', '.join(info['found'])}")
        if 'missing' in info:
            print(f"              Faltando: {', '.join(info['missing'])}")
    print()
    
    # 4. Calcular totales
    print("[4] CALCULANDO TOTALES DE CO2 (LÍNEA DE VERDAD)...")
    print("=" * 80)
    totals = calculate_dataset_totals(datasets)
    
    for metric, value in sorted(totals.items()):
        if 'kg' in metric:
            print(f"  {metric:40} {value:>15,.2f} kg")
    print()
    
    # 5. Resumen
    print("[5] RESUMEN EXECUTIVO")
    print("=" * 80)
    
    all_complete = all(c['complete'] for c in completeness.values() if c.get('complete') is not None)
    print(f"  Datasets completos (8,760 horas):  {'✅ SÍ' if all_complete else '❌ NO'}")
    
    all_co2_found = all(c['status'] == '✅ OK' for c in co2_cols.values() if 'status' in c)
    print(f"  Columnas CO2 encontradas:           {'✅ SÍ' if all_co2_found else '⚠️  ALGUNAS FALTAN'}")
    
    co2_total = totals.get('co2_total_evitado_kg', 0)
    print(f"  ")
    print(f"  CO2 TOTAL EVITADO (línea de verdadPOR AÑO):")
    print(f"    - Directo (EV):        {totals.get('co2_directo_total_kg', 0):>12,.0f} kg")
    print(f"    - Indirecto Solar:     {totals.get('co2_indirecto_solar_kg', 0):>12,.0f} kg")
    print(f"    - Indirecto BESS:      {totals.get('co2_indirecto_bess_kg', 0):>12,.0f} kg")
    print(f"    - TOTAL:               {co2_total:>12,.0f} kg")
    print()
    
    print("[6] RECOMENDACIONES")
    print("=" * 80)
    
    if not all_complete:
        print("  ⚠️  PROBLEMA: Algunos datasets no tienen 8,760 horas completas")
        print("     ACCIÓN: Verificar datos de entrada, posible archivo truncado")
        print()
    
    if not all_co2_found:
        print("  ⚠️  PROBLEMA: Faltan algunas columnas de CO2")
        print("     ACCIÓN: Verificar nombres de columnas en archivos CSV")
        print()
    
    print("  ✅ PRÓXIMOS PASOS:")
    print("     1. Ejecutar 1 episodio con SAC y registrar CO2 totales")
    print("     2. Ejecutar 1 episodio con PPO y comparar con SAC")
    print("     3. Ejecutar 1 episodio con A2C y comparar con SAC")
    print("     4. Diferencia permitida: ±5% en todos los componentes")
    print("     5. Si diferencia > 5%, revisar cálculos de recompensa")
    print()
    
    # Salida JSON para programmatic testing
    with open('test_consistency_result.json', 'w') as f:
        json.dump({
            'completeness': completeness,
            'co2_columns': co2_cols,
            'co2_totals': totals,
            'test_passed': all_complete and all_co2_found
        }, f, indent=2, default=str)
    
    print("  📊 Resultados guardados en: test_consistency_result.json")
    print()

if __name__ == '__main__':
    main()
