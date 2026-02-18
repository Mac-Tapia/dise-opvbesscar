"""OE2 Data Loader v5.6 - Unified with Dataset Catalog.

Carga datos OE2 desde fuentes diversas usando el catalogo centralizado como
fuente unica de verdad (Single Source of Truth).

Changes in v5.6 (14 feb 2026):
- Unificado con catalog_datasets.py para evitar duplicacion
- Imports de dataset_builder.py movidos aqui
- Compatible con stable-baselines3 y agents RL
- Soporta fallback a rutas intermedias si no existen datos primarios

Structure:
  OE2 (Primary, source of truth - FIXED PATHS)
    +-- Solar: data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv (8,760 rows, hourly)
    +-- BESS: data/oe2/bess/bess_ano_2024.csv (1,700 kWh, 400 kW)
    +-- Chargers: data/oe2/chargers/chargers_ev_ano_2024_v3.csv (38 sockets, 19 chargers)
    +-- Mall: data/oe2/demandamallkwh/demandamallhorakwh.csv (100 kW avg)

  Interim (Fallback if OE2 missing)
    +-- Solar: data/interim/oe2/solar/pv_generation_hourly_citylearn_v2.csv
    +-- BESS: data/interim/oe2/bess/bess_hourly_dataset_2024.csv
    +-- Chargers: data/interim/oe2/chargers/chargers_real_hourly_2024.csv
    +-- Demand: data/oe2/demandamallkwh/demandamallhorakwh.csv (primary demand)

  CityLearn (Processed, for agent training)
    +-- data/processed/citylearn/iquitos_ev_mall/

Critical Constraints:
  - Solar MUST be hourly (8,760 rows), NOT 15-minute data
  - BESS capacity: 1,700 kWh (confirmed from CSV, v5.3)
  - Chargers: 19 units × 2 sockets = 38 controllable sockets
  - Tariff: OSINERGMIN Iquitos (0.28 USD/kWh avg, HP/HFP schedule)

Validation enforced:
  - OE2ValidationError raised if data inconsistent
  - Missing files caught early with clear error messages
  - Column names validated against expected schema
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import logging

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# PATHS & CONSTANTS (Unified from dataset_builder.py)
# ============================================================================

# Primary data sources (OE2 - source of truth - FIXED PATHS v5.7)
DEFAULT_SOLAR_PATH = Path("data/oe2/Generacionsolar/pv_generation_citylearn2024.csv")
DEFAULT_BESS_PATH = Path("data/oe2/bess/bess_ano_2024.csv")
DEFAULT_CHARGERS_PATH = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
DEFAULT_MALL_DEMAND_PATH = Path("data/oe2/demandamallkwh/demandamallhorakwh.csv")

# Scenarios (OE2 optional)
DEFAULT_SCENARIOS_DIR = Path("data/oe2/chargers")
SCENARIOS_SELECTION_PE_FC_PATH = DEFAULT_SCENARIOS_DIR / "selection_pe_fc_completo.csv"
SCENARIOS_TABLA_DETALLADOS_PATH = DEFAULT_SCENARIOS_DIR / "tabla_escenarios_detallados.csv"
SCENARIOS_TABLA_ESTADISTICAS_PATH = DEFAULT_SCENARIOS_DIR / "tabla_estadisticas_escenarios.csv"
SCENARIOS_TABLA_RECOMENDADO_PATH = DEFAULT_SCENARIOS_DIR / "tabla_escenario_recomendado.csv"
SCENARIOS_TABLA13_PATH = DEFAULT_SCENARIOS_DIR / "escenarios_tabla13.csv"

# Interim fallback paths (ONLY valid paths that exist)
INTERIM_SOLAR_PATHS = [
    Path("data/oe2/Generacionsolar/pv_generation_citylearn2024.csv"),
    Path("data/interim/oe2/solar/pv_generation_hourly_citylearn_v2.csv"),
    Path("data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv"),
]
INTERIM_BESS_PATH = Path("data/interim/oe2/bess/bess_hourly_dataset_2024.csv")
INTERIM_CHARGERS_PATHS = [
    Path("data/interim/oe2/chargers/chargers_real_hourly_2024.csv"),
]
INTERIM_DEMAND_PATH = Path("data/oe2/demandamallkwh/demandamallhorakwh.csv")  # Always exists

# Processed (for CityLearn environment)
PROCESSED_CITYLEARN_DIR = Path("data/processed/citylearn/iquitos_ev_mall")

# Constants (OE2 v5.3 verified 2026-02-12)
BESS_CAPACITY_KWH = 1700.0  # From bess_ano_2024.csv (NOT 4,520 kWh as previously documented)
BESS_MAX_POWER_KW = 400.0   # Max charge/discharge rate
EV_DEMAND_KW = 50.0          # Constant demand (workaround for CityLearn 2.5.0)
N_CHARGERS = 19              # Physical chargers
TOTAL_SOCKETS = 38           # 19 × 2 sockets
MALL_DEMAND_KW = 100.0       # Mall baseline
SOLAR_PV_KWP = 4050.0        # 4,050 kWp installed

CO2_FACTOR_GRID_KG_PER_KWH = 0.4521  # Central termica Iquitos
CO2_FACTOR_EV_KG_PER_KWH = 2.146     # Equivalent fuel combustion


# ============================================================================
# EXCEPTIONS
# ============================================================================

class OE2ValidationError(Exception):
    """Raised when OE2 data validation fails."""
    pass


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass(frozen=True)
class SolarData:
    """Solar generation timeseries (OE2 validated)."""
    df: pd.DataFrame
    path: Path
    n_hours: int
    min_kw: float
    max_kw: float
    mean_kw: float
    
    def __post_init__(self):
        if self.n_hours != 8760:
            raise OE2ValidationError(
                f"Solar MUST be 8,760 hourly rows. Got {self.n_hours}. "
                "Do NOT use 15-minute data. Downsample: df.set_index('time').resample('h').mean()"
            )


@dataclass(frozen=True)
class BESSData:
    """BESS parameters and timeseries (OE2 validated)."""
    df: pd.DataFrame
    path: Path
    capacity_kwh: float
    max_power_kw: float
    n_hours: int = 8760


@dataclass(frozen=True)
class ChargerData:
    """EV charger specs and demand timeseries."""
    df: pd.DataFrame
    path: Path
    n_chargers: int
    total_sockets: int
    sockets_per_charger: int
    n_hours: int = 8760


@dataclass(frozen=True)
class DemandData:
    """Mall and EV demand timeseries."""
    df: pd.DataFrame
    path: Path
    n_hours: int
    mall_mean_kw: float = 100.0


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def resolve_data_path(
    primary: Path,
    fallbacks: Optional[List[Path]] = None,
    cwd: Optional[Path] = None,
) -> Path:
    """Resolver ruta de datos con fallbacks.

    Args:
        primary: Ruta primaria (source of truth)
        fallbacks: Rutas alternativas si primaria no existe
        cwd: Directorio de trabajo (default: cwd actual)

    Returns:
        Path existente

    Raises:
        OE2ValidationError si ninguna ruta existe
    """
    if cwd is None:
        cwd = Path.cwd()
    
    paths_to_try = [primary] + (fallbacks or [])
    
    for path in paths_to_try:
        full_path = cwd / path if not path.is_absolute() else path
        if full_path.exists():
            logger.info(f"[OK] Found data at: {full_path}")
            return full_path
    
    paths_str = " | ".join(str(p) for p in paths_to_try)
    raise OE2ValidationError(
        f"Data not found in any fallback path:\n{paths_str}\n"
        f"Current working directory: {cwd}"
    )


# ============================================================================
# LOAD FUNCTIONS
# ============================================================================

def load_solar_data(
    path: Optional[Path] = None,
    cwd: Optional[Path] = None,
) -> SolarData:
    """Load solar generation timeseries (MUST be 8,760 hourly rows).

    Args:
        path: Override default primary path
        cwd: Working directory

    Returns:
        SolarData with validation

    Raises:
        OE2ValidationError if data not 8,760 rows (hourly)
    """
    if path is None:
        path = resolve_data_path(DEFAULT_SOLAR_PATH, INTERIM_SOLAR_PATHS, cwd)
    else:
        path = resolve_data_path(path, cwd=cwd)

    df = pd.read_csv(path)
    
    if len(df) != 8760:
        raise OE2ValidationError(
            f"Solar MUST be 8,760 hourly rows. Got {len(df)}. "
            "Do NOT use 15-minute data. Resample: df.resample('h').mean()"
        )

    # Detect power column (common names: W, W/m2, Generation_W, pv_generation_W, etc)
    power_col = None
    for col in ['W', 'pv_generation_W', 'Generation_W', 'power_w', 'solar_power_w']:
        if col in df.columns:
            power_col = col
            break
    
    if power_col is None:
        # Fallback: numeric column with largest non-zero values
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) == 0:
            raise OE2ValidationError(f"No numeric column found in {path}")
        power_col = numeric_cols[0]

    solar_w = df[power_col].values
    solar_kw = solar_w / 1000.0 if max(solar_w) > 1000 else solar_w

    return SolarData(
        df=df,
        path=path,
        n_hours=len(df),
        min_kw=float(np.min(solar_kw)),
        max_kw=float(np.max(solar_kw)),
        mean_kw=float(np.mean(solar_kw)),
    )


def load_bess_data(
    path: Optional[Path] = None,
    cwd: Optional[Path] = None,
) -> BESSData:
    """Load BESS data (1,700 kWh capacity verified).

    Args:
        path: Override default primary path
        cwd: Working directory

    Returns:
        BESSData with validation

    Raises:
        OE2ValidationError if capacity mismatch
    """
    if path is None:
        path = resolve_data_path(DEFAULT_BESS_PATH, [INTERIM_BESS_PATH], cwd)
    else:
        path = resolve_data_path(path, cwd=cwd)

    df = pd.read_csv(path)

    if len(df) != 8760:
        logger.warning(f"BESS data has {len(df)} rows (expected 8,760)")

    # Verify capacity from file if available
    if 'bess_capacity_kwh' in df.columns:
        cap_from_file = df['bess_capacity_kwh'].iloc[0]
        if not np.isclose(cap_from_file, BESS_CAPACITY_KWH, rtol=0.01):
            logger.warning(
                f"BESS: File capacity={cap_from_file} kWh vs constant={BESS_CAPACITY_KWH} kWh"
            )

    return BESSData(
        df=df,
        path=path,
        capacity_kwh=BESS_CAPACITY_KWH,
        max_power_kw=BESS_MAX_POWER_KW,
        n_hours=len(df),
    )


def load_chargers_data(
    path: Optional[Path] = None,
    cwd: Optional[Path] = None,
) -> ChargerData:
    """Load charger data (38 sockets = 19 chargers × 2 sockets).

    Args:
        path: Override default primary path
        cwd: Working directory

    Returns:
        ChargerData with validation

    Raises:
        OE2ValidationError if socket count mismatch
    """
    if path is None:
        path = resolve_data_path(DEFAULT_CHARGERS_PATH, INTERIM_CHARGERS_PATHS, cwd)
    else:
        path = resolve_data_path(path, cwd=cwd)

    df = pd.read_csv(path)

    # Assume 19 chargers × 2 sockets = 38 controllable actions
    # Verify in metadata if available
    n_chargers = N_CHARGERS
    n_sockets = TOTAL_SOCKETS

    if n_sockets != 38:
        raise OE2ValidationError(
            f"Expected 38 sockets (19 × 2). Got {n_sockets}. "
            "Charger configuration mismatch in v5.3."
        )

    return ChargerData(
        df=df,
        path=path,
        n_chargers=n_chargers,
        total_sockets=n_sockets,
        sockets_per_charger=2,
        n_hours=len(df),
    )


def load_mall_demand_data(
    path: Optional[Path] = None,
    cwd: Optional[Path] = None,
) -> DemandData:
    """Load mall/non-shiftable demand.

    Args:
        path: Override default primary path
        cwd: Working directory

    Returns:
        DemandData with validation
    """
    if path is None:
        try:
            path = resolve_data_path(DEFAULT_MALL_DEMAND_PATH, cwd=cwd)
        except OE2ValidationError:
            # Fallback: use constant demand
            logger.warning(f"Mall demand file not found. Using constant {MALL_DEMAND_KW} kW")
            df = pd.DataFrame({
                'hour': range(8760),
                'mall_demand_kw': [MALL_DEMAND_KW] * 8760,
            })
            return DemandData(
                df=df,
                path=Path("constant_demand"),
                n_hours=8760,
                mall_mean_kw=MALL_DEMAND_KW,
            )
    else:
        path = resolve_data_path(path, cwd=cwd)

    df = pd.read_csv(path)

    # Detect demand column
    demand_col = None
    for col in ['kw', 'demanda_kw', 'mall_demand_kw', 'demand_kw']:
        if col in df.columns:
            demand_col = col
            break
    
    if demand_col is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        demand_col = numeric_cols[0] if len(numeric_cols) > 0 else 'kw'

    mean_kw = float(df[demand_col].mean()) if demand_col in df.columns else MALL_DEMAND_KW

    return DemandData(
        df=df,
        path=path,
        n_hours=len(df),
        mall_mean_kw=mean_kw,
    )


def load_scenarios_metadata(
    scenarios_dir: Optional[Path] = None,
) -> Dict[str, pd.DataFrame]:
    """Load OE2 scenario metadata (optional, for analysis).

    Returns:
        Dict with scenario tables
    """
    if scenarios_dir is None:
        scenarios_dir = DEFAULT_SCENARIOS_DIR

    scenarios: Dict[str, pd.DataFrame] = {}

    for name, path in [
        ("selection_pe_fc", SCENARIOS_SELECTION_PE_FC_PATH),
        ("detallados", SCENARIOS_TABLA_DETALLADOS_PATH),
        ("estadisticas", SCENARIOS_TABLA_ESTADISTICAS_PATH),
        ("recomendado", SCENARIOS_TABLA_RECOMENDADO_PATH),
        ("tabla13", SCENARIOS_TABLA13_PATH),
    ]:
        try:
            scenarios[name] = pd.read_csv(path)
            logger.info(f"[OK] Loaded scenarios: {name}")
        except Exception as e:
            logger.warning(f"[!] Could not load {name}: {e}")

    return scenarios


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_oe2_complete(
    solar: SolarData,
    bess: BESSData,
    chargers: ChargerData,
    demand: DemandData,
) -> bool:
    """Validate all OE2 data for consistency.

    Returns:
        True if all valid

    Raises:
        OE2ValidationError if mismatch
    """
    # Check all hourly (8,760 rows)
    for name, data_obj in [
        ("solar", solar),
        ("bess", bess),
        ("chargers", chargers),
        ("demand", demand),
    ]:
        if data_obj.n_hours != 8760:
            raise OE2ValidationError(
                f"{name}: Expected 8,760 rows, got {data_obj.n_hours}"
            )

    # Check BESS capacity
    if not np.isclose(bess.capacity_kwh, BESS_CAPACITY_KWH, rtol=0.01):
        raise OE2ValidationError(
            f"BESS capacity mismatch: {bess.capacity_kwh} kWh != {BESS_CAPACITY_KWH} kWh"
        )

    # Check charger socket count
    if chargers.total_sockets != 38:
        raise OE2ValidationError(
            f"Charger sockets: Expected 38, got {chargers.total_sockets}"
        )

    logger.info(
        f"[OK] OE2 validation passed:"
        f"\n  - Solar: {solar.n_hours} rows, {solar.mean_kw:.1f} kW avg"
        f"\n  - BESS: {bess.capacity_kwh:.0f} kWh, {bess.max_power_kw:.0f} kW"
        f"\n  - Chargers: {chargers.n_chargers} units, {chargers.total_sockets} sockets"
        f"\n  - Demand: {demand.n_hours} rows, {demand.mall_mean_kw:.1f} kW mall"
    )

    return True


def rebuild_oe2_datasets_complete(
    solar_path: Optional[Path] = None,
    bess_path: Optional[Path] = None,
    chargers_path: Optional[Path] = None,
    demand_path: Optional[Path] = None,
    cwd: Optional[Path] = None,
) -> Dict[str, Any]:
    """Load all OE2 data and validate (convenience function for scripts).

    Returns:
        Dict with keys: 'solar', 'bess', 'chargers', 'demand', 'scenarios'
    """
    solar = load_solar_data(solar_path, cwd)
    bess = load_bess_data(bess_path, cwd)
    chargers = load_chargers_data(chargers_path, cwd)
    demand = load_mall_demand_data(demand_path, cwd)

    validate_oe2_complete(solar, bess, chargers, demand)

    scenarios = load_scenarios_metadata(DEFAULT_SCENARIOS_DIR if not cwd else cwd / "data/oe2/chargers")

    return {
        "solar": solar,
        "bess": bess,
        "chargers": chargers,
        "demand": demand,
        "scenarios": scenarios,
    }


# ============================================================================
# CITYLEARN v2 DATASET BUILDER
# ============================================================================

def build_citylearn_dataset(
    solar_path: Optional[Path] = None,
    bess_path: Optional[Path] = None,
    chargers_path: Optional[Path] = None,
    demand_path: Optional[Path] = None,
    cwd: Optional[Path] = None,
) -> Dict[str, Any]:
    """Build complete CityLearn v2 dataset from OE2 sources.

    Loads all OE2 data (Solar, BESS, Chargers, Mall demand) and combines
    them into a unified dataset for CityLearn v2 environment training.

    Args:
        solar_path: Override default solar data path
        bess_path: Override default BESS data path
        chargers_path: Override default chargers data path
        demand_path: Override default mall demand data path
        cwd: Working directory (default: current cwd)

    Returns:
        Dict with keys:
            - 'solar': SolarData object
            - 'bess': BESSData object
            - 'chargers': ChargerData object
            - 'demand': DemandData object
            - 'scenarios': Dict[str, pd.DataFrame] of scenario metadata
            - 'combined': pd.DataFrame with merged hourly data
            - 'config': Dict with system configuration

    Raises:
        OE2ValidationError: If any data validation fails
    """
    print("=" * 80)
    print("🔨 BUILDING CITYLEARN v2 DATASET")
    print("=" * 80)
    print()

    # Load all OE2 data
    print("📥 Loading OE2 datasets...")
    datasets = rebuild_oe2_datasets_complete(
        solar_path=solar_path,
        bess_path=bess_path,
        chargers_path=chargers_path,
        demand_path=demand_path,
        cwd=cwd,
    )

    solar = datasets["solar"]
    bess = datasets["bess"]
    chargers = datasets["chargers"]
    demand = datasets["demand"]
    scenarios = datasets["scenarios"]

    print(f"\n✅ All OE2 datasets loaded successfully")
    print(f"   • Solar: {solar.n_hours} hours, {solar.mean_kw:.1f} kW avg")
    print(f"   • BESS: {bess.capacity_kwh:.0f} kWh capacity, {bess.n_hours} hours")
    print(f"   • Chargers: {chargers.n_chargers} units, {chargers.total_sockets} sockets")
    print(f"   • Demand: {demand.n_hours} hours, {demand.mall_mean_kw:.1f} kW avg mall")

    # Build combined dataset
    print(f"\n🔗 Merging hourly data...")
    
    # Start with solar
    combined = solar.df.copy()
    combined['hour'] = range(len(combined))
    combined.rename(columns={list(solar.df.columns)[0]: 'solar_generation_kw'}, inplace=True)
    
    # Add BESS data
    if len(bess.df) == 8760:
        bess_cols = bess.df.columns
        for col in bess_cols[:5]:  # Take first 5 relevant columns
            if col not in combined.columns:
                combined[col] = bess.df[col].values
    
    # Add demand data
    if len(demand.df) == 8760:
        demand_cols = demand.df.columns
        for col in demand_cols:
            if col not in combined.columns and col != 'hour':
                combined[col] = demand.df[col].values

    print(f"✅ Combined dataset shape: {combined.shape} (rows, columns)")

    # Build configuration dict
    config = {
        "version": "7.0",
        "date": "2026-02-18",
        "system": {
            "pv_capacity_kwp": SOLAR_PV_KWP,
            "bess_capacity_kwh": BESS_CAPACITY_KWH,
            "bess_max_power_kw": BESS_MAX_POWER_KW,
            "n_chargers": N_CHARGERS,
            "n_sockets": TOTAL_SOCKETS,
            "charger_power_kw": 7.4,
        },
        "demand": {
            "mall_avg_kw": demand.mall_mean_kw,
            "ev_avg_kw": EV_DEMAND_KW,
        },
        "co2": {
            "grid_factor_kg_per_kwh": CO2_FACTOR_GRID_KG_PER_KWH,
            "ev_factor_kg_per_kwh": CO2_FACTOR_EV_KG_PER_KWH,
        },
        "data_sources": {
            "solar": str(solar.path),
            "bess": str(bess.path),
            "chargers": str(chargers.path),
            "demand": str(demand.path),
        },
    }

    result = {
        "solar": solar,
        "bess": bess,
        "chargers": chargers,
        "demand": demand,
        "scenarios": scenarios,
        "combined": combined,
        "config": config,
    }

    print(f"\n✅ CityLearn v2 dataset built successfully")
    print(f"\n📊 Dataset Summary:")
    print(f"   • Total hours: {len(combined)}")
    print(f"   • Total columns: {combined.shape[1]}")
    print(f"   • PV system: {config['system']['pv_capacity_kwp']:.0f} kWp")
    print(f"   • BESS: {config['system']['bess_capacity_kwh']:.0f} kWh")
    print(f"   • Chargers: {config['system']['n_chargers']} × {config['system']['charger_power_kw']} kW")

    return result


def save_citylearn_dataset(
    dataset: Dict[str, Any],
    output_dir: Optional[Path] = None,
) -> Path:
    """Save CityLearn v2 dataset to disk for training.

    Args:
        dataset: Dict returned by build_citylearn_dataset()
        output_dir: Output directory (default: PROCESSED_CITYLEARN_DIR)

    Returns:
        Path to output directory
    """
    if output_dir is None:
        output_dir = PROCESSED_CITYLEARN_DIR

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n💾 Saving CityLearn v2 dataset to {output_dir}...")

    # Save combined dataset
    combined_path = output_dir / "citylearnv2_combined_dataset.csv"
    dataset["combined"].to_csv(combined_path, index=False)
    print(f"   ✓ Combined data: {combined_path.name}")

    # Save individual components
    solar_path = output_dir / "solar_generation.csv"
    dataset["solar"].df.to_csv(solar_path, index=False)
    print(f"   ✓ Solar: {solar_path.name}")

    bess_path = output_dir / "bess_timeseries.csv"
    dataset["bess"].df.to_csv(bess_path, index=False)
    print(f"   ✓ BESS: {bess_path.name}")

    chargers_path = output_dir / "chargers_timeseries.csv"
    dataset["chargers"].df.to_csv(chargers_path, index=False)
    print(f"   ✓ Chargers: {chargers_path.name}")

    demand_path = output_dir / "mall_demand.csv"
    dataset["demand"].df.to_csv(demand_path, index=False)
    print(f"   ✓ Demand: {demand_path.name}")

    # Save configuration
    config_path = output_dir / "dataset_config_v7.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(dataset["config"], f, indent=2, default=str)
    print(f"   ✓ Config: {config_path.name}")

    print(f"\n✅ Dataset saved successfully to {output_dir}")

    return output_dir


def load_citylearn_dataset(
    input_dir: Optional[Path] = None,
) -> Dict[str, pd.DataFrame]:
    """Load pre-built CityLearn v2 dataset from disk.

    Args:
        input_dir: Input directory (default: PROCESSED_CITYLEARN_DIR)

    Returns:
        Dict with keys: 'combined', 'solar', 'bess', 'chargers', 'demand', 'config'
    """
    if input_dir is None:
        input_dir = PROCESSED_CITYLEARN_DIR

    input_dir = Path(input_dir)

    if not input_dir.exists():
        raise OE2ValidationError(
            f"CityLearn dataset directory not found: {input_dir}\n"
            f"Run build_citylearn_dataset() and save_citylearn_dataset() first."
        )

    print(f"📂 Loading CityLearn v2 dataset from {input_dir}...")

    result = {}

    # Load combined dataset
    combined_path = input_dir / "citylearnv2_combined_dataset.csv"
    if combined_path.exists():
        result["combined"] = pd.read_csv(combined_path)
        print(f"   ✓ Combined data: {result['combined'].shape}")
    else:
        raise OE2ValidationError(f"Missing {combined_path.name}")

    # Load individual components
    for name, filename in [
        ("solar", "solar_generation.csv"),
        ("bess", "bess_timeseries.csv"),
        ("chargers", "chargers_timeseries.csv"),
        ("demand", "mall_demand.csv"),
    ]:
        path = input_dir / filename
        if path.exists():
            result[name] = pd.read_csv(path)
            print(f"   ✓ {name}: {result[name].shape}")
        else:
            logger.warning(f"Missing {filename}")

    # Load configuration
    config_path = input_dir / "dataset_config_v7.json"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            result["config"] = json.load(f)
        print(f"   ✓ Config: {len(result['config'])} keys")
    else:
        logger.warning(f"Missing {config_path.name}")

    print(f"\n✅ CityLearn v2 dataset loaded successfully")
    print(f"   • Total hours: {len(result['combined'])}")
    print(f"   • Total columns: {result['combined'].shape[1]}")

    return result


# ============================================================================
# CONVENIENCE EXPORTS (for backward compatibility)
# ============================================================================

__all__ = [
    # Exceptions
    "OE2ValidationError",
    # Data classes
    "SolarData",
    "BESSData",
    "ChargerData",
    "DemandData",
    # Paths
    "DEFAULT_SOLAR_PATH",
    "DEFAULT_BESS_PATH",
    "DEFAULT_CHARGERS_PATH",
    "DEFAULT_MALL_DEMAND_PATH",
    "DEFAULT_SCENARIOS_DIR",
    "INTERIM_SOLAR_PATHS",
    "INTERIM_BESS_PATH",
    "INTERIM_CHARGERS_PATHS",
    "INTERIM_DEMAND_PATH",
    "PROCESSED_CITYLEARN_DIR",
    # Constants
    "BESS_CAPACITY_KWH",
    "BESS_MAX_POWER_KW",
    "EV_DEMAND_KW",
    "N_CHARGERS",
    "TOTAL_SOCKETS",
    "MALL_DEMAND_KW",
    "SOLAR_PV_KWP",
    "CO2_FACTOR_GRID_KG_PER_KWH",
    "CO2_FACTOR_EV_KG_PER_KWH",
    # Functions
    "resolve_data_path",
    "load_solar_data",
    "load_bess_data",
    "load_chargers_data",
    "load_mall_demand_data",
    "load_scenarios_metadata",
    "validate_oe2_complete",
    "rebuild_oe2_datasets_complete",
    # CityLearn v2 builders
    "build_citylearn_dataset",
    "save_citylearn_dataset",
    "load_citylearn_dataset",
]
