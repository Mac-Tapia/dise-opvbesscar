"""
Comparación visual entre perfil horario vs 15 minutos
Muestra cómo la resolución de 15 min captura mejor los picos
"""
import sys
sys.path.insert(0, 'src')

import pandas as pd
import numpy as np
from pathlib import Path

# Cargar perfil de 15 min
perfil_15min = pd.read_csv('data/oe2/perfil_horario_carga.csv')

# Crear perfil "horario" agregando cada 4 intervalos
perfil_horario = perfil_15min.groupby('hour').agg({
    'energy_kwh': 'sum',
    'power_kw': 'mean',  # Promedio de potencia
    'is_peak': 'first'
}).reset_index()

print("=" * 80)
print("COMPARACIÓN: RESOLUCIÓN HORARIA vs 15 MINUTOS")
print("=" * 80)

print(f"\n{'='*80}")
print("DATOS GENERALES")
print("="*80)
print(f"Perfil 15 min:")
print(f"  - Intervalos: {len(perfil_15min)}")
print(f"  - Energía total: {perfil_15min['energy_kwh'].sum():.2f} kWh")
print(f"  - Potencia máxima: {perfil_15min['power_kw'].max():.2f} kW")

print(f"\nPerfil horario (agregado):")
print(f"  - Horas: {len(perfil_horario)}")
print(f"  - Energía total: {perfil_horario['energy_kwh'].sum():.2f} kWh")
print(f"  - Potencia máxima promedio: {perfil_horario['power_kw'].max():.2f} kW")

print(f"\n{'='*80}")
print("DIFERENCIA CRÍTICA: PICOS DE POTENCIA")
print("="*80)

# Hora pico más crítica (18h)
hora_18 = perfil_15min[perfil_15min['hour'] == 18]
hora_18_agg = perfil_horario[perfil_horario['hour'] == 18]

print(f"\nHORA 18 (6 PM) - Inicio de hora pico:")
print(f"\n  RESOLUCIÓN 15 MIN (4 intervalos):")
print(f"  {'Intervalo':<12} {'Tiempo':<12} {'Potencia (kW)':<15} {'Energía (kWh)'}")
print("  " + "-" * 60)
for idx, row in hora_18.iterrows():
    print(f"  {row['interval']:<12} {row['hour']:02d}:{row['minute']:02d}{'':>8} "
          f"{row['power_kw']:>14.2f} {row['energy_kwh']:>14.2f}")

print(f"\n  RESOLUCIÓN HORARIA (agregado):")
print(f"  {'Hora':<12} {'Potencia Prom (kW)':<20} {'Energía Total (kWh)'}")
print("  " + "-" * 60)
print(f"  {hora_18_agg.iloc[0]['hour']:<12} "
      f"{hora_18_agg.iloc[0]['power_kw']:>18.2f} "
      f"{hora_18_agg.iloc[0]['energy_kwh']:>20.2f}")

pico_15min = hora_18['power_kw'].max()
prom_horario = hora_18_agg.iloc[0]['power_kw']
diferencia_pct = ((pico_15min - prom_horario) / prom_horario) * 100

print(f"\n  {'='*76}")
print(f"  ANÁLISIS:")
print(f"    - Pico real (15 min): {pico_15min:,.2f} kW")
print(f"    - Promedio horario:   {prom_horario:,.2f} kW")
print(f"    - Diferencia:         {pico_15min - prom_horario:,.2f} kW (+{diferencia_pct:.1f}%)")
print(f"  {'='*76}")

print(f"\n{'='*80}")
print("IMPACTO EN DIMENSIONAMIENTO DE BESS")
print("="*80)
print(f"""
Con resolución HORARIA:
  - Potencia diseño: {prom_horario:.2f} kW (promedio horario)
  - ⚠️ SUBDIMENSIONADO: No cubre picos reales de 15 min

Con resolución 15 MINUTOS:
  - Potencia diseño: {pico_15min:.2f} kW (pico real detectado)
  - ✅ CORRECTO: Cubre todos los picos de demanda

CONCLUSIÓN:
  Un BESS dimensionado solo con datos horarios NO podría cubrir
  los picos reales de {pico_15min:.2f} kW que ocurren en intervalos de 15 min.

  Diferencia crítica: {pico_15min - prom_horario:.2f} kW adicionales necesarios
""")

print(f"{'='*80}")
print("RESUMEN DE HORARIO PICO (18h-21h)")
print("="*80)

horas_pico = perfil_15min[perfil_15min['is_peak'] == True]
horas_pico_agg = perfil_horario[perfil_horario['is_peak'] == True]

print(f"\nResolución 15 MIN:")
print(f"  - Intervalos pico: {len(horas_pico)}")
print(f"  - Energía pico: {horas_pico['energy_kwh'].sum():.2f} kWh")
print(f"  - Potencia máxima: {horas_pico['power_kw'].max():.2f} kW")
print(f"  - Potencia mínima: {horas_pico['power_kw'].min():.2f} kW")
print(f"  - Potencia promedio: {horas_pico['power_kw'].mean():.2f} kW")

print(f"\nResolución HORARIA:")
print(f"  - Horas pico: {len(horas_pico_agg)}")
print(f"  - Energía pico: {horas_pico_agg['energy_kwh'].sum():.2f} kWh")
print(f"  - Potencia máxima prom: {horas_pico_agg['power_kw'].max():.2f} kW")
print(f"  - Potencia mínima prom: {horas_pico_agg['power_kw'].min():.2f} kW")
print(f"  - Potencia promedio: {horas_pico_agg['power_kw'].mean():.2f} kW")

print(f"\n{'='*80}")
print("TABLA COMPARATIVA - HORARIO DE OPERACIÓN (9h-22h)")
print("="*80)
print(f"\n{'Hora':<6} {'15min Max (kW)':<16} {'Horario Prom (kW)':<20} {'Diferencia (kW)':<16} {'% Dif'}")
print("-" * 80)

for hora in range(9, 23):
    data_15min = perfil_15min[perfil_15min['hour'] == hora]
    data_horario = perfil_horario[perfil_horario['hour'] == hora]

    if len(data_15min) > 0 and len(data_horario) > 0:
        max_15min = data_15min['power_kw'].max()
        prom_horario_val = data_horario.iloc[0]['power_kw']
        diferencia = max_15min - prom_horario_val
        pct_dif = (diferencia / prom_horario_val * 100) if prom_horario_val > 0 else 0

        print(f"{hora:>4}h  {max_15min:>14.2f}  {prom_horario_val:>18.2f}  "
              f"{diferencia:>14.2f}  {pct_dif:>6.1f}%")

print("=" * 80)
