#!/usr/bin/env python3
"""Test completo del flujo de checkpoints."""
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent / "src"))

from scripts._common import load_all
from iquitos_citylearn.oe3.simulate import simulate

cfg, rp = load_all(Path("configs/default.yaml"))

# Extraer valores exactamente como lo hace run_oe3_simulate.py
eval_cfg = cfg["oe3"]["evaluation"]
sac_cfg = eval_cfg.get("sac", {})

sac_checkpoint_freq = int(sac_cfg.get("checkpoint_freq_steps", 1000))

logger.info(f"=== VALORES EXTRAÍDOS ===")
logger.info(f"sac_checkpoint_freq: {sac_checkpoint_freq}")

# Verificar directorios
training_dir = rp.analyses_dir / "oe3" / "training"
out_dir = rp.outputs_dir / "oe3" / "simulations"

logger.info(f"training_dir: {training_dir}")
logger.info(f"out_dir: {out_dir}")

schema_pv = Path("data/processed/citylearn/iquitos_pv_bess_ev_scenario/schema_pv_bess.json")
if not schema_pv.exists():
    logger.error(f"Schema no existe: {schema_pv}")
    sys.exit(1)

logger.info(f"=== LLAMANDO A SIMULATE ===")

# Solo probar SAC con 100 timesteps para ser rápido
try:
    result = simulate(
        schema_path=schema_pv,
        agent_name="SAC",
        out_dir=out_dir,
        training_dir=training_dir,
        carbon_intensity_kg_per_kwh=0.4521,
        seconds_per_time_step=3600,
        sac_episodes=1,
        sac_checkpoint_freq_steps=sac_checkpoint_freq,  # Este es el valor clave
        sac_device="cpu",  # CPU para test rápido
        deterministic_eval=True,
    )
    logger.info(f"=== RESULTADO ===")
    logger.info(f"Pasos: {result.steps}")
except Exception as e:
    logger.exception(f"Error: {e}")

# Verificar checkpoints creados
checkpoint_dir = training_dir / "checkpoints" / "sac"
if checkpoint_dir.exists():
    zips = list(checkpoint_dir.glob("*.zip"))
    logger.info(f"=== CHECKPOINTS ENCONTRADOS: {len(zips)} ===")
    for z in zips:
        logger.info(f"  - {z.name}")
else:
    logger.warning(f"Directorio de checkpoints no existe: {checkpoint_dir}")
