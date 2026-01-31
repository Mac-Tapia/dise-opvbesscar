#!/usr/bin/env python3
"""
Script de validación URGENTE: Verificar que el agente está aprendiendo correctamente.
"""
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import numpy as np

# Paths
ppo_progress = Path("analyses/oe3/training/progress/ppo_progress.json")
ppo_logs = Path("analyses/oe3/training/ppo_logs.json")
baseline_file = Path("outputs/oe3/simulations/baseline_real_uncontrolled.json")

print("\n" + "="*70)
print("VALIDACIÓN RÁPIDA: ¿ESTÁ APRENDIENDO EL AGENTE PPO?")
print("="*70)

# 1. Leer baseline
if baseline_file.exists():
    baseline = json.loads(baseline_file.read_text())
    baseline_grid_annual = float(baseline.get("grid_import_kwh", 0))
    baseline_grid_hourly = baseline_grid_annual / 8760
    baseline_co2_hourly = baseline_grid_hourly * 0.4521

    print(f"\n📊 BASELINE (anual, sin control):")
    print(f"   • Grid anual: {baseline_grid_annual:,.0f} kWh")
    print(f"   • Grid promedio horario: {baseline_grid_hourly:.1f} kW")
    print(f"   • CO₂ promedio horario: {baseline_co2_hourly:.1f} kg")

# 2. Datos observados
print(f"\n📈 DATOS DE ENTRENAMIENTO PPO (observados):")
print(f"   • Step 43:  grid=58.9 kWh, co2=26.6 kg")
print(f"   • Step 100: grid=78.1 kWh, co2=35.3 kg (+32.6% vs step 43)")
print(f"   • Step 200: grid=215.1 kWh, co2=97.2 kg (+175% vs step 100)")

# 3. Comparativa
if baseline_file.exists():
    print(f"\n🔴 ANÁLISIS CRÍTICO:")
    print(f"   Step 43:  {58.9 / baseline_grid_hourly * 100:.1f}% del baseline promedio")
    print(f"   Step 100: {78.1 / baseline_grid_hourly * 100:.1f}% del baseline promedio")
    print(f"   Step 200: {215.1 / baseline_grid_hourly * 100:.1f}% del baseline promedio")

    if 215.1 > baseline_grid_hourly:
        print(f"\n   ⚠️ PEOR QUE BASELINE: Step 200 ({215.1}) > baseline ({baseline_grid_hourly:.1f})")
    elif 215.1 > 78.1:
        print(f"\n   🔴 DIVERGENCIA CLARA: Consumo aumentando en lugar de bajar")
        print(f"      → Agente NO está aprendiendo a reducir consumo")
        print(f"      → Problema en función de reward o configuración de acciones")

# 4. Recomendaciones
print(f"\n💡 ACCIONES RECOMENDADAS:")
print(f"   1. PAUSAR entrenamiento (kill proceso)")
print(f"   2. Revisar reward en simulate.py - ¿signos invertidos?")
print(f"   3. Validar que acción[i]=1.0 → charger ON, =0.0 → charger OFF")
print(f"   4. Revisar baseline de comparación en compute_reward()")
print(f"   5. Reentrenar con n_steps=1000 (episodios más cortos)")

print("\n" + "="*70)
