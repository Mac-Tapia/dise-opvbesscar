"""
Verificar apertura en cero y crecimiento aleatorio del perfil
"""
import pandas as pd
import numpy as np

df = pd.read_csv('data/oe2/perfil_horario_carga.csv')

print("=" * 80)
print("VERIFICACIÓN: APERTURA EN CERO Y CRECIMIENTO ALEATORIO")
print("=" * 80)

# Verificar apertura
primer_intervalo_operacion = df[df['power_kw'] > 0].iloc[0] if len(df[df['power_kw'] > 0]) > 0 else None
apertura_9h = df[df['hour'] == 9].iloc[0]

print("\n" + "=" * 80)
print("1. APERTURA (9h) - DEBE SER CERO")
print("=" * 80)
print(f"Primer intervalo (9:00): {apertura_9h['power_kw']:.2f} kW")
if apertura_9h['power_kw'] == 0.0:
    print("✅ CORRECTO: Apertura en CERO")
else:
    print(f"❌ ERROR: Apertura NO es cero ({apertura_9h['power_kw']:.2f} kW)")

print("\n" + "=" * 80)
print("2. CRECIMIENTO ALEATORIO (9h-18h)")
print("=" * 80)
print("Primeras 2 horas de operación (9h-11h) con detalle cada 15 min:")
print("-" * 80)

horas_inicio = df[(df['hour'] >= 9) & (df['hour'] < 11)][['interval', 'time_of_day', 'hour', 'minute', 'power_kw']]
print(horas_inicio.to_string(index=False))

# Calcular variación entre intervalos consecutivos
print("\n" + "=" * 80)
print("3. ANÁLISIS DE VARIACIÓN (diferencias entre intervalos consecutivos)")
print("=" * 80)

# Solo periodo de crecimiento (9h-18h)
crecimiento = df[(df['hour'] >= 9) & (df['hour'] < 18)].copy()
crecimiento['diff_kw'] = crecimiento['power_kw'].diff()

# Mostrar algunas diferencias
print("\nPrimeros 20 intervalos de crecimiento (9h-14h):")
print(f"{'Intervalo':<10} {'Tiempo':<10} {'Potencia (kW)':<15} {'Cambio (kW)':<15} {'Variación'}")
print("-" * 80)

for idx, row in crecimiento.head(20).iterrows():
    diff = row['diff_kw']
    if pd.notna(diff):
        if diff > 0:
            variacion = "↗️ Aumento"
        elif diff < 0:
            variacion = "↘️ Disminución"
        else:
            variacion = "→ Estable"
        print(f"{row['interval']:<10} {row['time_of_day']:<10.2f} {row['power_kw']:<15.2f} "
              f"{diff:>13.2f} {variacion}")
    else:
        print(f"{row['interval']:<10} {row['time_of_day']:<10.2f} {row['power_kw']:<15.2f} "
              f"{'---':>13} (primer intervalo)")

# Estadísticas de variación
diferencias = crecimiento['diff_kw'].dropna()
aumentos = diferencias[diferencias > 0]
disminuciones = diferencias[diferencias < 0]

print("\n" + "=" * 80)
print("ESTADÍSTICAS DE VARIACIÓN EN PERIODO DE CRECIMIENTO:")
print("=" * 80)
print(f"Total intervalos analizados: {len(diferencias)}")
print(f"Intervalos con aumento: {len(aumentos)} ({len(aumentos)/len(diferencias)*100:.1f}%)")
print(f"Intervalos con disminución: {len(disminuciones)} ({len(disminuciones)/len(diferencias)*100:.1f}%)")
print(f"\nPromedio de cambios: {diferencias.mean():.2f} kW/intervalo")
print(f"Desviación estándar: {diferencias.std():.2f} kW")
print(f"Cambio máximo (aumento): {diferencias.max():.2f} kW")
print(f"Cambio mínimo (disminución): {diferencias.min():.2f} kW")

print("\n" + "=" * 80)
print("4. HORA PICO - VARIACIÓN")
print("=" * 80)
pico = df[df['is_peak'] == True][['interval', 'time_of_day', 'hour', 'minute', 'power_kw']]
print(pico.to_string(index=False))

print(f"\nVariación en hora pico:")
print(f"  Potencia máxima: {pico['power_kw'].max():.2f} kW")
print(f"  Potencia mínima: {pico['power_kw'].min():.2f} kW")
print(f"  Diferencia: {pico['power_kw'].max() - pico['power_kw'].min():.2f} kW")
print(f"  Variación: {(pico['power_kw'].max() - pico['power_kw'].min()) / pico['power_kw'].mean() * 100:.1f}%")

print("\n" + "=" * 80)
print("RESUMEN FINAL:")
print("=" * 80)
print(f"✅ Apertura (9:00): {apertura_9h['power_kw']:.2f} kW (debe ser 0.00)")
print(f"✅ Primer carga (9:15): {df[df['interval'] == 37]['power_kw'].values[0]:.2f} kW")
print(f"✅ Crecimiento con variación aleatoria: {len(disminuciones)} retrocesos de {len(diferencias)} cambios")
print(f"✅ Cierre (22:00): {df[df['hour'] == 22]['power_kw'].sum():.2f} kW (debe ser 0.00)")
print(f"✅ Energía total: {df['energy_kwh'].sum():.2f} kWh")
