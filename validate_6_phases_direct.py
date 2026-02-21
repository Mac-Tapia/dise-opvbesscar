"""
VALIDACION DIRECTA DE 6 FASES EN BESS.PY
Importa desde bess.py y valida que las 6 fases se ejecuten sin conflictos.
"""
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Agregar root al path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

# Importar desde bess.py DIRECTAMENTE
from src.dimensionamiento.oe2.disenobess.bess import (
    load_pv_generation,
    load_mall_demand_real,
    load_ev_demand,
    simulate_bess_ev_exclusive,
)

def main():
    print("\n" + "="*80)
    print("VALIDACION DIRECTA DE 6 FASES - IMPORTADO DESDE BESS.PY")
    print("="*80)

    # Rutas
    root = Path(__file__).parent
    oe2_dir = root / "data" / "oe2"
    
    pv_path = oe2_dir / "Generacionsolar" / "pv_generation_citylearn2024.csv"
    ev_path = oe2_dir / "chargers" / "chargers_ev_ano_2024_v3.csv"
    mall_path = oe2_dir / "demandamallkwh" / "demandamallhorakwh.csv"

    print("\n[1] CARGANDO DATOS...")
    print("-" * 80)
    print(f"PV:   {pv_path}")
    print(f"EV:   {ev_path}")
    print(f"MALL: {mall_path}")

    # Cargar datos
    df_pv = load_pv_generation(pv_path)
    df_mall = load_mall_demand_real(mall_path, year=2024)
    df_ev = load_ev_demand(ev_path, year=2024)

    pv_kwh = df_pv['pv_kwh'].values
    mall_kwh = df_mall['mall_kwh'].values
    ev_kwh = df_ev['ev_kwh'].values

    print(f"✓ PV: {len(pv_kwh)} horas, {pv_kwh.sum():,.0f} kWh/año")
    print(f"✓ EV: {len(ev_kwh)} horas, {ev_kwh.sum():,.0f} kWh/año")
    print(f"✓ MALL: {len(mall_kwh)} horas, {mall_kwh.sum():,.0f} kWh/año")

    # Simular con 6 fases
    print("\n[2] SIMULANDO BESS CON 6 FASES...")
    print("-" * 80)
    df_sim, metrics = simulate_bess_ev_exclusive(
        pv_kwh=pv_kwh,
        ev_kwh=ev_kwh,
        mall_kwh=mall_kwh,
        capacity_kwh=2000,
        power_kw=400,
        efficiency=0.95,
        soc_min=0.20,
        soc_max=1.00,
        closing_hour=22,
        year=2024
    )

    print("✓ Simulación completada")
    print(f"Dataset: {len(df_sim)} filas, {len(df_sim.columns)} columnas")
    
    # Mostrar columnas disponibles
    print("\nCOLUMNAS DISPONIBLES EN DATASET:")
    for i, col in enumerate(df_sim.columns, 1):
        print(f"  {i:2d}. {col}")

    # Validar 6 fases
    print("\n[3] VALIDANDO 6 FASES...")
    print("-" * 80)

    # Análisis por fase (aproximado)
    fase1_mask = (df_sim.index.hour >= 6) & (df_sim.index.hour < 9)
    fase2_mask = (df_sim.index.hour >= 9) & (df_sim['soc_percent'] < 99) & (df_sim['pv_to_bess_kwh'] > 0)
    fase3_mask = (df_sim.index.hour >= 9) & (df_sim['soc_percent'] >= 99) & (df_sim['pv_to_bess_kwh'] == 0)
    fase4_mask = (df_sim['pv_kwh'] < df_sim['mall_kwh']) & (df_sim['mall_kwh'] > 1900) & (df_sim['bess_to_mall_kwh'] > 0)
    fase5_mask = (df_sim['bess_to_ev_kwh'] > 0)
    fase6_mask = ((df_sim.index.hour >= 22) | (df_sim.index.hour < 6))

    print(f"FASE 1 (Carga primero, 6h-9h):     {fase1_mask.sum():>5} horas ({fase1_mask.sum()/8760*100:>5.1f}%)")
    print(f"FASE 2 (EV + BESS paralelo, <99%): {fase2_mask.sum():>5} horas ({fase2_mask.sum()/8760*100:>5.1f}%)")
    print(f"FASE 3 (Holding a 100%):           {fase3_mask.sum():>5} horas ({fase3_mask.sum()/8760*100:>5.1f}%)")
    print(f"FASE 4 (Peak shaving PV<MALL):     {fase4_mask.sum():>5} horas ({fase4_mask.sum()/8760*100:>5.1f}%)")
    print(f"FASE 5 (EV con descarga):          {fase5_mask.sum():>5} horas ({fase5_mask.sum()/8760*100:>5.1f}%)")
    print(f"FASE 6 (IDLE 22h-6h):              {fase6_mask.sum():>5} horas ({fase6_mask.sum()/8760*100:>5.1f}%)")

    # Validar conflictos (simultánea carga + descarga)
    print("\n[4] VALIDANDO CONFLICTOS (Carga XOR Descarga)...")
    print("-" * 80)

    with_bess_to_ev = (df_sim['bess_to_ev_kwh'] > 0).sum()
    with_bess_to_mall = (df_sim['bess_to_mall_kwh'] > 0).sum()
    with_pv_to_bess = (df_sim['pv_to_bess_kwh'] > 0).sum()
    
    # Conflictos: horas donde SIMULTÁNEAMENTE:
    # - Se carga BESS (pv_to_bess > 0) Y
    # - Se descarga BESS (bess_to_ev > 0 O bess_to_mall > 0)
    desc_total = df_sim['bess_to_ev_kwh'] + df_sim['bess_to_mall_kwh']
    simultan_conflicts = ((df_sim['pv_to_bess_kwh'] > 0) & (desc_total > 0)).sum()
    
    print(f"Horas con carga BESS (pv_to_bess > 0):   {with_pv_to_bess:>5}")
    print(f"Horas con descarga a EV (bess_to_ev > 0): {with_bess_to_ev:>5}")
    print(f"Horas con descarga MALL (bess_to_mall > 0): {with_bess_to_mall:>5}")
    print(f"Horas con AMBOS carga X descarga:       {simultan_conflicts:>5} (DEBE SER 0)")
    
    if simultan_conflicts == 0:
        print("✅ VALIDACION OK: No hay conflictos de carga/descarga simultánea")
    else:
        print(f"❌ ERROR: {simultan_conflicts} horas con conflictos")

    # Balance energético
    print("\n[5] BALANCE ENERGETICO ANUAL...")
    print("-" * 80)

    cargada = df_sim['pv_to_bess_kwh'].sum()
    descargada = (df_sim['bess_to_ev_kwh'] + df_sim['bess_to_mall_kwh']).sum()
    
    print(f"Energía cargada a BESS (pv_to_bess):   {cargada:>12,.0f} kWh")
    print(f"Energía descargada desde BESS:         {descargada:>12,.0f} kWh")
    print(f"Diferencia:                            {abs(cargada - descargada):>12,.0f} kWh")
    print(f"Ratio descarga/carga:                  {descargada/max(cargada, 1):>12,.2f}")

    # Metricas
    print("\n[6] METRICAS BESS...")
    print("-" * 80)
    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            if key.endswith('_kwh') or key.endswith('_kw'):
                print(f"{key:.<50} {value:>15,.0f}")
            elif key.endswith('_percent') or key.endswith('_%'):
                print(f"{key:.<50} {value:>15,.1f}%")
            else:
                print(f"{key:.<50} {value:>15,.2f}")

    print("\n" + "="*80)
    print("VALIDACION COMPLETADA")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
