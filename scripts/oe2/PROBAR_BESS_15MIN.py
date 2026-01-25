"""
Script de prueba para verificar que bess.py funciona correctamente
con el perfil de carga EV de 15 minutos
"""
from pathlib import Path
import sys

# Agregar src al path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from iquitos_citylearn.oe2.bess import run_bess_sizing

print("=" * 80)
print("PRUEBA DE BESS CON PERFIL DE 15 MINUTOS")
print("=" * 80)

# Rutas de archivos
base_dir = Path(__file__).parent
data_dir = base_dir / "data" / "oe2"
out_dir = base_dir / "data" / "oe2" / "interim"
reports_dir = base_dir / "reports"  # Para guardar gráficas

pv_profile_path = data_dir / "pv_profile_24h.csv"
ev_profile_path = data_dir / "perfil_horario_carga.csv"
mall_demand_path = data_dir / "demanda_mall_real.csv"

# Verificar archivos
print("\n📁 Verificando archivos...")
print(f"   PV profile: {pv_profile_path.exists()} - {pv_profile_path}")
print(f"   EV profile: {ev_profile_path.exists()} - {ev_profile_path}")
print(f"   Mall demand: {mall_demand_path.exists()} - {mall_demand_path}")

if not ev_profile_path.exists():
    print("\n❌ ERROR: No se encuentra el perfil EV de 15 minutos")
    print(f"   Ejecuta primero: GENERAR_PERFIL_15MIN.py")
    sys.exit(1)

# Parámetros BESS
print("\n⚙️ Parámetros de dimensionamiento:")
print("   - DoD: 80% (SOC 20%-100%)")
print("   - Eficiencia: 95%")
print("   - C-rate: 0.60")
print("   - Modo: ev_open_hours (solo déficit EV)")

# Ejecutar dimensionamiento
try:
    result = run_bess_sizing(
        out_dir=out_dir,
        reports_dir=reports_dir,  # Guardar gráficas en reports/oe2/bess/
        mall_energy_kwh_day=33885,  # Demanda mall diaria
        pv_profile_path=pv_profile_path,
        ev_profile_path=ev_profile_path,
        mall_demand_path=mall_demand_path if mall_demand_path.exists() else None,
        dod=0.80,  # 80% DoD (SOC 20%-100%)
        c_rate=0.60,
        efficiency_roundtrip=0.95,
        sizing_mode="ev_open_hours",
        soc_min_percent=20.0,  # SOC mínimo 20%
        generate_plots=True,
        year=2024,
    )

    print("\n" + "=" * 80)
    print("✅ DIMENSIONAMIENTO COMPLETADO EXITOSAMENTE")
    print("=" * 80)

    # Mostrar resultados clave
    if isinstance(result, dict):
        print("\n📊 RESULTADOS:")
        if 'capacity_kwh' in result:
            print(f"   Capacidad BESS: {result['capacity_kwh']:.0f} kWh")
        if 'power_kw' in result:
            print(f"   Potencia BESS: {result['power_kw']:.0f} kW")
        if 'metrics' in result:
            metrics = result['metrics']
            if 'self_sufficiency' in metrics:
                print(f"   Autosuficiencia: {metrics['self_sufficiency']*100:.1f}%")
            if 'cycles_per_day' in metrics:
                print(f"   Ciclos/día: {metrics['cycles_per_day']:.2f}")

    print("\n📁 Archivos generados en:")
    print(f"   {out_dir}")

except Exception as e:
    print("\n" + "=" * 80)
    print("❌ ERROR EN DIMENSIONAMIENTO")
    print("=" * 80)
    print(f"\n{type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ Prueba completada")
