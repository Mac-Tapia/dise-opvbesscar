#!/usr/bin/env python3
"""
Debug script para ver qué está pasando con el episodio uncontrolled.
"""

import sys
import logging
from pathlib import Path

# Agregar raíz al path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Habilitar debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from scripts._common import load_all
from iquitos_citylearn.oe3.simulate import simulate

def debug_episode():
    """Debug the episode execution."""
    
    print("\n" + "="*80)
    print("DEBUG: Ejecución de Episodio Uncontrolled")
    print("="*80)
    
    # Cargar config
    cfg, rp = load_all("configs/default.yaml")
    rp.ensure()
    
    dataset_name = cfg["oe3"]["dataset"]["name"]
    processed_dataset_dir = rp.processed_dir / "citylearn" / dataset_name
    schema_pv = processed_dataset_dir / "schema_pv_bess.json"
    
    out_dir = rp.outputs_dir / "oe3" / "simulations_debug"
    out_dir.mkdir(parents=True, exist_ok=True)
    training_dir = rp.analyses_dir / "oe3" / "training"
    
    print(f"\nEjecutando con DEBUG logging habilitado...")
    
    result = simulate(
        schema_path=schema_pv,
        agent_name="Uncontrolled",
        out_dir=out_dir,
        training_dir=training_dir,
        carbon_intensity_kg_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
        seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
        deterministic_eval=True,
        use_multi_objective=False,
    )
    
    print(f"\n✓ Completado")
    print(f"  Pasos: {result.steps}")
    print(f"  Años: {result.simulated_years:.4f}")

if __name__ == "__main__":
    debug_episode()
