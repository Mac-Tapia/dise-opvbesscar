#!/usr/bin/env python
"""
SAC Training Launcher - Solución de incompatibilidades NumPy/PIL/matplotlib
"""
import sys
import os

# CRITICAL: Set backend BEFORE any matplotlib import
os.environ['MPLBACKEND'] = 'Agg'

# Force rebuild of numpy to avoid dtype mismatch
import numpy
print(f"✓ NumPy: {numpy.__version__}")

# Test PIL import
try:
    from PIL import Image
    print(f"✓ PIL: {Image.__version__ if hasattr(Image, '__version__') else 'OK'}")
except Exception as e:
    print(f"✗ PIL error: {e}")
    sys.exit(1)

# Test matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')
    print(f"✓ Matplotlib: {matplotlib.__version__}")
except Exception as e:
    print(f"✗ Matplotlib error: {e}")
    sys.exit(1)

# Test stable-baselines3
try:
    from stable_baselines3 import SAC
    print(f"✓ Stable-baselines3: OK")
except Exception as e:
    print(f"✗ Stable-baselines3 error: {e}")
    sys.exit(1)

# Now run the actual training
print("\n[SAC TRAINING] Iniciando entrenamiento SAC...")
print("=" * 80)

from pathlib import Path
from scripts._common import load_all
from iquitos_citylearn.oe3.simulate import simulate

cfg, paths = load_all("configs/default.yaml")

result = simulate(
    schema_path=paths.processed_dir / "citylearn" / cfg["oe3"]["dataset"]["name"] / "schema.json",
    agent_name="sac",
    out_dir=paths.outputs_dir / "oe3",
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

print(f"\n✅ SAC Training Completed!")
print(f"   Agent: {result.agent}")
print(f"   Steps: {result.steps}")
print(f"   CO2 Neto: {result.co2_neto_kg:,.0f} kg")
print(f"   Grid Import: {result.grid_import_kwh:,.0f} kWh")
print(f"   PV Generation: {result.pv_generation_kwh:,.0f} kWh")

print("\n[OUTPUT FILES] Generated:")
print(f"   • {result.results_path}")
print(f"   • {result.timeseries_path}")
