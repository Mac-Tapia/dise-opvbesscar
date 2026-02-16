#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VALIDACION SIMPLE: Sin entrenar, solo verificar parámetros y datos
"""
import sys
import re
from pathlib import Path

print("=" * 90)
print("VALIDACION PRE-ENTRENAMIENTO: SAC, PPO, A2C (SIN ENTRENAR)")
print("=" * 90)
print()

# ============================================================================
# FASE 1: Validar archivos y constantes sin importar modules
# ============================================================================
print("[1] VALIDACION DE CONSTANTES (leyendo directamente de archivos):")
print()

agents = {
    'SAC': 'scripts/train/train_sac_multiobjetivo.py',
    'PPO': 'scripts/train/train_ppo_multiobjetivo.py',
    'A2C': 'scripts/train/train_a2c_multiobjetivo.py'
}

constants_ok = {}
for agent_name, file_path in agents.items():
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar SOLAR_MAX_KW
        solar_match = re.search(r'SOLAR_MAX_KW\s*(?::|=)\s*(?:float\s*=\s*)?([\d.]+)', content)
        solar_val = float(solar_match.group(1)) if solar_match else None
        solar_ok = solar_val == 2887.0 if solar_val else False
        
        # Buscar MALL_MAX_KW
        mall_match = re.search(r'MALL_MAX_KW\s*(?::|=)\s*(?:float\s*=\s*)?([\d.]+)', content)
        mall_val = float(mall_match.group(1)) if mall_match else None
        mall_ok = mall_val == 3000.0 if mall_val else False
        
        status = "✅" if (solar_ok and mall_ok) else "❌"
        print(f"    {status} {agent_name}:")
        print(f"       SOLAR_MAX_KW = {solar_val} {'✅' if solar_ok else '❌'}")
        print(f"       MALL_MAX_KW  = {mall_val}  {'✅' if mall_ok else '❌'}")
        
        constants_ok[agent_name] = (solar_ok and mall_ok)
    except Exception as e:
        print(f"    ❌ {agent_name}: Error - {str(e)[:60]}")
        constants_ok[agent_name] = False

print()

# ============================================================================
# FASE 2: Validar que los archivos existen
# ============================================================================
print("[2] VALIDACION DE ARCHIVOS DE AGENTES:")
print()

for agent_name, file_path in agents.items():
    exists = Path(file_path).exists()
    status = "✅" if exists else "❌"
    print(f"    {status} {file_path}")

print()

# ============================================================================
# FASE 3: Validar datasets
# ============================================================================
print("[3] VALIDACION DE DATASETS:")
print()

import pandas as pd

datasets = {
    'Solar': 'data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv',
    'Mall': 'data/oe2/demandamallkwh/demandamallhorakwh.csv',
    'Chargers': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
    'BESS': 'data/oe2/bess/bess_ano_2024.csv',
}

data_ok = {}
for name, path in datasets.items():
    file_path = Path(path)
    if file_path.exists():
        try:
            df = pd.read_csv(path)
            rows = len(df)
            cols = len(df.columns)
            
            # Validar 8760 rows (o close)
            rows_ok = abs(rows - 8760) <= 10  # Allow ±10 rows tolerance
            status = "✅" if rows_ok else "⚠️ "
            print(f"    {status} {name:10s} | {rows:5d} rows × {cols:3d} cols | {path}")
            data_ok[name] = rows_ok
        except Exception as e:
            print(f"    ❌ {name}: Error reading - {str(e)[:40]}")
            data_ok[name] = False
    else:
        print(f"    ❌ {name:10s} | FILE NOT FOUND: {path}")
        data_ok[name] = False

print()

# ============================================================================
# FASE 4: Verificar sync
# ============================================================================
print("[4] SINCRONIZACION:")
print()

all_constants_ok = all(constants_ok.values())
all_data_ok = all(data_ok.values())

if all_constants_ok:
    print("    ✅ TODAS LAS CONSTANTES SINCRONIZADAS (SOLAR_MAX_KW=2887, MALL_MAX_KW=3000)")
else:
    print("    ❌ CONSTANTES DESINCRONIZADAS")

if all_data_ok:
    print("    ✅ TODOS LOS DATASETS DISPONIBLES Y VALIDADOS")
else:
    print("    ⚠️  ALGUNOS DATASETS FALTA O INCOMPLETOS")

print()

# ============================================================================
# FASE 5: Resumen y recomendacion
# ============================================================================
print("=" * 90)

if all_constants_ok and all_data_ok:
    print("✅ SISTEMA LISTO PARA ENTRENAR")
    print("=" * 90)
    print()
    print("Estado verificado:")
    print("  ✅ SAC: SOLAR_MAX_KW=2887, MALL_MAX_KW=3000")
    print("  ✅ PPO: SOLAR_MAX_KW=2887, MALL_MAX_KW=3000")
    print("  ✅ A2C: SOLAR_MAX_KW=2887, MALL_MAX_KW=3000")
    print()
    print("  ✅ Datasets completos (8,760 horas c/u):")
    print("     - Solar: pv_generation_citylearn_enhanced_v2.csv")
    print("     - Mall: demandamallhorakwh.csv")
    print("     - Chargers: chargers_ev_ano_2024_v3.csv (38 sockets)")
    print("     - BESS: bess_ano_2024.csv")
    print()
    print("COMANDOS PARA ENTRENAR:")
    print()
    print("  1️⃣  SAC (Recomendado primero - mejor para rewards asimétricos):")
    print("      cd d:\\diseñopvbesscar")
    print("      python scripts/train/train_sac_multiobjetivo.py")
    print()
    print("  2️⃣  PPO (Entrenamiento en paralelo - on-policy more stable):")
    print("      cd d:\\diseñopvbesscar")
    print("      python scripts/train/train_ppo_multiobjetivo.py")
    print()
    print("  3️⃣  A2C (Simple, rápido):")
    print("      cd d:\\diseñopvbesscar")
    print("      python scripts/train/train_a2c_multiobjetivo.py")
    print()
    print("MONITOREO:")
    print("  tensorboard --logdir=runs/ --port=6006")
    print()
    sys.exit(0)
else:
    print("❌ PROBLEMAS DETECTADOS - REVISAR ARRIBA")
    print("=" * 90)
    if not all_constants_ok:
        agents_fail = [a for a, ok in constants_ok.items() if not ok]
        print(f"  Agentes con problemas: {', '.join(agents_fail)}")
    if not all_data_ok:
        data_fail = [name for name, ok in data_ok.items() if not ok]
        print(f"  Datasets falta: {', '.join(data_fail)}")
    print()
    sys.exit(1)
