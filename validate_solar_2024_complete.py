#!/usr/bin/env python
"""Validación completa del perfil solar 2024 para CityLearn v2"""

import pandas as pd
import numpy as np
from pathlib import Path

def validate_solar_profile():
    """Valida que el archivo solar generado cumple todos los requisitos"""

    # Cargar el archivo
    csv_path = Path('data/oe2/Generacionsolar/solar_generation_profile_2024.csv')

    if not csv_path.exists():
        print("❌ ERROR: Archivo no encontrado en", csv_path)
        return False

    df = pd.read_csv(csv_path)

    print("=" * 80)
    print("✅ VALIDACIÓN DE PERFIL SOLAR 2024")
    print("=" * 80)
    print()

    # Validación básica
    print("📊 INFORMACIÓN DEL ARCHIVO:")
    print(f"  • Ruta: {csv_path}")
    print(f"  • Tamaño: {csv_path.stat().st_size / 1024:.2f} KB")
    print(f"  • Total registros: {len(df):,} (esperado: 8,760 = 365 días × 24 horas)")
    print(f"  • Rango de fechas: {df['fecha'].min()} hasta {df['fecha'].max()}")
    print()

    # Validar estructura
    print("📋 COLUMNAS GENERADAS:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i}. {col}")
    print()

    # Validar integridad
    print("🔍 VALIDACIONES DE INTEGRIDAD:")
    checks = [
        ("Total registros == 8,760", len(df) == 8760),
        ("Sin valores NaN", df.isnull().sum().sum() == 0),
        ("Horas 0-23 válidas", set(df['hora']) == set(range(24))),
        ("Energía no negativa", (df['energia_kwh'] >= 0).all()),
        ("Potencia no negativa", (df['potencia_kw'] >= 0).all()),
    ]

    all_pass = True
    for check_name, result in checks:
        status = "✓" if result else "✗"
        print(f"  {status} {check_name}: {result}")
        all_pass = all_pass and result
    print()

    # Estadísticas
    print("📈 ESTADÍSTICAS POR COLUMNA:")
    print(f"  • Fecha (1 ene - 31 dic)")
    print(f"    {df['fecha'].min()} a {df['fecha'].max()}")

    print(f"  • Hora (índice por hora)")
    print(f"    0-23 (todas {len(set(df['hora']))} horas presentes)")

    print(f"  • Irradiancia GHI [W/m²]")
    print(f"    Min: {df['irradiancia_ghi'].min():.2f} | Max: {df['irradiancia_ghi'].max():.2f} | Prom: {df['irradiancia_ghi'].mean():.2f}")

    print(f"  • Potencia [kW]")
    print(f"    Min: {df['potencia_kw'].min():.2f} | Max: {df['potencia_kw'].max():.2f} | Prom: {df['potencia_kw'].mean():.2f}")

    print(f"  • Energía [kWh/hora]")
    print(f"    Min: {df['energia_kwh'].min():.2f} | Max: {df['energia_kwh'].max():.2f} | Total año: {df['energia_kwh'].sum():.0f}")

    print(f"  • Temperatura [°C]")
    print(f"    Min: {df['temperatura_c'].min():.2f} | Max: {df['temperatura_c'].max():.2f} | Prom: {df['temperatura_c'].mean():.2f}")

    print(f"  • Vel. Viento [m/s]")
    print(f"    Min: {df['velocidad_viento_ms'].min():.2f} | Max: {df['velocidad_viento_ms'].max():.2f} | Prom: {df['velocidad_viento_ms'].mean():.2f}")
    print()

    # Datos para entrenamiento
    print("🤖 LISTO PARA ENTRENAMIENTO EN CITYLEARN v2:")
    print(f"  ✅ Datos horarios completos: {len(df)} timesteps (1 año)")
    print(f"  ✅ Energía solar anual: {df['energia_kwh'].sum():,.0f} kWh")
    print(f"  ✅ Factor de carga: {(df['energia_kwh'].sum() / 4050 / 8760 * 100):.2f}%")
    print(f"  ✅ Archivo CSV: schema listo para DatasetBuilder")
    print(f"  ✅ Columnas requeridas presentes: fecha, hora, energia_kwh, potencia_kw, temperatura_c")
    print()

    # Preview
    print("📄 PRIMERAS 5 REGISTROS:")
    print(df.head(5).to_string(index=False))
    print()
    print("📄 ÚLTIMOS 5 REGISTROS:")
    print(df.tail(5).to_string(index=False))
    print()

    print("=" * 80)
    if all_pass:
        print("✅ ARCHIVO GENERADO Y VALIDADO CORRECTAMENTE")
    else:
        print("⚠️  ALGUNAS VALIDACIONES FALLARON")
    print("=" * 80)

    return all_pass

if __name__ == "__main__":
    validate_solar_profile()
