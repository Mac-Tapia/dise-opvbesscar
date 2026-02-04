"""
REPORTE: ENERO - Demanda del Mall por HORA para cada DÍA
Datos reales OE2 - Agregación horaria
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from _pandas_dt_helpers import extract_hour, extract_day, extract_date, extract_day_name, extract_values_float, extract_values_str, safe_int_convert, safe_float_convert, safe_str_convert

# ============================================================================
# 1. CARGAR Y FILTRAR DATOS
# ============================================================================
print('\n' + '='*100)
print('[REPORTE ENERO - DEMANDA HORARIA POR DÍA]')
print('='*100)

data_path = Path('data/interim/oe2/demandamallkwh/demandamallkwh.csv')
df = pd.read_csv(data_path, sep=';')
df['FECHAHORA'] = pd.to_datetime(df['FECHAHORA'], format='%d/%m/%Y %H:%M')
df = df.sort_values('FECHAHORA').reset_index(drop=True)

# Filtrar TODO enero
enero_start = pd.to_datetime('2024-01-01')
enero_end = pd.to_datetime('2024-01-31 23:59:59')
df_enero = df[(df['FECHAHORA'] >= enero_start) & (df['FECHAHORA'] <= enero_end)].copy()

# Agregar columnas
df_enero['hora'] = extract_hour(df_enero['FECHAHORA'])
df_enero['día'] = extract_day(df_enero['FECHAHORA'])
df_enero['fecha'] = extract_date(df_enero['FECHAHORA'])
df_enero['dia_semana'] = extract_day_name(df_enero['FECHAHORA'])

# Agregación horaria (convertir 15-min a hora: sumar 4 intervalos)
df_horario = df_enero.groupby(['día', 'hora', 'dia_semana']).agg({
    'kWh': 'sum'  # Sumar los 4 intervalos de 15-min para obtener kWh/hora
}).reset_index()
df_horario = df_horario.rename(columns={'kWh': 'kWh_hora'})

print(f'\n✓ Datos cargados: {len(df_horario):,} registros (31 días × 24 horas)')
print(f'  Período: 1 a 31 de enero')
print(f'  Unidad: kWh por HORA')

# ============================================================================
# 2. TABLA DETALLADA - TODO ENERO POR HORA
# ============================================================================
print('\n' + '-'*100)
print('[TABLA DETALLADA - ENERO 2024 (DEMANDA HORARIA POR DÍA)]')
print('-'*100)

# Crear tabla pivote: filas=hora, columnas=día
pivot_table = df_horario.pivot(index='hora', columns='día', values='kWh_hora').fillna(0)

# Mostrar tabla con formato
print('\n┌──────┬' + '─'*8*31 + '┬────────────────┐')
print('│ Hora │' + ' │ '.join([f' {i:2d}/01 ' for i in range(1, 32)]) + '│  Promedio  │')
print('├──────┼' + '─'*8*31 + '┼────────────────┤')

for hora in range(24):
    row_data = extract_values_float(pivot_table.loc[hora].values)
    promedio_hora = float(np.mean(row_data))
    row_str = ' │ '.join([f'{val:6.1f}' for val in row_data])
    print(f'│ {hora:2d}:00 │ {row_str} │   {promedio_hora:6.1f}    │')

print('├──────┼' + '─'*8*31 + '┼────────────────┤')
print('│ Mean │' + ' │ '.join([f'{pivot_table[i].mean():6.1f}' for i in range(1, 32)]) + '│  {:6.1f}    │'.format(pivot_table.values.mean()))
print('└──────┴' + '─'*8*31 + '┴────────────────┘')

# ============================================================================
# 3. ESTADÍSTICAS POR HORA (agregado de TODO enero)
# ============================================================================
print('\n' + '-'*100)
print('[ESTADÍSTICAS POR HORA - AGREGADO TODO ENERO (kWh/hora)]')
print('-'*100)

hourly_agg = df_horario.groupby('hora').agg({
    'kWh_hora': ['mean', 'min', 'max', 'std']
}).round(1)
hourly_agg.columns = ['Promedio', 'Mínimo', 'Máximo', 'Desv.Std']

print('\n┌────────┬────────────┬────────────┬────────────┬────────────┐')
print('│ Hora   │  Promedio  │   Mínimo   │   Máximo   │ Desv.Std   │')
print('│ (24h)  │  (kWh/h)   │  (kWh/h)   │  (kWh/h)   │  (kWh/h)   │')
print('├────────┼────────────┼────────────┼────────────┼────────────┤')

for hora in range(24):
    print(f'│ {hora:2d}:00  │  {hourly_agg.loc[hora, "Promedio"]:8.1f}  │  {hourly_agg.loc[hora, "Mínimo"]:8.1f}  │  {hourly_agg.loc[hora, "Máximo"]:8.1f}  │  {hourly_agg.loc[hora, "Desv.Std"]:8.1f}  │')

print('└────────┴────────────┴────────────┴────────────┴────────────┘')

# ============================================================================
# 4. ESTADÍSTICAS POR DÍA (total de 24 horas)
# ============================================================================
print('\n' + '-'*100)
print('[ESTADÍSTICAS POR DÍA - TOTAL DIARIO (kWh/día)]')
print('-'*100)

daily_stats = df_horario.groupby(['día', 'dia_semana']).agg({
    'kWh_hora': ['sum', 'mean', 'min', 'max']
}).round(1)
daily_stats.columns = ['Total_Día', 'Promedio', 'Mínimo', 'Máximo']
daily_stats = daily_stats.reset_index()

print('\n┌────────┬────────────┬─────────────┬────────────┬────────────┬────────────┐')
print('│   Día  │  Día Sem.  │ Total (kWh) │ Prom (kWh) │ Min (kWh)  │ Max (kWh)  │')
print('├────────┼────────────┼─────────────┼────────────┼────────────┼────────────┤')

for idx, row in daily_stats.iterrows():
    print(f'│ {int(row["día"]):2d}/01  │ {str(row["dia_semana"])[:10]:10s} │   {row["Total_Día"]:8.1f}   │  {row["Promedio"]:8.1f}  │  {row["Mínimo"]:8.1f}  │  {row["Máximo"]:8.1f}  │')

print('└────────┴────────────┴─────────────┴────────────┴────────────┴────────────┘')

# ============================================================================
# 5. TOP 10 HORAS MÁS DEMANDANTES
# ============================================================================
print('\n' + '-'*100)
print('[TOP 10 HORAS MÁS DEMANDANTES - ENERO]')
print('-'*100)

top_hours = df_horario.nlargest(10, 'kWh_hora')[['día', 'dia_semana', 'hora', 'kWh_hora']].reset_index(drop=True)

print('\n')
for idx, row in top_hours.iterrows():
    row_num = int(idx) + 1  # type: ignore
    print(f'  {row_num:2d}. {safe_int_convert(row["día"]):2d}/01 a las {safe_int_convert(row["hora"]):2d}:00 ({safe_str_convert(row["dia_semana"])[:10]:10s})  →  {safe_float_convert(row["kWh_hora"]):7.1f} kWh')

# ============================================================================
# 6. GENERACIÓN DE GRÁFICOS
# ============================================================================
print('\n' + '-'*100)
print('[GENERANDO GRÁFICOS]')
print('-'*100)

fig = plt.figure(figsize=(18, 12))
fig.suptitle('DEMANDA DEL MALL - ENERO 2024 (DEMANDA HORARIA POR DÍA)', fontsize=16, fontweight='bold')

# Subplot 1: Mapa de calor (heatmap) - Días vs Horas
ax1 = plt.subplot(2, 2, 1)
heatmap_data = pivot_table.T  # Transponer para que días sean filas y horas sean columnas
im = ax1.imshow(heatmap_data, cmap='YlOrRd', aspect='auto')
ax1.set_xlabel('Hora del Día (24h)', fontweight='bold')
ax1.set_ylabel('Día de Enero', fontweight='bold')
ax1.set_title('Heatmap: Demanda Horaria (kWh/h)', fontweight='bold')
ax1.set_xticks(range(0, 24))
ax1.set_xticklabels([str(i) for i in range(0, 24)])
ax1.set_yticks(range(0, 31, 2))
ax1.set_yticklabels([f'{i}/01' for i in range(1, 32, 2)])
cbar = plt.colorbar(im, ax=ax1)
cbar.set_label('kWh/hora')

# Subplot 2: Perfiles horarios por día (líneas)
ax2 = plt.subplot(2, 2, 2)
for día in range(1, 32):
    día_data = df_horario[df_horario['día'] == día].sort_values('hora')
    ax2.plot(día_data['hora'], día_data['kWh_hora'], alpha=0.4, linewidth=0.8)
# Promedios destacados
promedio_por_hora = df_horario.groupby('hora')['kWh_hora'].mean()
ax2.plot(extract_values_float(promedio_por_hora.index), extract_values_float(promedio_por_hora.values), color='red', linewidth=2.5, label='Promedio Enero', marker='o')
ax2.set_xlabel('Hora del Día (24h)', fontweight='bold')
ax2.set_ylabel('Demanda (kWh/h)', fontweight='bold')
ax2.set_title('Perfiles Horarios - Todos los Días de Enero', fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.legend()
ax2.set_xticks(range(0, 24))

# Subplot 3: Demanda acumulada diaria (barras)
ax3 = plt.subplot(2, 2, 3)
daily_totals = df_horario.groupby('día')['kWh_hora'].sum()
colors = ['red' if daily_totals[i] >= daily_totals.quantile(0.75) else 'steelblue' for i in daily_totals.index]
ax3.bar(extract_values_float(daily_totals.index), extract_values_float(daily_totals.values), color=colors, alpha=0.7, edgecolor='black')
ax3.set_xlabel('Día de Enero', fontweight='bold')
ax3.set_ylabel('Demanda Total (kWh)', fontweight='bold')
ax3.set_title('Demanda Acumulada por Día', fontweight='bold')
ax3.grid(True, alpha=0.3, axis='y')
ax3.set_xticks(range(1, 32, 2))

# Subplot 4: Boxplot por hora
ax4 = plt.subplot(2, 2, 4)
hourly_data = [df_horario[df_horario['hora'] == h]['kWh_hora'].values for h in range(24)]
hourly_data_arrays = [extract_values_float(h) for h in hourly_data]
bp = ax4.boxplot(hourly_data_arrays, labels=[str(h) for h in range(24)], patch_artist=True)
for patch in bp['boxes']:
    patch.set_facecolor('lightblue')
ax4.set_xlabel('Hora del Día (24h)', fontweight='bold')
ax4.set_ylabel('Demanda (kWh/h)', fontweight='bold')
ax4.set_title('Distribución de Demanda por Hora', fontweight='bold')
ax4.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
output_png = Path('outputs/mall_demand_enero_horario_por_dia.png')
output_png.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(output_png, dpi=150, bbox_inches='tight')
print(f'\n✓ Gráficos guardados: {output_png}')

# ============================================================================
# 7. EXPORTAR DATOS COMPLETOS
# ============================================================================
print('\n' + '-'*100)
print('[EXPORTAR DATOS]')
print('-'*100)

export_df = df_horario.copy()
export_df = export_df.sort_values(['día', 'hora']).reset_index(drop=True)
export_df.columns = ['día_mes', 'hora', 'día_semana', 'demanda_kwh_hora']

export_path = Path('outputs/mall_demand_enero_horario_por_dia.csv')
export_df.to_csv(export_path, index=False)
print(f'\n✓ Datos exportados: {export_path}')
print(f'  Registros: {len(export_df):,} (31 días × 24 horas)')

# ============================================================================
# 8. RESUMEN FINAL
# ============================================================================
print('\n' + '='*100)
print('[RESUMEN FINAL]')
print('='*100)

total_enero_kwh = df_horario['kWh_hora'].sum()
promedio_hora = df_horario['kWh_hora'].mean()
dia_max = daily_totals.idxmax()
dia_min = daily_totals.idxmin()
hora_max = df_horario.loc[df_horario['kWh_hora'].idxmax()]
hora_min = df_horario.loc[df_horario['kWh_hora'].idxmin()]

print(f'\n📊 Demanda del Mall - ENERO 2024 (HORARIA POR DÍA)')
print(f'   Período: 1 a 31 de enero')
print(f'   Resolución: 1 hora')
print(f'   Total registros: {len(export_df):,} (31 días × 24 horas)')

print(f'\n   📈 Estadísticas Energía (kWh):')
print(f'   ├─ Total ENERO: {total_enero_kwh:,.1f} kWh')
print(f'   ├─ Promedio por hora: {promedio_hora:.1f} kWh/h')
print(f'   ├─ Hora máxima: {safe_float_convert(hora_max["kWh_hora"]):.0f} kWh/h')
print(f'   └─ Hora mínima: {safe_float_convert(hora_min["kWh_hora"]):.0f} kWh/h')

print(f'\n   📍 Extremos:')
print(f'   ├─ Día más demandante: {int(dia_max)}/01 ({daily_stats.loc[daily_stats["día"]==dia_max, "dia_semana"].values[0]}) → {daily_totals[dia_max]:.1f} kWh')
print(f'   ├─ Día menos demandante: {int(dia_min)}/01 ({daily_stats.loc[daily_stats["día"]==dia_min, "dia_semana"].values[0]}) → {daily_totals[dia_min]:.1f} kWh')
print(f'   ├─ Hora pico máxima: {safe_int_convert(hora_max["día"])}/01 a las {safe_int_convert(hora_max["hora"]):02d}:00 → {safe_float_convert(hora_max["kWh_hora"]):.1f} kWh')
print(f'   └─ Hora valle mínima: {safe_int_convert(hora_min["día"])}/01 a las {safe_int_convert(hora_min["hora"]):02d}:00 → {safe_float_convert(hora_min["kWh_hora"]):.1f} kWh')

print(f'\n   ⏰ Horas de mayor demanda (promedio):')
for idx, (hora, kWh) in enumerate(hourly_agg['Promedio'].nlargest(5).items(), 1):
    print(f'   {idx}. {safe_int_convert(hora):02d}:00 → {safe_float_convert(kWh):.1f} kWh/h')

print(f'\n📁 Archivos generados:')
print(f'   ✓ {output_png} (heatmap + 3 gráficos)')
print(f'   ✓ {export_path} (datos horarios completos)')

print('\n' + '='*100)
