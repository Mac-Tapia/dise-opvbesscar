#!/usr/bin/env python3
"""
VALIDATION SCRIPT - SAC Training Pre-Check
===========================================
Ejecutar: python VALIDAR_SAC_TRAINING.py

Este script valida que todo está listo para entrenar SAC sin riesgos.
"""

import sys
from pathlib import Path
import json

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def check(condition, message):
    """Print check result"""
    if condition:
        print(f"{GREEN}✓{RESET} {message}")
        return True
    else:
        print(f"{RED}✗{RESET} {message}")
        return False

def section(title):
    """Print section header"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

def main():
    print(f"\n{YELLOW}SAC TRAINING VALIDATION{RESET}")
    print("="*60)
    
    all_ok = True
    workspace = Path("d:/diseñopvbesscar")
    
    # ===== SECTION 1: FILE STRUCTURE =====
    section("1. ESTRUCTURA DE ARCHIVOS")
    
    files_to_check = {
        "scripts/train/train_sac_multiobjetivo.py": "Script de entrenamiento SAC",
        "src/agents/sac.py": "Módulo SAC",
        "src/dataset_builder_citylearn/rewards.py": "Rewards calculator",
        "src/dataset_builder_citylearn/observations.py": "Observations builder",
        "configs/default.yaml": "Config por defecto",
    }
    
    for file_path, description in files_to_check.items():
        full_path = workspace / file_path
        exists = full_path.exists()
        all_ok &= check(exists, f"{description} → {file_path}")
    
    # ===== SECTION 2: DATA FILES =====
    section("2. ARCHIVOS DE DATOS")
    
    data_files = {
        "data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv": "Solar generation (16 cols)",
        "data/oe2/chargers/chargers_ev_ano_2024_v3.csv": "Chargers dataset (343 cols)",
        "data/oe2/demandamallkwh/demandamallhorakwh.csv": "Mall demand (6 cols)",
        "data/oe2/bess/bess_ano_2024.csv": "BESS simulation (25 cols)",
    }
    
    for file_path, description in data_files.items():
        full_path = workspace / file_path
        exists = full_path.exists()
        all_ok &= check(exists, f"{description} → {file_path}")
        
        # Validate row count if exists
        if exists and file_path.endswith(".csv"):
            try:
                import pandas as pd
                df = pd.read_csv(full_path)
                rows_ok = len(df) == 8760
                all_ok &= check(
                    rows_ok,
                    f"  └─ {len(df)} rows (expected 8760)"
                )
            except Exception as e:
                all_ok &= check(False, f"  └─ Error reading: {e}")
    
    # ===== SECTION 3: PYTHON ENVIRONMENT =====
    section("3. ENTORNO PYTHON")
    
    try:
        import pandas as pd
        check(True, f"pandas: {pd.__version__}")
    except ImportError:
        all_ok &= check(False, "pandas: NOT INSTALLED")
    
    try:
        import numpy as np
        check(True, f"numpy: {np.__version__}")
    except ImportError:
        all_ok &= check(False, "numpy: NOT INSTALLED")
    
    try:
        from stable_baselines3 import SAC
        check(True, f"stable-baselines3: {SAC.__version__}")
    except ImportError:
        all_ok &= check(False, "stable-baselines3: NOT INSTALLED")
    
    try:
        import gymnasium
        check(True, f"gymnasium: {gymnasium.__version__}")
    except ImportError:
        all_ok &= check(False, "gymnasium: NOT INSTALLED")
    
    try:
        import torch
        check(True, f"torch: {torch.__version__}")
        
        # Check GPU
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0)
            check(True, f"  └─ CUDA available: {gpu_count}x {gpu_name}")
        else:
            print(f"{YELLOW}⚠{RESET}  CUDA NOT available (will use CPU - SLOW)")
    except ImportError:
        check(False, "torch: NOT INSTALLED (required for GPU training)")
    
    try:
        import yaml
        check(True, f"PyYAML: {yaml.__version__}")
    except ImportError:
        all_ok &= check(False, "PyYAML: NOT INSTALLED")
    
    # ===== SECTION 4: CODE VALIDATION =====
    section("4. VALIDACIÓN DE CÓDIGO")
    
    # Check if train script can be parsed
    try:
        train_script = workspace / "scripts/train/train_sac_multiobjetivo.py"
        with open(train_script, 'r') as f:
            code = f.read()
        
        # Check for key components
        has_main = "def main():" in code
        has_sac_import = "from stable_baselines3 import SAC" in code
        has_oe2_env = "class RealOE2Environment" in code
        
        check(has_main, "train_sac_multiobjetivo.py has main() function")
        check(has_sac_import, "SAC import statement exists")
        check(has_oe2_env, "RealOE2Environment class defined")
        
        all_ok &= (has_main and has_sac_import and has_oe2_env)
        
    except Exception as e:
        all_ok &= check(False, f"Error reading train script: {e}")
    
    # ===== SECTION 5: CHECKPOINT DIRECTORY =====
    section("5. DIRECTORIO DE CHECKPOINTS")
    
    checkpoint_dir = workspace / "checkpoints/SAC"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    check(checkpoint_dir.exists(), f"Directory exists: {checkpoint_dir}")
    
    # Count existing checkpoints
    existing_checkpoints = list(checkpoint_dir.glob("*.zip"))
    if existing_checkpoints:
        print(f"{YELLOW}!{RESET}  Found {len(existing_checkpoints)} existing checkpoint(s)")
        for cp in existing_checkpoints:
            print(f"    └─ {cp.name}")
        print(f"{YELLOW}⚠{RESET}  Training will RESUME from latest, not start fresh")
        print(f"    To start fresh, delete these files first")
    else:
        check(True, "No existing checkpoints (will start fresh)")
    
    # ===== SECTION 6: KEY PARAMETERS VALIDATION =====
    section("6. PARÁMETROS CLAVE SAC")
    
    validation_ok = True
    
    try:
        # Extract SAC config from train script
        with open(workspace / "scripts/train/train_sac_multiobjetivo.py", 'r') as f:
            content = f.read()
        
        # Check REWARD_SCALE
        if "REWARD_SCALE = 0.1" in content:
            check(True, "REWARD_SCALE = 0.1 (optimal)")
        elif "REWARD_SCALE = 0.01" in content:
            print(f"{YELLOW}⚠{RESET}  REWARD_SCALE = 0.01 (too small, change to 0.1)")
            validation_ok = False
        else:
            print(f"{YELLOW}?{RESET}  REWARD_SCALE not found (should be 0.1)")
        
        # Check if agent.learn() is called
        if "agent.learn(" in content:
            check(True, "agent.learn() is called (training will operate)")
        else:
            print(f"{RED}✗{RESET}  agent.learn() NOT FOUND (training won't run!)")
            validation_ok = False
        
        # Check if environment is created
        if "RealOE2Environment(" in content:
            check(True, "Environment instantiated")
        else:
            print(f"{RED}✗{RESET}  Environment NOT CREATED")
            validation_ok = False
        
        all_ok &= validation_ok
        
    except Exception as e:
        all_ok &= check(False, f"Error validating parameters: {e}")
    
    # ===== SECTION 7: DOCUMENTATION =====
    section("7. DOCUMENTACIÓN DE SOPORTE")
    
    docs = {
        "DIAGNOSTICO_SAC_EPISODE_RETURN_CERO.md": "Diagnosis document",
        "SOLUCION_SAC_FRAGMENTOS.md": "Solution fragments",
        "PLAN_ACCION_SAC_TRAINING.md": "Action plan",
    }
    
    for doc_file, description in docs.items():
        doc_path = workspace / doc_file
        exists = doc_path.exists()
        check(exists, f"{description} → {doc_file}")
        all_ok &= exists
    
    # ===== FINAL SUMMARY =====
    section("RESUMEN FINAL")
    
    if all_ok:
        print(f"\n{GREEN}✓ TODAS LAS VALIDACIONES PASARON{RESET}")
        print(f"  Su sistema está listo para entrenar SAC.")
        print(f"\n{BLUE}Para iniciar entrenamiento, ejecute:{RESET}")
        print(f"  python scripts/train/train_sac_multiobjetivo.py")
        print(f"\n{BLUE}Para monitorear en tiempo real:{RESET}")
        print(f"  tensorboard --logdir=runs/ --port=6006")
        return 0
    else:
        print(f"\n{RED}✗ ALGUNAS VALIDACIONES FALLARON{RESET}")
        print(f"  Por favor, resolva los problemas antes de entrenar.")
        print(f"\n{YELLOW}Pasos de corrección:{RESET}")
        print(f"  1. Instale dependencias: pip install -r requirements.txt")
        print(f"  2. Verifique estructura de carpetas")
        print(f"  3. Descargue datasets si faltan")
        print(f"  4. Aplique cambios de PLAN_ACCION_SAC_TRAINING.md")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n{RED}ERROR: {e}{RESET}")
        sys.exit(2)
