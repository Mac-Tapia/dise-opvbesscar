#!/usr/bin/env python
"""
Regenerador automático de gráficas de BALANCE ENERGÉTICO.

Detecta cambios en TODOS los datasets (BESS, Solar, EV) y regenera gráficas automáticamente
sin necesidad de intervención manual.

USO:
    python scripts/regenerate_balance_auto.py [--force] [--verbose]

CARACTERÍSTICAS:
- ✓ Detecta cambios en: BESS, Solar, EV Chargers
- ✓ Regenera dataset transformado si hay cambios en BESS
- ✓ Regenera gráficas si hay cambios en cualquier dataset  
- ✓ Mantiene estado de datasets para próxima ejecución
- ✓ Reporta cambios detectados en console

LOGS:
- Estado datasets: data/processed/citylearn/.dataset_state.json
"""
from __future__ import annotations

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# Agregar root al path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.utils.dataset_change_detector import DatasetChangeDetector
from src.dimensionamiento.oe2.data_loader import load_balance_data
from src.dimensionamiento.oe2.balance_energetico.balance import BalanceEnergeticoSystem


def main(force_regenerate: bool = False, verbose: bool = False) -> None:
    """Detecta cambios en datasets y regenera gráficas automáticamente."""
    
    print("=" * 80)
    print("AUTO-REGENERACIÓN DE GRÁFICAS DE BALANCE ENERGÉTICO v5.8")
    print("=" * 80)
    print(f"\n⏰ Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. DETECTAR CAMBIOS EN DATASETS
    print("\n📊 Analizando datasets...")
    detector = DatasetChangeDetector(workspace_root=ROOT)
    changed_datasets = detector.get_changed_datasets()
    
    if verbose:
        print("\n   Datasets monitoreados:")
        for name, path in detector.DATASETS.items():
            full_path = ROOT / path
            if full_path.exists():
                info = detector.get_dataset_info(name)
                status = "⚠️  CAMBIO" if name in changed_datasets else "✓"
                size_mb = info['file_size'] / (1024 * 1024)
                print(f"      {status} {name:20s} | {size_mb:6.2f} MB | {Path(path).name}")
            else:
                print(f"      ❌ {name:20s} | NO ENCONTRADO")
    
    # 2. DECIDIR SI REGENERAR
    should_regenerate = force_regenerate or bool(changed_datasets)
    
    if not should_regenerate:
        print("\n✓ Sin cambios en datasets → Sin regeneración necesaria")
        return
    
    if changed_datasets:
        print(f"\n⚠️  Cambios detectados en:")
        for ds in changed_datasets:
            print(f"      • {ds}")
    elif force_regenerate:
        print(f"\n🔄 Regeneración FORZADA (--force)")
    
    # 3. CARGAR DATOS
    print("\n📂 Cargando datasets...")
    try:
        df_balance = load_balance_data(
            bess_csv=ROOT / "data/oe2/bess/bess_ano_2024.csv",
            solar_csv=ROOT / "data/interim/oe2/solar/pv_generation_timeseries.csv",
            ev_load_json=ROOT / "data/interim/oe2/carga_ev/ev_demand_hourly.json",
        )
        print(f"   ✓ Dataset cargado: {len(df_balance)} filas × {len(df_balance.columns)} columnas")
    except Exception as e:
        print(f"\n❌ ERROR: No se pudo cargar datasets")
        print(f"   {e}")
        return
    
    # 4. REGENERAR GRÁFICAS
    print("\n🎨 Regenerando gráficas...")
    try:
        out_dir = ROOT / "reports" / "balance_energetico"
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Instanciar con auto_update=False (ya hemos detectado cambios arriba)
        balance = BalanceEnergeticoSystem(df_balance, auto_update=False)
        
        # Regenerar todas las gráficas
        balance.plot_energy_balance(out_dir)
        
        print(f"\n✅ Gráficas regeneradas en: {out_dir}")
        
        # Listar archivos generados
        png_files = sorted(out_dir.glob("*.png"))
        print(f"\n📦 Archivos generados ({len(png_files)} PNG):")
        for png in png_files:
            size_mb = png.stat().st_size / (1024 * 1024)
            print(f"      ✓ {png.name} ({size_mb:.1f} MB)")
        
    except Exception as e:
        print(f"\n❌ ERROR durante regeneración de gráficas:")
        print(f"   {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return
    
    # 5. REPORTE FINAL
    print("\n" + "=" * 80)
    print("✅ REGENERACIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 80)
    print(f"⏰ Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Auto-regenerador de gráficas de balance energético"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Fuerza regeneración aunque no haya cambios"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Modo verbose (más detalles)"
    )
    
    args = parser.parse_args()
    
    try:
        main(force_regenerate=args.force, verbose=args.verbose)
    except KeyboardInterrupt:
        print("\n\n❌ Operación cancelada por usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR FATAL: {e}")
        sys.exit(1)
