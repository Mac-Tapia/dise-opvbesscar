"""
Reporte de Demanda Horaria - 1 Día de Enero (1/01)
Muestra la demanda real del mall para cada una de las 24 horas del día 1 de enero
Resolución: Horaria (1 hora por intervalo)
"""

from __future__ import annotations

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from _pandas_dt_helpers import extract_year, extract_month, extract_day, extract_hour, extract_minute, extract_dayofweek, extract_day_name, safe_int_convert, safe_float_convert

# ════════════════════════════════════════════════════════════════════════════════════════
# 1. CARGAR DATOS
# ════════════════════════════════════════════════════════════════════════════════════════

# Ruta del archivo
data_file = Path("data/interim/oe2/demandamallkwh/demandamallkwh.csv")

# Cargar datos con separador semicolon
df = pd.read_csv(data_file, sep=';')

# Renombrar columnas
df.columns = ['fechahora', 'kWh']

# Convertir a datetime
df['fechahora'] = pd.to_datetime(df['fechahora'], format='%d/%m/%Y %H:%M')

# Convertir kW a kWh (multiplicar por 0.25 porque cada intervalo es 15 minutos = 0.25 horas)
df['kWh'] = df['kWh'] * 0.25

# Extraer componentes de fecha - Usar métodos seguros de pandas
df['año'] = extract_year(df['fechahora'])
df['mes'] = extract_month(df['fechahora'])
df['día'] = extract_day(df['fechahora'])
df['hora'] = extract_hour(df['fechahora'])
df['minuto'] = extract_minute(df['fechahora'])
df['día_semana_num'] = extract_dayofweek(df['fechahora'])
df['día_semana'] = extract_day_name(df['fechahora'])

# Filtrar enero 2024
df_enero = df[(df['año'] == 2024) & (df['mes'] == 1)].copy()

# Filtrar solo el día 1 de enero
df_dia1 = df_enero[df_enero['día'] == 1].copy()

# Agregar por hora
df_horario_dia1 = df_dia1.groupby(['día', 'hora', 'día_semana']).agg({
    'kWh': 'sum'
}).reset_index()
df_horario_dia1 = df_horario_dia1.rename(columns={'kWh': 'kWh_hora'})

print("════════════════════════════════════════════════════════════════════════════════════════")
print("════            [REPORTE 1 DÍA ENERO - DEMANDA HORARIA]")
print("════════════════════════════════════════════════════════════════════════════════════════")
print("")

# Validar datos
if len(df_dia1) == 0:
    print("❌ ERROR: No se encontraron datos para 1/01")
    exit(1)

if len(df_horario_dia1) != 24:
    print(f"⚠️  WARNING: Se esperaban 24 horas, se encontraron {len(df_horario_dia1)}")

print(f"✓ Datos cargados: {len(df_dia1)} registros (15-minuto)")
print(f"✓ Datos agregados: {len(df_horario_dia1)} registros (HORARIO)")
print(f"  Período: 1 de enero 2024 ({df_horario_dia1['día_semana'].iloc[0]})")
print(f"  Unidad: kWh por HORA")
print("")

# ════════════════════════════════════════════════════════════════════════════════════════
# 2. ESTADÍSTICAS
# ════════════════════════════════════════════════════════════════════════════════════════

print("────────────────────────────────────────────────────────────────────────────────────────")
print("────        [ESTADÍSTICAS GLOBALES - 1/01 ENERO]")
print("────────────────────────────────────────────────────────────────────────────────────────")
print("")

total_energia = df_horario_dia1['kWh_hora'].sum()
promedio_hora = df_horario_dia1['kWh_hora'].mean()
min_hora = df_horario_dia1['kWh_hora'].min()
max_hora = df_horario_dia1['kWh_hora'].max()
std_hora = df_horario_dia1['kWh_hora'].std()

