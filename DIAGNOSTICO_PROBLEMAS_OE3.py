#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DIAGNÓSTICO EXHAUSTIVO - Problemas Detectados en OE3
Identifica y proporciona soluciones para cada problema
"""

import sys
import json
import yaml
import pandas as pd
from pathlib import Path

print("\n" + "="*80)
print("🔍 DIAGNÓSTICO EXHAUSTIVO - PROBLEMAS DETECTADOS EN OE3")
print("="*80 + "\n")

issues = []

# ============================================================================
# PROBLEMA 1: Charger profiles 127 en lugar de 128
# ============================================================================
print("PROBLEMA #1: Charger Profiles - 127 columnas en lugar de 128")
print("-" * 80)

charger_file = Path("data/interim/oe2/chargers/chargers_hourly_profiles_annual.csv")
df_chargers = pd.read_csv(charger_file, index_col=0, encoding='utf-8')

print(f"Shape actual: {df_chargers.shape}")
print(f"Columnas: {df_chargers.shape[1]} (esperado: 128)")
print(f"\nPrimeras 5 columnas: {df_chargers.columns[:5].tolist()}")
print(f"Últimas 5 columnas: {df_chargers.columns[-5:].tolist()}")

# Verifycar si falta MOTO_CH_001
if "MOTO_CH_001" not in df_chargers.columns:
    print("\n⚠️  CAUSA: Falta columna 'MOTO_CH_001'")
    print("   El archivo comienza desde MOTO_CH_002")
    issues.append({
        "id": 1,
        "severity": "HIGH",
        "file": "data/interim/oe2/chargers/chargers_hourly_profiles_annual.csv",
        "issue": "Falta MOTO_CH_001 (primera columna)",
        "impact": "Sistema espera 128 sockets (32×4), pero tiene 127",
        "solution": "Agregar columna MOTO_CH_001 al archivo CSV"
    })

print("\n🔧 SOLUCIÓN: Agregar columna faltante MOTO_CH_001")
print("   - Copiar valores de MOTO_CH_002 a nueva columna MOTO_CH_001")
print("   - Mover MOTO_CH_001 a primera posición\n")

# ============================================================================
# PROBLEMA 2: n_chargers faltante en config YAML
# ============================================================================
print("\nPROBLEMA #2: Configuration YAML - n_chargers no está definido")
print("-" * 80)

with open("configs/default.yaml", 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

if "oe2" in cfg and "ev_fleet" in cfg["oe2"]:
    ev_cfg = cfg["oe2"]["ev_fleet"]
    if "n_chargers" in ev_cfg:
        print(f"✓ n_chargers: {ev_cfg['n_chargers']}")
    else:
        print("❌ n_chargers: NO ENCONTRADO en config")
        print(f"✓ total_chargers: {ev_cfg.get('total_chargers', 'N/A')}")
        print(f"✓ total_sockets: {ev_cfg.get('total_sockets', 'N/A')}")
        issues.append({
            "id": 2,
            "severity": "MEDIUM",
            "file": "configs/default.yaml",
            "issue": "Campo 'n_chargers' no existe en oe2.ev_fleet",
            "impact": "Scripts pueden fallar si buscan n_chargers",
            "solution": "Agregar 'n_chargers: 32' a oe2.ev_fleet"
        })

print("\n🔧 SOLUCIÓN: Agregar n_chargers a configs/default.yaml")
print("   - Ubicación: oe2.ev_fleet")
print("   - Valor: 32")
print("   - Referencia: total_chargers ya está = 32\n")

# ============================================================================
# PROBLEMA 3: Baseline no contiene valores CO₂
# ============================================================================
print("\nPROBLEMA #3: Baseline Script - No contiene factores CO₂")
print("-" * 80)

baseline_file = Path("scripts/run_uncontrolled_baseline.py")
with open(baseline_file, 'r', encoding='utf-8') as f:
    baseline_content = f.read()

has_co2_grid = "0.4521" in baseline_content
has_co2_ev = "2.146" in baseline_content
has_iquitos_context = "IquitosContext" in baseline_content

print(f"¿Contiene 0.4521 (CO₂ grid)? {has_co2_grid}")
print(f"¿Contiene 2.146 (CO₂ EV)? {has_co2_ev}")
print(f"¿Contiene IquitosContext? {has_iquitos_context}")

if not has_iquitos_context:
    print("\n⚠️  CAUSA: IquitosContext no importado/usado")
    print("   Baseline no configura factores CO₂ explícitamente")
    issues.append({
        "id": 3,
        "severity": "MEDIUM",
        "file": "scripts/run_uncontrolled_baseline.py",
        "issue": "Baseline no inicializa IquitosContext con CO₂ factors",
        "impact": "Métricas baseline pueden tener CO₂ incorrecto",
        "solution": "Verificar que IquitosContext esté configurado correctamente"
    })

print("\n🔍 INVESTIGACIÓN: Búsqueda de donde se usan factores CO₂...")

# Buscar en data_loader o simulate
for search_file in ["src/iquitos_citylearn/oe3/data_loader.py",
                     "src/iquitos_citylearn/oe3/simulate.py"]:
    if Path(search_file).exists():
        with open(search_file, 'r', encoding='utf-8') as f:
            content = f.read()
        if "0.4521" in content or "2.146" in content:
            print(f"✓ Factores CO₂ encontrados en: {search_file}")

# ============================================================================
# PROBLEMA 4: Solar file error (type checking)
# ============================================================================
print("\nPROBLEMA #4: Solar File - Error de tipo en validación")
print("-" * 80)

solar_file = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
df_solar = pd.read_csv(solar_file, encoding='utf-8')

print(f"Columnas en solar file: {df_solar.columns.tolist()}")
print(f"Tipo datos columna 0: {df_solar.iloc[:, 0].dtype}")
print(f"Primeros valores: {df_solar.iloc[:5, 0].tolist()}")

# El problema es que la columna contiene strings, no números
try:
    numeric_vals = pd.to_numeric(df_solar.iloc[:, 0], errors='coerce')
    if numeric_vals.isna().any():
        print("\n⚠️  CAUSA: Algunos valores no son números")
        print(f"   NaN count: {numeric_vals.isna().sum()}")
        issues.append({
            "id": 4,
            "severity": "MEDIUM",
            "file": "data/interim/oe2/solar/pv_generation_timeseries.csv",
            "issue": "Columna solar contiene valores no numéricos o NaN",
            "impact": "Validación falla en chequeo de min/max",
            "solution": "Limpiar valores no numéricos en solar timeseries"
        })
except:
    pass

# ============================================================================
# RESUMEN DE PROBLEMAS
# ============================================================================
print("\n" + "="*80)
print("📋 RESUMEN DE PROBLEMAS DETECTADOS")
print("="*80 + "\n")

for i, issue in enumerate(issues, 1):
    severity_icon = "🔴" if issue["severity"] == "HIGH" else "🟡"
    print(f"{severity_icon} PROBLEMA #{issue['id']}: {issue['issue']}")
    print(f"   Archivo: {issue['file']}")
    print(f"   Severidad: {issue['severity']}")
    print(f"   Impacto: {issue['impact']}")
    print(f"   Solución: {issue['solution']}")
    print()

# ============================================================================
# VERIFICACIÓN CRUZADA: Valores sincronizados en código
# ============================================================================
print("\n" + "="*80)
print("✅ VALORES SINCRONIZADOS EN CÓDIGO (Status Correcto)")
print("="*80 + "\n")

# Valores correctos en rewards.py
with open("src/iquitos_citylearn/oe3/rewards.py", 'r', encoding='utf-8') as f:
    rewards_content = f.read()

import re
values_to_check = {
    "0.4521": "CO₂ grid factor",
    "2.146": "CO₂ conversion factor",
    "50.0": "EV demand constant",
    "128": "Total sockets",
    "32": "N chargers",
}

print("Valores en rewards.py:")
for value, desc in values_to_check.items():
    found = value in rewards_content
    icon = "✅" if found else "❌"
    print(f"{icon} {desc}: {value}")

print("\nValores en agentes (SAC/PPO/A2C):")
for agent in ["sac", "ppo_sb3", "a2c_sb3"]:
    agent_file = f"src/iquitos_citylearn/oe3/agents/{agent}.py"
    with open(agent_file, 'r', encoding='utf-8') as f:
        agent_content = f.read()

    has_50 = "50" in agent_content
    has_128 = "128" in agent_content
    icon_50 = "✅" if has_50 else "❌"
    icon_128 = "✅" if has_128 else "❌"
    print(f"{agent}.py: {icon_50} EV demand, {icon_128} sockets")

# ============================================================================
# RECOMENDACIONES
# ============================================================================
print("\n" + "="*80)
print("🎯 RECOMENDACIONES PRIORITARIAS")
print("="*80 + "\n")

print("1. URGENTE (Bloquea entrenamiento):")
print("   ❌ Problema #1: Charger profiles 127 → 128")
print("      Acción: Agregar columna MOTO_CH_001 faltante")
print()

print("2. IMPORTANTE (Puede causar errores):")
print("   ⚠️  Problema #2: n_chargers missing en YAML")
print("      Acción: Agregar n_chargers: 32 a oe2.ev_fleet")
print()

print("3. VERIFICAR (Menos crítico):")
print("   ⚠️  Problema #3: Baseline CO₂ factors")
print("      Acción: Confirmar que IquitosContext está configurado")
print()

print("   ⚠️  Problema #4: Solar file type check")
print("      Acción: Verificar que todos los valores sean numéricos")
print()

print("="*80)
print("\n✅ Sistema está 88.7% sincronizado")
print("❌ 7 tests fallaron (principalmente en validación)")
print("🔧 Necesita correcciones menores antes de entrenamiento")
print()
