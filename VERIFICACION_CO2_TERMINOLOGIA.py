#!/usr/bin/env python3
"""
VERIFICACIÓN: CO2 Reducción Directa vs CO2 Neto
Asegura que la distinción est BIEN CLARA en el código y datos
2026-02-16
"""
import pandas as pd
from pathlib import Path

print("="*80)
print("VERIFICACIÓN: CO2 REDUCCIÓN DIRECTA vs CO2 NETO")
print("="*80)
print()

# Cargar dataset
csv_path = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
df = pd.read_csv(csv_path, index_col=0, parse_dates=True)

print("1️⃣  COLUMNAS CO2 PRESENTES")
print("-" * 80)

co2_cols = [
    'co2_reduccion_motos_kg',
    'co2_reduccion_mototaxis_kg',
    'reduccion_directa_co2_kg',
    'co2_grid_kwh',
    'co2_neto_por_hora_kg'
]

for col in co2_cols:
    if col in df.columns:
        print(f"✅ {col}")
    else:
        print(f"❌ {col} - FALTANTE")

print()
print("2️⃣  DEFINICIONES (Anual)")
print("-" * 80)

reduce_motos = df['co2_reduccion_motos_kg'].sum()
reduce_taxis = df['co2_reduccion_mototaxis_kg'].sum()
reduce_directa = df['reduccion_directa_co2_kg'].sum()
co2_grid = df['co2_grid_kwh'].sum()
co2_neto = df['co2_neto_por_hora_kg'].sum()

print()
print("a) REDUCCIÓN DIRECTA (SOLO cambio de combustible)")
print("   = Gasolina que NO se quema porque usan EV")
print("-" * 80)
print(f"  • CO2 motos reducido:         {reduce_motos:,.0f} kg")
print(f"  • CO2 taxis reducido:         {reduce_taxis:,.0f} kg")
print(f"  • TOTAL reducción DIRECTA:    {reduce_directa:,.0f} kg")
print()
print("  ⚠️  Esto es SOLO por cambio (gasolina → eléctrico)")
print("  ⚠️  NO incluye costo del grid diesel")
print()

print("b) CO2 DEL GRID (SOLO costo de generar electricidad)")
print("   = Diesel que se quema en Iquitos para generar esa electricidad")
print("-" * 80)
print(f"  • CO2 por diesel generado:    {co2_grid:,.0f} kg")
print()
print("  ⚠️  Esto es SOLO costo de energía, sin reducción")
print()

print("c) CO2 NETO (Impacto REAL considerando todo)")
print("   = Reducción directa - CO2 grid")
print("   = (Gasolina evitada) - (Diesel generado)")
print("-" * 80)
print(f"  REDUCCIÓN DIRECTA:        +{reduce_directa:,.0f} kg")
print(f"  CO2 GRID:                 -{co2_grid:,.0f} kg")
print(f"  ─────────────────────────────────")
print(f"  CO2 NETO TOTAL:           {co2_neto:,.0f} kg")
print()

if co2_neto > 0:
    print(f"  ✅ POSITIVO: Beneficio ambiental neto de {co2_neto:,.0f} kg/año")
    print("     Los EVs son más eficientes que motos gasolina")
else:
    print(f"  ❌ NEGATIVO: Costo ambiental neto")
    print("     (pero solar cambiaría esto completamente)")

print()
print("3️⃣  VERIFICACIÓN DE COHERENCIA")
print("-" * 80)

# Verificar que reduccion_directa = motos + taxis
check1 = abs((reduce_motos + reduce_taxis) - reduce_directa) < 0.1
print(f"  {'✅' if check1 else '❌'} reduccion_directa = motos + taxis")

# Verificar que neto = reduccion_directa - grid
calculated_neto = reduce_directa - co2_grid
check2 = abs(calculated_neto - co2_neto) < 0.1
print(f"  {'✅' if check2 else '❌'} co2_neto = reduccion_directa - co2_grid")

# Verificar rango
energy_motos = df['ev_energia_motos_kwh'].sum()
energy_taxis = df['ev_energia_mototaxis_kwh'].sum()
energy_total = df['ev_energia_total_kwh'].sum()

check3 = energy_total == energy_motos + energy_taxis
print(f"  {'✅' if check3 else '❌'} Energía: motos + taxis = total")
print(f"     Motos:  {energy_motos:,.0f} kWh")
print(f"     Taxis:  {energy_taxis:,.0f} kWh")
print(f"     Total:  {energy_total:,.0f} kWh")

