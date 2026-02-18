"""
ANALISIS: Verificación de Dataset BESS Generado
================================================
Verifica:
1. Columnas generadas correctamente
2. Consistencia de datos según lógica BESS
3. Crea columnas de "demanda cortada por BESS" para agente
4. Valida balance energético
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
import sys

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dimensionamiento.oe2.disenobess.bess import (
    simulate_bess_ev_exclusive,
    load_pv_generation,
    load_ev_demand,
    load_mall_demand_real,
)


def analyze_bess_dataset(
    pv_kwh: np.ndarray,
    ev_kwh: np.ndarray,
    mall_kwh: np.ndarray,
    capacity_kwh: float = 1700.0,
    power_kw: float = 400.0,
) -> tuple[pd.DataFrame, dict]:
    """
    Genera dataset BESS y lo analiza detalladamente.
    
    Returns:
        (df_result: DataFrame con análisis, stats: diccionario de estadísticas)
    """
    print("\n" + "="*100)
    print("GENERANDO DATASET BESS (SIMULACION 1 AÑO = 8,760 HORAS)")
    print("="*100)
    
    # Generar simulación BESS
    df_sim, metrics = simulate_bess_ev_exclusive(
        pv_kwh=pv_kwh,
        ev_kwh=ev_kwh,
        mall_kwh=mall_kwh,
        capacity_kwh=capacity_kwh,
        power_kw=power_kw,
        closing_hour=22,
    )
    
    print(f"✅ Dataset generado: {len(df_sim)} filas (horas)")
    print(f"   Período: {df_sim.index[0]} a {df_sim.index[-1]}")
    
    # ======================================================================
    # PASO 1: VERIFICAR COLUMNAS GENERADAS
    # ======================================================================
    print("\n" + "-"*100)
    print("PASO 1: COLUMNAS GENERADAS")
    print("-"*100)
    
    columns = df_sim.columns.tolist()
    print(f"\nTotal de columnas: {len(columns)}")
    
    # Agrupar por categoría
    categories = {
        'Generación': ['pv_kwh'],
        'Demanda': ['ev_kwh', 'mall_kwh', 'load_kwh'],
        'PV Distribución': ['pv_to_ev_kwh', 'pv_to_bess_kwh', 'pv_to_mall_kwh', 'pv_curtailed_kwh'],
        'BESS Carga/Descarga': ['bess_charge_kwh', 'bess_discharge_kwh', 'bess_action_kwh', 'bess_mode'],
        'BESS Distribución': ['bess_to_ev_kwh', 'bess_to_mall_kwh', 'bess_total_discharge_kwh'],
        'Grid': ['grid_import_ev_kwh', 'grid_import_mall_kwh', 'grid_import_kwh', 'grid_export_kwh'],
        'Estado BESS': ['soc_percent', 'soc_kwh'],
        'Beneficios': ['co2_avoided_indirect_kg', 'cost_savings_hp_soles'],
    }
    
    print("\nCategorías de columnas:")
    for cat, cols in categories.items():
        found_cols = [c for c in cols if c in columns]
        status = "✅" if len(found_cols) == len(cols) else "⚠️"
        print(f"  {status} {cat}: {found_cols}")
    
    # ======================================================================
    # PASO 2: CONSISTENCIA DE DATOS - BALANCE ENERGÉTICO
    # ======================================================================
    print("\n" + "-"*100)
    print("PASO 2: BALANCE ENERGÉTICO (Balance = 0)")
    print("-"*100)
    
    # Balance horario: PV + BESS_descarga = EV + MALL + BESS_carga + Grid_export
    pv_balance = df_sim['pv_kwh'].values
    bess_discharge = df_sim['bess_discharge_kwh'].values
    ev_demand = df_sim['ev_kwh'].values
    mall_demand = df_sim['mall_kwh'].values
    bess_charge = df_sim['bess_charge_kwh'].values
    grid_export = df_sim['grid_export_kwh'].values
    
    # LHS = Supply (oferta)
    supply = pv_balance + bess_discharge
    
    # RHS = Demand (demanda)
    demand = ev_demand + mall_demand + bess_charge + grid_export
    
    # Balance
    balance = supply - demand
    
    # Estadísticas de balance
    balance_mean = np.mean(np.abs(balance))
    balance_max = np.max(np.abs(balance))
    balance_std = np.std(balance)
    
    print(f"\nBalance energético por hora:")
    print(f"  Supply (PV + BESS_descarga) = Demand (EV + MALL + BESS_carga + Grid_export)")
    print(f"\n  Media desviación absoluta: {balance_mean:.2f} kWh")
    print(f"  Máxima desviación absoluta: {balance_max:.2f} kWh")
    print(f"  Desviación estándar: {balance_std:.2f} kWh")
    
    if balance_max < 1.0:
        print(f"  ✅ BALANCE CORRECTO (desviación < 1 kWh)")
    else:
        print(f"  ⚠️  Balance con desviaciones > 1 kWh (revisar)")
    
    # ======================================================================
    # PASO 3: VERIFICAR DISTRIBUCION DE PV (PV suma a distribución)
    # ======================================================================
    print("\n" + "-"*100)
    print("PASO 3: DISTRIBUCIÓN DE GENERACION PV")
    print("-"*100)
    
    # Cada kWh de PV debe ir a EV, BESS, MALL o ser curtailed
    pv_distribution = (
        df_sim['pv_to_ev_kwh'].values + 
        df_sim['pv_to_bess_kwh'].values + 
        df_sim['pv_to_mall_kwh'].values + 
        df_sim['pv_curtailed_kwh'].values
    )
    
    pv_check = pv_balance - pv_distribution
    pv_error = np.max(np.abs(pv_check))
    
    print(f"\nVerificación: PV = PV_to_EV + PV_to_BESS + PV_to_MALL + PV_curtailed")
    print(f"  Error máximo: {pv_error:.6f} kWh")
    
    if pv_error < 0.01:
        print(f"  ✅ DISTRIBUCION DE PV CORRECTA")
    else:
        print(f"  ⚠️  Error en distribución de PV")
    
    # Resumen anual
    total_pv = pv_balance.sum()
    pv_to_ev_total = df_sim['pv_to_ev_kwh'].sum()
    pv_to_bess_total = df_sim['pv_to_bess_kwh'].sum()
    pv_to_mall_total = df_sim['pv_to_mall_kwh'].sum()
    pv_curtailed_total = df_sim['pv_curtailed_kwh'].sum()
    
    print(f"\nDistribución anual:")
    print(f"  Total PV generado: {total_pv:>12,.0f} kWh")
    print(f"  → EV (directo):    {pv_to_ev_total:>12,.0f} kWh ({100*pv_to_ev_total/max(total_pv,1):.1f}%)")
    print(f"  → BESS (carga):    {pv_to_bess_total:>12,.0f} kWh ({100*pv_to_bess_total/max(total_pv,1):.1f}%)")
    print(f"  → MALL (directo):  {pv_to_mall_total:>12,.0f} kWh ({100*pv_to_mall_total/max(total_pv,1):.1f}%)")
    print(f"  → Curtailed:       {pv_curtailed_total:>12,.0f} kWh ({100*pv_curtailed_total/max(total_pv,1):.1f}%)")
    print(f"  SUMA:              {pv_to_ev_total+pv_to_bess_total+pv_to_mall_total+pv_curtailed_total:>12,.0f} kWh")
    
    # ======================================================================
    # PASO 4: DEMANDA - CONTRIBUCION BESS = DEMANDA CORTADA
    # ======================================================================
    print("\n" + "-"*100)
    print("PASO 4: CREAR COLUMNAS DE DEMANDA 'CORTADA' POR BESS")
    print("-"*100)
    
    # Demanda cortada de EV = EV - contribución BESS
    ev_demand_after_bess = df_sim['ev_kwh'].values - df_sim['bess_to_ev_kwh'].values
    ev_demand_after_bess = np.maximum(ev_demand_after_bess, 0)  # No negativo
    
    # Demanda cortada de MALL = MALL - contribución BESS (peak shaving)
    mall_demand_after_bess = df_sim['mall_kwh'].values - df_sim['bess_to_mall_kwh'].values
    mall_demand_after_bess = np.maximum(mall_demand_after_bess, 0)  # No negativo
    
    # Demanda cortada total
    load_after_bess = ev_demand_after_bess + mall_demand_after_bess
    
    # Agregar al dataframe
    df_sim['ev_demand_after_bess_kwh'] = ev_demand_after_bess
    df_sim['mall_demand_after_bess_kwh'] = mall_demand_after_bess
    df_sim['load_after_bess_kwh'] = load_after_bess
    
    print(f"\n✅ Columnas de demanda 'cortada' creadas:")
    print(f"   - ev_demand_after_bess_kwh:    EV sin contribución BESS")
    print(f"   - mall_demand_after_bess_kwh:  MALL sin peak shaving BESS")
    print(f"   - load_after_bess_kwh:         Carga total sin BESS")
    
    # Estadísticas
    total_ev = df_sim['ev_kwh'].sum()
    total_ev_after = ev_demand_after_bess.sum()
    bess_to_ev_total = df_sim['bess_to_ev_kwh'].sum()
    
    total_mall = df_sim['mall_kwh'].sum()
    total_mall_after = mall_demand_after_bess.sum()
    bess_to_mall_total = df_sim['bess_to_mall_kwh'].sum()
    
    print(f"\nImpacto BESS en EV:")
    print(f"  Demanda EV original:        {total_ev:>12,.0f} kWh")
    print(f"  Cubre BESS:                 {bess_to_ev_total:>12,.0f} kWh ({100*bess_to_ev_total/max(total_ev,1):.1f}%)")
    print(f"  Demanda después (cortada):  {total_ev_after:>12,.0f} kWh ({100*total_ev_after/max(total_ev,1):.1f}%)")
    
    print(f"\nImpacto BESS en MALL (peak shaving):")
    print(f"  Demanda MALL original:      {total_mall:>12,.0f} kWh")
    print(f"  Peak shaving BESS:          {bess_to_mall_total:>12,.0f} kWh ({100*bess_to_mall_total/max(total_mall,1):.1f}%)")
    print(f"  Demanda después (cortada):  {total_mall_after:>12,.0f} kWh ({100*total_mall_after/max(total_mall,1):.1f}%)")
    
    # ======================================================================
    # PASO 5: COBERTURA DE DEMANDA CORTADA (PV + Grid)
    # ======================================================================
    print("\n" + "-"*100)
    print("PASO 5: VERIFICACIÓN - DEMANDA CORTADA CUBIERTA POR PV + GRID")
    print("-"*100)
    
    # Para EV:
    # ev_after_bess debe ser cubierta por pv_to_ev + grid_to_ev
    ev_covered_by_pv = df_sim['pv_to_ev_kwh'].values
    ev_covered_by_grid = df_sim['grid_import_ev_kwh'].values
    ev_coverage = ev_covered_by_pv + ev_covered_by_grid
    ev_coverage_check = ev_demand_after_bess - ev_coverage
    ev_error = np.max(np.abs(ev_coverage_check))
    
    print(f"\nEV: pv_to_ev + grid_to_ev = ev_demand_after_bess")
    print(f"  Error máximo: {ev_error:.6f} kWh")
    if ev_error < 0.01:
        print(f"  ✅ COBERTURA DE EV CORRECTA")
    
    # Para MALL:
    mall_covered_by_pv = df_sim['pv_to_mall_kwh'].values
    mall_covered_by_grid = df_sim['grid_import_mall_kwh'].values
    mall_coverage = mall_covered_by_pv + mall_covered_by_grid
    mall_coverage_check = mall_demand_after_bess - mall_coverage
    mall_error = np.max(np.abs(mall_coverage_check))
    
    print(f"\nMALL: pv_to_mall + grid_to_mall = mall_demand_after_bess")
    print(f"  Error máximo: {mall_error:.6f} kWh")
    if mall_error < 0.01:
        print(f"  ✅ COBERTURA DE MALL CORRECTA")
    
    # ======================================================================
    # PASO 6: ESTADISTICAS DIARIAS (MUESTRA)
    # ======================================================================
    print("\n" + "-"*100)
    print("PASO 6: MUESTRA DE DATOS POR DÍA (PRIMEROS 3 DÍAS)")
    print("-"*100)
    
    # Seleccionar primeros 3 días (72 horas)
    df_sample = df_sim.iloc[:72].copy()
    df_sample['hour'] = df_sample.index.hour
    df_sample['day'] = df_sample.index.day
    
    # Resumen por día
    daily_summary = df_sample.groupby('day').agg({
        'pv_kwh': 'sum',
        'ev_kwh': 'sum',
        'mall_kwh': 'sum',
        'bess_charge_kwh': 'sum',
        'bess_discharge_kwh': 'sum',
        'bess_to_ev_kwh': 'sum',
        'bess_to_mall_kwh': 'sum',
        'grid_import_ev_kwh': 'sum',
        'grid_import_mall_kwh': 'sum',
        'ev_demand_after_bess_kwh': 'sum',
        'mall_demand_after_bess_kwh': 'sum',
        'soc_percent': ['min', 'max', 'mean'],
    })
    
    print("\nResumen por día (kWh):\n")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    print(daily_summary.round(1).to_string())
    
    # ======================================================================
    # PASO 7: DATOS PARA ENTRENAMIENTO DEL AGENTE
    # ======================================================================
    print("\n" + "-"*100)
    print("PASO 7: DATOS PARA ENTRENAMIENTO DEL AGENTE")
    print("-"*100)
    
    # El agente debe ver:
    # 1. Demanda cortada (ev_demand_after_bess, mall_demand_after_bess)
    # 2. Generación PV (pv_kwh)
    # 3. Estado BESS (soc_percent)
    # 4. No debe ver contribución del BESS (ya está contabilizado)
    
    df_agent = df_sim[[
        'pv_kwh',  # Generación actual
        'ev_demand_after_bess_kwh',  # Demanda EV (sin BESS)
        'mall_demand_after_bess_kwh',  # Demanda MALL (sin peak shaving)
        'load_after_bess_kwh',  # Carga total sin BESS
        'soc_percent',  # Estado del BESS
        'soc_kwh',  # Estado en kWh
        'grid_import_ev_kwh',  # Grid que cubre EV
        'grid_import_mall_kwh',  # Grid que cubre MALL
        'grid_import_kwh',  # Total grid import
    ]].copy()
    
    print(f"\n✅ Dataset para agente creado: {len(df_agent)} filas")
    print(f"   Columnas necesarias para entrenamiento:")
    print(f"   - pv_kwh: Generación PV horaria")
    print(f"   - ev_demand_after_bess_kwh: Demanda EV sin BESS")
    print(f"   - mall_demand_after_bess_kwh: Demanda MALL sin peak shaving")
    print(f"   - load_after_bess_kwh: Carga total sin BESS")
    print(f"   - soc_percent: Estado BESS (0-100%)")
    print(f"   - soc_kwh: Estado BESS en kWh")
    print(f"   - grid_import_*: Uso de grid (para cálculo de rewards)")
    
    # ======================================================================
    # RESUMEN FINAL
    # ======================================================================
    print("\n" + "="*100)
    print("RESUMEN FINAL - VERIFICACIÓN COMPLETADA")
    print("="*100)
    
    stats = {
        'balance_max_error_kwh': float(balance_max),
        'pv_distribution_error_kwh': float(pv_error),
        'ev_coverage_error_kwh': float(ev_error),
        'mall_coverage_error_kwh': float(mall_error),
        'total_pv_kwh': float(total_pv),
        'total_ev_kwh': float(total_ev),
        'total_mall_kwh': float(total_mall),
        'bess_to_ev_kwh': float(bess_to_ev_total),
        'bess_to_mall_kwh': float(bess_to_mall_total),
        'ev_demand_after_bess_kwh': float(total_ev_after),
        'mall_demand_after_bess_kwh': float(total_mall_after),
        'total_grid_import_kwh': float(df_sim['grid_import_kwh'].sum()),
        'soc_min_percent': float(df_sim['soc_percent'].min()),
        'soc_max_percent': float(df_sim['soc_percent'].max()),
        'soc_avg_percent': float(df_sim['soc_percent'].mean()),
    }
    
    print("\n✅ TODOS LOS BALANCES VERIFICADOS CORRECTAMENTE" if all([
        balance_max < 1.0,
        pv_error < 0.01,
        ev_error < 0.01,
        mall_error < 0.01,
    ]) else "\n⚠️  REVISAR ERRORES DETECTADOS")
    
    print(f"\nDatos del dataset:")
    print(f"  Total filas: {len(df_sim)} (horas)")
    print(f"  Período: {df_sim.index[0]} a {df_sim.index[-1]}")
    print(f"  Columnas: {len(df_sim.columns)}")
    print(f"  Nuevas columnas agregadas: 3 (demanda cortada)")
    
    return df_sim, stats


if __name__ == "__main__":
    print("\n" + "="*100)
    print("ANALISIS DE DATASET BESS - VERIFICACION COMPLETA")
    print("="*100)
    
    # Cargar datos reales de OE2 si existen
    data_dir = Path("data/interim/oe2")
    
    # Intentar cargar datos reales
    try:
        pv_path = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
        ev_path = Path("data/interim/oe2/ev/ev_demand_hourly.csv")
        mall_path = Path("data/interim/oe2/demandamallhorakwh.csv")
        
        if pv_path.exists() and ev_path.exists() and mall_path.exists():
            print("\n📂 Cargando datos reales de OE2...")
            pv_kwh = load_pv_generation(pv_path)['pv_kwh'].values
            ev_kwh = load_ev_demand(ev_path)['ev_kwh'].values
            mall_kwh = load_mall_demand_real(mall_path)['mall_kwh'].values
            print("✅ Datos reales cargados")
        else:
            raise FileNotFoundError("Faltan archivos de OE2")
    except Exception as e:
        print(f"\n⚠️  No se encontraron datos de OE2: {e}")
        print("   Usando datos de prueba sintéticos...")
        
        # Crear datos sintéticos para demostración
        n_hours = 8760
        
        # PV: curva típica con hora local
        hour_of_day = np.arange(n_hours) % 24
        pv_kwh = np.where(
            (hour_of_day >= 6) & (hour_of_day < 18),
            500 * np.sin((hour_of_day - 6) * np.pi / 12) ** 1.5,
            0,
        )
        
        # EV: demanda diaria 6-22h
        ev_kwh = np.where(
            (hour_of_day >= 6) & (hour_of_day < 22),
            100 + 50 * np.sin((hour_of_day - 6) * np.pi / 16),
            0,
        )
        
        # MALL: demanda constante con variaciones
        mall_kwh = 100 + 30 * np.sin((hour_of_day - 6) * np.pi / 12)
        mall_kwh = np.maximum(mall_kwh, 30)  # Minimo 30 kW
    
    # Ejecutar análisis
    df_result, stats = analyze_bess_dataset(pv_kwh, ev_kwh, mall_kwh)
    
    # Guardar dataset con demanda cortada
    output_path = Path("outputs/bess_dataset_with_demand_cut.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_result.to_csv(output_path)
    print(f"\n✅ Dataset guardado en: {output_path}")
    
    print("\n" + "="*100 + "\n")
