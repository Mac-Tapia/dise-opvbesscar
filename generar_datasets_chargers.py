#!/usr/bin/env python3
"""
GENERADOR DE DATASETS DE CHARGERS
Genera perfiles horarios para año completo y un día del año 2024
Ejecuta y guarda en data/oe2/chargers/
"""

from __future__ import annotations

import sys
from pathlib import Path

# Agregar src al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Importar función del archivo chargers.py
from dimensionamiento.oe2.disenocargadoresev.chargers import (
    generate_soc_dynamic_dataset,
)

def generate_annual_profile():
    """Genera perfil de chargers para todo el año 2024."""
    
    print("\n" + "="*80)
    print("GENERANDO PERFIL ANUAL 2024 (8,760 horas)")
    print("="*80)
    
    # Llamar la función que genera el dataset completo
    df_annual = generate_soc_dynamic_dataset(
        output_dir=Path("data/oe2/chargers"),
    )
    
    print(f"\n✅ Perfil anual generado:")
    print(f"   Filas: {len(df_annual)}")
    print(f"   Columnas: {len(df_annual.columns)}")
    if 'timestamp' in df_annual.columns:
        print(f"   Período: {df_annual['timestamp'].min()} a {df_annual['timestamp'].max()}")
    print(f"   Archivo: data/oe2/chargers/chargers_real_hourly_2024.csv")
    
    return df_annual


def generate_daily_profile(df_annual: pd.DataFrame, day_num: int = 1):
    """Genera perfil de un único día del dataset anual."""
    
    print("\n" + "="*80)
    print(f"GENERANDO PERFIL DIARIO - DÍA {day_num} (24 horas)")
    print("="*80)
    
    # Extraer un día específico (día 1 = 2024-01-01)
    df_daily = df_annual[df_annual['day_of_year'] == day_num].copy()
    
    if len(df_daily) == 0:
        print(f"⚠️  No se encontró día {day_num}")
        return None
    
    # Guardar
    output_file = Path(f"data/oe2/chargers/chargers_daily_2024_day{day_num:03d}.csv")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df_daily.to_csv(output_file, index=False)
    
    print(f"\n✅ Perfil diario generado:")
    print(f"   Filas: {len(df_daily)}")
    print(f"   Columnas: {len(df_daily.columns)}")
    print(f"   Fecha: {df_daily['timestamp'].min().date()}")
    print(f"   Archivo: {output_file}")
    
    # Resumen de actividad del día
    print(f"\n📊 RESUMEN DEL DÍA {day_num}:")
    print(f"   Vehículos motos cargando (max): {df_daily['vehicles_charging_motos'].max():.0f}")
    print(f"   Vehículos mototaxis cargando (max): {df_daily['vehicles_charging_mototaxis'].max():.0f}")
    print(f"   Demanda EV total: {df_daily['ev_demand_kwh'].sum():,.0f} kWh")
    
    return df_daily


def main():
    """Función principal."""
    
    print("\n" + "="*80)
    print("GENERADOR DE DATASETS DE CHARGERS - 2024")
    print("="*80)
    
    try:
        # 1. Generar perfil anual
        df_annual = generate_annual_profile()
        
        # 2. Generar perfil diario (día 1)
        generate_daily_profile(df_annual, day_num=1)
        
        # 3. Generar perfil diario (día 100 - para ver variabilidad)
        generate_daily_profile(df_annual, day_num=100)
        
        print("\n" + "="*80)
        print("✅ TODOS LOS DATASETS GENERADOS CON ÉXITO")
        print("="*80)
        print("\nArchivos guardados en:")
        print("  • data/oe2/chargers/chargers_real_hourly_2024.csv (8,760 filas)")
        print("  • data/oe2/chargers/chargers_daily_2024_day001.csv (24 filas - Día 1)")
        print("  • data/oe2/chargers/chargers_daily_2024_day100.csv (24 filas - Día 100)")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
