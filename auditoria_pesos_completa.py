#!/usr/bin/env python3
"""AUDITORÍA COMPLETA: Verificar que pesos 0.35/0.20/0.30/0.10/0.05 están en TODOS los archivos."""

import re
from pathlib import Path

print("\n" + "="*90)
print("🔍 AUDITORÍA COMPLETA: PESOS SINCRONIZADOS EN TODOS ARCHIVOS")
print("="*90 + "\n")

# Archivos a auditar
files_to_audit = [
    # YAML
    ("Config YAML", Path("configs/default.yaml")),
    
    # Rewards
    ("Rewards.py", Path("src/rewards/rewards.py")),
    
    # Agentes
    ("PPO (train)", Path("train_ppo_multiobjetivo.py")),
    ("A2C (train)", Path("train_a2c_multiobjetivo.py")),
    ("SAC (train)", Path("train_sac_multiobjetivo.py")),
    ("PPO (src/agents)", Path("src/agents/ppo_sb3.py")),
    ("A2C (src/agents)", Path("src/agents/a2c_sb3.py")),
    ("SAC (src/agents)", Path("src/agents/sac.py")),
    
    # Utilities
    ("Agent Utils", Path("src/utils/agent_utils.py")),
]

# Patrones a buscar (valores esperados)
EXPECTED_VALUES = {
    "co2": 0.35,
    "solar": 0.20,
    "ev_satisfaction": 0.30,
    "cost": 0.10,
    "grid_stability": 0.05,
}

print("[PASO 1] VERIFICAR ARCHIVOS\n")

audit_results = {}

for file_label, file_path in files_to_audit:
    if not file_path.exists():
        print(f"❌ {file_label:30s} - ARCHIVO NO ENCONTRADO: {file_path}")
        audit_results[file_label] = {"status": "MISSING", "details": "Archivo no encontrado"}
        continue
    
    print(f"✅ {file_label:30s} - {file_path}")
    
    try:
        with open(file_path) as f:
            content = f.read()
        
        # Buscar valores
        findings = {}
        
        # Buscar CO2 weight
        co2_matches = re.findall(r'co2["\']?\s*[:=]\s*0[.,](\d+)', content, re.IGNORECASE)
        if co2_matches:
            findings["CO2"] = f"0.{co2_matches[0]}"
        
        # Buscar solar weight
        solar_matches = re.findall(r'solar["\']?\s*[:=]\s*0[.,](\d+)', content, re.IGNORECASE)
        if solar_matches:
            findings["Solar"] = f"0.{solar_matches[0]}"
        
        # Buscar EV weight
        ev_matches = re.findall(r'ev[_]?satisfaction["\']?\s*[:=]\s*0[.,](\d+)', content, re.IGNORECASE)
        if ev_matches:
            findings["EV"] = f"0.{ev_matches[0]}"
        
        # Buscar cost weight
        cost_matches = re.findall(r'cost["\']?\s*[:=]\s*0[.,](\d+)', content, re.IGNORECASE)
        if cost_matches:
            findings["Cost"] = f"0.{cost_matches[0]}"
        
        # Buscar grid weight
        grid_matches = re.findall(r'grid[_]?stability["\']?\s*[:=]\s*0[.,](\d+)', content, re.IGNORECASE)
        if grid_matches:
            findings["Grid"] = f"0.{grid_matches[0]}"
        
        # Verificar valores correctos
        correct_values = {
            "CO2": "0.35",
            "Solar": "0.20",
            "EV": "0.30",
            "Cost": "0.10",
            "Grid": "0.05",
        }
        
        status = "✅ OK"
        issues = []
        
        for param, expected in correct_values.items():
            if param in findings:
                actual = findings[param]
                if actual == expected:
                    print(f"     ✅ {param:10s}: {actual}")
                else:
                    print(f"     ❌ {param:10s}: {actual} (esperado {expected})")
                    issues.append(f"{param}: {actual} (esperado {expected})")
                    status = "❌ MISMATCH"
            else:
                print(f"     ⚠️  {param:10s}: NO ENCONTRADO")
                issues.append(f"{param}: NO ENCONTRADO")
                status = "⚠️  MISSING VALUES"
        
        audit_results[file_label] = {
            "status": status,
            "issues": issues,
            "findings": findings
        }
        
    except Exception as e:
        print(f"     ❌ ERROR: {e}")
        audit_results[file_label] = {"status": "ERROR", "error": str(e)}

# PARTE 2: RESUMEN
print("\n" + "="*90)
print("[PASO 2] RESUMEN AUDITORÍA")
print("="*90 + "\n")

print("📊 ESTADO POR ARCHIVO:\n")

ok_count = 0
mismatch_count = 0
missing_count = 0
error_count = 0

for file_label, result in audit_results.items():
    status = result.get("status", "UNKNOWN")
    
    if "OK" in status:
        ok_count += 1
        print(f"✅ {file_label:30s} - {status}")
    elif "MISMATCH" in status:
        mismatch_count += 1
        issues = result.get("issues", [])
        print(f"❌ {file_label:30s} - {status}")
        for issue in issues:
            print(f"   └─ {issue}")
    elif "MISSING" in status:
        missing_count += 1
        print(f"⚠️  {file_label:30s} - {status}")
    else:
        error_count += 1
        print(f"❌ {file_label:30s} - {status}")

print(f"\n📈 TOTALES:")
print(f"  ✅ OK:          {ok_count}")
print(f"  ❌ Mismatch:    {mismatch_count}")
print(f"  ⚠️  Faltantes:   {missing_count}")
print(f"  ❌ Errores:     {error_count}")

# PARTE 3: VALORES ESPERADOS vs ACTUALES
print("\n" + "="*90)
print("[PASO 3] VALORES ESPERADOS GLOBALES")
print("="*90 + "\n")

print("✅ PESOS ESPERADOS EN TODOS LOS ARCHIVOS:")
print("  • CO2:              0.35")
print("  • Solar:            0.20")
print("  • EV satisfaction:  0.30")
print("  • Cost:             0.10")
print("  • Grid stability:   0.05")
print("  • TOTAL:            1.00\n")

# PARTE 4: RECOMENDACIONES
print("="*90)
print("[PASO 4] RECOMENDACIONES")
print("="*90 + "\n")

if mismatch_count > 0 or missing_count > 0:
    print("⚠️  NECESARIOS CAMBIOS EN:\n")
    for file_label, result in audit_results.items():
        if "MISMATCH" in result.get("status", ""):
            print(f"  ❌ {file_label}")
            for issue in result.get("issues", []):
                print(f"     └─ {issue}")
else:
    print("✅ TODOS LOS ARCHIVOS ESTÁN SINCRONIZADOS CON PESOS CORRECTOS\n")

print("\n" + "="*90 + "\n")
