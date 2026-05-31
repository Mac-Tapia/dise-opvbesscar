#!/usr/bin/env python3
from __future__ import annotations

"""
CO2 formulas for OE3.

This module keeps the hour-level accounting helper used by historical scripts, but the
current source of truth for agent selection is:

  reports/oe3/agents_comparison_canonical.json

Canonical OE3 result as of 2026-05-30: PPO selected, F2 minimum
3,657,483 kg CO2/year in episode 49.
"""

from dataclasses import dataclass


CO2_FACTOR_IQUITOS: float = 0.4521
CO2_FACTOR_MOTO_KG_KWH: float = 0.87
CO2_FACTOR_MOTOTAXI_KG_KWH: float = 0.54
FRAC_MOTOS_REAL: float = 0.8458
FRAC_MOTOTAXIS_REAL: float = 0.1542
CO2_FACTOR_EV_PONDERADO: float = round(
    FRAC_MOTOS_REAL * CO2_FACTOR_MOTO_KG_KWH
    + FRAC_MOTOTAXIS_REAL * CO2_FACTOR_MOTOTAXI_KG_KWH,
    4,
)


@dataclass
class CO2Resultado:
    co2_directo_baseline_kg: float
    co2_indirecto_ev_baseline_kg: float
    co2_indirecto_mall_baseline_kg: float
    co2_indirecto_baseline_kg: float
    co2_total_baseline_kg: float
    co2_reduccion_directa_baseline_kg: float
    co2_reduccion_indirecta_baseline_kg: float
    co2_directo_control_kg: float
    co2_indirecto_control_kg: float
    co2_total_control_kg: float
    co2_reduccion_directa_control_kg: float
    co2_reduccion_indirecta_control_kg: float
    co2_solar_indirect_kg: float
    co2_solar_ev_kg: float
    co2_solar_mall_kg: float
    co2_solar_bess_kg: float
    co2_solar_export_kg: float
    co2_bess_discharge_indirect_kg: float
    co2_reduccion_directa_kg: float
    co2_reduccion_indirecta_kg: float
    co2_impacto_control_kg: float
    co2_total_sistema_evitado_kg: float


def compute_co2_baseline_control(
    ev_demand_dataset_kwh: float,
    mall_demand_kwh_h: float,
    grid_import_kwh: float,
    co2_indirecto_solar_kg: float,
    co2_indirecto_bess_kg: float,
    co2_avoided_direct_kg: float = 0.0,
    co2_reduccion_directa_kg: float = 0.0,
    solar_total_kwh: float = 0.0,
    bess_discharge_kwh: float = 0.0,
    grid_export_kwh: float = 0.0,
) -> CO2Resultado:
    """Compute baseline/control CO2 accounting for one hourly timestep."""
    direct_kg = co2_avoided_direct_kg if co2_avoided_direct_kg else co2_reduccion_directa_kg

    co2_directo_baseline_kg = 0.0
    co2_indirecto_ev_baseline_kg = ev_demand_dataset_kwh * CO2_FACTOR_IQUITOS
    co2_indirecto_mall_baseline_kg = mall_demand_kwh_h * CO2_FACTOR_IQUITOS
    co2_indirecto_baseline_kg = co2_indirecto_ev_baseline_kg + co2_indirecto_mall_baseline_kg
    co2_total_baseline_kg = co2_indirecto_baseline_kg

    co2_directo_control_kg = 0.0
    co2_indirecto_control_kg = grid_import_kwh * CO2_FACTOR_IQUITOS
    co2_total_control_kg = co2_indirecto_control_kg

    ev_solar_kwh = min(max(solar_total_kwh, 0.0), max(ev_demand_dataset_kwh, 0.0))
    remaining_solar_kwh = max(0.0, solar_total_kwh - ev_solar_kwh)
    mall_solar_kwh = min(remaining_solar_kwh, max(mall_demand_kwh_h, 0.0))
    remaining_solar_kwh = max(0.0, remaining_solar_kwh - mall_solar_kwh)
    export_solar_kwh = max(grid_export_kwh, 0.0)
    bess_solar_kwh = max(0.0, remaining_solar_kwh - export_solar_kwh)

    co2_solar_indirect_kg = solar_total_kwh * CO2_FACTOR_IQUITOS
    co2_solar_ev_kg = ev_solar_kwh * CO2_FACTOR_IQUITOS
    co2_solar_mall_kg = mall_solar_kwh * CO2_FACTOR_IQUITOS
    co2_solar_bess_kg = bess_solar_kwh * CO2_FACTOR_IQUITOS
    co2_solar_export_kg = export_solar_kwh * CO2_FACTOR_IQUITOS
    co2_bess_discharge_indirect_kg = bess_discharge_kwh * CO2_FACTOR_IQUITOS

    co2_reduccion_indirecta_out = co2_indirecto_baseline_kg - co2_indirecto_control_kg
    co2_total_sistema_evitado_kg = direct_kg + co2_reduccion_indirecta_out

    return CO2Resultado(
        co2_directo_baseline_kg=co2_directo_baseline_kg,
        co2_indirecto_ev_baseline_kg=co2_indirecto_ev_baseline_kg,
        co2_indirecto_mall_baseline_kg=co2_indirecto_mall_baseline_kg,
        co2_indirecto_baseline_kg=co2_indirecto_baseline_kg,
        co2_total_baseline_kg=co2_total_baseline_kg,
        co2_reduccion_directa_baseline_kg=direct_kg,
        co2_reduccion_indirecta_baseline_kg=0.0,
        co2_directo_control_kg=co2_directo_control_kg,
        co2_indirecto_control_kg=co2_indirecto_control_kg,
        co2_total_control_kg=co2_total_control_kg,
        co2_reduccion_directa_control_kg=direct_kg,
        co2_reduccion_indirecta_control_kg=co2_indirecto_solar_kg + co2_indirecto_bess_kg,
        co2_solar_indirect_kg=co2_solar_indirect_kg,
        co2_solar_ev_kg=co2_solar_ev_kg,
        co2_solar_mall_kg=co2_solar_mall_kg,
        co2_solar_bess_kg=co2_solar_bess_kg,
        co2_solar_export_kg=co2_solar_export_kg,
        co2_bess_discharge_indirect_kg=co2_bess_discharge_indirect_kg,
        co2_reduccion_directa_kg=direct_kg,
        co2_reduccion_indirecta_kg=co2_reduccion_indirecta_out,
        co2_impacto_control_kg=co2_reduccion_indirecta_out,
        co2_total_sistema_evitado_kg=co2_total_sistema_evitado_kg,
    )
