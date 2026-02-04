#!/usr/bin/env python
"""
Verification script - Confirms all Pylance error fixes are applied
Run: python verify_pylance_fixes.py
"""
from pathlib import Path
import re

def check_file(filepath: Path, pattern: str, description: str) -> bool:
    """Check if a file contains the expected pattern."""
    if not filepath.exists():
        print(f"❌ {filepath.name} - FILE NOT FOUND")
        return False

    content = filepath.read_text()
    if re.search(pattern, content, re.MULTILINE):
        print(f"✅ {filepath.name} - {description}")
        return True
    else:
        print(f"❌ {filepath.name} - {description} NOT FOUND")
        return False

def main():
    print("=" * 80)
    print("PYLANCE FIXES VERIFICATION")
    print("=" * 80)
    print()

    results = []

    # Check 1: transformar_15min_a_hora_usuario.py
    print("1️⃣  Checking transformar_15min_a_hora_usuario.py...")
    result = check_file(
        Path("scripts/transformar_15min_a_hora_usuario.py"),
        r"df\['fecha'\]\s*=\s*df\['datetime'\]\.dt\.date\.astype\(str\)",
        "Pandas .astype(str) for date"
    )
    results.append(result)
    print()

    # Check 2: report_enero_1dia_por_hora.py
    print("2️⃣  Checking report_enero_1dia_por_hora.py...")
    result = check_file(
        Path("scripts/report_enero_1dia_por_hora.py"),
        r"set_xticklabels\(\[str\(i\)\s+for i in range",
        "Matplotlib set_xticklabels list conversion"
    )
    results.append(result)
    print()

    # Check 3: validate_a2c_sac_ppo_alignment.py - Path.mkdir()
    print("3️⃣  Checking validate_a2c_sac_ppo_alignment.py (Path.mkdir)...")
    result = check_file(
        Path("scripts/validate_a2c_sac_ppo_alignment.py"),
        r"agent_dir\.mkdir\(parents=True,\s*exist_ok=True\)\s+if agent_dir\.exists\(\):",
        "Path operations separated from conditional"
    )
    results.append(result)
    print()

    # Check 4: validate_a2c_sac_ppo_alignment.py - return type
    print("4️⃣  Checking validate_a2c_sac_ppo_alignment.py (return type)...")
    result = check_file(
        Path("scripts/validate_a2c_sac_ppo_alignment.py"),
        r"def generate_summary\(.*\)\s*->\s*int:",
        "Return type annotation changed to int"
    )
    results.append(result)
    print()

    # Check 5: pyrightconfig.json
    print("5️⃣  Checking pyrightconfig.json...")
    config_path = Path("pyrightconfig.json")
    if config_path.exists():
        config_content = config_path.read_text()

        # Check that demo/report/validate scripts are in include
        has_demo = "demo_agregacion_15min_a_hora.py" in config_content
        has_report = "report_enero_1dia_por_hora.py" in config_content
        has_transformar = "transformar_15min_a_hora_usuario.py" in config_content
        has_validate = "validate_a2c_sac_ppo_alignment.py" in config_content

        # Check that validate_*.py is NOT in exclude
        no_validate_exclude = "scripts/validate_*.py" not in config_content

        if has_demo and has_report and has_transformar and has_validate and no_validate_exclude:
            print("✅ pyrightconfig.json - Files properly included/excluded")
            results.append(True)
        else:
            print("❌ pyrightconfig.json - Configuration incomplete")
            print(f"   has_demo: {has_demo}, has_report: {has_report}, has_transformar: {has_transformar}, has_validate: {has_validate}")
            print(f"   no_validate_exclude: {no_validate_exclude}")
            results.append(False)
    else:
        print("❌ pyrightconfig.json - FILE NOT FOUND")
        results.append(False)
    print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        print()
        print("Next step: Restart Pylance (Ctrl+Shift+M) to verify 0 errors in Problems panel")
        return 0
    else:
        print(f"❌ SOME CHECKS FAILED ({passed}/{total})")
        print()
        print("Failed checks need investigation before proceeding.")
        return 1

if __name__ == "__main__":
    exit(main())
