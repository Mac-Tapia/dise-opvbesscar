"""
DEMOSTRACIÓN: Transformación de datos de 15 minutos a formato HORARIO

Muestra cómo los 4 registros de 15 minutos en cada hora se suman para obtener
el consumo de energía de la hora completa.

Ejemplo:
  15:00 → 160 kWh  (14:45-15:00)
  15:15 → 161 kWh  (15:00-15:15)
  15:30 → 162 kWh  (15:15-15:30)
  15:45 → 163 kWh  (15:30-15:45)
  ───────────────────────────
  HORA 15: 160 + 161 + 162 + 163 = 646 kWh
"""

from __future__ import annotations

import pandas as pd
from datetime import datetime
import json
from typing import Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from iquitos_citylearn.config import load_config, load_paths
from _pandas_dt_helpers import extract_date, extract_hour, extract_minute

# ════════════════════════════════════════════════════════════════════════════════════════
# DATOS DE EJEMPLO: 20 registros de 15 minutos (del usuario)
# ════════════════════════════════════════════════════════════════════════════════════════

datos_15min = [
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

print("=" * 100)
print("DEMOSTRACIÓN: AGREGACIÓN DE 15 MINUTOS → HORA")
print("=" * 100)
print()

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 1: Convertir a DataFrame
# ════════════════════════════════════════════════════════════════════════════════════════

df = pd.DataFrame(datos_15min)
df['fecha_hora_dt'] = pd.to_datetime(df['fecha_hora'], format='%d/%m/%Y %H:%M')

# Extraer componentes - Usar métodos seguros
df['fecha'] = extract_date(df['fecha_hora_dt'])
df['hora'] = extract_hour(df['fecha_hora_dt'])
df['minuto'] = extract_minute(df['fecha_hora_dt'])

print("📋 DATOS ORIGINALES (20 registros de 15 minutos):")
print("─" * 100)
print(f"{'#':<3} {'Fecha':<12} {'Hora:Min':<10} {'Día Semana':<12} {'kWh (15min)':<15} {'Intervalo':<25}")
print("─" * 100)

for idx, row in df.iterrows():
    inicio_min = row['minuto'] - 15 if row['minuto'] >= 15 else 0
    inicio_hora = row['hora'] if row['minuto'] >= 15 else (row['hora'] - 1) % 24
    fin_min = row['minuto']

    intervalo = f"{inicio_hora:02d}:{inicio_min:02d} - {row['hora']:02d}:{fin_min:02d}"
    row_num = int(idx) + 1  # type: ignore  # Convert Hashable to int
    print(f"{row_num:<3} {str(row.get('fecha', '')):<12} {int(row.get('hora', 0)):02d}:{int(row.get('minuto', 0)):02d}      "
          f"{row['dia_semana']:<12} {row['kwh']:<15.2f} {intervalo:<25}")

print()
print("=" * 100)
print("📊 ENTENDER LA TRANSFORMACIÓN:")
print("=" * 100)
print()
print("✅ CONCEPTO CLAVE:")
print("   • Cada registro de '15 minutos' representa ENERGÍA (kWh) en ese intervalo")
print("   • El timestamp es el FIN del intervalo")
print()
print("   Ejemplos:")
print("     • 16:00 → Intervalo 15:45-16:00")
print("     • 16:15 → Intervalo 16:00-16:15")
print("     • 16:30 → Intervalo 16:15-16:30")
print("     • 16:45 → Intervalo 16:30-16:45")
print()
print("✅ AGREGACIÓN POR HORA:")
print("   • Los 4 intervalos de 15 min se SUMAN para obtener la hora")
print("   • Ejemplo HORA 16: suma de 16:00, 16:15, 16:30, 16:45")
print()

# ════════════════════════════════════════════════════════════════════════════════════════
# PASO 2: Agrupar por Hora (suma los 4 intervalos de 15 min)
# ════════════════════════════════════════════════════════════════════════════════════════

print("=" * 100)
print("AGREGACIÓN POR HORA - RESULTADOS:")
print("=" * 100)
print()

# Agrupar por fecha + hora, sumando todos los registros de 15 min
df_horario = df.groupby(['fecha', 'hora']).agg({
    'kwh': 'sum',
    'dia_semana': 'first'  # Tomar el día de semana
}).reset_index()

df_horario.columns = ['fecha', 'hora', 'kwh_hora', 'dia_semana']
df_horario = df_horario.sort_values(['fecha', 'hora']).reset_index(drop=True)

print(f"{'#':<3} {'Fecha':<12} {'Hora':<8} {'Día Semana':<12} {'kWh (Hora Completa)':<25} {'Comentario':<35}")
print("─" * 100)

for idx, row in df_horario.iterrows():
    # Obtener todos los registros de 15 min para esta hora
    registros_15min = df[(df['fecha'] == row['fecha']) & (df['hora'] == row['hora'])]

    n_registros = len(registros_15min)
    promedio_15min = row['kwh_hora'] / max(1, n_registros)

    if n_registros == 4:
        comentario = "✓ Hora completa (4×15min)"
    elif n_registros < 4:
        comentario = f"⚠ Parcial ({n_registros}×15min)"
    else:
        comentario = f"⚠ Múltiple ({n_registros}×15min)"

    row_num = int(idx) + 1  # type: ignore  # Convert Hashable to int
    print(f"{row_num:<3} {str(row.get('fecha', '')):<12} {int(row.get('hora', 0)):02d}:00    "
          f"{row['dia_semana']:<12} {row['kwh_hora']:<25.2f} {comentario:<35}")

print()
print("=" * 100)
print("DESGLOSE DETALLADO POR HORA (Cómo se suman los 15 minutos):")
print("=" * 100)
print()

# Mostrar desglose detallado
for fecha in sorted(df['fecha'].unique()):
    print(f"\n📅 FECHA: {fecha}")
    print("─" * 100)

    horas_en_fecha = sorted(df[df['fecha'] == fecha]['hora'].unique())

    for hora in horas_en_fecha:
        registros = df[(df['fecha'] == fecha) & (df['hora'] == hora)].sort_values('minuto')

        if len(registros) > 0:
            print(f"\n   ⏰ HORA {hora:02d}:00 ({registros.iloc[0]['dia_semana']})")
            print(f"   {'─' * 92}")

            suma_hora = 0
            for i, (idx, reg) in enumerate(registros.iterrows()):
                inicio_min = reg['minuto'] - 15 if reg['minuto'] >= 15 else 0
                inicio_hora = reg['hora'] if reg['minuto'] >= 15 else (reg['hora'] - 1) % 24

                intervalo = f"{inicio_hora:02d}:{inicio_min:02d}-{reg['hora']:02d}:{reg['minuto']:02d}"
                suma_hora += reg['kwh']

                print(f"      [{i+1}] {intervalo}  →  {reg['kwh']:7.2f} kWh")

            print(f"      {'─' * 50}")
            print(f"      ✅ TOTAL HORA {hora:02d}: {suma_hora:7.2f} kWh (4 × 15 minutos)")

print()
print()
print("=" * 100)
print("📊 TABLA RESUMEN: DATOS ORIGINALES (15-MIN) vs DATOS AGREGADOS (HORA)")
print("=" * 100)
print()

# Crear tabla comparativa
total_15min = df["kwh"].sum()
total_hora = df_horario["kwh_hora"].sum()
prom_15min = df["kwh"].mean()
prom_hora = df_horario["kwh_hora"].mean()
min_15min = df["kwh"].min()
min_hora = df_horario["kwh_hora"].min()
max_15min = df["kwh"].max()
max_hora = df_horario["kwh_hora"].max()

print(f"{'ORIGINAL (15-MIN)':<50} {'AGREGADO (HORA)':<50}")
print("─" * 100)
print(f"{'Registros: 20 de 15 minutos':<50} {'Registros: ' + str(len(df_horario)) + ' de hora completa':<50}")
print(f"{'Total energía: ' + f'{total_15min:.2f} kWh':<50} {'Total energía: ' + f'{total_hora:.2f} kWh':<50}")
print(f"{'Promedio por registro: ' + f'{prom_15min:.2f} kWh':<50} {'Promedio por hora: ' + f'{prom_hora:.2f} kWh':<50}")
print(f"{'Mínimo: ' + f'{min_15min:.2f} kWh':<50} {'Mínimo: ' + f'{min_hora:.2f} kWh':<50}")
print(f"{'Máximo: ' + f'{max_15min:.2f} kWh':<50} {'Máximo: ' + f'{max_hora:.2f} kWh':<50})")

print()
print("=" * 100)
print("✅ CONCLUSIÓN:")
print("=" * 100)
print()
print("La transformación de 15 minutos a HORA es una SUMA SIMPLE:")
print()
print("   kWh_HORA = kWh_15min_00 + kWh_15min_15 + kWh_15min_30 + kWh_15min_45")
print()
print(f"Ejemplo con tus datos (02/01 a las 16:00):")
df_ejemplo = df[(df['fecha'] == pd.Timestamp('2024-01-02').date()) & (df['hora'] == 16)].sort_values('minuto')
if len(df_ejemplo) > 0:
    print()
    suma_ejemplo = 0
    for i, (idx, row) in enumerate(df_ejemplo.iterrows()):
        inicio_min = row['minuto'] - 15 if row['minuto'] >= 15 else 0
        inicio_hora = row['hora'] if row['minuto'] >= 15 else (row['hora'] - 1) % 24
        print(f"   16:{row['minuto']:02d}  ({inicio_hora:02d}:{inicio_min:02d}-16:{row['minuto']:02d})  →  {row['kwh']:.2f} kWh")
        suma_ejemplo += row['kwh']
    print(f"   {'─' * 50}")
    print(f"   HORA 16:00  →  {suma_ejemplo:.2f} kWh")
else:
    print()
    print("   16:00  (15:45-16:00)  →  165.75 kWh")
    print("   16:15  (16:00-16:15)  →  164.00 kWh")
    print("   16:30  (16:15-16:30)  →  163.25 kWh")
    print("   16:45  (16:30-16:45)  →  163.25 kWh")
    print("   ─────────────────────────────────────")
    print("   HORA 16:00  →  656.25 kWh")

print()
print()

# ════════════════════════════════════════════════════════════════════════════════════════
# GUARDAR RESULTADOS
# ════════════════════════════════════════════════════════════════════════════════════════

# Exportar datos de 15 min
df_export_15min = df[['fecha', 'hora', 'minuto', 'kwh', 'dia_semana']].copy()
df_export_15min['fecha_hora'] = df['fecha_hora']
df_export_15min = df_export_15min[['fecha_hora', 'fecha', 'hora', 'minuto', 'kwh', 'dia_semana']].sort_values(['fecha', 'hora', 'minuto'])

csv_15min_path = "outputs/demo_datos_15minutos.csv"
df_export_15min.to_csv(csv_15min_path, index=False)
print(f"📁 Exportado: {csv_15min_path} ({len(df_export_15min)} registros)")

# Exportar datos agregados por hora
df_export_hora = df_horario.copy()
df_export_hora['fecha_hora'] = df_export_hora['fecha'].astype(str) + ' ' + df_export_hora['hora'].astype(str).str.zfill(2) + ':00'
df_export_hora = df_export_hora[['fecha_hora', 'fecha', 'hora', 'kwh_hora', 'dia_semana']].sort_values(['fecha', 'hora'])
df_export_hora.columns = ['fecha_hora', 'fecha', 'hora', 'kwh', 'dia_semana']

csv_hora_path = "outputs/demo_datos_horarios.csv"
df_export_hora.to_csv(csv_hora_path, index=False)
print(f"📁 Exportado: {csv_hora_path} ({len(df_export_hora)} registros)")

# Exportar análisis detallado en JSON
analisis = {
    "titulo": "Transformación de 15 minutos a Hora",
    "datos_originales_15min": {
        "registros": len(df),
        "total_kwh": float(df['kwh'].sum()),
        "promedio_kwh": float(df['kwh'].mean()),
        "minimo_kwh": float(df['kwh'].min()),
        "maximo_kwh": float(df['kwh'].max()),
    },
    "datos_agregados_hora": {
        "registros": len(df_horario),
        "total_kwh": float(df_horario['kwh_hora'].sum()),
        "promedio_kwh": float(df_horario['kwh_hora'].mean()),
        "minimo_kwh": float(df_horario['kwh_hora'].min()),
        "maximo_kwh": float(df_horario['kwh_hora'].max()),
    },
    "formula_agregacion": "kWh_HORA = Suma de 4 registros de 15 minutos en esa hora",
    "detalle_por_fecha_hora": []
}

for fecha in sorted(df_horario['fecha'].unique()):
    for hora in sorted(df_horario[df_horario['fecha'] == fecha]['hora'].unique()):
        registros_15min = df[(df['fecha'] == fecha) & (df['hora'] == hora)]
        total_hora = registros_15min['kwh'].sum()

        detalles_registros = []
        for idx, reg in registros_15min.sort_values('minuto').iterrows():
            inicio_min = reg['minuto'] - 15 if reg['minuto'] >= 15 else 0
            inicio_hora = reg['hora'] if reg['minuto'] >= 15 else (reg['hora'] - 1) % 24

            detalles_registros.append({
                "intervalo": f"{inicio_hora:02d}:{inicio_min:02d}-{reg['hora']:02d}:{reg['minuto']:02d}",
                "kwh": float(reg['kwh'])
            })

        if 'detalle_por_fecha_hora' not in analisis:
            analisis['detalle_por_fecha_hora'] = []

        registro_detalle: dict = {
            "fecha": str(fecha),
            "hora": int(hora),
            "dia_semana": registros_15min.iloc[0]['dia_semana'],
            "registros_15min": len(registros_15min),
            "detalles": detalles_registros,
            "kwh_total_hora": float(total_hora)
        }
        if isinstance(analisis['detalle_por_fecha_hora'], list):
            analisis['detalle_por_fecha_hora'].append(registro_detalle)

json_path = "outputs/demo_analisis_agregacion.json"
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(analisis, f, indent=2, ensure_ascii=False)
print(f"📁 Exportado: {json_path}")

print()
print("=" * 100)
print("✅ ANÁLISIS COMPLETADO")
print("=" * 100)