print(f"📊 DEMANDA POR ENERGÍA (kWh):")
print(f"├─ Energía promedio por hora: {promedio_hora:.2f} kWh/h")
print(f"├─ Energía mínima: {min_hora:.2f} kWh/h")
print(f"├─ Energía máxima: {max_hora:.2f} kWh/h")
print(f"├─ Desv.Std: {std_hora:.2f} kWh/h")
print(f"└─ Energía acumulada 1/01: {total_energia:.1f} kWh")
print("")

# ════════════════════════════════════════════════════════════════════════════════════════
# 3. TABLA DETALLADA - TODAS LAS HORAS DEL DÍA 1
# ════════════════════════════════════════════════════════════════════════════════════════

print("────────────────────────────────────────────────────────────────────────────────────────")
print("────        [TABLA HORARIA - 1 DE ENERO 2024]")
print("────────────────────────────────────────────────────────────────────────────────────────")
print("")

# Crear tabla con formato bonito
tabla_display = df_horario_dia1[['hora', 'kWh_hora']].copy()
tabla_display.columns = ['Hora', 'kWh/hora']
tabla_display['Hora'] = tabla_display['Hora'].apply(lambda x: f"{int(x):02d}:00")

print("┌────────┬──────────────┐")
print("│  Hora  │  Demanda kWh │")
print("├────────┼──────────────┤")
for idx, row in tabla_display.iterrows():
    print(f"│ {row['Hora']:6s} │   {row['kWh/hora']:8.2f}   │")
print("└────────┴──────────────┘")
print("")

# ════════════════════════════════════════════════════════════════════════════════════════
# 4. ANÁLISIS COMPLEMENTARIO
# ════════════════════════════════════════════════════════════════════════════════════════

print("────────────────────────────────────────────────────────────────────────────────────────")
print("────        [ANÁLISIS DE HORARIOS]")
print("────────────────────────────────────────────────────────────────────────────────────────")
print("")

# Períodos del día
horas_madrugada = df_horario_dia1[df_horario_dia1['hora'] < 6]['kWh_hora']
horas_manana = df_horario_dia1[(df_horario_dia1['hora'] >= 6) & (df_horario_dia1['hora'] < 12)]['kWh_hora']
horas_tarde = df_horario_dia1[(df_horario_dia1['hora'] >= 12) & (df_horario_dia1['hora'] < 18)]['kWh_hora']
horas_noche = df_horario_dia1[(df_horario_dia1['hora'] >= 18) & (df_horario_dia1['hora'] < 24)]['kWh_hora']

print(f"🌙 MADRUGADA (0-5h):   {horas_madrugada.sum():8.1f} kWh  |  Promedio: {horas_madrugada.mean():7.2f} kWh/h")
print(f"🌅 MAÑANA (6-11h):     {horas_manana.sum():8.1f} kWh  |  Promedio: {horas_manana.mean():7.2f} kWh/h")
print(f"☀️  TARDE (12-17h):     {horas_tarde.sum():8.1f} kWh  |  Promedio: {horas_tarde.mean():7.2f} kWh/h")
print(f"🌙 NOCHE (18-23h):     {horas_noche.sum():8.1f} kWh  |  Promedio: {horas_noche.mean():7.2f} kWh/h")
print("")

# Hora pico y hora valle
hora_pico = df_horario_dia1.loc[df_horario_dia1['kWh_hora'].idxmax()]
hora_valle = df_horario_dia1.loc[df_horario_dia1['kWh_hora'].idxmin()]

print(f"📈 Hora PICO:  {safe_int_convert(hora_pico['hora']):02d}:00  →  {safe_float_convert(hora_pico['kWh_hora']):.2f} kWh/h")
print(f"📉 Hora VALLE: {safe_int_convert(hora_valle['hora']):02d}:00  →  {safe_float_convert(hora_valle['kWh_hora']):.2f} kWh/h")
print("")

# ════════════════════════════════════════════════════════════════════════════════════════
# 5. GENERAR GRÁFICOS
# ════════════════════════════════════════════════════════════════════════════════════════

