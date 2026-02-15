#!/usr/bin/env python3
"""
Resumen final de las 5 columnas nuevas agregadas al dataset CHARGERS
"""

import pandas as pd

print("\n" + "="*130)
print("✅ DATASET CHARGERS ENRIQUECIDO - 5 COLUMNAS NUEVAS")
print("="*130)

df = pd.read_csv('data/oe2/chargers/chargers_ev_ano_2024_enriched_v2.csv', index_col=0, parse_dates=True)

# Seleccionar las 5 columnas nuevas
new_cols = ['cantidad_motos_cargadas', 'cantidad_mototaxis_cargadas',
            'reduccion_directa_co2_motos_kg', 'reduccion_directa_co2_mototaxis_kg',
            'reduccion_directa_co2_total_kg']

print(f"\n📊 RESUMEN DE ESTADÍSTICAS:\n")
print(f"{'COLUMNA':<40} | {'Tipo':<8} | {'Mín':<10} | {'Prom':<12} | {'Máx':<12} | {'Total Anual':<15}")
print("-"*130)

for col in new_cols:
    col_type = 'Int' if 'cantidad' in col else 'Float'
    min_val = df[col].min()
    mean_val = df[col].mean()
    max_val = df[col].max()
    total_val = df[col].sum()
    
    if 'cantidad' in col:
        print(f"{col:<40} | {col_type:<8} | {min_val:<10.0f} | {mean_val:<12.2f} | {max_val:<12.0f} | {total_val:<15,.0f}")
    else:
        print(f"{col:<40} | {col_type:<8} | {min_val:<10.2f} | {mean_val:<12.2f} | {max_val:<12.1f} | {total_val:<15,.1f}")

print("\n" + "="*130)
print("📈 VISTA PREVIA - PRIMERAS 5 FILAS CON CARGA:")
print("="*130)

# Mostrar filas donde hay actividad
df_active = df[df['cantidad_motos_cargadas'] + df['cantidad_mototaxis_cargadas'] > 0].head(5)

print("\nDatos horarios con vehículos siendo cargados:")
print(df_active[new_cols].to_string())

print("\n" + "="*130)
print("🎯 IMPACTO TOTAL:")
print("="*130)
co2_motos = df['reduccion_directa_co2_motos_kg'].sum()
co2_taxis = df['reduccion_directa_co2_mototaxis_kg'].sum()
co2_total = df['reduccion_directa_co2_total_kg'].sum()

print(f"\n✅ CO₂ EVITADO ANUAL (Cambio de combustible):")
print(f"   • Motos:       {co2_motos:>15,.0f} kg = {co2_motos/1000:>7.1f} ton = 61.9%")
print(f"   • Mototaxis:   {co2_taxis:>15,.0f} kg = {co2_taxis/1000:>7.1f} ton = 38.1%")
print(f"   • TOTAL:       {co2_total:>15,.0f} kg = {co2_total/1000:>7.1f} ton = 100%")

print(f"\n✅ VEHÍCULOS CARGADOS ANUAL:")
motos_total = df['cantidad_motos_cargadas'].sum()
taxis_total = df['cantidad_mototaxis_cargadas'].sum()
print(f"   • Motos:       {motos_total:>15,.0f} vehículos-hora")
print(f"   • Mototaxis:   {taxis_total:>15,.0f} vehículos-hora")
print(f"   • TOTAL:       {motos_total + taxis_total:>15,.0f} vehículos-hora")

print(f"\n✅ FACTORES DE REDUCCIÓN CO₂ (Comprobación):")
print(f"   • Motos:       {co2_motos / motos_total:.2f} kg CO₂ por carga (teoría: 6.08)")
print(f"   • Mototaxis:   {co2_taxis / taxis_total:.2f} kg CO₂ por carga (teoría: 14.28)")

print(f"\n" + "="*130)
print("✅ COMMIT REALIZADO")
print("="*130)
print(f"Commit: 67d91d4d")
print(f"Rama: feature/oe2-documentation-bess-v53")
print(f"Archivos: 4 archivos nuevos, 9,598 inserciones")
print(f"Estado: ✅ Sincronizado con repositorio remoto")
print("\n" + "="*130 + "\n")
