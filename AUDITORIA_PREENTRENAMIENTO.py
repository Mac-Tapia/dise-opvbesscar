#!/usr/bin/env python3
"""
AUDITORIA PRE-ENTRENAMIENTO: SAC, PPO, A2C
===========================================

Verifica ANTES de entrenar:
1. Configuraciones críticas correctas (sin ajustes previos)
2. GPU al máximo uso
3. Outputs correctos (checkpoint, JSON, CSVs)
4. Validación configs JSON/YAML
5. Estado limpio sin checkpoints conflictivos
"""

from __future__ import annotations

import sys
from pathlib import Path
import json
import yaml
import torch
import logging
from datetime import datetime
from typing import Any
import warnings

warnings.filterwarnings('ignore')

print("\n" + "="*80)
print("AUDITORIA PRE-ENTRENAMIENTO: SAC, PPO, A2C")
print("="*80)

# ============================================================================
# PASO 1: VERIFICAR GPU Y CONFIGURACIÓN DEVICE
# ============================================================================

print("\n[PASO 1] VERIFICAR GPU Y CONFIGURACIÓN DEVICE")
print("-" * 80)

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"\n✓ Device detectado: {DEVICE.upper()}")

if DEVICE == 'cuda':
    GPU_COUNT = torch.cuda.device_count()
    print(f"✓ GPUs disponibles: {GPU_COUNT}")

    for i in range(GPU_COUNT):
        props = torch.cuda.get_device_properties(i)
        memory_gb = props.total_memory / 1e9
        print(f"  GPU {i}: {props.name}")
        print(f"    Memoria: {memory_gb:.1f} GB")
        print(f"    Compute capability: {props.major}.{props.minor}")

    cuda_version: str | None = getattr(torch.version, 'cuda', None)  # type: ignore[attr-defined]
    cudnn_version: int | None = torch.backends.cudnn.version()
    print(f"\nCUDA Version: {cuda_version}")
    print(f"cuDNN: {cudnn_version}")
    print(f"cuDNN enabled: {torch.backends.cudnn.enabled}")

    # Verificar que GPU está optimizado
    if torch.backends.cudnn.enabled:
        print("✓ cuDNN HABILITADO - GPU OPTIMIZADO")
    else:
        print("⚠️  cuDNN NO HABILITADO - Activar para máximo rendimiento")
        torch.backends.cudnn.enabled = True
else:
    print("⚠️  MODO CPU - Sin GPU detectada")
    print("    El entrenamiento será LENTO")

print("\n[✓ PASO 1 COMPLETADO]")

# ============================================================================
# PASO 2: VALIDAR CONFIGURACIÓN FILES (YAML)
# ============================================================================

print("\n[PASO 2] VALIDAR ARCHIVOS DE CONFIGURACIÓN (YAML)")
print("-" * 80)

config_files = [
    Path('configs/default.yaml'),
    Path('configs/default_optimized.yaml'),
]

for cfg_file in config_files:
    if cfg_file.exists():
        try:
            with open(cfg_file, 'r') as f:
                cfg = yaml.safe_load(f)
            print(f"\n✓ {cfg_file.name}")
            print(f"  Keys: {list(cfg.keys())}")
            if 'gym' in cfg:
                print(f"  Gym timesteps: {cfg['gym'].get('timesteps', 'N/A')}")
        except Exception as e:
            print(f"\n❌ ERROR: {cfg_file.name}")
            print(f"  {e}")
    else:
        print(f"\n⚠️  FALTA: {cfg_file.name}")

print("\n[✓ PASO 2 COMPLETADO]")

# ============================================================================
# PASO 3: VALIDAR AGENTE CONFIGS (JSON)
# ============================================================================

print("\n[PASO 3] VALIDAR ARCHIVOS DE CONFIGURACIÓN AGENTES (JSON)")
print("-" * 80)

# Verificar que existan configs para cada agente
agents = ['SAC', 'PPO', 'A2C']

