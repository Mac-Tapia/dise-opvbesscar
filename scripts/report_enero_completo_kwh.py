"""
REPORTE: TODO ENERO - Demanda del Mall cada 15 minutos EN ENERGÍA (kWh)
Datos reales OE2 sin procesamiento
Conversión: kWh = kW × 0.25 horas (15 minutos)
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from _pandas_dt_helpers import extract_hour, extract_minute, extract_date, extract_day_name, extract_day

# ============================================================================
# 1. CARGAR Y FILTRAR DATOS
# ============================================================================
print('\n' + '='*90)
print('[REPORTE TODO ENERO - DEMANDA 15-MINUTO EN ENERGÍA (kWh)]')
print('='*90)

data_path = Path('data/interim/oe2/demandamallkwh/demandamallkwh.csv')
df = pd.read_csv(data_path, sep=';')
df['FECHAHORA'] = pd.to_datetime(df['FECHAHORA'], format='%d/%m/%Y %H:%M')
df = df.sort_values('FECHAHORA').reset_index(drop=True)

# Filtrar TODO enero (1-31)
enero_start = pd.to_datetime('2024-01-01')
enero_end = pd.to_datetime('2024-01-31 23:59:59')
df_enero = df[(df['FECHAHORA'] >= enero_start) & (df['FECHAHORA'] <= enero_end)].copy()

# Convertir kW a kWh (15 minutos = 0.25 horas)
df_enero['kWh'] = df_enero['kWh'] * 0.25

print(f'\n✓ Datos cargados: {len(df_enero):,} registros (TODO enero)')
print(f'  Período: {df_enero["FECHAHORA"].min()} a {df_enero["FECHAHORA"].max()}')
print(f'  Registros esperados: {31 * 24 * 4} (31 días × 24 horas × 4 intervalos de 15-min)')
print(f'  Unidad: kWh (Energía por intervalo 15-minuto)')

# Agregar columnas de análisis
df_enero['hora'] = extract_hour(df_enero['FECHAHORA'])
df_enero['minuto'] = extract_minute(df_enero['FECHAHORA'])
df_enero['fecha'] = extract_date(df_enero['FECHAHORA'])
df_enero['dia_semana'] = extract_day_name(df_enero['FECHAHORA'])
df_enero['día'] = extract_day(df_enero['FECHAHORA'])

# ============================================================================
# 2. ESTADÍSTICAS GLOBALES
# ============================================================================
print('\n' + '-'*90)
print('[ESTADÍSTICAS GLOBALES - TODO ENERO]')
print('-'*90)

print(f'\n📊 DEMANDA POR ENERGÍA (kWh):')
print(f'   ├─ Energía promedio por intervalo: {df_enero["kWh"].mean():.2f} kWh')
print(f'   ├─ Energía mínima: {df_enero["kWh"].min():.2f} kWh')
print(f'   ├─ Energía máxima: {df_enero["kWh"].max():.2f} kWh')
print(f'   └─ Energía acumulada ENERO: {df_enero["kWh"].sum():.1f} kWh')

# ============================================================================
# 3. ESTADÍSTICAS POR DÍA
# ============================================================================
print('\n' + '-'*90)
print('[ESTADÍSTICAS POR DÍA - ENERO 2024]')
print('-'*90)

daily_stats = df_enero.groupby('día').agg({
    'kWh': ['count', 'mean', 'min', 'max', 'sum']
}).round(2)

daily_stats.columns = ['Registros', 'Promedio', 'Mínimo', 'Máximo', 'Acumulado']

print('\n┌────────┬──────────┬────────────┬──────────┬──────────┬──────────────┐')
print('│  Día   │ Registros│  Promedio  │  Mínimo  │  Máximo  │ Acumulado    │')
print('│ (Enero)│ (15-min) │   (kWh)    │  (kWh)   │  (kWh)   │  (kWh)       │')
print('├────────┼──────────┼────────────┼──────────┼──────────┼──────────────┤')

for dia, row in daily_stats.iterrows():
    print(f'│ {dia:2d}/01 │   {int(row["Registros"]):3d}    │   {row["Promedio"]:6.2f}    │  {row["Mínimo"]:6.2f}  │  {row["Máximo"]:6.2f}  │    {row["Acumulado"]:8.1f}    │')

print('└────────┴──────────┴────────────┴──────────┴──────────┴──────────────┘')

# ============================================================================
# 4. ANÁLISIS HORARIO (promedio por hora del día en todo enero)
# ============================================================================
print('\n' + '-'*90)
print('[ANÁLISIS HORARIO - Promedio de TODO ENERO (kWh)]')
print('-'*90)

hourly_stats = df_enero.groupby('hora').agg({
    'kWh': ['mean', 'min', 'max', 'std']
}).round(2)

hourly_stats.columns = ['Promedio', 'Mínimo', 'Máximo', 'Desv.Std']

print('\n┌─────────┬─────────────┬─────────┬─────────┬─────────────┐')
print('│  Hora   │   Promedio  │  Mínimo │  Máximo │  Desv.Std   │')
print('│ (24h)   │    (kWh)    │  (kWh)  │  (kWh)  │    (kWh)    │')
print('├─────────┼─────────────┼─────────┼─────────┼─────────────┤')

for hora, row in hourly_stats.iterrows():
    print(f'│ {hora:2d}:00  │    {row["Promedio"]:6.2f}   │  {row["Mínimo"]:6.2f}  │  {row["Máximo"]:6.2f}  │    {row["Desv.Std"]:6.2f}    │')

print('└─────────┴─────────────┴─────────┴─────────┴─────────────┘')

# ============================================================================
# 5. TOP 20 MÁXIMOS INTERVALOS DE ENERGÍA
# ============================================================================
print('\n' + '-'*90)
print('[TOP 20 MÁXIMOS INTERVALOS DE ENERGÍA - ENERO]')
print('-'*90)

top_peaks = df_enero.nlargest(20, 'kWh')[['FECHAHORA', 'dia_semana', 'kWh']].reset_index(drop=True)
top_peaks.index = top_peaks.index + 1

print('\n')
for idx, row in top_peaks.iterrows():
    timestamp = row['FECHAHORA'].strftime('%d/01 %H:%M')
    day_name = row['dia_semana']
    energy = row['kWh']
    print(f'  {idx:2d}. {timestamp}  ({day_name:9s})  →  {energy:6.2f} kWh')

# ============================================================================
# 6. GENERACIÓN DE GRÁFICOS
# ============================================================================
print('\n' + '-'*90)
print('[GENERANDO GRÁFICOS]')
print('-'*90)

fig, axes = plt.subplots(2, 2, figsize=(16, 10))
fig.suptitle('DEMANDA DEL MALL - ENERO 2024 (ENERGÍA EN kWh)', fontsize=16, fontweight='bold')

# Subplot 1: Serie temporal completa (TODO enero)
ax1 = axes[0, 0]
ax1.plot(df_enero['FECHAHORA'], df_enero['kWh'], linewidth=1, color='steelblue', alpha=0.8)
ax1.set_title('Serie Temporal - TODO ENERO (cada 15 minutos)', fontweight='bold')
ax1.set_xlabel('Fecha')
ax1.set_ylabel('Energía (kWh)')
ax1.grid(True, alpha=0.3)
ax1.tick_params(axis='x', rotation=45)

# Subplot 2: Energía acumulada por día
ax2 = axes[0, 1]
daily_cumsum = df_enero.groupby('día')['kWh'].sum()
ax2.bar(daily_cumsum.index, daily_cumsum.values, color='forestgreen', alpha=0.7, edgecolor='black')
ax2.set_title('Energía Acumulada por Día', fontweight='bold')
ax2.set_xlabel('Día de Enero')
ax2.set_ylabel('Energía Acumulada (kWh)')
ax2.grid(True, alpha=0.3, axis='y')
ax2.set_xticks(range(1, 32, 2))

# Subplot 3: Promedio horario (boxplot)
ax3 = axes[1, 0]
hourly_data = [df_enero[df_enero['hora'] == h]['kWh'].values for h in range(24)]
bp = ax3.boxplot(hourly_data, labels=range(24), patch_artist=True)
for patch in bp['boxes']:
    patch.set_facecolor('lightblue')
ax3.set_title('Distribución de Energía por Hora del Día', fontweight='bold')
ax3.set_xlabel('Hora (24h)')
ax3.set_ylabel('Energía (kWh)')
ax3.grid(True, alpha=0.3, axis='y')

# Subplot 4: Histograma
ax4 = axes[1, 1]
ax4.hist(df_enero['kWh'], bins=40, color='coral', alpha=0.7, edgecolor='black')
ax4.set_title('Distribución de Energía - TODO ENERO', fontweight='bold')
ax4.set_xlabel('Energía (kWh)')
ax4.set_ylabel('Frecuencia (intervalos)')
ax4.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
output_path = Path('outputs/mall_demand_enero_completo_kwh.png')
output_path.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f'\n✓ Gráficos guardados: {output_path}')

# ============================================================================
# 7. EXPORTAR DATOS COMPLETOS
# ============================================================================
print('\n' + '-'*90)
print('[EXPORTAR DATOS]')
print('-'*90)

export_df = df_enero[['FECHAHORA', 'dia_semana', 'hora', 'minuto', 'día', 'kWh']].copy()
export_df.columns = ['fecha_hora', 'día_semana', 'hora', 'minuto', 'día_mes', 'energía_kwh']
export_df = export_df.sort_values('fecha_hora').reset_index(drop=True)

export_path = Path('outputs/mall_demand_enero_completo_kwh.csv')
export_df.to_csv(export_path, index=False)
print(f'\n✓ Datos exportados: {export_path}')
print(f'  Registros: {len(export_df):,}')

# ============================================================================
# 8. RESUMEN FINAL
# ============================================================================
print('\n' + '='*90)
print('[RESUMEN FINAL]')
print('='*90)

print(f'\n📊 Demanda del Mall - ENERO 2024 (EN ENERGÍA kWh)')
print(f'   Período: 1 a 31 de enero')
print(f'   Resolución: 15-minuto')
print(f'   Total registros: {len(export_df):,}')
print(f'\n   Estadísticas de Energía (kWh):')
print(f'   ├─ Promedio por intervalo: {df_enero["kWh"].mean():.2f} kWh')
print(f'   ├─ Mínimo: {df_enero["kWh"].min():.2f} kWh')
print(f'   ├─ Máximo: {df_enero["kWh"].max():.2f} kWh')
print(f'   └─ Total ENERO: {df_enero["kWh"].sum():.1f} kWh')
print(f'\n   Días más demandantes:')
for i, (dia, val) in enumerate(daily_cumsum.nlargest(3).items(), 1):
    print(f'   {i}. Día {dia}: {val:.1f} kWh')

print(f'\n📁 Archivos generados:')
print(f'   ✓ {output_path} (gráficos)')
print(f'   ✓ {export_path} (datos completos)')

print('\n' + '='*90)