# Verificar factores
factor_motos_calc = reduce_motos / energy_motos if energy_motos > 0 else 0
factor_taxis_calc = reduce_taxis / energy_taxis if energy_taxis > 0 else 0

print()
print(f"  Factor CO2 motos:   {factor_motos_calc:.4f} kg CO2/kWh (esperado: 0.8700)")
print(f"  Factor CO2 taxis:   {factor_taxis_calc:.4f} kg CO2/kWh (esperado: 0.4700)")

check4 = abs(factor_motos_calc - 0.87) < 0.001
check5 = abs(factor_taxis_calc - 0.47) < 0.001
print(f"  {'✅' if check4 else '❌'} Factor motos correcto (0.87)")
print(f"  {'✅' if check5 else '❌'} Factor taxis correcto (0.47)")

print()
print("4️⃣  EJEMPLO HORA ESPECÍFICA (cualquier hora del año)")
print("-" * 80)

hora_ejemplo = 14  # A las 2 PM
print(f"\nHora {hora_ejemplo}:00 (Peak)")
print()
print(f"  Energía motos:           {df['ev_energia_motos_kwh'].iloc[hora_ejemplo]:.1f} kWh")
print(f"  Energía taxis:           {df['ev_energia_mototaxis_kwh'].iloc[hora_ejemplo]:.1f} kWh")
print(f"  Energía total:           {df['ev_energia_total_kwh'].iloc[hora_ejemplo]:.1f} kWh")
print()
print(f"  REDUCCIÓN DIRECTA (solo combustible):")
print(f"    Motos:     {df['co2_reduccion_motos_kg'].iloc[hora_ejemplo]:.2f} kg CO2 evitado")
print(f"    Taxis:     {df['co2_reduccion_mototaxis_kg'].iloc[hora_ejemplo]:.2f} kg CO2 evitado")
print(f"    TOTAL:     {df['reduccion_directa_co2_kg'].iloc[hora_ejemplo]:.2f} kg CO2 evitado ⚠️ SOLO COMBUSTIBLE")
print()
print(f"  CO2 GRID (solo diesel para electricidad):")
print(f"    Diesel:    {df['co2_grid_kwh'].iloc[hora_ejemplo]:.2f} kg CO2 generado")
print()
print(f"  CO2 NETO (impacto real):")
print(f"    {df['reduccion_directa_co2_kg'].iloc[hora_ejemplo]:.2f} - {df['co2_grid_kwh'].iloc[hora_ejemplo]:.2f} = {df['co2_neto_por_hora_kg'].iloc[hora_ejemplo]:.2f} kg CO2")

if df['co2_neto_por_hora_kg'].iloc[hora_ejemplo] > 0:
    print(f"    ✅ Esta hora fue POSITIVA (beneficio)")
else:
    print(f"    ❌ Esta hora fue NEGATIVA (costo)")

print()
print("="*80)
print("✅ VERIFICACIÓN COMPLETADA")
print("="*80)
print()
print("CONCLUSIONES:")
print("━" * 80)
print()
print("1. REDUCCIÓN DIRECTA (reduccion_directa_co2_kg)")
print("   = SOLO cambio de combustible (gasolina → eléctrico)")
print(f"   = {reduce_directa/1000:.1f} Mg CO2 evitado por cambio combustible")
print("   → Esto sería idéntico incluso sin usar grid solar")
print()
print("2. CO2 GRID (co2_grid_kwh)")
print("   = SOLO costo de generar electricidad con diesel")
print(f"   = {co2_grid/1000:.1f} Mg CO2 generado por red diesel")
print("   → Este costo se REDUCE con solar (reemplaza diesel)")
print()
print("3. CO2 NETO (co2_neto_por_hora_kg)")
print("   = Impacto REAL: (gasolina evitada) - (diesel generado)")
print(f"   = {co2_neto/1000:.1f} Mg CO2 beneficio NETO")
print()
if co2_neto > 0:
    print(f"   ✅ POSITIVO: EVs generan {co2_neto/1000:.1f} Mg beneficio neto")
    print("      (motos EV son 44% más eficientes que motos gasolina)")
    print("      (con solar, el beneficio sería incluso mayor)")
print()
print("━" * 80)
print()
