"""
CityLearn v2 Integration - MIXTO Scenario (30% Diésel + 70% Gasolina)

Extiende CompleteDatasetBuilder para soportar múltiples escenarios de combustible.

Escenarios soportados:
- BASELINE: chargers_ev_ano_2024_v3.csv (original)
- ENHANCED: chargers_ev_ano_2024_v3_enhanced.csv (con CO2/socket y tiempo variable)
- MIXTO: chargers_ev_ano_2024_v3_citylearn_mixto.csv (30% diésel + 70% gasolina) ← ACTUAL
- DIESEL_100: chargers_ev_ano_2024_v3_diesel.csv (100% diésel)
- GASOLINA_100: chargers_ev_ano_2024_v3_gasolina.csv (100% gasolina)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, List, Any, Literal
import logging

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class CityLearnScenarioBuilder:
    """Extends CompleteDatasetBuilder with scenario support."""
    
    # Scenario definitions
    SCENARIOS = {
        'baseline': {
            'name': 'Original (no CO2 tracking)',
            'chargers_file': 'chargers_ev_ano_2024_v3.csv',
            'description': 'Original dataset without CO2 reduction tracking',
        },
        'enhanced': {
            'name': 'Enhanced (per-socket CO2 + variable time)',
            'chargers_file': 'chargers_ev_ano_2024_v3_enhanced.csv',
            'description': 'Enhanced with socket-level CO2 and time de carga variable',
        },
        'mixto': {
            'name': 'MIXTO (30% Diésel + 70% Gasolina)',
            'chargers_file': 'chargers_ev_ano_2024_v3_citylearn_mixto.csv',
            'description': 'Mixed scenario with realistic combustible distribution',
            'co2_factors': {
                'motos': 0.10,  # kg CO2 per charge
                'taxis': 0.34,  # kg CO2 per charge
            }
        },
        'diesel_100': {
            'name': 'Diesel 100%',
            'chargers_file': 'chargers_ev_ano_2024_v3_diesel.csv',
            'description': '100% diésel scenario (worst case)',
        },
        'gasolina_100': {
            'name': 'Gasolina 100%',
            'chargers_file': 'chargers_ev_ano_2024_v3_gasolina.csv',
            'description': '100% gasolina scenario (baseline)',
        }
    }
    
    # Base paths
    SOLAR_PATH = Path("data/oe2/Generacionsolar/pv_generation_citylearn2024.csv")
    BESS_PATH = Path("data/oe2/bess/bess_ano_2024.csv")
    CHARGERS_DIR = Path("data/oe2/chargers")
    DEMAND_PATH = Path("data/oe2/demandamallkwh/demandamallhorakwh.csv")
    
    # OE2 Constants
    BESS_CAPACITY_KWH = 1700.0
    BESS_MAX_POWER_KW = 400.0
    N_CHARGERS = 19
    TOTAL_SOCKETS = 38
    SOLAR_PV_KWP = 4050.0
    MALL_DEMAND_KW = 100.0
    
    def __init__(
        self,
        scenario: Literal['baseline', 'enhanced', 'mixto', 'diesel_100', 'gasolina_100'] = 'mixto',
        cwd: Optional[Path] = None
    ):
        """Initialize with scenario selection.
        
        Args:
            scenario: Scenario name (default: 'mixto' = 30% diésel + 70% gasolina)
            cwd: Working directory
        """
        self.scenario = scenario
        self.cwd = cwd or Path.cwd()
        
        if scenario not in self.SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario}. Available: {list(self.SCENARIOS.keys())}")
        
        self.scenario_config = self.SCENARIOS[scenario]
        
        # Loaded data
        self._solar_df: Optional[pd.DataFrame] = None
        self._bess_df: Optional[pd.DataFrame] = None
        self._chargers_df: Optional[pd.DataFrame] = None
        self._demand_df: Optional[pd.DataFrame] = None
        
        # Column metadata
        self.solar_columns: List[str] = []
        self.bess_columns: List[str] = []
        self.chargers_columns: List[str] = []
        self.demand_columns: List[str] = []
    
    def load_all(self) -> Dict[str, Any]:
        """Load all datasets with scenario-specific chargers.
        
        Returns:
            Dict with: solar, bess, chargers, demand, metadata, scenario
        """
        results = {}
        
        print("[CityLearn v2] SCENARIO-BASED DATASET BUILDER")
        print("=" * 100)
        print(f"\n🎯 SCENARIO: {self.scenario.upper()}")
        print(f"   {self.scenario_config['name']}")
        print(f"   {self.scenario_config['description']}")
        print()
        
        # 1. Load Solar
        print("1️⃣  Loading SOLAR data...")
        self._load_solar()
        results['solar'] = self._solar_df
        print(f"   ✓ {len(self._solar_df)} rows × {len(self.solar_columns)} columns")
        print()
        
        # 2. Load BESS
        print("2️⃣  Loading BESS data...")
        self._load_bess()
        results['bess'] = self._bess_df
        print(f"   ✓ {len(self._bess_df)} rows × {len(self.bess_columns)} columns")
        print()
        
        # 3. Load Chargers (scenario-specific)
        print("3️⃣  Loading CHARGERS data (scenario-specific)...")
        self._load_chargers()
        results['chargers'] = self._chargers_df
        print(f"   ✓ {len(self._chargers_df)} rows × {len(self.chargers_columns)} columns")
        print(f"   📍 File: {self.scenario_config['chargers_file']}")
        
        # Mostrar factores CO2 si están disponibles
        if 'co2_factors' in self.scenario_config:
            factors = self.scenario_config['co2_factors']
            print(f"   💨 CO2 Factors: Motos {factors['motos']:.2f} kg, Taxis {factors['taxis']:.2f} kg")
        print()
        
        # 4. Load Demand
        print("4️⃣  Loading DEMAND data...")
        self._load_demand()
        results['demand'] = self._demand_df
        print(f"   ✓ {len(self._demand_df)} rows × {len(self.demand_columns)} columns")
        print()
        
        # 5. Generate metadata
        results['metadata'] = self._generate_metadata()
        results['scenario'] = {
            'name': self.scenario,
            'config': self.scenario_config
        }
        
        print("=" * 100)
        print("[✓ OK] ALL DATASETS LOADED SUCCESSFULLY")
        print(f"      Total observations: {len(self._solar_df):,} timesteps")
        print(f"      Sockets: {self.TOTAL_SOCKETS}")
        print(f"      Scenario: {self.scenario.upper()}")
        print()
        
        return results
    
    def _load_solar(self):
        """Load solar dataset."""
        path = self.cwd / self.SOLAR_PATH if not self.SOLAR_PATH.is_absolute() else self.SOLAR_PATH
        
        if not path.exists():
            raise FileNotFoundError(f"Solar file not found: {path}")
        
        self._solar_df = pd.read_csv(path)
        self.solar_columns = list(self._solar_df.columns)
        
        if len(self._solar_df) != 8760:
            raise ValueError(f"Solar must have 8,760 hourly rows, got {len(self._solar_df)}")
    
    def _load_bess(self):
        """Load BESS dataset."""
        path = self.cwd / self.BESS_PATH if not self.BESS_PATH.is_absolute() else self.BESS_PATH
        
        if not path.exists():
            raise FileNotFoundError(f"BESS file not found: {path}")
        
        self._bess_df = pd.read_csv(path)
        self.bess_columns = list(self._bess_df.columns)
        
        if len(self._bess_df) != 8760:
            raise ValueError(f"BESS must have 8,760 hourly rows, got {len(self._bess_df)}")
    
    def _load_chargers(self):
        """Load chargers dataset (scenario-specific)."""
        chargers_file = self.scenario_config['chargers_file']
        path = (self.cwd / self.CHARGERS_DIR / chargers_file 
                if not (self.CHARGERS_DIR / chargers_file).is_absolute() 
                else self.CHARGERS_DIR / chargers_file)
        
        if not path.exists():
            # Try alternative location
            alt_path = Path(chargers_file)
            if not alt_path.exists():
                raise FileNotFoundError(
                    f"Chargers file not found for scenario '{self.scenario}':\n"
                    f"  Expected: {path}\n"
                    f"  Alternative: {alt_path}\n"
                    f"  Please run: python scripts/integrate_citylearn_mixto.py"
                )
            path = alt_path
        
        self._chargers_df = pd.read_csv(path)
        self.chargers_columns = list(self._chargers_df.columns)
        
        if len(self._chargers_df) != 8760:
            raise ValueError(f"Chargers must have 8,760 hourly rows, got {len(self._chargers_df)}")
        
        # Verify 38 sockets
        socket_cols = [c for c in self.chargers_columns if 'socket_' in c.lower()]
        socket_ids = set()
        for col in socket_cols:
            parts = col.split('_')
            if len(parts) >= 2:
                try:
                    socket_ids.add(int(parts[1]))
                except ValueError:
                    pass
        
        if len(socket_ids) != self.TOTAL_SOCKETS:
            logger.warning(f"Expected {self.TOTAL_SOCKETS} sockets, found {len(socket_ids)}")
    
    def _load_demand(self):
        """Load demand dataset."""
        path = self.cwd / self.DEMAND_PATH if not self.DEMAND_PATH.is_absolute() else self.DEMAND_PATH
        
        if not path.exists():
            raise FileNotFoundError(f"Demand file not found: {path}")
        
        self._demand_df = pd.read_csv(path)
        self.demand_columns = list(self._demand_df.columns)
        
        if len(self._demand_df) != 8760:
            raise ValueError(f"Demand must have 8,760 hourly rows, got {len(self._demand_df)}")
    
    def _generate_metadata(self) -> Dict[str, Any]:
        """Generate metadata about loaded datasets."""
        return {
            'n_rows': len(self._solar_df),
            'n_sockets': self.TOTAL_SOCKETS,
            'n_chargers': self.N_CHARGERS,
            'scenario': self.scenario,
            'scenario_config': self.scenario_config,
            'solar_columns': self.solar_columns,
            'bess_columns': self.bess_columns,
            'chargers_columns': self.chargers_columns,
            'demand_columns': self.demand_columns,
            'columns_summary': {
                'solar': len(self.solar_columns),
                'bess': len(self.bess_columns),
                'chargers': len(self.chargers_columns),
                'demand': len(self.demand_columns),
                'total': (len(self.solar_columns) + len(self.bess_columns) + 
                         len(self.chargers_columns) + len(self.demand_columns))
            },
            'constants': {
                'bess_capacity_kwh': self.BESS_CAPACITY_KWH,
                'bess_max_power_kw': self.BESS_MAX_POWER_KW,
                'solar_pv_kwp': self.SOLAR_PV_KWP,
                'mall_demand_kw': self.MALL_DEMAND_KW,
            }
        }
    
    def get_observation_dimensions(self) -> Dict[str, int]:
        """Get observation space dimensions for the scenario."""
        return {
            'solar': len(self.solar_columns),
            'bess': len(self.bess_columns),
            'chargers': len(self.chargers_columns),
            'demand': len(self.demand_columns),
            'total': (len(self.solar_columns) + len(self.bess_columns) + 
                     len(self.chargers_columns) + len(self.demand_columns))
        }
    
    @staticmethod
    def list_available_scenarios():
        """Print available scenarios."""
        print("\n" + "=" * 100)
        print("AVAILABLE CITYLEARN SCENARIOS")
        print("=" * 100 + "\n")
        
        for key, config in CityLearnScenarioBuilder.SCENARIOS.items():
            print(f"🎯 {key.upper()}")
            print(f"   Name: {config['name']}")
            print(f"   File: {config['chargers_file']}")
            print(f"   Desc: {config['description']}")
            if 'co2_factors' in config:
                factors = config['co2_factors']
                print(f"   CO2:  Motos {factors['motos']:.2f} kg, Taxis {factors['taxis']:.2f} kg")
            print()


# ============================================================================
# USAGE EXAMPLES & ENTRY POINTS
# ============================================================================

def load_citylearn_mixto():
    """Load CityLearn datasets with MIXTO scenario.
    
    This is the RECOMMENDED approach for RL agent training:
    - 30% diésel + 70% gasolina (realistic for Iquitos)
    - Per-socket CO2 tracking
    - Variable charging time based on SOC state
    - All 423 columns available
    
    Usage:
        datasets = load_citylearn_mixto()
        chargers_df = datasets['chargers']
        metadata = datasets['metadata']
        
        # Train agent with MIXTO scenario
        agent.learn(...)
    
    CO2 Reduction:
        ~28,234 ton CO2/año (MIXTO scenario)
    """
    builder = CityLearnScenarioBuilder(scenario='mixto')
    return builder.load_all()


def load_citylearn_scenario(scenario: str):
    """Load CityLearn with any available scenario.
    
    Args:
        scenario: One of 'baseline', 'enhanced', 'mixto', 'diesel_100', 'gasolina_100'
    
    Returns:
        Dict with all datasets loaded for the scenario
    """
    builder = CityLearnScenarioBuilder(scenario=scenario)
    return builder.load_all()


if __name__ == '__main__':
    # Show available scenarios
    CityLearnScenarioBuilder.list_available_scenarios()
    
    # Load MIXTO (default)
    print("\n🔄 Loading MIXTO scenario (default)...\n")
    try:
        datasets = load_citylearn_mixto()
        print("\n✓ SUCCESS: MIXTO scenario loaded and ready for training")
        print(f"  CO2 Total: {datasets['chargers']['total_co2_reducido_kg'].sum():,.1f} kg/año")
    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTo create MIXTO dataset, run:")
        print("  python scripts/integrate_citylearn_mixto.py")
