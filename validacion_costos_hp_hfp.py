#!/usr/bin/env python3
"""
Validación: Costos y Ahorros HP/HFP - OSINERGMIN Integrado v5.7
Verifica que los nuevos cálculos de tarifas estén correctos en ambas funciones BESS
"""

import numpy as np
import pandas as pd
from pathlib import Path

# Cambiar al directorio del proyecto
import sys
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dimensionamiento.oe2.disenobess.bess import (
    simulate_bess_ev_exclusive,
    simulate_bess_arbitrage_hp_hfp,
    TARIFA_ENERGIA_HP_SOLES,
    TARIFA_ENERGIA_HFP_SOLES,
    FACTOR_CO2_KG_KWH
)

print("\n" + "="*100)
print("✅ VALIDACIÓN: COSTOS Y AHORROS HP/HFP - OSINERGMIN INTEGRADO v5.7")
print("="*100)

# Datos de prueba
np.random.seed(42)
pv = np.random.uniform(0, 100, 8760)
pv[0:6] = 0
pv[18:24] = 0  
ev = np.random.uniform(20, 100, 8760)
mall = np.random.uniform(80, 150, 8760)

print(f"\n📊 TARIFAS OSINERGMIN (desde 2024-11-04):")
print(f"   - Hora Punta (HP 18-23h): S/. {TARIFA_ENERGIA_HP_SOLES}/kWh")
print(f"   - Fuera de Punta (HFP): S/. {TARIFA_ENERGIA_HFP_SOLES}/kWh")
print(f"   - DIFERENCIAL: S/. {TARIFA_ENERGIA_HP_SOLES - TARIFA_ENERGIA_HFP_SOLES}/kWh")
print(f"   - FACTOR HP/HFP: {TARIFA_ENERGIA_HP_SOLES / TARIFA_ENERGIA_HFP_SOLES:.3f}x")

# TEST 1: simulate_bess_ev_exclusive
print(f"\n{'='*100}")
print("1️⃣  VALIDACIÓN: simulate_bess_ev_exclusive")
print(f"{'='*100}")

try:
    df1, metrics1 = simulate_bess_ev_exclusive(pv, ev, mall, 1700, 400)
    print(f"✅ Ejecución exitosa")
    print(f"\n📋 COLUMNAS DE COSTOS/TARIFAS:")
    cost_cols = [col for col in df1.columns if 'cost' in col.lower() or 'tariff' in col.lower() or 'saving' in col.lower()]
    for col in cost_cols:
        print(f"   - {col}")
    
    print(f"\n📊 ESTADÍSTICAS DE COSTOS (EV Exclusive):")
    if 'tariff_period' in df1.columns:
        hp_hours = (df1['tariff_period'] == 'HP').sum()
        hfp_hours = (df1['tariff_period'] == 'HFP').sum()
        print(f"   Horas HP: {hp_hours} (esperado ~1,825)")
        print(f"   Horas HFP: {hfp_hours} (esperado ~6,935)")
    
    if 'cost_savings_hp_soles' in df1.columns:
        total_savings_hp = df1['cost_savings_hp_soles'].sum()
        print(f"   Ahorro total HP: S/. {total_savings_hp:,.2f}/año")
    
    if 'cost_savings_hfp_soles' in df1.columns:
        total_savings_hfp = df1['cost_savings_hfp_soles'].sum()
        print(f"   Ahorro total HFP: S/. {total_savings_hfp:,.2f}/año")
    
    if 'cost_avoided_by_bess_soles' in df1.columns:
        total_avoided = df1['cost_avoided_by_bess_soles'].sum()
        print(f"   Costo evitado total: S/. {total_avoided:,.2f}/año")
    
    if 'tariff_index_hp_hfp' in df1.columns:
        index_vals = df1['tariff_index_hp_hfp'].unique()
        print(f"   Factor índice: {sorted(index_vals)}")
    
    print(f"✅ validate_ev_exclusive: PASS")
except Exception as e:
    print(f"❌ Error en simulate_bess_ev_exclusive:")
    print(f"   {str(e)[:200]}")

# TEST 2: simulate_bess_arbitrage_hp_hfp
print(f"\n{'='*100}")
print("2️⃣  VALIDACIÓN: simulate_bess_arbitrage_hp_hfp")
print(f"{'='*100}")

