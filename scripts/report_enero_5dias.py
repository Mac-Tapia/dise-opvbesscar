"""
REPORTE: Primeros 5 días de Enero - Demanda del Mall cada 15 minutos
Datos reales OE2 sin procesamiento
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
print('[REPORTE 5 PRIMEROS DÍAS DE ENERO - DEMANDA 15-MINUTO]')
print('='*90)

data_path = Path('data/interim/oe2/demandamallkwh/demandamallkwh.csv')
df = pd.read_csv(data_path, sep=';')
df['FECHAHORA'] = pd.to_datetime(df['FECHAHORA'], format='%d/%m/%Y %H:%M')
df = df.sort_values('FECHAHORA').reset_index(drop=True)

# Filtrar a los primeros 5 días de enero
enero_start = pd.to_datetime('2024-01-01')
enero_end = pd.to_datetime('2024-01-05 23:59:59')
df_enero = df[(df['FECHAHORA'] >= enero_start) & (df['FECHAHORA'] <= enero_end)].copy()

print(f'\n✓ Datos cargados: {len(df_enero):,} registros (5 días de enero)')
print(f'  Período: {df_enero["FECHAHORA"].min()} a {df_enero["FECHAHORA"].max()}')
print(f'  Registros esperados: {5 * 24 * 4} (5 días × 24 horas × 4 intervalos de 15-min)')

# ============================================================================
# 2. TABLA DETALLADA (primeros 5 días)
# ============================================================================
print('\n' + '-'*90)
print('[TABLA DETALLADA - PRIMEROS 5 DÍAS DE ENERO (cada 15 minutos)]')
print('-'*90)

# Agregar columnas de análisis
df_enero['hora'] = extract_hour(df_enero['FECHAHORA'])
df_enero['minuto'] = extract_minute(df_enero['FECHAHORA'])
df_enero['fecha'] = extract_date(df_enero['FECHAHORA'])
df_enero['dia_semana'] = extract_day_name(df_enero['FECHAHORA'])
df_enero['día'] = extract_day(df_enero['FECHAHORA'])

# Mostrar tabla completa
display_df = df_enero[['FECHAHORA', 'dia_semana', 'hora', 'minuto', 'kWh']].copy()
display_df['kWh'] = display_df['kWh'].astype(int)
display_df = display_df.rename(columns={
    'FECHAHORA': 'Fecha/Hora',
    'dia_semana': 'Día Semana',
    'hora': 'H',
    'minuto': 'M',
    'kWh': 'Demanda (kW)'
})

# Mostrar en bloques por día
for día in range(1, 6):
    dia_data = df_enero[df_enero['día'] == día]
    if len(dia_data) > 0:
        fecha_str = dia_data['FECHAHORA'].iloc[0].strftime('%A, %d de enero de 2024')
        print('\n' + '='*90)
        print(f'  DÍA {día}: {fecha_str}  ({len(dia_data):,} registros)')
        print('='*90)

        # Crear tabla para este día
        día_display = display_df[display_df['H'].isin(dia_data['hora'].values)].copy()

        # Agrupar por hora para mejor visualización
        for hora in range(0, 24):
            hora_data = dia_data[dia_data['hora'] == hora]
            if len(hora_data) > 0:
                print(f"\n  {hora:02d}:00 - {hora:02d}:45")
                print('  ' + '-'*82)
                for idx, row in hora_data.iterrows():
                    print(f"    {row['FECHAHORA'].strftime('%H:%M'):5s} │ {row['kWh']:6.0f} kW")

# ============================================================================
# 3. ESTADÍSTICAS POR DÍA
# ============================================================================
print('\n' + '='*90)
print('[ESTADÍSTICAS POR DÍA]')
print('='*90)

daily_stats = df_enero.groupby('día').agg({
    'kWh': ['count', 'mean', 'min', 'max', 'sum']
}).round(1)

print('\n┌─────────┬──────────┬──────────────┬──────────┬──────────┬──────────────┐')
print('│   Día   │ Registros│  Promedio    │  Mínimo  │  Máximo  │ Acumulado    │')
print('│         │ (15-min) │   (kW)       │   (kW)   │   (kW)   │  (kWh)       │')
print('├─────────┼──────────┼──────────────┼──────────┼──────────┼──────────────┤')
for día in range(1, 6):
    dia_data = df_enero[df_enero['día'] == día]
    if len(dia_data) > 0:
        n_regs = len(dia_data)
        mean = dia_data['kWh'].mean()
        min_val = dia_data['kWh'].min()
        max_val = dia_data['kWh'].max()
        acum = dia_data['kWh'].sum() * 0.25  # 15-min = 0.25 horas
        fecha_str = dia_data['FECHAHORA'].iloc[0].strftime('%a')
        print(f'│ 1/{día:02d} ({fecha_str}) │  {n_regs:5d}   │  {mean:8.1f}    │  {min_val:7.1f} │  {max_val:7.1f} │ {acum:11.1f} │')
print('└─────────┴──────────┴──────────────┴──────────┴──────────┴──────────────┘')

# ============================================================================
# 4. ANÁLISIS HORARIO (promedio de los 5 días)
# ============================================================================
print('\n' + '-'*90)
print('[ANÁLISIS HORARIO - Promedio de los 5 días de enero]')
print('-'*90)

hourly_stats = df_enero.groupby('hora')['kWh'].agg(['mean', 'min', 'max', 'std']).round(1)

print('\n┌─────────┬─────────────┬─────────┬─────────┬─────────────┐')
print('│  Hora   │   Promedio  │  Mínimo │  Máximo │  Desv.Std   │')
print('│ (24h)   │    (kW)     │  (kW)   │  (kW)   │    (kW)     │')
print('├─────────┼─────────────┼─────────┼─────────┼─────────────┤')
for hora in range(24):
    if hora in hourly_stats.index:
        mean = hourly_stats.loc[hora, 'mean']
        min_val = hourly_stats.loc[hora, 'min']
        max_val = hourly_stats.loc[hora, 'max']
        std = hourly_stats.loc[hora, 'std']
        print(f'│ {hora:02d}:00  │  {mean:9.1f}  │ {min_val:6.1f} │ {max_val:6.1f} │  {std:8.1f}   │')
print('└─────────┴─────────────┴─────────┴─────────┴─────────────┘')

# ============================================================================
# 5. GRÁFICOS
# ============================================================================
print('\n' + '-'*90)
print('[GENERANDO GRÁFICOS]')
print('-'*90)

fig, axes = plt.subplots(2, 1, figsize=(16, 10))
fig.suptitle('Demanda del Mall - Primeros 5 días de Enero 2024 (cada 15 minutos)',
             fontsize=14, fontweight='bold')

# Gráfico 1: Serie temporal completa (5 días)
ax1 = axes[0]
ax1.plot(df_enero['FECHAHORA'], df_enero['kWh'], linewidth=1.5, color='steelblue', label='Demanda real')
ax1.fill_between(df_enero['FECHAHORA'], df_enero['kWh'], alpha=0.3, color='steelblue')

# Marcar líneas verticales para cada día
for día in range(1, 6):
    fecha_inicio = pd.to_datetime(f'2024-01-{día:02d} 00:00:00')
    ax1.axvline(fecha_inicio, color='gray', linestyle='--', alpha=0.5, linewidth=1)
    ax1.text(fecha_inicio, ax1.get_ylim()[1] * 0.95, f'  Día {día}',
            fontsize=9, ha='left', va='top', rotation=0, color='gray')

ax1.set_title('Serie temporal - Demanda cada 15 minutos', fontweight='bold', fontsize=12)
ax1.set_xlabel('Fecha/Hora', fontsize=11)
ax1.set_ylabel('Demanda (kW)', fontsize=11)
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper right')

# Gráfico 2: Promedio por hora del día (superpuesto para 5 días)
ax2 = axes[1]
colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
for día in range(1, 6):
    dia_data = df_enero[df_enero['día'] == día]
    if len(dia_data) > 0:
        hourly_avg = dia_data.groupby('hora')['kWh'].mean()
        ax2.plot(hourly_avg.index, hourly_avg.values,
                marker='o', linewidth=2, label=f'Día {día}',
                color=colors[día-1], markersize=5)

ax2.set_title('Perfil de demanda horaria - Comparativa de los 5 días', fontweight='bold', fontsize=12)
ax2.set_xlabel('Hora del día (0-23)', fontsize=11)
ax2.set_ylabel('Demanda promedio (kW)', fontsize=11)
ax2.set_xticks(range(0, 24, 2))
ax2.set_xlim(-1, 24)
ax2.grid(True, alpha=0.3)
ax2.legend(loc='best', ncol=2)

plt.tight_layout()
output_path = Path('outputs/mall_demand_enero_5dias_15min.png')
output_path.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f'\n✓ Gráficos guardados: {output_path}')
plt.close()

# ============================================================================
# 6. EXPORTAR CSV
# ============================================================================
print('\n' + '-'*90)
print('[EXPORTAR DATOS]')
print('-'*90)

export_df = df_enero[['FECHAHORA', 'dia_semana', 'hora', 'minuto', 'kWh']].copy()
export_df.columns = ['fecha_hora', 'día_semana', 'hora', 'minuto', 'demanda_kw']
export_df = export_df.reset_index(drop=True)

export_path = Path('outputs/mall_demand_enero_5dias_15min.csv')
export_df.to_csv(export_path, index=False)
print(f'\n✓ Datos exportados: {export_path}')
print(f'  Registros: {len(export_df):,}')

# ============================================================================
# 7. RESUMEN FINAL
# ============================================================================
print('\n' + '='*90)
print('[RESUMEN FINAL]')
print('='*90)

total_kwh = df_enero['kWh'].sum() * 0.25  # 15-min = 0.25 horas
mean_kw = df_enero['kWh'].mean()
min_kw = df_enero['kWh'].min()
max_kw = df_enero['kWh'].max()

print(f'\n📊 Demanda del Mall - 5 Primeros Días de Enero 2024')
print(f'   Período: {df_enero["FECHAHORA"].min().date()} a {df_enero["FECHAHORA"].max().date()}')
print(f'   Registros: {len(df_enero):,} (resolución 15-minuto)')
print(f'\n   Estadísticas:')
print(f'   ├─ Demanda promedio: {mean_kw:.1f} kW')
print(f'   ├─ Demanda mínima: {min_kw:.1f} kW')
print(f'   ├─ Demanda máxima: {max_kw:.1f} kW')
print(f'   └─ Demanda acumulada: {total_kwh:,.1f} kWh')
print(f'\n📁 Archivos generados:')
print(f'   ✓ outputs/mall_demand_enero_5dias_15min.png (gráficos)')
print(f'   ✓ outputs/mall_demand_enero_5dias_15min.csv (datos completos)')
print('\n' + '='*90 + '\n')
