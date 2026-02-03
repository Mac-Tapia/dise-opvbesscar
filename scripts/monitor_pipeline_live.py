#!/usr/bin/env python
"""
=============================================================================
        🎯 REAL-TIME TRAINING PIPELINE MONITOR - SAC → PPO → A2C
=============================================================================

Monitor automático del pipeline de entrenamiento con actualizaciones en tiempo real.
Sigue el progreso de los 3 agentes RL y reporta métricas clave.
"""

import json
import time
from pathlib import Path
from datetime import datetime
import sys

def format_number(n):
    """Format number with thousands separator"""
    if isinstance(n, float):
        return f"{n:,.2f}"
    return f"{n:,}"

def monitor_training_pipeline():
    """Monitor the training pipeline in real-time"""

    root = Path("d:\\diseñopvbesscar")
    outputs_dir = root / "outputs" / "oe3_simulations"
    progress_dir = root / "checkpoints" / "progress"

    print("\n" + "="*80)
    print("🚀 TRAINING PIPELINE MONITOR - SAC → PPO → A2C")
    print("="*80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")

    agents_status = {
        "SAC": {"status": "monitoring", "completed": False},
        "PPO": {"status": "waiting", "completed": False},
        "A2C": {"status": "waiting", "completed": False},
    }

    checkpoint_counts = {}
    iteration = 0

    while not all(v["completed"] for v in agents_status.values()):
        iteration += 1
        timestamp = datetime.now().strftime("%H:%M:%S")

        print(f"\n[{timestamp}] 📊 Pipeline Status Check #{iteration}")
        print("-" * 80)

        for agent in ["SAC", "PPO", "A2C"]:
            result_path = outputs_dir / f"result_{agent}.json"
            progress_path = progress_dir / f"{agent.lower()}_progress.csv"

            if result_path.exists():
                agents_status[agent]["status"] = "completed"
                agents_status[agent]["completed"] = True

                try:
                    with open(result_path) as f:
                        result = json.load(f)

                    print(f"\n✅ {agent} COMPLETED")
                    print(f"   Steps: {format_number(result.get('steps', 0))}")
                    print(f"   Grid Import: {format_number(result.get('grid_import_kwh', 0))} kWh")
                    print(f"   PV Generation: {format_number(result.get('pv_generation_kwh', 0))} kWh")
                    print(f"   CO2 Net: {format_number(result.get('co2_neto_kg', 0))} kg")
                    print(f"   CO2 Avoided: {format_number(result.get('co2_total_evitado_kg', 0))} kg")

                except Exception as e:
                    print(f"   ✗ Error reading result: {e}")

            elif progress_path.exists():
                try:
                    lines = list(open(progress_path).readlines())
                    current_count = len(lines)

                    prev_count = checkpoint_counts.get(agent, 0)
                    new_entries = current_count - prev_count

                    if agent == "SAC":
                        agents_status[agent]["status"] = "training"
                        print(f"\n🔄 {agent} TRAINING")
                    else:
                        print(f"\n⏳ {agent} WAITING")

                    print(f"   Progress entries: {current_count}")
                    if new_entries > 0:
                        print(f"   New entries: +{new_entries}")

                    if lines:
                        last_line = lines[-1].strip()
                        print(f"   Latest: {last_line[:70]}...")

                    checkpoint_counts[agent] = current_count

                except Exception as e:
                    print(f"   ✗ Error reading progress: {e}")

            else:
                if agent == "SAC":
                    print(f"\n🟠 {agent} (initializing...)")
                elif agents_status.get("SAC", {}).get("completed"):
                    agents_status[agent]["status"] = "initializing"
                    print(f"\n🟠 {agent} (initializing...)")
                else:
                    print(f"\n⏳ {agent} (waiting for {list(agents_status.keys())[list(agents_status.keys()).index(agent)-1]})")

        # Summary
        print("\n" + "-" * 80)
        completed = sum(1 for v in agents_status.values() if v["completed"])
        print(f"Summary: {completed}/3 agents completed")

        if all(v["completed"] for v in agents_status.values()):
            print("\n✅ TRAINING PIPELINE COMPLETED!")
            break

        # Wait before next check
        time.sleep(30)

    print("\n" + "="*80)
    print("🎉 TRAINING COMPLETE!")
    print("="*80)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

if __name__ == "__main__":
    try:
        monitor_training_pipeline()
    except KeyboardInterrupt:
        print("\n\nMonitoring interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nMonitoring error: {e}")
        sys.exit(1)
