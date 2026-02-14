#!/usr/bin/env python3
"""Análisis detallado del dataset SOLAR mejorado con 5 columnas nuevas"""

import pandas as pd
import numpy as np

df = pd.read_csv('data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv', index_col=0, parse_dates=True)

print("\n" + "="*100)
print("📊 ANÁLISIS DATASET SOLAR MEJORADO - 5 COLUMNAS NUEVAS AGREGADAS")
print("="*100)

print(f"\n✓ Filas: {len(df):,} (365 días × 24 horas)")
print(f"✓ Columnas totales: {len(df.columns)}")
print(f"✓ Período: 2024 completo (Iquitos, Perú)")

print("\n" + "-"*100)
print("📋 COLUMNAS NUEVAS AGREGADAS")
print("-"*100)

print(f"\n1️⃣  Energía suministrada al BESS:")
print(f"    • Total anual: {df['energia_suministrada_al_bess_kwh'].sum():>15,.0f} kWh")
print(f"    • Promedio por hora: {df['energia_suministrada_al_bess_kwh'].mean():>10.1f} kWh/h")
print(f"    • Máximo horario: {df['energia_suministrada_al_bess_kwh'].max():>14.1f} kWh/h")
print(f"    • Horas con suministro: {(df['energia_suministrada_al_bess_kwh'] > 0).sum():>5d} horas ({(df['energia_suministrada_al_bess_kwh'] > 0).sum()/len(df)*100:.1f}%)")
print(f"    └─ Descripción: Solar almacenada en BESS para uso posterior")

print(f"\n2️⃣  Energía suministrada al EV:")
print(f"    • Total anual: {df['energia_suministrada_al_ev_kwh'].sum():>15,.0f} kWh")
print(f"    • Promedio por hora: {df['energia_suministrada_al_ev_kwh'].mean():>10.1f} kWh/h")
print(f"    • Máximo horario: {df['energia_suministrada_al_ev_kwh'].max():>14.1f} kWh/h")
print(f"    • Horas con suministro: {(df['energia_suministrada_al_ev_kwh'] > 0).sum():>5d} horas ({(df['energia_suministrada_al_ev_kwh'] > 0).sum()/len(df)*100:.1f}%)")
print(f"    └─ Descripción: Solar directo a EV + BESS descargado a EV (100% aprovechamiento)")

print(f"\n3️⃣  Energía suministrada al Mall:")
print(f"    • Total anual: {df['energia_suministrada_al_mall_kwh'].sum():>15,.0f} kWh")
print(f"    • Promedio por hora: {df['energia_suministrada_al_mall_kwh'].mean():>10.1f} kWh/h")
print(f"    • Máximo horario: {df['energia_suministrada_al_mall_kwh'].max():>14.1f} kWh/h")
print(f"    • Horas con suministro: {(df['energia_suministrada_al_mall_kwh'] > 0).sum():>5d} horas ({(df['energia_suministrada_al_mall_kwh'] > 0).sum()/len(df)*100:.1f}%)")
print(f"    └─ Descripción: Solar directo a mall + BESS descargado a mall (100% aprovechamiento)")

print(f"\n4️⃣  Energía suministrada a Red Pública:")
print(f"    • Total anual: {df['energia_suministrada_a_red_kwh'].sum():>15,.0f} kWh")
print(f"    • Promedio por hora: {df['energia_suministrada_a_red_kwh'].mean():>10.1f} kWh/h")
print(f"    • Máximo horario: {df['energia_suministrada_a_red_kwh'].max():>14.1f} kWh/h")
print(f"    • Horas con suministro: {(df['energia_suministrada_a_red_kwh'] > 0).sum():>5d} horas ({(df['energia_suministrada_a_red_kwh'] > 0).sum()/len(df)*100:.1f}%)")
print(f"    └─ Descripción: Solar excedente/curtido (exportación a red)")

print(f"\n5️⃣  Reducción Indirecta CO₂ (TOTAL - de TODA la generación solar):")
print(f"    • Total anual: {df['reduccion_indirecta_co2_kg_total'].sum():>15,.0f} kg")
print(f"    • Total anual: {df['reduccion_indirecta_co2_kg_total'].sum()/1000:>20.1f} ton")
print(f"    • Promedio por hora: {df['reduccion_indirecta_co2_kg_total'].mean():>10.3f} kg/h")
print(f"    • Factor aplicado: 0.4521 kg CO₂/kWh (diesel Iquitos)")
print(f"    └─ Descripción: TODA la generación solar × factor CO₂ (100% desplaza diesel)")

print("\n" + "-"*100)
print("🔗 FLUJOS DE ENERGÍA ANUALES (Balance 100% aprovechamiento)")
print("-"*100)

pv_totl = df['energia_kwh'].sum()
sumin_bess = df['energia_suministrada_al_bess_kwh'].sum()
sumin_ev = df['energia_suministrada_al_ev_kwh'].sum()
sumin_mall = df['energia_suministrada_al_mall_kwh'].sum()
sumin_red = df['energia_suministrada_a_red_kwh'].sum()
co2_total = df['reduccion_indirecta_co2_kg_total'].sum()

print(f"\nGeneración Solar PV Total: {pv_totl:>15,.0f} kWh (100%)")
print(f"├─ → Energía a BESS:       {sumin_bess:>15,.0f} kWh ({sumin_bess/pv_totl*100:>5.1f}%)")
print(f"├─ → Energía a EV:         {sumin_ev:>15,.0f} kWh ({sumin_ev/pv_totl*100:>5.1f}%)")
print(f"├─ → Energía a Mall:       {sumin_mall:>15,.0f} kWh ({sumin_mall/pv_totl*100:>5.1f}%)")
print(f"└─ → Energía a Red Pública: {sumin_red:>15,.0f} kWh ({sumin_red/pv_totl*100:>5.1f}%)")

print(f"\nCO₂ Reducido Indirecto (desplazamiento diesel):")
print(f"└─ TODA la solar desplaza diesel: {co2_total:>15,.0f} kg ({co2_total/1000:.1f} ton)")

print("\n" + "-"*100)
print("📈 DATOS HORARIOS - EJEMPLOS")
print("-"*100)

# Mostrar hora con máxima generación solar
max_idx = df['energia_kwh'].idxmax()
print(f"\nHora con máxima generación solar: {max_idx}")
print(df.loc[max_idx, ['energia_kwh', 'energia_suministrada_al_bess_kwh', 
                       'energia_suministrada_al_ev_kwh', 'energia_suministrada_al_mall_kwh',
                       'energia_suministrada_a_red_kwh', 'reduccion_indirecta_co2_kg_total']].to_string())

# Mostrar primeras 3 filas
print(f"\nPrimeras 3 filas (madrugada, sin solar):")
print(df[['energia_kwh', 'energia_suministrada_al_bess_kwh', 
          'energia_suministrada_al_ev_kwh', 'energia_suministrada_al_mall_kwh',
          'energia_suministrada_a_red_kwh', 'reduccion_indirecta_co2_kg_total']].head(3).to_string())

print("\n" + "="*100)
print("✅ DATASET SOLAR MEJORADO LISTO PARA CityLearn v2")
print("="*100 + "\n")
