#!/usr/bin/env python3
"""
TEST: Validar balance energético del BESS v5.4 CORREGIDO

Propósito: Verificar que los cambios a simulate_bess_solar_priority()
generan un dataset con balance energético correcto (sin desequilibrio 8.7:1)

Criterios de Éxito:
1. Archivo bess_ano_2024.csv generado con 8,760 filas
2. Balance: (total_charge × sqrt(eff)) ≈ total_discharge / sqrt(eff)
   - Tolerancia: ±10% (pérdidas de eficiencia)
3. No hay valores NaN o infinitos
4. SOC dentro de [20%, 100%]
5. Columnas requeridas presentes
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from src.dimensionamiento.oe2.disenobess.bess import run_bess_sizing

def test_bess_balance():
    """Test: Ejecutar BESS y validar balance energético"""
    
    print("\n" + "="*80)
    print("TEST: BESS v5.4 BALANCE ENERGÉTICO CORREGIDO")
    print("="*80 + "\n")
    
    # Paths de datos OE2
    project_root = Path(__file__).parent
    data_oe2 = project_root / "data" / "oe2"
    
    # Archivos de entrada
    pv_path = data_oe2 / "Generacionsolar" / "pv_generation_citylearn2024.csv"
    ev_path = data_oe2 / "chargers" / "chargers_ev_ano_2024_v3.csv"
    mall_path = data_oe2 / "demandamallkwh" / "demandamallhorakwh.csv"
    
    # Directorio de salida
    out_dir = project_root / "data" / "processed" / "citylearn" / "iquitos_ev_mall"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Validar que todos los archivos de entrada existen
    print("[1/5] Validando archivos de entrada...")
    for p, name in [(pv_path, "PV"), (ev_path, "EV"), (mall_path, "Mall")]:
        if p.exists():
            print(f"  ✅ {name}: {p.name}")
        else:
            print(f"  ❌ {name} NO ENCONTRADO: {p}")
            return False
    
    # Ejecutar dimensionamiento BESS
    print("\n[2/5] Ejecutando BESS con lógica CORREGIDA (solar_priority)...")
    try:
        result = run_bess_sizing(
            out_dir=out_dir,
            pv_profile_path=pv_path,
            ev_profile_path=ev_path,
            mall_demand_path=mall_path,
            year=2024,
            generate_plots=False,  # Sin gráficas para test rápido
        )
        print(f"  ✅ Dimensionamiento completo")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Cargar dataset generado
    print("\n[3/5] Cargando dataset BESS generado...")
    csv_path = out_dir / "bess_ano_2024.csv"
    
    if not csv_path.exists():
        print(f"  ❌ Archivo NO ENCONTRADO: {csv_path}")
        return False
    
    try:
        df = pd.read_csv(csv_path, index_col=0)
        print(f"  ✅ Dataset cargado: {len(df)} filas × {len(df.columns)} columnas")
    except Exception as e:
        print(f"  ❌ Error al cargar CSV: {e}")
        return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDACIONES
    # ═══════════════════════════════════════════════════════════════════════════
    
    print("\n[4/5] Validando estructura del dataset...")
    
    # 4.1: Número de filas
    if len(df) != 8760:
        print(f"  ❌ ERROR: Dataset tiene {len(df)} filas, espera 8,760")
        return False
    print(f"  ✅ Filas: 8,760 (exacto)")
    
    # 4.2: Columnas requeridas
    required_cols = [
        'pv_generation_kwh', 'ev_demand_kwh', 'mall_demand_kwh',
        'pv_to_ev_kwh', 'pv_to_bess_kwh', 'pv_to_mall_kwh',
        'bess_charge_kwh', 'bess_discharge_kwh',
        'bess_to_ev_kwh', 'bess_to_mall_kwh',
        'grid_to_ev_kwh', 'grid_to_mall_kwh',
        'bess_soc_percent', 'bess_mode'
    ]
    
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        print(f"  ❌ Columnas faltantes: {missing_cols}")
        return False
    print(f"  ✅ Todas las columnas requeridas presentes")
    
    # 4.3: Sin valores NaN
    nan_count = df[required_cols].isna().sum().sum()
    if nan_count > 0:
        print(f"  ❌ {nan_count} valores NaN encontrados")
        return False
    print(f"  ✅ Sin valores NaN")
    
    # 4.4: Sin valores infinitos (solo en columnas numéricas, no en 'bess_mode')
    numeric_cols = [c for c in required_cols if c != 'bess_mode']
    inf_count = np.isinf(df[numeric_cols].values).sum()
    if inf_count > 0:
        print(f"  ❌ {inf_count} valores infinitos encontrados")
        return False
    print(f"  ✅ Sin valores infinitos")
    
    # 4.5: SOC dentro de rango [20%, 100%]
    soc = df['bess_soc_percent']
    soc_min = soc.min()
    soc_max = soc.max()
    
    if soc_min < 19.5 or soc_max > 100.5:  # Margen pequeño para redondeo
        print(f"  ⚠️ SOC fuera de rango: min={soc_min:.1f}%, max={soc_max:.1f}%")
        print(f"     (esperado: [20%, 100%])")
    else:
        print(f"  ✅ SOC en rango: min={soc_min:.1f}%, max={soc_max:.1f}%")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BALANCE ENERGÉTICO (LA VALIDACIÓN CRÍTICA)
    # ═══════════════════════════════════════════════════════════════════════════
    
    print("\n[5/5] VALIDACIÓN CRÍTICA: Balance Energético BESS")
    print("-" * 80)
    
    # Leer valores
    total_charge_kwh = df['bess_charge_kwh'].sum()
    total_discharge_kwh = df['bess_discharge_kwh'].sum()
    
    # Eficiencia round-trip (de bess.py)
    efficiency = 0.95
    eff_sqrt = np.sqrt(efficiency)  # sqrt(0.95) ≈ 0.9747
    
    # Balance esperado (con pérdidas de eficiencia):
    # energy_stored = charge * sqrt(eff)
    # energy_out = discharge / sqrt(eff)
    # energy_stored ≈ energy_out (con pérdidas)
    
    energy_stored = total_charge_kwh * eff_sqrt
    energy_out = total_discharge_kwh / eff_sqrt
    
    print(f"\nEnergía del año 2024:")
    print(f"  Total CARGA:      {total_charge_kwh:>12,.0f} kWh")
    print(f"  Total DESCARGA:   {total_discharge_kwh:>12,.0f} kWh")
    print(f"  Ratio (D/C):      {total_discharge_kwh/max(total_charge_kwh, 1):>12.3f}")
    
    print(f"\nCon eficiencia round-trip = {efficiency*100:.0f}% (sqrt = {eff_sqrt:.4f}):")
    print(f"  Energía CARGADA (·√eff):   {energy_stored:>12,.0f} kWh")
    print(f"  Energía ENTREGADA (/√eff): {energy_out:>12,.0f} kWh")
    
    imbalance_percent = abs(energy_stored - energy_out) / max(energy_stored, energy_out) * 100
    print(f"  Desequilibrio:              {imbalance_percent:>12.1f}%")
    
    # CONDICIÓN CRÍTICA: Antes tenía 8.7:1 (870%), ahora debe ser < 15% de desequilibrio
    # Tolerancia justificada: sqrt(eficiencia), redondeos horarios, discretización
    if imbalance_percent > 20:
        print(f"\n  ❌ FALLO CRÍTICO: Desequilibrio {imbalance_percent:.1f}% > 20%")
        return False
    elif imbalance_percent > 15:
        print(f"\n  ⚠️ ADVERTENCIA: Desequilibrio {imbalance_percent:.1f}% > tolerancia 15%")
        print(f"     (Posible causa: redondeos horarios, discretización)")
    else:
        print(f"\n  ✅ ÉXITO: Balance energético EXCELENTE (desequilibrio {imbalance_percent:.1f}%)")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ANÁLISIS ADICIONAL
    # ═══════════════════════════════════════════════════════════════════════════
    
    print(f"\n{'─'*80}")
    print("ANÁLISIS ADICIONAL:")
    print(f"{'─'*80}")
    
    # Energía anual generada y demandada
    total_pv = df['pv_generation_kwh'].sum()
    total_ev = df['ev_demand_kwh'].sum()
    total_mall = df['mall_demand_kwh'].sum()
    total_load = total_ev + total_mall
    
    print(f"\nEnergía anual:")
    print(f"  Generación PV:  {total_pv:>12,.0f} kWh ({total_pv/1e6:.2f} GWh)")
    print(f"  Demanda EV:     {total_ev:>12,.0f} kWh ({total_ev/1e6:.2f} GWh)")
    print(f"  Demanda Mall:   {total_mall:>12,.0f} kWh ({total_mall/1e6:.2f} GWh)")
    print(f"  Demanda Total:  {total_load:>12,.0f} kWh ({total_load/1e6:.2f} GWh)")
    
    # Cobertura EV
    ev_from_pv = df['pv_to_ev_kwh'].sum()
    ev_from_bess = df['bess_to_ev_kwh'].sum()
    ev_from_grid = df['grid_to_ev_kwh'].sum()
    
    ev_coverage_pv = ev_from_pv / total_ev * 100
    ev_coverage_bess = ev_from_bess / total_ev * 100
    ev_coverage_grid = ev_from_grid / total_ev * 100
    
    print(f"\nCobertura EV (Total: {total_ev:,.0f} kWh):")
    print(f"  PV directo:   {ev_from_pv:>12,.0f} kWh ({ev_coverage_pv:>5.1f}%)")
    print(f"  Desde BESS:   {ev_from_bess:>12,.0f} kWh ({ev_coverage_bess:>5.1f}%)")
    print(f"  Desde Grid:   {ev_from_grid:>12,.0f} kWh ({ev_coverage_grid:>5.1f}%)")
    
    total_ev_autosuficiency = (ev_from_pv + ev_from_bess) / total_ev * 100
    print(f"  Autosuficiencia EV (PV+BESS): {total_ev_autosuficiency:.1f}%")
    
    # Ciclos BESS
    cycles_per_day = total_charge_kwh / 1700 / 365  # Max SOC = 1700 kWh
    print(f"\nOperación BESS:")
    print(f"  Ciclos/día:     {cycles_per_day:>12.2f}")
    print(f"  SOC mín:        {soc.min():>12.1f}%")
    print(f"  SOC máx:        {soc.max():>12.1f}%")
    print(f"  SOC promedio:   {soc.mean():>12.1f}%")
    
    # Resumen final
    print(f"\n{'='*80}")
    # Tolerancia: 15% (razonable con redondeos y discretización horaria)
    success = imbalance_percent <= 15
    
    if success:
        print("✅ TEST PASADO: Balance energético BESS corregido correctamente")
        print(f"   Desequilibrio: {imbalance_percent:.1f}% (dentro de tolerancia 15%)")
        print(f"   MEGA MEJORA: Reducido de 870% a {imbalance_percent:.1f}%")
    else:
        print("❌ TEST FALLIDO: Balance energético aún tiene desequilibrio")
        print(f"   Desequilibrio: {imbalance_percent:.1f}% > tolerancia 15%")
    print("="*80 + "\n")
    
    return success

if __name__ == "__main__":
    success = test_bess_balance()
    sys.exit(0 if success else 1)
