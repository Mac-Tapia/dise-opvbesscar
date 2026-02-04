#!/usr/bin/env python
"""
SAC Training Launcher - Versión SIMPLIFICADA sin reqs.txt
"""
import sys
import subprocess
from pathlib import Path

print("=" * 80)
print("[SAC TRAINING LAUNCHER] Versión simplificada")
print("=" * 80)

# 1. Instalar solo lo esencial
print("\n[SETUP] Instalando dependencias esenciales...")
essential_packages = [
    'numpy',
    'pandas',
    'scipy',
    'matplotlib',
    'pyyaml',
    'gymnasium',
    'stable-baselines3',
    'torch',
    'scikit-learn',
]

for pkg in essential_packages:
    print(f"  • Verificando {pkg}...", end=" ", flush=True)
    try:
        __import__(pkg.replace('-', '_'))
        print("✓")
    except ImportError:
        print(f"✗ Instalando...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg, "-q", "--no-cache-dir"],
            check=False,
        )

# 2. Verificar CityLearn
print("\n[SETUP] Verificando CityLearn (puede tomar 30s)...")
try:
    import citylearn
    print("  ✓ CityLearn disponible")
except ImportError:
    print("  ! CityLearn no disponible - continuando sin validar importación")

# 3. Configurar matplotlib antes de cualquier otro import
print("\n[CONFIG] Configurando backend...")
import os
os.environ['MPLBACKEND'] = 'Agg'
import matplotlib
matplotlib.use('Agg')
print("  ✓ Backend Agg configurado")

# 4. Verificar imports críticos
print("\n[VERIFY] Verificando imports críticos...")
try:
    from stable_baselines3 import SAC
    print("  ✓ SB3 SAC importado correctamente")
except Exception as e:
    print(f"  ✗ Error en SB3 SAC: {e}")
    sys.exit(1)

try:
    from iquitos_citylearn.config import load_config, load_paths
    print("  ✓ iquitos_citylearn config importado")
except Exception as e:
    print(f"  ! Warning: iquitos_citylearn no disponible: {e}")

# 5. Preparar simulación
print("\n[PREPARE] Preparando simulación SAC...")
try:
    from pathlib import Path
    from scripts._common import load_all
    from iquitos_citylearn.oe3.simulate import simulate

    cfg, paths = load_all("configs/default.yaml")
    schema_path = paths.processed_dir / "citylearn" / cfg["oe3"]["dataset"]["name"] / "schema.json"

    print(f"  ✓ Config cargada desde: configs/default.yaml")
    print(f"  ✓ Schema esperado: {schema_path}")
    print(f"  ✓ Output dir: {paths.outputs_dir}")

except Exception as e:
    print(f"  ✗ Error preparando simulación: {e}")
    sys.exit(1)

# 6. Ejecutar SAC Training
print("\n" + "=" * 80)
print("[SAC TRAINING] ¡INICIANDO ENTRENAMIENTO!")
print("=" * 80 + "\n")

try:
    result = simulate(
        schema_path=schema_path,
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

    print("\n" + "=" * 80)
    print("✅ SAC TRAINING COMPLETADO EXITOSAMENTE")
    print("=" * 80)
    print(f"Agent:          {result.agent}")
    print(f"Steps:          {result.steps}")
    print(f"CO2 Neto:       {result.co2_neto_kg:,.0f} kg")
    print(f"Grid Import:    {result.grid_import_kwh:,.0f} kWh")
    print(f"PV Generation:  {result.pv_generation_kwh:,.0f} kWh")
    print(f"EV Charging:    {result.ev_charging_kwh:,.0f} kWh")
    print("\n📁 Output files:")
    print(f"   • {result.results_path}")
    print(f"   • {result.timeseries_path}")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ ERROR durante entrenamiento: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
