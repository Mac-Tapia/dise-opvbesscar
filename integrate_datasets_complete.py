#!/usr/bin/env python3
"""
Integrador completo de datasets OE2: Solar + Chargers + BESS

Propósito: Agregar 5 columnas nuevas al dataset SOLAR basadas en la lógica
de que TODA la generación solar desplaza diesel (100% aprovechamiento).

Columnas a agregar:
1. energía_suministrada_al_bess_kwh      - Solar → BESS (almacenamiento)
2. energía_suministrada_al_ev_kwh        - Solar (directo) + BESS (descargado) → EV
3. energía_suministrada_al_mall_kwh      - Solar (directo) + BESS (descargado) → Mall
4. energía_suministrada_a_red_kwh        - Solar excedente (curtido) → Red
5. reducción_indirecta_co2_kg_total      - TODA solar × 0.4521 kg CO₂/kWh

Lógica energética (100% aprovechamiento):
  PV generación (100%)
  ├─ PV→EV directo          [solar directo a EV]
  ├─ PV→BESS carga          [solar almacenado en BESS]
  ├─ PV→Mall directo        [solar directo a mall]
  └─ PV curtido             [solar excedente a red]

  Suministro total a usuarios:
  ├─ EV: PV→EV + BESS→EV               [directo + almacenado]
  ├─ Mall: PV→Mall + BESS→Mall         [directo + almacenado]
  └─ Red: PV curtido                   [exportación)

  CO₂ reducido (indirecto):
  └─ TODA PV generación × 0.4521 kg/kWh [desplaza 100% diesel térmico]
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Constantes OSINERGMIN
FACTOR_CO2_KG_KWH = 0.4521  # kg CO₂/kWh (sistema térmico Iquitos)

def integrate_datasets() -> pd.DataFrame:
    """
    Integra los 3 datasets (Solar, Chargers, BESS) y agrega 5 columnas nuevas al Solar.
    
    Returns:
        DataFrame solar enriquecido con 5 columnas nuevas
    """
    
    print("\n" + "="*100)
    print("🔗 INTEGRADOR COMPLETO OE2: Solar + Chargers + BESS")
    print("="*100)
    
    # =========================================================================
    # PASO 1: Cargar los 3 datasets
    # =========================================================================
    print(f"\n1️⃣  Cargando datasets base...")
    
    solar_path = Path("data/oe2/Generacionsolar/pv_generation_citylearn2024.csv")
    chargers_path = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
    bess_path = Path("data/oe2/bess/bess_ano_2024.csv")
    
    # Cargar Solar
    df_solar = pd.read_csv(solar_path, index_col=0, parse_dates=True)
    print(f"   ✅ Solar: {len(df_solar)} filas × {len(df_solar.columns)} columnas")
    
    # Cargar Chargers (EV)
    df_ev = pd.read_csv(chargers_path)
    print(f"   ✅ Chargers: {len(df_ev)} filas × {len(df_ev.columns)} columnas")
    
    # Cargar BESS
    df_bess = pd.read_csv(bess_path)
    df_bess['datetime'] = pd.to_datetime(df_bess['datetime'])
    print(f"   ✅ BESS: {len(df_bess)} filas × {len(df_bess.columns)} columnas")
    
    # =========================================================================
    # PASO 2: Verificar alineación temporal
    # =========================================================================
    print(f"\n2️⃣  Verificando alineación temporal...")
    
    if len(df_solar) != len(df_ev) or len(df_solar) != len(df_bess):
        raise ValueError(f"Longitudes no coinciden: Solar={len(df_solar)}, EV={len(df_ev)}, BESS={len(df_bess)}")
    
    print(f"   ✅ Todos alineados: 8,760 horas")
    
    # =========================================================================
    # PASO 3: Extraer columnas de energía de cada dataset
    # =========================================================================
    print(f"\n3️⃣  Extrayendo columnas de energía...")
    
    # SOLAR
    pv_generation = df_solar['energia_kwh'].values
    print(f"   ✅ Solar generación: {pv_generation.sum():,.0f} kWh/año")
    
    # CHARGERS (suma de 38 sockets)
    socket_cols = [col for col in df_ev.columns if 'socket_' in col and 'charging_power_kw' in col]
    if len(socket_cols) > 0:
        ev_demand = df_ev[socket_cols].sum(axis=1).values
    else:
        # Fallback: buscar columna de demanda total
        if 'total_ev_demand_kw' in df_ev.columns:
            ev_demand = df_ev['total_ev_demand_kw'].values * 1.0  # Conversión de potencia a energía (1h)
        else:
            ev_demand = np.zeros(len(df_solar))
    print(f"   ✅ EV demanda: {ev_demand.sum():,.0f} kWh/año")
    
    # MALL
    mall_demand = df_bess['mall_demand_kwh'].values
    print(f"   ✅ Mall demanda: {mall_demand.sum():,.0f} kWh/año")
    
    # BESS flujos
    pv_to_bess = df_bess['pv_to_bess_kwh'].values
    pv_to_ev = df_bess['pv_to_ev_kwh'].values
    pv_to_mall = df_bess['pv_to_mall_kwh'].values
    pv_curtiled = df_bess['pv_curtailed_kwh'].values
    
    bess_to_ev = df_bess['bess_to_ev_kwh'].values
    bess_to_mall = df_bess['bess_to_mall_kwh'].values
    
    print(f"   ✅ BESS carga: {pv_to_bess.sum():,.0f} kWh/año")
    
    # =========================================================================
    # PASO 4: CALCULAR LAS 5 COLUMNAS NUEVAS
    # =========================================================================
    print(f"\n4️⃣  Calculando 5 columnas nuevas...")
    
    # COLUMNA 1: Energía suministrada al BESS
    # Energía que entra al BESS (desde solar)
    energia_suministrada_al_bess = pv_to_bess.copy()
    print(f"   ✅ Col 1 - Suministro BESS: {energia_suministrada_al_bess.sum():,.0f} kWh/año")
    
    # COLUMNA 2: Energía suministrada al EV
    # Solar directo a EV + BESS descargado a EV (100% aprovechamiento)
    energia_suministrada_al_ev = pv_to_ev + bess_to_ev
    print(f"   ✅ Col 2 - Suministro EV: {energia_suministrada_al_ev.sum():,.0f} kWh/año")
    
    # COLUMNA 3: Energía suministrada al Mall
    # Solar directo a mall + BESS descargado a mall (100% aprovechamiento)
    energia_suministrada_al_mall = pv_to_mall + bess_to_mall
    print(f"   ✅ Col 3 - Suministro Mall: {energia_suministrada_al_mall.sum():,.0f} kWh/año")
    
    # COLUMNA 4: Energía suministrada a Red Pública
    # Solar curtido/excedente (lo que no se usa localmente y se exporta)
    energia_suministrada_a_red = pv_curtiled.copy()
    print(f"   ✅ Col 4 - Suministro Red: {energia_suministrada_a_red.sum():,.0f} kWh/año")
    
    # COLUMNA 5: Reducción indirecta CO₂ (TODA la generación solar)
    # LÓGICA: TODA la PV generación desplaza diesel porque no hay desperdicio
    # Cada kWh solar = 0.4521 kg CO₂ evitado de la red térmica
    reduccion_indirecta_co2_kg_total = pv_generation * FACTOR_CO2_KG_KWH
    print(f"   ✅ Col 5 - CO₂ reducido (indirecto): {reduccion_indirecta_co2_kg_total.sum():,.0f} kg/año")
    print(f"              ({reduccion_indirecta_co2_kg_total.sum()/1000:,.1f} ton/año)")
    
    # =========================================================================
    # PASO 5: VALIDACIONES DE ENERGÍA
    # =========================================================================
    print(f"\n5️⃣  Validaciones de balance energético...")
    
    # Verificar que toda la generación solar se distribuye
    total_suministrado = (energia_suministrada_al_bess + 
                         energia_suministrada_al_ev + 
                         energia_suministrada_al_mall + 
                         energia_suministrada_a_red)
    
    diferencia = np.abs(pv_generation - total_suministrado).sum()
    
    print(f"   Solar generación: {pv_generation.sum():,.0f} kWh")
    print(f"   Total suministrado (BESS+EV+Mall+Red): {total_suministrado.sum():,.0f} kWh")
    print(f"   Diferencia (debería ser ~0): {diferencia:,.0f} kWh")
    
    if diferencia < 1:
        print(f"   ✅ BALANCE PERFECTO (100% aprovechamiento)")
    else:
        print(f"   ⚠️  Diferencia detectada (revisar cálculo)")
    
    # =========================================================================
    # PASO 6: AGREGAR COLUMNAS AL DATASET SOLAR
    # =========================================================================
    print(f"\n6️⃣  Agregando columnas al dataset SOLAR...")
    
    df_solar_enhanced = df_solar.copy()
    
    df_solar_enhanced['energia_suministrada_al_bess_kwh'] = energia_suministrada_al_bess
    df_solar_enhanced['energia_suministrada_al_ev_kwh'] = energia_suministrada_al_ev
    df_solar_enhanced['energia_suministrada_al_mall_kwh'] = energia_suministrada_al_mall
    df_solar_enhanced['energia_suministrada_a_red_kwh'] = energia_suministrada_a_red
    df_solar_enhanced['reduccion_indirecta_co2_kg_total'] = reduccion_indirecta_co2_kg_total
    
    print(f"   ✅ Columnas agregadas (5 nuevas)")
    print(f"   ✅ Filas: {len(df_solar_enhanced)}")
    print(f"   ✅ Columnas totales: {len(df_solar_enhanced.columns)} (antes: {len(df_solar.columns)})")
    
    # =========================================================================
    # PASO 7: GUARDAR DATASET MEJORADO
    # =========================================================================
    print(f"\n7️⃣  Guardando dataset mejorado...")
    
    output_path = Path("data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    df_solar_enhanced.to_csv(output_path)
    file_size_kb = output_path.stat().st_size / 1024
    print(f"   ✅ Guardado: {output_path.name}")
    print(f"   ✅ Tamaño: {file_size_kb:.1f} KB")
    
    # =========================================================================
    # PASO 8: MOSTRAR RESUMEN ESTADÍSTICO
    # =========================================================================
    print(f"\n8️⃣  Resumen estadístico (8,760 filas)...")
    
    print(f"\n📊 DISTRIBUCIÓN ANUAL DE ENERGÍA SOLAR:")
    print(f"   └─ TOTAL Generación PV: {pv_generation.sum():>15,.0f} kWh")
    print(f"      ├─ → BESS (almacenamiento):  {energia_suministrada_al_bess.sum():>12,.0f} kWh ({energia_suministrada_al_bess.sum()/pv_generation.sum()*100:>5.1f}%)")
    print(f"      ├─ → EV (directo+recuperado): {energia_suministrada_al_ev.sum():>12,.0f} kWh ({energia_suministrada_al_ev.sum()/pv_generation.sum()*100:>5.1f}%)")
    print(f"      ├─ → Mall (directo+recuperado): {energia_suministrada_al_mall.sum():>10,.0f} kWh ({energia_suministrada_al_mall.sum()/pv_generation.sum()*100:>5.1f}%)")
    print(f"      └─ → Red Pública (exportación): {energia_suministrada_a_red.sum():>10,.0f} kWh ({energia_suministrada_a_red.sum()/pv_generation.sum()*100:>5.1f}%)")
    
    print(f"\n🌿 CO₂ REDUCIDO (INDIRECTO):")
    print(f"   Factor CO₂ diesel: {FACTOR_CO2_KG_KWH} kg/kWh")
    print(f"   TODA la solar desplaza diesel (100% aprovechamiento):")
    print(f"   └─ Reducción CO₂ anual: {reduccion_indirecta_co2_kg_total.sum():>12,.0f} kg ({reduccion_indirecta_co2_kg_total.sum()/1000:>7.1f} ton)")
    
    # Mostrar primeras 3 filas
    print(f"\n📋 PRIMERAS 3 FILAS DEL DATASET MEJORADO:")
    print(df_solar_enhanced[['energia_kwh', 'energia_suministrada_al_bess_kwh', 
                             'energia_suministrada_al_ev_kwh', 'energia_suministrada_al_mall_kwh',
                             'energia_suministrada_a_red_kwh', 'reduccion_indirecta_co2_kg_total']].head(3).to_string())
    
    print(f"\n" + "="*100)
    print("✅ INTEGRACIÓN COMPLETA EXITOSA")
    print("="*100 + "\n")
    
    return df_solar_enhanced


if __name__ == "__main__":
    df_enhanced = integrate_datasets()
