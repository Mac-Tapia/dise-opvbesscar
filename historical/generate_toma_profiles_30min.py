#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generador de perfiles INDEPENDIENTES por toma (128 tomas)
Resolución: 30 minutos (Modo 3, AC 16A)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).parent
CHARGERS_DIR = BASE_DIR / "data" / "interim" / "oe2" / "chargers"

def generate_toma_profiles():
    """
    Genera perfiles INDEPENDIENTES de 30 minutos para cada una de las 128 tomas.
    """
    print("\n" + "="*80)
    print("   GENERADOR DE PERFILES POR TOMA - MODO 3 (AC 16A)")
    print("="*80)

    # Base de tiempo: 365 días × 48 intervalos/día = 17,520 intervalos
    start_date = datetime(2023, 1, 1)
    intervals_per_day = 48
    total_intervals = 365 * intervals_per_day

    print(f"\n✓ Calendario base: 365 días × {intervals_per_day} intervalos/día = {total_intervals:,} intervalos")

    # Factor horario base (igual para todas las tomas)
    def get_30min_factor(hour: int, minute: int) -> float:
        """Factor de carga por intervalo de 30 minutos (Modo 3)."""
        time_decimal = hour + minute / 60.0

        if time_decimal < 9.0 or time_decimal >= 22.0:
            return 0.0  # Cerrado (22:00-09:00)
        elif 18.0 <= time_decimal < 22.0:
            return 1.0  # Pico (18:00-22:00): carga completa
        elif 9.0 <= time_decimal < 18.0:
            return 0.5  # Off-pico (09:00-18:00): carga media
        else:
            return 0.0

    # Generar perfiles para CADA TOMA
    np.random.seed(42)  # Reproducibilidad

    all_profiles = []

    print(f"\n[GENERANDO PERFILES INDEPENDIENTES]")

    for toma_id in range(128):
        toma_type = 'moto' if toma_id < 112 else 'mototaxi'
        power_max = 2.0 if toma_id < 112 else 3.0

        # Crear dataframe para esta toma
        rows = []

        for day in range(365):
            for hour_of_day in range(24):
                for minute in [0, 30]:
                    date = start_date + timedelta(days=day)
                    time_decimal = hour_of_day + minute / 60.0

                    # Factor horario base
                    charge_factor = get_30min_factor(hour_of_day, minute)

                    # Variabilidad INDEPENDIENTE por toma
                    # Simula ocupancia aleatoria (algunos intervalos sin EV)
                    occupancy = np.random.random()  # 0-1 aleatoria
                    is_occupied = occupancy > 0.15  # 85% probabilidad de ocupancia

                    # Potencia solo si hay ocupancia
                    power_kw = charge_factor * power_max if is_occupied else 0.0

                    rows.append({  # type: ignore[attr-defined]
                        'toma_id': toma_id,
                        'toma_type': toma_type,
                        'date': date.strftime('%Y-%m-%d'),
                        'hour_of_day': hour_of_day,
                        'minute_of_hour': minute,
                        'time_decimal': time_decimal,
                        'day_of_week': date.weekday(),
                        'month': date.month,
                        'charge_factor': charge_factor,
                        'occupancy': occupancy,
                        'is_occupied': int(is_occupied),
                        'power_max_kw': power_max,
                        'power_kw': power_kw,
                        'energy_kwh': power_kw * 0.5,  # 30 min = 0.5 horas
                    })

        df_toma = pd.DataFrame(rows)
        all_profiles.append(df_toma)  # type: ignore[attr-defined]

        # Mostrar progreso cada 32 tomas
        if (toma_id + 1) % 32 == 0:
            print(f"  └─ Completadas {toma_id + 1}/128 tomas")

    # Consolidar todos los perfiles
    df_all = pd.concat(all_profiles, ignore_index=True)  # type: ignore[attr-defined]

    print(f"\n✓ Perfiles generados para 128 TOMAS INDEPENDIENTES")
    print(f"  └─ Total: {len(df_all):,} filas ({len(df_all)/128:.0f} intervalos por toma)")

    # Estadísticas agregadas
    print(f"\n[ESTADÍSTICAS AGREGADAS]")

    # Agrupar por intervalo
    df_agg = df_all.groupby('date').agg({
        'power_kw': 'sum',
        'energy_kwh': 'sum',
        'occupancy': 'mean'
    }).reset_index()

    print(f"\n  Demanda TOTAL (128 tomas):")
    print(f"    ├─ Media: {df_all.groupby('date')['power_kw'].sum().mean():.2f} kW/día")
    print(f"    ├─ Pico: {df_all.groupby('date')['power_kw'].sum().max():.2f} kW/día")
    print(f"    └─ Total anual: {df_all['energy_kwh'].sum():.0f} kWh/año")

    # Por tipo
    motos = df_all[df_all['toma_type'] == 'moto']
    mototaxis = df_all[df_all['toma_type'] == 'mototaxi']

    print(f"\n  Desglose por tipo:")
    print(f"    ├─ Motos (112 × 2kW): {motos['energy_kwh'].sum():.0f} kWh/año ({motos['energy_kwh'].sum()/(motos['energy_kwh'].sum()+mototaxis['energy_kwh'].sum())*100:.1f}%)")
    print(f"    └─ Mototaxis (16 × 3kW): {mototaxis['energy_kwh'].sum():.0f} kWh/año ({mototaxis['energy_kwh'].sum()/(motos['energy_kwh'].sum()+mototaxis['energy_kwh'].sum())*100:.1f}%)")

    print(f"\n  Variabilidad por toma:")
    print(f"    ├─ Ocupancia promedio: {df_all['occupancy'].mean():.1%}")
    print(f"    ├─ Ocupancia rango: {df_all['occupancy'].min():.1%} - {df_all['occupancy'].max():.1%}")
    print(f"    └─ Cada toma INDEPENDIENTE con patrón aleatorio")

    return df_all

