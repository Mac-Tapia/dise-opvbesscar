#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DIAGNOSTICO PRE-ENTRENAMIENTO SAC
Valida que todo está listo antes de iniciar entrenamiento
"""
from __future__ import annotations

import sys
from pathlib import Path

# Workspace root
workspace_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(workspace_root))

import torch
import numpy as np
import pandas as pd

def check_environment():
    """Verifica que el ambiente esté correctamente configurado."""
    
    print("=" * 100)
    print("DIAGNOSTICO PRE-ENTRENAMIENTO SAC v2026-02-17")
    print("=" * 100)
    
    checks_passed = 0
    checks_failed = 0
    
    # 1. Python version
    print(f"\n[1] Python Version")
    if sys.version_info >= (3, 11):
        print(f"    ✓ Python {sys.version_info.major}.{sys.version_info.minor} (OK)")
        checks_passed += 1
    else:
        print(f"    ✗ Python {sys.version_info.major}.{sys.version_info.minor} (Requiere 3.11+)")
        checks_failed += 1
    
    # 2. PyTorch
    print(f"\n[2] PyTorch")
    try:
        import torch
        gpu_available = torch.cuda.is_available()
        device = 'CUDA' if gpu_available else 'CPU'
        if gpu_available:
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.mem_get_info()[1] / 1e9
            print(f"    ✓ PyTorch {torch.__version__} ({device})")
            print(f"      GPU: {gpu_name} ({gpu_memory:.1f} GB)")
            checks_passed += 1
        else:
            print(f"    ✓ PyTorch {torch.__version__} ({device}) [Training en CPU - más lento]")
            checks_passed += 1
    except Exception as e:
        print(f"    ✗ PyTorch error: {e}")
        checks_failed += 1
    
    # 3. Stable-Baselines3
    print(f"\n[3] Stable-Baselines3")
    try:
        from stable_baselines3 import SAC
        from stable_baselines3.common.callbacks import BaseCallback, CallbackList
        print(f"    ✓ Stable-Baselines3 importado (SAC, callbacks disponibles)")
        checks_passed += 1
    except Exception as e:
        print(f"    ✗ Stable-Baselines3: {e}")
        checks_failed += 1
    
    # 4. Datos OE2
    print(f"\n[4] Datos OE2")
    try:
        data_paths = {
            'Solar': [
                workspace_root / 'data/interim/oe2/solar/pv_generation_timeseries.csv',
                workspace_root / 'data/oe2/solar/pv_generation_citylearn_enhanced_v2.csv',
                workspace_root / 'data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv',
            ],
            'Chargers': [
                workspace_root / 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
            ],
            'BESS': [
                workspace_root / 'data/oe2/bess/bess_simulation_hourly.csv',
                workspace_root / 'data/oe2/bess/bess_ano_2024.csv',
            ],
            'Mall': [
                workspace_root / 'data/oe2/demandamallkwh/demandamallhorakwh.csv',
            ],
        }
        
        all_exist = True
        for name, paths in data_paths.items():
            found = False
            for path in paths:
                if path.exists():
                    # Contar filas del CSV
                    if name == 'Solar':
                        df = pd.read_csv(path)
                        rows = len(df)
                        status = '✓ 8760 filas (correcto)' if rows == 8760 else f'✗ {rows} filas (requiere 8760)'
                        print(f"    {status}: {name} ({path.name})")
                        if rows != 8760:
                            all_exist = False
                    else:
                        print(f"    ✓ {name} ({path.name})")
                    found = True
                    break
            
            if not found:
                print(f"    ✗ FALTA: {name}")
                all_exist = False
        
        if all_exist:
            checks_passed += 1
        else:
            checks_failed += 1
            
    except Exception as e:
        print(f"    ✗ Error al validar datos: {e}")
        checks_failed += 1
    
    # 5. Nuevo callback
    print(f"\n[5] Nuevo Callback SACLiveMetricsCallback")
    try:
        from scripts.train.sac_metrics_live_capture import SACLiveMetricsCallback
        print(f"    ✓ SACLiveMetricsCallback importado exitosamente")
        checks_passed += 1
    except Exception as e:
        print(f"    ✗ Error importando callback: {e}")
        checks_failed += 1
    
    # 6. Outputs directory
    print(f"\n[6] Directorios de Salida")
    try:
        output_dirs = {
            'checkpoints': workspace_root / 'checkpoints/SAC',
            'outputs': workspace_root / 'outputs',
            'metrics': workspace_root / 'outputs/sac_metrics',
        }
        
        for name, path in output_dirs.items():
            path.mkdir(parents=True, exist_ok=True)
            print(f"    ✓ {name}: {path}")
        
        checks_passed += 1
    except Exception as e:
        print(f"    ✗ Error creando directorios: {e}")
        checks_failed += 1
    
    # 7. Training script
    print(f"\n[7] Script de Entrenamiento")
    try:
        train_script = workspace_root / 'scripts/train/train_sac_multiobjetivo.py'
        if train_script.exists():
            print(f"    ✓ train_sac_multiobjetivo.py encontrado")
            checks_passed += 1
        else:
            print(f"    ✗ train_sac_multiobjetivo.py NO encontrado")
            checks_failed += 1
    except Exception as e:
        print(f"    ✗ Error: {e}")
        checks_failed += 1
    
    # Resumen
    print(f"\n" + "=" * 100)
    print(f"RESULTADO: {checks_passed} OK, {checks_failed} FALLOS")
    
    if checks_failed == 0:
        print("✓ LISTO PARA ENTRENAR SAC")
        print("\nProximo paso:")
        print(f"  python scripts/train/train_sac_multiobjetivo.py")
        return 0
    else:
        print("✗ NECESITA CORREGIR LOS ERRORES ANTES DE ENTRENAR")
        return 1

if __name__ == '__main__':
    exit_code = check_environment()
    sys.exit(exit_code)
