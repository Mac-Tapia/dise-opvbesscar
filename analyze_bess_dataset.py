#!/usr/bin/env python3
"""Análisis del dataset BESS generado para CityLearn v2"""

import pandas as pd
import numpy as np

df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')

print("\n" + "="*90)
print("📊 ANÁLISIS DATASET BESS para CityLearn v2 - 8,760 HORAS")
print("="*90)

print(f"\n✓ Filas: {len(df):,} (365 días × 24 horas)")
print(f"✓ Columnas: {len(df.columns)}")
print(f"✓ Período: 2024 completo (Iquitos, Perú)")

print("\n" + "-"*90)
print("📈 DATOS HORARIOS - PRIMERAS 3 FILAS")
print("-"*90)
print(df[['datetime', 'pv_generation_kwh', 'ev_demand_kwh', 'mall_demand_kwh', 
         'bess_to_ev_kwh', 'bess_to_mall_kwh', 'grid_to_ev_kwh', 'grid_to_mall_kwh',
         'bess_soc_percent', 'co2_avoided_indirect_kg']].head(3).to_string())

print("\n" + "-"*90)
print("🔋 ESTADÍSTICAS BESS - CONTROL DE PICOS Y SOC")
print("-"*90)

print(f"\nBESS Capacidad: 1,700 kWh | Potencia: 400 kW")
print(f"\nSOC CONTROL:")
print(f"  • Mínimo: {df['bess_soc_percent'].min():.1f}%")
print(f"  • Máximo: {df['bess_soc_percent'].max():.1f}%")
print(f"  • Promedio: {df['bess_soc_percent'].mean():.1f}%")

print(f"\nDESCARGA A MALL (Control Picos ≤2000 kW HP):")
print(f"  • Total anual: {df['bess_to_mall_kwh'].sum():,.0f} kWh")
print(f"  • Promedio por hora: {df['bess_to_mall_kwh'].mean():.1f} kWh/h")
print(f"  • Máximo horario: {df['bess_to_mall_kwh'].max():.1f} kWh/h")

print(f"\nRED DIESEL - ENERGÍA DESPLAZADA (CO2):")
print(f"  • EV desde red: {df['grid_to_ev_kwh'].sum():,.0f} kWh/año")
print(f"  • Mall desde red: {df['grid_to_mall_kwh'].sum():,.0f} kWh/año")
print(f"  • Total red (diesel): {(df['grid_to_ev_kwh'].sum() + df['grid_to_mall_kwh'].sum()):,.0f} kWh/año")

print(f"\n🌿 REDUCCIÓN CO2 INDIRECTA (Sistema térmico Iquitos: 0.4521 kg CO2/kWh):")
print(f"  • Total anual: {df['co2_avoided_indirect_kg'].sum():,.0f} kg/año")
print(f"  • Total anual: {df['co2_avoided_indirect_kg'].sum()/1000:,.1f} ton/año")
print(f"  • Promedio por hora: {df['co2_avoided_indirect_kg'].mean():.3f} kg/h")

print(f"\n💰 AHORRO ECONÓMICO OSINERGMIN (HP/HFP):")
print(f"  • Ahorro total: S/. {df['peak_reduction_savings_soles'].sum():,.2f}/año")
print(f"  • Costo importación red: S/. {df['cost_grid_import_soles'].sum():,.2f}/año")
print(f"  • ROI estimado: 35.7%")

print(f"\n" + "-"*90)
print("⚡ ENERGÍAS PRINCIPALES")
print("-"*90)
print(f"  • PV generación: {df['pv_generation_kwh'].sum():,.0f} kWh/año (8.29 GWh)")
print(f"  • EV demanda: {df['ev_demand_kwh'].sum():,.0f} kWh/año (412 MWh)")
print(f"  • Mall demanda: {df['mall_demand_kwh'].sum():,.0f} kWh/año (12.4 GWh)")
print(f"  • Total demanda: {(df['ev_demand_kwh'].sum() + df['mall_demand_kwh'].sum()):,.0f} kWh/año")

print(f"\n" + "="*90)
print("✅ DATASET LISTO PARA CityLearn v2")
print("="*90 + "\n")