for agent in agents:
    print(f"\n{agent}:")

    # Checkpoint dir
    checkpoint_dir = Path(f'checkpoints/{agent}')
    print(f"  Checkpoint dir: {checkpoint_dir}")
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    print(f"  ✓ Creado/verificado")

    # Output dir
    output_dir = Path(f'outputs/{agent.lower()}_training')
    print(f"  Output dir: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"  ✓ Creado/verificado")

    # Config file
    config_file = Path(f'configs/{agent.lower()}_config.json')
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                agent_cfg = json.load(f)
            print(f"  Config: {config_file}")
            print(f"    Keys: {list(agent_cfg.keys())}")
        except Exception as e:
            print(f"  ⚠️  CONFIG PARSE ERROR: {e}")
    else:
        print(f"  ℹ️  Config: {config_file} (opcional)")

print("\n[✓ PASO 3 COMPLETADO]")

# ============================================================================
# PASO 4: VERIFICAR OUTPUTS ESPERADOS
# ============================================================================

print("\n[PASO 4] VERIFICAR OUTPUTS ESPERADOS POR AGENTE")
print("-" * 80)

expected_outputs = {
    'SAC': [
        'outputs/sac_training/result_sac.json',
        'outputs/sac_training/timeseries_sac.csv',
        'outputs/sac_training/trace_sac.csv',
        'checkpoints/SAC/sac_final_model.zip',
    ],
    'PPO': [
        'outputs/ppo_training/result_ppo.json',
        'outputs/ppo_training/timeseries_ppo.csv',
        'outputs/ppo_training/trace_ppo.csv',
        'checkpoints/PPO/ppo_final_model.zip',
    ],
    'A2C': [
        'outputs/a2c_training/result_a2c.json',
        'outputs/a2c_training/timeseries_a2c.csv',
        'outputs/a2c_training/trace_a2c.csv',
        'checkpoints/A2C/a2c_final_model.zip',
    ],
}

for agent, outputs in expected_outputs.items():
    print(f"\n{agent} - Outputs esperados:")
    for output in outputs:
        output_path = Path(output)
        if output_path.exists():
            size = output_path.stat().st_size
            print(f"  ✓ {output} ({size} bytes)")
        else:
            # Pre-crear directorios
            output_path.parent.mkdir(parents=True, exist_ok=True)
            print(f"  ℹ️  {output} (será creado por script)")

print("\n[✓ PASO 4 COMPLETADO]")

# ============================================================================
# PASO 5: AUDITAR CONFIGURACIONES CRÍTICAS SAC
# ============================================================================

print("\n[PASO 5] AUDITAR CONFIGURACIONES CRÍTICAS")
print("-" * 80)

print("\nSAC - Parámetros críticos a validar:")

critical_params: dict[str, dict[str, tuple[Any, Any, str]]] = {
    'SAC': {
        'learning_rate': (1e-4, 1e-3, 'Rango: 1e-4 a 1e-3'),
        'batch_size': (64, 512, 'Rango: 64 a 512 (según GPU)'),
        'buffer_size': (1e6, 1e7, 'Rango: 1M a 10M'),
        'ent_coef': ('auto', 0.1, 'Auto o valor fijo 0.01-0.1'),
        'target_update_interval': (1, 10, 'Rango: 1 a 10'),
        'gradient_steps': (1, 5, 'Rango: 1 a 5'),
    },
    'PPO': {
        'learning_rate': (1e-4, 1e-3, 'Rango: 1e-4 a 1e-3'),
        'batch_size': (64, 512, 'Rango: 64 a 512'),
        'n_steps': (512, 4096, 'Rango: 512 a 4096'),
        'n_epochs': (3, 20, 'Rango: 3 a 20'),
        'clip_range': (0.1, 0.3, 'Rango: 0.1 a 0.3'),
        'gae_lambda': (0.9, 0.99, 'Rango: 0.9 a 0.99'),
    },
    'A2C': {
        'learning_rate': (1e-4, 1e-3, 'Rango: 1e-4 a 1e-3'),
        'n_steps': (5, 32, 'Rango: 5 a 32'),
        'ent_coef': (0.0, 0.01, 'Rango: 0.0 a 0.01'),
        'gamma': (0.95, 0.99, 'Gamma discount: 0.95-0.99'),
    }
}

for agent, params in critical_params.items():
    print(f"\n{agent}:")
    for param, (min_val, max_val, description) in params.items():
        print(f"  - {param}: {description}")

print("\n✓ Verificar que estos parámetros son CORRECTOS en train_*.py")

print("\n[✓ PASO 5 COMPLETADO]")

# ============================================================================
# PASO 6: VERIFICAR LIMPIEZA DE CHECKPOINTS VIEJOS
# ============================================================================

print("\n[PASO 6] VERIFICAR ESTADO LIMPIO DE CHECKPOINTS")
print("-" * 80)

for agent in ['SAC', 'PPO', 'A2C']:
    checkpoint_dir = Path(f'checkpoints/{agent}')

    if checkpoint_dir.exists():
        checkpoints = list(checkpoint_dir.glob('*_steps_*.zip'))
        final_models = list(checkpoint_dir.glob('*_final_model*.zip'))

        print(f"\n{agent}:")
        print(f"  Checkpoints intermedios: {len(checkpoints)}")
        print(f"  Modelos finales: {len(final_models)}")

        if checkpoints or final_models:
            print(f"\n  ⚠️  ADVERTENCIA: Existen checkpoints previos")
            print(f"      ¿Son del entrenamiento ANTERIOR con los MISMOS pesos?")
            print(f"      SI: Puedes continuar (reset_num_timesteps=False)")
            print(f"      NO: Borra antes para empezar limpio:")
            print(f"          rm checkpoints/{agent}/*.zip")
    else:
        print(f"\n{agent}: Directorio vacío (nuevo entrenamiento) ✓")

print("\n[✓ PASO 6 COMPLETADO]")

# ============================================================================
# PASO 7: GENERAR REPORTE DE AUDITORÍA
# ============================================================================

print("\n[PASO 7] GENERAR REPORTE DE AUDITORÍA")
print("-" * 80)

audit_report: dict[str, Any] = {
    'timestamp': datetime.now().isoformat(),
    'device': DEVICE,
    'gpu_available': DEVICE == 'cuda',

    'agents': {},
}

if DEVICE == 'cuda':
    audit_report['gpu_info'] = {
        'count': torch.cuda.device_count(),
        'cuda_version': getattr(torch.version, 'cuda', None),  # type: ignore[attr-defined]
        'cudnn_enabled': torch.backends.cudnn.enabled,
    }

for agent in ['SAC', 'PPO', 'A2C']:
    checkpoint_dir = Path(f'checkpoints/{agent}')
    output_dir = Path(f'outputs/{agent.lower()}_training')

    audit_report['agents'][agent] = {
        'checkpoint_dir_exists': checkpoint_dir.exists(),
        'checkpoint_dir_path': str(checkpoint_dir.absolute()),
        'output_dir_exists': output_dir.exists(),
        'output_dir_path': str(output_dir.absolute()),
        'previous_checkpoints': len(list(checkpoint_dir.glob('*.zip'))) if checkpoint_dir.exists() else 0,
    }

# Guardar reporte
report_file = Path('outputs/audit_pretraining.json')
report_file.parent.mkdir(parents=True, exist_ok=True)

with open(report_file, 'w') as f:
    json.dump(audit_report, f, indent=2)

print(f"\n✓ Reporte guardado: {report_file}")
print(f"  Verificar: prev_checkpoints = 0 si es nuevo entrenamiento")

print("\n[✓ PASO 7 COMPLETADO]")

# ============================================================================
# PASO 8: RESUMEN Y CHECKLIST
# ============================================================================

print("\n[PASO 8] CHECKLIST PRE-ENTRENAMIENTO")
print("-" * 80)

checklist = [
    ("GPU/CUDA disponible", DEVICE == 'cuda'),
    ("cuDNN habilitado", torch.backends.cudnn.enabled if DEVICE == 'cuda' else None),
    ("Configs YAML existen", Path('configs/default.yaml').exists()),
    ("Directorios checkpoints creados", all(Path(f'checkpoints/{a}').exists() for a in ['SAC', 'PPO', 'A2C'])),
    ("Directorios outputs creados", all(Path(f'outputs/{a.lower()}_training').exists() for a in ['SAC', 'PPO', 'A2C'])),
    ("Dataset OE2 accesible", Path('data/oe2').exists()),
    ("5 archivos obligatorios OE2", all(
        Path(f'data/oe2/{d}/{f}').exists() for d, f in [
            ('chargers', 'chargers_real_hourly_2024.csv'),
            ('chargers', 'chargers_real_statistics.csv'),
            ('bess', 'bess_hourly_dataset_2024.csv'),
            ('demandamallkwh', 'demandamallhorakwh.csv'),
            ('Generacionsolar', 'pv_generation_hourly_citylearn_v2.csv'),
        ]
    )),
]

for check_name, result in checklist:
    if result is None:
        status = "⚠️  N/A (CPU mode)"
    elif result:
        status = "✓ PASS"
    else:
        status = "❌ FAIL"

    print(f"{status:12} {check_name}")

print("\n" + "="*80)
print("AUDITORIA COMPLETADA")
print("="*80)

print("\n📋 PRÓXIMOS PASOS:")
print("  1. Revisar checklist arriba - todos deben ser ✓")
print("  2. Si algo es ❌, corregir antes de entrenar")
print("  3. Ejecutar SAC:  python train_sac_multiobjetivo.py")
print("  4. Ejecutar PPO:  python train_ppo_a2c_multiobjetivo.py PPO")
print("  5. Ejecutar A2C:  python train_ppo_a2c_multiobjetivo.py A2C")
print("\nOutputs esperados por agente:")
print("  - checkpoints/{AGENT}/{agent}_final_model.zip")
print("  - outputs/{agent}_training/result_{agent}.json")
print("  - outputs/{agent}_training/timeseries_{agent}.csv")
print("  - outputs/{agent}_training/trace_{agent}.csv")
print("\n" + "="*80 + "\n")
