import pandas as pd
from pathlib import Path

csv_path = Path('data/processed/citylearn/iquitos_ev_mall/Building_1.csv')
df = pd.read_csv(csv_path)

print("="*80)
print("[BUILDING_1.CSV] Análisis Completo de Demanda")
print("="*80)
print(f"\nTotal filas: {len(df)}")
print(f"\nColumnas disponibles:")
for col in df.columns:
    print(f"  • {col}")

print("\n" + "─"*80)
print("[DESGLOSE DE DEMANDA]")
print("─"*80)

# Analizar cada columna de demanda
for col in ['non_shiftable_load', 'dhw_demand', 'cooling_demand', 'heating_demand']:
    if col in df.columns:
        total = df[col].sum()
        print(f"\n{col}:")
        print(f"  • Total: {total:,.0f} kWh")
        print(f"  • Min: {df[col].min():.1f} kW")
        print(f"  • Max: {df[col].max():.1f} kW")
        print(f"  • Mean: {df[col].mean():.1f} kW")

# Demanda TOTAL (si se suman todas las cargas)
all_demand_cols = [c for c in df.columns if 'demand' in c.lower() or 'load' in c.lower()]
print(f"\n" + "─"*80)
print("[DEMANDA TOTAL (TODAS LAS CARGAS)]")
print("─"*80)
if all_demand_cols:
    print(f"\nColumnas consideradas: {all_demand_cols}")
    df['total_demand'] = df[all_demand_cols].sum(axis=1)
    total_all = df['total_demand'].sum()
    print(f"\nSuma de todas las demandas/cargas:")
    print(f"  • Total: {total_all:,.0f} kWh")
    print(f"  • Mean: {df['total_demand'].mean():.1f} kW")
    print(f"  • Max: {df['total_demand'].max():.1f} kW")

# Energía solar
print(f"\n" + "─"*80)
print("[ENERGÍA SOLAR]")
print("─"*80)
if 'solar_generation' in df.columns:
    solar_total = df['solar_generation'].sum()
    print(f"\nSolar generation total: {solar_total:,.0f} kWh")
    print(f"  • Mean: {df['solar_generation'].mean():.1f} kW")
    print(f"  • Max: {df['solar_generation'].max():.1f} kW")

# Explicación clara
print(f"\n" + "="*80)
print("[INTERPRETACIÓN]")
print("="*80)
print(f"\n3,092,204 kWh = SOLO 'non_shiftable_load' (demanda del edificio)")
print(f"\nEsto NO incluye:")
print(f"  • EV charging demand (cargadores de vehículos)")
print(f"  • DHW demand (agua caliente)")
print(f"  • Cooling demand (refrigeración)")
print(f"  • Heating demand (calefacción)")
print(f"\nDemanda TOTAL del edificio = suma de TODAS las columnas")