print("────────────────────────────────────────────────────────────────────────────────────────")
print("────        [GENERANDO GRÁFICOS]")
print("────────────────────────────────────────────────────────────────────────────────────────")
print("")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Demanda del Mall - 1 DE ENERO 2024 (Resolución Horaria)', fontsize=16, fontweight='bold')

# Gráfico 1: Línea de demanda por hora
ax1 = axes[0, 0]
horas = df_horario_dia1['hora'].astype(int)
demanda = df_horario_dia1['kWh_hora']
ax1.plot(horas, demanda, marker='o', linewidth=2.5, markersize=8, color='steelblue', label='Demanda')
ax1.fill_between(horas, demanda, alpha=0.3, color='steelblue')
ax1.set_xlabel('Hora del día', fontweight='bold')
ax1.set_ylabel('Demanda (kWh/h)', fontweight='bold')
ax1.set_title('Perfil de Demanda Horaria - 1/01', fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.set_xticks(range(0, 24, 2))
ax1.set_xticklabels([str(i) for i in range(0, 24, 2)])
ax1.set_xlim(-0.5, 23.5)
ax1.axhline(y=promedio_hora, color='red', linestyle='--', linewidth=1.5, label=f'Promedio: {promedio_hora:.1f} kWh/h')
ax1.legend()

# Gráfico 2: Barras de demanda por hora
ax2 = axes[0, 1]
colors = ['red' if d > promedio_hora else 'steelblue' for d in demanda]
bars = ax2.bar(horas, demanda, color=colors, alpha=0.7, edgecolor='black', linewidth=0.5)
ax2.axhline(y=promedio_hora, color='green', linestyle='--', linewidth=2, label=f'Promedio: {promedio_hora:.1f} kWh/h')
ax2.set_xlabel('Hora del día', fontweight='bold')
ax2.set_ylabel('Demanda (kWh/h)', fontweight='bold')
ax2.set_title('Demanda por Hora - 1/01 (Barras)', fontweight='bold')
ax2.set_xticks(range(0, 24, 2))
ax2.set_xlim(-0.5, 23.5)
ax2.grid(True, alpha=0.3, axis='y')
ax2.legend()

# Gráfico 3: Distribución por período
ax3 = axes[1, 0]
periodos = ['Madrugada\n(0-5h)', 'Mañana\n(6-11h)', 'Tarde\n(12-17h)', 'Noche\n(18-23h)']
energias_periodo = [
    horas_madrugada.sum(),
    horas_manana.sum(),
    horas_tarde.sum(),
    horas_noche.sum()
]
colores_periodo = ['darkblue', 'orange', 'red', 'purple']
bars3 = ax3.bar(periodos, energias_periodo, color=colores_periodo, alpha=0.7, edgecolor='black', linewidth=1)
ax3.set_ylabel('Energía Total (kWh)', fontweight='bold')
ax3.set_title('Energía por Período del Día - 1/01', fontweight='bold')
ax3.grid(True, alpha=0.3, axis='y')
# Agregar valores sobre barras
for bar, energia in zip(bars3, energias_periodo):
    height = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2., height,
             f'{energia:.0f}\nkWh',
             ha='center', va='bottom', fontweight='bold')

