#!/usr/bin/env python
"""Monitor training progress in real time."""

import json
import time
import os
from pathlib import Path
from datetime import datetime

def monitor_training():
    """Monitor SAC/PPO/A2C training progress."""
    checkpoint_dir = Path("analyses/oe3/training/checkpoints")
    summary_file = Path("outputs/oe3/simulations/simulation_summary.json")
    
    print("\n" + "="*70)
    print("MONITOR DE ENTRENAMIENTO EN TIEMPO REAL")
    print("="*70)
    
    while True:
        # Check baseline
        baseline_file = checkpoint_dir / "baseline_metrics.json"
        if baseline_file.exists():
            with open(baseline_file) as f:
                baseline = json.load(f)
            print(f"\n✓ BASELINE calculado:")
            print(f"  • Energía solar: {baseline.get('solar_kwh', 0):,.0f} kWh")
            print(f"  • Importación grid: {baseline.get('net_import_kwh', 0):,.0f} kWh")
            print(f"  • CO2 anual: {baseline.get('co2_kg', 0):,.0f} kg")
        
        # Check SAC progress
        sac_files = sorted(checkpoint_dir.glob("sac_step_*.zip"))
        if sac_files:
            latest_sac = sac_files[-1]
            sac_step = int(latest_sac.stem.split("_")[-1])
            sac_size = latest_sac.stat().st_size / (1024**2)
            print(f"\n✓ SAC entrenamiento:")
            print(f"  • Checkpoint: {latest_sac.name}")
            print(f"  • Step: {sac_step:,}")
            print(f"  • Tamaño: {sac_size:.1f} MB")
        
        # Check PPO progress
        ppo_files = sorted(checkpoint_dir.glob("ppo_step_*.zip"))
        if ppo_files:
            latest_ppo = ppo_files[-1]
            ppo_step = int(latest_ppo.stem.split("_")[-1])
            ppo_size = latest_ppo.stat().st_size / (1024**2)
            print(f"\n✓ PPO entrenamiento:")
            print(f"  • Checkpoint: {latest_ppo.name}")
            print(f"  • Step: {ppo_step:,}")
            print(f"  • Tamaño: {ppo_size:.1f} MB")
        
        # Check A2C progress
        a2c_files = sorted(checkpoint_dir.glob("a2c_step_*.zip"))
        if a2c_files:
            latest_a2c = a2c_files[-1]
            a2c_step = int(latest_a2c.stem.split("_")[-1])
            a2c_size = latest_a2c.stat().st_size / (1024**2)
            print(f"\n✓ A2C entrenamiento:")
            print(f"  • Checkpoint: {latest_a2c.name}")
            print(f"  • Step: {a2c_step:,}")
            print(f"  • Tamaño: {a2c_size:.1f} MB")
        
        # Check summary
        if summary_file.exists():
            try:
                with open(summary_file) as f:
                    summary = json.load(f)
                print(f"\n✓ Resumen disponible:")
                print(f"  • Agentes: {', '.join(summary.keys())}")
            except:
                pass
        
        print(f"\n⏱ Próxima verificación en 10s... ({datetime.now().strftime('%H:%M:%S')})")
        print("-" * 70)
        
        time.sleep(10)

if __name__ == "__main__":
    try:
        monitor_training()
    except KeyboardInterrupt:
        print("\n✓ Monitor detenido")
