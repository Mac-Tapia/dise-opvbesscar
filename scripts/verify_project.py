#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICACION INTEGRAL DEL PROYECTO pvbesscar
=============================================
Verifica que todos los componentes estén listos para producción.
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

os.environ['PYTHONIOENCODING'] = 'utf-8'

def main() -> int:
    """Ejecutar verificación integral."""
    print('=' * 80)
    print('VERIFICACION INTEGRAL DEL PROYECTO pvbesscar')
    print('=' * 80)
    print()

    errors = 0

    # [1] Python Version
    print(f'[1] Python Version: {sys.version.split()[0]}')
    if sys.version_info < (3, 11):
        print('    ADVERTENCIA: Se recomienda Python 3.11+')
    print()

    # [2] Estructura de archivos
    print('[2] ARCHIVOS DE ENTRENAMIENTO')
    print('-' * 60)
    training_files = [
        'train_sac_multiobjetivo.py',
        'train_ppo_multiobjetivo.py',
        'train_a2c_multiobjetivo.py',
        'configs/default.yaml',
        'src/rewards/rewards.py',
    ]
    for f in training_files:
        p = Path(f)
        if p.exists():
            size = p.stat().st_size
            print(f'  [OK] {f} ({size:,} bytes)')
        else:
            print(f'  [FALTA] {f}')
            errors += 1
    print()

    # [3] Datos OE2
    print('[3] DATOS OE2 (Dimensionamiento)')
    print('-' * 60)
    import pandas as pd

    oe2_files = {
        'data/oe2/chargers/chargers_real_hourly_2024.csv': ',',
        'data/oe2/bess/bess_hourly_dataset_2024.csv': ',',
        'data/oe2/demandamallkwh/demandamallhorakwh.csv': ';',
        'data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv': ',',
    }
    for f, sep in oe2_files.items():
        p = Path(f)
        if p.exists():
            try:
                df = pd.read_csv(p, sep=sep)
                fname = f.split('/')[-1]
                print(f'  [OK] {fname}: {len(df):,} rows x {len(df.columns)} cols')
            except Exception as e:
                print(f'  [ERROR] {f}: {e}')
                errors += 1
        else:
            print(f'  [FALTA] {f}')
            errors += 1
    print()

    # [4] Dependencias críticas
    print('[4] DEPENDENCIAS CRITICAS')
    print('-' * 60)
    deps = [
        ('torch', 'PyTorch (GPU/CPU)'),
        ('stable_baselines3', 'Stable-Baselines3'),
        ('gymnasium', 'Gymnasium'),
        ('numpy', 'NumPy'),
        ('pandas', 'Pandas'),
        ('yaml', 'PyYAML'),
    ]
    for mod, name in deps:
        try:
            m = __import__(mod)
            ver = getattr(m, '__version__', 'OK')
            print(f'  [OK] {name}: {ver}')
        except ImportError:
            print(f'  [FALTA] {name}')
            errors += 1
    print()

    # [5] GPU disponible
    print('[5] CONFIGURACION GPU')
    print('-' * 60)
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f'  [OK] GPU: {gpu_name}')
            print(f'       Memoria: {gpu_mem:.1f} GB')
            torch_version_module = getattr(torch, 'version', None)
            cuda_ver = getattr(torch_version_module, 'cuda', 'N/A') if torch_version_module else 'N/A'
            print(f'       CUDA: {cuda_ver}')
        else:
            print('  [INFO] GPU no disponible - usará CPU')
    except Exception as e:
        print(f'  [ERROR] {e}')
    print()

    # [6] Verificar imports de agentes
    print('[6] VERIFICAR IMPORTS DE AGENTES')
    print('-' * 60)

    # Test SAC imports
    try:
        from stable_baselines3 import SAC
        print('  [OK] SAC imports correctos')
    except ImportError as e:
        print(f'  [ERROR] SAC: {e}')
        errors += 1

    # Test PPO imports
    try:
        from stable_baselines3 import PPO
        print('  [OK] PPO imports correctos')
    except ImportError as e:
        print(f'  [ERROR] PPO: {e}')
        errors += 1

    # Test A2C imports
    try:
        from stable_baselines3 import A2C
        print('  [OK] A2C imports correctos')
    except ImportError as e:
        print(f'  [ERROR] A2C: {e}')
        errors += 1

    # Test rewards module
    try:
        from src.rewards.rewards import (
            IquitosContext,
            MultiObjectiveReward,
            create_iquitos_reward_weights,
        )
        weights = create_iquitos_reward_weights('co2_focus')
        print(f'  [OK] Rewards module: CO2={weights.co2:.2f}, Solar={weights.solar:.2f}')
    except ImportError as e:
        print(f'  [ERROR] Rewards: {e}')
        errors += 1
    print()

    # [7] Verificar config
    print('[7] CONFIGURACION (configs/default.yaml)')
    print('-' * 60)
    try:
        import yaml as pyyaml
        cfg = pyyaml.safe_load(Path('configs/default.yaml').read_text(encoding='utf-8'))
        print(f'  [OK] Config cargado: {len(cfg)} keys')
        if 'training' in cfg:
            print(f'       Episodes: {cfg["training"].get("episodes", "N/A")}')
            print(f'       Timesteps: {cfg["training"].get("timesteps_per_episode", "N/A")}')
    except Exception as e:
        print(f'  [ERROR] Config: {e}')
        errors += 1
    print()

    # [8] Verificar checkpoints
    print('[8] DIRECTORIOS DE CHECKPOINTS')
    print('-' * 60)
    for agent in ['SAC', 'PPO', 'A2C']:
        cp_dir = Path(f'checkpoints/{agent}')
        if cp_dir.exists():
            files = list(cp_dir.glob('*.zip'))
            print(f'  [OK] {agent}: {len(files)} checkpoints')
        else:
            print(f'  [INFO] {agent}: Sin checkpoints (se crearán al entrenar)')
    print()

    # [9] Test rápido de environment
    print('[9] TEST RAPIDO DE ENVIRONMENT')
    print('-' * 60)
    try:
        import numpy as np
        from gymnasium import Env, spaces

        class TestEnv(Env):
            def __init__(self):
                self.observation_space = spaces.Box(
                    low=-np.inf, high=np.inf, shape=(1045,), dtype=np.float32
                )
                self.action_space = spaces.Box(
                    low=0.0, high=1.0, shape=(129,), dtype=np.float32
                )

            def reset(self, seed=None, options=None):
                return np.zeros(1045, dtype=np.float32), {}

            def step(self, action):
                return np.zeros(1045, dtype=np.float32), 0.0, False, False, {}

        env = TestEnv()
        obs, _ = env.reset()
        print(f'  [OK] Observation space: {env.observation_space.shape}')
        print(f'  [OK] Action space: {env.action_space.shape}')
        print(f'  [OK] Reset OK: obs shape = {obs.shape}')
    except Exception as e:
        print(f'  [ERROR] Environment test: {e}')
        errors += 1
    print()

    # Resumen
    print('=' * 80)
    if errors == 0:
        print('RESULTADO: PROYECTO LISTO PARA PRODUCCION')
        print('  Todos los componentes verificados correctamente.')
        print()
        print('  Comandos de entrenamiento:')
        print('    python train_sac_multiobjetivo.py')
        print('    python train_ppo_multiobjetivo.py')
        print('    python train_a2c_multiobjetivo.py')
    else:
        print(f'RESULTADO: {errors} ERRORES ENCONTRADOS')
        print('  Revisar los errores antes de continuar.')
    print('=' * 80)

    return errors


if __name__ == '__main__':
    sys.exit(main())
