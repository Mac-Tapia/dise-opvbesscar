"""
Verifica disponibilidad de columnas PV en el dataset transformado
"""
import pandas as pd

df = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')

print("=" * 80)
print("VERIFICACIÓN: DESGLOSE DE ENERGÍA SOLAR (PV)")
print("=" * 80)

pv_cols = [col for col in df.columns if col.startswith('pv_')]
print("\nColumnas disponibles relacionadas a PV:")
for col in sorted(pv_cols):
    total = df[col].sum()
    print(f"  {col:30s}: {total:>15,.0f}")

print("\n" + "=" * 80)
print("DESGLOSE TOTAL DE GENERACIÓN SOLAR")
print("=" * 80)

pv_total = df['pv_kwh'].sum()
pv_to_ev = df['pv_to_ev_kwh'].sum() if 'pv_to_ev_kwh' in df.columns else 0
pv_to_bess = df['pv_to_bess_kwh'].sum() if 'pv_to_bess_kwh' in df.columns else 0
pv_to_mall = df['pv_to_mall_kwh'].sum() if 'pv_to_mall_kwh' in df.columns else 0
pv_to_grid = df['grid_export_kwh'].sum() if 'grid_export_kwh' in df.columns else 0

print(f"\n  Generación Solar Total:       {pv_total:>15,.0f} kWh (100%)")
print(f"  └─ Directo a EV:              {pv_to_ev:>15,.0f} kWh ({pv_to_ev/pv_total*100:>6.1f}%)")
print(f"  └─ A Carga BESS:              {pv_to_bess:>15,.0f} kWh ({pv_to_bess/pv_total*100:>6.1f}%)")
print(f"  └─ Directo a Mall:            {pv_to_mall:>15,.0f} kWh ({pv_to_mall/pv_total*100:>6.1f}%)")
print(f"  └─ EXPORTACIÓN A RED:         {pv_to_grid:>15,.0f} kWh ({pv_to_grid/pv_total*100:>6.1f}%)")
print(f"\n  Total asignado:               {pv_to_ev + pv_to_bess + pv_to_mall + pv_to_grid:>15,.0f} kWh")
print(f"  Diferencia (rounding):        {pv_total - (pv_to_ev + pv_to_bess + pv_to_mall + pv_to_grid):>15,.0f} kWh")

# Verificar BESS descarga
print("\n" + "=" * 80)
print("BESS DESCARGA (sale de BESS)")
print("=" * 80)

bess_to_ev = df['bess_to_ev_kwh'].sum() if 'bess_to_ev_kwh' in df.columns else 0
bess_to_mall = df['bess_to_mall_kwh'].sum() if 'bess_to_mall_kwh' in df.columns else 0
bess_total = bess_to_ev + bess_to_mall

print(f"\n  Descarga Total BESS:          {bess_total:>15,.0f} kWh")
print(f"  └─ Hacia EV:                  {bess_to_ev:>15,.0f} kWh ({bess_to_ev/bess_total*100:>6.1f}%)")
print(f"  └─ Hacia Mall:                {bess_to_mall:>15,.0f} kWh ({bess_to_mall/bess_total*100:>6.1f}%)")
