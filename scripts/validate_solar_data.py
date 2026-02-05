"""Script para validar y mostrar información del archivo de generación solar."""

import pandas as pd
import os

csv_path = 'data/oe2/Generacionsolar/solar_generation_profile_2024.csv'

if os.path.exists(csv_path):
    file_size = os.path.getsize(csv_path) / 1024
    print(f'📊 INFORMACIÓN DEL ARCHIVO')
    print(f'   Ruta: {csv_path}')
    print(f'   Tamaño: {file_size:.2f} KB')

    df = pd.read_csv(csv_path)
    print(f'\n✅ VALIDACIÓN')
    print(f'   Total registros: {len(df)} (esperado: 8,760)')
    print(f'   Tamaño correcto: {"SÍ" if len(df) == 8760 else "NO"}')

    print(f'\n📋 COLUMNAS GENERADAS:')
    for col in df.columns:
        print(f'   ✓ {col}')

    print(f'\n📈 ESTADÍSTICAS POR COLUMNA:')
    for col in ['irradiancia_ghi', 'potencia_kw', 'energia_kwh', 'temperatura_c', 'velocidad_viento_ms']:
        if col in df.columns:
            print(f'\n   {col.upper()}:')
            print(f'      Mínimo: {df[col].min():.2f}')
            print(f'      Máximo: {df[col].max():.2f}')
            print(f'      Promedio: {df[col].mean():.2f}')
            print(f'      Desv. Est: {df[col].std():.2f}')

    print(f'\n📅 RANGO DE FECHAS:')
    print(f'   Desde: {df["fecha"].min()}')
    print(f'   Hasta: {df["fecha"].max()}')

    print(f'\n⏰ RANGO HORARIO:')
    print(f'   Horas disponibles: {sorted(df["hora"].unique())}')

    print(f'\n💡 ENERGÍA TOTAL AÑO 2024:')
    print(f'   {df["energia_kwh"].sum():,.2f} kWh')

    print(f'\n📝 PRIMEROS 10 REGISTROS:')
    print(df.head(10).to_string(index=False))

    print(f'\n📝 ÚLTIMOS 10 REGISTROS:')
    print(df.tail(10).to_string(index=False))

    print(f'\n✅ ARCHIVO LISTO PARA ENTRENAR AGENTES')
else:
    print(f'❌ ERROR: No se encontró el archivo {csv_path}')
