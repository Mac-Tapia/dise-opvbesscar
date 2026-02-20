#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificación de Balance Energético del BESS
Ejecuta la simulación BESS y valida que carga ≈ descarga
"""

from pathlib import Path
import sys

# Rutas de datos
pv_path = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
ev_path = Path("data/interim/oe2/ev_demand/ev_demand_timeseries.csv")
mall_path = Path("data/interim/oe2/mall_demand/mall_demand_real_hourly.csv")
out_dir = Path("outputs/bess_validation_check")

print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║           VERIFICACIÓN DE BALANCE ENERGÉTICO DEL BESS                          ║
║   Validando que: Energía Cargada ≈ Energía Descargada × Eficiencia            ║
╚═══════════════════════════════════════════════════════════════════════════════╝
""")

# Verificar archivos
print("\n[1] Verificando archivos de entrada...")
if not pv_path.exists():
    print(f"   ❌ ERROR: No encontrado {pv_path}")
    sys.exit(1)
if not ev_path.exists():
    print(f"   ❌ ERROR: No encontrado {ev_path}")
    sys.exit(1)
if not mall_path.exists():
    print(f"   ❌ ERROR: No encontrado {mall_path}")
    sys.exit(1)

print(f"   ✅ PV: {pv_path}")
print(f"   ✅ EV: {ev_path}")
print(f"   ✅ Mall: {mall_path}")

# Ejecutar dimensionamiento BESS (que incluye validación de balance)
print("\n[2] Ejecutando BESS Sizing con validación de balance energético...")
print("   (Este proceso ejecutará la simulación BESS y mostrará la validación)")

try:
    from src.dimensionamiento.oe2.disenobess.bess import run_bess_sizing
    
    results = run_bess_sizing(
        out_dir=out_dir,
        pv_profile_path=pv_path,
        ev_profile_path=ev_path,
        mall_demand_path=mall_path,
        dod=0.80,
        efficiency_roundtrip=0.95,
        year=2024,
        generate_plots=False,  # Sin gráficas para ir más rápido
        sizing_mode="ev_open_hours",
        fixed_capacity_kwh=1700.0,
        fixed_power_kw=400.0,
    )
    
    print("\n[3] Resultados del Balance Energético:")
    print("=" * 80)
    
    if 'bess_energy_stored_kwh' in results:
        stored = results['bess_energy_stored_kwh']
        delivered = results['bess_energy_delivered_kwh']
        balance_error = results['bess_balance_error_kwh']
        balance_error_pct = results['bess_balance_error_percent']
        
        print(f"\n   Energía Cargada (bruta):        {results['total_bess_charge_kwh']:>15,.0f} kWh/año")
        print(f"   Energía Almacenada (neta):     {stored:>15,.0f} kWh/año")
        print(f"   Energía Descargada (bruta):    {results['total_bess_discharge_kwh']:>15,.0f} kWh/año")
        print(f"   Energía Entregada (neta):      {delivered:>15,.0f} kWh/año")
        print(f"\n   Balance Error:                  {balance_error:>15,.0f} kWh/año")
        print(f"   Balance Error %:                {balance_error_pct:>15.2f}%")
        
        print("\n[4] Ecuación Energética:")
        print("=" * 80)
        print(f"\n   TEÓRICA: Descarga = Carga × Eficiencia")
        print(f"            {delivered:>15,.0f} ≈ {results['total_bess_charge_kwh']:>15,.0f} × 0.95")
        print(f"            {delivered:>15,.0f} ≈ {results['total_bess_charge_kwh'] * 0.95:>15,.0f}")
        
        if balance_error_pct <= 5.0:
            print(f"\n   ✅ VALIDACION EXITOSA: Balance dentro de tolerancia ({balance_error_pct:.2f}% < 5%)")
        else:
            print(f"\n   ⚠️  ALERTA: Balance fuera de tolerancia ({balance_error_pct:.2f}% > 5%)")
            if balance_error > 0:
                print(f"   ❌ Problema: Se descargó MÁS de lo que se cargó")
            else:
                print(f"   ⚠️  Exceso: Hay energía sin descargar")
    
    print("\n" + "=" * 80)
    print(f"\n[5] Otros Resultados Relevantes:")
    print(f"\n   Ciclos/día:                     {results.get('cycles_per_day', 0):>15.2f}")
    print(f"   SOC Mín/Máx:                    {results.get('soc_min_percent', 0):>15.1f}% / {results.get('soc_max_percent', 0):.1f}%")
    print(f"   Autosuficiencia EV:             {results.get('ev_self_sufficiency', 0):>15.1%}")
    print(f"   Autosuficiencia Total:          {results.get('self_sufficiency', 0):>15.1%}")
    
    print("\n" + "=" * 80)
    print("\n✅ VERIFICACIÓN COMPLETADA")
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ ERROR durante ejecución:")
    print(f"   {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
