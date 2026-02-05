"""
Script de ejemplo: Integración de datos solares con CityLearn.

Demuestra cómo usar el archivo de generación solar para entrenar agentes RL.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional

def load_solar_data() -> pd.DataFrame:
    """
    Carga el perfil de generación solar 2024.

    Returns:
        DataFrame con columnas: fecha, hora, irradiancia_ghi, potencia_kw,
        energia_kwh, temperatura_c, velocidad_viento_ms
    """
    csv_path = Path("data/oe2/Generacionsolar/solar_generation_profile_2024.csv")

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Archivo de generación solar no encontrado: {csv_path}\n"
            f"Ejecutar primero: python scripts/generate_solar_profile_2024.py"
        )

    df = pd.read_csv(csv_path)
    df["fecha"] = pd.to_datetime(df["fecha"])

    print(f"✅ Datos solares cargados: {len(df)} registros")
    return df

def validate_for_citylearn(df: pd.DataFrame) -> bool:
    """
    Valida que el dataset sea compatible con CityLearn.

    Requisitos:
    - 8,760 timesteps (365 días × 24 horas)
    - Sin valores NaN en columnas críticas
    - Energía en kWh
    """

    checks = []

    # 1. Tamaño
    if len(df) != 8760:
        checks.append(f"❌ Tamaño incorrecto: {len(df)} (esperado 8,760)")
    else:
        checks.append(f"✅ Tamaño correcto: {len(df)} registros")

    # 2. Valores faltantes
    critical_cols = ["fecha", "hora", "energia_kwh", "temperatura_c"]
    for col in critical_cols:
        if df[col].isna().any():
            checks.append(f"❌ Valores faltantes en '{col}'")
        else:
            checks.append(f"✅ Columna '{col}' sin NaN")

    # 3. Rangos
    if df["hora"].min() < 0 or df["hora"].max() > 23:
        checks.append(f"❌ Rango horario inválido: {df['hora'].min()}-{df['hora'].max()}")
    else:
        checks.append(f"✅ Rango horario válido: 0-23")

    if (df["energia_kwh"] < 0).any():
        checks.append(f"❌ Energía negativa detectada")
    else:
        checks.append(f"✅ Energía no negativa")

    # 4. Temporalidad
    if df["fecha"].min().month != 1 or df["fecha"].min().day != 1:
        checks.append(f"❌ Inicio incorrecto: {df['fecha'].min()}")
    else:
        checks.append(f"✅ Inicio correcto: 1 enero")

    # Imprimir resultados
    print("\n📋 VALIDACIÓN CITYLEARN")
    print("=" * 50)
    for check in checks:
        print(check)

    is_valid = all(c.startswith("✅") for c in checks)
    if is_valid:
        print("\n✅ Dataset LISTO para CityLearn")
    else:
        print("\n❌ Dataset REQUIERE correcciones")

    return is_valid

def example_usage_citylearn(df: pd.DataFrame) -> None:
    """
    Ejemplo de cómo usar los datos solares en CityLearn.

    En el código real, esto se haría en DatasetBuilder o similar:

    ```python
    from citylearn.data import DatasetBuilder

    # 1. Crear builder
    builder = DatasetBuilder()

    # 2. Cargar datos solares
    solar_df = pd.read_csv("data/oe2/Generacionsolar/solar_generation_profile_2024.csv")

    # 3. Obtener timeseries de energía (kWh por hora)
    solar_timeseries = solar_df["energia_kwh"].values

    # 4. Asignar al building
    building.energy_simulation.solar_generation = solar_timeseries.tolist()

    # 5. Crear environment
    env = builder.get_environment(...)

    # 6. Entrenar agentes
    agent.learn(env)
    ```
    """

    print("\n" + "=" * 70)
    print("EJEMPLO: USO EN CITYLEARN")
    print("=" * 70)

    # Extraer columna de energía (lo que CityLearn espera)
    solar_timeseries = df["energia_kwh"].values.tolist()

    print("\n📊 Timeseries de generación solar (primeras 24 horas):")
    print("hora | generacion_kwh")
    print("-" * 30)
    for hora, gen_kwh in enumerate(solar_timeseries[:24]):
        print(f"{hora:4d} | {gen_kwh:14.2f}")

    print(f"\n... (8,760 - 24 = 8,736 registros más)")

    # Ejemplo de demanda de chargers
    charger_demand_hourly = np.array([
        50.0 if 6 <= h <= 22 else 10.0  # 50 kW durante día, 10 kW noche
        for h in range(24)
    ])

    print("\n📊 Demanda de chargers (ejemplo patrón diario):")
    print("hora | demanda_kw")
    print("-" * 30)
    for hora in range(24):
        demand = charger_demand_hourly[hora]
        print(f"{hora:4d} | {demand:10.1f}")

    # Análisis de balance
    daily_solar_gen = sum(solar_timeseries[:24])  # Primer día
    daily_charger_demand = np.sum(charger_demand_hourly)

    print(f"\n⚡ ANÁLISIS DE BALANCE DÍA 1 (2024-01-01):")
    print(f"   Generación solar: {daily_solar_gen:.2f} kWh")
    print(f"   Demanda chargers: {daily_charger_demand:.2f} kWh")
    print(f"   Balance: {daily_solar_gen - daily_charger_demand:+.2f} kWh")
    if daily_solar_gen > daily_charger_demand:
        print(f"   ✅ Solar CUBRE completamente la demanda")
    else:
        print(f"   ⚠️  Déficit: requiere {daily_charger_demand - daily_solar_gen:.2f} kWh del grid")

    # Análisis anual
    annual_solar = sum(solar_timeseries)
    annual_charger = daily_charger_demand * 365

    print(f"\n⚡ ANÁLISIS ANUAL (2024):")
    print(f"   Generación solar: {annual_solar:,.2f} kWh")
    print(f"   Demanda chargers: {annual_charger:,.2f} kWh")
    print(f"   Solar/Demanda ratio: {annual_solar/annual_charger:.2%}")
    print(f"\n   → Sin RL: ~{annual_charger - annual_solar:,.0f} kWh desde grid")
    print(f"   → Con RL (best case): solar + BESS podrían optimizar balance")

def generate_summary_report(df: pd.DataFrame) -> None:
    """Genera un reporte resumido."""

    print("\n" + "=" * 70)
    print("REPORTE RESUMIDO - GENERACIÓN SOLAR 2024")
    print("=" * 70)

    print("\n📍 UBICACIÓN")
    print("   Latitud: 3.74°S | Longitud: 73.27°W")
    print("   Ciudad: Iquitos, Perú (Amazonía)")
    print("   Región: Clima tropical ecuatorial")

    print("\n⚡ INFRAESTRUCTURA")
    print("   Capacidad instalada: 4,050 kWp")
    print("   Eficiencia panel: 18% (STC)")
    print("   Eficiencia inversor: 96%")
    print("   Área total: ~22,500 m²")

    print("\n📊 GENERACIÓN")
    print(f"   Total anual: {df['energia_kwh'].sum():,.0f} kWh")
    print(f"   Promedio diario: {df['energia_kwh'].sum()/365:,.0f} kWh")
    print(f"   Promedio horario: {df['energia_kwh'].mean():.2f} kWh")
    print(f"   Factor de capacidad: {df['energia_kwh'].sum()/365/4050*100:.2f}%")

    print("\n🌞 RADIACIÓN SOLAR")
    print(f"   Irradiancia promedio: {df['irradiancia_ghi'].mean():.2f} W/m²")
    print(f"   Irradiancia máxima: {df['irradiancia_ghi'].max():.2f} W/m²")
    print(f"   Nubosidad estimada: ~50-55% (Iquitos tropical)")

    print("\n🌡️  CLIMA")
    print(f"   Temperatura promedio: {df['temperatura_c'].mean():.2f}°C")
    print(f"   Rango temperatura: {df['temperatura_c'].min():.2f}°C a {df['temperatura_c'].max():.2f}°C")
    print(f"   Velocidad viento promedio: {df['velocidad_viento_ms'].mean():.2f} m/s")

    print("\n✅ ARCHIVO")
    print(f"   Ruta: data/oe2/Generacionsolar/solar_generation_profile_2024.csv")
    print(f"   Tamaño: ~818 KB")
    print(f"   Registros: {len(df):,} (8,760 = 1 año)")
    print(f"   Formato: CSV UTF-8")

    print("\n📌 CASOS DE USO")
    print("   ✓ Entrenar agentes RL (SAC, PPO, A2C)")
    print("   ✓ Optimizar despacho de chargers")
    print("   ✓ Analizar variabilidad solar")
    print("   ✓ Evaluar desempeño del sistema BESS")
    print("   ✓ Dimensionamiento de infraestructura")

    print("\n" + "=" * 70 + "\n")

def main():
    """Función principal."""
    print("🔍 Verificando integración con CityLearn...\n")

    # 1. Cargar datos
    df = load_solar_data()

    # 2. Validar
    is_valid = validate_for_citylearn(df)

    # 3. Ejemplos de uso
    if is_valid:
        example_usage_citylearn(df)
        generate_summary_report(df)

        print("🎯 PRÓXIMOS PASOS:")
        print("   1. Integrar datos en DatasetBuilder (OE3)")
        print("   2. Crear environment CityLearn")
        print("   3. Entrenar agentes: python -m scripts.run_oe3_simulate --agent sac")
        print("   4. Evaluar resultados vs baseline\n")

if __name__ == "__main__":
    main()
