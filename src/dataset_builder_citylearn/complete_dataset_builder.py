"""
Complete Dataset Builder v7.0 - Loads ALL columns from each dataset.

Purpose:
- Ensure ALL columns are loaded from every dataset before agent training
- Dynamically discover and use all available columns
- Consistent across all agents (SAC, PPO, A2C)
- Single source of truth for dataset construction

Key Features:
- Complete column loading from OE2 datasets
- Dynamic configuration based on actual columns
- Validation and consistency checks
- Observation builder with ALL available features
- Reusable across all training scripts
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, List, Any
import logging

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# COMPLETE DATASET LOADER (Load ALL columns)
# ============================================================================

class CompleteDatasetBuilder:
    """Builds complete datasets with ALL columns loaded and validated."""
    
    # Canonical paths (OE2 primary sources)
    SOLAR_PATH = Path("data/oe2/Generacionsolar/pv_generation_citylearn2024.csv")
    BESS_PATH = Path("data/oe2/bess/bess_ano_2024.csv")
    CHARGERS_PATH = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
    DEMAND_PATH = Path("data/oe2/demandamallkwh/demandamallhorakwh.csv")
    
    # OE2 v5.3 Constants (verified)
    BESS_CAPACITY_KWH = 1700.0
    BESS_MAX_POWER_KW = 400.0
    N_CHARGERS = 19
    TOTAL_SOCKETS = 38
    SOLAR_PV_KWP = 4050.0
    MALL_DEMAND_KW = 100.0
    
    def __init__(self, cwd: Optional[Path] = None):
        """Initialize builder."""
        self.cwd = cwd or Path.cwd()
        
        # Loaded data (will contain ALL columns)
        self._solar_df: Optional[pd.DataFrame] = None
        self._bess_df: Optional[pd.DataFrame] = None
        self._chargers_df: Optional[pd.DataFrame] = None
        self._demand_df: Optional[pd.DataFrame] = None
        
        # Column metadata (discovered at load time)
        self.solar_columns: List[str] = []
        self.bess_columns: List[str] = []
        self.chargers_columns: List[str] = []
        self.demand_columns: List[str] = []
    
    def load_all(self) -> Dict[str, Any]:
        """Load ALL datasets with ALL columns.
        
        Returns:
            Dict with keys: solar, bess, chargers, demand, metadata
        """
        results = {}
        
        print("[GRAPH] COMPLETE DATASET BUILDER v7.0")
        print("=" * 90)
        print()
        
        # 1. Load Solar (ALL columns)
        print("1️⃣  Loading SOLAR data...")
        self._load_solar_complete()
        results['solar'] = self._solar_df
        print(f"   [OK] Loaded {len(self._solar_df)} rows × {len(self.solar_columns)} columns")
        print(f"   +- Columns: {', '.join(self.solar_columns[:5])}{'...' if len(self.solar_columns) > 5 else ''}")
        print()
        
        # 2. Load BESS (ALL columns)
        print("2️⃣  Loading BESS data...")
        self._load_bess_complete()
        results['bess'] = self._bess_df
        print(f"   [OK] Loaded {len(self._bess_df)} rows × {len(self.bess_columns)} columns")
        print(f"   +- Columns: {', '.join(self.bess_columns[:5])}{'...' if len(self.bess_columns) > 5 else ''}")
        print()
        
        # 3. Load Chargers (ALL columns)
        print("3️⃣  Loading CHARGERS data (38 sockets)...")
        self._load_chargers_complete()
        results['chargers'] = self._chargers_df
        print(f"   [OK] Loaded {len(self._chargers_df)} rows × {len(self.chargers_columns)} columns")
        print(f"   +- Columns: {len(self.chargers_columns)} total columns (socket-based)")
        print()
        
        # 4. Load Demand (ALL columns)
        print("4️⃣  Loading DEMAND data...")
        self._load_demand_complete()
        results['demand'] = self._demand_df
        print(f"   [OK] Loaded {len(self._demand_df)} rows × {len(self.demand_columns)} columns")
        print(f"   +- Columns: {', '.join(self.demand_columns)}")
        print()
        
        # 5. Generate metadata
        results['metadata'] = self._generate_metadata()
        
        print("=" * 90)
        print("[OK] ALL DATASETS LOADED SUCCESSFULLY")
        print(f"   Total rows: {len(self._solar_df):,}")
        print(f"   Total columns: {len(self.solar_columns) + len(self.bess_columns) + len(self.chargers_columns) + len(self.demand_columns)}")
        print()
        
        return results
    
    def _load_solar_complete(self):
        """Load SOLAR with ALL columns."""
        path = self.cwd / self.SOLAR_PATH if not self.SOLAR_PATH.is_absolute() else self.SOLAR_PATH
        
        if not path.exists():
            raise FileNotFoundError(f"Solar file not found: {path}")
        
        self._solar_df = pd.read_csv(path)
        self.solar_columns = list(self._solar_df.columns)
        
        # Validation
        if len(self._solar_df) != 8760:
            raise ValueError(f"Solar must have 8,760 rows (hourly), got {len(self._solar_df)}")
    
    def _load_bess_complete(self):
        """Load BESS with ALL columns."""
        path = self.cwd / self.BESS_PATH if not self.BESS_PATH.is_absolute() else self.BESS_PATH
        
        if not path.exists():
            raise FileNotFoundError(f"BESS file not found: {path}")
        
        self._bess_df = pd.read_csv(path)
        self.bess_columns = list(self._bess_df.columns)
        
        # Validation
        if len(self._bess_df) != 8760:
            raise ValueError(f"BESS must have 8,760 rows, got {len(self._bess_df)}")
    
    def _load_chargers_complete(self):
        """Load CHARGERS with ALL columns (38 sockets)."""
        path = self.cwd / self.CHARGERS_PATH if not self.CHARGERS_PATH.is_absolute() else self.CHARGERS_PATH
        
        if not path.exists():
            raise FileNotFoundError(f"Chargers file not found: {path}")
        
        self._chargers_df = pd.read_csv(path)
        self.chargers_columns = list(self._chargers_df.columns)
        
        # Validation
        if len(self._chargers_df) != 8760:
            raise ValueError(f"Chargers must have 8,760 rows, got {len(self._chargers_df)}")
        
        # Count socket columns to verify 38 sockets
        socket_cols = [c for c in self.chargers_columns if 'socket_' in c.lower()]
        socket_ids = set()
        for col in socket_cols:
            # Extract socket ID from column name (e.g., socket_000_* -> 000)
            parts = col.split('_')
            if len(parts) >= 2:
                socket_ids.add(parts[1])
        
        if len(socket_ids) != self.TOTAL_SOCKETS:
            logger.warning(f"Expected {self.TOTAL_SOCKETS} sockets, found {len(socket_ids)}")
    
    def _load_demand_complete(self):
        """Load DEMAND with ALL columns."""
        path = self.cwd / self.DEMAND_PATH if not self.DEMAND_PATH.is_absolute() else self.DEMAND_PATH
        
        if not path.exists():
            raise FileNotFoundError(f"Demand file not found: {path}")
        
        self._demand_df = pd.read_csv(path)
        self.demand_columns = list(self._demand_df.columns)
        
        # Validation
        if len(self._demand_df) != 8760:
            raise ValueError(f"Demand must have 8,760 rows, got {len(self._demand_df)}")
    
    def _generate_metadata(self) -> Dict[str, Any]:
        """Generate metadata about loaded datasets."""
        return {
            'n_rows': len(self._solar_df),
            'n_sockets': self.TOTAL_SOCKETS,
            'n_chargers': self.N_CHARGERS,
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
        """Get dimensions for observation space based on loaded columns.
        
        Returns:
            Dict with observation dimensions for each data source
        """
        return {
            'solar': len(self.solar_columns),
            'bess': len(self.bess_columns),
            'chargers': len(self.chargers_columns),
            'demand': len(self.demand_columns),
            'total': (len(self.solar_columns) + len(self.bess_columns) + 
                     len(self.chargers_columns) + len(self.demand_columns))
        }


# ============================================================================
# USAGE PATTERN (For all training scripts)
# ============================================================================

def build_complete_datasets_for_training() -> Dict[str, Any]:
    """Main entry point for dataset construction before agent training.
    
    Usage:
        # At the START of any training script:
        datasets = build_complete_datasets_for_training()
        
        solar_df = datasets['solar']
        bess_df = datasets['bess']
        chargers_df = datasets['chargers']
        demand_df = datasets['demand']
        metadata = datasets['metadata']
        
        # Now use ALL columns available in each dataset
        for col in metadata['solar_columns']:
            # Process column
            pass
    
    Returns:
        Dict with:
        - 'solar': DataFrame with ALL columns
        - 'bess': DataFrame with ALL columns
        - 'chargers': DataFrame with ALL columns
        - 'demand': DataFrame with ALL columns
        - 'metadata': Dictionary with column info and constants
    """
    builder = CompleteDatasetBuilder()
    return builder.load_all()


if __name__ == '__main__':
    # Test
    datasets = build_complete_datasets_for_training()
    print("\n[OK] Test successful - all datasets loaded with all columns")