# Gráfico 4: Estadísticas circulares
ax4 = axes[1, 1]
ax4.axis('off')
# Texto de resumen
resumen_text = f"""
RESUMEN - 1 DE ENERO 2024

📊 Energía Total: {total_energia:.1f} kWh

⏰ Horario de Operación:
  • Apertura: {safe_int_convert(hora_pico['hora']):02d}:00 (max demand)
  • Cierre: {safe_int_convert(hora_valle['hora']):02d}:00 (min demand)

📈 Estadísticas:
  • Promedio: {promedio_hora:.2f} kWh/h
  • Máximo: {max_hora:.2f} kWh/h
  • Mínimo: {min_hora:.2f} kWh/h
  • Variación: {std_hora:.2f} kWh/h

⚡ Demanda por Período:
  • Madrugada: {horas_madrugada.sum():.1f} kWh ({100*horas_madrugada.sum()/total_energia:.1f}%)
  • Mañana: {horas_manana.sum():.1f} kWh ({100*horas_manana.sum()/total_energia:.1f}%)
  • Tarde: {horas_tarde.sum():.1f} kWh ({100*horas_tarde.sum()/total_energia:.1f}%)
  • Noche: {horas_noche.sum():.1f} kWh ({100*horas_noche.sum()/total_energia:.1f}%)
"""
ax4.text(0.1, 0.95, resumen_text, transform=ax4.transAxes,
         fontsize=11, verticalalignment='top', fontfamily='monospace',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
plt.savefig('outputs/mall_demand_enero_1dia_horario.png', dpi=150, bbox_inches='tight')
print(f"✓ Gráficos guardados: outputs\\mall_demand_enero_1dia_horario.png")
print("")

# ════════════════════════════════════════════════════════════════════════════════════════
# 6. EXPORTAR DATOS A CSV
# ════════════════════════════════════════════════════════════════════════════════════════

print("────────────────────────────────────────────────────────────────────────────────────────")
print("────        [EXPORTAR DATOS]")
print("────────────────────────────────────────────────────────────────────────────────────────")
print("")

# Preparar datos para exportar
export_df = df_horario_dia1[['día', 'hora', 'día_semana', 'kWh_hora']].copy()
export_df.columns = ['día_mes', 'hora', 'día_semana', 'demanda_kwh_hora']
export_df = export_df.sort_values('hora').reset_index(drop=True)

# Exportar CSV
csv_path = Path('outputs/mall_demand_enero_1dia_horario.csv')
csv_path.parent.mkdir(parents=True, exist_ok=True)
export_df.to_csv(csv_path, index=False)

print(f"✓ Datos exportados: outputs\\mall_demand_enero_1dia_horario.csv")
print(f"  Registros: {len(export_df)} (24 horas)")
print("")

# ════════════════════════════════════════════════════════════════════════════════════════
# 7. RESUMEN FINAL
# ════════════════════════════════════════════════════════════════════════════════════════

print("════════════════════════════════════════════════════════════════════════════════════════")
print("════            [RESUMEN FINAL]")
print("════════════════════════════════════════════════════════════════════════════════════════")
print("")
print(f"📊 Demanda del Mall - 1 DE ENERO 2024 (HORARIA)")
print(f"   Período: 1 de enero (Monday - Feriado)")
print(f"   Resolución: 1 hora")
print(f"   Total registros: 24 (24 horas del día)")
print("")
print(f"   📈 Estadísticas Energía (kWh):")
print(f"   ├─ Total 1/01: {total_energia:.1f} kWh")
print(f"   ├─ Promedio por hora: {promedio_hora:.2f} kWh/h")
print(f"   ├─ Máximo: {max_hora:.2f} kWh/h")
print(f"   └─ Mínimo: {min_hora:.2f} kWh/h")
print("")
print(f"   ⏰ Extremos:")
print(f"   ├─ Hora pico: {safe_int_convert(hora_pico['hora']):02d}:00 → {safe_float_convert(hora_pico['kWh_hora']):.2f} kWh/h")
print(f"   └─ Hora valle: {safe_int_convert(hora_valle['hora']):02d}:00 → {safe_float_convert(hora_valle['kWh_hora']):.2f} kWh/h")
print("")
print(f"📁 Archivos generados:")
print(f"   ✓ outputs\\mall_demand_enero_1dia_horario.png (4 gráficos)")
print(f"   ✓ outputs\\mall_demand_enero_1dia_horario.csv (24 registros)")
print("")
print("════════════════════════════════════════════════════════════════════════════════════════")
