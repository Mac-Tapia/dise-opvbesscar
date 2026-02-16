#!/usr/bin/env python3
"""
Enriquecedor de dataset CHARGERS con reduccion directa de CO₂.

Agrega 5 columnas nuevas al dataset de cargadores:
1. cantidad_motos_cargadas - Numero de motos cargando por hora (0-26)
2. cantidad_mototaxis_cargadas - Numero de mototaxis cargando por hora (0-8)
3. reduccion_directa_co2_motos_kg - CO₂ evitado gasolina -> electrico
4. reduccion_directa_co2_mototaxis_kg - CO₂ evitado diesel -> electrico
5. reduccion_directa_co2_total_kg - CO₂ total evitado

METODOLOGIA:
- MOTOS: 2.86 L/100km gasolina × 2.31 kg CO₂/L = 6.08 kg CO₂ por carga
- MOTOTAXIS: 3.6 L/100km diesel × 2.68 kg CO₂/L = 14.28 kg CO₂ por carga

Fuentes: IPCC 2006, IEA, ICCT
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path

# Constantes de reduccion DIRECTA de CO₂ (combustible -> electrico)
MOTO_CO2_POR_CARGA = 6.08              # kg CO₂/carga (gasolina -> EV)
MOTOTAXI_CO2_POR_CARGA = 14.28         # kg CO₂/carga (diesel -> EV)

def enrich_chargers_dataset(chargers_path: str | Path = "data/oe2/chargers/chargers_ev_ano_2024_v3.csv",
                             output_path: str | Path = "data/oe2/chargers/chargers_ev_ano_2024_enriched_v2.csv"):
    """
    Enriquece dataset CHARGERS con 5 columnas de CO₂ directo.
    
    Args:
        chargers_path: Ruta al dataset original
        output_path: Ruta para guardar dataset enriquecido
        
    Returns:
        DataFrame enriquecido
    """
    
    print("\n" + "="*110)
    print("🔌 ENRIQUECEDOR DE DATASET CHARGERS - REDUCCION DIRECTA CO₂")
    print("="*110)
    
    # Cargar dataset original
    chargers_path = Path(chargers_path)
    if not chargers_path.exists():
        raise FileNotFoundError(f"Dataset no encontrado: {chargers_path}")
    
    df = pd.read_csv(chargers_path, index_col=0, parse_dates=True)
    
    print(f"\n[OK] Dataset cargado: {chargers_path.name}")
    print(f"   Filas: {len(df):,} (8,760 horas)")
    print(f"   Columnas originales: {len(df.columns)}")
    
    # Calcular cantidad de vehiculos cargados
    moto_cols = [col for col in df.columns if '_charging_power_kw' in col and int(col.split('_')[1]) < 30]
    taxi_cols = [col for col in df.columns if '_charging_power_kw' in col and int(col.split('_')[1]) >= 30]
    
    df['cantidad_motos_cargadas'] = (df[moto_cols] > 0).sum(axis=1)
    df['cantidad_mototaxis_cargadas'] = (df[taxi_cols] > 0).sum(axis=1)
    
    # Calcular reduccion de CO₂
    df['reduccion_directa_co2_motos_kg'] = df['cantidad_motos_cargadas'] * MOTO_CO2_POR_CARGA
    df['reduccion_directa_co2_mototaxis_kg'] = df['cantidad_mototaxis_cargadas'] * MOTOTAXI_CO2_POR_CARGA
    df['reduccion_directa_co2_total_kg'] = df['reduccion_directa_co2_motos_kg'] + df['reduccion_directa_co2_mototaxis_kg']
    
    # Guardar
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path)
    
    print(f"\n[OK] Dataset enriquecido guardado:")
    print(f"   Ruta: {output_path}")
    print(f"   Filas: {len(df):,}")
    print(f"   Columnas: {len(df.columns)} (+5 nuevas)")
    
    # Estadisticas
    co2_motos = df['reduccion_directa_co2_motos_kg'].sum()
    co2_taxis = df['reduccion_directa_co2_mototaxis_kg'].sum()
    co2_total = df['reduccion_directa_co2_total_kg'].sum()
    
    print(f"\n[GRAPH] REDUCCION CO₂ ANUAL:")
    print(f"   - Motos: {co2_motos:>15,.0f} kg ({co2_motos/1000:.1f} ton)")
    print(f"   - Mototaxis: {co2_taxis:>15,.0f} kg ({co2_taxis/1000:.1f} ton)")
    print(f"   - TOTAL: {co2_total:>15,.0f} kg ({co2_total/1000:.1f} ton)")
    
    print(f"\n" + "="*110 + "\n")
    
    return df


if __name__ == "__main__":
    enrich_chargers_dataset()
