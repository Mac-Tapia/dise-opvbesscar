#!/usr/bin/env python
"""
🚀 LANZADOR DE ENTRENAMIENTO OPTIMIZADO - 3 AGENTES RL
======================================================

Ejecuta el pipeline completo SIN INTERRUPCIONES:
1. Dataset (si no existe)
2. Baseline (uncontrolled)
3. SAC Training (50 episodios, batch=512, LR=1.5e-4)
4. PPO Training (50 episodios, n_steps=2048, LR=3e-4)
5. A2C Training (50 episodios, n_steps=5, LR=7e-4)

Duración estimada: 3.5-4 horas
GPU: Auto-detected (CPU fallback)
"""

from __future__ import annotations

import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def main() -> int:
    """Lanza el pipeline de entrenamiento completo."""

    print("\n" + "="*70)
    print("🚀 INICIANDO ENTRENAMIENTO OPTIMIZADO - 3 AGENTES RL")
    print("="*70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"CWD: {Path.cwd()}")
    print("="*70 + "\n")

    try:
        # Verifica disponibilidad de PyTorch/CUDA
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            device = torch.cuda.get_device_name(0) if cuda_available else "CPU"
            print(f"✅ PyTorch: {torch.__version__}")
            print(f"✅ CUDA Available: {cuda_available}")
            print(f"✅ Device: {device}\n")
        except ImportError:
            print("⚠️ PyTorch not available (will use CPU fallback)\n")

        # Carga configuraciones
        from scripts._common import load_all
        from iquitos_citylearn.utils.logging import setup_logging

        setup_logging()
        logger = logging.getLogger(__name__)

        config_path = "configs/default.yaml"
        if not Path(config_path).exists():
            print(f"❌ Configuración no encontrada: {config_path}")
            return 1

        cfg, rp = load_all(config_path)
        logger.info("✅ Configuración cargada")

        # Paso 1: Dataset
        print("\n" + "-"*70)
        print("PASO 1: Construcción de Dataset CityLearn")
        print("-"*70)

        from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset

        dataset_name = cfg["oe3"]["dataset"]["name"]
        processed_dataset_dir = rp.processed_dir / "citylearn" / dataset_name

        if processed_dataset_dir.exists():
            print(f"✅ Dataset ya existe: {processed_dataset_dir}")
            dataset_dir = processed_dataset_dir
        else:
            print(f"🔨 Construyendo dataset: {dataset_name}")
            built = build_citylearn_dataset(
                cfg=cfg,
                _raw_dir=rp.raw_dir,
                interim_dir=rp.interim_dir,
                processed_dir=rp.processed_dir,
            )
            dataset_dir = built.dataset_dir
            print(f"✅ Dataset construido: {dataset_dir}")

        # Paso 2: Baseline (Uncontrolled)
        print("\n" + "-"*70)
        print("PASO 2: Calculando Baseline (Uncontrolled)")
        print("-"*70)

        from iquitos_citylearn.oe3.simulate import simulate_uncontrolled

        simulation_summary_path = rp.outputs_dir / "oe3" / "simulations" / "simulation_summary.json"

        if simulation_summary_path.exists():
            import json
            summary = json.loads(simulation_summary_path.read_text(encoding="utf-8"))
            if "Uncontrolled" in summary:
                print(f"✅ Baseline ya calculado: CO₂={summary['Uncontrolled']['co2_kg']:.1f} kg")
            else:
                print("🔨 Calculando baseline (no existe en summary)")
                simulate_uncontrolled(cfg=cfg, rp=rp)
        else:
            print("🔨 Calculando baseline (primera vez)")
            simulate_uncontrolled(cfg=cfg, rp=rp)

        # Paso 3: Entrenamiento de Agentes
        print("\n" + "-"*70)
        print("PASO 3: ENTRENAMIENTO DE 3 AGENTES (SIN INTERRUPCIONES)")
        print("-"*70)

        from iquitos_citylearn.oe3.simulate import simulate

        print("\n🤖 SAC (Soft Actor-Critic) - Off-Policy")
        print("   Batch: 512, Buffer: 1M, LR: 1.5e-4")
        print("   Esperado: 300-400 minutos, -26% CO₂")
        simulate(cfg=cfg, rp=rp, agent_name="SAC")
        print("✅ SAC Training Complete\n")

        print("\n🤖 PPO (Proximal Policy Optimization) - On-Policy")
        print("   n_steps: 2048, LR: 3e-4, gae_lambda: 0.95")
        print("   Esperado: 200-300 minutos, -29% CO₂")
        simulate(cfg=cfg, rp=rp, agent_name="PPO")
        print("✅ PPO Training Complete\n")

        print("\n🤖 A2C (Advantage Actor-Critic) - Simple")
        print("   n_steps: 5, LR: 7e-4")
        print("   Esperado: 150-200 minutos, -24% CO₂")
        simulate(cfg=cfg, rp=rp, agent_name="A2C")
        print("✅ A2C Training Complete\n")

        # Paso 4: Resultados
        print("\n" + "-"*70)
        print("PASO 4: Generando Tabla Comparativa")
        print("-"*70)

        import json
        results_path = rp.outputs_dir / "oe3" / "simulations" / "simulation_summary.json"
        if results_path.exists():
            results = json.loads(results_path.read_text(encoding="utf-8"))
            print("\n📊 RESULTADOS FINALES:")
            print("\n| Agent | CO₂ (kg) | Reduction | Solar Util |")
            print("|-------|----------|-----------|-----------|")

            baseline_co2 = None
            for agent_name, metrics in results.items():
                if agent_name == "Uncontrolled":
                    baseline_co2 = metrics.get("co2_kg", 0)
                    print(f"| {agent_name:8} | {baseline_co2:8.1f} | 0% | {metrics.get('solar_util', 0):.1f}% |")

            if baseline_co2:
                for agent_name in ["SAC", "PPO", "A2C"]:
                    if agent_name in results:
                        metrics = results[agent_name]
                        co2 = metrics.get("co2_kg", 0)
                        reduction = 100 * (baseline_co2 - co2) / baseline_co2
                        solar_util = metrics.get("solar_util", 0)
                        print(f"| {agent_name:8} | {co2:8.1f} | {reduction:7.1f}% | {solar_util:7.1f}% |")

        print("\n" + "="*70)
        print("✅ ENTRENAMIENTO COMPLETADO SIN INTERRUPCIONES")
        print("="*70)
        print(f"Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")

        return 0

    except KeyboardInterrupt:
        print("\n❌ Entrenamiento interrumpido por el usuario")
        return 130
    except Exception as e:
        print(f"\n❌ Error durante entrenamiento: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
