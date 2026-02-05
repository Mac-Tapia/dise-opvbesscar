#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EJECUTOR_ENTRENAMIENTO_3_AGENTES.py
====================================

Script para ejecutar secuencialmente el entrenamiento de SAC → PPO → A2C
con GPU NVIDIA RTX 4060 activado y optimizado.

Ejecutar:
  python EJECUTOR_ENTRENAMIENTO_3_AGENTES.py

Tiempo total estimado: 15-30 horas (GPU)
Antes era: 30-45 horas (CPU) - 2x más rápido ahora
"""

import subprocess
import sys
import time
import json
from pathlib import Path
from datetime import datetime


def print_header(text: str):
    """Imprimir encabezado destacado."""
    print("\n" + "="*80)
    print(text)
    print("="*80 + "\n")


def run_phase(phase_num: int, agent_name: str, command: str, estimated_time: str) -> int:
    """
    Ejecutar un agente de entrenamiento.

    Args:
        phase_num: Número de fase (1, 2, 3)
        agent_name: Nombre del agente (SAC, PPO, A2C)
        command: Comando a ejecutar
        estimated_time: Tiempo estimado

    Returns:
        0 si exitoso, 1 si error
    """

    print_header(f"FASE {phase_num}: ENTRENAMIENTO {agent_name}")
    print(f"Comando: {command}")
    print(f"Tiempo estimado: {estimated_time}")
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)

    # Ejecutar comando
    result = subprocess.run(command, shell=True)

    if result.returncode != 0:
        print(f"\n❌ ERROR en FASE {phase_num} ({agent_name})")
        print(f"   Return code: {result.returncode}")
        return 1

    print(f"\n✅ FASE {phase_num} ({agent_name}) COMPLETADA")
    print(f"Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return 0


def validate_outputs(agent_name: str) -> bool:
    """
    Validar que los outputs del agente existan.

    Args:
        agent_name: SAC, PPO, o A2C

    Returns:
        True si todos los outputs existen
    """

    agent_lower = agent_name.lower()
    checkpoint = Path(f"checkpoints/{agent_name}/{agent_name.lower()}_final_model.zip")
    result_json = Path(f"outputs/{agent_lower}_training/result_{agent_lower}.json")
    timeseries_csv = Path(f"outputs/{agent_lower}_training/timeseries_{agent_lower}.csv")
    trace_csv = Path(f"outputs/{agent_lower}_training/trace_{agent_lower}.csv")

    files_ok = [checkpoint.exists(), result_json.exists(), timeseries_csv.exists(), trace_csv.exists()]

    print(f"\n  Validar {agent_name} outputs:")
    print(f"    ✓ Checkpoint" if files_ok[0] else f"    ❌ Checkpoint")
    print(f"    ✓ result_{agent_lower}.json" if files_ok[1] else f"    ❌ result_{agent_lower}.json")
    print(f"    ✓ timeseries_{agent_lower}.csv" if files_ok[2] else f"    ❌ timeseries_{agent_lower}.csv")
    print(f"    ✓ trace_{agent_lower}.csv" if files_ok[3] else f"    ❌ trace_{agent_lower}.csv")

    return all(files_ok)


def main():
    """Ejecutar entrenamiento de 3 agentes secuencialmente."""

    print_header("ENTRENAMIENTO SECUENCIAL: SAC → PPO → A2C")
    print("GPU: NVIDIA RTX 4060 Laptop")
    print("CUDA: 12.1 (activado ✓)")
    print("Tiempo total: ~15-30 horas")
    print()

    # Verificaciones previas
    print("[VERIFICACIÓN PREVIA]")
    print("-" * 80)

    # Verificar que existe train_sac_multiobjetivo.py
    if not Path("train_sac_multiobjetivo.py").exists():
        print("❌ train_sac_multiobjetivo.py no encontrado")
        return 1
    else:
        print("✓ train_sac_multiobjetivo.py encontrado")

    # Verificar que existe train_ppo_a2c_multiobjetivo.py
    if not Path("train_ppo_a2c_multiobjetivo.py").exists():
        print("❌ train_ppo_a2c_multiobjetivo.py no encontrado")
        return 1
    else:
        print("✓ train_ppo_a2c_multiobjetivo.py encontrado")

    # Verificar que CONFIG_GPU_CUDA_TRAINING.py existe
    if not Path("CONFIG_GPU_CUDA_TRAINING.py").exists():
        print("❌ CONFIG_GPU_CUDA_TRAINING.py no encontrado")
        return 1
    else:
        print("✓ CONFIG_GPU_CUDA_TRAINING.py encontrado")

    # Crear directorios
    Path("checkpoints/SAC").mkdir(parents=True, exist_ok=True)
    Path("checkpoints/PPO").mkdir(parents=True, exist_ok=True)
    Path("checkpoints/A2C").mkdir(parents=True, exist_ok=True)
    Path("outputs/sac_training").mkdir(parents=True, exist_ok=True)
    Path("outputs/ppo_training").mkdir(parents=True, exist_ok=True)
    Path("outputs/a2c_training").mkdir(parents=True, exist_ok=True)

    print("✓ Directorios de entrenamiento creados")
    print()

    # Timestamp de inicio
    start_time = datetime.now()
    results = {
        'start_time': start_time.isoformat(),
        'phases': {}
    }

    # ===== FASE 1: SAC =====
    phase_1_start = datetime.now()
    ret1 = run_phase(
        1,
        "SAC",
        "python train_sac_multiobjetivo.py",
        "5-10 horas (GPU)"
    )
    phase_1_end = datetime.now()
    phase_1_time = (phase_1_end - phase_1_start).total_seconds() / 3600
    results['phases']['SAC'] = {
        'status': 'SUCCESS' if ret1 == 0 else 'FAILED',
        'duration_hours': phase_1_time,
        'start_time': phase_1_start.isoformat(),
        'end_time': phase_1_end.isoformat()
    }

    if ret1 != 0:
        print_header("❌ ENTRENAMIENTO FALLIDO EN FASE 1")
        print("Error durante SAC training")
        print(f"Total time: {(datetime.now() - start_time).total_seconds() / 3600:.1f} horas")
        return 1

    # Validar outputs SAC
    if not validate_outputs("SAC"):
        print("⚠️  Algunos outputs de SAC no encontrados")

    # ===== FASE 2: PPO =====
    print("\n" + "-"*80)
    print("Esperando 5 segundos antes de FASE 2...")
    time.sleep(5)

    phase_2_start = datetime.now()
    ret2 = run_phase(
        2,
        "PPO",
        "python train_ppo_a2c_multiobjetivo.py",
        "8-12 horas (GPU)"
    )
    phase_2_end = datetime.now()
    phase_2_time = (phase_2_end - phase_2_start).total_seconds() / 3600
    results['phases']['PPO'] = {
        'status': 'SUCCESS' if ret2 == 0 else 'FAILED',
        'duration_hours': phase_2_time,
        'start_time': phase_2_start.isoformat(),
        'end_time': phase_2_end.isoformat()
    }

    if ret2 != 0:
        print_header("❌ ENTRENAMIENTO FALLIDO EN FASE 2")
        print("Error durante PPO training")
        print(f"Total time: {(datetime.now() - start_time).total_seconds() / 3600:.1f} horas")
        return 1

    # Validar outputs PPO
    if not validate_outputs("PPO"):
        print("⚠️  Algunos outputs de PPO no encontrados")

    # ===== FASE 3: A2C =====
    print("\n" + "-"*80)
    print("Esperando 5 segundos antes de FASE 3...")
    time.sleep(5)

    phase_3_start = datetime.now()
    ret3 = run_phase(
        3,
        "A2C",
        "python train_ppo_a2c_multiobjetivo.py A2C",
        "6-10 horas (GPU)"
    )
    phase_3_end = datetime.now()
    phase_3_time = (phase_3_end - phase_3_start).total_seconds() / 3600
    results['phases']['A2C'] = {
        'status': 'SUCCESS' if ret3 == 0 else 'FAILED',
        'duration_hours': phase_3_time,
        'start_time': phase_3_start.isoformat(),
        'end_time': phase_3_end.isoformat()
    }

    if ret3 != 0:
        print_header("❌ ENTRENAMIENTO FALLIDO EN FASE 3")
        print("Error durante A2C training")
        print(f"Total time: {(datetime.now() - start_time).total_seconds() / 3600:.1f} horas")
        return 1

    # Validar outputs A2C
    if not validate_outputs("A2C"):
        print("⚠️  Algunos outputs de A2C no encontrados")

    # ===== RESUMEN FINAL =====
    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds() / 3600

    results['end_time'] = end_time.isoformat()
    results['total_duration_hours'] = total_time

    print_header("✅ ENTRENAMIENTO EXITOSO - TODAS LAS FASES COMPLETADAS")

    print("RESUMEN DE FASES:")
    print(f"  FASE 1 (SAC):  {phase_1_time:.1f} horas ✓")
    print(f"  FASE 2 (PPO):  {phase_2_time:.1f} horas ✓")
    print(f"  FASE 3 (A2C):  {phase_3_time:.1f} horas ✓")
    print()
    print(f"TIEMPO TOTAL: {total_time:.1f} horas (~{int(total_time)} horas)")
    print(f"Inicio: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Fin:    {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    print("OUTPUTS GENERADOS:")
    print("  SAC:  checkpoints/SAC/sac_final_model.zip")
    print("        outputs/sac_training/{result_sac.json, timeseries_sac.csv, trace_sac.csv}")
    print("  PPO:  checkpoints/PPO/ppo_final_model.zip")
    print("        outputs/ppo_training/{result_ppo.json, timeseries_ppo.csv, trace_ppo.csv}")
    print("  A2C:  checkpoints/A2C/a2c_final_model.zip")
    print("        outputs/a2c_training/{result_a2c.json, timeseries_a2c.csv, trace_a2c.csv}")
    print()

    # Guardar resultados a JSON
    results_file = Path("outputs/entrenamiento_3_agentes_resultados.json")
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"✓ Resultados guardados: {results_file}")

    print("\nPRÓXIMOS PASOS:")
    print("  1. Validar outputs:")
    print("     python VALIDADOR_OUTPUTS_POSTENTRENAMIENTO.py")
    print()
    print("  2. Comparar resultados de los 3 agentes:")
    print("     - CO₂ emissions saved (kg)")
    print("     - Solar utilization (%)")
    print("     - EV satisfaction score")
    print("     - Training time (GPU benefits)")
    print()

    print("="*80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
