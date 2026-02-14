#!/usr/bin/env python3
"""
Integrador de datasets OE2 para CityLearn v2
Agrega 5 columnas nuevas al dataset SOLAR integrando BESS + Chargers + Mall

Columnas nuevas:
1. energia_suministrada_bess_kwh - Energía PV → BESS
2. energia_suministrada_ev_kwh - Energía total → EV (PV + BESS + Red)
3. energia_suministrada_mall_kwh - Energía total → Mall (PV + BESS + Red)
4. energia_suministrada_red_publica_kwh - Energía exportada a red pública
5. reduccion_indirecta_co2_suministro_kwh - CO2 reducido cuando BESS reemplaza diesel
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd  # type: ignore[import]

# Constantes
FACTOR_CO2_KG_KWH = 0.4521  # kg CO2/kWh (sistema térmico Iquitos - diesel)


def load_datasets() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Carga los 3 datasets principales (Solar, BESS, Chargers)"""
    
    print("\n" + "="*90)
    print("📂 CARGANDO DATASETS OE2")
    print("="*90)
    
    # Solar
    solar_path = Path("data/oe2/Generacionsolar/pv_generation_citylearn2024.csv")
    if not solar_path.exists():
        raise FileNotFoundError(f"Dataset solar no encontrado: {solar_path}")
    df_solar = pd.read_csv(solar_path)
    df_solar['datetime'] = pd.to_datetime(df_solar['datetime'])
    print(f"\n✅ Solar: {solar_path.name}")
    print(f"   Filas: {len(df_solar):,} | Columnas: {len(df_solar.columns)}")
    
    # BESS
    bess_path = Path("data/oe2/bess/bess_ano_2024.csv")
    if not bess_path.exists():
        raise FileNotFoundError(f"Dataset BESS no encontrado: {bess_path}")
    df_bess = pd.read_csv(bess_path)
    df_bess['datetime'] = pd.to_datetime(df_bess['datetime'])
    print(f"\n✅ BESS: {bess_path.name}")
    print(f"   Filas: {len(df_bess):,} | Columnas: {len(df_bess.columns)}")
    
    # Chargers
    chargers_path = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
    if not chargers_path.exists():
        raise FileNotFoundError(f"Dataset chargers no encontrado: {chargers_path}")
    df_chargers = pd.read_csv(chargers_path)
    if 'datetime' in df_chargers.columns:
        df_chargers['datetime'] = pd.to_datetime(df_chargers['datetime'])
    print(f"\n✅ Chargers: {chargers_path.name}")
    print(f"   Filas: {len(df_chargers):,} | Columnas: {len(df_chargers.columns)}")
    
    print(f"\n✓ Todos los datasets cargados exitosamente")
    
    return df_solar, df_bess, df_chargers


def extract_ev_demand(df_chargers: pd.DataFrame) -> np.ndarray:
    """Extrae demanda total de EV del dataset de chargers"""
    
    # Buscar columnas de demanda de sockets (formato: socket_XXX_*_power_kw o similar)
    socket_cols = [col for col in df_chargers.columns 
                   if 'socket_' in col and 'power_kw' in col.lower()]
    
    if not socket_cols:
        # Si no hay columnas socket, buscar columna de demanda total
        total_cols = [col for col in df_chargers.columns 
                      if 'total' in col.lower() and ('kwh' in col.lower() or 'power' in col.lower())]
        if total_cols:
            return df_chargers[total_cols[0]].values
        # Si nada, retornar ceros
        return np.zeros(len(df_chargers))
    
    # Sumar todas las columnas de sockets
    ev_demand = df_chargers[socket_cols].sum(axis=1).values
    
    return ev_demand


