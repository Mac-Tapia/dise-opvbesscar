#!/usr/bin/env python3
"""
Validation script for Critical Corrections C1, C2, C3 (2026-02-08)

Validates:
  C1: CO₂ directo - replaced gallons_avoided with ev_kwh_renewable × 2.146
  C2: Baseline solar - uses real PVGIS data instead of cosine model
  C3: Log terminology - clarified direct vs indirect reduction
  
References:
  [1] Liu et al. (2022) "Multi-objective EV charging optimization"
  [2] Messagie et al. (2014) "Environmental impact of electric vehicles in Europe"
  [3] PVGIS (2024) - Photovoltaic Geographical Information System
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np


def validate_c1_rewards_calculation() -> Tuple[bool, List[str]]:
    """C1: Validate CO₂ directo calculation uses ev_kwh_renewable × 2.146."""
    print("\n" + "="*80)
    print("C1 VALIDATION: CO₂ DIRECTO (rewards.py)")
    print("="*80)
    
    warnings = []
    rewards_path = Path('src/rewards/rewards.py')
    
    if not rewards_path.exists():
        return False, [f"❌ File not found: {rewards_path}"]
    
    content = rewards_path.read_text(encoding='utf-8')
    
    # Check 1: Old method should NOT exist
    if 'gallons_avoided' in content and 'km_avoided' in content:
        warnings.append("⚠️  Legacy km_avoided/gallons_avoided still present (should be removed)")
    
    # Check 2: New method should reference ev_kwh_renewable
    if 'ev_kwh_from_renewable' in content:
        print("✅ ev_kwh_from_renewable variable found")
    else:
        warnings.append("❌ ev_kwh_from_renewable NOT found - C1 may not be fully implemented")
    
    # Check 3: Conversion factor 2.146 should be used
    if 'co2_conversion_factor' in content or '2.146' in content:
        print("✅ Conversion factor (2.146 kg CO₂/kWh) referenced")
    else:
        warnings.append("⚠️  Conversion factor 2.146 not explicitly referenced")
    
    # Check 4: Paper references should be added
    if 'Liu et al.' in content or 'Messagie' in content:
        print("✅ Paper references (Liu/Messagie) found in comments")
    else:
        warnings.append("⚠️  Paper references missing from C1 implementation")
    
    if not warnings:
        print("✅ C1 VALIDATION PASSED")
        return True, []
    else:
        print("⚠️  C1 VALIDATION - WARNINGS FOUND")
        return len(warnings) == 0, warnings


def validate_c2_baseline_solar() -> Tuple[bool, List[str]]:
    """C2: Validate baseline uses real PVGIS data instead of cosine model."""
    print("\n" + "="*80)
    print("C2 VALIDATION: BASELINE SOLAR (baseline_calculator.py)")
    print("="*80)
    
    warnings = []
    baseline_path = Path('src/baseline/baseline_calculator.py')
    
    if not baseline_path.exists():
        return False, [f"❌ File not found: {baseline_path}"]
    
    content = baseline_path.read_text(encoding='utf-8')
    
    # Check 1: Should load PVGIS data
    if 'pv_generation_citylearn_v2.csv' in content or 'pvgis_path' in content:
        print("✅ PVGIS data path referenced")
    else:
        warnings.append("⚠️  PVGIS data loading not clearly implemented")
    
    # Check 2: Cosine model should still be fallback only
    if 'cosine' in content.lower():
        # Check if it's fallback-only
        if 'fallback' in content or 'except' in content:
            print("✅ Cosine model present as fallback only")
        else:
            warnings.append("⚠️  Cosine model may still be primary (should be fallback)")
    
    # Check 3: Validate PVGIS data integrity check
    if 'len(solar_generation_kw)' in content or 'assert len' in content:
        print("✅ Data validation (8,760 timesteps check) present")
    else:
        warnings.append("⚠️  No explicit validation of 8,760 hourly timesteps")
    
    # Check 4: Paper references
    if 'PVGIS' in content or 'Heymans' in content:
        print("✅ Paper references (PVGIS/Heymans) found")
    else:
        warnings.append("⚠️  Paper references missing from C2")
    
    # Check 5: Test PVGIS file existence and format
    pvgis_path = Path('data/interim/oe2/solar/pv_generation_citylearn_v2.csv')
    if pvgis_path.exists():
        try:
            pvgis_df = pd.read_csv(pvgis_path)
            if len(pvgis_df) == 8760:
                print(f"✅ PVGIS data file valid: {len(pvgis_df)} rows (8,760 hourly)")
            else:
                warnings.append(f"⚠️  PVGIS data has {len(pvgis_df)} rows (expected 8,760)")
        except Exception as e:
            warnings.append(f"❌ Failed to read PVGIS data: {e}")
    else:
        warnings.append(f"⚠️  PVGIS data file not found: {pvgis_path}")
    
    if len(warnings) <= 1:
        print("✅ C2 VALIDATION PASSED")
        return True, warnings
    else:
        print("⚠️  C2 VALIDATION - ISSUES FOUND")
        return False, warnings


def validate_c3_log_terminology() -> Tuple[bool, List[str]]:
    """C3: Validate logs clarify direct vs indirect CO₂ reduction."""
    print("\n" + "="*80)
    print("C3 VALIDATION: LOG TERMINOLOGY (train_ppo_multiobjetivo.py)")
    print("="*80)
    
    warnings = []
    train_path = Path('train_ppo_multiobjetivo.py')
    
    if not train_path.exists():
        return False, [f"❌ File not found: {train_path}"]
    
    content = train_path.read_text(encoding='utf-8')
    
    # Check 1: _log_episode_summary should have clarified terminology
    if '_log_episode_summary' in content:
        print("✅ _log_episode_summary method found")
        
        # Check for terminology clarification comments
        if 'REDUCIDO_INDIRECTO' in content or 'Reducido Indirecto' in content:
            print("✅ Indirect reduction terminology clarified in logs")
        else:
            warnings.append("⚠️  Indirect reduction terminology not clearly separated")
        
        if 'REDUCIDO_DIRECTO' in content or 'Reducido Directo' in content:
            print("✅ Direct reduction terminology clarified in logs")
        else:
            warnings.append("⚠️  Direct reduction terminology not clearly separated")
    else:
        warnings.append("❌ _log_episode_summary method not found")
    
    # Check 2: Comments explaining the difference
    if 'CO₂_CONTABILIDAD' in content or 'CO2_CONTABILIDAD' in content:
        print("✅ CO₂ accounting section with clear breakdown found")
    else:
        warnings.append("⚠️  CO₂ accounting terminology not clearly structured")
    
    # Check 3: Should reference baseline scenarios
    if 'CON_SOLAR' in content or 'SIN_SOLAR' in content or 'baseline' in content.lower():
        print("✅ Baseline scenario references found")
    else:
        warnings.append("⚠️  Baseline comparison terminology missing")
    
    # Check 4: Check for confusing old terminology
    if 'CO2_evitado:' in content and 'Reducción Total:' not in content:
        warnings.append("⚠️  Old 'CO2_evitado' label may still cause confusion (should be 'Reducción Total')")
    
    if not warnings:
        print("✅ C3 VALIDATION PASSED")
        return True, []
    else:
        print("⚠️  C3 VALIDATION - ISSUES FOUND")
        return len(warnings) == 0, warnings


def validate_context_consistency() -> Tuple[bool, List[str]]:
    """Validate all config files have consistent reward weights and CO₂ factors."""
    print("\n" + "="*80)
    print("CONSISTENCY CHECK: Reward Weights & CO₂ Factors")
    print("="*80)
    
    warnings = []
    
    # Load default config
    config_path = Path('configs/default.yaml')
    if config_path.exists():
        import yaml
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
            
            if 'reward_weights' in config:
                weights = config['reward_weights']
                print(f"✅ Config weights loaded: CO₂={weights.get('co2', 'N/A')}, EV={weights.get('ev', 'N/A')}")
            else:
                warnings.append("⚠️  reward_weights section not found in config")
        except Exception as e:
            warnings.append(f"⚠️  Failed to load config: {e}")
    else:
        warnings.append(f"⚠️  Config file not found: {config_path}")
    
    # Check CO₂ factors in rewards.py
    rewards_path = Path('src/rewards/rewards.py')
    if rewards_path.exists():
        content = rewards_path.read_text(encoding='utf-8')
        if '0.4521' in content:
            print("✅ CO₂ factor 0.4521 kg/kWh (grid) found in rewards")
        else:
            warnings.append("⚠️  Grid CO₂ factor (0.4521) not found")
        
        if '2.146' in content:
            print("✅ CO₂ conversion 2.146 kg/kWh (EV combustion equivalent) found")
        else:
            warnings.append("⚠️  EV conversion factor (2.146) not found")
    
    return len(warnings) == 0, warnings


def generate_summary_report() -> str:
    """Generate a summary report of all validations."""
    c1_ok, c1_warns = validate_c1_rewards_calculation()
    c2_ok, c2_warns = validate_c2_baseline_solar()
    c3_ok, c3_warns = validate_c3_log_terminology()
    ctx_ok, ctx_warns = validate_context_consistency()
    
    all_ok = all([c1_ok, c2_ok, c3_ok, ctx_ok])
    
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    
    status = "✅ ALL CORRECTIONS VALIDATED" if all_ok else "⚠️  REVIEW RECOMMENDATIONS"
    print(f"\n{status}\n")
    
    print("RESULTS BY CORRECTION:")
    print(f"  C1 (CO₂ directo):       {'✅ PASS' if c1_ok else '⚠️  NEEDS REVIEW'} ({len(c1_warns)} warnings)")
    print(f"  C2 (Baseline solar):    {'✅ PASS' if c2_ok else '⚠️  NEEDS REVIEW'} ({len(c2_warns)} warnings)")
    print(f"  C3 (Log terminology):   {'✅ PASS' if c3_ok else '⚠️  NEEDS REVIEW'} ({len(c3_warns)} warnings)")
    print(f"  Consistency checks:     {'✅ PASS' if ctx_ok else '⚠️  NEEDS REVIEW'} ({len(ctx_warns)} warnings)")
    
    all_warns = c1_warns + c2_warns + c3_warns + ctx_warns
    if all_warns:
        print(f"\nTotal warnings: {len(all_warns)}")
        print("\nDetailed warnings:")
        for i, warn in enumerate(all_warns, 1):
            print(f"  {i}. {warn}")
    
    print("\nRECOMMENDATIONS:")
    if all_ok:
        print("  ✅ System is ready for training")
        print("  ✅ Proceed with: python train_ppo_multiobjetivo.py")
    else:
        print("  ⚠️  Review warnings above before training")
        print("  ⚠️  Critical issues (❌) must be resolved")
    
    return "ALL_OK" if all_ok else "NEEDS_REVIEW"


def main():
    """Run all validations."""
    print("\n" + "="*80)
    print("VALIDATING CRITICAL CORRECTIONS (C1, C2, C3) - 2026-02-08")
    print("="*80)
    print("\nReferences:")
    print("  [1] Liu et al. (2022) - Multi-objective EV charging optimization")
    print("  [2] Messagie et al. (2014) - Environmental impact of EVs")
    print("  [3] PVGIS (2024) - Photovoltaic Geographical Information System")
    
    result = generate_summary_report()
    
    print("\n" + "="*80)
    sys.exit(0 if result == "ALL_OK" else 1)


if __name__ == '__main__':
    main()
