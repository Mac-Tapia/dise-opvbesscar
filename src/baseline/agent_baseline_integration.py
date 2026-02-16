"""Agent Baseline Integration Module.

Conecta entrenamientos de agentes RL (SAC, PPO, A2C) con baselines para:
1. Registrar metricas de baseline al iniciar entrenamiento
2. Comparar resultados de agentes contra baselines
3. Generar reportes de mejora

Uso en entrenamientos:
```python
from src.baseline.agent_baseline_integration import setup_agent_training_with_baselines

# Al iniciar entrenamiento
baseline_integration = setup_agent_training_with_baselines(
    agent_name='SAC',
    output_dir='outputs/agent_training/sac_v54'
)

# Despues del entrenamiento
baseline_integration.compare_and_report(
    agent_co2_kg=7500.0,
    agent_grid_kwh=3000000.0
)
```
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd
import numpy as np

from .citylearn_baseline_integration import BaselineCityLearnIntegration

logger = logging.getLogger(__name__)


class AgentBaselineIntegration:
    """Integra un agente RL con baselines para tracking y comparacion."""

    def __init__(
        self,
        agent_name: str,
        output_dir: str = 'outputs/agent_training',
        baseline_dir: str = 'outputs/baselines'
    ):
        """Initialize agent-baseline integration.
        
        Args:
            agent_name: Name of agent (e.g., 'SAC', 'PPO', 'A2C')
            output_dir: Directory for agent-specific outputs
            baseline_dir: Directory containing baseline results
        """
        self.agent_name = agent_name
        self.output_dir = Path(output_dir)
        self.baseline_dir = Path(baseline_dir)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.baseline_integration = BaselineCityLearnIntegration(str(self.baseline_dir))
        
        # Compute baselines if not already done
        if not (self.baseline_dir / 'baseline_con_solar.json').exists():
            logger.info(f"[{agent_name}] Computing baselines (first time)...")
            baselines = self.baseline_integration.compute_baselines()
            self.baseline_integration.save_baselines(baselines)
        
        # Load baseline results
        self._load_baselines()
        
        # Training log
        self.training_log = {
            'agent': agent_name,
            'timestamp': pd.Timestamp.now().isoformat(),
            'baseline_con_solar_co2_kg': self.con_solar_co2_kg,
            'baseline_sin_solar_co2_kg': self.sin_solar_co2_kg,
            'training_results': None,
        }
    
    def _load_baselines(self) -> None:
        """Load baseline results from disk."""
        con_solar_file = self.baseline_dir / 'baseline_con_solar.json'
        sin_solar_file = self.baseline_dir / 'baseline_sin_solar.json'
        
        with open(con_solar_file, 'r') as f:
            con_solar = json.load(f)
        with open(sin_solar_file, 'r') as f:
            sin_solar = json.load(f)
        
        self.con_solar_co2_kg = con_solar['co2_grid_kg']
        self.con_solar_grid_kwh = con_solar['grid_import_kwh']
        self.con_solar_co2_t = con_solar['co2_t']
        
        self.sin_solar_co2_kg = sin_solar['co2_grid_kg']
        self.sin_solar_grid_kwh = sin_solar['grid_import_kwh']
        self.sin_solar_co2_t = sin_solar['co2_t']
        
        logger.info(
            f"[{self.agent_name}] Baselines loaded:\n"
            f"  - CON_SOLAR: {self.con_solar_co2_t:,.1f} t CO₂/ano\n"
            f"  - SIN_SOLAR: {self.sin_solar_co2_t:,.1f} t CO₂/ano"
        )
    
    def log_training_config(self, config: Dict[str, Any]) -> None:
        """Log training configuration.
        
        Args:
            config: Training configuration dict
        """
        self.training_log['config'] = config
        logger.info(f"[{self.agent_name}] Training configuration logged")
    
    def register_training_results(
        self,
        co2_kg: float,
        grid_import_kwh: float,
        solar_generation_kwh: float = 0.0,
        additional_metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register final training results.
        
        Args:
            co2_kg: Total CO2 emissions (kg/year)
            grid_import_kwh: Total grid import (kWh/year)
            solar_generation_kwh: Total solar generation (kWh/year)
            additional_metrics: Any additional metrics to log
        """
        self.training_log['training_results'] = {
            'co2_kg_anual': co2_kg,
            'co2_t_anual': co2_kg / 1000,
            'grid_import_kwh': grid_import_kwh,
            'solar_generation_kwh': solar_generation_kwh,
            'timestamp': pd.Timestamp.now().isoformat(),
        }
        
        if additional_metrics:
            self.training_log['training_results'].update(additional_metrics)
        
        logger.info(
            f"[{self.agent_name}] Training results registered:\n"
            f"  - CO₂: {co2_kg/1000:,.1f} t/ano\n"
            f"  - Grid import: {grid_import_kwh:,.0f} kWh/ano"
        )
    
    def compare_and_report(self) -> Dict[str, float]:
        """Compare training results against baselines and generate report.
        
        Returns:
            Dict with comparison metrics
        """
        if self.training_log['training_results'] is None:
            raise ValueError(f"[{self.agent_name}] No training results registered yet")
        
        results = self.training_log['training_results']
        agent_co2_kg = results['co2_kg_anual']
        agent_grid_kwh = results['grid_import_kwh']
        
        # Calculate improvements
        co2_vs_con_solar = self.baseline_integration.compare_agent_vs_baseline(
            self.agent_name,
            agent_co2_kg,
            agent_grid_kwh,
            baseline='con_solar'
        )
        
        co2_vs_sin_solar = self.baseline_integration.compare_agent_vs_baseline(
            self.agent_name,
            agent_co2_kg,
            agent_grid_kwh,
            baseline='sin_solar'
        )
        
        # Create comparison report
        comparison = {
            'agent': self.agent_name,
            'co2_kg_anual': agent_co2_kg,
            'co2_t_anual': agent_co2_kg / 1000,
            **co2_vs_con_solar,
        }
        
        # Save to file
        report_file = self.output_dir / f'{self.agent_name.lower()}_vs_baseline.json'
        with open(report_file, 'w') as f:
            json.dump(comparison, f, indent=2)
        
        logger.info(f"[{self.agent_name}] Comparison report saved to {report_file}")
        
        # Print summary
        self._print_comparison_summary(comparison)
        
        return comparison
    
    def _print_comparison_summary(self, comparison: Dict[str, float]) -> None:
        """Print comparison summary to console.
        
        Args:
            comparison: Comparison dict from compare_and_report()
        """
        print(f"\n{'='*80}")
        print(f"AGENT BASELINE COMPARISON: {self.agent_name} (OE2 v5.4)")
        print(f"{'='*80}")
        
        print(f"\n[CHART] {self.agent_name} RESULTS")
        print(f"   CO₂ emissions: {comparison['co2_t_anual']:,.1f} t/ano")
        print(f"   Grid import: {comparison.get('grid_import_kwh', 'N/A'):,.0f} kWh/ano")
        
        print(f"\n[GRAPH] BASELINE 1: CON SOLAR (Reference)")
        print(f"   CO₂: {self.con_solar_co2_t:,.1f} t/ano")
        print(f"   Improvement: {comparison['co2_improvement_pct']:.1f}% CO₂ reduction")
        print(f"   Absolute reduction: {comparison['co2_reduction_t']:,.1f} t/ano")
        
        print(f"\n[GRAPH] BASELINE 2: SIN SOLAR (Worst case)")
        print(f"   CO₂: {self.sin_solar_co2_t:,.1f} t/ano")  
        gap_to_sin = self.sin_solar_co2_kg - comparison['co2_kg_anual']
        gap_pct = gap_to_sin / self.sin_solar_co2_kg * 100 if self.sin_solar_co2_kg > 0 else 0
        print(f"   Gap: {gap_pct:.1f}% improvement over baseline without solar")
        
        print(f"\n🎯 PERFORMANCE ASSESSMENT")
        if comparison['co2_improvement_pct'] > 0:
            print(f"   [OK] {self.agent_name} IMPROVED baseline by {comparison['co2_improvement_pct']:.1f}%")
        elif comparison['co2_improvement_pct'] == 0:
            print(f"   ⚖️  {self.agent_name} MATCHED baseline (no improvement)")
        else:
            print(f"   [!]  {self.agent_name} UNDERPERFORMED baseline")
        
        print(f"{'='*80}\n")
    
    def save_training_log(self) -> None:
        """Save complete training log to disk."""
        log_file = self.output_dir / f'{self.agent_name.lower()}_training_log.json'
        with open(log_file, 'w') as f:
            json.dump(self.training_log, f, indent=2)
        logger.info(f"[{self.agent_name}] Training log saved to {log_file}")


