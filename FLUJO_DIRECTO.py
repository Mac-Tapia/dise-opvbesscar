#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FLUJO DIRECTO: DATASET → SCHEMA → ENTRENAR AGENTES
Ejecutar secuencialmente sin parar.
Respeta estructura del proyecto existente.
"""

import subprocess
import sys
from pathlib import Path

print("\n" + "="*80)
print("FLUJO DIRECTO: DATASET → SCHEMA → ENTRENAR")
print("="*80 + "\n")

# PASO 1: Generar CSV SOC Dinámico
print("[PASO 1] Generando CSV SOC Dinámico...\n")
try:
    result = subprocess.run(
        [sys.executable, "-m", "src.dimensionamiento.oe2.disenocargadoresev.chargers"],
        cwd=Path.cwd(),
        check=True
    )
    print("\n✅ PASO 1 COMPLETADO: CSV SOC Dinámico generado\n")
except Exception as e:
    print(f"\n❌ ERROR PASO 1: {e}\n")
    sys.exit(1)

# PASO 2: Seleccionar agente
print("[PASO 2] Selecciona agente a entrenar:\n")
print("  1) PPO (recomendado)")
print("  2) SAC")
print("  3) A2C\n")

choice = input("Opción (1/2/3): ").strip()

agent_script = {
    "1": "train_ppo_multiobjetivo.py",
    "2": "train_sac_multiobjetivo.py",
    "3": "train_a2c_multiobjetivo.py",
}

if choice not in agent_script:
    print("\n❌ Opción inválida\n")
    sys.exit(1)

script = agent_script[choice]

# PASO 3: Entrenar
print(f"\n[PASO 3] Entrenando {script}...\n")
print("="*80 + "\n")

try:
    result = subprocess.run(
        [sys.executable, script],
        cwd=Path.cwd(),
        check=True
    )
    print("\n" + "="*80)
    print("✅ FLUJO DIRECTO COMPLETADO")
    print("="*80 + "\n")
    print("Resumen:")
    print("  ✅ CSV SOC Dinámico: Generado")
    print("  ✅ Dataset: Construido automáticamente en training")
    print("  ✅ Schema: CityLearn v2 (778-dim o 394-dim)")
    print("  ✅ Agente: Entrenado\n")
except Exception as e:
    print(f"\n❌ ERROR PASO 3: {e}\n")
    sys.exit(1)

