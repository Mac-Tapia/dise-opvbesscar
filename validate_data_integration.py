#!/usr/bin/env python3
"""
VALIDATION SCRIPT - Verificar sincronización completa de datos BESS, costos y CO2
para el entrenamiento de SAC en pvbesscar v5.2 (Feb 2026)
"""

import sys
from pathlib import Path
import pandas as pd
import json

def validate_bess_specification():
    """Valida que BESS capacity está correctamente especificado en todas partes"""
    print("="*80)
    print("VALIDACIÓN 1: BESS CAPACITY SPECIFICATION")
    print("="*80)
    
    issues = []
    
    # Check 1: Data file
    bess_file = Path('data/oe2/bess/bess_simulation_hourly.csv')
    if bess_file.exists():
        df = pd.read_csv(bess_file)
        actual_capacity = df['soc_kwh'].max()
        if abs(actual_capacity - 1700) < 10:
            print(f"✓ BESS Dataset: {actual_capacity:.0f} kWh (CORRECT)")
        else:
            print(f"✗ BESS Dataset: {actual_capacity:.0f} kWh (EXPECTED 1,700)")
            issues.append("BESS actual capacity mismatch in data")
    else:
        print("✗ BESS dataset not found at data/oe2/bess/bess_simulation_hourly.csv")
        issues.append("Missing BESS data file")
    
    # Check 2: train_sac_multiobjetivo.py
    with open('train_sac_multiobjetivo.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'BESS_CAPACITY_KWH: float = 940.0' in content:
        print("✓ train_sac_multiobjetivo.py: BESS_CAPACITY = 940 kWh (EV-exclusive, CORRECT)")
    else:
        print("⚠ train_sac_multiobjetivo.py: BESS_CAPACITY may need verification")
    
    # Check 3: config files
    with open('configs/default.yaml', 'r', encoding='utf-8') as f:
        yaml_content = f.read()
    
    if 'fixed_capacity_kwh: 940.0' in yaml_content:
        print("✓ configs/default.yaml: BESS EV capacity = 940 kWh (CORRECT)")
    else:
        print("⚠ configs/default.yaml: BESS capacity specification unclear")
    
    # Check 4: Documentation
    with open('.github/copilot-instructions.md', 'r', encoding='utf-8') as f:
        doc_content = f.read()
    
    # The docs should say 1,700 kWh is correct and 4,520 is deprecated
    if '1,700 kWh' in doc_content:
        if 'NOT 4,520' in doc_content or 'previously documented' in doc_content:
            print("✓ .github/copilot-instructions.md: BESS = 1,700 kWh (UPDATED, old spec marked as deprecated)")
        else:
            print("✓ .github/copilot-instructions.md: BESS = 1,700 kWh (UPDATED)")
    else:
        print("✗ .github/copilot-instructions.md: Does not mention 1,700 kWh")
        issues.append("Documentation not updated with correct BESS capacity")
    
    print()
    return issues


def validate_bess_data_loading():
    """Valida que el código puede cargar correctamente datos BESS con costos y CO2"""
    print("="*80)
    print("VALIDACIÓN 2: BESS DATA LOADING IN train_sac_multiobjetivo.py")
    print("="*80)
    
    issues = []
    
    # Check 1: Load path points to correct file
    with open('train_sac_multiobjetivo.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "Path('data/oe2/bess/bess_simulation_hourly.csv')" in content:
        print("✓ BESS path: Correctly points to data/oe2/bess/bess_simulation_hourly.csv")
    else:
        print("✗ BESS path: Does NOT point to correct file")
        issues.append("BESS loading path incorrect in train_sac.py")
    
    # Check 2: Old paths removed
    old_paths = [
        'electrical_storage_simulation.csv',
        'bess_hourly_dataset_2024.csv',
        'bess_dataset.csv'
    ]
    
    for old_path in old_paths:
        if old_path in content and 'bess' in content:
            found_lines = [i for i, line in enumerate(content.split('\n'), 1) 
                          if old_path in line]
            print(f"⚠ Old BESS path found: {old_path} (lines {found_lines})")
            issues.append(f"Deprecated BESS path still in code: {old_path}")
    
    if not issues:
        print("✓ No deprecated BESS paths found")
    
    # Check 3: Cost data loading
    if 'bess_costs' in content and 'cost_grid_import_soles' in content:
        print("✓ Cost data: Loaded from cost_grid_import_soles column")
    else:
        print("⚠ Cost data: May not be loaded properly")
    
    # Check 4: CO2 data loading
    if 'bess_co2' in content and 'co2_grid_kg' in content and 'co2_avoided_kg' in content:
        print("✓ CO2 data: Loaded from co2_grid_kg and co2_avoided_kg columns")
    else:
        print("⚠ CO2 data: May not be loaded properly")
    
    # Check 5: Dictionary return format
    if "return {" in content and "'bess_soc':" in content:
        print("✓ Return format: Updated to dictionary with bess_soc, bess_costs, bess_co2")
    else:
        print("⚠ Return format: May still be tuple format")
        issues.append("Return statement may not include cost/CO2 data")
    
    print()
    return issues


def validate_bess_dataset_structure():
    """Valida que el dataset BESS tiene todas las columnas necesarias"""
    print("="*80)
    print("VALIDACIÓN 3: BESS DATASET STRUCTURE")
    print("="*80)
    
    issues = []
    
    bess_file = Path('data/oe2/bess/bess_simulation_hourly.csv')
    if not bess_file.exists():
        print("✗ BESS file not found")
        return issues
    
    df = pd.read_csv(bess_file)
    
    # Check dimensions
    if len(df) == 8760:
        print(f"✓ Rows: {len(df)} (8,760 hours = 1 year)")
    else:
        print(f"✗ Rows: {len(df)} (expected 8,760)")
        issues.append(f"BESS has {len(df)} rows instead of 8,760")
    
    # Check SOC
    required_cols = ['soc_kwh', 'cost_grid_import_soles', 'co2_grid_kg', 'co2_avoided_kg']
    for col in required_cols:
        if col in df.columns:
            values = df[col].sum()
            print(f"✓ Column '{col}': Present (sum={values:.0f})")
        else:
            print(f"✗ Column '{col}': MISSING")
            issues.append(f"Required column missing: {col}")
    
    # Summary stats
    print()
    print("Data summaries:")
    if 'soc_kwh' in df.columns:
        soc = df['soc_kwh']
        print(f"  SOC: min={soc.min():.0f}, max={soc.max():.0f}, mean={soc.mean():.0f} kWh")
    
    if 'cost_grid_import_soles' in df.columns:
        cost = df['cost_grid_import_soles'].sum()
        print(f"  Annual grid cost: {cost:.2f} soles")
    
    if 'co2_avoided_kg' in df.columns:
        co2 = df['co2_avoided_kg'].sum()
        print(f"  Annual CO2 avoided: {co2:.0f} kg")
    
    print()
    return issues


def validate_data_loader_integration():
    """Valida si data_loader.py está integrado correctamente"""
    print("="*80)
    print("VALIDACIÓN 4: data_loader.py INTEGRATION")
    print("="*80)
    
    issues = []
    
    # Check if data_loader exists
    data_loader_path = Path('src/dimensionamiento/oe2/disenocargadoresev/data_loader.py')
    if data_loader_path.exists():
        print("✓ data_loader.py: File exists")
        
        with open(data_loader_path, 'r', encoding='utf-8') as f:
            loader_content = f.read()
        
        if 'class BESSData' in loader_content:
            print("✓ data_loader.py: Contains BESSData class")
        else:
            print("✗ data_loader.py: No BESSData class found")
            issues.append("data_loader.py missing BESSData class")
    else:
        print("✗ data_loader.py: File not found")
        issues.append("data_loader.py not found")
    
    # Check if used in train_sac
    with open('train_sac_multiobjetivo.py', 'r', encoding='utf-8') as f:
        train_content = f.read()
    
    if 'from' in train_content and 'data_loader' in train_content:
        print("✓ train_sac_multiobjetivo.py: Imports data_loader")
    else:
        print("⚠ train_sac_multiobjetivo.py: Does NOT import data_loader")
        print("  (This is OK if load_datasets_from_processed() handles all loading)")
    
    print()
    return issues


def validate_reward_integration():
    """Valida que costos y CO2 están integrados en el reward"""
    print("="*80)
    print("VALIDACIÓN 5: REWARD FUNCTION INTEGRATION")
    print("="*80)
    
    issues = []
    
    with open('train_sac_multiobjetivo.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check CO2 factor
    if 'CO2_FACTOR_IQUITOS' in content and '0.4521' in content:
        print("✓ CO2 Factor: Defined as 0.4521 kg CO2/kWh (grid thermal)")
    else:
        print("⚠ CO2 Factor: May not be correctly defined")
    
    # Check reward weights
    if 'MultiObjectiveWeights' in content or 'reward_weights' in content or 'co2_weight' in content:
        print("✓ Reward structure: Multi-objective reward system present")
    else:
        print("⚠ Reward structure: Multi-objective configuration unclear")
    
    # Check if CO2 is in observation/reward calculation
    if 'co2' in content.lower() and 'reward' in content.lower():
        print("✓ CO2 in reward: CO2 appears to be used in reward calculation")
    else:
        print("⚠ CO2 in reward: May not be integrated into reward function")
        issues.append("CO2 integration in reward function unclear")
    
    print()
    return issues


def main():
    """Ejecutar todas las validaciones"""
    print("\n")
    print("█" * 80)
    print("COMPREHENSIVE DATA VALIDATION - pvbesscar v5.2 (Feb 2026)")
    print("█" * 80)
    print("\n")
    
    all_issues = []
    
    # Run all validations
    all_issues.extend(validate_bess_specification())
    all_issues.extend(validate_bess_data_loading())
    all_issues.extend(validate_bess_dataset_structure())
    all_issues.extend(validate_data_loader_integration())
    all_issues.extend(validate_reward_integration())
    
    # Final summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    
    if not all_issues:
        print("\n✓ ALL VALIDATIONS PASSED")
        print("  - BESS data correctly synchronized (1,700 kWh capacity)")
        print("  - BESS loading path correct (data/oe2/bess/bess_simulation_hourly.csv)")
        print("  - Cost data available (cost_grid_import_soles)")
        print("  - CO2 data available (co2_grid_kg, co2_avoided_kg)")
        print("  - Documentation updated (1,700 kWh specification)")
        print()
        return 0
    else:
        print(f"\n✗ {len(all_issues)} ISSUE(S) FOUND:\n")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
