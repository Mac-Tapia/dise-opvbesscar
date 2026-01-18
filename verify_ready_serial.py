#!/usr/bin/env python3
"""
Verificación RÁPIDA pre-lanzamiento: GPU, archivos, config.
Ejecución: python verify_ready_serial.py
"""

import sys
import json
from pathlib import Path
import torch

def check_cuda():
    """Verificar CUDA/GPU."""
    cuda_ok = torch.cuda.is_available()
    if cuda_ok:
        gpu_count = torch.cuda.device_count()
        device_name = torch.cuda.get_device_name(0)
        mem_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        return True, f"{gpu_count} GPU(s) - {device_name} ({mem_gb:.1f} GB)"
    return False, "CPU only"

def check_files():
    """Verificar archivos críticos."""
    required = {
        "Config": "configs/default.yaml",
        "Schema Grid": "data/processed/citylearn/iquitos_ev_mall/schema_grid_only.json",
        "Schema PV+BESS": "data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json",
        "OE2 Solar": "data/interim/oe2/solar/solar_results.json",
        "OE2 BESS": "data/interim/oe2/bess/bess_results.json",
        "OE2 Chargers": "data/interim/oe2/chargers/chargers_results.json",
    }
    
    missing = []
    for name, path in required.items():
        if not Path(path).exists():
            missing.append((name, path))
    
    return len(missing) == 0, missing

def check_config():
    """Verificar configuración OE3."""
    config_path = Path("configs/default.yaml")
    if not config_path.exists():
        return False, "Config no existe"
    
    import yaml
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    
    agents = cfg.get("oe3", {}).get("evaluation", {}).get("agents", [])
    return True, f"Agentes: {', '.join(agents)}"

def main():
    print("\n" + "=" * 60)
    print("VERIFICACIÓN PRE-LANZAMIENTO")
    print("=" * 60 + "\n")
    
    # Check Python
    py_version = sys.version.split()[0]
    print(f"✓ Python: {py_version}")
    
    # Check CUDA
    cuda_ok, cuda_msg = check_cuda()
    status = "✓" if cuda_ok else "⚠"
    print(f"{status} GPU: {cuda_msg}")
    
    # Check files
    files_ok, missing = check_files()
    if files_ok:
        print("✓ Todos los archivos requeridos")
    else:
        print("✗ Archivos faltantes:")
        for name, path in missing:
            print(f"    - {name}: {path}")
        return False
    
    # Check config
    try:
        cfg_ok, cfg_msg = check_config()
        if cfg_ok:
            print(f"✓ Config: {cfg_msg}")
        else:
            print(f"✗ Config: {cfg_msg}")
            return False
    except Exception as e:
        print(f"✗ Error leyendo config: {e}")
        return False
    
    # Dataset check
    dataset_dir = Path("data/processed/citylearn/iquitos_ev_mall")
    csv_count = len(list(dataset_dir.glob("*.csv")))
    print(f"✓ Dataset: {csv_count} CSV files")
    
    # Space check
    output_dir = Path("outputs/oe3")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"✓ Output dir: {output_dir.resolve()}")
    
    print("\n" + "=" * 60)
    print("✓ LISTO PARA LANZAR ENTRENAMIENTO")
    print("=" * 60)
    print("\nComandos:")
    print("  PowerShell: .\\train_agents_serial.ps1")
    print("  Python:     python train_agents_serial_gpu.py")
    print("=" * 60 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
