#!/usr/bin/env python3
"""
Verifica y repara CSVs de chargers para asegurar que tengan 8761 filas (8760 timesteps + 1 extra).
CityLearn intenta acceder a t+1 en el último timestep.
"""
import logging
from pathlib import Path
import pandas as pd
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

DATASET_DIR = Path("data/processed/citylearn/iquitos_ev_mall")
REQUIRED_ROWS = 8761  # 8760 timesteps + 1 extra para CityLearn

def fix_charger_csvs():
    """Verifica todos los CSVs de chargers y agrega filas si falta."""
    charger_csvs = list(DATASET_DIR.glob("MOTO_CH_*.csv")) + list(DATASET_DIR.glob("MOTO_TAXI_CH_*.csv"))
    logger.info(f"Encontrados {len(charger_csvs)} archivos de chargers")
    
    fixed_count = 0
    for csv_path in sorted(charger_csvs):
        try:
            df = pd.read_csv(csv_path)
            n_rows = len(df)
            
            if n_rows < REQUIRED_ROWS:
                logger.warning(f"{csv_path.name}: {n_rows} filas (esperadas {REQUIRED_ROWS})")
                
                # Agregar filas faltantes duplicando la última fila
                missing_rows = REQUIRED_ROWS - n_rows
                last_row = df.iloc[-1:].copy()
                rows_to_add = pd.concat([last_row] * missing_rows, ignore_index=True)
                df = pd.concat([df, rows_to_add], ignore_index=True)
                
                df.to_csv(csv_path, index=False)
                logger.info(f"  → Reparado: {n_rows} → {len(df)} filas")
                fixed_count += 1
            else:
                logger.debug(f"{csv_path.name}: OK ({n_rows} filas)")
                
        except Exception as e:
            logger.error(f"{csv_path.name}: {e}")
    
    logger.info(f"Total reparados: {fixed_count}/{len(charger_csvs)}")

if __name__ == "__main__":
    fix_charger_csvs()
