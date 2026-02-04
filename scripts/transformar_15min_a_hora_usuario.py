"""
TRANSFORMACIÓN: Valores de 15 minutos a HORAS
Datos proporcionados por el usuario - 20 registros
"""

import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _pandas_dt_helpers import extract_date, extract_hour, extract_minute

print("=" * 120)
print("TRANSFORMACIÓN DE 15 MINUTOS A HORAS")
print("=" * 120)
print()

# Datos del usuario - 20 registros de 15 minutos
datos = [
    {"fecha_hora": "02/01/2024 17:00", "dia_semana": "Tuesday", "kwh": 165.75},
    {"fecha_hora": "02/01/2024 16:15", "dia_semana": "Tuesday", "kwh": 164.00},
    {"fecha_hora": "02/01/2024 14:00", "dia_semana": "Tuesday", "kwh": 163.25},
    {"fecha_hora": "02/01/2024 16:45", "dia_semana": "Tuesday", "kwh": 163.25},
    {"fecha_hora": "30/01/2024 16:30", "dia_semana": "Tuesday", "kwh": 163.25},
    {"fecha_hora": "02/01/2024 15:30", "dia_semana": "Tuesday", "kwh": 162.25},
    {"fecha_hora": "04/01/2024 14:45", "dia_semana": "Thursday", "kwh": 162.25},
    {"fecha_hora": "30/01/2024 16:45", "dia_semana": "Tuesday", "kwh": 162.25},
    {"fecha_hora": "04/01/2024 15:00", "dia_semana": "Thursday", "kwh": 161.50},
    {"fecha_hora": "30/01/2024 16:15", "dia_semana": "Tuesday", "kwh": 161.50},
    {"fecha_hora": "02/01/2024 14:15", "dia_semana": "Tuesday", "kwh": 160.50},
    {"fecha_hora": "02/01/2024 15:15", "dia_semana": "Tuesday", "kwh": 160.50},
    {"fecha_hora": "02/01/2024 16:00", "dia_semana": "Tuesday", "kwh": 160.50},
    {"fecha_hora": "02/01/2024 18:00", "dia_semana": "Tuesday", "kwh": 160.50},
    {"fecha_hora": "30/01/2024 14:45", "dia_semana": "Tuesday", "kwh": 160.50},
    {"fecha_hora": "30/01/2024 16:00", "dia_semana": "Tuesday", "kwh": 160.50},
    {"fecha_hora": "02/01/2024 13:00", "dia_semana": "Tuesday", "kwh": 159.75},
    {"fecha_hora": "02/01/2024 13:15", "dia_semana": "Tuesday", "kwh": 159.75},
    {"fecha_hora": "02/01/2024 13:45", "dia_semana": "Tuesday", "kwh": 159.75},
    {"fecha_hora": "02/01/2024 14:30", "dia_semana": "Tuesday", "kwh": 159.75},
]

# Convertir a DataFrame
df = pd.DataFrame(datos)
df['datetime'] = pd.to_datetime(df['fecha_hora'], format='%d/%m/%Y %H:%M')
df['fecha'] = extract_date(df['datetime'])
df['hora'] = extract_hour(df['datetime'])
df['minuto'] = extract_minute(df['datetime'])

# Mostrar datos originales
print("📋 DATOS ORIGINALES (20 registros de 15 minutos):")
print("─" * 120)
print(f"{'#':<3} {'Fecha':<12} {'Hora:Min':<10} {'Día':<10} {'kWh':<10} {'Intervalo':<30}")
print("─" * 120)

for idx, row in df.iterrows():
    # Calcular el intervalo (el timestamp es el FIN)
    inicio_min = row['minuto'] - 15 if row['minuto'] >= 15 else 0
    inicio_hora = row['hora'] if row['minuto'] >= 15 else (row['hora'] - 1) % 24
    intervalo = f"{inicio_hora:02d}:{inicio_min:02d} - {row['hora']:02d}:{row['minuto']:02d}"

    row_num = int(idx) + 1  # type: ignore  # Convert Hashable to int
    print(f"{row_num:<3} {str(row.get('fecha', '')):<12} {int(row.get('hora', 0)):02d}:{int(row.get('minuto', 0)):02d}      "
          f"{row['dia_semana']:<10} {row['kwh']:<10.2f} {intervalo:<30}")

