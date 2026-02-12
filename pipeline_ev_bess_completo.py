#!/usr/bin/env python3
"""Script completo: Regenerar EV dataset + Dimensionar BESS con datos reales"""
from pathlib import Path
import sys

print("="*80)
print("PIPELINE COMPLETO: DATASET EV → DIMENSIONAMIENTO BESS")
print("="*80)

# ============================================================================
# PASO 1: REGENERAR DATASET EV CON PARÁMETROS REALES
# ============================================================================
print("\n[PASO 1/2] Regenerando dataset EV con parámetros v5.2...")
print("   • Motos: 1.0 cargas/toma/hora (60 min carga real)")
print("   • Mototaxis: 0.67 cargas/toma/hora (90 min carga real)")
print("   • Estructura: 15 cargadores motos + 4 cargadores mototaxis = 19 cargadores")
print("   • Tomas: 19 × 2 = 38 tomas (30 motos + 8 mototaxis) @ 7.4 kW")
print("   • Potencia instalada: 281.2 kW")

try:
    from src.dimensionamiento.oe2.disenocargadoresev.chargers import generate_socket_level_dataset_v3
    
    output_dir = Path('data/interim/oe2/chargers')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    df_annual, df_daily = generate_socket_level_dataset_v3(
        output_dir=output_dir,
        random_seed=42
    )
    
    # Sumar potencias de todos los sockets para obtener demanda horaria
    socket_power_cols = [col for col in df_annual.columns if '_power_kw' in col]
    ev_demand_hourly = df_annual[socket_power_cols].sum(axis=1)
    
    # Guardar perfil agregado
    import pandas as pd
    df_ev_profile = pd.DataFrame({
        'hour': range(len(ev_demand_hourly)),
        'ev_demand_kw': ev_demand_hourly.values,
        'ev_demand_kwh': ev_demand_hourly.values  # Asumir 1 hora = 1 kWh/kW
    })
    df_ev_profile.to_csv(output_dir / 'ev_demand_horario.csv', index=False)
    
    total_ev_energy = ev_demand_hourly.sum()
    print(f"\n✅ Dataset EV regenerado exitosamente")
    print(f"   • Energía anual EV: {total_ev_energy:,.0f} kWh/año")
    print(f"   • Energía diaria promedio: {total_ev_energy/365:,.0f} kWh/día")
    print(f"   • Potencia máxima: {ev_demand_hourly.max():.1f} kW")
    print(f"   • Archivo: {output_dir / 'ev_demand_horario.csv'}")
    
except Exception as e:
    print(f"\n❌ ERROR en regeneración EV: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# PASO 2: DIMENSIONAR BESS CON DATOS REALES
# ============================================================================
print("\n[PASO 2/2] Dimensionando BESS con datos reales de EV...")
print("   • Cargando: Solar PV 4,050 kWp")
print("   • Cargando: Demanda Mall real")
print("   • Cargando: Demanda EV real (2 motos + 2 mototaxis/socket/hora)")

try:
    from src.dimensionamiento.oe2.disenobess.bess import run_bess_sizing
    
    out_dir = Path('data/interim/oe2/bess')
    out_dir.mkdir(parents=True, exist_ok=True)
    
    pv_profile = Path('data/interim/oe2/solar/pv_generation_timeseries.csv')
    ev_profile = Path('data/interim/oe2/chargers/ev_demand_horario.csv')
    
    # Verificar que existan
    if not pv_profile.exists():
        print(f"⚠️  ADVERTENCIA: Solar no encontrado en {pv_profile}")
        pv_profile = Path('data/interim/oe2/solar/pv_generation_timeseries.csv')
    
    if not ev_profile.exists():
        print(f"❌ ERROR: EV demand no encontrado en {ev_profile}")
        sys.exit(1)
    
    print(f"\n   Ejecutando dimensionamiento...")
    results = run_bess_sizing(
        out_dir=out_dir,
        mall_energy_kwh_day=33885.0,  # Demanda mall Iquitos
        pv_profile_path=pv_profile,
        ev_profile_path=ev_profile,
        mall_demand_path=None,
        dod=0.80,
        c_rate=0.36,  # v5.2: 0.36 C-rate
        round_kwh=10.0,
        efficiency_roundtrip=0.95,  # v5.2
        autonomy_hours=4.0,
        pv_dc_kw=4050.0,
        sizing_mode='ev_open_hours',
        soc_min_percent=20.0,
        load_scope='total',
        generate_plots=True,
        reports_dir=None,
    )
    
    print(f"\n✅ DIMENSIONAMIENTO BESS COMPLETADO")
    print(f"\n{'='*80}")
    print(f"RESULTADOS FINALES (con datos reales EV λ=2.0):")
    print(f"{'='*80}")
    
    if isinstance(results, dict):
        print(f"\n📊 Capacidad BESS:")
        print(f"   • Capacidad: {results.get('bess_capacity_kwh', 'N/A'):.0f} kWh")
        print(f"   • Potencia: {results.get('bess_power_kw', 'N/A'):.0f} kW")
        print(f"\n⚡ Energía:")
        print(f"   • Total PV: {results.get('total_pv_kwh', 'N/A'):,.0f} kWh/año")
        print(f"   • Demanda total: {results.get('total_load_kwh', 'N/A'):,.0f} kWh/año")
        print(f"   • Importación red: {results.get('total_grid_import_kwh', 'N/A'):,.0f} kWh/año")
        print(f"\n🔋 BESS:")
        print(f"   • Carga/año: {results.get('total_bess_charge_kwh', 'N/A'):,.0f} kWh")
        print(f"   • Descarga/año: {results.get('total_bess_discharge_kwh', 'N/A'):,.0f} kWh")
        print(f"   • Ciclos/día: {results.get('cycles_per_day', 'N/A'):.2f}")
        print(f"\n📈 Eficiencia:")
        print(f"   • Autosuficiencia: {results.get('self_sufficiency', 'N/A')*100:.1f}%")
        print(f"   • SOC min: {results.get('soc_min_percent', 'N/A'):.1f}%")
        print(f"   • SOC max: {results.get('soc_max_percent', 'N/A'):.1f}%")
        print(f"\n✅ Datos guardados en: {out_dir}")
    
    print(f"\n{'='*80}\n")
    
except Exception as e:
    print(f"\n❌ ERROR en dimensionamiento BESS: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("✅ PIPELINE COMPLETADO EXITOSAMENTE")
