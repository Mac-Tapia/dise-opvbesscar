#!/usr/bin/env python3
"""
Script para ejecutar dimensionamiento BESS y guardar en data/oe2/bess
"""
from __future__ import annotations
import sys
from pathlib import Path

# Agregar raíz al path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from src.dimensionamiento.oe2.disenobess.bess import run_bess_sizing

# Rutas de entrada (data/oe2/)
oe2_dir = root_dir / "data" / "oe2"
pv_profile_path = oe2_dir / "Generacionsolar" / "pv_generation_timeseries.csv"
ev_profile_path = oe2_dir / "chargers" / "chargers_ev_ano_2024_v3.csv"
mall_demand_path = oe2_dir / "demandamallkwh" / "demandamallhorakwh.csv"

# Ruta de salida
out_dir = oe2_dir / "bess"
reports_dir = root_dir / "reports" / "oe2"

print("\n" + "="*80)
print("  DIMENSIONAMIENTO BESS - Script Ejecutable")
print("="*80)

# Verificar archivos
print("\n📂 VERIFICANDO ARCHIVOS DE ENTRADA:")
print(f"   PV:     {pv_profile_path}")
print(f"           Existe: {'✓' if pv_profile_path.exists() else '✗'}")
print(f"   EV:     {ev_profile_path}")
print(f"           Existe: {'✓' if ev_profile_path.exists() else '✗'}")
print(f"   Mall:   {mall_demand_path}")
print(f"           Existe: {'✓' if mall_demand_path.exists() else '✗'}")

if not pv_profile_path.exists() or not ev_profile_path.exists():
    print("\n❌ ERROR: Archivos faltantes")
    sys.exit(1)

print(f"\n📁 DIRECTORIO DE SALIDA: {out_dir}")

# Ejecutar dimensionamiento
print("\n⚙️  Iniciando dimensionamiento BESS...")
print("="*80)

result = run_bess_sizing(
    out_dir=out_dir,
    mall_energy_kwh_day=100.0,  # Fallback (se carga del archivo real)
    pv_profile_path=pv_profile_path,
    ev_profile_path=ev_profile_path,
    mall_demand_path=mall_demand_path if mall_demand_path.exists() else None,
    dod=0.80,  # v5.2: 80% DOD
    c_rate=0.36,  # v5.2: 0.36 C-rate
    round_kwh=10.0,
    efficiency_roundtrip=0.95,  # v5.2
    autonomy_hours=4.0,
    pv_dc_kw=4050.0,
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

# Mostrar resumen
print("\n" + "="*80)
print("  RESUMEN FINAL - BESS DIMENSIONAMIENTO")
print("="*80)

print("\n📦 ESPECIFICACIONES DIMENSIONADAS:")
print(f"   • Capacidad:         {result.get('capacity_kwh', 0):,.0f} kWh")
print(f"   • Potencia nominal:  {result.get('nominal_power_kw', 0):,.0f} kW")
print(f"   • DoD:               {result.get('dod', 0)*100:.0f}%")
print(f"   • C-rate:            {result.get('c_rate', 0):.2f}")

print("\n⚡ BALANCE ENERGÉTICO ANUAL:")
pv_gen = result.get('pv_generation_kwh_day', 0) * 365
total_dem = result.get('total_demand_kwh_day', 0) * 365
mall_dem = result.get('mall_demand_kwh_day', 0) * 365
ev_dem = result.get('ev_demand_kwh_day', 0) * 365
print(f"   • Generación PV:     {pv_gen:,.0f} kWh/año")
print(f"   • Demanda total:     {total_dem:,.0f} kWh/año")
print(f"     - Mall:            {mall_dem:,.0f} kWh/año")
print(f"     - EV:              {ev_dem:,.0f} kWh/año")
print(f"   • Excedente PV:      {result.get('surplus_kwh_day', 0)*365:,.0f} kWh/año")
print(f"   • Deficit diario:    {result.get('deficit_kwh_day', 0):,.0f} kWh/día")

print("\n🔋 OPERACIÓN PROYECTADA:")
self_suff = result.get('self_sufficiency', 0)
grid_import = result.get('grid_import_kwh_day', 0)
grid_export = result.get('grid_export_kwh_day', 0)
print(f"   • Autosuficiencia:   {self_suff*100:.1f}%")
print(f"   • Import red/día:    {grid_import:,.0f} kWh")
print(f"   • Export red/día:    {grid_export:,.0f} kWh")
print(f"   • Ciclos/día:        {result.get('cycles_per_day', 0):.2f}")
print(f"   • Rango SOC:         {result.get('soc_min_percent', 0):.0f}% - {result.get('soc_max_percent', 0):.0f}%")

print("\n📊 ARCHIVOS GENERADOS EN:")
csv_files = [
    out_dir / "bess_results.json",
    out_dir / "bess_simulation_hourly.csv",
    out_dir / "bess_daily_balance_24h.csv",
]
for f in csv_files:
    if f.exists():
        print(f"   ✓ {f.relative_to(root_dir)}")
    else:
        print(f"   ✗ {f.relative_to(root_dir)}")

plots_dir = reports_dir / "bess" if reports_dir else None
if plots_dir and plots_dir.exists():
    plot_files = list(plots_dir.glob("*.png"))
    print(f"\n   📈 Gráficos ({len(plot_files)} archivos):")
    for f in plot_files[:3]:
        print(f"      • {f.name}")

print("\n" + "="*80)
print("✅ DIMENSIONAMIENTO BESS COMPLETADO")
print("="*80 + "\n")
