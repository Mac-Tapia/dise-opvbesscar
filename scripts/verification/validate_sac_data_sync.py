#!/usr/bin/env python3
"""Validación: SAC <-> datos reales CityLearn v2."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dataset_builder_citylearn.data_loader import (
    load_citylearn_dataset,
    BESS_CAPACITY_KWH, TOTAL_SOCKETS, SOLAR_PV_KWP,
    CO2_FACTOR_GRID_KG_PER_KWH, N_CHARGERS,
)

print("=" * 70)
print("VALIDACION SAC <-> DATOS REALES CITYLEARN v2")
print("=" * 70)

result = load_citylearn_dataset()
issues: list[str] = []

# 1 Solar
solar_df = result["solar"]
n_solar = len(solar_df)
solar_max = solar_df["potencia_kw"].max() if "potencia_kw" in solar_df.columns else -1
solar_sum = solar_df["potencia_kw"].sum() if "potencia_kw" in solar_df.columns else 0
ok_solar = n_solar == 8760 and solar_max <= 4500
print(f"\n[1] SOLAR")
print(f"    Archivo : data/oe2/Generacionsolar/pv_generation_citylearn2024.csv")
print(f"    Filas   : {n_solar}  (esperado 8760) -> {'OK' if n_solar==8760 else 'ERROR'}")
print(f"    Max kW  : {solar_max:.1f} kW (<= 4,500 razonable con 4,050 kWp)")
print(f"    Anual   : {solar_sum:,.0f} kWh/año")
if not ok_solar:
    issues.append(f"Solar: {n_solar} filas (esperado 8760)")

# 2 BESS
bess_df = result["bess"]
n_bess = len(bess_df)
ok_bess = n_bess == 8760 and BESS_CAPACITY_KWH == 2000.0
print(f"\n[2] BESS")
print(f"    Archivo   : data/oe2/bess/bess_ano_2024.csv")
print(f"    Filas     : {n_bess}  (esperado 8760) -> {'OK' if n_bess==8760 else 'ERROR'}")
print(f"    Capacidad : {BESS_CAPACITY_KWH} kWh (esperado 2000) -> {'OK' if BESS_CAPACITY_KWH==2000.0 else 'ERROR'}")
print(f"    Max power : 400 kW (constante)")
if not ok_bess:
    issues.append(f"BESS: {n_bess} filas o cap {BESS_CAPACITY_KWH} != 2000")

# 3 Chargers
ch_df = result["chargers"]
n_ch = len(ch_df)
socket_pwr_cols = [c for c in ch_df.columns if "socket" in c and "charger_power" in c]
n_sockets = len(socket_pwr_cols)
ok_chargers = n_ch == 8760 and n_sockets == 38
print(f"\n[3] CHARGERS")
print(f"    Archivo  : data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
print(f"    Filas    : {n_ch}  (esperado 8760) -> {'OK' if n_ch==8760 else 'ERROR'}")
print(f"    Sockets  : {n_sockets} con charger_power_kw (esperado 38) -> {'OK' if n_sockets==38 else 'ERROR'}")
print(f"    Chargers : {N_CHARGERS} (esperado 19) -> {'OK' if N_CHARGERS==19 else 'ERROR'}")
if not ok_chargers:
    issues.append(f"Chargers: {n_sockets} sockets (esperado 38)")

# 4 Mall demand
dem_df = result["demand"]
n_dem = len(dem_df)
mall_mean = dem_df["mall_demand_kwh"].mean() if "mall_demand_kwh" in dem_df.columns else 0
ok_mall = n_dem == 8760
print(f"\n[4] MALL DEMAND")
print(f"    Archivo : data/oe2/demandamallkwh/demandamallhorakwh.csv")
print(f"    Filas   : {n_dem}  (esperado 8760) -> {'OK' if n_dem==8760 else 'ERROR'}")
print(f"    Media   : {mall_mean:.1f} kWh/h (referencia ~100 kW)")
if not ok_mall:
    issues.append(f"Mall demand: {n_dem} filas (esperado 8760)")

# 5 Combined CityLearn v2
cl_combined = result["combined"]
n_cl = len(cl_combined)
cfg = result.get("config", {})
ready = cfg.get("validation_status", {}).get("ready_for_citylearn_v2", False)
ok_cl = n_cl == 8760 and ready
print(f"\n[5] DATASET COMBINADO CityLearn v2")
print(f"    Directorio              : data/iquitos_ev_mall/")
print(f"    Filas                   : {n_cl}  (esperado 8760) -> {'OK' if n_cl==8760 else 'ERROR'}")
print(f"    Columnas                : {len(cl_combined.columns)}")
print(f"    ready_for_citylearn_v2  : {ready}")
if not ok_cl:
    issues.append(f"CityLearn combined: {n_cl} filas, ready={ready}")

# 6 Constantes SAC (data_loader.py -> train_sac.py)
print(f"\n[6] CONSTANTES SINCRONIZADAS (data_loader -> train_sac)")
print(f"    CO2_FACTOR_GRID : {CO2_FACTOR_GRID_KG_PER_KWH} kg/kWh  (esperado 0.4521)")
print(f"    SOLAR_PV_KWP    : {SOLAR_PV_KWP} kWp  (esperado 4050)")
print(f"    BESS_CAPACITY   : {BESS_CAPACITY_KWH} kWh  (esperado 2000)")
print(f"    TOTAL_SOCKETS   : {TOTAL_SOCKETS}    (esperado 38)")

ok_consts = (
    CO2_FACTOR_GRID_KG_PER_KWH == 0.4521 and
    SOLAR_PV_KWP == 4050.0 and
    BESS_CAPACITY_KWH == 2000.0 and
    TOTAL_SOCKETS == 38
)
if not ok_consts:
    issues.append("Constantes del data_loader no coinciden con esperado")

# Resumen
print(f"\n{'='*70}")
print("RESUMEN SINCRONIZACION SAC <-> CITYLEARN v2:")
checks = [
    ("Solar (8760 h, 4050 kWp)", ok_solar),
    ("BESS (8760 h, 2000 kWh)", ok_bess),
    ("Chargers (8760 h, 38 sockets)", ok_chargers),
    ("Mall demand (8760 h)", ok_mall),
    ("CityLearn v2 combined", ok_cl),
    ("Constantes data_loader", ok_consts),
]
for name, ok in checks:
    print(f"  {'[OK]' if ok else '[ERROR]'} {name}")

print()
if not issues:
    print("RESULTADO: SAC conectado y SINCRONIZADO correctamente a datos reales CityLearn v2")
else:
    print("RESULTADO: PROBLEMAS DETECTADOS:")
    for issue in issues:
        print(f"  - {issue}")
print("=" * 70)
