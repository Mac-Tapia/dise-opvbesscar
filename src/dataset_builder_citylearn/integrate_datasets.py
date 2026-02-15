#!/usr/bin/env python3
"""
Integrador completo de datasets OE2: Solar + Chargers + BESS.

Proposito: Crear dataset solar enriquecido con 5 nuevas columnas de energia
basadas en la distribucion de energia entre BESS, EV, Mall y Red.

Columnas agregadas:
1. energia_suministrada_al_bess_kwh      - Solar -> BESS
2. energia_suministrada_al_ev_kwh        - Solar + BESS -> EV
3. energia_suministrada_al_mall_kwh      - Solar + BESS -> Mall
4. energia_suministrada_a_red_kwh        - Solar excedente -> Red
5. reduccion_indirecta_co2_kg_total      - TODA solar × 0.4521 kg CO₂/kWh
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from pathlib import Path

# Constante: Factor CO₂ sistema termico Iquitos
FACTOR_CO2_KG_KWH = 0.4521

def integrate_datasets(solar_path: str | Path = "data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv",
                       chargers_path: str | Path = "data/oe2/chargers/chargers_ev_ano_2024_v3.csv",
                       bess_path: str | Path = "data/oe2/bess/bess_ano_2024.csv",
                       output_path: str | Path = "data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv") -> pd.DataFrame:
    """
    Integra los 3 datasets (Solar, Chargers, BESS) y enriquece el de Solar.
    
    Args:
        solar_path: Ruta a dataset solar
        chargers_path: Ruta a dataset chargers
        bess_path: Ruta a dataset BESS
        output_path: Ruta para guardar dataset enriquecido
        
    Returns:
        DataFrame solar enriquecido con 5 columnas nuevas
    """
    
    print("\n" + "="*100)
    print("🔗 INTEGRADOR COMPLETO OE2: Solar + Chargers + BESS")
    print("="*100)
    
    # Cargar datasets
    print(f"\n1️⃣  Cargando datasets...")
    
    solar_path = Path(solar_path)
    chargers_path = Path(chargers_path)
    bess_path = Path(bess_path)
    
    df_solar = pd.read_csv(solar_path, index_col=0, parse_dates=True)
    df_chargers = pd.read_csv(chargers_path, index_col=0, parse_dates=True)
    df_bess = pd.read_csv(bess_path, index_col=0, parse_dates=True)
    
    print(f"   [OK] Solar: {len(df_solar):,} filas × {len(df_solar.columns)} cols")
    print(f"   [OK] Chargers: {len(df_chargers):,} filas × {len(df_chargers.columns)} cols")
    print(f"   [OK] BESS: {len(df_bess):,} filas × {len(df_bess.columns)} cols")
    
    # Verificar alineacion
    if len(df_solar) != len(df_chargers) or len(df_solar) != len(df_bess):
        raise ValueError(f"Longitudes no coinciden")
    
    # Extraer columnas de energia
    print(f"\n2️⃣  Extrayendo energia...")
    
    pv_generation = df_solar['energia_kwh'].values
    pv_to_bess = df_bess['pv_to_bess'].values if 'pv_to_bess' in df_bess else np.zeros(len(df_solar))
    pv_to_ev = df_bess['pv_to_ev'].values if 'pv_to_ev' in df_bess else np.zeros(len(df_solar))
    bess_to_ev = df_bess['bess_to_ev'].values if 'bess_to_ev' in df_bess else np.zeros(len(df_solar))
    pv_to_mall = df_bess['pv_to_mall'].values if 'pv_to_mall' in df_bess else np.zeros(len(df_solar))
    bess_to_mall = df_bess['bess_to_mall'].values if 'bess_to_mall' in df_bess else np.zeros(len(df_solar))
    pv_curtailed = df_bess['pv_curtailed'].values if 'pv_curtailed' in df_bess else np.zeros(len(df_solar))
    
    print(f"   [OK] PV generacion: {pv_generation.sum():,.0f} kWh/ano")
    
    # Calcular 5 columnas nuevas
    print(f"\n3️⃣  Calculando 5 columnas nuevas...")
    
    energia_bess = pv_to_bess
    energia_ev = pv_to_ev + bess_to_ev
    energia_mall = pv_to_mall + bess_to_mall
    energia_red = pv_curtailed
    reduccion_co2 = pv_generation * FACTOR_CO2_KG_KWH
    
    df_solar['energia_suministrada_al_bess_kwh'] = energia_bess
    df_solar['energia_suministrada_al_ev_kwh'] = energia_ev
    df_solar['energia_suministrada_al_mall_kwh'] = energia_mall
    df_solar['energia_suministrada_a_red_kwh'] = energia_red
    df_solar['reduccion_indirecta_co2_kg_total'] = reduccion_co2
    
    # Guardar
    print(f"\n4️⃣  Guardando dataset enriquecido...")
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_solar.to_csv(output_path)
    
    print(f"   [OK] Guardado: {output_path}")
    print(f"   +- Filas: {len(df_solar):,}")
    print(f"   +- Columnas: {len(df_solar.columns)} (+5 nuevas)")
    
    # Estadisticas
    print(f"\n[GRAPH] BALANCE ENERGETICO:")
    print(f"   - BESS: {energia_bess.sum():>15,.0f} kWh")
    print(f"   - EV: {energia_ev.sum():>15,.0f} kWh")
    print(f"   - Mall: {energia_mall.sum():>15,.0f} kWh")
    print(f"   - Red: {energia_red.sum():>15,.0f} kWh")
    print(f"   - CO₂ reducido: {reduccion_co2.sum():>15,.0f} kg")
    
    print(f"\n" + "="*100 + "\n")
    
    return df_solar


if __name__ == "__main__":
    integrate_datasets()
