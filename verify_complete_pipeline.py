#!/usr/bin/env python3
"""
🔍 VERIFICATION SCRIPT - Validación completa del pipeline sincronizado
Ejecuta todas las verificaciones posteriores a las correcciones
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional
import importlib.util

def test_import(module_path: str, item_name: Optional[str] = None) -> bool:
    """Test si un módulo/item puede importarse"""
    try:
        if item_name:
            exec(f"from {module_path} import {item_name}")
        else:
            exec(f"import {module_path}")
        return True
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False

def check_file_exists(path: str) -> bool:
    """Verifica si un archivo existe"""
    exists = Path(path).exists()
    status = "✓ EXISTS" if exists else "✗ MISSING"
    print(f"  {status}: {path}")
    return exists

def run_command(cmd: str, description: str) -> bool:
    """Ejecuta un comando y captura output"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"  ✅ {description}")
            return True
        else:
            print(f"  ❌ {description}")
            if result.stderr:
                print(f"     Error: {result.stderr[:100]}")
            return False
    except Exception as e:
        print(f"  ❌ {description} (Exception: {e})")
        return False

def main():
    print("\n" + "="*80)
    print("🔍 VERIFICATION SCRIPT - Pipeline Syncronization Validation")
    print("="*80 + "\n")

    results = {
        "imports": [],
        "files": [],
        "compilation": [],
        "dependencies": []
    }

    # ========================================================================
    # PHASE 1: Verificar archivos críticos existen
    # ========================================================================
    print("\n📂 PHASE 1: Verificando archivos críticos")
    print("-" * 80)

    critical_files = [
        "src/agents/sac.py",
        "src/agents/ppo_sb3.py",
        "src/agents/a2c_sb3.py",
        "src/citylearnv2/progress/progress.py",
        "src/citylearnv2/progress/metrics_extractor.py",
        "src/citylearnv2/dataset_builder/dataset_builder_consolidated.py",
        "configs/default.yaml",
        "pyproject.toml",
    ]

    for file_path in critical_files:
        exists = check_file_exists(file_path)
        results["files"].append((file_path, exists))

    # ========================================================================
    # PHASE 2: Validar compilación Python
    # ========================================================================
    print("\n🔧 PHASE 2: Validando compilación Python")
    print("-" * 80)

    agent_files = [
        "src/agents/sac.py",
        "src/agents/ppo_sb3.py",
        "src/agents/a2c_sb3.py",
    ]

    for agent_file in agent_files:
        cmd = f"python -m py_compile {agent_file}"
        result = run_command(cmd, f"Compilar {Path(agent_file).name}")
        results["compilation"].append((agent_file, result))

    # ========================================================================
    # PHASE 3: Verificar imports
    # ========================================================================
    print("\n📦 PHASE 3: Verificando imports directos")
    print("-" * 80)

    import_tests = [
        ("src.citylearnv2.progress", "append_progress_row", "Progress module import"),
        ("src.citylearnv2.progress.metrics_extractor", "EpisodeMetricsAccumulator", "Metrics module import"),
        ("src.rewards.rewards", "create_iquitos_reward_weights", "Reward weights factory import"),
        ("src.agents.sac", "SACAgent", "SAC agent import"),
        ("src.agents.ppo_sb3", "PPOAgent", "PPO agent import"),
        ("src.agents.a2c_sb3", "A2CAgent", "A2C agent import"),
    ]

    sys.path.insert(0, str(Path.cwd()))

    for module_path, item, description in import_tests:
        try:
            mod = importlib.import_module(module_path)
            if hasattr(mod, item):
                print(f"  ✅ {description}")
                results["imports"].append((f"{module_path}.{item}", True))
            else:
                print(f"  ❌ {description} - Item not found: {item}")
                results["imports"].append((f"{module_path}.{item}", False))
        except ImportError as e:
            print(f"  ❌ {description} - {str(e)[:60]}")
            results["imports"].append((f"{module_path}.{item}", False))

    # ========================================================================
    # PHASE 4: Verificar dependencias
    # ========================================================================
    print("\n🐍 PHASE 4: Verificando dependencias Python")
    print("-" * 80)

    dependencies = [
        ("yaml", "PyYAML"),
        ("gymnasium", "Gymnasium"),
        ("numpy", "NumPy"),
        ("pandas", "Pandas"),
        ("torch", "PyTorch"),
        ("stable_baselines3", "Stable-Baselines3"),
    ]

    for module_name, display_name in dependencies:
        cmd = f"python -c \"import {module_name}; print('OK')\""
        result = run_command(cmd, f"Package {display_name}")
        results["dependencies"].append((display_name, result))

    # ========================================================================
    # PHASE 5: Dataset Check
    # ========================================================================
    print("\n📊 PHASE 5: Verificando dataset")
    print("-" * 80)

    schema_exists = check_file_exists("data/interim/oe3/schema.json")

    if schema_exists:
        charger_files = list(Path("data/interim/oe3/chargers").glob("*.csv"))
        num_chargers = len(charger_files)
        expected = 128
        if num_chargers == expected:
            print(f"  ✅ Charger files: {num_chargers}/{expected}")
        else:
            print(f"  ⚠️  Charger files: {num_chargers}/{expected} (expected 128)")
    else:
        print(f"  ⚠️  Dataset needs to be generated:")
        print(f"     python -m scripts.run_oe3_build_dataset --config configs/default.yaml")

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "="*80)
    print("📋 VERIFICATION SUMMARY")
    print("="*80 + "\n")

    total_checks = len(results["files"]) + len(results["compilation"]) + len(results["imports"]) + len(results["dependencies"])
    passed_checks = (
        sum(1 for _, r in results["files"] if r) +
        sum(1 for _, r in results["compilation"] if r) +
        sum(1 for _, r in results["imports"] if r) +
        sum(1 for _, r in results["dependencies"] if r)
    )

    print(f"Files verified:        {sum(1 for _, r in results['files'] if r)}/{len(results['files'])} ✓")
    print(f"Compilation passed:    {sum(1 for _, r in results['compilation'] if r)}/{len(results['compilation'])} ✓")
    print(f"Imports verified:      {sum(1 for _, r in results['imports'] if r)}/{len(results['imports'])} ✓")
    print(f"Dependencies checked:  {sum(1 for _, r in results['dependencies'] if r)}/{len(results['dependencies'])} ✓")
    print(f"\nTotal:                 {passed_checks}/{total_checks} checks passed")

    if passed_checks == total_checks:
        print("\n🟢 SYSTEM STATUS: ✅ FULLY SYNCHRONIZED AND READY FOR TRAINING")
        return 0
    else:
        failed_checks = total_checks - passed_checks
        print(f"\n🟡 SYSTEM STATUS: ⚠️  {failed_checks} check(s) failed - review above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