def setup_agent_training_with_baselines(
    agent_name: str,
    output_dir: str = 'outputs/agent_training',
    baseline_dir: str = 'outputs/baselines'
) -> AgentBaselineIntegration:
    """Setup agent training with baseline integration.
    
    Call at start of training to initialize baseline tracking.
    
    Args:
        agent_name: Name of agent (e.g., 'SAC', 'PPO', 'A2C')
        output_dir: Directory for agent outputs
        baseline_dir: Directory for baseline results
    
    Returns:
        AgentBaselineIntegration instance for use during training
    
    Example:
        >>> baseline_integration = setup_agent_training_with_baselines('SAC')
        >>> # ... train agent ...
        >>> baseline_integration.register_training_results(co2_kg=7500, grid_import_kwh=3e6)
        >>> baseline_integration.compare_and_report()
    """
    logger.info(f"[{agent_name}] Setting up baseline integration...")
    
    integration = AgentBaselineIntegration(
        agent_name=agent_name,
        output_dir=output_dir,
        baseline_dir=baseline_dir
    )
    
    logger.info(f"[{agent_name}] Baseline integration ready")
    return integration


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )
    
    # Example usage
    sac_integration = setup_agent_training_with_baselines('SAC')
    print("\nBaseline integration initialized. Ready for agent training.")
