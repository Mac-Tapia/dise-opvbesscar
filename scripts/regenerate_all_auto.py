#!/usr/bin/env python
"""
REGENERADOR COMPLETO V5.8 - Un comando para TODO.

Flujo automático:
1. Detecta cambios en TODOS los datasets (BESS, Solar, EV)
2. Si BESS cambió: ejecuta transform_dataset_v57
3. Regenera gráficas de balance energético
4. Todo sin intervención manual

USO:
    python scripts/regenerate_all_auto.py

DATASETS MONITOREADOS:
- ✓ BESS: data/oe2/bess/bess_ano_2024.csv
- ✓ SOLAR: data/interim/oe2/solar/pv_generation_timeseries.csv  
- ✓ EV: data/oe2/chargers/chargers_ev_ano_2024_v3.csv

SALIDA:
- Dataset transformado: data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv
- Gráficas: reports/balance_energetico/*.png (15 archivos)
"""
from __future__ import annotations

import sys
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.utils.dataset_change_detector import DatasetChangeDetector


def run_command(cmd: list[str], description: str) -> bool:
    """Ejecuta comando y retorna True si éxito."""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(cmd, capture_output=False, text=True, cwd=ROOT)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error ejecutando: {e}")
        return False


def main():
    """Pipeline completo auto."""
    
    print("\n" + "=" * 80)
    print("🚀 REGENERADOR COMPLETO v5.8 - Todo Automatizado")
    print("=" * 80)
    print(f"⏰ Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. DETECTAR CAMBIOS
    print("\n📊 Detectando cambios en datasets...")
    detector = DatasetChangeDetector(workspace_root=ROOT)
    changed = detector.get_changed_datasets()
    
    if not changed:
        print("✓ Sin cambios detectados")
        print("  → Nada que regenerar")
        return
    
    print(f"⚠️  Cambios detectados:")
    for ds in changed:
        print(f"   • {ds}")
    
    # 2. Si BESS cambió, transformar dataset
    if "BESS" in changed or "TRANSFORMED_BESS" in changed:
        print("\n📦 BESS cambió → Regenerando dataset transformado...")
        if not run_command(
            ["python", "scripts/transform_dataset_v57.py"],
            "Transformación de dataset BESS"
        ):
            print("❌ Error en transformación - abortar")
            return
    
    # 3. Siempre regenerar gráficas si hay cambios
    print("\n🎨 Regenerando todas las gráficas...")
    if not run_command(
        ["python", "scripts/regenerate_graphics_v57.py"],
        "Regeneración de gráficas"
    ):
        print("❌ Error en regeneración - abortar")
        return
    
    # 4. Resumen
    print("\n" + "=" * 80)
    print("✅ REGENERACIÓN COMPLETA EXITOSA")
    print("=" * 80)
    print(f"\n📁 Outputs:")
    print(f"   • Dataset: data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv")
    print(f"   • Gráficas: reports/balance_energetico/ (15 PNG)")
    print(f"   • Estado: data/processed/citylearn/.dataset_state.json")
    print(f"\n⏰ Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelado por usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)