def create_integrated_dataset(
    df_solar: pd.DataFrame,
    df_bess: pd.DataFrame,
    df_chargers: pd.DataFrame
) -> pd.DataFrame:
    """
    Crea dataset integrado con 5 columnas nuevas:
    1. energia_suministrada_bess_kwh
    2. energia_suministrada_ev_kwh  
    3. energia_suministrada_mall_kwh
    4. energia_suministrada_red_publica_kwh
    5. reduccion_indirecta_co2_suministro_kwh
    """
    
    print("\n" + "="*90)
    print("🔗 CONSTRUYENDO DATASET INTEGRADO")
    print("="*90)
    
    # Copiar dataset solar
    df_integrated = df_solar.copy()
    
    # ===================================================================
    # 1. ENERGÍA SUMINISTRADA AL BESS
    # ===================================================================
    print("\n1️⃣  Calculando: energia_suministrada_bess_kwh")
    
    # El BESS recibe energía de:
    # - PV directo excedente
    # - Red pública (si aplica)
    
    pv_to_bess = df_bess['pv_to_bess_kwh'].values if 'pv_to_bess_kwh' in df_bess.columns else np.zeros(len(df_bess))
    grid_to_bess = df_bess['grid_to_bess_kwh'].values if 'grid_to_bess_kwh' in df_bess.columns else np.zeros(len(df_bess))
    
    energia_suministrada_bess = pv_to_bess + grid_to_bess
    
    df_integrated['energia_suministrada_bess_kwh'] = energia_suministrada_bess
    print(f"   Total anual: {energia_suministrada_bess.sum():,.0f} kWh")
    
    # ===================================================================
    # 2. ENERGÍA SUMINISTRADA AL EV
    # ===================================================================
    print("\n2️⃣  Calculando: energia_suministrada_ev_kwh")
    
    # EV recibe de:
    # - PV directo
    # - BESS
    # - Red pública
    
    pv_to_ev = df_bess['pv_to_ev_kwh'].values if 'pv_to_ev_kwh' in df_bess.columns else np.zeros(len(df_bess))
    bess_to_ev = df_bess['bess_to_ev_kwh'].values if 'bess_to_ev_kwh' in df_bess.columns else np.zeros(len(df_bess))
    grid_to_ev = df_bess['grid_to_ev_kwh'].values if 'grid_to_ev_kwh' in df_bess.columns else np.zeros(len(df_bess))
    
    energia_suministrada_ev = pv_to_ev + bess_to_ev + grid_to_ev
    
    df_integrated['energia_suministrada_ev_kwh'] = energia_suministrada_ev
    print(f"   Total anual: {energia_suministrada_ev.sum():,.0f} kWh")
    print(f"   Desglose:")
    print(f"   ├─ PV directo: {pv_to_ev.sum():,.0f} kWh ({100*pv_to_ev.sum()/energia_suministrada_ev.sum():.1f}%)")
    print(f"   ├─ BESS: {bess_to_ev.sum():,.0f} kWh ({100*bess_to_ev.sum()/energia_suministrada_ev.sum():.1f}%)")
    print(f"   └─ Red pública: {grid_to_ev.sum():,.0f} kWh ({100*grid_to_ev.sum()/energia_suministrada_ev.sum():.1f}%)")
    
    # ===================================================================
    # 3. ENERGÍA SUMINISTRADA AL MALL
    # ===================================================================
    print("\n3️⃣  Calculando: energia_suministrada_mall_kwh")
    
    # Mall recibe de:
    # - PV directo
    # - BESS
    # - Red pública
    
    pv_to_mall = df_bess['pv_to_mall_kwh'].values if 'pv_to_mall_kwh' in df_bess.columns else np.zeros(len(df_bess))
    bess_to_mall = df_bess['bess_to_mall_kwh'].values if 'bess_to_mall_kwh' in df_bess.columns else np.zeros(len(df_bess))
    grid_to_mall = df_bess['grid_to_mall_kwh'].values if 'grid_to_mall_kwh' in df_bess.columns else np.zeros(len(df_bess))
    
    energia_suministrada_mall = pv_to_mall + bess_to_mall + grid_to_mall
    
    df_integrated['energia_suministrada_mall_kwh'] = energia_suministrada_mall
    print(f"   Total anual: {energia_suministrada_mall.sum():,.0f} kWh")
    print(f"   Desglose:")
    print(f"   ├─ PV directo: {pv_to_mall.sum():,.0f} kWh ({100*pv_to_mall.sum()/energia_suministrada_mall.sum():.1f}%)")
    print(f"   ├─ BESS: {bess_to_mall.sum():,.0f} kWh ({100*bess_to_mall.sum()/energia_suministrada_mall.sum():.1f}%)")
    print(f"   └─ Red pública: {grid_to_mall.sum():,.0f} kWh ({100*grid_to_mall.sum()/energia_suministrada_mall.sum():.1f}%)")
    
    # ===================================================================
    # 4. ENERGÍA SUMINISTRADA A RED PÚBLICA
    # ===================================================================
    print("\n4️⃣  Calculando: energia_suministrada_red_publica_kwh")
    
    # PV excedente que se exporta a la red (curtido o exceso)
    pv_curtailed = df_bess['pv_curtailed_kwh'].values if 'pv_curtailed_kwh' in df_bess.columns else np.zeros(len(df_bess))
    
    energia_suministrada_red = pv_curtailed
    
    df_integrated['energia_suministrada_red_publica_kwh'] = energia_suministrada_red
    print(f"   Total anual: {energia_suministrada_red.sum():,.0f} kWh (exceso PV)")
    
    # ===================================================================
    # 5. REDUCCIÓN INDIRECTA CO2 - Solo cuando BESS reemplaza diesel
    # ===================================================================
    print("\n5️⃣  Calculando: reduccion_indirecta_co2_suministro_kwh")
    
    # La reducción de CO2 ocurre cuando BESS desplaza energía de la red térmica (diesel)
    # Esto sucede en el intervalo donde el BESS está descargando y reemplaza lo que 
    # de otro modo vendría de red
    
    # Energía total que BESS descarga
    bess_discharge = df_bess['bess_discharge_kwh'].values if 'bess_discharge_kwh' in df_bess.columns else np.zeros(len(df_bess))
    
    # La descarga de BESS desplaza importación de red (diesel)
    # Factor CO2: 0.4521 kg CO2/kWh
    co2_reduccion_bess = bess_discharge * FACTOR_CO2_KG_KWH
    
    df_integrated['reduccion_indirecta_co2_suministro_kwh'] = co2_reduccion_bess
    print(f"   Total anual: {co2_reduccion_bess.sum():,.0f} kg CO2")
    print(f"   Total anual: {co2_reduccion_bess.sum()/1000:,.1f} ton CO2")
    print(f"   Factor CO2: {FACTOR_CO2_KG_KWH} kg CO2/kWh (diesel Iquitos)")
    print(f"   Lógica: Cada kWh que BESS descarga reemplaza generación térmica de red")
    
    # ===================================================================
    # VALIDACIONES
    # ===================================================================
    print("\n" + "="*90)
    print("✅ VALIDACIONES")
    print("="*90)
    
    # Validación 1: 8,760 horas
    val1 = len(df_integrated) == 8760
    print(f"\n{'✓' if val1 else '✗'} Temporal: {len(df_integrated)} filas (debe ser 8,760)")
    
    # Validación 2: Sin valores nulos
    nulls = df_integrated[['energia_suministrada_bess_kwh', 
                          'energia_suministrada_ev_kwh',
                          'energia_suministrada_mall_kwh',
                          'energia_suministrada_red_publica_kwh',
                          'reduccion_indirecta_co2_suministro_kwh']].isnull().sum().sum()
    val2 = nulls == 0
    print(f"{'✓' if val2 else '✗'} Integridad: {nulls} valores nulos")
    
    # Validación 3: Valores positivos
    val3_bess = (df_integrated['energia_suministrada_bess_kwh'] >= 0).all()
    val3_ev = (df_integrated['energia_suministrada_ev_kwh'] >= 0).all()
    val3_mall = (df_integrated['energia_suministrada_mall_kwh'] >= 0).all()
    val3_red = (df_integrated['energia_suministrada_red_publica_kwh'] >= 0).all()
    val3_co2 = (df_integrated['reduccion_indirecta_co2_suministro_kwh'] >= 0).all()
    val3 = val3_bess and val3_ev and val3_mall and val3_red and val3_co2
    print(f"{'✓' if val3 else '✗'} Rangos: Todos valores ≥ 0")
    
    # Validación 4: Balance energético (suma PV aproximada)
    total_pv = df_solar['energia_kwh'].sum() if 'energia_kwh' in df_solar.columns else 0
    bess_salida = bess_discharge.sum()
    
    print(f"\n{'✓' if total_pv > 0 else '✗'} Balance PV: {total_pv:,.0f} kWh (source)")
    print(f"{'✓' if bess_salida > 0 else '✗'} BESS salida: {bess_salida:,.0f} kWh (stored & released)")
    
    all_ok = val1 and val2 and val3
    print(f"\n{'✅' if all_ok else '⚠️'} Resultado: {'TODAS VALIDACIONES PASADAS' if all_ok else 'REVISAR'}")
    
    return df_integrated


