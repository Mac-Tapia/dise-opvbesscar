#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CONFIG_GPU_CUDA_TRAINING.py
===========================

Configuración centralizada para entrenamiento con GPU/CUDA.
Auto-detecta GPU y ajusta parámetros óptimos para Stable-Baselines3 + SAC/PPO/A2C

Uso:
  from CONFIG_GPU_CUDA_TRAINING import get_training_config
  config = get_training_config('SAC')  # o 'PPO', 'A2C'
"""

import torch
from typing import Dict, Any
from pathlib import Path


def detect_gpu() -> dict[str, Any]:
    """Detectar GPU/CUDA disponible."""
    cuda_available: bool = torch.cuda.is_available()
    device: str = 'cuda:0' if cuda_available else 'cpu'

    gpu_info: dict[str, Any] = {}
    if cuda_available:
        gpu_info['device'] = device
        gpu_info['device_name'] = torch.cuda.get_device_name(0)
        gpu_info['total_memory_gb'] = torch.cuda.get_device_properties(0).total_memory / 1e9
        cuda_ver: str | None = getattr(torch.version, 'cuda', None)  # type: ignore[attr-defined]
        gpu_info['cuda_version'] = cuda_ver
        gpu_info['cudnn_version'] = torch.backends.cudnn.version()
        gpu_info['cudnn_enabled'] = torch.backends.cudnn.enabled
    else:
        gpu_info['device'] = 'cpu'
        gpu_info['device_name'] = 'CPU (no GPU)'
        gpu_info['total_memory_gb'] = None
        gpu_info['cuda_version'] = None

    return gpu_info


def get_training_config(agent_type: str = 'SAC') -> dict[str, Any]:
    """
    Obtener configuración de entrenamiento optimizada según GPU disponible.

    Args:
        agent_type: 'SAC', 'PPO', o 'A2C'

    Returns:
        Dict con configuración de entrenamiento
    """

    gpu_info: dict[str, Any] = detect_gpu()
    device: str = gpu_info['device']
    is_gpu: bool = device.startswith('cuda')

    # Configuración base para todos los agentes
    base_config: dict[str, Any] = {
        'device': device,
        'gpu_info': gpu_info,
        'is_gpu': is_gpu,
        'output_dir': Path(f'outputs/{agent_type.lower()}_training'),
        'checkpoint_dir': Path(f'checkpoints/{agent_type}'),
    }

    # Configuración específica por agente y device
    agent_type = agent_type.upper()

    if agent_type == 'SAC':
        if is_gpu:
            # GPU optimizado
            config = {
                **base_config,
                'learning_rate': 3e-4,
                'batch_size': 128,
                'buffer_size': 2000000,
                'gradient_steps': 1,
                'train_freq': 8,
                'network_arch': [512, 512],
                'tau': 0.005,
                'gamma': 0.99,
                'ent_coef': 0.2,
                'target_entropy': 'auto',
                'max_episodes': 50,
                'use_sde': False,
                'sde_sample_freq': -1,
                'tensorboard_log': Path('outputs/tensorboard/sac_gpu'),
                'verbose': 1,
                'notes': 'GPU RTX 4060 - optimizado para velocidad'
            }
        else:
            # CPU optimizado
            config = {
                **base_config,
                'learning_rate': 3e-4,
                'batch_size': 64,
                'buffer_size': 1000000,
                'gradient_steps': 1,
                'train_freq': 4,
                'network_arch': [256, 256],
                'tau': 0.005,
                'gamma': 0.99,
                'ent_coef': 0.2,
                'target_entropy': 'auto',
                'max_episodes': 50,
                'use_sde': False,
                'sde_sample_freq': -1,
                'tensorboard_log': Path('outputs/tensorboard/sac_cpu'),
                'verbose': 1,
                'notes': 'CPU mode - parámetros conservadores'
            }

    elif agent_type == 'PPO':
        if is_gpu:
            config = {
                **base_config,
                'learning_rate': 3e-4,
                'batch_size': 128,
                'n_steps': 2048,
                'n_epochs': 20,
                'gae_lambda': 0.95,
                'gamma': 0.99,
                'clip_range': 0.2,
                'ent_coef': 0.0,
                'network_arch': [512, 512],
                'max_episodes': 50,
                'tensorboard_log': Path('outputs/tensorboard/ppo_gpu'),
                'verbose': 1,
                'notes': 'GPU optimized PPO'
            }
        else:
            config = {
                **base_config,
                'learning_rate': 3e-4,
                'batch_size': 64,
                'n_steps': 512,
                'n_epochs': 10,
                'gae_lambda': 0.95,
                'gamma': 0.99,
                'clip_range': 0.2,
                'ent_coef': 0.0,
                'network_arch': [256, 256],
                'max_episodes': 50,
                'tensorboard_log': Path('outputs/tensorboard/ppo_cpu'),
                'verbose': 1,
                'notes': 'CPU optimized PPO'
            }

    elif agent_type == 'A2C':
        if is_gpu:
            config = {
                **base_config,
                'learning_rate': 7e-4,
                'batch_size': 128,
                'n_steps': 20,
                'gae_lambda': 0.95,
                'gamma': 0.99,
                'ent_coef': 0.0,
                'network_arch': [256, 256],
                'max_episodes': 50,
                'tensorboard_log': Path('outputs/tensorboard/a2c_gpu'),
                'verbose': 1,
                'notes': 'GPU optimized A2C'
            }
        else:
            config = {
                **base_config,
                'learning_rate': 7e-4,
                'batch_size': 64,
                'n_steps': 20,
                'gae_lambda': 0.95,
                'gamma': 0.99,
                'ent_coef': 0.0,
                'network_arch': [256, 256],
                'max_episodes': 50,
                'tensorboard_log': Path('outputs/tensorboard/a2c_cpu'),
                'verbose': 1,
                'notes': 'CPU optimized A2C'
            }
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")

    # Crear directorios
    config['output_dir'].mkdir(parents=True, exist_ok=True)
    config['checkpoint_dir'].mkdir(parents=True, exist_ok=True)

    return config


def print_gpu_config():
    """Imprimir configuración GPU detectada."""
    gpu_info = detect_gpu()

    print("\n" + "="*80)
    print("GPU/CUDA CONFIGURATION SUMMARY")
    print("="*80 + "\n")

    print(f"Device: {gpu_info['device']}")
    print(f"Device Name: {gpu_info['device_name']}")

    if gpu_info.get('total_memory_gb'):
        print(f"Total Memory: {gpu_info['total_memory_gb']:.1f} GB")

    if gpu_info.get('cuda_version'):
        print(f"CUDA Version: {gpu_info['cuda_version']}")
        print(f"cuDNN Version: {gpu_info['cudnn_version']}")
        print(f"cuDNN Enabled: {gpu_info['cudnn_enabled']}")

    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    import json

    print_gpu_config()

    # Mostrar configuración de cada agente
    for agent in ['SAC', 'PPO', 'A2C']:
        config = get_training_config(agent)
        print(f"{agent} Configuration:")
        print(f"  Device: {config['device']}")
        print(f"  Batch Size: {config['batch_size']}")
        print(f"  Learning Rate: {config['learning_rate']}")
        print(f"  Network: {config['network_arch']}")
        print()
