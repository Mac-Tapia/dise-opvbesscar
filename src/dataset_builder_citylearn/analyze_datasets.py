#!/usr/bin/env python3
"""
Analisis consolidado de datasets enriquecidos para CityLearn v2.

Proporciona estadisticas completas de los 3 datasets (Solar, Chargers, BESS)
despues de enriquecimiento.
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path


def analyze_solar_dataset(solar_path: str | Path = "data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv"):
    """Analiza dataset solar enriquecido."""
    
    print("\n" + "="*110)
    print("[GRAPH] ANALISIS DATASET SOLAR ENRIQUECIDO")
    print("="*110)
    
    solar_path = Path(solar_path)
    df = pd.read_csv(solar_path, index_col=0, parse_dates=True)
    
    cols_nuevas = ['energia_suministrada_al_bess_kwh', 'energia_suministrada_al_ev_kwh',
                    'energia_suministrada_al_mall_kwh', 'energia_suministrada_a_red_kwh',
                    'reduccion_indirecta_co2_kg_total']
    
    print(f"\n[OK] Dataset: {solar_path.name}")
    print(f"   Filas: {len(df):,} | Columnas: {len(df.columns)} | 5 nuevas")
    
    print(f"\n[CHART] ESTADISTICAS 5 COLUMNAS NUEVAS:")
    for col in cols_nuevas:
        if col in df.columns:
            total = df[col].sum()
            prom = df[col].mean()
            maximo = df[col].max()
            print(f"   {col}:")
            print(f"      Total: {total:>15,.0f} | Prom: {prom:>10.2f} | Max: {maximo:>10.1f}")
    
    print("\n" + "="*110)


def analyze_chargers_dataset(chargers_path: str | Path = "data/oe2/chargers/chargers_ev_ano_2024_enriched_v2.csv"):
    """Analiza dataset chargers enriquecido."""
    
    print("\n" + "="*110)
    print("[GRAPH] ANALISIS DATASET CHARGERS ENRIQUECIDO")
    print("="*110)
    
    chargers_path = Path(chargers_path)
    df = pd.read_csv(chargers_path, index_col=0, parse_dates=True)
    
    cols_nuevas = ['cantidad_motos_cargadas', 'cantidad_mototaxis_cargadas',
                    'reduccion_directa_co2_motos_kg', 'reduccion_directa_co2_mototaxis_kg',
                    'reduccion_directa_co2_total_kg']
    
    print(f"\n[OK] Dataset: {chargers_path.name}")
    print(f"   Filas: {len(df):,} | Columnas: {len(df.columns)} | 5 nuevas")
    
    print(f"\n[CHART] ESTADISTICAS 5 COLUMNAS NUEVAS:")
    for col in cols_nuevas:
        if col in df.columns:
            total = df[col].sum()
            prom = df[col].mean()
            maximo = df[col].max()
            print(f"   {col}:")
            print(f"      Total: {total:>15,.0f} | Prom: {prom:>10.2f} | Max: {maximo:>10.1f}")
    
    print("\n" + "="*110)


def analyze_all_datasets():
    """Ejecuta analisis de todos los datasets enriquecidos."""
    
    print("\n" + "="*110)
    print("🔗 ANALISIS CONSOLIDADO - DATASETS ENRIQUECIDOS PARA CityLearn v2")
    print("="*110)
    
    try:
        analyze_solar_dataset()
    except FileNotFoundError:
        print("[!]  Dataset solar no encontrado")
    
    try:
        analyze_chargers_dataset()
    except FileNotFoundError:
        print("[!]  Dataset chargers no encontrado")
    
    print("\n" + "="*110)
    print("[OK] ANALISIS COMPLETO")
    print("="*110 + "\n")


if __name__ == "__main__":
    analyze_all_datasets()