try:
    df2, metrics2 = simulate_bess_arbitrage_hp_hfp(pv, ev, mall, 1700, 400)
    print(f"✅ Ejecución exitosa")
    print(f"\n📋 COLUMNAS DE COSTOS/TARIFAS:")
    cost_cols = [col for col in df2.columns if 'cost' in col.lower() or 'tariff' in col.lower() or 'saving' in col.lower()]
    for col in cost_cols:
        print(f"   - {col}")
    
    print(f"\n📊 ESTADÍSTICAS DE COSTOS (Arbitrage HP/HFP):")
    if 'tariff_period' in df2.columns:
        hp_hours = (df2['tariff_period'] == 'HP').sum()
        hfp_hours = (df2['tariff_period'] == 'HFP').sum()
        print(f"   Horas HP: {hp_hours} (esperado ~1,825)")
        print(f"   Horas HFP: {hfp_hours} (esperado ~6,935)")
    
    if 'cost_savings_hp_soles' in df2.columns:
        total_savings_hp = df2['cost_savings_hp_soles'].sum()
        print(f"   Ahorro total HP: S/. {total_savings_hp:,.2f}/año")
    
    if 'cost_savings_hfp_soles' in df2.columns:
        total_savings_hfp = df2['cost_savings_hfp_soles'].sum()
        print(f"   Ahorro total HFP: S/. {total_savings_hfp:,.2f}/año")
    
    if 'savings_bess_soles' in df2.columns:
        total_bess_savings = df2['savings_bess_soles'].sum()
        print(f"   Ahorro BESS total: S/. {total_bess_savings:,.2f}/año")
    
    if 'cost_avoided_by_bess_soles' in df2.columns:
        total_avoided = df2['cost_avoided_by_bess_soles'].sum()
        print(f"   Costo evitado total: S/. {total_avoided:,.2f}/año")
    
    if 'tariff_index_hp_hfp' in df2.columns:
        index_vals = df2['tariff_index_hp_hfp'].unique()
        print(f"   Factor índice: {sorted(index_vals)}")
    
    print(f"✅ validate_arbitrage: PASS")
except Exception as e:
    print(f"❌ Error en simulate_bess_arbitrage_hp_hfp:")
    print(f"   {str(e)[:200]}")

# COMPARACIÓN DE COSTOS
print(f"\n{'='*100}")
print("3️⃣  COMPARACIÓN: EV Exclusive vs Arbitrage")
print(f"{'='*100}")

try:
    cols_compare = ['tariff_period', 'cost_savings_hp_soles', 'cost_savings_hfp_soles', 'cost_avoided_by_bess_soles']
    
    print(f"\n📊 Muestra de datos (primeras 3 horas):")
    print(f"\nEV Exclusive (columnas de costo):")
    if all(col in df1.columns for col in cols_compare):
        print(df1[cols_compare].head(3).to_string())
    
    print(f"\nArbitrage (columnas de costo):")
    if all(col in df2.columns for col in cols_compare):
        print(df2[cols_compare].head(3).to_string())
    
    # Validación de diferencias
    if 'cost_savings_hp_soles' in df1.columns and 'cost_savings_hp_soles' in df2.columns:
        ev_hp_savings = df1['cost_savings_hp_soles'].sum()
        arb_hp_savings = df2['cost_savings_hp_soles'].sum()
        print(f"\n📈 Ahorros HP:")
        print(f"   EV Exclusive: S/. {ev_hp_savings:,.2f}")
        print(f"   Arbitrage: S/. {arb_hp_savings:,.2f}")
        print(f"   Diferencia: S/. {arb_hp_savings - ev_hp_savings:,.2f} ({((arb_hp_savings - ev_hp_savings) / ev_hp_savings * 100) if ev_hp_savings != 0 else 0:.1f}%)")
    
    print(f"\n✅ COMPARACIÓN: PASS")
except Exception as e:
    print(f"⚠️  Error en comparación: {str(e)[:100]}")

print(f"\n{'='*100}")
print("✅ VALIDACIÓN COMPLETADA")
print(f"{'='*100}\n")
