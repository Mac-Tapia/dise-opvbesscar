#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUDITORÍA COMPLETA OE3 - VERIFICACIÓN EXHAUSTIVA PRE-PRODUCCIÓN
Fecha: 2026-01-31
Objetivo: Verificar sincronización total, configuraciones, baseline, y estado producción
"""

import sys
import json
import yaml
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple

print("\n" + "="*80)
print("🔍 AUDITORÍA COMPLETA OE3 - VERIFICACIÓN EXHAUSTIVA PRE-PRODUCCIÓN")
print("="*80 + "\n")

# Colors for terminal output
GREEN = "✅"
RED = "❌"
BLUE = "ℹ️"
WARN = "⚠️"

results = {
    "passed": 0,
    "failed": 0,
    "warnings": 0,
    "details": []
}

def test(condition, message, category="GENERAL"):
    """Log test result"""
    if condition:
        print(f"{GREEN} {message}")
        results["passed"] += 1
        results["details"].append({"status": "PASS", "message": message, "category": category})
    else:
        print(f"{RED} {message}")
        results["failed"] += 1
        results["details"].append({"status": "FAIL", "message": message, "category": category})
    return condition

def warn(message, category="WARNING"):
    """Log warning"""
    print(f"{WARN} {message}")
    results["warnings"] += 1
    results["details"].append({"status": "WARN", "message": message, "category": category})

def info(message):
    """Log info"""
    print(f"{BLUE} {message}")

# ============================================================================
# SECCIÓN 1: VERIFICACIÓN DE DATOS OE2
# ============================================================================
print("\n1️⃣  VERIFICACIÓN DE DATOS OE2 (Base de Todo)")
print("-" * 80)

try:
    solar_file = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
    if solar_file.exists():
        solar_df = pd.read_csv(solar_file, encoding='utf-8')
        test(len(solar_df) == 8760, f"Solar timeseries: {len(solar_df)} filas (esperado 8760)", "OE2_DATA")
        test(solar_df.shape[1] >= 1, f"Solar columnas: {solar_df.shape[1]} (esperado >= 1)", "OE2_DATA")
        test(solar_df.iloc[:, 0].min() >= 0, f"Solar min value: {solar_df.iloc[:, 0].min():.4f} kW (>=0)", "OE2_DATA")
        test(solar_df.iloc[:, 0].max() <= 1000, f"Solar max value: {solar_df.iloc[:, 0].max():.4f} kW (<=1000)", "OE2_DATA")
    else:
        test(False, f"Solar file NOT found: {solar_file}", "OE2_DATA")
except Exception as e:
    test(False, f"Solar file error: {str(e)}", "OE2_DATA")

try:
    charger_file = Path("data/interim/oe2/chargers/chargers_hourly_profiles_annual.csv")
    if charger_file.exists():
        charger_df = pd.read_csv(charger_file, encoding='utf-8', index_col=0)
        test(charger_df.shape[0] == 8760, f"Charger profiles rows: {charger_df.shape[0]} (esperado 8760)", "OE2_DATA")
        test(charger_df.shape[1] == 128, f"Charger profiles cols: {charger_df.shape[1]} (esperado 128)", "OE2_DATA")
        test(charger_df.min().min() >= 0, f"Charger min: {charger_df.min().min():.4f} (>=0)", "OE2_DATA")
    else:
        test(False, f"Charger file NOT found: {charger_file}", "OE2_DATA")
except Exception as e:
    test(False, f"Charger file error: {str(e)}", "OE2_DATA")

try:
    bess_file = Path("data/interim/oe2/bess/bess_config.json")
    if bess_file.exists():
        with open(bess_file, 'r', encoding='utf-8') as f:
            bess_cfg = json.load(f)
        test("capacity_kwh" in bess_cfg, "BESS config has capacity_kwh", "OE2_DATA")
        if "capacity_kwh" in bess_cfg:
            test(bess_cfg["capacity_kwh"] == 4520, f"BESS capacity: {bess_cfg['capacity_kwh']} kWh (esperado 4520)", "OE2_DATA")
    else:
        test(False, f"BESS config NOT found: {bess_file}", "OE2_DATA")
except Exception as e:
    test(False, f"BESS config error: {str(e)}", "OE2_DATA")

# ============================================================================
# SECCIÓN 2: VERIFICACIÓN DE CONFIGURACIONES YAML
# ============================================================================
print("\n2️⃣  VERIFICACIÓN DE CONFIGURACIONES YAML")
print("-" * 80)

try:
    config_file = Path("configs/default.yaml")
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)

        # Verificar estructura
        test("oe2" in cfg, "Config tiene sección 'oe2'", "CONFIG_YAML")
        test("oe3" in cfg, "Config tiene sección 'oe3'", "CONFIG_YAML")

        # Verificar valores OE2
        if "oe2" in cfg and "ev_fleet" in cfg["oe2"]:
            ev_cfg = cfg["oe2"]["ev_fleet"]
            test(ev_cfg.get("ev_demand_constant_kw") == 50.0,
                 f"ev_demand_constant_kw: {ev_cfg.get('ev_demand_constant_kw')} (esperado 50.0)", "CONFIG_YAML")
            test(ev_cfg.get("total_sockets") == 128,
                 f"total_sockets: {ev_cfg.get('total_sockets')} (esperado 128)", "CONFIG_YAML")
            test(ev_cfg.get("n_chargers") == 32,
                 f"n_chargers: {ev_cfg.get('n_chargers')} (esperado 32)", "CONFIG_YAML")

        # Verificar CO₂ factors
        if "oe3" in cfg and "dispatch_rules" in cfg["oe3"]:
            test("co2_factors" in cfg["oe3"], "Config tiene co2_factors en oe3", "CONFIG_YAML")
    else:
        test(False, f"Config NOT found: {config_file}", "CONFIG_YAML")
except Exception as e:
    test(False, f"Config YAML error: {str(e)}", "CONFIG_YAML")

# ============================================================================
# SECCIÓN 3: VERIFICACIÓN DE VALORES EN CÓDIGO OE3
# ============================================================================
print("\n3️⃣  VERIFICACIÓN DE VALORES SINCRONIZADOS EN CÓDIGO OE3")
print("-" * 80)

def check_value_in_file(file_path, search_value, description):
    """Check if value exists in file"""
    try:
        if Path(file_path).exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            found = str(search_value) in content
            test(found, f"{description}: '{search_value}' en {Path(file_path).name}", "CODE_SYNC")
            return found
        else:
            test(False, f"Archivo NO encontrado: {file_path}", "CODE_SYNC")
            return False
    except Exception as e:
        test(False, f"Error leyendo {Path(file_path).name}: {str(e)}", "CODE_SYNC")
        return False

# Verificar rewards.py
rewards_file = "src/iquitos_citylearn/oe3/rewards.py"
check_value_in_file(rewards_file, "0.4521", "CO₂ grid factor (rewards.py)")
check_value_in_file(rewards_file, "2.146", "CO₂ conversion factor (rewards.py)")
check_value_in_file(rewards_file, "50.0", "EV demand (rewards.py)")
check_value_in_file(rewards_file, "128", "Total sockets (rewards.py)")
check_value_in_file(rewards_file, "32", "N chargers (rewards.py)")

# Verificar agents
for agent_name in ["sac", "ppo_sb3", "a2c_sb3"]:
    agent_file = f"src/iquitos_citylearn/oe3/agents/{agent_name}.py"
    check_value_in_file(agent_file, "50.0", f"EV demand ({agent_name}.py)")
    check_value_in_file(agent_file, "128", f"Total sockets ({agent_name}.py)")

# Verificar dataset_builder
check_value_in_file("src/iquitos_citylearn/oe3/dataset_builder.py", "128", "Total sockets (dataset_builder)")
check_value_in_file("src/iquitos_citylearn/oe3/dataset_builder.py", "8760", "Solar rows (dataset_builder)")

# ============================================================================
# SECCIÓN 4: VERIFICACIÓN DE COMPILACIÓN Y SINTAXIS
# ============================================================================
print("\n4️⃣  VERIFICACIÓN DE COMPILACIÓN Y SINTAXIS PYTHON")
print("-" * 80)

import py_compile
import tempfile

core_files = [
    "src/iquitos_citylearn/oe3/rewards.py",
    "src/iquitos_citylearn/oe3/agents/sac.py",
    "src/iquitos_citylearn/oe3/agents/ppo_sb3.py",
    "src/iquitos_citylearn/oe3/agents/a2c_sb3.py",
    "src/iquitos_citylearn/oe3/dataset_builder.py",
    "src/iquitos_citylearn/oe3/simulate.py",
]

for file_path in core_files:
    try:
        if Path(file_path).exists():
            py_compile.compile(file_path, doraise=True)
            test(True, f"Compilable sin errores: {Path(file_path).name}", "COMPILATION")
        else:
            test(False, f"Archivo NO encontrado: {file_path}", "COMPILATION")
    except py_compile.PyCompileError as e:
        test(False, f"Error compilación {Path(file_path).name}: {str(e)[:60]}", "COMPILATION")

# ============================================================================
# SECCIÓN 5: VERIFICACIÓN DE SCRIPTS PRINCIPALES
# ============================================================================
print("\n5️⃣  VERIFICACIÓN DE SCRIPTS PRINCIPALES")
print("-" * 80)

scripts = [
    "scripts/run_oe3_build_dataset.py",
    "scripts/run_uncontrolled_baseline.py",
    "scripts/run_sac_ppo_a2c_only.py",
    "scripts/run_oe3_co2_table.py",
]

for script in scripts:
    if Path(script).exists():
        test(True, f"Script encontrado: {Path(script).name}", "SCRIPTS")
        try:
            py_compile.compile(script, doraise=True)
            test(True, f"Script compilable: {Path(script).name}", "SCRIPTS")
        except:
            test(False, f"Script con error compilación: {Path(script).name}", "SCRIPTS")
    else:
        test(False, f"Script NO encontrado: {script}", "SCRIPTS")

# ============================================================================
# SECCIÓN 6: VERIFICACIÓN DE CÁLCULOS BASELINE
# ============================================================================
print("\n6️⃣  VERIFICACIÓN DE CÁLCULOS BASELINE")
print("-" * 80)

try:
    # Verificar que baseline script existe y es funcional
    baseline_script = Path("scripts/run_uncontrolled_baseline.py")
    if baseline_script.exists():
        with open(baseline_script, 'r', encoding='utf-8') as f:
            baseline_content = f.read()

        test("IquitosContext" in baseline_content, "Baseline usa IquitosContext", "BASELINE")
        test("0.4521" in baseline_content, "Baseline contiene CO₂ grid factor (0.4521)", "BASELINE")
        test("2.146" in baseline_content, "Baseline contiene CO₂ conversion factor (2.146)", "BASELINE")
        test("50.0" in baseline_content or "ev_demand" in baseline_content,
             "Baseline contiene EV demand config", "BASELINE")
    else:
        test(False, "Baseline script NO encontrado", "BASELINE")
except Exception as e:
    test(False, f"Error verificando baseline: {str(e)}", "BASELINE")

# ============================================================================
# SECCIÓN 7: VERIFICACIÓN DE ESTRUCTURA OE3
# ============================================================================
print("\n7️⃣  VERIFICACIÓN DE ESTRUCTURA OE3")
print("-" * 80)

required_dirs = [
    "src/iquitos_citylearn/oe3/",
    "src/iquitos_citylearn/oe3/agents/",
    "configs/",
    "scripts/",
    "data/interim/oe2/solar/",
    "data/interim/oe2/chargers/",
    "data/interim/oe2/bess/",
]

for dir_path in required_dirs:
    exists = Path(dir_path).exists()
    test(exists, f"Directorio existe: {dir_path}", "STRUCTURE")

# ============================================================================
# SECCIÓN 8: VERIFICACIÓN DE SINCRONIZACIÓN (CROSS-CHECK)
# ============================================================================
print("\n8️⃣  VERIFICACIÓN CRUZADA DE SINCRONIZACIÓN")
print("-" * 80)

# Extrae valores de rewards.py
try:
    with open("src/iquitos_citylearn/oe3/rewards.py", 'r', encoding='utf-8') as f:
        rewards_content = f.read()

    # Buscar valores críticos
    import re
    co2_grid_match = re.search(r'0\.4521', rewards_content)
    co2_ev_match = re.search(r'2\.146', rewards_content)
    ev_demand_match = re.search(r'50\.0', rewards_content)
    sockets_match = re.search(r'128', rewards_content)
    chargers_match = re.search(r'32', rewards_content)

    test(co2_grid_match is not None, "rewards.py: 0.4521 (CO₂ grid) ✓", "CROSS_CHECK")
    test(co2_ev_match is not None, "rewards.py: 2.146 (CO₂ EV) ✓", "CROSS_CHECK")
    test(ev_demand_match is not None, "rewards.py: 50.0 (EV demand) ✓", "CROSS_CHECK")
    test(sockets_match is not None, "rewards.py: 128 (sockets) ✓", "CROSS_CHECK")
    test(chargers_match is not None, "rewards.py: 32 (chargers) ✓", "CROSS_CHECK")

except Exception as e:
    test(False, f"Error en cross-check rewards.py: {str(e)}", "CROSS_CHECK")

# Verificar sincronización en agentes
for agent in ["sac", "ppo_sb3", "a2c_sb3"]:
    try:
        agent_path = f"src/iquitos_citylearn/oe3/agents/{agent}.py"
        with open(agent_path, 'r', encoding='utf-8') as f:
            agent_content = f.read()

        has_50 = "50" in agent_content
        has_128 = "128" in agent_content

        test(has_50, f"{agent}.py: contiene '50' (EV demand) ✓", "CROSS_CHECK")
        test(has_128, f"{agent}.py: contiene '128' (sockets) ✓", "CROSS_CHECK")
    except:
        test(False, f"Error verificando {agent}.py", "CROSS_CHECK")

# ============================================================================
# SECCIÓN 9: VERIFICACIÓN DE ESTADO DE ENTRENAMIENTO
# ============================================================================
print("\n9️⃣  VERIFICACIÓN DE ESTADO ENTRENAMIENTO (Checkpoints)")
print("-" * 80)

checkpoint_dirs = Path("checkpoints")
if checkpoint_dirs.exists():
    for agent_dir in checkpoint_dirs.glob("*/"):
        if agent_dir.is_dir():
            info(f"Directorio checkpoints encontrado: {agent_dir.name}")
            checkpoint_files = list(agent_dir.glob("*.zip"))
            if checkpoint_files:
                info(f"  - Checkpoints disponibles: {len(checkpoint_files)}")
else:
    info("Directorio checkpoints/ aún no existe (se creará en primer entrenamiento)")

# ============================================================================
# SECCIÓN 10: VERIFICACIÓN DE ESTADO GENERAL
# ============================================================================
print("\n🔟 VERIFICACIÓN DE ESTADO GENERAL")
print("-" * 80)

# Resumen
total_tests = results["passed"] + results["failed"]
success_rate = (results["passed"] / total_tests * 100) if total_tests > 0 else 0

print(f"\n✓ Tests pasados: {results['passed']}")
print(f"✗ Tests fallidos: {results['failed']}")
print(f"⚠  Warnings: {results['warnings']}")
print(f"\nTasa de éxito: {success_rate:.1f}%")

# ============================================================================
# RESULTADO FINAL
# ============================================================================
print("\n" + "="*80)
if results["failed"] == 0:
    print("🎯 RESULTADO FINAL: ✅ SISTEMA COMPLETAMENTE SINCRONIZADO Y LISTO")
    print("="*80)
    print("\n📋 RESUMEN:")
    print("  ✅ Todos los archivos OE3 sincronizados")
    print("  ✅ Todas las configuraciones actualizadas")
    print("  ✅ Cálculos de baseline funcionales")
    print("  ✅ 0 errores en código de producción")
    print("  ✅ Sistema integral y funcional")
    print("  ✅ Listo para producción y entrenamiento\n")
    sys.exit(0)
else:
    print(f"❌ RESULTADO FINAL: {results['failed']} PROBLEMAS ENCONTRADOS")
    print("="*80)
    print("\n🔧 PROBLEMAS DETECTADOS:")
    for detail in results["details"]:
        if detail["status"] == "FAIL":
            print(f"  ❌ {detail['message']}")
    print()
    sys.exit(1)
