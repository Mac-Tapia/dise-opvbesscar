#!/usr/bin/env python3
"""
Script simplificado para entrenar SAC con GPU y guardar checkpoints.
"""

import sys
from pathlib import Path

# Agregar proyecto al path
sys.path.insert(0, str(Path(__file__).parent))

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.simulate import simulate
from scripts._common import load_all

setup_logging()

print("""
╔══════════════════════════════════════════════════════════════════════╗
║  ENTRENAMIENTO SAC + UNCONTROLLED CON GPU (MÁXIMO RENDIMIENTO)      ║
╚══════════════════════════════════════════════════════════════════════╝
""")

# Cargar configuración
cfg, rp = load_all("configs/default.yaml")
oe3_cfg = cfg["oe3"]

print(f"✓ Configuración cargada")
print(f"  - Dataset: {oe3_cfg['dataset']['name']}")
print(f"  - Agentes: {oe3_cfg['evaluation']['agents']}")
print(f"  - SAC Episodes: {oe3_cfg['evaluation']['sac']['episodes']}")
print(f"  - GPU: {oe3_cfg['evaluation']['sac']['device']}")

# Construir dataset
dataset_name = oe3_cfg["dataset"]["name"]
processed_dataset_dir = rp.processed_dir / "citylearn" / dataset_name

if processed_dataset_dir.exists():
    print(f"✓ Dataset ya existe: {processed_dataset_dir}")
    dataset_dir = processed_dataset_dir
else:
    print(f"🔧 Construyendo dataset...")
    built = build_citylearn_dataset(
        cfg=cfg,
        raw_dir=rp.raw_dir,
        interim_dir=rp.interim_dir,
        processed_dir=rp.processed_dir,
    )
    dataset_dir = built.dataset_dir
    print(f"✓ Dataset construido: {dataset_dir}")

schema_pv = dataset_dir / "schema_pv_bess.json"

print(f"\n{'='*70}")
print(f"FASE 1: ENTRENAR UNCONTROLLED (Baseline)")
print(f"{'='*70}\n")

try:
    result_unc = simulate(
        schema_path=schema_pv,
        agent_name="Uncontrolled",
        out_dir=rp.outputs_dir / "oe3" / "simulations",
        training_dir=None,  # No training artifacts para uncontrolled
        carbon_intensity_kg_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
        seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
        use_multi_objective=False,
    )
    print(f"\n✓ Uncontrolled completado")
    print(f"  CO2 Anual: {result_unc.carbon_kg:.2f} kg")
    print(f"  Reducción: No aplica (baseline)")
except Exception as e:
    print(f"\n✗ Error Uncontrolled: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*70}")
print(f"FASE 2: ENTRENAR SAC CON GPU")
print(f"{'='*70}\n")

try:
    # Configurar para máximo GPU
    sac_cfg = oe3_cfg["evaluation"]["sac"]
    sac_cfg["batch_size"] = 4096  # Aumentar batch size para GPU
    sac_cfg["buffer_size"] = 500000
    sac_cfg["device"] = "cuda"
    sac_cfg["use_amp"] = True  # Usar Automatic Mixed Precision
    sac_cfg["episodes"] = 50  # Aumentar episodios para buen entrenamiento
    
    print(f"Config SAC para GPU:")
    print(f"  - Episodes: {sac_cfg['episodes']}")
    print(f"  - Batch Size: {sac_cfg['batch_size']}")
    print(f"  - Buffer Size: {sac_cfg['buffer_size']}")
    print(f"  - Device: {sac_cfg['device']}")
    print(f"  - AMP (Mixed Precision): {sac_cfg['use_amp']}")
    print(f"  - Checkpoint Freq: {sac_cfg['checkpoint_freq_steps']} steps\n")
    
    training_dir = rp.outputs_dir / "oe3" / "training"
    
    result_sac = simulate(
        schema_path=schema_pv,
        agent_name="SAC",
        out_dir=rp.outputs_dir / "oe3" / "simulations",
        training_dir=training_dir,
        carbon_intensity_kg_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
        seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
        sac_episodes=sac_cfg['episodes'],
        sac_batch_size=sac_cfg.get('batch_size', 512),
        sac_log_interval=sac_cfg.get('log_interval', 500),
        sac_use_amp=sac_cfg.get('use_amp', True),
        sac_device="cuda",
        sac_checkpoint_freq_steps=sac_cfg.get('checkpoint_freq_steps', 1000),
        use_multi_objective=True,
        multi_objective_priority="co2_focus",
        seed=int(cfg["project"]["seed"]),
    )
    
    print(f"\n✓ SAC entrenamiento completado")
    print(f"  CO2 Anual: {result_sac.carbon_kg:.2f} kg")
    reduction_pct = ((result_unc.carbon_kg - result_sac.carbon_kg) / result_unc.carbon_kg * 100) if result_unc else 0
    print(f"  Reducción vs Uncontrolled: {reduction_pct:.2f}%")
    
    # Verificar checkpoints guardados
    checkpoint_dir = rp.outputs_dir / "oe3" / "checkpoints" / "SAC"
    if checkpoint_dir.exists():
        checkpoints = list(checkpoint_dir.glob("SAC_step_*.zip")) + list(checkpoint_dir.glob("SAC_final.zip"))
        print(f"\n✓ Checkpoints guardados:")
        for ckpt in sorted(checkpoints):
            size_mb = ckpt.stat().st_size / (1024*1024)
            print(f"    {ckpt.name}: {size_mb:.2f} MB")
    
except Exception as e:
    print(f"\n✗ Error SAC: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*70}")
print(f"✓ ENTRENAMIENTO COMPLETADO")
print(f"{'='*70}\n")
