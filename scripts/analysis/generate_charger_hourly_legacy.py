#!/usr/bin/env python3
"""
Genera dataset horario de cargadores para año 2024 desde perfil existente.

Lee el perfil de 24 horas y lo expande a 8,760 horas con índice de fechas.
Output: data/oe2/chargers/charger_load_hourly_2024.csv
"""
from __future__ import annotations

from pathlib import Path
import sys
import pandas as pd
import numpy as np
from datetime import datetime

def generate_charger_dataset():
    """Genera dataset horario de cargadores con fechas."""

    print("=" * 80)
    print("GENERACIÓN DE DATASET HORARIO - CARGADORES EV 2024")
    print("=" * 80)

    # Directorio de datos
    out_dir = Path("data/oe2/chargers")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Intentar cargar perfil horario
    profile_path = out_dir / "perfil_horario_carga.csv"

    print(f"\n[1] Buscando perfil de carga...")
    print(f"    Ruta: {profile_path}")

    if not profile_path.exists():
        print(f"    ❌ Perfil no encontrado. Generando perfil sintético...")

        # Crear perfil sintético para 38 tomaes
        # Patrón: bajo (9-18), alto (18-22), bajo (22-9)
        hours = np.arange(24)

        # Patrón de demanda horaria (día típico)
        # Bajo: 9-18 (9h) -> 0.3 - 0.5
        # Alto: 18-22 (4h) -> 0.8 - 1.0
        # Bajo: 22-9 (9h) -> 0.0 - 0.2

        pattern = np.array([
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,  # 0-8: cerrado
            0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3,   # 9-17: bajo
            0.8, 0.9, 0.95, 0.9, 0.8,                       # 18-22: alto (pico)
            0.1, 0.05, 0.0, 0.0                             # 23-2: muy bajo (cierre)
        ])

        # Crear matriz de 24h × 38 tomaes
        # Cada cargador varía ligeramente del patrón base
        df_profile = pd.DataFrame(index=hours)
        df_profile['hour'] = hours

        for i in range(38):
            # Variación aleatoria por cargador (±10%)
            charger_id = f"charger_{i:03d}"
            variation = np.random.uniform(0.9, 1.1, size=24)
            df_profile[charger_id] = pattern * variation

        print(f"    ✅ Perfil sintético generado (38 tomaes)")
    else:
        # Cargar perfil existente
        df_profile = pd.read_csv(profile_path)
        print(f"    ✅ Perfil encontrado: {len(df_profile)} horas")

        # Si tiene 96 filas (15 min), resamplear a 24h
        if len(df_profile) == 96:
            print(f"    ! Perfil en resolución 15-min (96 filas). Agregando a horario...")
            # Agrupar cada 4 filas (60 min)
            df_profile = df_profile.groupby(df_profile.index // 4).mean()
            print(f"    ✅ Agregado a {len(df_profile)} horas")

    # Obtener columnas de cargadores (excluyendo 'hour')
    charger_cols = [col for col in df_profile.columns if col.startswith('charger_') or col.startswith('CHARGER_')]

    if len(charger_cols) == 0:
        # Si no hay columnas explícitas de cargadores, asumir todas excepto 'hour'
        charger_cols = [col for col in df_profile.columns if col != 'hour']

    print(f"\n[2] Cargadores detectados: {len(charger_cols)}")
    print(f"    Primeros: {charger_cols[:5]}")

    # Crear índice de fechas para 2024 (8,760 horas)
    print(f"\n[3] Creando índice temporal para 2024...")
    start_date = datetime(2024, 1, 1, 0, 0)
    dates = pd.date_range(start=start_date, periods=8760, freq='h')
    print(f"    Rango: {dates[0]} a {dates[-1]}")
    print(f"    Total: {len(dates)} horas")

    # Expandir perfil de 24h a 8,760h (repetir 365 veces)
    print(f"\n[4] Expandiendo perfil horario a año completo...")

    profile_values = df_profile[charger_cols].values  # Shape: (24, n_chargers)

    # Repetir 365 veces
    days_in_year = 365
    annual_values = np.tile(profile_values, (days_in_year, 1))

    # Crear DataFrame
    df_annual = pd.DataFrame(
        annual_values,
        columns=charger_cols,
        index=dates
    )
    df_annual.index.name = 'datetime'

    # Agregar coluna de hora del día
    df_annual['hour'] = dates.hour

    print(f"    ✅ Dataset generado: {df_annual.shape}")

    # Verificación de datos
    print(f"\n[5] Validación de datos...")
    print(f"    Min: {df_annual[charger_cols].min().min():.4f}")
    print(f"    Max: {df_annual[charger_cols].max().max():.4f}")
    print(f"    Mean: {df_annual[charger_cols].mean().mean():.4f}")

    # Energía diaria (suma por día)
    daily_energy = df_annual[charger_cols].resample('D').sum()
    print(f"\n[6] Energía diaria:")
    print(f"    Promedio: {daily_energy.sum(axis=1).mean():.2f} kWh/día")
    print(f"    Mínimo: {daily_energy.sum(axis=1).min():.2f} kWh/día")
    print(f"    Máximo: {daily_energy.sum(axis=1).max():.2f} kWh/día")
    print(f"    Anual: {df_annual[charger_cols].sum().sum():.2f} kWh/año")

    # Guardar archivos
    print(f"\n[7] Guardando datasets...")

    # Opción 1: Con índice de fechas
    file1 = out_dir / "charger_load_hourly_2024.csv"
    df_annual.to_csv(file1)
    print(f"    ✅ {file1.name} ({file1.stat().st_size / 1024:.1f} KB)")

    # Opción 2: Sin índice (para compatibilidad)
    file2 = out_dir / "charger_load_hourly_2024_no_index.csv"
    df_annual.to_csv(file2, index=False)
    print(f"    ✅ {file2.name} ({file2.stat().st_size / 1024:.1f} KB)")

    # Opción 3: Con datetime en columna
    df_export = df_annual.reset_index()
    file3 = out_dir / "charger_load_hourly_2024_with_date_col.csv"
    df_export.to_csv(file3, index=False)
    print(f"    ✅ {file3.name} ({file3.stat().st_size / 1024:.1f} KB)")

    # Mostrar muestra
    print(f"\n[8] Muestra de datos:")
    print(f"\n    Primeras 5 filas:")
    print(df_annual.iloc[:5, :5])
    print(f"\n    Últimas 5 filas:")
    print(df_annual.iloc[-5:, :5])

    print(f"\n" + "=" * 80)
    print(f"✅ GENERACIÓN COMPLETADA")
    print(f"=" * 80)
    print(f"\nArchivos generados en: {out_dir.absolute()}")
    print(f"  • charger_load_hourly_2024.csv (recomendado - con índice de fechas)")
    print(f"  • charger_load_hourly_2024_no_index.csv")
    print(f"  • charger_load_hourly_2024_with_date_col.csv")
    print(f"\nDimensiones:")
    print(f"  • Horas: {len(dates)} (8,760 = 365 días × 24 horas)")
    print(f"  • Cargadores: {len(charger_cols)}")
    print(f"  • Período: {dates[0].date()} a {dates[-1].date()}")
    print(f"  • Energía anual: {df_annual[charger_cols].sum().sum():.2f} kWh")


if __name__ == "__main__":
    try:
        generate_charger_dataset()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
