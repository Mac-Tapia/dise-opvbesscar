#!/usr/bin/env python
"""
Direct SAC training - minimal approach
"""
from pathlib import Path
import sys
import os

# Configurar matplotlib PRIMERO
os.environ['MPLBACKEND'] = 'Agg'

# Importar config
from scripts._common import load_all
from iquitos_citylearn.oe3.simulate import simulate

print("\n[SAC TRAINING] Lanzando entrenamiento SAC...")
print("=" * 80)

try:
    # Cargar configuración
    cfg, paths = load_all("configs/default.yaml")

    # Ruta del schema
    schema_path = paths.processed_dir / "citylearn" / cfg["oe3"]["dataset"]["name"] / "schema.json"

    # Ejecutar simulación SAC
    result = simulate(
        schema_path=schema_path,
        agent_name="sac",
        out_dir=paths.outputs_dir / "oe3" / "simulations",
        training_dir=paths.checkpoints_dir,
        carbon_intensity_kg_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
        seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
        sac_episodes=3,
        sac_batch_size=512,
        sac_learning_rate=5e-5,
        sac_checkpoint_freq_steps=1000,
        use_multi_objective=True,
        multi_objective_priority="co2_focus",
    )

    print("\n✅ TRAINING COMPLETED")
    print(f"Agent: {result.agent}")
    print(f"Steps: {result.steps}")
    print(f"CO2 Neto: {result.co2_neto_kg:,.0f} kg")
    print(f"Results: {result.results_path}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
