#!/usr/bin/env python
"""
FASE 4: Ejecutar simulación BESS v5.5 con nueva estrategia de descarga
Nueva lógica: SOC exacto 20% a las 22h + descarga máxima a MALL
"""
import sys
import traceback
from pathlib import Path
import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*90)
print("FASE 4: BESS v5.5 - Simulación con estrategia mixta (EV + MALL SOC=20%)")
print("="*90)

try:
    print("\n[1] Importando módulo BESS...")
    from src.dimensionamiento.oe2.disenobess.bess import (
        load_mall_demand_real,
        load_pv_generation,
        load_ev_demand,
        simulate_bess_solar_priority,
        analyze_bess_characteristics,
        generate_bess_analysis_report,
        save_bess_analysis_summary,
        BESS_CAPACITY_KWH_V53,
        BESS_POWER_KW_V53,
        BESS_EFFICIENCY_V53,
        BESS_SOC_MIN_V53,
    )
    print("    ✓ Importación exitosa")
    
    # Rutas a archivos de entrada
    pv_path = Path("data/oe2/solar/pv_generation_timeseries.csv")
    ev_path = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
    mall_path = Path("data/oe2/demandamallkwh/demandamallhorakwh.csv")
    
    print("\n[2] Cargando datos de entrada...")
    
    # Cargar PV
    print(f"    Cargando PV desde {pv_path}...")
    df_pv = load_pv_generation(pv_path)
    pv_kwh = df_pv['pv_kwh'].values if 'pv_kwh' in df_pv.columns else df_pv.iloc[:, 0].values
    print(f"    ✓ PV: {len(pv_kwh)} horas ({pv_kwh.sum():,.0f} kWh/año)")
    
    # Cargar EV
    print(f"    Cargando EV desde {ev_path}...")
    df_ev = load_ev_demand(ev_path, year=2024)
    # Asegurar 8,760 horas
    if len(df_ev) != 8760:
        print(f"    ADVERTENCIA: EV tiene {len(df_ev)} registros, esperaba 8,760")
    ev_kwh = df_ev['ev_kwh'].values[:8760] if 'ev_kwh' in df_ev.columns else df_ev.iloc[:8760, 0].values
    print(f"    ✓ EV: {len(ev_kwh)} horas ({ev_kwh.sum():,.0f} kWh/año)")
    
    # Cargar MALL
    print(f"    Cargando MALL desde {mall_path}...")
    df_mall = load_mall_demand_real(mall_path, year=2024)
    # Asegurar 8,760 horas
    if len(df_mall) != 8760:
        print(f"    ADVERTENCIA: MALL tiene {len(df_mall)} registros, esperaba 8,760")
    mall_kwh = df_mall['mall_kwh'].values[:8760] if 'mall_kwh' in df_mall.columns else df_mall.iloc[:8760, 0].values
    print(f"    ✓ MALL: {len(mall_kwh)} horas ({mall_kwh.sum():,.0f} kWh/año)")
    
    # Parámetros BESS (confirmados, no cambios)
    capacity_kwh = BESS_CAPACITY_KWH_V53  # 1,700 kWh
    power_kw = BESS_POWER_KW_V53  # 400 kW
    efficiency = BESS_EFFICIENCY_V53  # 0.95
    soc_min = BESS_SOC_MIN_V53  # 0.20 (20%)
    
    print(f"\n[3] Parámetros BESS v5.5 (confirmados)...")
    print(f"    ✓ Capacidad: {capacity_kwh:,.0f} kWh")
    print(f"    ✓ Potencia: {power_kw:,.0f} kW")
    print(f"    ✓ Eficiencia round-trip: {efficiency:.2%}")
    print(f"    ✓ SOC mínimo: {soc_min:.0%}")
    print(f"    ✓ Cierre a las: 22h (closing_hour=22)")
    print(f"    ✓ Objetivo SOC 22h: 20.0% DURO")
    
    print(f"\n[4] Ejecutando simulación horaria (8,760 horas)...")
    print(f"    Esto puede tardar 60-120 segundos...")
    
    # Ejecutar simulación CON LA NUEVA LÓGICA
    # La función ahora usa calculate_max_discharge_to_mall() en PRIORIDAD 2
    df_sim, metrics = simulate_bess_solar_priority(
        pv_kwh=pv_kwh,
        ev_kwh=ev_kwh,
        mall_kwh=mall_kwh,
        capacity_kwh=capacity_kwh,
        power_kw=power_kw,
        efficiency=efficiency,
        soc_min=soc_min,
        closing_hour=22,
        year=2024,
    )
    
    print(f"    ✓ Simulación completada: {len(df_sim)} timesteps")
    
    print(f"\n[5] Calculando características BESS...")
    characteristics = analyze_bess_characteristics(
        df_sim,
        capacity_kwh=capacity_kwh,
        power_kw=power_kw
    )
    print(f"    ✓ {len(characteristics)} métricas calculadas")
    
    print(f"\n[6] Generando reporte...")
    report = generate_bess_analysis_report(
        characteristics,
        capacity_kwh=capacity_kwh,
        power_kw=power_kw
    )
    print(f"    ✓ Reporte generado ({len(report)} líneas)")
    
    print(f"\n[7] Guardando resultados...")
    out_dir = Path("data/oe2/bess")
    summary = save_bess_analysis_summary(
        characteristics=characteristics,
        capacity_kwh=capacity_kwh,
        power_kw=power_kw,
        efficiency=efficiency,
        report_text=report,
        out_dir=out_dir
    )
    print(f"    ✓ Archivos guardados a:")
    print(f"      - data/oe2/bess/bess_simulation_hourly.csv")
    print(f"      - data/oe2/bess/bess_characteristics_summary.txt")
    print(f"      - data/oe2/bess/bess_characteristics_analysis.json")
    
    print(f"\n[8] RESUMEN DE RESULTADOS v5.5")
    print("-" * 90)
    
    # Verificar SOC a las 22h
    if 'bess_soc_percent' in df_sim.columns and 'hour' in df_sim.columns:
        soc_22h = df_sim[df_sim['hour'] == 22]['bess_soc_percent']
        print(f"    SOC a las 22h:")
        print(f"      - Promedio: {soc_22h.mean():.1f}%")
        print(f"      - Mín/Máx:  {soc_22h.min():.1f}% / {soc_22h.max():.1f}%")
        if abs(soc_22h.mean() - 20.0) < 1.0:
            print(f"      ✓ [OK] Meta alcanzada (target 20%)")
        else:
            print(f"      ⚠ [ALERTA] Desviación {abs(soc_22h.mean()-20.0):.1f}%")
    
    # Extraer métricas clave del diccionario de características
    if isinstance(characteristics, dict):
        if 'bess_to_mall_kwh_total' in characteristics:
            mall_energy = characteristics['bess_to_mall_kwh_total']
            print(f"    BESS a MALL: {mall_energy:>12,.0f} kWh/año")
        
        if 'ev_coverage_percent' in characteristics:
            ev_cov = characteristics['ev_coverage_percent']
            print(f"    Cobertura EV: {ev_cov:>11.1f}%")
        
        if 'mall_coverage_percent' in characteristics:
            mall_cov = characteristics['mall_coverage_percent']
            print(f"    Cobertura MALL: {mall_cov:>9.1f}%")
        
        if 'cycles_per_year' in characteristics:
            cycles = characteristics['cycles_per_year']
            print(f"    Ciclos/año: {cycles:>14.2f}")
    
    print(f"\n[9] Comparativa ESPERADA:")
    print("-" * 90)
    print(f"    v5.4 (antigua):          v5.5 (nueva):")
    print(f"    - SOC 22h: 27.8% avg     20.0% exacto     ← Consistencia")
    print(f"    - BESS→MALL: 265k kWh    ~665k kWh        ← +400k kWh/año")
    print(f"    - MALL coverage: 3.3%    5.4%             ← +2.1 puntos")
    print(f"    - EV coverage: 81%       81%              ← Sin cambios")
    print(f"    - Picos <1800 kW: NO     NO (aún 18.1%)   ← Limitación BESS 400kW")
    
    print(f"\n" + "="*90)
    print("FASE 4: Simulación exitosa ✓")
    print("="*90)
    
except Exception as e:
    print(f"\n[ERROR] {str(e)}")
    print("\nTraceback completo:")
    traceback.print_exc()
    sys.exit(1)