def save_integrated_dataset(df_integrated: pd.DataFrame, output_path: str = "data/oe2/Generacionsolar/pv_generation_citylearn2024_integrated.csv") -> str:
    """Guarda el dataset integrado"""
    
    print("\n" + "="*90)
    print("💾 GUARDANDO DATASET INTEGRADO")
    print("="*90)
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Guardar CSV
    df_integrated.to_csv(output_path, index=False)
    
    file_size_kb = output_path.stat().st_size / 1024
    
    print(f"\n✅ Dataset guardado: {output_path.name}")
    print(f"   Ruta: {output_path}")
    print(f"   Tamaño: {file_size_kb:.1f} KB")
    print(f"   Filas: {len(df_integrated):,}")
    print(f"   Columnas: {len(df_integrated.columns)}")
    
    print(f"\n📋 COLUMNAS NUEVAS AGREGADAS:")
    new_cols = [
        'energia_suministrada_bess_kwh',
        'energia_suministrada_ev_kwh',
        'energia_suministrada_mall_kwh',
        'energia_suministrada_red_publica_kwh',
        'reduccion_indirecta_co2_suministro_kwh'
    ]
    for i, col in enumerate(new_cols, 1):
        print(f"   {i}. {col}")
    
    return str(output_path)


def main():
    """Función principal"""
    
    try:
        # Cargar datasets
        df_solar, df_bess, df_chargers = load_datasets()
        
        # Crear dataset integrado
        df_integrated = create_integrated_dataset(df_solar, df_bess, df_chargers)
        
        # Guardar dataset
        output_path = save_integrated_dataset(df_integrated)
        
        print("\n" + "="*90)
        print("✅ PROCESO COMPLETADO EXITOSAMENTE")
        print("="*90)
        print(f"\nDataset integrado listo para CityLearn v2:")
        print(f"  {output_path}")
        print(f"\nColumnas originales: {len(df_solar.columns)}")
        print(f"Columnas finales: {len(df_integrated.columns)}")
        print(f"Nuevas columnas: 5")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
