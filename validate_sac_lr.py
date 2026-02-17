#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VALIDACION RAPIDA: Confirmar learning_rate=5e-4 en SACConfig.for_gpu()
"""

from pathlib import Path
import sys

workspace_root = Path(__file__).parent
sys.path.insert(0, str(workspace_root))

# Importar el script de SAC
from scripts.train.train_sac_multiobjetivo import SACConfig, DEVICE
import torch

print("\n" + "="*80)
print("VALIDACION LEARNING_RATE SAC OPCION B")
print("="*80 + "\n")

# Crear configuración
print("[1] Detectando dispositivo...")
print(f"    DEVICE: {DEVICE}")
print(f"    GPU disponible: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"    GPU: {torch.cuda.get_device_name(0)}")

print("\n[2] Creando SACConfig...")
sac_config = SACConfig.for_gpu() if DEVICE == 'cuda' else SACConfig.for_cpu()

print(f"\n[3] PARAMETROS OPCION B:")
print(f"    Learning rate:        {sac_config.learning_rate} (esperado: 5e-4)")
print(f"    Learning rate valor:  {float(sac_config.learning_rate):.2e}")
print(f"    Buffer size:          {sac_config.buffer_size:,} (esperado: 600000)")
print(f"    Batch size:           {sac_config.batch_size} (esperado: 128)")
print(f"    Train freq:           {sac_config.train_freq} (esperado: (1, 'step'))")
print(f"    Gradient steps:       {sac_config.gradient_steps} (esperado: 2)")
print(f"    Tau:                  {sac_config.tau} (esperado: 0.005)")
print(f"    Target entropy:       {sac_config.target_entropy} (esperado: -20.0)")
print(f"    Entropy coef:         {sac_config.ent_coef} (esperado: 'auto')")
print(f"    SDE enabled:          {sac_config.use_sde} (esperado: True)")
print(f"    Networks pi:          {sac_config.policy_kwargs['net_arch']['pi']} (esperado: [512, 512])")
print(f"    Networks qf:          {sac_config.policy_kwargs['net_arch']['qf']} (esperado: [512, 512])")
print(f"    log_std_init:         {sac_config.policy_kwargs['log_std_init']} (esperado: 0.0)")

# Validacion
print("\n[4] VALIDACION:")
checks = [
    ("Learning rate = 5e-4", float(sac_config.learning_rate) == 5e-4),
    ("Buffer size = 600K", sac_config.buffer_size == 600_000),
    ("Batch size = 128", sac_config.batch_size == 128),
    ("Train freq = (1, 'step')", sac_config.train_freq == (1, 'step')),
    ("Gradient steps = 2", sac_config.gradient_steps == 2),
    ("Tau = 0.005", sac_config.tau == 0.005),
    ("Target entropy = -20", sac_config.target_entropy == -20.0),
    ("Entropy coef = 'auto'", sac_config.ent_coef == 'auto'),
    ("SDE = True", sac_config.use_sde == True),
    ("Networks = 512x512", sac_config.policy_kwargs['net_arch']['pi'] == [512, 512]),
]

all_ok = True
for check_name, result in checks:
    status = "✅" if result else "❌"
    print(f"    {status} {check_name}")
    if not result:
        all_ok = False

print("\n" + "="*80)
if all_ok:
    print("✅ RESULTADO: OPCION B CORRECTAMENTE CONFIGURADA")
    print("   SAC se entrenará con:")
    print("   - Learning rate: 5e-4 (AGRESIVO para romper óptimo local)")
    print("   - Exploración: target_entropy=-20.0 (50% más que v9.2)")
    print("   - Training: train_freq=(1,step) (4x más updates)")
    print("   - Networks: 512x512 (máxima expresividad)")
else:
    print("❌ ERROR: Configuración NO coincide con OPCION B")
    print("   Revisar SACConfig.for_gpu()")

print("="*80 + "\n")
