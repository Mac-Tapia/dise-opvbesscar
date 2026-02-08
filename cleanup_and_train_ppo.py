#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cleanup PPO Checkpoints and Launch Training
Limpia directorios de checkpoints y lanza entrenamiento PPO
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

def cleanup_ppo_checkpoints():
    """Clean PPO checkpoint directory"""
    ppo_dir = Path('checkpoints/PPO')
    
    print("=" * 80)
    print("LIMPIEZA DE CHECKPOINTS Y LANZAMIENTO DE ENTRENAMIENTO PPO")
    print("=" * 80)
    print()
    
    print("[1] Limpiando checkpoints PPO...")
    if ppo_dir.exists():
        try:
            shutil.rmtree(ppo_dir, ignore_errors=True)
            print("    ✅ Directorio removido")
        except Exception as e:
            print(f"    ⚠️  Error removiendo: {e}")
    else:
        print("    ℹ️  Directorio no encontrado (primera ejecución)")
    
    # Create fresh directory
    ppo_dir.mkdir(parents=True, exist_ok=True)
    print("    ✅ Directorio PPO creado vacío")
    print()
    
    # Clean outputs
    print("[2] Limpiando outputs/ppo_training...")
    output_dir = Path('outputs/ppo_training')
    if output_dir.exists():
        for file_pattern in ['*.csv', '*.json', 'trace*.txt']:
            for f in output_dir.glob(file_pattern):
                try:
                    f.unlink()
                except:
                    pass
        print("    ✅ Outputs anteriores limpios")
    output_dir.mkdir(parents=True, exist_ok=True)
    print()
    
    # Verify
    print("[3] Verificando estructura...")
    ppo_files = list(ppo_dir.glob('*'))
    print(f"    Checkpoints PPO: {len(ppo_files)} archivos")
    print()
    
    return True


def launch_training():
    """Launch PPO training"""
    print("=" * 80)
    print("INICIANDO ENTRENAMIENTO PPO - MULTIOBJETIVO CON DATOS REALES")
    print("=" * 80)
    print()
    print("⏱️  Duración estimada: 25-30 minutos (GPU RTX 4060)")
    print("📊 Episodios: 10 × 8,760 timesteps = 87,600 pasos")
    print("🎯 Objetivo: Minimizar CO2 grid + Maximizar solar self-consumption")
    print()
    print("Inicio:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)
    print()
    
    try:
        result = subprocess.run(
            [sys.executable, "train_ppo_multiobjetivo.py"],
            cwd=".",
            check=False
        )
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error lanzando entrenamiento: {e}")
        return False


if __name__ == "__main__":
    # Step 1: Cleanup
    if cleanup_ppo_checkpoints():
        # Step 2: Launch training
        success = launch_training()
        
        print()
        print("=" * 80)
        if success:
            print("✅ ENTRENAMIENTO COMPLETADO EXITOSAMENTE")
            print("   Resultados guardados en: outputs/ppo_training/")
        else:
            print("❌ ENTRENAMIENTO FINALIZADO (revisar logs)")
        print("=" * 80)
        
        sys.exit(0 if success else 1)
    else:
        print("❌ Error en limpieza de checkpoints")
        sys.exit(1)
