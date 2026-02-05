#!/usr/bin/env python3
"""
Ejecuta dimensionamiento de cargadores y genera dataset horario con fechas.

Output: data/oe2/chargers/charger_load_hourly_2024.csv
- Index: Datetime (enero a diciembre 2024)
- Columnas: 128 cargadores EV individuales
"""
from __future__ import annotations

from pathlib import Path
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dimensionamiento.oe2.disenocargadoresev.chargers import (
    run_charger_sizing,
    generate_playa_annual_dataset,
    ESCENARIOS_PREDEFINIDOS,
)


def main():
    """Ejecuta charger sizing y genera dataset con fechas."""

    print("=" * 80)
    print("GENERACIÓN DE DATASET HORARIO DE CARGADORES EV - AÑO 2024")
    print("=" * 80)

    # Directorio output
    out_dir = Path(__file__).parent / "data" / "oe2" / "chargers"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[1] Ejecutando dimensionamiento de cargadores...")
    print(f"    Output dir: {out_dir}")

    # Parámetros de Tabla 13 OE2 (escenario RECOMENDADO)
    # Ver comentarios en chargers.py para documentación completa
    result = run_charger_sizing(
        out_dir=out_dir,
        seed=2024,
        n_motos=900,  # Motos en hora pico (6pm-10pm)
        n_mototaxis=130,  # Mototaxis en hora pico
        pe_motos=0.90,  # Probabilidad evento carga (90% pentración)
        pe_mototaxis=0.90,
        fc_motos=0.90,  # Factor carga (90% carga completa)
        fc_mototaxis=0.90,
        peak_share_day=0.40,  # 40% de energía en horas pico (6pm-10pm)
        session_minutes=60.0,  # Sesión de carga = 60 minutos
        utilization=0.90,  # 90% utilización de tomas
        charger_power_kw_moto=2.0,  # 2 kW por cargador moto
        charger_power_kw_mototaxi=3.0,  # 3 kW por cargador mototaxi
        sockets_per_charger=4,  # 4 tomas por cargador
        opening_hour=9,  # Abre a las 9am
        closing_hour=22,  # Cierra a las 10pm
        km_per_kwh=5.0,  # Eficiencia EV
        km_per_gallon=25.0,  # Eficiencia gasolina
        kgco2_per_gallon=2.31,  # Factor emisión gasolina
        grid_carbon_kg_per_kwh=0.4521,  # Iquitos grid
        peak_hours=[18, 19, 20, 21],  # Horas pico: 6pm-10pm
        n_scenarios=101,
        generate_plots=True,
    )

    print(f"\n[2] Resultado del dimensionamiento:")
    print(f"    Escenario: {result.get('recommended_scenario_name', 'N/A')}")
    print(f"    Cargadores motos: {result.get('chargers_motos', 'N/A')}")
    print(f"    Cargadores mototaxis: {result.get('chargers_mototaxis', 'N/A')}")
    print(f"    Total sockets: {result.get('total_sockets', 'N/A')}")
    print(f"    Energía diaria: {result.get('energy_day_kwh', 'N/A'):.2f} kWh")

    # Generar perfil horario
    print(f"\n[3] Generando perfil horario...")

    # Leer el archivo de perfil generado
    profile_path = out_dir / "perfil_horario_carga.csv"
    if not profile_path.exists():
        print(f"    ❌ ERROR: {profile_path} no encontrado")
        return

    df_profile = pd.read_csv(profile_path)
    print(f"    Perfil cargado: {len(df_profile)} horas")
    print(f"    Columnas: {list(df_profile.columns)[:5]}...")

    # Generar dataset anual con fechas (2024)
    print(f"\n[4] Generando dataset anual 2024 con fechas...")

    # Crear índice de fechas (enero a diciembre 2024)
    start_date = datetime(2024, 1, 1)
    dates = pd.date_range(start=start_date, periods=8760, freq='h')
    print(f"    Rango de fechas: {dates[0]} a {dates[-1]}")
    print(f"    Total registros: {len(dates)}")

    # Crear dataset anual repitiendo el perfil de 24 horas
    # El perfil de 24 horas se repite cada día del año
    days_in_year = 365
    hours_per_day = 24
    total_hours = days_in_year * hours_per_day

    # Obtener las columnas de demanda (excluyendo 'hour' y 'load_kwh')
    charger_cols = [col for col in df_profile.columns
                   if col not in ['hour', 'load_kwh', 'load_kw']]

    print(f"    Columnas de cargadores detectadas: {len(charger_cols)}")
    if len(charger_cols) == 0:
        print(f"    ❌ ERROR: No se encontraron columnas de cargadores")
        return

    # Expandir perfil a año completo (repetir el perfil de 24 horas)
    profile_values = df_profile[charger_cols].values  # Shape: (24, n_chargers)

    # Repetir 365 veces para cubrir un año
    annual_values = np.tile(profile_values, (days_in_year, 1))

    # Crear DataFrame con fechas como índice
    df_annual = pd.DataFrame(
        annual_values,
        columns=charger_cols,
        index=dates
    )

    # Asegurar que el índice tenga nombre
    df_annual.index.name = 'datetime'

    # Añadir columna de hora del día (para referencia)
    df_annual['hour'] = dates.hour

    print(f"\n[5] Dataset generado:")
    print(f"    Shape: {df_annual.shape}")
    print(f"    Index: {type(df_annual.index).__name__}")
    print(f"    Primeras filas:")
    print(df_annual.head())
    print(f"\n    Últimas filas:")
    print(df_annual.tail())

    # Estadísticas
    print(f"\n[6] Estadísticas:")
    charger_data = df_annual.drop(columns=['hour'])
    print(f"    Promedio diario (kWh): {charger_data.sum(axis=1).mean():.2f}")
    print(f"    Mínimo (kWh): {charger_data.sum(axis=1).min():.2f}")
    print(f"    Máximo (kWh): {charger_data.sum(axis=1).max():.2f}")
    print(f"    Anual (kWh): {charger_data.sum().sum():.2f}")

    # Guardar en CSV
    output_file = out_dir / "charger_load_hourly_2024.csv"
    print(f"\n[7] Guardando dataset...")
    print(f"    Archivo: {output_file}")

    df_annual.to_csv(output_file)

    # Verificar que se guardó
    if output_file.exists():
        file_size = output_file.stat().st_size / 1024  # KB
        print(f"    ✅ Guardado exitosamente")
        print(f"    Tamaño: {file_size:.1f} KB")
    else:
        print(f"    ❌ ERROR: No se pudo guardar el archivo")
        return

    # Generar también un CSV sin índice para compatibilidad
    output_file_no_index = out_dir / "charger_load_hourly_2024_no_index.csv"
    df_annual.to_csv(output_file_no_index, index=False)
    print(f"    Alternativa (sin índice): {output_file_no_index.name}")

    # Generar también CSV con fechas en columna separada
    df_export = df_annual.reset_index()
    output_file_with_col = out_dir / "charger_load_hourly_2024_with_date_col.csv"
    df_export.to_csv(output_file_with_col, index=False)
    print(f"    Alternativa (fecha en columna): {output_file_with_col.name}")

    print(f"\n" + "=" * 80)
    print(f"✅ GENERACIÓN COMPLETADA")
    print(f"=" * 80)
    print(f"\nArchivos generados en: {out_dir}")
    print(f"  1. charger_load_hourly_2024.csv (con índice de fechas)")
    print(f"  2. charger_load_hourly_2024_no_index.csv (sin índice)")
    print(f"  3. charger_load_hourly_2024_with_date_col.csv (fecha en columna)")
    print(f"\nDimensiones: {df_annual.shape[0]} horas × {df_annual.shape[1]-1} cargadores")
    print(f"Período: {dates[0].date()} a {dates[-1].date()}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
