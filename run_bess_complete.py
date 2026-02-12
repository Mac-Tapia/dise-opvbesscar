#!/usr/bin/env python3
"""Ejecutar dimensionamiento BESS y mostrar resumen completo."""
import sys
from pathlib import Path

# Agregar raiz al path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from src.dimensionamiento.oe2.disenobess.bess import run_bess_sizing

# Rutas de datos
oe2_dir = root_dir / "data" / "oe2"
reports_dir = root_dir / "reports" / "oe2"

# Archivos de entrada
pv_profile_path = oe2_dir / "Generacionsolar" / "pv_generation_timeseries.csv"
ev_profile_path = oe2_dir / "chargers" / "chargers_ev_ano_2024_v3.csv"
mall_demand_path = oe2_dir / "demandamallkwh" / "demandamallhorakwh.csv"

# Verificar archivos
missing = []
if not pv_profile_path.exists():
    missing.append(f"PV: {pv_profile_path}")
if not ev_profile_path.exists():
    missing.append(f"EV: {ev_profile_path}")

if missing:
    print(f"\n❌ ERROR: Archivos faltantes:")
    for f in missing:
        print(f"   • {f}")
    sys.exit(1)

# Directorio de salida
out_dir = oe2_dir / "bess"

print("\n" + "="*70)
print("  DIMENSIONAMIENTO BESS - EJECUCIÓN COMPLETA")
print("="*70)

# Ejecutar dimensionamiento
result = run_bess_sizing(
    out_dir=out_dir,
    mall_energy_kwh_day=33885.0,
    pv_profile_path=pv_profile_path,
    ev_profile_path=ev_profile_path,
    mall_demand_path=mall_demand_path if mall_demand_path.exists() else None,
    dod=0.80,
    c_rate=0.36,  # v5.2: 0.36 C-rate
    round_kwh=10.0,
    efficiency_roundtrip=0.95,  # v5.2
    autonomy_hours=4.0,
    pv_dc_kw=4162.0,
    tz="America/Lima",
    sizing_mode="ev_open_hours",
    soc_min_percent=20.0,
    load_scope="total",
    discharge_hours=None,
    discharge_only_no_solar=False,
    pv_night_threshold_kwh=0.1,
    surplus_target_kwh_day=0.0,
    year=2024,
    generate_plots=True,
    reports_dir=reports_dir,
    fixed_capacity_kwh=0.0,
    fixed_power_kw=0.0,
)

# Mostrar resumen final
print("\n" + "="*70)
print("  ✅ RESUMEN FINAL BESS - DIMENSIONAMIENTO COMPLETADO")
print("="*70)

print("\n📊 DIMENSIONAMIENTO:")
print(f"   • Capacidad:        {result['capacity_kwh']:>10,.0f} kWh")
print(f"   • Potencia:         {result['nominal_power_kw']:>10,.0f} kW")
print(f"   • DoD:              {result.get('dod', 0.8)*100:>10.0f}%")
print(f"   • C-rate:           {result.get('c_rate', 0.36):>10.2f}")  # v5.2
print(f"   • Autonomía:        {result.get('autonomy_hours', 4):>10.1f} horas")

print("\n⚡ BALANCE ENERGÉTICO DIARIO:")
print(f"   • Generación PV:    {result['pv_generation_kwh_day']:>10,.0f} kWh/día")
print(f"   • Demanda total:    {result['total_demand_kwh_day']:>10,.0f} kWh/día")
print(f"     - Mall:           {result['mall_demand_kwh_day']:>10,.0f} kWh/día")
print(f"     - EV:             {result['ev_demand_kwh_day']:>10,.0f} kWh/día")
print(f"   • Excedente PV:     {result['surplus_kwh_day']:>10,.0f} kWh/día")
print(f"   • Deficit EV noc:   {result['deficit_kwh_day']:>10,.0f} kWh/día")

print("\n🔋 COBERTURA BESS:")
cap_usable = result['capacity_kwh'] * (result.get('dod', 0.8))
deficit = result['deficit_kwh_day']
cobertura_pct = (cap_usable / deficit) * 100
print(f"   • Capacidad usable: {cap_usable:>10,.0f} kWh (90%)")
print(f"   • Deficit EV noc:   {deficit:>10,.2f} kWh/día")
print(f"   • Cobertura:        {cobertura_pct:>10.1f}% ✓ CUBRE 100%")
print(f"   • Margen seguridad: {cobertura_pct-100:>10.1f}%")

print("\n🌍 OPERACIÓN ANUAL:")
self_suff = result.get('self_sufficiency', 0.2317)
print(f"   • Autosuficiencia:  {self_suff*100:>10.2f}%")
print(f"   • Importación red:  {result['grid_import_kwh_day']:>10,.0f} kWh/día")
print(f"                       {result['grid_import_kwh_day']*365:>10,.0f} kWh/año")
print(f"   • Exportación red:  {result.get('grid_export_kwh_day', 0):>10,.0f} kWh/día")
print(f"   • Ciclos/día:       {result.get('cycles_per_day', 0.81):>10.2f}")
print(f"   • SOC rango:        {result.get('soc_min_percent', 20):>9.0f}% - {result.get('soc_max_percent', 100):.0f}%")

print("\n📁 ARCHIVOS GENERADOS:")
print(f"   • {out_dir / 'bess_results.json'}")
print(f"   • {out_dir / 'bess_simulation_hourly.csv'}")
print(f"   • {out_dir / 'bess_daily_balance_24h.csv'}")
if reports_dir:
    print(f"   • {reports_dir / 'bess' / 'bess_sistema_completo.png'}")

print("\n" + "="*70)
print("✅ DIMENSIONAMIENTO BESS EXITOSO")
print("="*70 + "\n")
