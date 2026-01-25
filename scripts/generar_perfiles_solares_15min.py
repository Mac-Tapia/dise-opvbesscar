#!/usr/bin/env python3
"""
Generador de perfiles solares a 15 minutos para CityLearn v2
Genera UNA ÚNICA serie de generación solar para un año completo (35,040 timesteps)
Resolución: 15 minutos
"""

import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd

# Agregar ruta del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from iquitos_citylearn.oe2.solar_pvlib import build_pv_timeseries_sandia, PVSystemConfig

def generar_perfil_solar_15min():
    """
    Genera perfil de generación solar con resolución 15 minutos para un año.
    Retorna DataFrame con columnas: timestamp, pv_power_kw, pv_energy_kwh
    """

    print("\n" + "="*80)
    print("GENERADOR DE PERFIL SOLAR - 15 MINUTOS")
    print("="*80)

    # Configuración del sistema PV (usa valores por defecto de Iquitos)
    config = PVSystemConfig()

    # Parámetros objetivo del sistema
    target_dc_kw = 622.4  # Basado en verificación anterior
    target_ac_kw = 497.92  # 80% de DC
    target_annual_kwh = 750_000  # Meta anual

    # Generar serie temporal solar con resolución 15 minutos
    pv_results, metadata = build_pv_timeseries_sandia(
        year=2024,
        config=config,
        target_dc_kw=target_dc_kw,
        target_ac_kw=target_ac_kw,
        target_annual_kwh=target_annual_kwh,
        seconds_per_time_step=900,  # 15 minutos
        selection_mode="manual",
        candidate_count=0,
        selection_metric="energy_per_m2",
    )

    print("\n" + "="*80)
    print("SERIE TEMPORAL SOLAR GENERADA")
    print("="*80)
    print(f"Resolución: 15 minutos")
    print(f"Período: {pv_results.index[0]} a {pv_results.index[-1]}")
    print(f"Total de timesteps: {len(pv_results)}")
    print(f"Energía anual AC: {pv_results['ac_energy_kwh'].sum():,.0f} kWh")
    print(f"Potencia máxima: {pv_results['ac_power_kw'].max():.2f} kW")
    print(f"Potencia media: {pv_results['ac_power_kw'].mean():.2f} kW")

    return pv_results

def guardar_perfil_solar(pv_results):
    """
    Guarda perfil solar en CSV con formato para CityLearn v2
    """

    output_dir = PROJECT_ROOT / "data" / "oe2" / "perfiles_solares"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Crear DataFrame simplificado
    solar_profile = pd.DataFrame({
        'timestamp': pv_results.index,
        'hour': [ts.hour for ts in pv_results.index],
        'minute': [ts.minute for ts in pv_results.index],
        'day': [ts.dayofyear - 1 for ts in pv_results.index],
        'pv_power_kw': pv_results['ac_power_kw'].values,
        'pv_energy_kwh': pv_results['ac_energy_kwh'].values,
    })

    output_file = output_dir / "perfil_solar_15min_anual.csv"
    solar_profile.to_csv(output_file, index=False)

    print(f"\nPerfil solar guardado: {output_file}")
    print(f"   Tamaño: {output_file.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"   Registros: {len(solar_profile):,}")

    # Generar metadatos
    metadata = {
        "nombre": "Perfil Solar Único - Iquitos BESS",
        "ubicacion": "Iquitos, Perú",
        "latitud": -3.75,
        "longitud": -73.25,
        "año": 2024,
        "resolucion_minutos": 15,
        "timesteps_totales": len(solar_profile),
        "dias": 365,
        "energia_anual_kwh": float(pv_results['ac_energy_kwh'].sum()),
        "potencia_maxima_kw": float(pv_results['ac_power_kw'].max()),
        "potencia_promedio_kw": float(pv_results['ac_power_kw'].mean()),
        "archivo_csv": str(output_file.name),
        "observacion": "Una única serie de generación solar para todos los 101 escenarios"
    }

    metadata_file = output_dir / "perfil_solar_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"Metadatos guardados: {metadata_file}")

    return solar_profile

if __name__ == "__main__":
    print("\nINICIANDO GENERACIÓN DE PERFIL SOLAR ÚNICA")

    try:
        # Generar perfil solar
        pv_results = generar_perfil_solar_15min()

        # Guardar en CSV
        solar_profile = guardar_perfil_solar(pv_results)

        print("\n" + "="*80)
        print("\nGENERAÓN COMPLETADA")
        print("="*80)
        print("\n📊 RESUMEN:")
        print(f"   • Perfil solar único para todo un año")
        print(f"   • Resolución: 15 minutos")
        print(f"   • Timesteps: {len(solar_profile):,}")
        print(f"   • Energía anual: {pv_results['ac_energy_kwh'].sum():,.0f} kWh")
        print(f"   • Listo para combinar con 101 escenarios de demanda")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
