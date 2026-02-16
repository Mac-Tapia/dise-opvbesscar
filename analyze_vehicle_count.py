import pandas as pd
import numpy as np

print("="*80)
print("ANÁLISIS CORRECTO: CONTANDO VEHÍCULOS EN TODOS LOS SOCKETS")
print("="*80)
print()

df = pd.read_csv(
    "data/oe2/chargers/chargers_ev_ano_2024_v3.csv",
    on_bad_lines='skip',
    engine='python'
)

print(f"[1] ESTRUCTURA DEL DATASET:")
print(f"    Total registros: {len(df)} (8,760 = 1 año × 24 horas)")
print(f"    Total columnas: {df.shape[1]}")
print()

# Contar sockets
socket_columns = [col for col in df.columns if 'socket_' in col]
unique_sockets = set()
for col in socket_columns:
    socket_num = col.split('_')[1]
    unique_sockets.add(socket_num)

print(f"[2] SOCKETS DETECTADOS: {len(unique_sockets)}")
print(f"    Sockets: {sorted([f'socket_{i}' for i in sorted([int(x) for x in unique_sockets])])[:5]}...")
print()

# Contar vehículos por socket (columna vehicle_count)
print(f"[3] CONTANDO VEHÍCULOS EN CADA SOCKET:")
total_vehicles = 0
socket_totals = {}

for socket_id in sorted(unique_sockets):
    col = f'socket_{socket_id}_vehicle_count'
    if col in df.columns:
        count = df[col].sum()
        socket_totals[socket_id] = count
        total_vehicles += count
        if int(socket_id) < 3:
            print(f"    socket_{socket_id}: {count} vehículos/año")

print(f"    ...")
print(f"    socket_{max(unique_sockets)}: {socket_totals[max(unique_sockets)]} vehículos/año")
print()

print(f"[4] TOTAL DE VEHÍCULOS EN DATASET:")
print(f"    Total anual: {total_vehicles} vehículos")
print(f"    Promedio diario: {total_vehicles/365:.1f} vehículos")
print(f"    Promedio por socket: {total_vehicles/len(unique_sockets):.1f} vehículos/año")
print()

print(f"[5] COMPARACIÓN CON ESPECIFICACIÓN:")
print(f"    Especificación: 270 motos + 39 mototaxis = 309 vehículos/día")
print(f"    Dataset real: {total_vehicles/365:.1f} vehículos/día")

expected_annual = 309 * 365
if total_vehicles < expected_annual:
    ratio = (total_vehicles / expected_annual) * 100
    print(f"    ❌ Dataset incompleto: Solo {ratio:.1f}% de la demanda esperada")
    print(f"       Faltan: {expected_annual - total_vehicles} vehículos")
else:
    print(f"    ✓ Dataset completo o superior a especificación")
print()

# Analizar por tipo de vehículo si hay columnas de vehículos
print(f"[6] DISTRIBUCIÓN DE VEHÍCULOS POR DÍA:")
df['datetime'] = pd.to_datetime(df['datetime'])
df['date'] = df['datetime'].dt.date
daily_vehicles = df.groupby('date')[[col for col in df.columns if 'vehicle_count' in col]].sum().sum(axis=1)
print(f"    Min: {daily_vehicles.min()}, Max: {daily_vehicles.max()}, Promedio: {daily_vehicles.mean():.1f}")
print()

print("="*80)
print("RESPUESTA A: ¿POR QUÉ AGENTES CARGAN SOLO ~28 MOTOS?")
print("="*80)
print()
print(f"El dataset tiene SOLO ~{total_vehicles/365:.0f} vehículos/día")
print(f"Pero la especificación espera 309 vehículos/día")
print(f"Ratio: {(total_vehicles/365)/309*100:.1f}% de la demanda esperada")
print()
print("SOLUCIÓN: El dataset de demanda está SUB-DIMENSIONADO")
print("Los agentes cargan TODO lo que está disponible (~28 motos/día)")
print("Pero NO es x10-15 más porque no llegan 270 motos, solo ~10 motos/día por socket")
print("="*80)
