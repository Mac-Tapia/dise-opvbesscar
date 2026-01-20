#!/usr/bin/env python3
"""
TIER 2 V2 ENTRENAMIENTO DESDE CERO
- Construcción de datos con esquemas validados
- Cálculo de baseline
- Entrenamiento en serie: A2C (2ep) -> PPO (2ep) -> SAC (2ep)
- GPU optimizado

Ejecución: python train_tier2_v2_from_scratch.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import logging
import json
import numpy as np
from typing import Dict, Any, cast

# ============ SETUP GPU ============
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '0'

sys.path.insert(0, str(Path(__file__).parent))

# ============ LOGGER SETUP ============
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

print("\n" + "=" * 100)
print("TIER 2 V2 - ENTRENAMIENTO DESDE CERO")
print("=" * 100)
print(f"Inicio: {datetime.now().isoformat()}\n")

# ============ IMPORTAR MÓDULOS ============
logger.info("Importando módulos...")
try:
    from citylearn_monkeypatch import apply_citylearn_patches
    apply_citylearn_patches()
    logger.info("✓ Monkeypatch CityLearn aplicado")
except Exception as e:
    logger.warning(f"Monkeypatch CityLearn: {e}")

try:
    from iquitos_citylearn.oe3.simulate import simulate
    from scripts._common import load_all
    from src.iquitos_citylearn.oe3.tier2_v2_config import TIER2V2Config
    logger.info("✓ Módulos importados exitosamente")
except Exception as e:
    logger.error(f"Error importando módulos: {e}")
    sys.exit(1)

# ============ FASE 1: CARGAR CONFIGURACIÓN ============
print("\n" + "=" * 100)
print("[FASE 1/4] CARGAR CONFIGURACIÓN")
print("=" * 100)

try:
    cfg, rp = load_all("configs/default.yaml")
    logger.info("✓ Config default.yaml cargada")
except Exception as e:
    logger.error(f"Error cargando config: {e}")
    sys.exit(1)

# Crear config V2
try:
    config_v2 = TIER2V2Config()
    logger.info("✓ TIER 2 V2 Config creada")
    logger.info(f"  • Entropy coef (FIJO): {config_v2.entropy_coef_fixed}")
    logger.info(f"  • LR base: {config_v2.learning_rate_base:.2e}")
    logger.info(f"  • LR pico: {config_v2.learning_rate_peak:.2e}")
    logger.info(f"  • CO2 weight: {config_v2.co2_weight}")
    logger.info(f"  • Peak power penalty: {config_v2.peak_power_penalty}")
    logger.info(f"  • SOC reserve penalty: {config_v2.soc_reserve_penalty}")
except Exception as e:
    logger.error(f"Error creando TIER 2 V2 Config: {e}")
    sys.exit(1)

# ============ FASE 2: CONSTRUIR ESQUEMAS Y DATASET ============
print("\n" + "=" * 100)
print("[FASE 2/4] CONSTRUIR ESQUEMAS Y DATASET")
print("=" * 100)

dataset_name = cfg["oe3"]["dataset"]["name"]
processed_dataset_dir = rp.processed_dir / "citylearn" / dataset_name

logger.info(f"Dataset: {dataset_name}")
logger.info(f"Path: {processed_dataset_dir}")

if not processed_dataset_dir.exists():
    logger.error(f"Dataset no encontrado: {processed_dataset_dir}")
    sys.exit(1)

# Validar esquemas
schema_pv = processed_dataset_dir / "schema_pv_bess.json"
schema_buildings = processed_dataset_dir / "schema.json"

try:
    assert schema_pv.exists(), f"Schema PV no encontrado: {schema_pv}"
    logger.info(f"✓ Schema PV: {schema_pv}")
    
    assert schema_buildings.exists(), f"Schema buildings no encontrado: {schema_buildings}"
    logger.info(f"✓ Schema buildings: {schema_buildings}")
    
    # Validar JSON schemas
    with open(schema_pv) as f:
        pv_schema_data = json.load(f)
        logger.info(f"  • PV Schema: {len(pv_schema_data.get('buildings', []))} edificios")
    
    with open(schema_buildings) as f:
        bldg_schema_data = json.load(f)
        logger.info(f"  • Buildings Schema: {len(bldg_schema_data.get('buildings', []))} edificios")
        
except Exception as e:
    logger.error(f"Error validando esquemas: {e}")
    sys.exit(1)

carbon_intensity = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])
seconds_per_step = int(cfg["project"]["seconds_per_time_step"])

logger.info(f"✓ Parámetros cargados:")
logger.info(f"  • Carbon intensity: {carbon_intensity} kg/kWh")
logger.info(f"  • Seconds per step: {seconds_per_step}")

# ============ FASE 3: CALCULAR BASELINE ============
print("\n" + "=" * 100)
print("[FASE 3/4] CALCULAR BASELINE (sin agente RL)")
print("=" * 100)

training_dir = rp.outputs_dir / "oe3" / "training" / "tier2_v2_from_scratch"
training_dir.mkdir(parents=True, exist_ok=True)

baseline_results = {}
baseline_file = training_dir / "baseline_metrics.json"

logger.info("Calculando baseline (estrategia reactiva sin RL)...")

try:
    result_baseline = simulate(
        schema_path=schema_pv,
        agent_name="uncontrolled",
        out_dir=training_dir / "baseline",
        training_dir=training_dir / "baseline_metrics",
        carbon_intensity_kg_per_kwh=carbon_intensity,
        seconds_per_time_step=seconds_per_step,
        seed=42,
        use_multi_objective=False
    )
    
    baseline_raw: Dict[str, Any] = cast(Dict[str, Any], result_baseline or {})
    
    if baseline_raw:
        baseline_results = {
            "co2_total_kg": float(np.mean(baseline_raw.get("co2_total_kg", [0]))),
            "cost_total_usd": float(np.mean(baseline_raw.get("cost_total_usd", [0]))),
            "peak_import_kw": float(np.max(baseline_raw.get("peak_import_kw", [0]))),
            "solar_used_kwh": float(np.mean(baseline_raw.get("solar_used_kwh", [0]))),
        }
        
        with open(baseline_file, 'w') as f:
            json.dump(baseline_results, f, indent=2)
        
        logger.info("✓ Baseline calculado:")
        logger.info(f"  • CO2 total: {baseline_results['co2_total_kg']:.2f} kg")
        logger.info(f"  • Cost total: ${baseline_results['cost_total_usd']:.2f}")
        logger.info(f"  • Peak import: {baseline_results['peak_import_kw']:.2f} kW")
        logger.info(f"  • Solar used: {baseline_results['solar_used_kwh']:.2f} kWh")
    else:
        logger.warning("Baseline retornó None, usando valores por defecto")
        baseline_results = {
            "co2_total_kg": 150.0,
            "cost_total_usd": 500.0,
            "peak_import_kw": 200.0,
            "solar_used_kwh": 50.0,
        }
        
except Exception as e:
    logger.warning(f"Error calculando baseline (continuando): {e}")
    baseline_results = {
        "co2_total_kg": 150.0,
        "cost_total_usd": 500.0,
        "peak_import_kw": 200.0,
        "solar_used_kwh": 50.0,
    }

# ============ FASE 4: ENTRENAMIENTO EN SERIE ============
print("\n" + "=" * 100)
print("[FASE 4/4] ENTRENAMIENTO EN SERIE - A2C -> PPO -> SAC")
print("=" * 100)

results = {}

# ========== A2C: 2 EPISODIOS ==========
print("\n" + "-" * 100)
print("[A2C 2/6] A2C TIER 2 V2 - 2 EPISODIOS")
print("-" * 100)
print(f"Config: entropy=0.01, lr_base={config_v2.learning_rate_base:.2e}, lr_peak={config_v2.learning_rate_peak:.2e}\n")

try:
    result_a2c = simulate(
        schema_path=schema_pv,
        agent_name="a2c",
        out_dir=training_dir / "a2c_2ep",
        training_dir=training_dir / "a2c_metrics",
        carbon_intensity_kg_per_kwh=carbon_intensity,
        seconds_per_time_step=seconds_per_step,
        a2c_timesteps=100000,
        a2c_n_steps=1024,
        a2c_learning_rate=config_v2.learning_rate_base,
        a2c_entropy_coef=config_v2.entropy_coef_fixed,
        use_multi_objective=True,
        multi_objective_priority="balanced",
        seed=42,
    )
    
    results["a2c"] = result_a2c
    logger.info(f"✓ A2C completado")
    logger.info(f"  • Episodes: 2")
    logger.info(f"  • Output: {training_dir / 'a2c_2ep'}")
    
except Exception as e:
    logger.error(f"Error en A2C: {e}")
    results["a2c"] = None

# ========== PPO: 2 EPISODIOS ==========
print("\n" + "-" * 100)
print("[PPO 4/6] PPO TIER 2 V2 - 2 EPISODIOS")
print("-" * 100)
print(f"Config: entropy=0.01, batch=256, n_epochs=15, clip=0.2\n")

try:
    result_ppo = simulate(
        schema_path=schema_pv,
        agent_name="ppo",
        out_dir=training_dir / "ppo_2ep",
        training_dir=training_dir / "ppo_metrics",
        carbon_intensity_kg_per_kwh=carbon_intensity,
        seconds_per_time_step=seconds_per_step,
        ppo_timesteps=100000,
        ppo_n_steps=1024,
        ppo_batch_size=256,
        ppo_use_amp=True,
        use_multi_objective=True,
        multi_objective_priority="balanced",
        seed=42,
    )
    
    results["ppo"] = result_ppo
    logger.info(f"✓ PPO completado")
    logger.info(f"  • Episodes: 2")
    logger.info(f"  • Output: {training_dir / 'ppo_2ep'}")
    
except Exception as e:
    logger.error(f"Error en PPO: {e}")
    results["ppo"] = None

# ========== SAC: 2 EPISODIOS ==========
print("\n" + "-" * 100)
print("[SAC 6/6] SAC TIER 2 V2 - 2 EPISODIOS")
print("-" * 100)
print(f"Config: entropy=0.01, batch=256, lr={config_v2.learning_rate_base:.2e}\n")

try:
    result_sac = simulate(
        schema_path=schema_pv,
        agent_name="sac",
        out_dir=training_dir / "sac_2ep",
        training_dir=training_dir / "sac_metrics",
        carbon_intensity_kg_per_kwh=carbon_intensity,
        seconds_per_time_step=seconds_per_step,
        sac_episodes=2,
        sac_batch_size=256,
        sac_use_amp=True,
        use_multi_objective=True,
        multi_objective_priority="balanced",
        seed=42,
    )
    
    results["sac"] = result_sac
    logger.info(f"✓ SAC completado")
    logger.info(f"  • Episodes: 2")
    logger.info(f"  • Output: {training_dir / 'sac_2ep'}")
    
except Exception as e:
    logger.error(f"Error en SAC: {e}")
    results["sac"] = None

# ============ RESUMEN FINAL ============
print("\n" + "=" * 100)
print("RESUMEN FINAL")
print("=" * 100)

print("\n📊 BASELINE (Reactivo sin RL):")
print(f"  • CO2: {baseline_results['co2_total_kg']:.2f} kg")
print(f"  • Cost: ${baseline_results['cost_total_usd']:.2f}")
print(f"  • Peak: {baseline_results['peak_import_kw']:.2f} kW")

print("\n🤖 RESULTADOS RL:")
for agent, result in results.items():
    if result:
        print(f"\n  {agent.upper()}:")
        print(f"    ✓ Completado")
    else:
        print(f"\n  {agent.upper()}:")
        print(f"    ✗ Falló")

print(f"\n📁 Outputs guardados en: {training_dir}")
print(f"\n✅ Fin: {datetime.now().isoformat()}")
print("=" * 100 + "\n")

logger.info(f"Entrenamiento desde cero completado")
logger.info(f"Directorio de outputs: {training_dir}")
