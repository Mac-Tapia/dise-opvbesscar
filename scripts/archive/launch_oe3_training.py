#!/usr/bin/env python3
"""
LANZADOR AUTOMÁTICO DE ENTRENAMIENTO OE3
==========================================

USO: Cuando el usuario diga "LANZA ENTRENAMIENTO"
Ejecutar: python launch_oe3_training.py

Esto ejecutará en orden:
1. Build Dataset (1 min)
2. Baseline (10 seg)
3. Entrenar SAC+PPO+A2C (15-30 min)
4. Tabla Comparativa (<1 seg)

Sistema completamente sincronizado y listo.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_command(cmd, description):
    """Ejecutar comando y reportar resultado."""
    print("\n" + "="*80)
    print(f"▶️  EJECUTANDO: {description}")
    print(f"   Comando: {' '.join(cmd)}")
    print("="*80)

    try:
        subprocess.run(cmd, check=True, capture_output=False, text=True)
        print(f"\n✅ COMPLETADO: {description}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ ERROR en {description}: {e}")
        return False


def main():
    print("\n" + "="*80)
    print("🚀 LANZADOR OE3 TRAINING - SISTEMA SINCRONIZADO")
    print("="*80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Rama: oe3-optimization-sac-ppo")
    print("="*80)

    # Verificar que estamos en directorio correcto
    if not Path("configs/default.yaml").exists():
        print("❌ ERROR: No está en directorio pvbesscar (no encontró configs/default.yaml)")
        return 1

    steps = [
        # PASO 1: Build Dataset
        (
            ["python", "-m", "scripts.run_oe3_build_dataset", "--config", "configs/default.yaml"],
            "PASO 1: BUILD DATASET (1 minuto)",
            "Dataset CityLearn desde OE2 artifacts"
        ),
        # PASO 2: Baseline
        (
            ["python", "-m", "scripts.run_uncontrolled_baseline", "--config", "configs/default.yaml"],
            "PASO 2: BASELINE (10 segundos)",
            "Calcular baseline sin control"
        ),
        # PASO 3: Training
        (
            ["python", "-m", "scripts.run_sac_ppo_a2c_only",
             "--sac-episodes", "1", "--ppo-episodes", "1", "--a2c-episodes", "1"],
            "PASO 3: ENTRENAR (15-30 min con GPU)",
            "Entrenar SAC → PPO → A2C"
        ),
        # PASO 4: Comparación
        (
            ["python", "-m", "scripts.run_oe3_co2_table", "--config", "configs/default.yaml"],
            "PASO 4: TABLA COMPARATIVA (<1 segundo)",
            "Generar tabla CO₂: Baseline vs SAC vs PPO vs A2C"
        ),
    ]

    results = []
    start_time = datetime.now()

    for cmd, title, desc in steps:
        success = run_command(cmd, f"{title} - {desc}")
        results.append((title, success))

        if not success:
            print(f"\n⚠️  Entrenamiento interrumpido en: {title}")
            print("   Revisar logs para diagnosticar")
            break

    # Resumen final
    print("\n" + "="*80)
    print("📊 RESUMEN DEL ENTRENAMIENTO")
    print("="*80)

    for _, (title, success) in enumerate(results, 1):
        status = "✅" if success else "❌"
        print(f"  {status} {title}")

    elapsed = datetime.now() - start_time
    print(f"\nTiempo total: {elapsed}")

    if all(success for _, success in results):
        print("\n🎉 ENTRENAMIENTO COMPLETADO EXITOSAMENTE")
        print("\nResultados disponibles en:")
        print("  - outputs/oe3/simulations/")
        print("  - checkpoints/SAC/, checkpoints/PPO/, checkpoints/A2C/")
        print("  - TABLA COMPARATIVA CO₂: Búsca en stdout arriba ↑")
        return 0
    else:
        print("\n❌ ENTRENAMIENTO INCOMPLETO - Revisar errores arriba")
        return 1


if __name__ == "__main__":
    sys.exit(main())
