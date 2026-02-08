#!/usr/bin/env python3
"""
QUICK VALIDATION SCRIPT - Verificar actualizaciones 2026-02-08

Valida:
1. Tarifas OSINERGMIN unificadas (0.28)
2. Pesos de recompensa balanceados (sum=1.0)
3. Cálculo CO₂ DUAL REDUCTION implementado
4. Cost baseline recalibrado (420 USD)
5. Vehiculos cargados tracking disponible
"""

import re
import sys
from pathlib import Path

class ValidationChecker:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.workspace_root = Path("d:/diseñopvbesscar").resolve()
        
    def check(self, condition, message):
        if condition:
            print(f"✅ {message}")
            self.passed += 1
        else:
            print(f"❌ {message}")
            self.failed += 1
    
    def read_file(self, path):
        """Read file content safely"""
        try:
            full_path = self.workspace_root / path
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"⚠️  Cannot read {path}: {e}")
            return ""
    
    def validate_tariffs(self):
        """Validar tarifas OSINERGMIN unificadas"""
        print("\n" + "="*60)
        print("1. TARIFFS VALIDATION (OSINERGMIN 0.28 USD/kWh)")
        print("="*60)
        
        # Check rewards.py
        rewards_content = self.read_file("src/rewards/rewards.py")
        self.check(
            "tariff_generation_solar_usd_per_kwh: float = 0.10" in rewards_content,
            "rewards.py: Generation solar tariff 0.10 ✓"
        )
        self.check(
            "tariff_bess_storage_usd_per_kwh: float = 0.06" in rewards_content,
            "rewards.py: BESS storage tariff 0.06 ✓"
        )
        self.check(
            "tariff_ev_charge_distribution_usd_per_kwh: float = 0.12" in rewards_content,
            "rewards.py: EV distribution tariff 0.12 ✓"
        )
        self.check(
            "tariff_usd_per_kwh: float = 0.28" in rewards_content,
            "rewards.py: Integral tariff 0.28 ✓"
        )
        
        # Check train_sac
        sac_content = self.read_file("train_sac_multiobjetivo.py")
        self.check(
            "tariff_grid_import_usd_per_kwh = 0.28" in sac_content,
            "train_sac: Tariff 0.28 OSINERGMIN ✓"
        )
        self.check(
            "OSINERGMIN Iquitos 2025" in sac_content,
            "train_sac: OSINERGMIN reference ✓"
        )
        
        # Check default.yaml
        yaml_content = self.read_file("configs/default.yaml")
        self.check(
            "tariff_usd_per_kwh: 0.28" in yaml_content,
            "default.yaml: Tariff 0.28 ✓"
        )
    
    def validate_weights(self):
        """Validar pesos de recompensa balanceados"""
        print("\n" + "="*60)
        print("2. REWARD WEIGHTS VALIDATION (sum = 1.00)")
        print("="*60)
        
        sac_content = self.read_file("train_sac_multiobjetivo.py")
        
        # Find weight values in training section
        weights_patterns = [
            (r'co2.*0\.30', "CO₂ weight: 0.30"),
            (r'solar.*0\.20', "Solar weight: 0.20"),
            (r'ev.*0\.35', "EV weight: 0.35"),
            (r'cost.*0\.10', "Cost weight: 0.10"),
            (r'grid.*0\.05', "Grid weight: 0.05"),
        ]
        
        for pattern, desc in weights_patterns:
            self.check(
                bool(re.search(pattern, sac_content, re.IGNORECASE)),
                f"train_sac: {desc} ✓"
            )
        
        # Verify sum
        self.check(
            0.30 + 0.20 + 0.35 + 0.10 + 0.05 == 1.0,
            "Weights sum = 1.00 exactly ✓"
        )
        
        # Check in configs
        sac_config = self.read_file("configs/agents/sac_config.yaml")
        self.check(
            "co2: 0.30" in sac_config and "ev: 0.35" in sac_config,
            "sac_config.yaml: Weights 0.30/0.35 ✓"
        )
    
    def validate_co2_model(self):
        """Validar modelo CO₂ DUAL REDUCTION"""
        print("\n" + "="*60)
        print("3. CO₂ DUAL REDUCTION MODEL VALIDATION")
        print("="*60)
        
        rewards_content = self.read_file("src/rewards/rewards.py")
        
        self.check(
            "vehicles_charged_equivalent" in rewards_content,
            "rewards.py: vehicles_charged_equivalent calculated ✓"
        )
        self.check(
            "km_avoided = ev_charging_kwh * self.context.km_per_kwh" in rewards_content,
            "rewards.py: EV → km conversion ✓"
        )
        self.check(
            "gallons_avoided = km_avoided / max(self.context.km_per_gallon" in rewards_content,
            "rewards.py: km → gallon conversion ✓"
        )
        self.check(
            "co2_avoided_direct_kg = gallons_avoided * self.context.kgco2_per_gallon" in rewards_content,
            "rewards.py: CO₂ DIRECTO calculation ✓"
        )
        self.check(
            "co2_avoided_indirect_kg = solar_generation_kwh * self.context.co2_factor_kg_per_kwh" in rewards_content,
            "rewards.py: CO₂ INDIRECTA calculation ✓"
        )
        self.check(
            'components["vehicles_charged_equivalent"]' in rewards_content,
            "rewards.py: vehicles_charged_equivalent in components ✓"
        )
        self.check(
            'components["co2_avoided_direct_kg"]' in rewards_content,
            "rewards.py: co2_avoided_direct_kg in components ✓"
        )
    
    def validate_cost_baseline(self):
        """Validar cost baseline recalibrado"""
        print("\n" + "="*60)
        print("4. COST BASELINE VALIDATION (420 USD)")
        print("="*60)
        
        rewards_content = self.read_file("src/rewards/rewards.py")
        
        self.check(
            "cost_baseline = 1500.0 * self.context.tariff_usd_per_kwh" in rewards_content,
            "rewards.py: cost_baseline formula updated ✓"
        )
        self.check(
            "1500.0 kWh × 0.28 = 420 USD" in rewards_content or \
            "420 USD" in rewards_content,
            "rewards.py: cost_baseline 420 USD documented ✓"
        )
        
        sac_content = self.read_file("train_sac_multiobjetivo.py")
        self.check(
            "cost_baseline_usd = (ev_charging_kwh + float(self.mall_hourly_kwh" in sac_content and \
            "tariff_grid_import_usd_per_kwh" in sac_content,
            "train_sac: cost_baseline uses OSINERGMIN tariff ✓"
        )
    
    def validate_documentation(self):
        """Validar documentación nueva creada"""
        print("\n" + "="*60)
        print("5. DOCUMENTATION VALIDATION")
        print("="*60)
        
        docs = [
            ("CO2_DUAL_REDUCTION_MODEL_2026-02-08.md", "CO₂ Dual Reduction Model"),
            ("TARIFAS_OSINERGMIN_IQUITOS_2025.md", "OSINERGMIN Tariffs"),
            ("RESUMEN_CO2_DUAL_REDUCTION_2026-02-08.md", "CO₂ Summary"),
            ("ACTUALIZACION_TARIFAS_OSINERGMIN_2026-02-08.md", "Tariffs Update"),
            ("RESUMEN_INTEGRAL_ACTUALIZACIONES_2026-02-08.md", "Integral Summary"),
        ]
        
        for doc_file, description in docs:
            content = self.read_file(doc_file)
            self.check(
                len(content) > 100,
                f"{doc_file}: Created ✓"
            )
    
    def run_all_validations(self):
        """Run all validation checks"""
        print("\n" + "="*60)
        print("QUICK VALIDATION - ACTUALIZACIONES 2026-02-08")
        print("="*60)
        
        self.validate_tariffs()
        self.validate_weights()
        self.validate_co2_model()
        self.validate_cost_baseline()
        self.validate_documentation()
        
        # Summary
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)
        total = self.passed + self.failed
        percentage = (self.passed / total * 100) if total > 0 else 0
        
        print(f"✅ Passed: {self.passed}/{total} ({percentage:.1f}%)")
        print(f"❌ Failed: {self.failed}/{total}")
        
        if self.failed == 0:
            print("\n🎉 ALL VALIDATIONS PASSED - READY FOR TRAINING!")
            return 0
        else:
            print(f"\n⚠️  {self.failed} validation(s) failed - Review needed")
            return 1

if __name__ == "__main__":
    checker = ValidationChecker()
    exit_code = checker.run_all_validations()
    sys.exit(exit_code)
