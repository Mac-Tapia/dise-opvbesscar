"""
Generar visualización de datos para REDUCCIÓN DIRECTA CO₂ ANUAL
"""

import json
import pandas as pd
from pathlib import Path

# Cargar datos del JSON
with open('REDUCCION_DIRECTA_CO2_ANUAL_DETALLADO.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# ============================================================================
# VISUALIZACIÓN 1: RESUMEN EN TEXTO
# ============================================================================

print("╔" + "═" * 88 + "╗")
print("║" + " " * 88 + "║")
print("║" + "REDUCCIÓN DIRECTA DE CO₂ ANUAL - RESUMEN VISUAL".center(88) + "║")
print("║" + " " * 88 + "║")
print("╚" + "═" * 88 + "╝")
print()

# Datos motos
motos = data['motos']
mototaxis = data['mototaxis']
totales = data['totales']

# ============================================================================
# TABLA 1: COMPARATIVA DIRECTA
# ============================================================================

print("┌─ TABLA 1: REDUCCIÓN POR TIPO DE VEHÍCULO")
print("│")
print("│      Tipo      │ Cantidad │  Energía   │  Factor  │ Reducción CO₂ │  Por Veh.")
print("│                │ Vehículos│ (kWh/año)  │(kg CO₂)  │   (tCO₂/año)  │(tCO₂/año)")
print("├────────────────┼──────────┼────────────┼──────────┼───────────────┼──────────")
print(f"│ 🏍️  Motos      │    {motos['cantidad']:2d}    │{motos['energía_cargada_kwh']:>10,.0f} │  {motos['factor_co2_kg_per_kwh']:.2f}   │   {motos['reduccion_co2_total_tco2']:>6.1f}      │   {motos['reduccion_co2_por_vehiculo_tco2']:>5.1f}")
print(f"│ 🚕 Mototaxis   │    {mototaxis['cantidad']:2d}    │{mototaxis['energía_cargada_kwh']:>10,.0f} │  {mototaxis['factor_co2_kg_per_kwh']:.2f}   │   {mototaxis['reduccion_co2_total_tco2']:>6.1f}      │   {mototaxis['reduccion_co2_por_vehiculo_tco2']:>5.1f}")
print("├────────────────┼──────────┼────────────┼──────────┼───────────────┼──────────")
print(f"│ TOTAL          │    {totales['vehículos_totales']:2d}    │{totales['energía_total_kwh']:>10,.0f} │    —    │   {totales['reduccion_co2_anual_total_tco2']:>6.1f}      │    —")
print("└────────────────┴──────────┴────────────┴──────────┴───────────────┴──────────")
print()

# ============================================================================
# GRÁFICO 1: DISTRIBUCIÓN DE REDUCCIÓN CO₂
# ============================================================================

print("┌─ GRÁFICO 1: DISTRIBUCIÓN DE REDUCCIÓN CO₂")
print("│")

motos_pct = (motos['reduccion_co2_total_tco2'] / totales['reduccion_co2_anual_total_tco2']) * 100
mototaxis_pct = (mototaxis['reduccion_co2_total_tco2'] / totales['reduccion_co2_anual_total_tco2']) * 100

bar_length = 50
motos_bar = int((motos_pct / 100) * bar_length)
mototaxis_bar = int((mototaxis_pct / 100) * bar_length)

print(f"│ Motos ({motos_pct:.1f}%):")
print(f"│ {'█' * motos_bar}{'░' * (bar_length - motos_bar)}  {motos['reduccion_co2_total_tco2']:.1f} tCO₂/año")
print(f"│")
print(f"│ Mototaxis ({mototaxis_pct:.1f}%):")
print(f"│ {'█' * mototaxis_bar}{'░' * (bar_length - mototaxis_bar)}  {mototaxis['reduccion_co2_total_tco2']:.1f} tCO₂/año")
print("│")
print(f"│ TOTAL: {totales['reduccion_co2_anual_total_tco2']:.1f} tCO₂/año")
print("└")
print()

# ============================================================================
# TABLA 2: DESGLOSE TEMPORAL
# ============================================================================

print("┌─ TABLA 2: REDUCCIÓN ACUMULADA POR PERÍODO TEMPORAL")
print("│")

print("│ Período        │      Motos      │    Mototaxis    │        TOTAL")
print("│                │  (tCO₂/período) │ (tCO₂/período)  │   (tCO₂/período)")
print("├────────────────┼─────────────────┼─────────────────┼──────────────────")

# Diario
diario_motos = motos['reduccion_co2_diaria_tco2']
diario_mototaxis = mototaxis['reduccion_co2_diaria_tco2']
diario_total = totales['reduccion_co2_diaria_total_tco2']
print(f"│ Por día        │        {diario_motos:.2f}      │       {diario_mototaxis:.2f}      │       {diario_total:.2f}")

# Mensual
mensual_motos = motos['reduccion_co2_total_tco2'] / 12
mensual_mototaxis = mototaxis['reduccion_co2_total_tco2'] / 12
mensual_total = totales['reduccion_co2_mensual_total_tco2']
print(f"│ Por mes        │       {mensual_motos:.1f}       │       {mensual_mototaxis:.1f}       │       {mensual_total:.1f}")

# Anual
print(f"│ Por año        │       {motos['reduccion_co2_total_tco2']:.1f}       │       {mototaxis['reduccion_co2_total_tco2']:.1f}       │       {totales['reduccion_co2_anual_total_tco2']:.1f}")

print("└────────────────┴─────────────────┴─────────────────┴──────────────────")
print()

# ============================================================================
# TABLA 3: EQUIVALENTE DE COMBUSTIBLE
# ============================================================================

print("┌─ TABLA 3: EQUIVALENTE DE COMBUSTIBLE NO QUEMADO")
print("│")
print("│ Tipo       │ Combustible │  Cantidad Equiv.  │  Por Vehículo")
print("│            │   Tipo      │  (Litros/año)     │  (Litros/año)")
print("├────────────┼─────────────┼───────────────────┼──────────────")
print(f"│ Motos      │  Gasolina   │  {motos['combustible_equivalente_litros']:>15,.0f} │  {motos['combustible_equivalente_litros']/motos['cantidad']:>10,.0f}")
print(f"│ Mototaxis  │  Diésel     │  {mototaxis['combustible_equivalente_litros']:>15,.0f} │  {mototaxis['combustible_equivalente_litros']/mototaxis['cantidad']:>10,.0f}")
print("├────────────┼─────────────┼───────────────────┼──────────────")
print(f"│ TOTAL      │     —       │  {totales['combustible_equivalente_total_litros']:>15,.0f} │      —")
print("└────────────┴─────────────┴───────────────────┴──────────────")
print()

# ============================================================================
# TABLA 4: DIFERENCIA DE TANQUE
# ============================================================================

print("┌─ TABLA 4: ANÁLISIS DE DIFERENCIA DE TAMAÑO DE TANQUE")
print("│")

energia_per_moto = motos['energía_cargada_kwh'] / motos['cantidad']
energia_per_mototaxi = mototaxis['energía_cargada_kwh'] / mototaxis['cantidad']
ratio = energia_per_mototaxi / energia_per_moto

print(f"│ Energía promedio por vehículo:")
print(f"│   Moto:        {energia_per_moto:>10,.0f} kWh/año")
print(f"│   Mototaxi:    {energia_per_mototaxi:>10,.0f} kWh/año")
print(f"│   Ratio:       {ratio:>10.2f}x más en mototaxis")
print(f"│")
print(f"│ Combustible equivalente por vehículo:")
print(f"│   Moto:        {motos['combustible_equivalente_litros']/motos['cantidad']:>10,.0f} L/año")
print(f"│   Mototaxi:    {mototaxis['combustible_equivalente_litros']/mototaxis['cantidad']:>10,.0f} L/año")
print(f"│   Diferencia:  {(mototaxis['combustible_equivalente_litros']/mototaxis['cantidad']) - (motos['combustible_equivalente_litros']/motos['cantidad']):>10,.0f} L/año (+{((energia_per_mototaxi/energia_per_moto)-1)*100:.0f}%)")
print(f"│")
print(f"│ Reducción CO₂ por vehículo:")
print(f"│   Moto:        {motos['reduccion_co2_por_vehiculo_tco2']:>10.1f} tCO₂/año")
print(f"│   Mototaxi:    {mototaxis['reduccion_co2_por_vehiculo_tco2']:>10.1f} tCO₂/año")
print(f"│")
print(f"│ 📌 Nota: Aunque mototaxis cargan {ratio:.2f}× más energía,")
print(f"│    la reducción es MENOR por el factor CO₂ más bajo (diésel)")
print("└")
print()

# ============================================================================
# FÓRMULAS
# ============================================================================

print("╔" + "═" * 88 + "╗")
print("║" + "FÓRMULAS UTILIZADAS".center(88) + "║")
print("╚" + "═" * 88 + "╝")
print()

print("📐 MOTOS (Gasolina):")
print(f"   Reducción = Energía × Factor CO₂")
print(f"   Reducción = {motos['energía_cargada_kwh']:,.0f} kWh/año × {motos['factor_co2_kg_per_kwh']} kg CO₂/kWh ÷ 1,000")
print(f"   Reducción = {motos['reduccion_co2_total_tco2']:.1f} tCO₂/año")
print()

print("📐 MOTOTAXIS (Diésel):")
print(f"   Reducción = Energía × Factor CO₂")
print(f"   Reducción = {mototaxis['energía_cargada_kwh']:,.0f} kWh/año × {mototaxis['factor_co2_kg_per_kwh']} kg CO₂/kWh ÷ 1,000")
print(f"   Reducción = {mototaxis['reduccion_co2_total_tco2']:.1f} tCO₂/año")
print()

print("📐 TOTAL:")
print(f"   Reducción TOTAL = {motos['reduccion_co2_total_tco2']:.1f} + {mototaxis['reduccion_co2_total_tco2']:.1f}")
print(f"   Reducción TOTAL = {totales['reduccion_co2_anual_total_tco2']:.1f} tCO₂/año")
print()

# ============================================================================
# CONCLUSIÓN
# ============================================================================

print("╔" + "═" * 88 + "╗")
print("║" + "✅ CONCLUSIÓN FINAL".center(88) + "║")
print("╚" + "═" * 88 + "╝")
print()

print(f"La REDUCCIÓN DIRECTA DE CO₂ del proyecto PVBESSCAR es:")
print()
print(f"  🎯 VALOR TOTAL:  {totales['reduccion_co2_anual_total_tco2']:>10.1f} tCO₂/año")
print()
print(f"  📊 Desglose:")
print(f"     • Motos (15 veh):     {motos['reduccion_co2_total_tco2']:>8.1f} tCO₂/año  ({motos_pct:.1f}%)")
print(f"     • Mototaxis (4 veh):  {mototaxis['reduccion_co2_total_tco2']:>8.1f} tCO₂/año  ({mototaxis_pct:.1f}%)")
print()
print(f"  ⏱️  Temporalidad:")
print(f"     • Por día:   {totales['reduccion_co2_diaria_total_tco2']:>8.2f} tCO₂/día")
print(f"     • Por mes:   {totales['reduccion_co2_mensual_total_tco2']:>8.1f} tCO₂/mes")
print(f"     • Por año:   {totales['reduccion_co2_anual_total_tco2']:>8.1f} tCO₂/año")
print()
print(f"  ⛽ Equivalente de Combustible:")
print(f"     • Gasolina no quemada (motos):     {motos['combustible_equivalente_litros']:>8,.0f} L/año")
print(f"     • Diésel no quemado (mototaxis):  {mototaxis['combustible_equivalente_litros']:>8,.0f} L/año")
print(f"     • TOTAL combustible evitado:      {totales['combustible_equivalente_total_litros']:>8,.0f} L/año")
print()
print(f"✓ Período:              1 AÑO COMPLETO (8,760 horas)")
print(f"✓ Consideraciones:      Diferencias de tanque (1.35× en mototaxis)")
print(f"✓ Factores:             Diferenciados por combustible (0.87 vs 0.47)")
print(f"✓ Datos:                Reales 2024 (chargers_real_statistics.csv)")
print()
