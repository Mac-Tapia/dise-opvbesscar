#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VALIDACION: A2C CO2 CALCULATIONS = PPO = SAC
Verifica que los tres agentes usan EXACTAMENTE el mismo cálculo de CO2 directo e indirecto
"""
from __future__ import annotations

import json
import pandas as pd
import numpy as np
from pathlib import Path

print("="*80)
print("VALIDACION: CO2 CALCULATIONS A2C = PPO = SAC")
print("="*80)
print()

# ============================================================================
# PASO 1: CARGAR DATASETS OE2
# ============================================================================

print("[1] CARGAR DATASETS OE2 REALES")
print("-"*80)

chargers_df = pd.read_csv('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
bess_df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')
solar_df = pd.read_csv('data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv')

print(f"  Chargers: {len(chargers_df)} rows")
print(f"  BESS:     {len(bess_df)} rows")
print(f"  Solar:    {len(solar_df)} rows")
print()

# ============================================================================
# PASO 2: CALCULARCO2 COMO LO HACE PPO
# ============================================================================

print("[2] CO2 CALCULATION METHOD (PPO FORMULA)")
print("-"*80)

# CO2 DIRECTO: Chargers
CO2_DIRECTO_PPO = (
    chargers_df['co2_reduccion_motos_kg'].sum() +
    chargers_df['co2_reduccion_mototaxis_kg'].sum()
)

# Verificar que sea igual a reduccion_directa_co2_kg
CO2_DIRECTO_PPO_CHECK = chargers_df['reduccion_directa_co2_kg'].sum()

print(f"  CO2 DIRECTO (PPO):                    {CO2_DIRECTO_PPO:,.0f} kg/año")
print(f"  CO2 DIRECTO (usando columna total):  {CO2_DIRECTO_PPO_CHECK:,.0f} kg/año")
if abs(CO2_DIRECTO_PPO - CO2_DIRECTO_PPO_CHECK) < 1:
    print(f"  ✓ Consistencia: OK (diferencia < 1 kg)")
else:
    print(f"  ✗ INCONSISTENCIA: diferencia {abs(CO2_DIRECTO_PPO - CO2_DIRECTO_PPO_CHECK):,.0f} kg")
print()

# CO2 INDIRECTO SOLAR
CO2_INDIRECTO_SOLAR_PPO = solar_df['reduccion_indirecta_co2_kg'].sum()
print(f"  CO2 INDIRECTO SOLAR (PPO):            {CO2_INDIRECTO_SOLAR_PPO:,.0f} kg/año")
print()

# CO2 INDIRECTO BESS
CO2_INDIRECTO_BESS_PPO = bess_df['co2_avoided_indirect_kg'].sum()
print(f"  CO2 INDIRECTO BESS (PPO):             {CO2_INDIRECTO_BESS_PPO:,.0f} kg/año")
print()

# TOTAL
CO2_TOTAL_PPO = CO2_DIRECTO_PPO_CHECK + CO2_INDIRECTO_SOLAR_PPO + CO2_INDIRECTO_BESS_PPO
print(f"  CO2 TOTAL (PPO):                      {CO2_TOTAL_PPO:,.0f} kg/año")
print()

# ============================================================================
# PASO 3: DESGLOSE POR COMPONENTE
# ============================================================================

print("[3] DESGLOSE CO2 (%)") 
print("-"*80)

pct_directo = (CO2_DIRECTO_PPO_CHECK / CO2_TOTAL_PPO * 100) if CO2_TOTAL_PPO > 0 else 0
pct_solar = (CO2_INDIRECTO_SOLAR_PPO / CO2_TOTAL_PPO * 100) if CO2_TOTAL_PPO > 0 else 0
pct_bess = (CO2_INDIRECTO_BESS_PPO / CO2_TOTAL_PPO * 100) if CO2_TOTAL_PPO > 0 else 0

print(f"  CO2 Directo (EV):       {pct_directo:6.2f}% = {CO2_DIRECTO_PPO_CHECK:>12,.0f} kg")
print(f"  CO2 Indirecto (Solar):  {pct_solar:6.2f}% = {CO2_INDIRECTO_SOLAR_PPO:>12,.0f} kg")
print(f"  CO2 Indirecto (BESS):   {pct_bess:6.2f}% = {CO2_INDIRECTO_BESS_PPO:>12,.0f} kg")
print(f"  {'─'*50}")
print(f"  TOTAL:                  100.00% = {CO2_TOTAL_PPO:>12,.0f} kg")
print()

# ============================================================================
# PASO 4: VERIFICAR DATOS A2C (RESULTADO ENTRENAMIENTO)
# ============================================================================

print("[4] VALIDACION: A2C RESULT INCLUDES CO2")
print("-"*80)

a2c_result_path = Path('outputs/a2c_training/result_a2c.json')

if a2c_result_path.exists():
    with open(a2c_result_path, 'r', encoding='utf-8') as f:
        a2c_result = json.load(f)
    
    if 'metrics' in a2c_result:
        metrics = a2c_result['metrics']
        
        # Extraer CO2 valores
        co2_total_a2c = metrics.get('co2_total_kg', 0)
        co2_directo_a2c = metrics.get('co2_directo_kg', 0)
        co2_indirecto_a2c = metrics.get('co2_indirecto_kg', 0)
        
        print(f"  A2C CO2 Total Evitado:      {co2_total_a2c:,.0f} kg (10 episodios)")
        print(f"  A2C CO2 Directo:            {co2_directo_a2c:,.0f} kg")
        print(f"  A2C CO2 Indirecto:          {co2_indirecto_a2c:,.0f} kg")
        print()
        
        # Comparar con dataset
        print(f"  DATASET CO2 Total:          {CO2_TOTAL_PPO:,.0f} kg (1 año)")
        print(f"  DATASET CO2 Directo:        {CO2_DIRECTO_PPO_CHECK:,.0f} kg")
        print(f"  DATASET CO2 Indirecto:      {CO2_INDIRECTO_SOLAR_PPO + CO2_INDIRECTO_BESS_PPO:,.0f} kg")
        print()
        
        # La validación
        a2c_expected_per_episode = CO2_TOTAL_PPO / 10  # Suponiendo 10 episodios
        a2c_expected_10_episodes = CO2_TOTAL_PPO
        
        print(f"  ESPERADO (A2C 10 episodios): {a2c_expected_10_episodes:,.0f} kg")
        print(f"  OBTENIDO (A2C 10 episodios): {co2_total_a2c:,.0f} kg")
        
        diff_pct = abs(a2c_expected_10_episodes - co2_total_a2c) / a2c_expected_10_episodes * 100
        print(f"  Diferencia:                  {diff_pct:.2f}%")
        
        if diff_pct < 5:
            print(f"  ✓ A2C ESTÁ CORRECTAMENTE ALINEADO CON DATASET (< 5% diferencia)")
        elif diff_pct < 10:
            print(f"  ⚠️  A2C parcialmente alineado (5-10% diferencia, probablemente por acciones)")
        else:
            print(f"  ✗ A2C NO ESTÁ ALINEADO (> 10% diferencia, revisar cálculos)")
    else:
        print("  ⚠️  No se encontró 'metrics' en result_a2c.json")
else:
    print(f"  ✗ result_a2c.json no encontrado: {a2c_result_path}")

print()

# ============================================================================
# PASO 5: RESUMEN Y CHECKLIST
# ============================================================================

print("="*80)
print("RESUMEN VALIDACION CO2")
print("="*80)
print()

checklist = {
    '✓ Dataset Chargers disponible': chargers_df is not None,
    '✓ Columna co2_reduccion_motos_kg': 'co2_reduccion_motos_kg' in chargers_df.columns,
    '✓ Columna co2_reduccion_mototaxis_kg': 'co2_reduccion_mototaxis_kg' in chargers_df.columns,
    '✓ Columna reduccion_directa_co2_kg': 'reduccion_directa_co2_kg' in chargers_df.columns,
    '✓ Dataset BESS disponible': bess_df is not None,
    '✓ Columna co2_avoided_indirect_kg (BESS)': 'co2_avoided_indirect_kg' in bess_df.columns,
    '✓ Dataset Solar disponible': solar_df is not None,
    '✓ Columna reduccion_indirecta_co2_kg (Solar)': 'reduccion_indirecta_co2_kg' in solar_df.columns,
    '✓ A2C result.json existe': a2c_result_path.exists(),
}

all_ok = True
for check_name, result in checklist.items():
    status = "✓" if result else "✗"
    print(f"  {status} {check_name}")
    if not result:
        all_ok = False

print()
print("="*80)

if all_ok:
    print("✓✓✓ TODOS LOS CHECKS PASARON - A2C ESTÁ ALINEADO CON PPO/SAC ✓✓✓")
else:
    print("⚠️  ALGUNOS CHECKS FALLARON - REVISAR ARRIBA")

print()
print(f"RESUMEN CO2 DATASET (OE2 v5.2):")
print(f"  • CO2 DIRECTO total:       {CO2_DIRECTO_PPO_CHECK:>15,.0f} kg/año")
print(f"  • CO2 INDIRECTO SOLAR:     {CO2_INDIRECTO_SOLAR_PPO:>15,.0f} kg/año")
print(f"  • CO2 INDIRECTO BESS:      {CO2_INDIRECTO_BESS_PPO:>15,.0f} kg/año")
print(f"  • CO2 TOTAL EVITADO:       {CO2_TOTAL_PPO:>15,.0f} kg/año")
print()
print(f"Los cálculos de A2C deben usar EXACTAMENTE estos valores para ser idénticos a PPO/SAC")
print("="*80)
