"""
REPORTE: Demanda del Mall OE2 - Resolución 15-minuto
Sin procesamiento para CityLearn, solo análisis de datos reales.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from _pandas_dt_helpers import extract_hour, extract_day_name, extract_month, extract_day, extract_date

# ============================================================================
# 1. CARGAR DATOS 15-MINUTO
# ============================================================================
print('\n' + '='*80)
print('[REPORTE DEMANDA 15-MINUTO] Análisis de datos OE2 reales')
print('='*80)

data_path = Path('data/interim/oe2/demandamallkwh/demandamallkwh.csv')
df = pd.read_csv(data_path, sep=';')
df['FECHAHORA'] = pd.to_datetime(df['FECHAHORA'], format='%d/%m/%Y %H:%M')
df = df.sort_values('FECHAHORA').reset_index(drop=True)

print(f'\n✓ Datos cargados: {len(df):,} registros 15-minuto')
print(f'  Rango: {df["FECHAHORA"].min().date()} a {df["FECHAHORA"].max().date()}')

# ============================================================================
# 2. ESTADÍSTICAS BÁSICAS
# ============================================================================
print('\n' + '-'*80)
print('[ESTADÍSTICAS GLOBALES]')
print('-'*80)

print(f'\nDemanda instantánea (kW):')
print(f'  Media: {df["kWh"].mean():.1f} kW')
print(f'  Mediana: {df["kWh"].median():.1f} kW')
print(f'  Mín: {df["kWh"].min():.1f} kW')
print(f'  Máx: {df["kWh"].max():.1f} kW')
print(f'  Std: {df["kWh"].std():.1f} kW')

print(f'\nDemanda acumulada:')
print(f'  Total (anual): {df["kWh"].sum() * 0.25 / 1000:.2f} MWh')
print(f'  Total (anual): {df["kWh"].sum() * 0.25:,.0f} kWh')

# ============================================================================
# 3. ANÁLISIS HORARIO
# ============================================================================
print('\n' + '-'*80)
print('[ANÁLISIS POR HORA DEL DÍA]')
print('-'*80)

df['hora'] = extract_hour(df['FECHAHORA'])
df['dia_semana'] = extract_day_name(df['FECHAHORA'])
df['mes'] = extract_month(df['FECHAHORA'])
df['dia_mes'] = extract_day(df['FECHAHORA'])

hourly_stats = df.groupby('hora')['kWh'].agg(['mean', 'min', 'max', 'std']).round(1)
print('\nDemanda promedio por hora:')
print(hourly_stats)

# ============================================================================
# 4. ANÁLISIS POR DÍA DE LA SEMANA
# ============================================================================
print('\n' + '-'*80)
print('[ANÁLISIS POR DÍA DE LA SEMANA]')
print('-'*80)

df['fecha'] = extract_date(df['FECHAHORA'])
daily_stats = df.groupby('dia_semana')['kWh'].agg(['mean', 'min', 'max']).round(1)
print('\nDemanda promedio por día de semana:')
print(daily_stats)

# ============================================================================
# 5. DETECTAR PICOS
# ============================================================================
print('\n' + '-'*80)
print('[PICOS DE DEMANDA]')
print('-'*80)

threshold = df['kWh'].quantile(0.95)
picos = df[df['kWh'] >= threshold].sort_values('kWh', ascending=False).head(10)

print(f'\nTop 10 demandas máximas (≥ {threshold:.0f} kW):')
for idx, row in picos.iterrows():
    print(f'  {row["FECHAHORA"]}: {row["kWh"]:.0f} kW ({row["dia_semana"]} {row["FECHAHORA"].strftime("%H:%M")})')

# ============================================================================
# 6. GRÁFICOS
# ============================================================================
print('\n' + '-'*80)
print('[GENERANDO GRÁFICOS]')
print('-'*80)

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Demanda del Mall OE2 - Análisis 15-minuto', fontsize=14, fontweight='bold')

# Gráfico 1: Serie temporal completa (primeros 7 días)
ax1 = axes[0, 0]
first_week = df[df['FECHAHORA'] < '2024-01-08']
ax1.plot(first_week['FECHAHORA'], first_week['kWh'], linewidth=1.5, color='steelblue')
ax1.fill_between(first_week['FECHAHORA'], first_week['kWh'], alpha=0.3, color='steelblue')
ax1.set_title('Primera semana (7 días)', fontweight='bold')
ax1.set_xlabel('Fecha')
ax1.set_ylabel('Demanda (kW)')
ax1.grid(True, alpha=0.3)
ax1.tick_params(axis='x', rotation=45)

# Gráfico 2: Promedio horario
ax2 = axes[0, 1]
hourly_mean = df.groupby('hora')['kWh'].mean()
ax2.bar(hourly_mean.index, hourly_mean.values, color='coral', alpha=0.7, edgecolor='black')
ax2.set_title('Demanda promedio por hora del día', fontweight='bold')
ax2.set_xlabel('Hora del día')
ax2.set_ylabel('Demanda promedio (kW)')
ax2.set_xticks(range(0, 24, 2))
ax2.grid(True, alpha=0.3, axis='y')

# Gráfico 3: Caja por día de semana
ax3 = axes[1, 0]
days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
df_reordered = df.copy()
df_reordered['dia_semana'] = pd.Categorical(df_reordered['dia_semana'], categories=days_order, ordered=True)
df_reordered_sorted = df_reordered.sort_values('dia_semana')
ax3.boxplot([df[df['dia_semana'] == day]['kWh'].values for day in days_order],
            labels=['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sab', 'Dom'])
ax3.set_title('Distribución de demanda por día de semana', fontweight='bold')
ax3.set_ylabel('Demanda (kW)')
ax3.grid(True, alpha=0.3, axis='y')

# Gráfico 4: Distribución estadística
ax4 = axes[1, 1]
ax4.hist(df['kWh'], bins=50, color='green', alpha=0.7, edgecolor='black')
ax4.axvline(df['kWh'].mean(), color='red', linestyle='--', linewidth=2, label=f'Media: {df["kWh"].mean():.0f} kW')
ax4.axvline(df['kWh'].median(), color='orange', linestyle='--', linewidth=2, label=f'Mediana: {df["kWh"].median():.0f} kW')
ax4.set_title('Histograma de demanda', fontweight='bold')
ax4.set_xlabel('Demanda (kW)')
ax4.set_ylabel('Frecuencia')
ax4.legend()
ax4.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
output_path = Path('outputs/mall_demand_15min_report.png')
output_path.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f'\n✓ Gráficos guardados: {output_path}')
plt.close()

# ============================================================================
# 7. EXPORTAR REPORTE CSV
# ============================================================================
print('\n' + '-'*80)
print('[EXPORTAR REPORTES]')
print('-'*80)

# Reporte horario
hourly_report = df.groupby('hora')['kWh'].agg(['count', 'mean', 'min', 'max', 'std']).reset_index()
hourly_report.columns = ['hora', 'n_registros', 'demanda_promedio_kW', 'demanda_min_kW', 'demanda_max_kW', 'desv_std_kW']
hourly_report_path = Path('outputs/mall_demand_15min_hourly_stats.csv')
hourly_report.to_csv(hourly_report_path, index=False)
print(f'\n✓ Estadísticas horarias: {hourly_report_path}')

# Reporte diario
daily_report = df.groupby('fecha').agg({
    'kWh': ['count', 'mean', 'min', 'max', 'sum']
}).reset_index()
daily_report.columns = ['fecha', 'n_registros', 'demanda_promedio_kW', 'demanda_min_kW', 'demanda_max_kW', 'demanda_total_kWh']
daily_report['demanda_total_kWh'] = daily_report['demanda_total_kWh'] * 0.25  # 15-min = 0.25 horas
daily_report['dia_semana'] = pd.to_datetime(daily_report['fecha']).dt.day_name().astype(str)
daily_report_path = Path('outputs/mall_demand_15min_daily_stats.csv')
daily_report.to_csv(daily_report_path, index=False)
print(f'✓ Estadísticas diarias: {daily_report_path}')

# Resumen ejecutivo
summary = {
    'periodo': f'{df["FECHAHORA"].min().date()} a {df["FECHAHORA"].max().date()}',
    'n_registros': len(df),
    'n_registros_diarios': len(df) / ((df["FECHAHORA"].max() - df["FECHAHORA"].min()).days + 1),
    'resolucion': '15 minutos',
    'demanda_media_kW': round(df['kWh'].mean(), 1),
    'demanda_min_kW': round(df['kWh'].min(), 1),
    'demanda_max_kW': round(df['kWh'].max(), 1),
    'demanda_anual_kwh': round(df['kWh'].sum() * 0.25, 0),
}
summary_df = pd.DataFrame([summary])
summary_path = Path('outputs/mall_demand_15min_summary.csv')
summary_df.to_csv(summary_path, index=False)
print(f'✓ Resumen ejecutivo: {summary_path}')

# ============================================================================
# 8. REPORTE FINAL
# ============================================================================
print('\n' + '='*80)
print('[RESUMEN FINAL]')
print('='*80)
print(f'\n📊 Demanda del Mall OE2 (Datos Reales 15-minuto)')
print(f'   Período: {df["FECHAHORA"].min().date()} a {df["FECHAHORA"].max().date()}')
print(f'   Registros: {len(df):,} (resolución 15-minuto)')
print(f'   Demanda promedio: {df["kWh"].mean():.0f} kW')
print(f'   Demanda anual: {df["kWh"].sum() * 0.25:,.0f} kWh ({df["kWh"].sum() * 0.25 / 1000:.1f} MWh)')
print(f'\n📁 Archivos generados:')
print(f'   ✓ outputs/mall_demand_15min_report.png (gráficos)')
print(f'   ✓ outputs/mall_demand_15min_hourly_stats.csv (por hora)')
print(f'   ✓ outputs/mall_demand_15min_daily_stats.csv (por día)')
print(f'   ✓ outputs/mall_demand_15min_summary.csv (resumen)')
print('\n' + '='*80 + '\n')
