#!/usr/bin/env python3
"""
LANZAR ENTRENAMIENTO PPO CON DATOS REALES OE2
Iquitos, Perú - EV Charging Optimization
"""
import sys
from pathlib import Path

# Agregar src al path
project = Path('.')
sys.path.insert(0, str(project))
sys.path.insert(0, str(project / 'src'))

print('\n' + '='*80)
print('INICIANDO ENTRENAMIENTO PPO v5.7')
print('='*80)
print('Location: Iquitos, Peru')
print('Episodes: 10 x 8,760 hours = 87,600 timesteps')
print('Data: Real OE2 (Solar, BESS, Chargers, Vehicles)')
print('='*80 + '\n')

try:
    from scripts.train.train_ppo_multiobjetivo import main
    main()
except Exception as e:
    print(f'\nERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
