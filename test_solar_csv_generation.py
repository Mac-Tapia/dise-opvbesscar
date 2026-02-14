#!/usr/bin/env python
"""Test script para generar todos los CSVs de energía solar."""

from pathlib import Path
import sys

# Agregar el src al path
sys.path.insert(0, str(Path(__file__).parent))

from src.dimensionamiento.oe2.generacionsolar.disenopvlib.solar_pvlib import generate_pv_csv_datasets

if __name__ == "__main__":
    dataset_file = Path("data/oe2/Generacionsolar/pv_generation_citylearn2024.csv")
    output_dir = Path("data/oe2/Generacionsolar")
    
    if dataset_file.exists():
        print(f"\n✓ Dataset encontrado: {dataset_file}")
        print(f"✓ Directorio de salida: {output_dir}")
        
        try:
            results = generate_pv_csv_datasets(
                dataset_path=dataset_file,
                output_dir=output_dir
            )
            print(f"\n✅ ÉXITO: {len(results)} archivos CSV generados")
            for filename, filepath in results.items():
                print(f"   ✓ {filename}")
        except Exception as e:
            print(f"\n❌ ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"\n❌ Dataset no encontrado: {dataset_file}")