print()
print("=" * 120)
print("🔄 AGRUPANDO POR HORA (Sumando los 4 registros de 15 minutos)")
print("=" * 120)
print()

# Agrupar por fecha y hora
df_horario = df.groupby(['fecha', 'hora']).agg({
    'kwh': 'sum',
    'dia_semana': 'first'
}).reset_index()

df_horario.columns = ['fecha', 'hora', 'kwh_total', 'dia_semana']
df_horario = df_horario.sort_values(['fecha', 'hora']).reset_index(drop=True)

print(f"{'#':<3} {'Fecha':<12} {'Hora':<8} {'Día':<12} {'kWh TOTAL':<15} {'Detalles 15min':<80}")
print("─" * 120)

resultado_horas = []

for idx, row in df_horario.iterrows():
    # Obtener los 4 registros de 15 min para esta hora
    registros = df[(df['fecha'] == row['fecha']) & (df['hora'] == row['hora'])].sort_values('minuto')

    # Detalles
    detalles_lista = []
    for _, reg in registros.iterrows():
        detalles_lista.append(f"{reg['minuto']:02d}min → {reg['kwh']:.2f} kWh")

    detalles = " + ".join(detalles_lista)

    row_num = int(idx) + 1  # type: ignore  # Convert Hashable to int
    print(f"{row_num:<3} {str(row.get('fecha', '')):<12} {int(row.get('hora', 0)):02d}:00    "
          f"{row['dia_semana']:<12} {row['kwh_total']:<15.2f} {detalles:<80}")

    # Guardar resultado
    resultado_horas.append({
        'fecha': row['fecha'],
        'hora': row['hora'],
        'hora_formateada': f"{row['hora']:02d}:00",
        'dia_semana': row['dia_semana'],
        'kwh_total': row['kwh_total'],
        'n_registros': len(registros)
    })

print()
print("=" * 120)
print("✅ RESULTADO FINAL - DATOS TRANSFORMADOS A HORAS")
print("=" * 120)
print()

resultado_df = pd.DataFrame(resultado_horas)

print(f"{'#':<3} {'Fecha':<12} {'Hora':<8} {'Día':<12} {'kWh (Hora Completa)':<22}")
print("─" * 120)

for idx, row in resultado_df.iterrows():
    row_num = int(idx) + 1  # type: ignore  # Convert Hashable to int
    print(f"{row_num:<3} {str(row.get('fecha', '')):<12} {str(row.get('hora_formateada', '')):8} "
          f"{row['dia_semana']:<12} {row['kwh_total']:<22.2f}")

print()
print("=" * 120)
print("📊 RESUMEN ESTADÍSTICO")
print("=" * 120)
print()

print(f"Total de horas transformadas: {len(resultado_df)}")
print(f"Total de energía (suma de horas): {resultado_df['kwh_total'].sum():.2f} kWh")
print(f"Energía promedio por hora: {resultado_df['kwh_total'].mean():.2f} kWh")
print(f"Energía mínima en una hora: {resultado_df['kwh_total'].min():.2f} kWh")
print(f"Energía máxima en una hora: {resultado_df['kwh_total'].max():.2f} kWh")
print()

# Exportar a CSV
csv_path = "outputs/transformacion_15min_a_horas.csv"
resultado_df_export = resultado_df[['fecha', 'hora_formateada', 'dia_semana', 'kwh_total', 'n_registros']]
resultado_df_export.columns = ['fecha', 'hora', 'dia_semana', 'kwh_hora', 'registros_15min']
resultado_df_export.to_csv(csv_path, index=False)

print(f"📁 Resultado exportado a: {csv_path}")
print()
print("=" * 120)
print("✅ TRANSFORMACIÓN COMPLETADA")
print("=" * 120)
