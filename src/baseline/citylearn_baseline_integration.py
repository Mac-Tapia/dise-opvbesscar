"""CityLearn Baseline Integration (v5.4).

Integra calculos de baseline con CityLearnv2 para:
1. Comparar agentes RL contra baselines
2. Validar performance relativo
3. Generar reportes de mejora

Conecta con:
- BaselineCalculator: Calcula baselines CON_SOLAR y SIN_SOLAR
- AgentTrainer: Registra resultados para comparacion
- dataset_builder.py: Usa mismo conjunto de datos OE2 v5.4
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class BaselineCityLearnIntegration:
    """Integra baselines con CityLearn v2 para entrenamiento de agentes y comparacion."""

    def __init__(self, output_dir: str = 'outputs/baselines'):
        """Initialize integration.
        
        Args:
            output_dir: Directory for baseline results
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Import BaselineCalculator only when needed
        self._calculator = None
    
    @property
    def calculator(self):
        """Lazy load BaselineCalculator."""
        if self._calculator is None:
            from .baseline_calculator_v2 import BaselineCalculator
            self._calculator = BaselineCalculator(co2_intensity=0.4521)
        return self._calculator
    
    def compute_baselines(self) -> Dict[str, Dict[str, Any]]:
        """Compute both CON_SOLAR and SIN_SOLAR baselines.
        
        Returns:
            Dict with 'con_solar' and 'sin_solar' baseline results
        """
        logger.info("[CityLearn Integration] Computing baselines...")
        con_solar, sin_solar = self.calculator.calculate_all_baselines()
        
        return {
            'con_solar': con_solar,
            'sin_solar': sin_solar,
        }
    
    def save_baselines(self, baselines: Dict[str, Dict[str, Any]]) -> None:
        """Save baseline results to disk.
        
        Args:
            baselines: Dict with baseline results from compute_baselines()
        """
        self.calculator.save_baseline_results(
            baselines['con_solar'],
            baselines['sin_solar'],
            str(self.output_dir)
        )
    
    def compare_agent_vs_baseline(
        self,
        agent_name: str,
        agent_co2_kg: float,
        agent_grid_import_kwh: float,
        baseline: str = 'con_solar'
    ) -> Dict[str, float]:
        """Compare agent performance vs baseline.
        
        Args:
            agent_name: Name of agent (e.g., 'SAC', 'PPO', 'A2C')
            agent_co2_kg: CO2 emissions of agent (kg/year)
            agent_grid_import_kwh: Grid import of agent (kWh/year)
            baseline: Which baseline to compare against ('con_solar' or 'sin_solar')
        
        Returns:
            Dict with comparison metrics:
            - co2_improvement_pct: % reduction vs baseline
            - grid_reduction_pct: % grid import reduction
            - absolute_co2_reduction_kg: Absolute CO2 reduction
        """
        # Load baseline results
        baseline_file = self.output_dir / f'baseline_{baseline}.json'
        
        if not baseline_file.exists():
            logger.warning(f"Baseline file not found: {baseline_file}")
            logger.info("Computing baselines...")
            baselines = self.compute_baselines()
            self.save_baselines(baselines)
        
        # Load baseline data
        with open(baseline_file, 'r') as f:
            baseline_data = json.load(f)
        
        baseline_co2_kg = baseline_data['co2_grid_kg']
        baseline_grid_kwh = baseline_data['grid_import_kwh']
        
        # Calculate improvements
        co2_reduction_kg = baseline_co2_kg - agent_co2_kg
        co2_improvement_pct = (co2_reduction_kg / baseline_co2_kg * 100) if baseline_co2_kg > 0 else 0
        
        grid_reduction_kwh = baseline_grid_kwh - agent_grid_import_kwh
        grid_reduction_pct = (grid_reduction_kwh / baseline_grid_kwh * 100) if baseline_grid_kwh > 0 else 0
        
        return {
            'agent': agent_name,
            'co2_improvement_pct': co2_improvement_pct,
            'co2_reduction_kg': co2_reduction_kg,
            'co2_reduction_t': co2_reduction_kg / 1000,
            'grid_reduction_pct': grid_reduction_pct,
            'grid_reduction_kwh': grid_reduction_kwh,
            'baseline_used': baseline,
            'agent_co2_kg': agent_co2_kg,
            'baseline_co2_kg': baseline_co2_kg,
        }
    
    def generate_comparison_report(
        self,
        agent_results: Dict[str, Dict[str, Any]],
        output_file: Optional[str] = None
    ) -> pd.DataFrame:
        """Generate comprehensive comparison report.
        
        Args:
            agent_results: Dict mapping agent names to results
            output_file: Optional output CSV file
        
        Returns:
            DataFrame with comparison results
        """
        # Load baselines
        con_solar_file = self.output_dir / 'baseline_con_solar.json'
        sin_solar_file = self.output_dir / 'baseline_sin_solar.json'
        
        if not con_solar_file.exists():
            logger.info("computing baselines...")
            baselines = self.compute_baselines()
            self.save_baselines(baselines)
        
        with open(con_solar_file, 'r') as f:
            con_solar_base = json.load(f)
        with open(sin_solar_file, 'r') as f:
            sin_solar_base = json.load(f)
        
        rows = []
        
        # Add baselines to report
        rows.append({
            'agent': 'BASELINE_CON_SOLAR',
            'co2_kg_anual': con_solar_base['co2_grid_kg'],
            'co2_t_anual': con_solar_base['co2_t'],
            'grid_import_kwh': con_solar_base['grid_import_kwh'],
            'solar_generation_kwh': con_solar_base['solar_generation_kwh'],
            'improvement_vs_con_solar_pct': 0.0,  # Reference
            'improvement_vs_sin_solar_pct': (sin_solar_base['co2_grid_kg'] - con_solar_base['co2_grid_kg']) / sin_solar_base['co2_grid_kg'] * 100,
        })
        
        rows.append({
            'agent': 'BASELINE_SIN_SOLAR',
            'co2_kg_anual': sin_solar_base['co2_grid_kg'],
            'co2_t_anual': sin_solar_base['co2_t'],
            'grid_import_kwh': sin_solar_base['grid_import_kwh'],
            'solar_generation_kwh': sin_solar_base['solar_generation_kwh'],
            'improvement_vs_con_solar_pct': (sin_solar_base['co2_grid_kg'] - con_solar_base['co2_grid_kg']) / sin_solar_base['co2_grid_kg'] * 100,
            'improvement_vs_sin_solar_pct': 0.0,  # No improvement (worst case)
        })
        
        # Add agent results
        for agent_name, result in agent_results.items():
            agent_co2_kg = result.get('co2_kg', result.get('co2_kg_anual'))
            agent_grid_kwh = result.get('grid_import_kwh', result.get('grid_import_kwh_anual'))
            
            if agent_co2_kg is None or agent_grid_kwh is None:
                logger.warning(f"Invalid result format for {agent_name}, skipping")
                continue
            
            # Calculate improvements vs both baselines
            co2_vs_con_solar = (con_solar_base['co2_grid_kg'] - agent_co2_kg) / con_solar_base['co2_grid_kg'] * 100
            co2_vs_sin_solar = (sin_solar_base['co2_grid_kg'] - agent_co2_kg) / sin_solar_base['co2_grid_kg'] * 100
            
            rows.append({
                'agent': agent_name,
                'co2_kg_anual': agent_co2_kg,
                'co2_t_anual': agent_co2_kg / 1000,
                'grid_import_kwh': agent_grid_kwh,
                'solar_generation_kwh': result.get('solar_generation_kwh', 'N/A'),
                'improvement_vs_con_solar_pct': co2_vs_con_solar,
                'improvement_vs_sin_solar_pct': co2_vs_sin_solar,
            })
        
        df = pd.DataFrame(rows)
        
        # Save if output file specified
        if output_file:
            df.to_csv(output_file, index=False)
            logger.info(f"[OK] Comparison report saved to {output_file}")
        
        return df

    def print_summary(self):
        """Print baseline summary to console."""
        baselines = self.compute_baselines()
        con_solar = baselines['con_solar']
        sin_solar = baselines['sin_solar']
        
        print("\n" + "="*80)
        print("CityLearn v2 Baseline Summary (OE2 v5.4)")
        print("="*80)
        
        print("\n[GRAPH] BASELINE 1: CON SOLAR (4,050 kWp)")
        print(f"   CO₂: {con_solar['co2_grid_kg']:,.0f} kg/ano ({con_solar['co2_t']:,.1f} t/ano)")
        print(f"   Grid import: {con_solar['grid_import_kwh']:,.0f} kWh/ano")
        print(f"   Solar generation: {con_solar['solar_generation_kwh']:,.0f} kWh/ano")
        
        print("\n[GRAPH] BASELINE 2: SIN SOLAR (0 kWp)")
        print(f"   CO₂: {sin_solar['co2_grid_kg']:,.0f} kg/ano ({sin_solar['co2_t']:,.1f} t/ano)")
        print(f"   Grid import: {sin_solar['grid_import_kwh']:,.0f} kWh/ano")
        
        print("\n🎯 SOLAR IMPACT")
        diff_kg = sin_solar['co2_grid_kg'] - con_solar['co2_grid_kg']
        diff_pct = diff_kg / sin_solar['co2_grid_kg'] * 100
        print(f"   CO₂ reduction: {diff_kg:,.0f} kg/ano ({diff_pct:.1f}%)")
        
        print("\n[TIP] RL AGENT TARGET")
        print(f"   Agents should beat CON_SOLAR ({con_solar['co2_t']:,.1f} t/ano)")
        print(f"   Maximum theoretical: Approach SIN_SOLAR ({sin_solar['co2_t']:,.1f} t/ano)")
        print(f"   Feasible range: {con_solar['co2_t']:,.1f} - {con_solar['co2_t']*0.7:,.1f} t/ano")
        print("="*80 + "\n")


def initialize_baselines_for_training() -> BaselineCityLearnIntegration:
    """Initialize baselines for agent training integration.
    
    Returns:
        BaselineCityLearnIntegration instance ready for use
    """
    logger.info("[CityLearn] Initializing baseline integration...")
    integration = BaselineCityLearnIntegration()
    
    # Compute and save baselines
    baselines = integration.compute_baselines()
    integration.save_baselines(baselines)
    
    # Print summary
    integration.print_summary()
    
    return integration


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )
    
    # Initialize and print summary
    integration = initialize_baselines_for_training()