def save_toma_profiles(df: pd.DataFrame):
    """Guarda perfiles independientes por toma."""
    CHARGERS_DIR.mkdir(parents=True, exist_ok=True)

    output_file = CHARGERS_DIR / 'perfil_tomas_30min.csv'
    df.to_csv(output_file, index=False)

    print(f"\n✓ Archivo guardado: {output_file}")
    print(f"  └─ Filas: {len(df):,} (128 tomas × 17,520 intervalos)")

    return output_file

def save_toma_individual_files(df: pd.DataFrame):
    """Guarda archivos individuales por toma (opcional)."""
    output_dir = CHARGERS_DIR / 'toma_profiles'
    output_dir.mkdir(parents=True, exist_ok=True)

    for toma_id in range(128):
        df_toma = df[df['toma_id'] == toma_id].copy()
        toma_type = 'moto' if toma_id < 112 else 'mototaxi'

        filename = output_dir / f'toma_{toma_id:03d}_{toma_type}_30min.csv'
        df_toma.to_csv(filename, index=False)

    print(f"\n✓ Archivos individuales por toma guardados en: {output_dir}")
    print(f"  └─ Total: 128 archivos CSV (uno por toma)")

def main():
    """Función principal."""
    print("\n" + "╔" + "="*78 + "╗")
    print("║" + " "*20 + "GENERADOR DE PERFILES INDEPENDIENTES POR TOMA" + " "*14 + "║")
    print("╚" + "="*78 + "╝")

    # Generar perfiles
    df = generate_toma_profiles()

    # Guardar perfiles consolidados
    save_toma_profiles(df)

    # Guardar archivos individuales (opcional)
    print("\n[Generando archivos individuales por toma...]")
    save_toma_individual_files(df)

    print("\n" + "="*80)
    print("✅ GENERACION COMPLETADA - 128 TOMAS × 30 MINUTOS (MODO 3)")
    print("="*80)

if __name__ == '__main__':
    main()
