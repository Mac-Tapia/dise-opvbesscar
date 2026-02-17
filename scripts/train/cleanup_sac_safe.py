#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LIMPIEZA SEGURA DE CHECKPOINTS SAC SOLAMENTE
Protege PPO y A2C, limpia solo SAC
"""
from pathlib import Path
import shutil

print("="*80)
print("LIMPIEZA SEGURA CHECKPOINTS - SAC ONLY")
print("="*80)
print()

checkpoint_dir = Path('checkpoints')

# 1. VERIFICAR ESTRUCTURA
print("1. VALIDANDO CHECKPOINTS EXISTENTES:")
print("-" * 80)

agents = ['SAC', 'PPO', 'A2C']
for agent in agents:
    agent_dir = checkpoint_dir / agent
    if agent_dir.exists():
        files = list(agent_dir.glob('*.zip'))
        print(f"  [{agent}] {len(files)} checkpoints encontrados")
        if files:
            for f in files[:3]:  # Mostrar primeros 3
                print(f"      - {f.name}")
            if len(files) > 3:
                print(f"      ... y {len(files)-3} más")
    else:
        print(f"  [{agent}] No existe directorio")

print()

# 2. CONFIRMAR LIMPIEZA
print("2. PLAN DE LIMPIEZA:")
print("-" * 80)
print("  ✓ SAC:  LIMPIAR TODOS los checkpoints")
print("  ✓ PPO:  PROTEGER (no tocar)")
print("  ✓ A2C:  PROTEGER (no tocar)")
print()

# 3. EJECUTAR LIMPIEZA
print("3. EJECUTANDO LIMPIEZA:")
print("-" * 80)

sac_dir = checkpoint_dir / 'SAC'
if sac_dir.exists():
    sac_files = list(sac_dir.glob('*.zip'))
    if sac_files:
        print(f"  Eliminando {len(sac_files)} checkpoints SAC...")
        for f in sac_files:
            try:
                f.unlink()
                print(f"    ✓ {f.name}")
            except Exception as e:
                print(f"    ✗ {f.name} - Error: {e}")
        print(f"  [OK] {len(sac_files)} archivos eliminados")
    else:
        print("  [OK] No hay checkpoints SAC para limpiar")
else:
    print("  [OK] Directorio SAC no existe (crear al iniciar entrenamiento)")

print()

# 4. VALIDAR OTROS AGENTES INTACTOS
print("4. VALIDACIÓN POST-LIMPIEZA:")
print("-" * 80)

for agent in ['PPO', 'A2C']:
    agent_dir = checkpoint_dir / agent
    if agent_dir.exists():
        files = list(agent_dir.glob('*.zip'))
        print(f"  [{agent}] ✓ PROTEGIDO - {len(files)} checkpoints intactos")
    else:
        print(f"  [{agent}] INFO - Directorio no existe (normal si no se ha entrenado)")

print()
print("="*80)
print("LIMPIEZA COMPLETA")
print("="*80)
print()
