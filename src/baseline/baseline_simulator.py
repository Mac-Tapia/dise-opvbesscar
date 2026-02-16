"""
Simulacion de baseline sin control inteligente.

Calcula CO2, cost, y otros KPIs para comparacion con RL agents.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class BaselineResults:
    """Resultados de simulacion baseline."""
    # Energia (kWh/ano)
    solar_generation_kwh: float
    charger_demand_kwh: float
    mall_demand_kwh: float
    total_demand_kwh: float

    # Flujo de energia
    solar_to_chargers_kwh: float
    solar_to_mall_kwh: float
    solar_to_bess_kwh: float
    solar_curtailed_kwh: float
    bess_discharge_to_chargers_kwh: float
    bess_discharge_to_mall_kwh: float
    grid_import_chargers_kwh: float
    grid_import_mall_kwh: float
    grid_export_kwh: float

    # Emisiones
    co2_from_chargers_kg: float
    co2_from_mall_kg: float
    co2_total_kg: float
    co2_total_t: float

    # Costos (USD/ano)
    cost_chargers_usd: float
    cost_mall_usd: float
    cost_total_usd: float

    # KPIs
    solar_utilization_pct: float
    self_consumption_pct: float
    peak_demand_kw: float
    avg_demand_kw: float

    def to_dict(self) -> Dict:
        """Convertir a diccionario."""
        return {
            'solar_generation_kwh': self.solar_generation_kwh,
            'charger_demand_kwh': self.charger_demand_kwh,
            'mall_demand_kwh': self.mall_demand_kwh,
            'total_demand_kwh': self.total_demand_kwh,
            'solar_to_chargers_kwh': self.solar_to_chargers_kwh,
            'solar_to_mall_kwh': self.solar_to_mall_kwh,
            'solar_to_bess_kwh': self.solar_to_bess_kwh,
            'solar_curtailed_kwh': self.solar_curtailed_kwh,
            'bess_discharge_to_chargers_kwh': self.bess_discharge_to_chargers_kwh,
            'bess_discharge_to_mall_kwh': self.bess_discharge_to_mall_kwh,
            'grid_import_chargers_kwh': self.grid_import_chargers_kwh,
            'grid_import_mall_kwh': self.grid_import_mall_kwh,
            'grid_export_kwh': self.grid_export_kwh,
            'co2_from_chargers_kg': self.co2_from_chargers_kg,
            'co2_from_mall_kg': self.co2_from_mall_kg,
            'co2_total_kg': self.co2_total_kg,
            'co2_total_t': self.co2_total_t,
            'cost_chargers_usd': self.cost_chargers_usd,
            'cost_mall_usd': self.cost_mall_usd,
            'cost_total_usd': self.cost_total_usd,
            'solar_utilization_pct': self.solar_utilization_pct,
            'self_consumption_pct': self.self_consumption_pct,
            'peak_demand_kw': self.peak_demand_kw,
            'avg_demand_kw': self.avg_demand_kw,
        }


class BaselineSimulator:
    """Simulacion de baseline: sin control inteligente."""

    def __init__(
        self,
        carbon_intensity_kg_per_kwh: float = 0.4521,
        tariff_usd_per_kwh: float = 0.20,
        bess_capacity_kwh: float = 2000,
        bess_power_kw: float = 1200,
        bess_efficiency: float = 0.95,
        bess_min_soc: float = 0.20,
    ):
        self.carbon_intensity = carbon_intensity_kg_per_kwh
        self.tariff = tariff_usd_per_kwh
        self.bess_capacity = bess_capacity_kwh
        self.bess_power = bess_power_kw
        self.bess_efficiency = bess_efficiency
        self.bess_min_soc = bess_min_soc

        logger.info(f"BaselineSimulator initialized:")
        logger.info(f"  - Carbon intensity: {self.carbon_intensity} kg CO₂/kWh")
        logger.info(f"  - Tariff: ${self.tariff}/kWh")
        logger.info(f"  - BESS: {self.bess_capacity} kWh, {self.bess_power} kW")

    def simulate(
        self,
        solar_generation: np.ndarray,  # 8,760 hourly kW
        charger_demand: np.ndarray,      # 8,760 hourly kW
        mall_demand: np.ndarray,         # 8,760 hourly kW
    ) -> Tuple[BaselineResults, pd.DataFrame]:
        """
        Simular baseline sin control inteligente.

        Estrategia:
        1. Chargers se alimentan de: Solar -> Grid (demanda directa)
        2. Excedente solar se guarda en BESS (si hay espacio)
        3. Cuando solar insuficiente, usar BESS luego Grid
        """
        logger.info("=== Simulacion Baseline ===")

        n_timesteps = len(solar_generation)

        # Arrays para tracking
        bess_soc = np.zeros(n_timesteps)
        bess_soc[0] = 0.5  # Comenzar en 50%

        solar_to_chargers = np.zeros(n_timesteps)
        solar_to_mall = np.zeros(n_timesteps)
        solar_to_bess = np.zeros(n_timesteps)
        solar_curtailed = np.zeros(n_timesteps)

        bess_discharge_to_chargers = np.zeros(n_timesteps)
        bess_discharge_to_mall = np.zeros(n_timesteps)
        bess_charge = np.zeros(n_timesteps)

        grid_import_chargers = np.zeros(n_timesteps)
        grid_import_mall = np.zeros(n_timesteps)
        grid_export = np.zeros(n_timesteps)

        # Simulacion horaria
        for t in range(n_timesteps):
            # Disponibilidad BESS
            bess_min_kwh = self.bess_capacity * self.bess_min_soc
            bess_current_kwh = bess_soc[t] * self.bess_capacity
            bess_available_discharge = max(0, (bess_current_kwh - bess_min_kwh) / self.bess_efficiency)
            bess_available_charge = (self.bess_capacity - bess_current_kwh) * self.bess_efficiency

            # Demanda
            charger_dem = charger_demand[t]
            mall_dem = mall_demand[t]
            total_dem = charger_dem + mall_dem

            # Disponibilidad solar
            solar_avail = solar_generation[t]

            # Estrategia baseline simple:
            # 1. Alimentar chargers primero (prioridad EV)
            # 2. Luego mall
            # 3. Excedente a BESS

            # Chargers: Solar -> BESS -> Grid
            if solar_avail >= charger_dem:
                solar_to_chargers[t] = charger_dem
                solar_remaining = solar_avail - charger_dem
            else:
                solar_to_chargers[t] = solar_avail
                solar_remaining = 0

                # Usar BESS
                bess_discharge_charger = min(bess_available_discharge, charger_dem - solar_avail)
                bess_discharge_to_chargers[t] = bess_discharge_charger
                bess_available_discharge -= bess_discharge_charger

                # Complemento Grid
                grid_import_chargers[t] = charger_dem - solar_avail - bess_discharge_charger

            # Mall: Solar -> BESS -> Grid
            if solar_remaining >= mall_dem:
                solar_to_mall[t] = mall_dem
                solar_remaining -= mall_dem
            else:
                solar_to_mall[t] = solar_remaining
                mall_remaining = mall_dem - solar_remaining

                bess_discharge_mall = min(bess_available_discharge, mall_remaining)
                bess_discharge_to_mall[t] = bess_discharge_mall
                bess_available_discharge -= bess_discharge_mall

                grid_import_mall[t] = mall_remaining - bess_discharge_mall

            # Excedente solar a BESS (si hay espacio)
            if solar_remaining > 0:
                bess_charge_possible = min(bess_available_charge, solar_remaining)
                bess_charge[t] = bess_charge_possible
                solar_to_bess[t] = bess_charge_possible
                solar_curtailed[t] = max(0, solar_remaining - bess_charge_possible)
            else:
                solar_curtailed[t] = 0

            # Actualizar BESS SOC
            bess_energy_change = (
                bess_charge[t] -
                bess_discharge_to_chargers[t] -
                bess_discharge_to_mall[t]
            ) / self.bess_capacity

            if t < n_timesteps - 1:
                bess_soc[t + 1] = np.clip(
                    bess_soc[t] + bess_energy_change,
                    self.bess_min_soc,
                    1.0
                )

        # Calculos anuales
        total_solar = solar_generation.sum()
        total_charger_dem = charger_demand.sum()
        total_mall_dem = mall_demand.sum()
        total_dem = total_charger_dem + total_mall_dem

        total_grid_import = grid_import_chargers.sum() + grid_import_mall.sum()
        total_solar_to_loads = solar_to_chargers.sum() + solar_to_mall.sum()

        # CO2
        co2_chargers = grid_import_chargers.sum() * self.carbon_intensity
        co2_mall = grid_import_mall.sum() * self.carbon_intensity
        co2_total = co2_chargers + co2_mall

        # Costos
        cost_chargers = grid_import_chargers.sum() * self.tariff
        cost_mall = grid_import_mall.sum() * self.tariff
        cost_total = cost_chargers + cost_mall

        # KPIs
        solar_utilization = (total_solar_to_loads + solar_to_bess.sum()) / max(total_solar, 1e-9)
        self_consumption = total_solar_to_loads / max(total_solar, 1e-9)
        peak_demand = np.max(charger_demand + mall_demand)
        avg_demand = total_dem / len(charger_demand)

        results = BaselineResults(
            solar_generation_kwh=total_solar,
            charger_demand_kwh=total_charger_dem,
            mall_demand_kwh=total_mall_dem,
            total_demand_kwh=total_dem,
            solar_to_chargers_kwh=solar_to_chargers.sum(),
            solar_to_mall_kwh=solar_to_mall.sum(),
            solar_to_bess_kwh=solar_to_bess.sum(),
            solar_curtailed_kwh=solar_curtailed.sum(),
            bess_discharge_to_chargers_kwh=bess_discharge_to_chargers.sum(),
            bess_discharge_to_mall_kwh=bess_discharge_to_mall.sum(),
            grid_import_chargers_kwh=grid_import_chargers.sum(),
            grid_import_mall_kwh=grid_import_mall.sum(),
            grid_export_kwh=0,  # Iquitos no exporta a grid
            co2_from_chargers_kg=co2_chargers,
            co2_from_mall_kg=co2_mall,
            co2_total_kg=co2_total,
            co2_total_t=co2_total / 1000,
            cost_chargers_usd=cost_chargers,
            cost_mall_usd=cost_mall,
            cost_total_usd=cost_total,
            solar_utilization_pct=solar_utilization * 100,
            self_consumption_pct=self_consumption * 100,
            peak_demand_kw=peak_demand,
            avg_demand_kw=avg_demand,
        )

        # DataFrame de detalles horarios
        details_df = pd.DataFrame({
            'solar_generation_kw': solar_generation,
            'charger_demand_kw': charger_demand,
            'mall_demand_kw': mall_demand,
            'solar_to_chargers_kw': solar_to_chargers,
            'solar_to_mall_kw': solar_to_mall,
            'solar_to_bess_kw': solar_to_bess,
            'solar_curtailed_kw': solar_curtailed,
            'bess_discharge_to_chargers_kw': bess_discharge_to_chargers,
            'bess_discharge_to_mall_kw': bess_discharge_to_mall,
            'grid_import_chargers_kw': grid_import_chargers,
            'grid_import_mall_kw': grid_import_mall,
            'bess_soc': bess_soc,
            'grid_import_total_kw': grid_import_chargers + grid_import_mall,
        })

        # Log resultados
        logger.info(f"\n=== BASELINE RESULTS ===")
        logger.info(f"Solar generation: {results.solar_generation_kwh:,.0f} kWh/ano")
        logger.info(f"Charger demand: {results.charger_demand_kwh:,.0f} kWh/ano")
        logger.info(f"Mall demand: {results.mall_demand_kwh:,.0f} kWh/ano")
        logger.info(f"\nGrid import (chargers): {results.grid_import_chargers_kwh:,.0f} kWh/ano")
        logger.info(f"Grid import (mall): {results.grid_import_mall_kwh:,.0f} kWh/ano")
        logger.info(f"Grid import total: {results.grid_import_chargers_kwh + results.grid_import_mall_kwh:,.0f} kWh/ano")
        logger.info(f"\nCO₂ emissions: {results.co2_total_t:,.1f} t/ano")
        logger.info(f"  - From chargers: {results.co2_from_chargers_kg/1000:,.1f} t/ano")
        logger.info(f"  - From mall: {results.co2_from_mall_kg/1000:,.1f} t/ano")
        logger.info(f"\nCosts: ${results.cost_total_usd:,.0f}/ano")
        logger.info(f"  - Chargers: ${results.cost_chargers_usd:,.0f}/ano")
        logger.info(f"  - Mall: ${results.cost_mall_usd:,.0f}/ano")
        logger.info(f"\nKPIs:")
        logger.info(f"  - Solar utilization: {results.solar_utilization_pct:.1f}%")
        logger.info(f"  - Self-consumption: {results.self_consumption_pct:.1f}%")
        logger.info(f"  - Peak demand: {results.peak_demand_kw:.0f} kW")
        logger.info(f"  - Avg demand: {results.avg_demand_kw:.0f} kW")

        return results, details_df

    def save_results(
        self,
        results: BaselineResults,
        details_df: pd.DataFrame,
        output_dir: Path | str,
    ):
        """Guardar resultados de baseline."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # JSON summary
        with open(output_dir / "baseline_summary.json", 'w') as f:
            json.dump(results.to_dict(), f, indent=2)

        # CSV details
        details_df.to_csv(output_dir / "baseline_hourly_details.csv", index=False)

        logger.info(f"[OK] Baseline results saved to {output_dir}")
