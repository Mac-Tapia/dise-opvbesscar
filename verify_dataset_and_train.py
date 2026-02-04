#!/usr/bin/env python3
"""
Verificación rápida del dataset + Lanzar SAC training
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

# Validar Python 3.11
if sys.version_info[:2] != (3, 11):
    print(f"❌ Python {sys.version_info.major}.{sys.version_info.minor} detectado (requiere 3.11)")
    sys.exit(1)

print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} OK")

# Setup paths
project_root = Path(__file__).resolve().parents[0]
os.chdir(project_root)
sys.path.insert(0, str(project_root / "src"))

# ============================================================================
# STEP 1: VERIFICAR DATASET
# ============================================================================
print("\n" + "="*80)
print("STEP 1: VERIFICAR DATASET CITYLEARN")
print("="*80)

dataset_dir = project_root / "data/processed/citylearn/iquitos_ev_mall"
schema_file = dataset_dir / "schema.json"
building_1_csv = dataset_dir / "Building_1.csv"
weather_csv = dataset_dir / "weather.csv"

print(f"\n✓ Dataset dir: {dataset_dir}")
print(f"  Existe: {dataset_dir.exists()}")

print(f"\n✓ schema.json: {schema_file}")
print(f"  Existe: {schema_file.exists()}")
print(f"  Tamaño: {schema_file.stat().st_size if schema_file.exists() else 'N/A'} bytes")

print(f"\n✓ Building_1.csv: {building_1_csv}")
print(f"  Existe: {building_1_csv.exists()}")
print(f"  Tamaño: {building_1_csv.stat().st_size if building_1_csv.exists() else 'N/A'} bytes")

print(f"\n✓ weather.csv: {weather_csv}")
print(f"  Existe: {weather_csv.exists()}")
print(f"  Tamaño: {weather_csv.stat().st_size if weather_csv.exists() else 'N/A'} bytes")

# Contar charger CSVs
charger_files = list(dataset_dir.glob("charger_simulation_*.csv"))
print(f"\n✓ Archivos charger_simulation_*.csv: {len(charger_files)}")
if len(charger_files) > 0:
    print(f"  Primero: {charger_files[0].name}")
    print(f"  Último: {charger_files[-1].name}")

# ============================================================================
# STEP 2: VALIDAR CARGA DE DATASET CON CITYLEARN
# ============================================================================
print("\n" + "="*80)
print("STEP 2: VALIDAR CARGA CITYLEARN")
print("="*80)

try:
    from iquitos_citylearn.oe3.simulate import _make_env

    print(f"\nCargando CityLearn environment desde: {schema_file}")
    env = _make_env(schema_file)

    print(f"✅ Environment cargado correctamente")

    # Verificar buildings
    buildings = getattr(env, "buildings", [])
    print(f"✓ Buildings: {len(buildings)}")

    if buildings:
        b = buildings[0]
        print(f"✓ Building 0: {b.name if hasattr(b, 'name') else 'unnamed'}")

        # Verificar energy_simulation
        energy_sim = getattr(b, 'energy_simulation', None)
        if energy_sim:
            print(f"  ✓ energy_simulation presente")
            nsl = getattr(energy_sim, 'non_shiftable_load', None)
            if nsl and hasattr(nsl, '__len__'):
                print(f"    - non_shiftable_load: {len(nsl)} timesteps")

            solar = getattr(energy_sim, 'solar_generation', None)
            if solar and hasattr(solar, '__len__'):
                solar_sum = sum(solar) if hasattr(solar, '__iter__') else 0
                print(f"    - solar_generation: {len(solar)} timesteps, suma={solar_sum:.0f}")

    # Obtener timesteps
    time_steps = getattr(env, 'time_steps', 0)
    print(f"✓ Time steps: {time_steps}")

    env.close()
    print("\n✅ Dataset VALIDADO EXITOSAMENTE")

except Exception as e:
    print(f"\n❌ Error validando dataset: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# STEP 3: LANZAR ENTRENAMIENTO SAC
# ============================================================================
print("\n" + "="*80)
print("STEP 3: LANZAR ENTRENAMIENTO SAC (5 EPISODIOS)")
print("="*80)

try:
    from scripts._common import load_all
    from iquitos_citylearn.oe3.simulate import simulate

    print("\nCargando configuración...")
    cfg, paths = load_all("configs/default.yaml")
    print("✅ Configuración cargada")

    print("\nParametros SAC:")
    print(f"  Episodes: 5")
    print(f"  Total timesteps: 43,800")
    print(f"  Batch size: 256")
    print(f"  Learning rate: 5e-5")
    print(f"  Device: auto")

    print("\n🚀 Iniciando entrenamiento SAC...")
    print("="*80)

    result = simulate(
        schema_path=schema_file,
        agent_name="sac",
        out_dir=paths.outputs_dir / "oe3_simulations",
        training_dir=paths.checkpoints_dir,
        carbon_intensity_kg_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
        seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
        sac_episodes=5,
        sac_batch_size=256,
        sac_learning_rate=5e-5,
        sac_log_interval=500,
        sac_use_amp=True,
        sac_checkpoint_freq_steps=1000,
        sac_resume_checkpoints=False,
        deterministic_eval=True,
        use_multi_objective=True,
        multi_objective_priority="co2_focus",
        seed=42,
    )

    print("\n" + "="*80)
    print("✅ ENTRENAMIENTO SAC COMPLETADO")
    print("="*80)
    print(f"\nResultados:")
    print(f"  Steps: {result.steps}")
    print(f"  Grid import: {result.grid_import_kwh:,.0f} kWh")
    print(f"  PV generation: {result.pv_generation_kwh:,.0f} kWh")
    print(f"  EV charging: {result.ev_charging_kwh:,.0f} kWh")
    print(f"  CO₂ neto: {result.co2_neto_kg:,.0f} kg")
    print(f"\nArchivos:")
    print(f"  Results: {result.results_path}")
    print(f"  Timeseries: {result.timeseries_path}")

except Exception as e:
    print(f"\n❌ Error en entrenamiento: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ PIPELINE COMPLETADO EXITOSAMENTE\n")
sys.exit(0)
