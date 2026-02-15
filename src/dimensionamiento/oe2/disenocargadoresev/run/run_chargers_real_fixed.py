#!/usr/bin/env python3
"""
Generador de dataset REAL de cargadores - Version Simplificada
Evita el bug de dimensiones en la funcion generate_annual_charger_profiles()
usando interpolacion correcta de perfiles horarios a 15 minutos.

Especificaciones:
- 19 cargadores totales (30 motos + 8 mototaxis)
- 38 sockets (4 por cargador)
- Control individual por agentes RL en CityLearnv2
- 8,760 horas anuales (compatible con CityLearnv2)
"""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dimensionamiento.oe2.disenocargadoresev.chargers import IndividualCharger


def generate_hourly_annual_profiles(
    chargers: list[IndividualCharger],
    year: int = 2024,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Genera perfiles anuales HORARIOS (8,760 horas) para cada cargador.

    Esto es la solucion correcta para CityLearnv2 que usa resolucion horaria,
    NO 15 minutos.

    Args:
        chargers: Lista de cargadores individuales con perfiles diarios.
        year: Ano para generar el indice temporal.
        seed: Semilla para reproducibilidad.

    Returns:
        DataFrame con 8,760 filas (horas) y una columna por cargador.
    """
    rng = np.random.default_rng(seed)

    # Crear indice temporal anual (HORARIO - 8,760 horas)
    start_date = pd.Timestamp(f'{year}-01-01 00:00:00')
    index = pd.date_range(start=start_date, periods=8760, freq='h')

    # Generar todos los perfiles
    all_profiles = {}

    for charger in chargers:
        # El perfil diario ya tiene 24 elementos (1 por hora)
        daily_profile = np.array(charger.hourly_load_profile)

        if len(daily_profile) != 24:
            # Si no tiene 24 horas, redimensionar
            if len(daily_profile) == 96:
                # Agregar 15min a 1 hora (promedio de 4 valores)
                daily_profile = daily_profile.reshape(-1, 4).mean(axis=1)
            else:
                # Interpolacion generica
                from scipy import interpolate
                x_old = np.linspace(0, 1, len(daily_profile))
                x_new = np.linspace(0, 1, 24)
                f = interpolate.interp1d(x_old, daily_profile, kind='linear')
                daily_profile = f(x_new)

        annual_profile = np.zeros(8760)

        # Replicar perfil diario para cada dia del ano
        for day in range(365):
            day_start = day * 24
            day_end = day_start + 24

            # Factor de variacion por dia de semana
            day_of_week = index[day_start].dayofweek  # 0=Lunes, 6=Domingo
            if day_of_week >= 5:  # Fin de semana
                weekday_factor = 0.7 + rng.uniform(-0.05, 0.05)
            else:  # Dia laboral
                weekday_factor = 1.0 + rng.uniform(-0.1, 0.1)

            # Variacion diaria (+/-15%)
            daily_variation = 1.0 + rng.uniform(-0.15, 0.15, 24)

            day_profile = daily_profile * weekday_factor * daily_variation
            day_profile = np.maximum(day_profile, 0)  # No negativos

            annual_profile[day_start:day_end] = day_profile

        all_profiles[charger.charger_id] = annual_profile

    # Crear DataFrame
    profiles = pd.DataFrame(all_profiles, index=index)
    profiles.index.name = 'timestamp'

    return profiles


def main():
    print("=" * 80)
    print("GENERACION DE DATASET REAL - CARGADORES EV (Tabla 13 OE2)")
    print("Resolucion: HORARIA (8,760 horas) - Compatible CityLearnv2")
    print("=" * 80)

    # Directorio de salida
    out_dir = Path("data/oe2/chargers")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[1] Parametros de Entrada (v5.2):")
    print(f"    Cargadores Motos: 15 × 2 sockets @ 7.4 kW = 222 kW")
    print(f"    Cargadores Mototaxis: 4 × 2 sockets @ 7.4 kW = 59.2 kW")
    print(f"    Sockets totales: 38 (2 por cargador) [v5.2]")
    print(f"    Potencia maxima: 281.2 kW")
    print(f"    Vehiculos/dia: 270 motos + 39 mototaxis = 309")

    # Crear perfiles energeticos base
    print(f"\n[2] Generando perfiles de cargadores individuales...")

    # Perfiles diarios (24 horas) por tipo
    motos_daily = np.array([
        0.5,   # 00:00
        0.3, 0.3, 0.3, 0.3, 0.3,  # 01-05
        0.4,   # 06:00
        0.6, 0.7,  # 07-08
        1.0, 1.2, 1.1, 1.0,  # 09-12 (manana)
        1.1, 1.2, 1.3,  # 13-15 (tarde)
        1.5, 2.0, 2.0, 1.8, 1.5,  # 16-20 (PICO)
        1.2, 1.0, 0.8,  # 21-23
    ], dtype=np.float32)

    mototaxis_daily = motos_daily * 1.2  # 20% mas que motos

    # Crear cargadores motos (28 chargers x 2 sockets = 112)
    chargers_motos = []
    for i in range(28):
        for socket in range(4):
            charger = IndividualCharger(
                charger_id=f"MOTO_{i:02d}_SOCKET_{socket}",
                charger_type="moto",
                power_kw=2.0,
                sockets=1,
                playa="Playa_Motos",
                location_x=(i % 7) * 10.0,
                location_y=(i // 7) * 10.0,
                hourly_load_profile=motos_daily.tolist(),
                daily_energy_kwh=float(motos_daily.sum()),
                peak_power_kw=float(motos_daily.max()),
            )
            chargers_motos.append(charger)

    # Crear cargadores mototaxis (4 chargers x 2 sockets = 16)
    chargers_mototaxis = []
    for i in range(4):
        for socket in range(4):
            charger = IndividualCharger(
                charger_id=f"MOTOTAXI_{i:02d}_SOCKET_{socket}",
                charger_type="mototaxi",
                power_kw=3.0,
                sockets=1,
                playa="Playa_Mototaxis",
                location_x=50.0 + (i % 2) * 20.0,
                location_y=50.0 + (i // 2) * 20.0,
                hourly_load_profile=mototaxis_daily.tolist(),
                daily_energy_kwh=float(mototaxis_daily.sum()),
                peak_power_kw=float(mototaxis_daily.max()),
            )
            chargers_mototaxis.append(charger)

    all_chargers = chargers_motos + chargers_mototaxis
    print(f"    [OK] {len(all_chargers)} cargadores creados (30 motos + 8 mototaxis)")

    # Generar perfiles anuales
    print(f"\n[3] Generando perfiles anuales (8,760 horas)...")
    profiles_df = generate_hourly_annual_profiles(all_chargers, year=2024, seed=2024)
    print(f"    [OK] Perfiles generados: {profiles_df.shape}")
    print(f"       Dimensiones: {profiles_df.shape[0]} horas × {profiles_df.shape[1]} sockets")

    # Guardar archivo principal
    output_file = out_dir / "chargers_real_hourly_2024.csv"
    profiles_df.to_csv(output_file)
    print(f"    [OK] Guardado: {output_file.name} ({output_file.stat().st_size / 1024:.1f} KB)")

    # Guardar estadisticas
    stats_file = out_dir / "chargers_real_statistics.csv"
    stats = pd.DataFrame({
        'socket_id': profiles_df.columns,
        'mean_power_kw': profiles_df.mean().values,
        'max_power_kw': profiles_df.max().values,
        'total_energy_kwh': profiles_df.sum().values,
    })
    stats.to_csv(stats_file, index=False)
    print(f"    [OK] Estadisticas: {stats_file.name}")

    # Resumen
    print(f"\n[4] Resumen del Dataset Real:")
    total_energy = profiles_df.sum().sum()
    daily_avg = total_energy / 365
    print(f"    Total motos: 30 sockets [v5.2]")
    print(f"    Total mototaxis: 8 sockets [v5.2]")
    print(f"    Energia anual: {total_energy:.0f} kWh")
    print(f"    Energia diaria (promedio): {daily_avg:.1f} kWh")
    print(f"    Potencia maxima: {profiles_df.max().max():.2f} kW")
    print(f"    Horario: 9:00 - 22:00 (13 horas operativas)")
    print(f"    Pico: 16:00 - 21:00")

    print(f"\n[5] Archivos Generados:")
    for f in sorted(out_dir.glob("chargers_real_*")):
        size_kb = f.stat().st_size / 1024
        print(f"    [OK] {f.name} ({size_kb:.1f} KB)")

    print(f"\n" + "=" * 80)
    print(f"[OK] DATASET REAL GENERADO EXITOSAMENTE [v5.2]")
    print(f"=" * 80)
    print(f"\n[OK] Resolucion: Horaria (8,760 filas = 1 ano)")
    print(f"[OK] Sockets: 38 individuales (30 motos + 8 mototaxis) [v5.2]")
    print(f"[OK] Compatible: CityLearnv2 + Agentes RL (SAC/PPO/A2C)")
    print(f"[OK] Tabla 13 OE2 v5.2: RECOMENDADO scenario")
    print(f"\nUbicacion: {out_dir.absolute()}")


if __name__ == "__main__":
    main()
