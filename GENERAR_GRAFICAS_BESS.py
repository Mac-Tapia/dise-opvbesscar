"""
Generador de gráficas para análisis del BESS y perfil de carga
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
from datetime import datetime, timedelta
import json

# Configurar estilo de gráficas
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 10

# Crear carpeta para gráficas
output_dir = Path("data/oe2/graficas")
output_dir.mkdir(parents=True, exist_ok=True)

# Cargar datos
df = pd.read_csv('data/oe2/perfil_horario_carga.csv')
with open('data/oe2/bess_dimensionamiento_schema.json', 'r') as f:
    schema = json.load(f)

# Parámetros BESS
capacidad_bess = schema['bess']['capacidad_nominal_kwh']
potencia_bess = schema['bess']['potencia_nominal_kw']
DoD = schema['bess']['dod']
SOC_min = schema['bess']['soc_min']

print("=" * 80)
print("GENERANDO GRÁFICAS DE ANÁLISIS BESS")
print("=" * 80)

# =============================================================================
# GRÁFICA 1: PERFIL DE DEMANDA EV (15 MINUTOS)
# =============================================================================
print("\n1. Generando gráfica de perfil de demanda EV...")

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

# Crear tiempos
tiempos = [datetime(2024, 1, 1, 0, 0) + timedelta(minutes=15*i) for i in range(96)]

# Subplot 1: Potencia
ax1.fill_between(tiempos, df['power_kw'], alpha=0.3, color='blue', label='Potencia demandada')
ax1.plot(tiempos, df['power_kw'], color='darkblue', linewidth=1.5)

# Marcar horarios clave
ax1.axvline(datetime(2024, 1, 1, 9, 0), color='green', linestyle='--', alpha=0.7, label='Apertura (9h)')
ax1.axvline(datetime(2024, 1, 1, 17, 0), color='orange', linestyle='--', alpha=0.7, label='Fin solar (17h)')
ax1.axvline(datetime(2024, 1, 1, 22, 0), color='red', linestyle='--', alpha=0.7, label='Cierre (22h)')

# Zona de déficit
ax1.axvspan(datetime(2024, 1, 1, 18, 0), datetime(2024, 1, 1, 22, 0),
            alpha=0.2, color='red', label='Zona déficit (BESS)')

ax1.set_ylabel('Potencia (kW)', fontsize=12, fontweight='bold')
ax1.set_title('PERFIL DE DEMANDA EV - RESOLUCIÓN 15 MINUTOS', fontsize=14, fontweight='bold')
ax1.legend(loc='upper left', fontsize=10)
ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

# Subplot 2: Energía acumulada
energia_acum = df['energy_kwh'].cumsum()
ax2.plot(tiempos, energia_acum, color='darkgreen', linewidth=2, label='Energía acumulada')
ax2.fill_between(tiempos, energia_acum, alpha=0.3, color='green')

# Marcar horarios clave
ax2.axvline(datetime(2024, 1, 1, 9, 0), color='green', linestyle='--', alpha=0.7)
ax2.axvline(datetime(2024, 1, 1, 17, 0), color='orange', linestyle='--', alpha=0.7)
ax2.axvline(datetime(2024, 1, 1, 22, 0), color='red', linestyle='--', alpha=0.7)

ax2.set_ylabel('Energía acumulada (kWh)', fontsize=12, fontweight='bold')
ax2.set_xlabel('Hora del día', fontsize=12, fontweight='bold')
ax2.legend(loc='upper left', fontsize=10)
ax2.grid(True, alpha=0.3)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

plt.tight_layout()
plt.savefig(output_dir / 'perfil_demanda_ev_15min.png', dpi=300, bbox_inches='tight')
print(f"   ✅ Guardada: {output_dir / 'perfil_demanda_ev_15min.png'}")

# =============================================================================
# GRÁFICA 2: SIMULACIÓN DE OPERACIÓN BESS
# =============================================================================
print("\n2. Generando gráfica de operación BESS...")

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12))

# Simular operación BESS
soc = np.ones(96) * 100  # Iniciar con 100%
potencia_bess_list = np.zeros(96)
estado_bess = ['Reposo'] * 96

# Horarios
hora_fin_solar = 17
energia_restante = capacidad_bess

for i, row in df.iterrows():
    hora = row['hour']

    if hora >= 18 and hora < 22:  # Descarga
        energia_descarga = row['energy_kwh']
        energia_restante -= energia_descarga
        soc[i] = max(SOC_min * 100, (energia_restante / capacidad_bess) * 100)
        potencia_bess_list[i] = -row['power_kw']  # Negativo = descarga
        estado_bess[i] = 'Descarga'
    elif i > 0:
        soc[i] = soc[i-1]  # Mantener SOC
        potencia_bess_list[i] = 0
        if hora >= 5 and hora < 17:
            estado_bess[i] = 'Carga (solar)'
        else:
            estado_bess[i] = 'Reposo'

# Subplot 1: Estado de carga (SOC)
ax1.plot(tiempos, soc, color='darkblue', linewidth=2.5, label='SOC BESS')
ax1.fill_between(tiempos, soc, SOC_min * 100, alpha=0.3, color='blue')

# Límites SOC
ax1.axhline(100, color='green', linestyle='--', alpha=0.7, linewidth=1.5, label='SOC máximo (100%)')
ax1.axhline(SOC_min * 100, color='red', linestyle='--', alpha=0.7, linewidth=1.5, label=f'SOC mínimo ({SOC_min*100:.0f}%)')

# Zonas operacionales
ax1.axvspan(datetime(2024, 1, 1, 5, 0), datetime(2024, 1, 1, 17, 0),
            alpha=0.15, color='yellow', label='Zona carga (solar)')
ax1.axvspan(datetime(2024, 1, 1, 18, 0), datetime(2024, 1, 1, 22, 0),
            alpha=0.15, color='red', label='Zona descarga (EV)')

ax1.set_ylabel('SOC (%)', fontsize=12, fontweight='bold')
ax1.set_title('OPERACIÓN DEL BESS - ESTADO DE CARGA (SOC)', fontsize=14, fontweight='bold')
ax1.legend(loc='best', fontsize=9)
ax1.grid(True, alpha=0.3)
ax1.set_ylim([0, 110])
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

# Subplot 2: Potencia BESS
colores_potencia = ['red' if p < 0 else 'green' if p > 0 else 'gray' for p in potencia_bess_list]
ax2.bar(tiempos, potencia_bess_list, width=0.008, color=colores_potencia, alpha=0.7)

ax2.axhline(0, color='black', linewidth=1)
ax2.set_ylabel('Potencia BESS (kW)', fontsize=12, fontweight='bold')
ax2.set_title('FLUJO DE POTENCIA DEL BESS\n(Positivo=Carga, Negativo=Descarga)', fontsize=14, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

# Subplot 3: Demanda EV vs Capacidad BESS
ax3.plot(tiempos, df['power_kw'], color='blue', linewidth=2, label='Demanda EV', marker='o', markersize=2)
ax3.axhline(potencia_bess, color='red', linestyle='--', linewidth=2, label=f'Potencia nominal BESS ({potencia_bess:.0f} kW)')

ax3.fill_between(tiempos, df['power_kw'], 0, where=(df['hour'] >= 18) & (df['hour'] < 22),
                  alpha=0.3, color='red', label='Demanda cubierta por BESS')

ax3.set_ylabel('Potencia (kW)', fontsize=12, fontweight='bold')
ax3.set_xlabel('Hora del día', fontsize=12, fontweight='bold')
ax3.set_title('DEMANDA EV vs CAPACIDAD BESS', fontsize=14, fontweight='bold')
ax3.legend(loc='upper left', fontsize=10)
ax3.grid(True, alpha=0.3)
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

plt.tight_layout()
plt.savefig(output_dir / 'operacion_bess_simulacion.png', dpi=300, bbox_inches='tight')
print(f"   ✅ Guardada: {output_dir / 'operacion_bess_simulacion.png'}")

# =============================================================================
# GRÁFICA 3: BALANCE ENERGÉTICO
# =============================================================================
print("\n3. Generando gráfica de balance energético...")

fig, ax = plt.subplots(figsize=(12, 8))

# Datos para balance
categorias = ['Demanda EV\nTotal', 'Cubierto por\nSolar (estimado)', 'Déficit\n(BESS)', 'Capacidad\nBESS']
valores = [
    schema['perfil']['energia_total_dia_kwh'],
    schema['perfil']['energia_total_dia_kwh'] - schema['deficit']['energia_total_kwh'],
    schema['deficit']['energia_total_kwh'],
    capacidad_bess
]
colores = ['blue', 'yellow', 'red', 'green']

bars = ax.bar(categorias, valores, color=colores, alpha=0.7, edgecolor='black', linewidth=2)

# Añadir valores en las barras
for bar, valor in zip(bars, valores):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{valor:,.0f} kWh',
            ha='center', va='bottom', fontsize=12, fontweight='bold')

# Añadir línea de referencia DoD
ax.axhline(capacidad_bess * DoD, color='orange', linestyle='--', linewidth=2,
           label=f'Energía utilizable ({DoD*100:.0f}% DoD = {capacidad_bess*DoD:,.0f} kWh)')

ax.set_ylabel('Energía (kWh)', fontsize=12, fontweight='bold')
ax.set_title('BALANCE ENERGÉTICO DIARIO - DEMANDA EV Y DIMENSIONAMIENTO BESS',
             fontsize=14, fontweight='bold')
ax.legend(loc='upper right', fontsize=10)
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig(output_dir / 'balance_energetico_bess.png', dpi=300, bbox_inches='tight')
print(f"   ✅ Guardada: {output_dir / 'balance_energetico_bess.png'}")

# =============================================================================
# GRÁFICA 4: DISTRIBUCIÓN HORARIA DE DEMANDA
# =============================================================================
print("\n4. Generando gráfica de distribución horaria...")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# Agrupar por hora
df_horario = df.groupby('hour').agg({
    'energy_kwh': 'sum',
    'power_kw': 'max'
}).reset_index()

# Subplot 1: Energía por hora
colores_horas = ['red' if h >= 18 else 'yellow' if h >= 5 and h < 17 else 'gray'
                 for h in df_horario['hour']]

bars1 = ax1.bar(df_horario['hour'], df_horario['energy_kwh'],
                color=colores_horas, alpha=0.7, edgecolor='black', linewidth=1.5)

ax1.set_xlabel('Hora del día', fontsize=12, fontweight='bold')
ax1.set_ylabel('Energía (kWh)', fontsize=12, fontweight='bold')
ax1.set_title('DISTRIBUCIÓN HORARIA DE ENERGÍA', fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3, axis='y')
ax1.set_xticks(range(0, 24, 2))

# Leyenda
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='gray', alpha=0.7, label='Cerrado'),
    Patch(facecolor='yellow', alpha=0.7, label='Solar disponible'),
    Patch(facecolor='red', alpha=0.7, label='Déficit (BESS)')
]
ax1.legend(handles=legend_elements, loc='upper left', fontsize=10)

# Subplot 2: Gráfica de pastel - distribución de demanda
deficit_energia = schema['deficit']['energia_total_kwh']
solar_energia = schema['perfil']['energia_total_dia_kwh'] - deficit_energia

labels = ['Cubierto por Solar\n(estimado)', 'Cubierto por BESS\n(déficit)']
sizes = [solar_energia, deficit_energia]
colors = ['#FFD700', '#FF6B6B']
explode = (0.05, 0.05)

wedges, texts, autotexts = ax2.pie(sizes, explode=explode, labels=labels, colors=colors,
                                     autopct='%1.1f%%', shadow=True, startangle=90,
                                     textprops={'fontsize': 11, 'fontweight': 'bold'})

# Añadir valores absolutos
for i, (wedge, autotext) in enumerate(zip(wedges, autotexts)):
    ang = (wedge.theta2 - wedge.theta1)/2. + wedge.theta1
    y = np.sin(np.deg2rad(ang))
    x = np.cos(np.deg2rad(ang))
    autotext.set_text(f'{sizes[i]:,.0f} kWh\n({sizes[i]/sum(sizes)*100:.1f}%)')

ax2.set_title('DISTRIBUCIÓN DE FUENTES DE ENERGÍA', fontsize=14, fontweight='bold')

plt.tight_layout()
plt.savefig(output_dir / 'distribucion_horaria_demanda.png', dpi=300, bbox_inches='tight')
print(f"   ✅ Guardada: {output_dir / 'distribucion_horaria_demanda.png'}")

# =============================================================================
# GRÁFICA 5: CARACTERÍSTICAS DEL PERFIL
# =============================================================================
print("\n5. Generando gráfica de características del perfil...")

fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

# 1. Variación de potencia entre intervalos
variacion = df['power_kw'].diff()
ax1.plot(tiempos[1:], variacion[1:], color='purple', linewidth=1.5)
ax1.axhline(0, color='black', linestyle='--', linewidth=1)
ax1.fill_between(tiempos[1:], variacion[1:], 0, alpha=0.3, color='purple')
ax1.set_ylabel('Cambio de potencia (kW)', fontsize=11, fontweight='bold')
ax1.set_title('VARIACIÓN DE POTENCIA ENTRE INTERVALOS\n(Muestra crecimiento aleatorio)',
              fontsize=12, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

# 2. Histograma de variación
variacion_filtrada = variacion[(df['hour'] >= 9) & (df['hour'] < 22)].dropna()
ax2.hist(variacion_filtrada, bins=30, color='purple', alpha=0.7, edgecolor='black')
ax2.axvline(0, color='red', linestyle='--', linewidth=2)
ax2.set_xlabel('Cambio de potencia (kW)', fontsize=11, fontweight='bold')
ax2.set_ylabel('Frecuencia', fontsize=11, fontweight='bold')
ax2.set_title('DISTRIBUCIÓN DE VARIACIONES\n(Horario operación: 9h-22h)',
              fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3, axis='y')

# Stats
mean_var = variacion_filtrada.mean()
std_var = variacion_filtrada.std()
ax2.text(0.05, 0.95, f'Media: {mean_var:.2f} kW\nDesv. Std: {std_var:.2f} kW',
         transform=ax2.transAxes, fontsize=10, verticalalignment='top',
         bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

# 3. Apertura y cierre (zoom)
df_apertura_cierre = df[(df['hour'] >= 8) & (df['hour'] <= 22)]
tiempos_ac = [datetime(2024, 1, 1, 0, 0) + timedelta(minutes=15*i)
              for i in df_apertura_cierre.index]

ax3.plot(tiempos_ac, df_apertura_cierre['power_kw'], color='darkgreen', linewidth=2.5)
ax3.fill_between(tiempos_ac, df_apertura_cierre['power_kw'], alpha=0.3, color='green')

# Marcar puntos clave
ax3.scatter([datetime(2024, 1, 1, 9, 0)], [0], color='green', s=200,
            marker='o', zorder=5, label='Apertura (0 kW)')
ax3.scatter([datetime(2024, 1, 1, 22, 0)], [0], color='red', s=200,
            marker='o', zorder=5, label='Cierre (0 kW)')

ax3.set_ylabel('Potencia (kW)', fontsize=11, fontweight='bold')
ax3.set_title('DETALLE: APERTURA Y CIERRE CON RAMPA\n(Carga cero en apertura y cierre)',
              fontsize=12, fontweight='bold')
ax3.legend(loc='upper left', fontsize=10)
ax3.grid(True, alpha=0.3)
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

# 4. Rampa de cierre (zoom en última hora)
df_rampa = df[(df['hour'] >= 21) & (df['hour'] < 23)]
tiempos_rampa = [datetime(2024, 1, 1, 0, 0) + timedelta(minutes=15*i)
                 for i in df_rampa.index]

ax4.plot(tiempos_rampa, df_rampa['power_kw'], color='darkred', linewidth=3,
         marker='o', markersize=8)
ax4.fill_between(tiempos_rampa, df_rampa['power_kw'], alpha=0.3, color='red')

# Añadir valores
for i, (t, p) in enumerate(zip(tiempos_rampa, df_rampa['power_kw'])):
    ax4.text(t, p + 15, f'{p:.0f} kW', ha='center', fontsize=9)

ax4.set_ylabel('Potencia (kW)', fontsize=11, fontweight='bold')
ax4.set_xlabel('Hora', fontsize=11, fontweight='bold')
ax4.set_title('RAMPA DE CIERRE (21h-22h)\n(Descenso lineal a cero)',
              fontsize=12, fontweight='bold')
ax4.grid(True, alpha=0.3)
ax4.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

plt.tight_layout()
plt.savefig(output_dir / 'caracteristicas_perfil.png', dpi=300, bbox_inches='tight')
print(f"   ✅ Guardada: {output_dir / 'caracteristicas_perfil.png'}")

# =============================================================================
# RESUMEN
# =============================================================================
print("\n" + "=" * 80)
print("RESUMEN DE GRÁFICAS GENERADAS")
print("=" * 80)
print(f"\nCarpeta de salida: {output_dir.resolve()}\n")
print("Gráficas generadas:")
print("  1. perfil_demanda_ev_15min.png - Perfil de demanda con resolución 15 minutos")
print("  2. operacion_bess_simulacion.png - Simulación de operación del BESS (SOC, potencia)")
print("  3. balance_energetico_bess.png - Balance energético diario")
print("  4. distribucion_horaria_demanda.png - Distribución por hora y fuentes")
print("  5. caracteristicas_perfil.png - Características del perfil (variación, rampa)")
print("\n✅ TODAS LAS GRÁFICAS GENERADAS EXITOSAMENTE")
print("=" * 80)
