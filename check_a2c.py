#!/usr/bin/env python
"""Verificar estado de A2C."""
from pathlib import Path
import pandas as pd

csv_files = sorted(Path('outputs/a2c_training').glob('*.csv'))
if csv_files:
    latest = csv_files[-1]
    df = pd.read_csv(latest)
    lines = len(df)
    percent = (lines / 87600) * 100
    
    print(f'\n✅ A2C ENTRENAMIENTO:')
    print(f'   Timesteps: {lines:,} / 87,600 ({percent:.1f}%)')
    print(f'   Episodios: {int(df["episode"].max())} / 10')
    
    if lines >= 87600:
        print(f'\n🎉 ¡ENTRENAMIENTO COMPLETADO!')
    else:
        print(f'\n⏳ Aún en progreso...')
else:
    print('Sin logs aún')
