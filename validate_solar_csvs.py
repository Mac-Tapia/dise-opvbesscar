#!/usr/bin/env python
"""
Script de validación para verificar que todos los CSVs de energía solar
se hayan generado correctamente con la estructura esperada.
"""

import pandas as pd
from pathlib import Path

def validate_pv_csvs() -> bool:
    """Valida la estructura y contenido de todos los CSVs solares generados."""
    
    output_dir = Path("data/oe2/Generacionsolar")
    
    print("="*70)
    print("VALIDACIÓN DE DATASETS CSV DE ENERGÍA SOLAR")
    print("="*70)
    print()
    
    # Define las especificaciones esperadas para cada CSV
    specifications = {
        'pv_daily_energy.csv': {
            'columns': ['datetime', 'ac_energy_kwh'],
            'min_rows': 365,
            'description': 'Energía diaria (365 días)'
        },
        'pv_monthly_energy.csv': {
            'columns': ['datetime', 'ac_energy_kwh'],
            'min_rows': 12,
            'description': 'Energía mensual (12 meses)'
        },
        'pv_profile_24h.csv': {
            'columns': ['hour', 'pv_kwh_avg', 'pv_kwh_per_kwp'],
            'min_rows': 24,
            'description': 'Perfil promedio 24h'
        },
        'pv_profile_dia_maxima_generacion.csv': {
            'columns': ['hora', 'ghi_wm2', 'ac_power_kw', 'ac_energy_kwh', 'fecha', 'tipo_dia'],
            'min_rows': 24,
            'description': 'Día con máxima generación'
        },
        'pv_profile_dia_despejado.csv': {
            'columns': ['hora', 'ghi_wm2', 'ac_power_kw', 'ac_energy_kwh', 'fecha', 'tipo_dia'],
            'min_rows': 24,
            'description': 'Día despejado (representativo)'
        },
        'pv_profile_dia_intermedio.csv': {
            'columns': ['hora', 'ghi_wm2', 'ac_power_kw', 'ac_energy_kwh', 'fecha', 'tipo_dia'],
            'min_rows': 24,
            'description': 'Día intermedio (mediana)'
        },
        'pv_profile_dia_nublado.csv': {
            'columns': ['hora', 'ghi_wm2', 'ac_power_kw', 'ac_energy_kwh', 'fecha', 'tipo_dia'],
            'min_rows': 24,
            'description': 'Día nublado (mínima generación)'
        },
        'pv_profile_monthly_hourly.csv': {
            'columns': ['hour', 'mes_01', 'mes_02', 'mes_03', 'mes_04', 'mes_05', 'mes_06',
                       'mes_07', 'mes_08', 'mes_09', 'mes_10', 'mes_11', 'mes_12'],
            'min_rows': 24,
            'description': 'Perfil horario por mes (24h × 12 meses)'
        },
        'pv_candidates_modules.csv': {
            'columns': ['name', 'pmp_w', 'area_m2', 'density_w_m2', 'n_max', 'dc_kw_max'],
            'min_rows': 5,
            'description': 'Módulos fotovoltaicos candidatos (5 opciones)'
        },
        'pv_candidates_inverters.csv': {
            'columns': ['name', 'paco_kw', 'pdco_kw', 'efficiency', 'n_inverters', 'oversize_ratio', 'score'],
            'min_rows': 5,
            'description': 'Inversores candidatos (5 opciones)'
        },
        'pv_candidates_combinations.csv': {
            'columns': ['module_name', 'inverter_name', 'annual_kwh', 'energy_per_m2', 'performance_ratio',
                       'score', 'system_dc_kw', 'area_modules_m2', 'modules_per_string', 'strings_parallel',
                       'total_modules', 'num_inverters'],
            'min_rows': 5,
            'description': 'Combinaciones módulo+inversor (5 opciones)'
        }
    }
    
    # Validar cada CSV
    print("1️⃣  VALIDACIÓN DE EXISTENCIA Y ESTRUCTURA:\n")
    
    results = {}
    all_passed = True
    
    for filename, spec in specifications.items():
        filepath = output_dir / filename
        
        if not filepath.exists():
            print(f"  ❌ {filename:<45} (NO EXISTE)")
            results[filename] = False
            all_passed = False
            continue
        
        try:
            df = pd.read_csv(filepath)
            
            # Verificar columnas
            expected_cols = set(spec['columns'])
            actual_cols = set(df.columns)
            cols_match = expected_cols == actual_cols
            
            # Verificar número de filas
            rows_ok = len(df) >= spec['min_rows']
            
            if cols_match and rows_ok:
                size_kb = filepath.stat().st_size / 1024
                print(f"  ✓ {filename:<45} ({len(df):>3} filas × {len(df.columns):>2} cols | {size_kb:>7.2f} KB)")
                results[filename] = True
            else:
                print(f"  ⚠ {filename:<45} (PARCIAL)")
                if not cols_match:
                    print(f"      → Columnas: {len(actual_cols)} actual vs {len(expected_cols)} esperadas")
                    missing = expected_cols - actual_cols
                    extra = actual_cols - expected_cols
                    if missing:
                        print(f"        Faltantes: {missing}")
                    if extra:
                        print(f"        Extras: {extra}")
                if not rows_ok:
                    print(f"      → Filas: {len(df)} actual vs {spec['min_rows']} mínimas")
                results[filename] = False
                all_passed = False
        
        except Exception as e:
            print(f"  ❌ {filename:<45} (ERROR: {type(e).__name__})")
            results[filename] = False
            all_passed = False
    
    # Resumen
    print("\n" + "="*70)
    print("2️⃣  RESUMEN FINAL:\n")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"  Validaciones exitosas: {passed}/{total}")
    print(f"  Ubicación: {output_dir.resolve()}")
    print()
    
    if all_passed:
        print("  ✅ VALIDACIÓN COMPLETA - Todos los CSVs fueron generados correctamente")
        print("="*70)
        return True
    else:
        print("  ⚠️  VALIDACIÓN CON ADVERTENCIAS - Revisar detalles arriba")
        print("="*70)
        return False
    

if __name__ == "__main__":
    success = validate_pv_csvs()
    exit(0 if success else 1)
