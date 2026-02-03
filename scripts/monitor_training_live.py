#!/usr/bin/env python
"""
MONITOREO EN TIEMPO REAL: SAC → PPO → A2C Training Pipeline

Monitorea:
1. Progreso de archivos (result_*.json)
2. Métricas en checkpoints y progress CSV
3. Transiciones automáticas entre agentes
4. Archivos técnicos generados (trace_*.csv, timeseries_*.csv)
"""

from pathlib import Path
import json
import pandas as pd
import time
from datetime import datetime
import sys

def monitor_training():
    """Monitoreo continuo del pipeline de entrenamiento."""

    root = Path("d:\\diseñopvbesscar")
    outputs_dir = root / "outputs" / "oe3_simulations"
    checkpoints_dir = root / "checkpoints"

    agents = ["SAC", "PPO", "A2C"]

    print("\n" + "=" * 80)
    print("MONITOREO EN TIEMPO REAL: SAC → PPO → A2C Training Pipeline")
    print("=" * 80)
    print(f"Hora de inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")

    monitored_files = {
        "SAC": {
            "result": outputs_dir / "result_SAC.json",
            "timeseries": outputs_dir / "timeseries_SAC.csv",
            "trace": outputs_dir / "trace_SAC.csv",
            "checkpoint": checkpoints_dir / "sac" / "sac_final.zip"
        },
        "PPO": {
            "result": outputs_dir / "result_PPO.json",
            "timeseries": outputs_dir / "timeseries_PPO.csv",
            "trace": outputs_dir / "trace_PPO.csv",
            "checkpoint": checkpoints_dir / "ppo" / "ppo_final.zip"
        },
        "A2C": {
            "result": outputs_dir / "result_A2C.json",
            "timeseries": outputs_dir / "timeseries_A2C.csv",
            "trace": outputs_dir / "trace_A2C.csv",
            "checkpoint": checkpoints_dir / "a2c" / "a2c_final.zip"
        }
    }

    iteration = 0
    agents_completed = set()

    while len(agents_completed) < len(agents):
        iteration += 1
        timestamp = datetime.now().strftime("%H:%M:%S")

        print(f"\n[{timestamp}] MONITOREO #{iteration}")
        print("-" * 80)

        for agent in agents:
            files = monitored_files[agent]

            # Verificar si el agent está completado
            result_exists = files["result"].exists()
            timeseries_exists = files["timeseries"].exists()
            trace_exists = files["trace"].exists()

            status_symbol = "✓" if result_exists else "⏳"

            print(f"\n  {status_symbol} {agent} Agent:")

            if result_exists:
                try:
                    with open(files["result"]) as f:
                        result = json.load(f)

                    steps = result.get("steps", 0)
                    co2_net = result.get("co2_neto_kg", 0)
                    solar_avoided = result.get("co2_solar_avoided_kg", 0)
                    grid_import = result.get("grid_import_kwh", 0)

                    print(f"     ✓ Result: {result['agent']} | Steps: {steps:,} | "
                          f"CO2 Net: {co2_net:,.0f} kg | Solar Avoided: {solar_avoided:,.0f} kg")

                    if agent not in agents_completed:
                        agents_completed.add(agent)
                        print(f"     >>> {agent} COMPLETADO EXITOSAMENTE")
                except Exception as e:
                    print(f"     ✗ Error leyendo result: {e}")
            else:
                print(f"     ⏳ Esperando result_{agent}.json...")

            # Mostrar archivos técnicos
            files_status = []
            for file_type in ["timeseries", "trace"]:
                if files[file_type].exists():
                    size = files[file_type].stat().st_size / 1024
                    files_status.append(f"{file_type} ({size:.1f} KB)")

            if files_status:
                print(f"     📊 Archivos técnicos: {', '.join(files_status)}")

        # Mostrar resumen
        print("\n" + "-" * 80)
        print(f"Agentes completados: {len(agents_completed)}/{len(agents)}")

        if len(agents_completed) >= len(agents):
            print("\n" + "=" * 80)
            print("✓ ENTRENAMIENTO COMPLETADO EXITOSAMENTE")
            print("=" * 80)
            break

        # Esperar antes del próximo monitoreo
        time.sleep(30)  # Monitorear cada 30 segundos

    # Mostrar resumen final
    print("\n" + "=" * 80)
    print("RESUMEN FINAL")
    print("=" * 80)

    for agent in agents:
        result_path = monitored_files[agent]["result"]
        if result_path.exists():
            try:
                with open(result_path) as f:
                    result = json.load(f)

                print(f"\n{agent} AGENT:")
                print(f"  Steps: {result.get('steps', 0):,}")
                print(f"  CO2 Indirecto: {result.get('co2_indirecto_kg', 0):,.0f} kg")
                print(f"  CO2 Evitado (Total): {result.get('co2_total_evitado_kg', 0):,.0f} kg")
                print(f"  CO2 Neto: {result.get('co2_neto_kg', 0):,.0f} kg")
                print(f"  Solar Consumed: {result.get('pv_generation_kwh', 0):,.0f} kWh")
                print(f"  Grid Import: {result.get('grid_import_kwh', 0):,.0f} kWh")
            except Exception as e:
                print(f"  Error: {e}")

if __name__ == "__main__":
    try:
        monitor_training()
    except KeyboardInterrupt:
        print("\n\nMonitoreo detenido por usuario")
        sys.exit(0)
