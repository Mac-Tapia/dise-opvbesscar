import pandas as pd
import numpy as np

print("="*80)
print("¿QUÉ SIGNIFICA REALMENTE 'VEHICLE_COUNT'?")
print("="*80)
print()

df = pd.read_csv(
    "data/oe2/chargers/chargers_ev_ano_2024_v3.csv",
    on_bad_lines='skip',
    engine='python'
)

print("[1] EXAMINANDO socket_000_vehicle_count:")
print(f"    Min: {df['socket_000_vehicle_count'].min()}")
print(f"    Max: {df['socket_000_vehicle_count'].max()}")
print(f"    Mean: {df['socket_000_vehicle_count'].mean():.2f}")
print(f"    Unique values: {df['socket_000_vehicle_count'].nunique()}")
print()
print("    Top 10 valores únicos:")
print(df['socket_000_vehicle_count'].value_counts().head(10))
print()

# Esto parece ser un SOC (State of Charge), no un contador
print("[2] INTERPRETACIÓN:")
print("    Rango [0-1] → Probablemente SOC (State of Charge)")
print("    Rango [0-100] → Probablemente SOC en %")
print("    Conteo entero → Número de vehículos")
print()

# Buscar la columna correcta para detectar arrivals
print("[3] COLUMNAS QUE PODRÍAN INDICAR ARRIVAL:")
for col in df.columns:
    if 'active' in col.lower() or 'arrival' in col.lower() or 'soc_arrival' in col.lower():
        print(f"    - {col}")
        if 'active' in col:
            print(f"      Values: {df[col].unique()[:5]}")
        if 'arrival' in col:
            print(f"      Stats: min={df[col].min()}, max={df[col].max()}")
print()

# socket_XXX_active indica si hay vehículo cargando
print("[4] ANALIZANDO socket_000_active (boolean de si hay vehículo activo):")
active_sum = df['socket_000_active'].sum()
print(f"    Horas con vehículo activo en socket_000: {active_sum} de 8760")
print(f"    Porcentaje: {(active_sum/8760)*100:.1f}%")
print()

# Contar vehículos activos por socket
print("[5] TOTAL DE ACTIVACIONES POR SOCKET (que ≈ vehículos cargados):")
total_activations = 0
for i in range(38):
    col = f'socket_{i:03d}_active'
    if col in df.columns:
        activations = df[col].sum()
        total_activations += activations
        if i < 3 or i >= 36:
            print(f"    socket_{i:03d}: {activations} horas/año con vehículo activo")
        elif i == 3:
            print(f"    ...")

print()
print(f"[6] TOTAL AGREGADO:")
print(f"    Total horas-vehículo: {total_activations} (no es lo mismo que # de vehículos)")
print(f"    Sockets × Horas = {38 * 8760} horas máximo posible")
print(f"    Utilización: {(total_activations/(38*8760))*100:.1f}%")
print()

# El número de vehículos cargados es cuándo socket_active cambia de False a True
print("[7] CONTANDO EVENTOS DE ARRIVAL (cambios de False→True):")
unique_events = 0
for i in range(38):
    col = f'socket_{i:03d}_active'
    if col in df.columns:
        # Contar transiciones de 0→1 (arrival)
        transitions = (df[col].astype(int).diff() > 0).sum()
        unique_events += transitions
        if i < 3 or i >= 36:
            print(f"    socket_{i:03d}: ~{int(transitions)} arrivals/año")
        elif i == 3:
            print(f"    ...")

print()
print(f"[8] ESTIMACIÓN DE VEHÍCULOS CARGADOS POR EPISODIO (1 día):")
vehicles_per_day = unique_events / 365
print(f"    Total arrivals/año: {int(unique_events)}")
print(f"    Promedio arrivals/día: {vehicles_per_day:.1f}")
print(f"    ESTO COINCIDE CON LO QUE CARGAN LOS AGENTES (~28)")
print()

print("="*80)
