#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRIPT WRAPPER - Activar ambiente y lanzar entrenamiento SAC
Asegura que siempre se use el .venv con PYTHONPATH configurado
"""
import os
import sys
import subprocess
from pathlib import Path

# Configurar PYTHONPATH PRIMERO
venv_python = Path(".venv") / "Scripts" / "python.exe"
repo_root = Path(__file__).parent

os.environ['PYTHONPATH'] = str(repo_root)
os.environ['PYTHONIOENCODING'] = 'utf-8'

print("="*80)
print("  🚀 ACTIVACIÓN DE AMBIENTE + LANZAMIENTO ENTRENAMIENTO SAC")
print("="*80)
print()

print("✅ Configuración de entorno:")
print(f"   PYTHONPATH = {os.environ.get('PYTHONPATH')}")
print(f"   Venv Python = {venv_python}")
print(f"   Python version:", end=" ")
sys.stdout.flush()

# Verificar Python en venv
result = subprocess.run([str(venv_python), "--version"], capture_output=True, text=True)
print(result.stdout.strip())
print()

# Lanzar script de entrenamiento
print("="*80)
print("  📊 LANZANDO ENTRENAMIENTO SAC CON DATOS REALES OE2")
print("="*80)
print()

cmd = [str(venv_python), "scripts/train/train_sac_multiobjetivo.py"]
subprocess.run(cmd)
