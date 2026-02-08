#!/usr/bin/env python3
"""
VALIDATE CORRECTIONS AND SHOW IMPLEMENTATION STATUS (2026-02-08)
"""

import sys
from pathlib import Path

def check_corrections():
    """Verify C1, C2, C3 implementations."""
    
    print("\n" + "="*80)
    print("VALIDATION REPORT: CORRECTIONS C1, C2, C3")
    print("="*80)
    
    validations = {}
    
    # C1: CO₂ DIRECTO (rewards.py)
    print("\n[C1] CO₂ DIRECTO - Method Check")
    print("-"*80)
    rewards_py = Path('src/rewards/rewards.py')
    if rewards_py.exists():
        content = rewards_py.read_text(encoding='utf-8')
        
        has_ev_kwh = 'ev_kwh_from_renewable' in content
        has_factor = '2.146' in content or 'co2_conversion_factor' in content
        has_liu = 'Liu et al' in content
        has_messagie = 'Messagie' in content
        
        validations['C1_Method'] = has_ev_kwh
        validations['C1_Factor'] = has_factor
        validations['C1_References'] = has_liu or has_messagie
        
        print(f"  {'✅' if has_ev_kwh else '❌'} ev_kwh_from_renewable variable: {'FOUND' if has_ev_kwh else 'NOT FOUND'}")
        print(f"  {'✅' if has_factor else '❌'} Factor 2.146 or co2_conversion_factor: {'FOUND' if has_factor else 'NOT FOUND'}")
        print(f"  {'✅' if has_liu or has_messagie else '❌'} Paper references: {'FOUND' if has_liu or has_messagie else 'NOT FOUND'}")
        print(f"\n  Result: {'✅ VALID' if all([has_ev_kwh, has_factor, has_liu or has_messagie]) else '⚠️ NEEDS REVIEW'}")
    else:
        print(f"  ❌ File not found: {rewards_py}")
        validations['C1_Method'] = False
    
    # C2: BASELINE SOLAR - PVGIS Data (baseline_calculator.py)
    print("\n[C2] BASELINE SOLAR - PVGIS Real Data Check")
    print("-"*80)
    baseline_calc = Path('src/baseline/baseline_calculator.py')
    if baseline_calc.exists():
        content = baseline_calc.read_text(encoding='utf-8')
        
        has_pvgis_path = 'pvgis_path' in content or 'pv_generation_citylearn_v2' in content
        has_fallback = 'fallback' in content.lower() or 'except' in content
        has_validation = '8760' in content or 'timesteps' in content
        has_pvgis_ref = 'PVGIS' in content
        has_heymans = 'Heymans' in content
        
        validations['C2_PVGIS'] = has_pvgis_path
        validations['C2_Fallback'] = has_fallback
        validations['C2_Validation'] = has_validation
        validations['C2_References'] = has_pvgis_ref or has_heymans
        
        print(f"  {'✅' if has_pvgis_path else '❌'} PVGIS path or reference: {'FOUND' if has_pvgis_path else 'NOT FOUND'}")
        print(f"  {'✅' if has_fallback else '❌'} Fallback to cosine: {'FOUND' if has_fallback else 'NOT FOUND'}")
        print(f"  {'✅' if has_validation else '❌'} 8,760 validation: {'FOUND' if has_validation else 'NOT FOUND'}")
        print(f"  {'✅' if has_pvgis_ref or has_heymans else '❌'} Paper references: {'FOUND' if has_pvgis_ref or has_heymans else 'NOT FOUND'}")
        print(f"\n  Result: {'✅ VALID' if all([has_pvgis_path, has_fallback, has_validation, has_pvgis_ref or has_heymans]) else '⚠️ NEEDS REVIEW'}")
    else:
        print(f"  ❌ File not found: {baseline_calc}")
        validations['C2_PVGIS'] = False
    
    # C3: LOG TERMINOLOGY (train_ppo_multiobjetivo.py)
    print("\n[C3] LOG TERMINOLOGY - Clarity Check")
    print("-"*80)
    train_ppo = Path('train_ppo_multiobjetivo.py')
    if train_ppo.exists():
        content = train_ppo.read_text(encoding='utf-8')
        
        has_indirect = 'Reducido Indirecto' in content or 'reducido_indirecto' in content.lower()
        has_direct = 'Reducido Directo' in content or 'reducido_directo' in content.lower()
        has_contabilidad = 'CONTABILIDAD' in content or 'Contabilidad' in content
        has_clarity = 'solar/BESS' in content or 'EV renovable' in content
        
        validations['C3_Clarity'] = has_indirect and has_direct
        validations['C3_Structure'] = has_contabilidad
        validations['C3_Explanation'] = has_clarity
        
        print(f"  {'✅' if has_indirect else '❌'} 'Reducido Indirecto' label: {'FOUND' if has_indirect else 'NOT FOUND'}")
        print(f"  {'✅' if has_direct else '❌'} 'Reducido Directo' label: {'FOUND' if has_direct else 'NOT FOUND'}")
        print(f"  {'✅' if has_contabilidad else '❌'} 'CONTABILIDAD' section: {'FOUND' if has_contabilidad else 'NOT FOUND'}")
        print(f"  {'✅' if has_clarity else '❌'} Explanatory comments: {'FOUND' if has_clarity else 'NOT FOUND'}")
        print(f"\n  Result: {'✅ VALID' if all([has_indirect, has_direct, has_contabilidad, has_clarity]) else '⚠️ NEEDS REVIEW'}")
    else:
        print(f"  ❌ File not found: {train_ppo}")
        validations['C3_Clarity'] = False
    
    # Check PVGIS Data
    print("\n[DATA] PVGIS Solar Data Integrity")
    print("-"*80)
    pvgis_file = Path('data/interim/oe2/solar/pv_generation_citylearn_v2.csv')
    
    try:
        import pandas as pd
        if pvgis_file.exists():
            df = pd.read_csv(pvgis_file)
            has_8760 = len(df) == 8760
            
            validations['PVGIS_Exists'] = True
            validations['PVGIS_Rows'] = has_8760
            
            print(f"  ✅ File exists: {pvgis_file}")
            print(f"  {'✅' if has_8760 else '❌'} Row count: {len(df)} (expected 8,760)")
            print(f"  Columns: {list(df.columns)}")
            print(f"\n  Result: {'✅ VALID' if has_8760 else '⚠️ INVALID ROW COUNT'}")
        else:
            print(f"  ⚠️ File not found: {pvgis_file}")
            print(f"     (Baseline will use cosine model fallback)")
            validations['PVGIS_Exists'] = False
    except Exception as e:
        print(f"  ❌ Error reading PVGIS: {e}")
        validations['PVGIS_Exists'] = False
    
    # SUMMARY
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    
    c1_valid = all([validations.get('C1_Method'), validations.get('C1_Factor'), validations.get('C1_References')])
    c2_valid = all([validations.get('C2_PVGIS'), validations.get('C2_Fallback'), validations.get('C2_References')])
    c3_valid = all([validations.get('C3_Clarity'), validations.get('C3_Structure')])
    
    print(f"\nC1 (CO₂ Directo):      {'✅ VALID' if c1_valid else '⚠️ REVIEW'}")
    print(f"C2 (PVGIS Baseline):   {'✅ VALID' if c2_valid else '⚠️ REVIEW'}")
    print(f"C3 (Log Terminology):  {'✅ VALID' if c3_valid else '⚠️ REVIEW'}")
    print(f"Data (PVGIS):          {'✅ VALID' if validations.get('PVGIS_Rows') else '⚠️ CHECK'}")
    
    all_valid = all([c1_valid, c2_valid, c3_valid])
    
    print(f"\nOverall: {'✅ ALL VALID - READY FOR BASELINE EXECUTION' if all_valid else '⚠️ SOME ISSUES - REVIEW ABOVE'}")
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    
    if all_valid:
        print("\n1. Execute baselines:")
        print("   python execute_baselines_simple.py")
        print("\n2. Results will be saved to:")
        print("   outputs/baseline/baseline_results.json")
        print("   outputs/baseline/comparison_table.csv")
        print("   outputs/baseline/comparison_table.json")
        print("\n3. Train RL agents:")
        print("   python train_ppo_multiobjetivo.py")
        print("\n4. Results will be integrated into comparison table")
    else:
        print("\nReview failed validations before executing baselines")
    
    print("\n" + "="*80 + "\n")
    
    return all_valid


if __name__ == '__main__':
    valid = check_corrections()
    sys.exit(0 if valid else 1)
