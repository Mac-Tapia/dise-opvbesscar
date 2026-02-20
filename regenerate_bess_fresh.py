from src.dimensionamiento.oe2.disenobess.bess import run_bess_sizing
from pathlib import Path

print('=' * 80)
print('REGENERANDO DATASET BESS COMPLETO')
print('=' * 80)

result = run_bess_sizing(
    out_dir=Path('data/oe2/bess'),
    pv_profile_path=Path('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv'),
    ev_profile_path=Path('data/oe2/demandaEV/EV_motos_mototaxis_ano_2024.csv'),
    mall_demand_path=Path('data/iquitos_ev_mall/mall_demand.csv'),
    fixed_capacity_kwh=2000.0,  # v5.9
    fixed_power_kw=400.0,  # v5.9
    year=2024,
    generate_plots=False  # Solo regenerar datos, no gráficas
)

print('\n✓ Dataset BESS regenerado correctamente')
annual_charge = result["metrics"]["annual_charge_kwh"]
annual_discharge = result["metrics"]["annual_discharge_kwh"]
print(f'  Descarga BESS anual: {annual_discharge:,.0f} kWh')
print(f'  Carga BESS anual: {annual_charge:,.0f} kWh')
