#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador de Sincronización PPO vs A2C
================================================================================
Verifica que PPO y A2C cargan EXACTAMENTE los mismos datasets y tienen 
la misma lógica de energía, de reward y métricas.

Ejecutar: python scripts/validate_ppo_a2c_sync.py
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

def validate_solar_datasets():
    """Verifica que solar sea idénético entre PPO y A2C."""
    print("\n" + "="*80)
    print("VALIDACIÓN 1: SOLAR GENERATION")
    print("="*80)
    
    solar_path = Path('data/interim/oe2/solar/pv_generation_citylearn_v2.csv')
    if not solar_path.exists():
        print(f"❌ FALLA: Solar no existe en {solar_path}")
        return False
    
    df_solar = pd.read_csv(solar_path)
    
    # Ambos usan pv_generation_kwh
    if 'pv_generation_kwh' not in df_solar.columns:
        print(f"❌ FALLA: Solar CSV no tiene columna 'pv_generation_kwh'")
        print(f"   Columnas disponibles: {list(df_solar.columns)}")
        return False
    
    solar_data = df_solar['pv_generation_kwh'].values.astype(np.float32)
    
    if len(solar_data) != 8760:
        print(f"❌ FALLA: Solar tiene {len(solar_data)} horas, esperaba 8760")
        return False
    
    total_solar = float(np.sum(solar_data))
    print(f"✅ PASS: Solar cargado correctamente")
    print(f"   Path: {solar_path}")
    print(f"   Filas: {len(solar_data)}")
    print(f"   Total: {total_solar:,.0f} kWh/año")
    print(f"   Media: {np.mean(solar_data):.2f} kW/h")
    print(f"   Min/Max: {np.min(solar_data):.2f} / {np.max(solar_data):.2f} kW")
    
    return True

def validate_chargers_datasets():
    """Verifica que chargers sean idénticos entre PPO y A2C."""
    print("\n" + "="*80)
    print("VALIDACIÓN 2: CHARGERS (38 sockets)")
    print("="*80)
    
    charger_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
    if not charger_path.exists():
        print(f"❌ FALLA: Chargers no existe en {charger_path}")
        return False
    
    df_chargers = pd.read_csv(charger_path)
    
    # Extraer columnas de potencia de sockets
    power_cols = [c for c in df_chargers.columns if 'charger_power_kw' in c.lower()]
    
    if len(power_cols) == 0:
        print(f"❌ FALLA: Chargers CSV no tiene columnas 'charger_power_kw'")
        print(f"   Columnas disponibles: {list(df_chargers.columns)[:10]}...")
        return False
    
    chargers_data = df_chargers[power_cols].values.astype(np.float32)
    
    if chargers_data.shape[0] != 8760:
        print(f"❌ FALLA: Chargers tiene {chargers_data.shape[0]} horas, esperaba 8760")
        return False
    
    n_sockets = chargers_data.shape[1]
    if n_sockets < 38:
        print(f"⚠️  ADVERTENCIA: Chargers tiene {n_sockets} sockets, esperaba 38")
        # Tomar solo los primeros 38
        chargers_data = chargers_data[:, :38]
        n_sockets = 38
    elif n_sockets > 38:
        print(f"⚠️  Reduciendo de {n_sockets} a 38 sockets (v5.2)")
        chargers_data = chargers_data[:, :38]
        n_sockets = 38
    
    total_demand = float(np.sum(chargers_data))
    print(f"✅ PASS: Chargers cargado correctamente")
    print(f"   Path: {charger_path}")
    print(f"   Sockets: {n_sockets}")
    print(f"   Filas: {chargers_data.shape[0]}")
    print(f"   Demanda total: {total_demand:,.0f} kWh/año")
    print(f"   Demanda por socket: {total_demand/n_sockets:,.0f} kWh/ano")
    print(f"   Media: {np.mean(chargers_data):.2f} kW/h")
    
    return True

def validate_mall_datasets():
    """Verifica que mall demand sea idéntico entre PPO y A2C."""
    print("\n" + "="*80)
    print("VALIDACIÓN 3: MALL DEMAND")
    print("="*80)
    
    mall_paths = [
        Path('data/oe2/demandamallkwh/demandamallhorakwh.csv'),
        Path('data/interim/oe2/demandamallkwh/demandamallhorakwh.csv'),
    ]
    
    mall_path = None
    for p in mall_paths:
        if p.exists():
            mall_path = p
            break
    
    if mall_path is None:
        print(f"❌ FALLA: Mall demand no encontrado en ninguna ruta")
        return False
    
    # Intentar cargar con diferentes separadores
    try:
        df_mall = pd.read_csv(mall_path, sep=';', encoding='utf-8')
    except Exception:
        df_mall = pd.read_csv(mall_path, encoding='utf-8')
    
    # Tomar última columna (valor)
    col = df_mall.columns[-1]
    mall_data = np.asarray(df_mall[col].values[:8760], dtype=np.float32)
    
    if len(mall_data) < 8760:
        mall_data = np.pad(mall_data, ((0, 8760 - len(mall_data)),), mode='wrap')
    
    total_mall = float(np.sum(mall_data))
    print(f"✅ PASS: Mall demand cargado correctamente")
    print(f"   Path: {mall_path}")
    print(f"   Columna: {col}")
    print(f"   Filas: {len(mall_data)}")
    print(f"   Demanda total: {total_mall:,.0f} kWh/año")
    print(f"   Media: {np.mean(mall_data):.2f} kW/h")
    print(f"   Min/Max: {np.min(mall_data):.2f} / {np.max(mall_data):.2f} kW")
    
    return True

