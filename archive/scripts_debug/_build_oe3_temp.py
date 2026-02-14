#!/usr/bin/env python3
"""Construir dataset OE3 temporal - será integrado al train_ppo_multiobjetivo.py después"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path('src')))

print('='*80)
print('[PASO 1] CONSTRUIR DATASET OE3 - DATOS REALES')
print('='*80)

import pandas as pd
import numpy as np

try:
    from citylearnv2.dataset_builder.dataset_builder import build_citylearn_dataset
    
    # Construir dataset OE3 (esto valida OE2 y crea OE3)
    print('Construyendo dataset OE3...')
    dataset = build_citylearn_dataset()
    print(f'✓ Dataset OE3 construido correctamente')
    print(f'  timesteps: {len(dataset.observations) if hasattr(dataset, "observations") else "N/A"}')
    print(f'  num_buildings: {dataset.num_buildings if hasattr(dataset, "num_buildings") else "N/A"}')
    
except Exception as e:
    print(f'✗ Error: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

print('='*80)
print('[OK] Dataset OE3 listo para entrenamiento')
print('='*80)
