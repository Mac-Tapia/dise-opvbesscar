#!/usr/bin/env python3
"""Ejecutar conversión de demanda 15-min a horaria y verificar resultado"""

import sys
import os
from pathlib import Path

# Set working directory
os.chdir(Path(__file__).parent)

# Importar script de conversión
sys.path.insert(0, 'data/oe2/demandamallkwh')

try:
    # Ejecutar el script
    print("=" * 80)
    print("EJECUTANDO CONVERSIÓN DE DEMANDA 15-MIN A HORARIA")
    print("=" * 80)

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "convertir",
        "data/oe2/demandamallkwh/convertir_15min_a_hora_dataset.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)

    print("\n" + "=" * 80)
    print("VERIFICANDO RESULTADO")
    print("=" * 80)

    # Verificar archivo
    import pandas as pd

    csv_path = Path('data/interim/oe2/demandamallkwh/demandamallhorakwh.csv')

    if csv_path.exists():
        print(f"\n✅ Archivo existe: {csv_path}")

        # Cargar y mostrar info
        df = pd.read_csv(csv_path, sep=';')

        print(f"\n📊 Estadísticas del archivo convertido:")
        print(f"   - Filas: {len(df)} (debería ser 8,760)")
        print(f"   - Columnas: {list(df.columns)}")
        print(f"   - Energía total: {df['kWh'].sum():,.0f} kWh")

        print(f"\n📋 Primeras 5 filas:")
        print(df.head())

        print(f"\n📋 Últimas 5 filas:")
        print(df.tail())

        print(f"\n✅ CONVERSIÓN EXITOSA")
    else:
        print(f"\n❌ ERROR: Archivo no encontrado: {csv_path}")
        sys.exit(1)

except Exception as e:
    print(f"\n❌ ERROR en ejecución: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
