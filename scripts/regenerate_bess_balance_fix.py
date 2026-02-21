#!/usr/bin/env python3
"""
Regenerar bess_ano_2024.csv con balance energético CORREGIDO (v5.9.1)

PROBLEMA IDENTIFICADO:
- Balance energético tenía discrepancia de 167,966 kWh
- Causa: Doble aplicación de eficiencia en bess_energy_stored_hourly_kwh y bess_energy_delivered_hourly_kwh
- Solución: Usar pv_to_bess y (bess_to_ev + bess_to_mall) directamente sin multiplicar por eficiencia

CORRECCIÓN APLICADA EN bess.py:
- Línea ~1402: bess_energy_stored_hourly_kwh = pv_to_bess (ya incluye eficiencia)
- Línea ~1403: bess_energy_delivered_hourly_kwh = bess_to_ev + bess_to_mall (ya incluye eficiencia)

Ejecución:
  python scripts/regenerate_bess_balance_fix.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Agregar proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
import math

def regenerate_bess_dataset():
    """Regenerar BESS dataset usando datos existentes con lógica corregida."""
    
    print("=" * 80)
    print("REGENERANDO: bess_ano_2024.csv con BALANCE ENERGÉTICO CORREGIDO v5.9.1")
    print("=" * 80)
    print()
    
    # Rutas
    bess_output = Path("data/oe2/bess/bess_ano_2024.csv")
    mall_csv = Path("data/oe2/demandamallkwh/demandamallhorakwh.csv")
    pv_csv = Path("data/oe2/Generacionsolar/pv_generation_citylearn2024.csv")
    
    # Cargar datos
    print("[CARGANDO] Datos de entrada...")
    
    # PV
    if pv_csv.exists():
        df_pv = pd.read_csv(pv_csv)
        if 'pv_kwh' in df_pv.columns:
            pv_kwh = df_pv['pv_kwh'].values
        elif 'pv_kw' in df_pv.columns:
            pv_kwh = df_pv['pv_kw'].values
        elif 'pv_w' in df_pv.columns:
            pv_kwh = df_pv['pv_w'].values / 1000
        else:
            # Primera columna numérica
            pv_kwh = df_pv.select_dtypes(include=['number']).iloc[:, 0].values / 1000
        print(f"  ✓ PV: {pv_kwh.sum():,.0f} kWh/año")
    else:
        print(f"  ✗ ERROR: PV no encontrado en {pv_csv}")
        return
    
    # MALL
    if mall_csv.exists():
        df_mall = pd.read_csv(mall_csv)
        mall_kwh = df_mall['mall_demand_kwh'].values
        print(f"  ✓ MALL: {mall_kwh.sum():,.0f} kWh/año")
    else:
        print(f"  ✗ ERROR: MALL no encontrado")
        return
    
    # EV (demanada horaria promedio constante)
    ev_total_year = 408282  # kWh/año
    ev_kwh = np.ones(len(pv_kwh)) * (ev_total_year / len(pv_kwh))
    print(f"  ✓ EV: {ev_kwh.sum():,.0f} kWh/año")
    
    # Validar longitud
    if len(pv_kwh) != len(mall_kwh) or len(pv_kwh) != len(ev_kwh):
        print(f"  ✗ ERROR: Longitudes inconsistentes: PV={len(pv_kwh)}, MALL={len(mall_kwh)}, EV={len(ev_kwh)}")
        return
    
    n_hours = len(pv_kwh)
    print(f"  ✓ Horas: {n_hours} (1 año = 8760 h)")
    print()
    
    # Importar función
    from src.dimensionamiento.oe2.disenobess.bess import simulate_bess_ev_exclusive
    
    # Ejecutar simulación
    print("[SIMULANDO] BESS con lógica de 6 fases + eficiencia corregida...")
    df_bess, metrics = simulate_bess_ev_exclusive(
        pv_kwh=pv_kwh,
        ev_kwh=ev_kwh,
        mall_kwh=mall_kwh,
        capacity_kwh=2000.0,
        power_kw=400.0,
        efficiency=0.95,
        soc_min=0.20,
        soc_max=1.00,
        closing_hour=22,
        year=2024
    )
    
    # Guardar
    bess_output.parent.mkdir(parents=True, exist_ok=True)
    df_bess.to_csv(bess_output, index=False)
    print(f"  ✓ Dataset guardado: {bess_output}")
    print(f"    - Filas: {len(df_bess):,}")
    print(f"    - Columnas: {len(df_bess.columns)}")
    print()
    
    # Validar balance energético
    print("[VALIDACIÓN] Balance Energético...")
    carga = df_bess['bess_energy_stored_hourly_kwh'].sum()
    descarga = df_bess['bess_energy_delivered_hourly_kwh'].sum()
    soc_inicial = df_bess['soc_percent'].iloc[0]
    soc_final = df_bess['soc_percent'].iloc[-1]
    capacity = 2000.0
    
    print(f"  SOC Inicial: {soc_inicial:.1f}%")
    print(f"  SOC Final: {soc_final:.1f}%")
    print(f"  Energía cargada: {carga:,.0f} kWh")
    print(f"  Energía descargada: {descarga:,.0f} kWh")
    print()
    
    # Validación de balance
    esperado_en_bess = (soc_final / 100) * capacity  # Energía final en BESS
    inicial_en_bess = (soc_inicial / 100) * capacity  # Energía inicial en BESS
    balance_teorico = carga - descarga
    balance_esperado = esperado_en_bess - inicial_en_bess
    error = abs(balance_teorico - balance_esperado)
    
    print(f"  Balance teórico (cargado - descargado): {balance_teorico:,.0f} kWh")
    print(f"  Balance esperado (SOC final - inicial): {balance_esperado:,.0f} kWh")
    print(f"  Error: {error:,.0f} kWh")
    
    if error < 100:
        print(f"  ✅ VALIDACIÓN EXITOSA - Balance cuadra (error < 100 kWh)")
    else:
        print(f"  ⚠️  ADVERTENCIA - Error de balance > 100 kWh")
    
    print()
    print("=" * 80)
    print(f"✅ Dataset BESS v5.9.1 regenerado correctamente")
    print("=" * 80)


if __name__ == '__main__':
    regenerate_bess_dataset()
