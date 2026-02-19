#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2C Training Launcher - Entrenamiento Continuo con Dataset OE2
Detecta checkpoint previo y continúa o crea nuevo agente automáticamente.

Uso:
    python train_a2c_launcher.py                    # Entrenar 1 run
    python train_a2c_launcher.py --runs 5          # Entrenar 5 runs consecutivos
    python train_a2c_launcher.py --help             # Ver opciones
"""

from __future__ import annotations

import sys
from pathlib import Path
import argparse
import subprocess
import time
from datetime import datetime, timedelta

# Asegurar que el proyecto está en PATH
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def check_dependencies() -> bool:
    """Verificar que las dependencias necesarias están disponibles."""
    print("[CHECK] Verificando dependencias...")
    try:
        import torch
        import numpy as np
        import pandas as pd
        from stable_baselines3 import A2C
        from gymnasium import spaces
        
        print(f"  [OK] PyTorch: {torch.__version__}")
        print(f"  [OK] NumPy: {np.__version__}")
        print(f"  [OK] Pandas: {pd.__version__}")
        print(f"  [OK] Stable-Baselines3: OK")
        print(f"  [OK] Gymnasium: OK")
        
        if torch.cuda.is_available():
            print(f"  [OK] CUDA: {torch.cuda.get_device_name(0)}")
        else:
            print(f"  [!] GPU no disponible - usando CPU")
        
        return True
    except ImportError as e:
        print(f"  [ERROR] Falta importar: {e}")
        return False


def check_data_files() -> bool:
    """Verificar que los archivos de datos OE2 existen."""
    print("\n[CHECK] Verificando archivos de datos OE2...")
    
    required_files = [
        "data/oe2/Generacionsolar/pv_generation_citylearn2024.csv",
        "data/oe2/cargadores/chargers_ev_ano_2024_v3.csv",
        "data/oe2/batteriaalmacenamiento/bess_ano_2024.csv",
        "data/oe2/demandamallkwh/demandamallhorakwh.csv",
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = Path(file_path)
        if full_path.exists():
            file_size_mb = full_path.stat().st_size / (1024**2)
            print(f"  [OK] {file_path} ({file_size_mb:.2f} MB)")
        else:
            print(f"  [!] FALTA: {file_path}")
            all_exist = False
    
    return all_exist


def create_output_dirs() -> None:
    """Crear directorios de salida si no existen."""
    output_dirs = [
        "outputs/a2c_training",
        "checkpoints/A2C",
        "logs",
    ]
    
    for dir_path in output_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"  [OK] {dir_path}/")


def get_checkpoint_status() -> dict[str, any]:
    """Obtener información del checkpoint actual."""
    checkpoint_dir = Path("checkpoints/A2C")
    
    status = {
        "has_checkpoint": False,
        "checkpoint_path": None,
        "checkpoint_age": None,
        "num_timesteps": None,
    }
    
    if not checkpoint_dir.exists():
        return status
    
    # Buscar checkpoint en orden de preferencia
    final_model = checkpoint_dir / "a2c_final_model.zip"
    best_model = checkpoint_dir / "best_model.zip"
    
    checkpoint = None
    if final_model.exists():
        checkpoint = final_model
    elif best_model.exists():
        checkpoint = best_model
    else:
        # Buscar ultimo checkpoint generado
        checkpoints = list(checkpoint_dir.glob("a2c_model_*.zip"))
        if checkpoints:
            checkpoint = max(checkpoints, key=lambda p: p.stat().st_mtime)
    
    if checkpoint:
        status["has_checkpoint"] = True
        status["checkpoint_path"] = checkpoint
        
        # Edad del checkpoint
        checkpoint_time = checkpoint.stat().st_mtime
        current_time = time.time()
        age_seconds = current_time - checkpoint_time
        age_minutes = age_seconds / 60
        status["checkpoint_age"] = f"{age_minutes:.1f} min"
    
    return status


def run_training(run_number: int, total_runs: int) -> bool:
    """Ejecutar un training run."""
    print(f"\n{'='*80}")
    print(f"RUN {run_number}/{total_runs} - A2C Training with OE2 Dataset")
    print(f"{'='*80}")
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Obtener estado de checkpoint
    checkpoint_status = get_checkpoint_status()
    if checkpoint_status["has_checkpoint"]:
        print(f"[RESUME] Encontrado checkpoint:")
        print(f"  - Path: {checkpoint_status['checkpoint_path'].name}")
        print(f"  - Edad: {checkpoint_status['checkpoint_age']}")
        print(f"  - Modo: ENTRENAMIENTO CONTINUO")
    else:
        print(f"[NEW] Creando nuevo agente")
        print(f"  - Modo: PRIMER ENTRENAMIENTO")
    print()
    
    # Ejecutar training script
    try:
        result = subprocess.run(
            [sys.executable, "scripts/train/train_a2c.py"],
            capture_output=False,
            timeout=3600  # 1 hora max por run
        )
        
        if result.returncode == 0:
            print()
            print(f"[OK] Run {run_number} completado exitosamente")
            return True
        else:
            print()
            print(f"[ERROR] Run {run_number} falló con código {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print()
        print(f"[ERROR] Run {run_number} excedió timeout (1 hora)")
        return False
    except Exception as e:
        print()
        print(f"[ERROR] Run {run_number} falló: {e}")
        return False


def main() -> None:
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="A2C Training Launcher - Entrenamiento continuo con datos OE2"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Número de training runs consecutivos (default: 1)",
    )
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Saltar verificaciones de dependencias y datos",
    )
    
    args = parser.parse_args()
    
    print("="*80)
    print("A2C TRAINING LAUNCHER - PVBESSCAR")
    print("="*80)
    print()
    
    # Verificaciones
    if not args.skip_checks:
        if not check_dependencies():
            print("\n[!] Algunas dependencias faltan. Instala:")
            print("    pip install -r requirements.txt")
            print("    pip install -r requirements-training.txt")
            sys.exit(1)
        
        if not check_data_files():
            print("\n[!] Falta algún archivo de datos OE2. Descarga desde:")
            print("    https://github.com/Mac-Tapia/dise-opvbesscar/releases/tag/v5.4-oe2-data")
            sys.exit(1)
        
        print("\n[OK] Todas las verificaciones pasaron")
    else:
        print("[SKIP] Saltando verificaciones")
    
    # Crear directorios
    print()
    print("[SETUP] Creando directorios de salida...")
    create_output_dirs()
    
    # Entrenar
    print()
    print(f"[TRAIN] Iniciando {args.runs} training run(s)")
    print()
    
    start_time = datetime.now()
    successful_runs = 0
    
    for run_num in range(1, args.runs + 1):
        if run_training(run_num, args.runs):
            successful_runs += 1
        
        # Esperar entre runs (dar tiempo a guardar archivos)
        if run_num < args.runs:
            print()
            print(f"[WAIT] Esperando 10 segundos antes del siguiente run...")
            time.sleep(10)
    
    # Resumen
    end_time = datetime.now()
    duration = end_time - start_time
    
    print()
    print("="*80)
    print("RESUMEN DE ENTRENAMIENTO")
    print("="*80)
    print(f"Runs completados: {successful_runs}/{args.runs}")
    print(f"Tiempo total: {duration}")
    print(f"Timesteps totales: {successful_runs * 87600:,}")
    print()
    
    if successful_runs == args.runs:
        print("[OK] ENTRENAMIENTO COMPLETADO EXITOSAMENTE")
        
        # Mostrar archivos generados
        print()
        print("Archivos generados:")
        output_dir = Path("outputs/a2c_training")
        if output_dir.exists():
            for file in sorted(output_dir.glob("*a2c*")):
                size_mb = file.stat().st_size / (1024**2)
                print(f"  - {file.name} ({size_mb:.1f} MB)")
        
        checkpoint_dir = Path("checkpoints/A2C")
        if checkpoint_dir.exists():
            final_model = checkpoint_dir / "a2c_final_model.zip"
            if final_model.exists():
                size_mb = final_model.stat().st_size / (1024**2)
                print(f"  - {final_model.name} ({size_mb:.1f} MB)")
        
        print()
        print("Próximos pasos:")
        print("  1. Analizar resultados: python scripts/analyze_training_results.py")
        print("  2. Continuar entrenando: python train_a2c_launcher.py --runs 3")
        print("  3. Ver logs: tail -f outputs/a2c_training/result_a2c.json")
    else:
        print(f"[!] {args.runs - successful_runs} run(s) fallaron")
        sys.exit(1)


if __name__ == "__main__":
    main()

