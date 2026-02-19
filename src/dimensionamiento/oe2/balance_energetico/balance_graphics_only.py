"""
Balance Energetico - Modulo de Visualizacion Unicamente v5.4.

Este modulo contiene SOLO los metodos de generacion de graficas para el analisis 
de balance energetico del sistema electrico de Iquitos.

Recibe DataFrames ya calculados y genera las visualizaciones correspondientes.

Graficas generadas:
1. Integral - Todas las curvas superpuestas
2. Flujo Energetico - Sankey integrado (CON EV y BESS desagregados desde chargers.py)
3. 5-day Balance - Flujos horarios en 5 dias representativos
4. Daily Balance - Balance energetico diario (365 dias)
5. Sources Distribution - Distribucion de fuentes (anual)
6. Energy Cascade - Cascada energetica (Sankey simplificado)
7. BESS SOC - Estado de carga BESS (365 dias)
8. CO2 Emissions - Analisis diario de emisiones
9. PV Utilization - Utilizacion mensual de PV
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

# Integración con perfil EV desde chargers.py
from .ev_profile_integration import (
    MOTO_SPEC,
    MOTOTAXI_SPEC,
    CHARGING_EFFICIENCY,
)


@dataclass(frozen=True)
class VisualizationConfig:
    """Configuracion minima de visualizacion."""
    pv_capacity_kwp: float = 4050.0
    demand_peak_limit_kw: float = 1900.0
    bess_capacity_kwh: float = 1700.0
    bess_power_kw: float = 400.0
    co2_intensity_kg_per_kwh: float = 0.4521


class BalanceEnergeticoGraphics:
    """Generador de graficas para analisis de balance energetico v5.4.
    
    Recibe DataFrames precalculados y genera visualizaciones.
    
    Uso:
    ----
    graphics = BalanceEnergeticoGraphics(df_balance, config)
    graphics.plot_all(output_dir)
    """
    
    def __init__(self, df_balance: pd.DataFrame, config: Optional[VisualizationConfig] = None):
        """
        Inicializa el generador de graficas.
        
        Args:
            df_balance: DataFrame con columnas [pv_generation_kw, ev_demand_kw, mall_demand_kw,
                       total_demand_kw, pv_to_demand_kw, pv_surplus_kw, bess_charge_kw,
                       bess_discharge_kw, bess_soc_percent, demand_from_grid_kw, etc.]
            config: Configuracion de visualizacion (usa defaults si es None)
        """
        self.df_balance = df_balance
        self.config = config or VisualizationConfig()
    
    def plot_all(self, out_dir: Optional[Path] = None) -> None:
        """Genera todas las graficas de balance energetico.
        
        Args:
            out_dir: Directorio para guardar graficas (default: reports/balance_energetico)
        """
        if out_dir is None:
            out_dir = Path("reports/balance_energetico")
        
        out_dir.mkdir(parents=True, exist_ok=True)
        
        df = self.df_balance
        print(f"\nGenerando graficas de balance energetico en {out_dir}...")
        
        # Generar todas las graficas
        self._plot_integral_curves(df, out_dir)
        self._plot_energy_flow_diagram(df, out_dir)
        self._plot_5day_balance(df, out_dir)
        self._plot_daily_balance(df, out_dir)
        self._plot_sources_distribution(df, out_dir)
        self._plot_energy_cascade(df, out_dir)
        self._plot_bess_soc(df, out_dir)
        self._plot_co2_emissions(df, out_dir)
        self._plot_pv_utilization(df, out_dir)
        
        print(f"✓ Todas las graficas generadas en {out_dir}")
    
    def _plot_integral_curves(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 0: Curvas integrales superpuestas."""
        pass  # Implementar
    
    def _plot_energy_flow_diagram(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 0.5: Diagrama de flujo energetico (CON PERFIL EV DESAGREGADO)."""
        pass  # Implementar
    
    def _plot_5day_balance(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 1: Balance energetico en 5 dias representativos."""
        pass  # Implementar
    
    def _plot_daily_balance(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 2: Balance energetico diario (365 dias)."""
        pass  # Implementar
    
    def _plot_sources_distribution(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 3: Distribucion de fuentes energeticas."""
        pass  # Implementar
    
    def _plot_energy_cascade(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 4: Cascada energetica (Sankey simplificado)."""
        pass  # Implementar
    
    def _plot_bess_soc(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 5: Estado de carga BESS (365 dias)."""
        pass  # Implementar
    
    def _plot_co2_emissions(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 6: Emisiones de CO2 (analisis diario)."""
        pass  # Implementar
    
    def _plot_pv_utilization(self, df: pd.DataFrame, out_dir: Path) -> None:
        """Grafica 7: Utilizacion mensual de PV."""
        pass  # Implementar


# Alias para retrocompatibilidad
BalanceEnergeticoSystem = BalanceEnergeticoGraphics