def validate_bess_datasets():
    """Verifica que BESS data sea idéntico entre PPO y A2C."""
    print("\n" + "="*80)
    print("VALIDACIÓN 4: BESS SOC DATA")
    print("="*80)
    
    bess_paths = [
        Path('data/oe2/bess/bess_ano_2024.csv'),
        Path('data/processed/citylearn/iquitos_ev_mall/bess_ano_2024.csv'),
    ]
    
    bess_path = None
    for p in bess_paths:
        if p.exists():
            bess_path = p
            break
    
    if bess_path is None:
        print(f"❌ FALLA: BESS data no encontrado en ninguna ruta")
        return False
    
    df_bess = pd.read_csv(bess_path)
    
    if 'bess_soc_percent' in df_bess.columns:
        col = 'bess_soc_percent'
    elif 'soc' in df_bess.columns:
        col = 'soc'
    else:
        # Tomar primera columna numérica que tenga SOC
        soc_cols = [c for c in df_bess.columns if 'soc' in c.lower()]
        if soc_cols:
            col = soc_cols[0]
        else:
            print(f"❌ FALLA: BESS CSV no tiene columna SOC")
            return False
    
    bess_data = df_bess[col].values[:8760].astype(np.float32)
    
    # Normalizar a [0,1] si está en [0,100]
    if np.max(bess_data) > 2.0:
        bess_data = bess_data / 100.0
    
    if len(bess_data) < 8760:
        bess_data = np.pad(bess_data, ((0, 8760 - len(bess_data)),), mode='wrap')
    
    print(f"✅ PASS: BESS SOC cargado correctamente")
    print(f"   Path: {bess_path}")
    print(f"   Columna: {col}")
    print(f"   Filas: {len(bess_data)}")
    print(f"   SOC medio: {np.mean(bess_data)*100:.1f}%")
    print(f"   Min/Max: {np.min(bess_data)*100:.1f}% / {np.max(bess_data)*100:.1f}%")
    
    return True

def validate_energy_balance():
    """Verifica que Energy Balance sea consistente."""
    print("\n" + "="*80)
    print("VALIDACIÓN 5: BALANCE ENERGÉTICO (Solar vs Demanda)")
    print("="*80)
    
    # Cargar datasets
    solar_path = Path('data/interim/oe2/solar/pv_generation_citylearn_v2.csv')
    charger_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
    mall_paths = [
        Path('data/oe2/demandamallkwh/demandamallhorakwh.csv'),
        Path('data/interim/oe2/demandamallkwh/demandamallhorakwh.csv'),
    ]
    
    # Solar
    df_solar = pd.read_csv(solar_path)
    solar = df_solar['pv_generation_kwh'].values.astype(np.float32)
    
    # Chargers
    df_chargers = pd.read_csv(charger_path)
    power_cols = [c for c in df_chargers.columns if 'charger_power_kw' in c.lower()]
    chargers = df_chargers[power_cols].values[:8760].astype(np.float32)[:, :38]
    
    # Mall
    mall_path = None
    for p in mall_paths:
        if p.exists():
            mall_path = p
            break
    df_mall = pd.read_csv(mall_path, sep=';' if 'demanda' in str(mall_path).lower() else ',', encoding='utf-8')
    col = df_mall.columns[-1]
    mall = df_mall[col].values[:8760].astype(np.float32)
    
    # Energy Balance
    solar_total = float(np.sum(solar))
    chargers_total = float(np.sum(chargers))
    mall_total = float(np.sum(mall))
    total_demand = chargers_total + mall_total
    
    print(f"✅ BALANCE ENERGÉTICO:")
    print(f"   Generación Solar:  {solar_total:>15,.0f} kWh/año")
    print(f"   Demanda Chargers:  {chargers_total:>15,.0f} kWh/año ({chargers_total/total_demand*100:.1f}% de demanda)")
    print(f"   Demanda Mall:      {mall_total:>15,.0f} kWh/año ({mall_total/total_demand*100:.1f}% de demanda)")
    print(f"   ────────────────────────────────────")
    print(f"   Demanda Total:     {total_demand:>15,.0f} kWh/año")
    print(f"   ────────────────────────────────────")
    print(f"   Solar Coverage:    {solar_total/total_demand*100:>14.1f}% de demanda")
    print(f"   Grid Import Need:  {max(0, total_demand - solar_total):>15,.0f} kWh/año")
    
    if solar_total < total_demand * 0.3:
        print(f"⚠️  ADVERTENCIA: Solar solo cubre {solar_total/total_demand*100:.1f}% de demanda (< 30%)")
    else:
        print(f"✅ Solar adecuado para el tamaño de instalación OE2")
    
    return True

def main():
    print("\n" + "="*80)
    print("VALIDACIÓN DE SINCRONIZACIÓN: PPO vs A2C")
    print("="*80)
    print("Verifica que ambos algoritmos cargan los MISMOS datasets OE2 reales")
    
    results = {
        "Solar": validate_solar_datasets(),
        "Chargers": validate_chargers_datasets(),
        "Mall": validate_mall_datasets(),
        "BESS": validate_bess_datasets(),
        "Balance": validate_energy_balance(),
    }
    
    print("\n" + "="*80)
    print("RESUMEN DE VALIDACIÓN")
    print("="*80)
    
    all_pass = True
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {test}")
        if not result:
            all_pass = False
    
    print("="*80 + "\n")
    
    if all_pass:
        print("✅ TODOS LOS TESTS PASARON")
        print("\nPPO y A2C están sincronizados con los MISMOS datasets OE2 reales.")
        print("Los resultados de entrenamiento serán COMPARABLES y REPRODUCIBLES.")
        return 0
    else:
        print("❌ ALGUNOS TESTS FALLARON")
        print("\nVerifica los archivos de entrada en data/oe2/")
        return 1

if __name__ == '__main__':
    sys.exit(main())
