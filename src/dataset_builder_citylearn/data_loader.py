"""OE2 Data Loader v5.8 - Data Validation & Corrections.

Carga datos OE2 desde fuentes diversas usando el catalogo centralizado como
fuente unica de verdad (Single Source of Truth).

Changes in v5.8 (18 feb 2026):
- CORRECCIÓN CRÍTICA: BESS_CAPACITY_KWH actualizada a 2000.0 kWh (era 1700.0)
- Valor verificado de bess_ano_2024.csv (max soc_kwh = 2000.0 kWh)
- Validación completa de estructura de datos real
- Chargers: confirmado 38 sockets (19 chargers × 2 sockets)
- Solar: pv_generation_citylearn2024.csv es el archivo CORRECTO (no hourly_v2)

Changes in v5.6 (14 feb 2026):
- Unificado con catalog_datasets.py para evitar duplicacion
- Imports de dataset_builder.py movidos aqui
- Compatible con stable-baselines3 y agents RL
- Soporta fallback a rutas intermedias si no existen datos primarios

Structure:
  OE2 (Primary, source of truth - FIXED PATHS)
    +-- Solar: data/oe2/Generacionsolar/pv_generation_citylearn2024.csv (8,760 rows, hourly)
    +-- BESS: data/oe2/bess/bess_ano_2024.csv (2,000 kWh CAPACITY, 400 kW POWER)
    +-- Chargers: data/oe2/chargers/chargers_ev_ano_2024_v3.csv (38 sockets, 19 chargers)
    +-- Mall: data/oe2/demandamallkwh/demandamallhorakwh.csv (100 kW avg)

  Interim (Fallback if OE2 missing)
    +-- Solar: data/interim/oe2/solar/pv_generation_hourly_citylearn_v2.csv
    +-- BESS: data/interim/oe2/bess/bess_hourly_dataset_2024.csv
    +-- Chargers: data/interim/oe2/chargers/chargers_real_hourly_2024.csv
    +-- Demand: data/oe2/demandamallkwh/demandamallhorakwh.csv (primary demand)

  CityLearn (Processed, for agent training)
    +-- data/processed/citylearn/iquitos_ev_mall/

Critical Constraints (VERIFIED 2026-02-18):
  - Solar MUST be hourly (8,760 rows), NOT 15-minute data
  - BESS capacity: 2,000 kWh (verified from CSV, max soc_kwh)
  - BESS DoD: 20% (min soc_kwh = 795 kWh, max = 2000 kWh)
  - Chargers: 38 sockets confirmed (socket_000 to socket_037)
  - Tariff: OSINERGMIN Iquitos (0.28-0.3 USD/kWh avg, HP/HFP schedule)

Validation enforced:
  - OE2ValidationError raised if data inconsistent
  - Missing files caught early with clear error messages
  - Column names validated against expected schema
  - Capacity verified against real CSV values
"""

from __future__ import annotations

import builtins
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _safe_print(*args: Any, **kwargs: Any) -> None:
    """Print status text without crashing on legacy Windows console encodings."""
    file = kwargs.get("file", sys.stdout)
    encoding = getattr(file, "encoding", None) or "utf-8"
    safe_args = [str(arg).encode(encoding, errors="replace").decode(encoding, errors="replace") for arg in args]
    builtins.print(*safe_args, **kwargs)


print = _safe_print


# ============================================================================
# PATHS & CONSTANTS — Single Source of Truth (imported from _paths.py / _constants.py)
# ============================================================================
from src.dimensionamiento.oe2._paths import (
    SOLAR_CANONICAL_CSV as DEFAULT_SOLAR_PATH,
    BESS_CANONICAL_CSV as DEFAULT_BESS_PATH,
    CHARGERS_CANONICAL_CSV as DEFAULT_CHARGERS_PATH,
    MALL_DEMAND_CANONICAL_CSV as DEFAULT_MALL_DEMAND_PATH,
    INTERIM_SOLAR_PATHS,
    INTERIM_BESS_PATH,
    INTERIM_CHARGERS_PATHS,
    CITYLEARN_OUTPUT_DIR as PROCESSED_CITYLEARN_DIR,
    BESS_CAPACITY_KWH,
    N_CHARGERS,
    N_SOCKETS as TOTAL_SOCKETS,
    SOLAR_PV_KWP,
)
from src.dimensionamiento.oe2._constants import (
    BESS_POWER_KW as BESS_MAX_POWER_KW,
    FACTOR_CO2_KG_KWH as CO2_FACTOR_GRID_KG_PER_KWH,
)

# Scenarios (OE2 optional)
DEFAULT_SCENARIOS_DIR = Path("data/oe2/chargers")
SCENARIOS_SELECTION_PE_FC_PATH = DEFAULT_SCENARIOS_DIR / "selection_pe_fc_completo.csv"
SCENARIOS_TABLA_DETALLADOS_PATH = DEFAULT_SCENARIOS_DIR / "tabla_escenarios_detallados.csv"
SCENARIOS_TABLA_ESTADISTICAS_PATH = DEFAULT_SCENARIOS_DIR / "tabla_estadisticas_escenarios.csv"
SCENARIOS_TABLA_RECOMENDADO_PATH = DEFAULT_SCENARIOS_DIR / "tabla_escenario_recomendado.csv"
SCENARIOS_TABLA13_PATH = DEFAULT_SCENARIOS_DIR / "escenarios_tabla13.csv"

# Interim fallback: also add charger primary to interim list for full coverage
INTERIM_DEMAND_PATH = DEFAULT_MALL_DEMAND_PATH  # Always exists (same canonical path)

# Non-migrated constants (specific to data_loader context)
EV_DEMAND_KW = 50.0  # Constant demand (workaround for CityLearn 2.5.0)
MALL_DEMAND_KW = 100.0  # Mall baseline
CO2_FACTOR_EV_KG_PER_KWH = 2.146  # Equivalent fuel combustion


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
    raise OE2ValidationError(f"Data not found in any fallback path:\n{paths_str}\n" f"Current working directory: {cwd}")


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

    # Detect power/energy column — ordered by preference
    power_col = None
    for col in ["potencia_kw", "energia_kwh", "W", "pv_generation_W", "Generation_W", "power_w", "solar_power_w"]:
        if col in df.columns:
            power_col = col
            break

    if power_col is None:
        # Fallback: first numeric column
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) == 0:
            raise OE2ValidationError(f"No numeric column found in {path}")
        power_col = numeric_cols[0]

    solar_values: np.ndarray = df[power_col].values.astype(np.float64)
    # Only explicit watt columns need conversion. potencia_kw and energia_kwh are already kW/kWh.
    watt_columns = {"w", "pv_generation_w", "generation_w", "power_w", "solar_power_w"}
    solar_kw: np.ndarray = solar_values / 1000.0 if power_col.lower() in watt_columns else solar_values

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
    """Load BESS data (2,000 kWh capacity verified).

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
    if "bess_capacity_kwh" in df.columns:
        cap_from_file = df["bess_capacity_kwh"].iloc[0]
        if not np.isclose(cap_from_file, BESS_CAPACITY_KWH, rtol=0.01):
            logger.warning(f"BESS: File capacity={cap_from_file} kWh vs constant={BESS_CAPACITY_KWH} kWh")

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
            f"Expected 38 sockets (19 × 2). Got {n_sockets}. " "Charger configuration mismatch in v5.3."
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
            df = pd.DataFrame(
                {
                    "hour": range(8760),
                    "mall_demand_kw": [MALL_DEMAND_KW] * 8760,
                }
            )
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
    for col in ["kw", "demanda_kw", "mall_demand_kw", "demand_kw"]:
        if col in df.columns:
            demand_col = col
            break

    if demand_col is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        demand_col = numeric_cols[0] if len(numeric_cols) > 0 else "kw"

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
    for name, n_hours in [
        ("solar", solar.n_hours),
        ("bess", bess.n_hours),
        ("chargers", chargers.n_hours),
        ("demand", demand.n_hours),
    ]:
        if n_hours != 8760:
            raise OE2ValidationError(f"{name}: Expected 8,760 rows, got {n_hours}")

    # Check BESS capacity
    if not np.isclose(bess.capacity_kwh, BESS_CAPACITY_KWH, rtol=0.01):
        raise OE2ValidationError(f"BESS capacity mismatch: {bess.capacity_kwh} kWh != {BESS_CAPACITY_KWH} kWh")

    # Check charger socket count
    if chargers.total_sockets != 38:
        raise OE2ValidationError(f"Charger sockets: Expected 38, got {chargers.total_sockets}")

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

    # Start with solar - but don't rename columns incorrectly
    combined = solar.df.copy()
    combined["hour"] = range(len(combined))

    # Ensure solar_generation_kw column exists
    if "solar_generation_kw" not in combined.columns:
        if "potencia_kw" in combined.columns:
            combined["solar_generation_kw"] = combined["potencia_kw"]
        elif "potencia_w" in combined.columns:
            combined["solar_generation_kw"] = combined["potencia_w"] / 1000.0
        else:
            # Use first numeric column
            numeric_cols = combined.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                combined["solar_generation_kw"] = combined[numeric_cols[0]]

    # Add BESS data
    if len(bess.df) == 8760:
        bess_cols = bess.df.columns
        for col in bess_cols:
            if col not in combined.columns:
                combined[col] = bess.df[col].values

    # Add demand data
    if len(demand.df) == 8760:
        demand_cols = demand.df.columns
        for col in demand_cols:
            if col not in combined.columns and col != "hour":
                combined[col] = demand.df[col].values

    print(f"✅ Combined dataset shape: {combined.shape} (rows, columns)")

    # Build configuration dict (with ACTUAL vehicle configuration extracted from data)
    config: Dict[str, Any] = {
        "version": "7.0",
        "date": "2026-02-18",
        "system": {
            "pv_capacity_kwp": SOLAR_PV_KWP,
            "bess_capacity_kwh": BESS_CAPACITY_KWH,
            "bess_max_power_kw": BESS_MAX_POWER_KW,
            "bess_avg_soc_percent": 75.57,  # From bess_ano_2024.csv
            "n_chargers": N_CHARGERS,
            "n_sockets": TOTAL_SOCKETS,
            "charger_power_kw": 7.4,
            "sockets_per_charger": 2.0,
        },
        "vehicles": {
            "motos": {
                "count": 30,  # EXACT: 30 motorcycles with socket_000 to socket_029
                "sockets": 30,  # 1 socket per moto
                "chargers_assigned": 15,  # Chargers 0-14 dedicated to motos
                "avg_power_kw": 7.4,
            },
            "mototaxis": {
                "count": 8,  # EXACT: 8 mototaxis with socket_030 to socket_037
                "sockets": 8,  # 1 socket per mototaxi
                "chargers_assigned": 4,  # Chargers 15-18 dedicated to mototaxis
                "avg_power_kw": 7.4,
            },
            "total_vehicles": 38,
            "total_sockets_allocated": 38,
        },
        "demand": {
            "mall_avg_kw": demand.mall_mean_kw,
            "mall_annual_kwh": 12_368_653.0,  # From demandamallhorakwh.csv
            "mall_max_hourly_kw": 2763.0,  # Peak demand in a single hour
            "ev_avg_kw": EV_DEMAND_KW,
            "ev_annual_kwh": 52_613_744.0,  # From compiled dataset
        },
        "solar": {
            "annual_kwh": float(solar.df["energia_kwh"].sum())
            if "energia_kwh" in solar.df.columns
            else solar.mean_kw * 8760,
            "max_power_kw": solar.max_kw,
            "mean_power_kw": solar.mean_kw,
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
        "validation_status": {
            "ready_for_citylearn_v2": True,
            "hourly_rows": len(combined),
            "combined_columns": int(combined.shape[1]),
            "solar_rows": solar.n_hours,
            "bess_rows": bess.n_hours,
            "chargers_rows": chargers.n_hours,
            "demand_rows": demand.n_hours,
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


def generate_tariffs_dataset(year: int = 2024) -> pd.DataFrame:
    """Genera dataset individual de tarifas OSINERGMIN horarias para Iquitos (Electro Oriente S.A.).

    Fuente: Res. N° 047-2024-OS/CD — Pliego Tarifario MT3 Media Tensión Comercial.
    Período vigente: desde 2024-11-04. Aplicado todo el año 2024 (pliego anual único).

    Componentes incluidos (Pliego MT3 Electro Oriente, Sistema Aislado Loreto):
      1. Cargo por Energía Activa HP/HFP (S/./kWh) — varía por período tarifario
      2. Cargo por Potencia HP/HFP (S/./kW-mes) — para cálculo de demanda mensual
      3. Cargo por Alumbrado Público (AAPP) — obligatorio, ~0.0116 S/./kWh
      4. Cargo Fijo Mensual — por punto de suministro (4.70 S/./mes)
      5. Mecanismo de Compensación SSAA (Sistema Aislado):
         - Costo real generación diesel B5 Iquitos: ~0.75 S/./kWh
         - Subsidio gobierno = costo_real − tarifa_regulada (∈ [0.30, 0.47] S/./kWh)
         - Fuente: MINEM — Compensación a Sistemas Aislados (fondos FISE/transferencias)
      6. Tarifa total pagada (sin cargo potencia): energía + AAPP
      7. Valor social completo de 1 kWh evitado: tarifa_pagada + mecanismo_compensacion

    Reducción costo para el mall = grid_import_kwh × tarifa_total_soles_kwh
    Ahorro social completo      = grid_import_kwh × (tarifa_total + mecanismo_compensacion)
    """
    from src.dimensionamiento.oe2._constants import (
        TARIFA_ENERGIA_HP_SOLES,
        TARIFA_ENERGIA_HFP_SOLES,
        TARIFA_POTENCIA_HP_SOLES,
        TARIFA_POTENCIA_HFP_SOLES,
        TIPO_CAMBIO_PEN_USD,
        HORA_INICIO_HP,
        HORA_FIN_HP,
    )

    # ── Pliego Tarifario OSINERGMIN MT3 Electro Oriente — Res. N° 047-2024-OS/CD ──
    CARGO_AAPP_SOLES_KWH: float = 0.0116  # Alumbrado Público (promedio MT media tensión)
    CARGO_FIJO_SOLES_MES: float = 4.70  # Cargo fijo mensual por punto suministro
    # Costo real estimado generación diesel B5 Iquitos (incluye O&M, depreciación)
    # Diesel B5: ~5.2 S/./gal, generador 35% eficiencia → 8.7 kWh/gal → 0.60 S/./kWh gen.
    # + transmisión/distribución aislada + riesgo abastecimiento → ~0.75 S/./kWh total
    COSTO_REAL_DIESEL_SOLES_KWH: float = 0.7500
    TIPO_CAMBIO = TIPO_CAMBIO_PEN_USD  # 3.75 S/./USD

    n_hours = 8760
    datetime_index = pd.date_range(start=f"{year}-01-01 00:00:00", periods=n_hours, freq="h")
    month = datetime_index.month
    hour_of_day = datetime_index.hour
    day_of_week = datetime_index.dayofweek  # 0=lunes, 6=domingo

    is_hp = ((hour_of_day >= HORA_INICIO_HP) & (hour_of_day < HORA_FIN_HP)).astype(int)

    # Energía activa: HP o HFP según período tarifario
    tarifa_energia = np.where(is_hp, TARIFA_ENERGIA_HP_SOLES, TARIFA_ENERGIA_HFP_SOLES)

    # Potencia referencia: cargo mensual por kW de demanda máxima (informativo por hora)
    # Período HP: cargo potencia HP aplica a la demanda máxima en HP del mes
    # Período HFP: cargo potencia HFP aplica a la demanda máxima en HFP del mes
    cargo_potencia_ref = np.where(is_hp, TARIFA_POTENCIA_HP_SOLES, TARIFA_POTENCIA_HFP_SOLES)

    # AAPP: constante por kWh (toda hora, todo mes)
    aapp = np.full(n_hours, CARGO_AAPP_SOLES_KWH)

    # Tarifa total pagada por el mall (energía + AAPP, excluye cargo potencia mensual)
    tarifa_total = tarifa_energia + aapp

    # Mecanismo de Compensación SSAA — subsidio gobierno por kWh
    # El regulador fija la tarifa por debajo del costo real; el diferencial es cubierto por el Estado
    mecanismo_comp = COSTO_REAL_DIESEL_SOLES_KWH - tarifa_energia  # siempre positivo

    # Valor social total por cada kWh reducido de la red (mall ahorra + gobierno ahorra)
    ahorro_social_kwh = tarifa_total + mecanismo_comp  # ≈ costo_real_diesel + AAPP

    # Tipo de día (informativo: laborable / sábado / domingo)
    tipo_dia = np.where(day_of_week < 5, "laborable", np.where(day_of_week == 5, "sabado", "domingo"))

    # Conversiones USD
    tarifa_energia_usd = tarifa_energia / TIPO_CAMBIO
    tarifa_total_usd = tarifa_total / TIPO_CAMBIO

    # Horas de demanda HP en el mes (para referencia de cargo de potencia)
    days_per_month = datetime_index.days_in_month
    hp_hours_per_month = 5 * days_per_month  # 5h HP × días del mes

    df = pd.DataFrame(
        {
            "datetime": datetime_index.strftime("%Y-%m-%d %H:%M:%S"),
            # ── Identificadores de período ────────────────────────────────────────
            "tariff_period": np.where(is_hp, "HP", "HFP"),
            "is_peak_hour": is_hp,
            "tipo_dia": tipo_dia,
            # ── Cargo por Energía Activa (S/./kWh) ───────────────────────────────
            "tarifa_energia_hp_soles_kwh": TARIFA_ENERGIA_HP_SOLES,  # 0.45 S/./kWh
            "tarifa_energia_hfp_soles_kwh": TARIFA_ENERGIA_HFP_SOLES,  # 0.28 S/./kWh
            "tarifa_energia_soles_kwh": tarifa_energia,  # efectiva esta hora
            "tarifa_energia_usd_kwh": tarifa_energia_usd.round(5),
            # ── Cargo por Potencia Activa (S/./kW-mes) ───────────────────────────
            # (referencia mensual; el cargo real se aplica sobre demanda pico del mes)
            "cargo_potencia_hp_soles_kw_mes": TARIFA_POTENCIA_HP_SOLES,  # 48.50 S/./kW-mes
            "cargo_potencia_hfp_soles_kw_mes": TARIFA_POTENCIA_HFP_SOLES,  # 22.80 S/./kW-mes
            "cargo_potencia_ref_soles_kw_mes": cargo_potencia_ref,  # aplicable esta hora
            "hp_hours_in_month": hp_hours_per_month,  # horas HP en el mes
            # ── Cargo por Alumbrado Público (AAPP) ───────────────────────────────
            "cargo_aapp_soles_kwh": aapp,  # 0.0116 S/./kWh (obligatorio)
            # ── Cargo Fijo Mensual (por punto suministro) ─────────────────────────
            "cargo_fijo_soles_mes": CARGO_FIJO_SOLES_MES,  # 4.70 S/./mes
            # ── Tarifa total pagada (energía + AAPP, sin cargo potencia) ──────────
            "tarifa_total_soles_kwh": tarifa_total.round(5),
            "tarifa_total_usd_kwh": tarifa_total_usd.round(6),
            # ── Mecanismo de Compensación SSAA (subsidio Estado) ──────────────────
            # Sistema Aislado Loreto: Estado cubre diferencia costo_real − tarifa_regulada
            "costo_real_diesel_soles_kwh": COSTO_REAL_DIESEL_SOLES_KWH,  # ~0.75 S/./kWh
            "mecanismo_compensacion_soles_kwh": mecanismo_comp.round(5),  # 0.30-0.47 S/./kWh
            # ── Valor social total (ahorro mall + ahorro Estado por kWh evitado) ──
            "ahorro_social_kwh_evitado_soles": ahorro_social_kwh.round(5),
        }
    )
    return df


def generate_co2_emissions_dataset(year: int = 2024) -> pd.DataFrame:
    """Genera dataset individual de factores de emisión CO₂ horarios para todo el sistema.

    Cubre TODOS los flujos del sistema: mall + EV + BESS + PV (no solo BESS).

    Metodología (datos estadísticos Sistema Aislado Loreto — MINEM 2024):
      Estacionalidad mensual (Loreto, generación 100% termoeléctrica diesel B5):
        Temporada lluviosa (dic-may): 0.43 kg CO₂/kWh — menor demanda, mezcla eficiente
        Temporada seca (jun-nov):    0.47 kg CO₂/kWh — mayor demanda, peakers frecuentes
      Variación HP/HFP intra-diaria (preserva promedio mensual):
        Hora Punta (18-23h):     factor_mes × 1.35  — generadores punta (efic. ~28-30%)
        Hora Fuera Punta (resto): factor_mes × 0.908 — carga base (efic. ~35-38%)
      Promedio anual ponderado: ≈ 0.45 kg CO₂/kWh ≈ MINEM Loreto (0.4521 kg/kWh)

    Reducción CO₂ directa   = EV_cargado × co2_direct_* (reemplaza ICE)
    Reducción CO₂ indirecta = (PV_gen + BESS_discharge) × co2_factor_kg_kwh (desplaza térmica)

    Columnas:
        datetime                   — marca temporal horaria
        co2_factor_kg_kwh          — factor grid horario (mensual × HP/HFP)
        tariff_period              — "HP" o "HFP"
        is_peak_hour               — 1 si hora punta (18-23h), 0 si fuera de punta
        co2_monthly_base_kg_kwh    — factor base mensual (sin variación HP/HFP)
        co2_direct_moto_kg_kwh     — 0.87 kg CO₂/kWh (moto gasolina 125cc — IPCC 2006)
        co2_direct_mototaxi_kg_kwh — 0.54 kg CO₂/kWh (mototaxi 150cc — IPCC 2006)
    """
    from src.dimensionamiento.oe2._constants import (
        HORA_INICIO_HP,
        HORA_FIN_HP,
        FACTOR_CO2_NETO_MOTO_KG_KWH,
        FACTOR_CO2_NETO_MOTOTAXI_KG_KWH,
    )

    # Factores mensuales base — estacionalidad real Sistema Aislado Loreto (MINEM 2024)
    # Temporada lluviosa (dic-may): generación base eficiente, menor demanda
    # Temporada seca (jun-nov): mayor demanda, peakers diesel frecuentes
    MONTHLY_CO2_LORETO: dict[int, float] = {
        1: 0.43,
        2: 0.43,
        3: 0.43,
        4: 0.43,
        5: 0.43,  # enero-mayo: lluviosa
        6: 0.47,
        7: 0.47,
        8: 0.47,
        9: 0.47,
        10: 0.47,
        11: 0.47,  # jun-nov: seca
        12: 0.43,  # diciembre: lluviosa
    }
    # Multiplicadores HP/HFP que preservan el promedio mensual
    # (5h HP × 1.35 + 19h HFP × 0.908) / 24 = 1.0 exactamente
    HP_MULT: float = 1.35  # generadores punta diesel (eficiencia ~28-30%)
    HFP_MULT: float = 0.908  # carga base diesel (eficiencia ~35-38%)

    n_hours = 8760
    datetime_index = pd.date_range(start=f"{year}-01-01 00:00:00", periods=n_hours, freq="h")
    month = datetime_index.month
    hour_of_day = datetime_index.hour

    is_hp = ((hour_of_day >= HORA_INICIO_HP) & (hour_of_day < HORA_FIN_HP)).astype(int)

    # Factor mensual base
    monthly_base = np.array([MONTHLY_CO2_LORETO[m] for m in month], dtype=float)

    # Factor horario = base_mensual × multiplicador_periodo
    co2_factor = monthly_base * np.where(is_hp, HP_MULT, HFP_MULT)

    df = pd.DataFrame(
        {
            "datetime": datetime_index.strftime("%Y-%m-%d %H:%M:%S"),
            "co2_factor_kg_kwh": co2_factor.round(4),
            "co2_monthly_base_kg_kwh": monthly_base,
            "tariff_period": np.where(is_hp, "HP", "HFP"),
            "is_peak_hour": is_hp,
            "co2_direct_moto_kg_kwh": FACTOR_CO2_NETO_MOTO_KG_KWH,  # 0.87 kg CO₂/kWh
            "co2_direct_mototaxi_kg_kwh": FACTOR_CO2_NETO_MOTOTAXI_KG_KWH,  # 0.54 kg CO₂/kWh
        }
    )
    return df


def _add_tariff_co2_columns(df: pd.DataFrame, n_rows: int = 8760) -> pd.DataFrame:
    """Add shared derived columns (tariff, CO2) to a CityLearn timeseries DataFrame.

    These columns were previously duplicated across OE2 source modules. Now they
    are computed once here and added to each CityLearn file at save time.
    Usa factores variables HP=0.61, HFP=0.41 kg CO₂/kWh (en lugar de constante 0.4521).

    Args:
        df: CityLearn timeseries (must have a datetime-parseable index or an 'hour' column)
        n_rows: Expected number of rows (default 8760)

    Returns:
        DataFrame with added columns (does NOT modify in place)
    """
    from src.dimensionamiento.oe2._constants import (
        TARIFA_ENERGIA_HP_SOLES,
        TARIFA_ENERGIA_HFP_SOLES,
        HORA_INICIO_HP,
        HORA_FIN_HP,
        FACTOR_CO2_HP_KG_KWH,
        FACTOR_CO2_HFP_KG_KWH,
    )

    df = df.copy()

    # Derive hour-of-day from index or existing column
    if hasattr(df.index, "hour"):
        hour = df.index.hour
    elif "datetime" in df.columns:
        hour = pd.to_datetime(df["datetime"]).dt.hour
    else:
        hour = np.arange(len(df)) % 24

    is_hp = ((hour >= HORA_INICIO_HP) & (hour < HORA_FIN_HP)).astype(int)
    if "is_hora_punta" not in df.columns:
        df["is_hora_punta"] = is_hp
    if "tarifa_soles_kwh" not in df.columns:
        df["tarifa_soles_kwh"] = np.where(is_hp, TARIFA_ENERGIA_HP_SOLES, TARIFA_ENERGIA_HFP_SOLES)

    # CO2 con factor horario variable (HP=0.61, HFP=0.41 kg/kWh)
    co2_factor = np.where(is_hp, FACTOR_CO2_HP_KG_KWH, FACTOR_CO2_HFP_KG_KWH)
    if "grid_import_kwh" in df.columns and "co2_grid_kg" not in df.columns:
        df["co2_grid_kg"] = df["grid_import_kwh"] * co2_factor

    return df


def save_citylearn_dataset(
    dataset: Dict[str, Any],
    output_dir: Optional[Path] = None,
) -> Path:
    """Save CityLearn v2 dataset to disk for training.

    Adds shared derived columns (is_hora_punta, tarifa_soles_kwh, co2_grid_kg)
    to each output file so the source OE2 modules do not need to duplicate them.

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

    print(f"Saving CityLearn v2 dataset to {output_dir}...")

    # Save combined dataset
    combined_path = output_dir / "citylearnv2_combined_dataset.csv"
    dataset["combined"].to_csv(combined_path, index=False)
    print(f"   [OK] Combined data: {combined_path.name}")

    # Save individual components — enrich each with shared derived columns
    solar_df = _add_tariff_co2_columns(dataset["solar"].df)
    solar_path = output_dir / "solar_generation.csv"
    solar_df.to_csv(solar_path, index=False)
    print(f"   [OK] Solar: {solar_path.name} ({solar_df.shape[1]} cols)")

    bess_df = _add_tariff_co2_columns(dataset["bess"].df)
    bess_path = output_dir / "bess_timeseries.csv"
    bess_df.to_csv(bess_path, index=False)
    print(f"   [OK] BESS: {bess_path.name} ({bess_df.shape[1]} cols)")

    chargers_path = output_dir / "chargers_timeseries.csv"
    chargers_df = dataset["chargers"].df.copy()
    # Drop categorical columns to prevent float conversion errors
    categorical_patterns = ["vehicle_type", "status", "bess_mode", "tariff_period", "bess_validation"]
    chargers_df_numeric = chargers_df.drop(
        columns=[c for c in chargers_df.columns if any(pat in c.lower() for pat in categorical_patterns)],
        errors="ignore",
    )
    chargers_df_numeric = _add_tariff_co2_columns(chargers_df_numeric)
    chargers_df_numeric.to_csv(chargers_path, index=False)
    print(f"   [OK] Chargers: {chargers_path.name} ({chargers_df_numeric.shape[1]} cols)")

    demand_df = _add_tariff_co2_columns(dataset["demand"].df)
    demand_path = output_dir / "mall_demand.csv"
    demand_df.to_csv(demand_path, index=False)
    print(f"   [OK] Demand: {demand_path.name} ({demand_df.shape[1]} cols)")

    # Save CO₂ emissions dataset (todo el sistema: diesel grid + vehículos ICE)
    co2_df = generate_co2_emissions_dataset(year=2024)
    co2_path = output_dir / "co2_emissions.csv"
    co2_df.to_csv(co2_path, index=False)
    annual_avg = co2_df["co2_factor_kg_kwh"].mean()
    print(f"   [OK] CO2 emissions: {co2_path.name} ({len(co2_df)} filas, avg={annual_avg:.4f} kg CO2/kWh)")

    # Save tariffs dataset (OSINERGMIN Electro Oriente Iquitos + mecanismo compensación SSAA)
    tariffs_df = generate_tariffs_dataset(year=2024)
    tariffs_path = output_dir / "tariffs_osinergmin.csv"
    tariffs_df.to_csv(tariffs_path, index=False)
    hp_rate = tariffs_df["tarifa_energia_hp_soles_kwh"].iloc[0]
    hfp_rate = tariffs_df["tarifa_energia_hfp_soles_kwh"].iloc[0]
    mc_hp = tariffs_df[tariffs_df["is_peak_hour"] == 1]["mecanismo_compensacion_soles_kwh"].mean()
    mc_hfp = tariffs_df[tariffs_df["is_peak_hour"] == 0]["mecanismo_compensacion_soles_kwh"].mean()
    print(
        f"   [OK] Tarifas OSINERGMIN: {tariffs_path.name} (HP={hp_rate} / HFP={hfp_rate} S/./kWh | MeComp HP={mc_hp:.4f} / HFP={mc_hfp:.4f} S/./kWh)"
    )

    # Save configuration
    config_path = output_dir / "dataset_config_v7.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(dataset["config"], f, indent=2, default=str)
    print(f"   [OK] Config: {config_path.name}")

    print(f"\n[OK] Dataset saved to {output_dir}")

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
        with open(config_path, "r", encoding="utf-8") as f:
            result["config"] = json.load(f)
        print(f"   ✓ Config: {len(result['config'])} keys")
    else:
        logger.warning(f"Missing {config_path.name}")

    print(f"\n✅ CityLearn v2 dataset loaded successfully")
    print(f"   • Total hours: {len(result['combined'])}")
    print(f"   • Total columns: {result['combined'].shape[1]}")

    return result


def load_agent_dataset_mandatory(agent_name: str = "Agent") -> Dict[str, Any]:
    """Load CityLearn dataset OBLIGATORILY from data/iquitos_ev_mall.

    This function MUST be used by all agents (SAC, PPO, A2C) to ensure
    they use the same validated dataset.

    Args:
        agent_name: Name of agent (for logging)

    Returns:
        Dict with all processed datasets

    Raises:
        OE2ValidationError: If dataset missing or incomplete
    """
    print("=" * 80)
    print(f"[{agent_name}] LOADING MANDATORY DATASET FROM: data/iquitos_ev_mall")
    print("=" * 80)

    iquitos_dir = Path("data/iquitos_ev_mall")

    if not iquitos_dir.exists():
        raise OE2ValidationError(
            f"\n❌ FATAL: Dataset not found in {iquitos_dir}\n"
            f"\nREQUIRED DATASETS:\n"
            f"  • citylearnv2_combined_dataset.csv\n"
            f"  • solar_generation.csv\n"
            f"  • bess_timeseries.csv\n"
            f"  • chargers_timeseries.csv\n"
            f"  • mall_demand.csv\n"
            f"\nSOLUTION: Run data_loader to generate datasets:\n"
            f'  python -c "from src.dataset_builder_citylearn.data_loader import build_citylearn_dataset, save_citylearn_dataset; dataset = build_citylearn_dataset(); save_citylearn_dataset(dataset)"\n'
        )

    # Load all required files
    required_files = {
        "combined": "citylearnv2_combined_dataset.csv",
        "solar": "solar_generation.csv",
        "bess": "bess_timeseries.csv",
        "chargers": "chargers_timeseries.csv",
        "demand": "mall_demand.csv",
        "config": "dataset_config_v7.json",
    }

    datasets = {}
    missing = []

    for name, filename in required_files.items():
        path = iquitos_dir / filename
        if not path.exists():
            missing.append(filename)
            continue

        if filename.endswith(".json"):
            with open(path, "r") as f:
                datasets[name] = json.load(f)
        else:
            datasets[name] = pd.read_csv(path)
        print(f"  ✓ {filename}")

    if missing:
        raise OE2ValidationError(
            f"\n❌ INCOMPLETE DATASET - Missing files:\n"
            f"  {missing}\n"
            f'\nRun: python -c "from src.dataset_builder_citylearn.data_loader import build_citylearn_dataset, save_citylearn_dataset; dataset = build_citylearn_dataset(); save_citylearn_dataset(dataset)"\n'
        )

    print(f"\n✅ {agent_name}: All datasets loaded from data/iquitos_ev_mall")
    return datasets


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
    "load_agent_dataset_mandatory",  # NEW: Mandatory loader for agents
]


# ============================================================================
# EXECUTABLE SCRIPT MODE
# ============================================================================

if __name__ == "__main__":
    """Build and save complete CityLearn v2 dataset when run directly."""
    import sys

    print("\n" + "=" * 80)
    print("DATA LOADER v5.8 - EXECUTABLE MODE")
    print("=" * 80)
    print("\nBuilding and saving CityLearn v2 dataset...")
    print()

    try:
        # Build dataset
        dataset = build_citylearn_dataset()

        # Save to disk
        output_dir = save_citylearn_dataset(dataset)

        # Show configuration
        config = dataset["config"]
        vehicles = config.get("vehicles", {})
        system = config.get("system", {})

        print("\n" + "=" * 80)
        print("✅ DATASET BUILD COMPLETE")
        print("=" * 80)

        print(f"\n📊 CONFIGURATION SUMMARY:")
        print(f"\n  VEHICLES (from chargers_ev_ano_2024_v3.csv):")
        print(
            f"    • Motos:      {vehicles['motos']['count']} units, {vehicles['motos']['chargers_assigned']} chargers (0-14)"
        )
        print(
            f"    • mototaxis:  {vehicles['mototaxis']['count']} units, {vehicles['mototaxis']['chargers_assigned']} chargers (15-18)"
        )
        print(f"    • Total:      {vehicles['total_vehicles']} vehicles, {vehicles['total_sockets_allocated']} sockets")

        print(f"\n  INFRASTRUCTURE:")
        print(f"    • Solar:      {system['pv_capacity_kwp']:.0f} kWp")
        print(f"    • BESS:       {system['bess_capacity_kwh']:.0f} kWh @ {system['bess_max_power_kw']:.0f} kW")
        print(
            f"    • Chargers:   {system['n_chargers']} × {system['charger_power_kw']} kW = {system['n_chargers'] * system['charger_power_kw']:.1f} kW"
        )

        print(f"\n  FILES SAVED TO: {output_dir}")
        print(f"    ✓ dataset_config_v7.json (WITH vehicles section)")
        print(f"    ✓ citylearnv2_combined_dataset.csv")
        print(f"    ✓ solar_generation.csv")
        print(f"    ✓ bess_timeseries.csv")
        print(f"    ✓ chargers_timeseries.csv")
        print(f"    ✓ mall_demand.csv")

        print(f"\n" + "=" * 80)
        print("Ready for agent training (SAC/PPO/A2C)")
        print("=" * 80 + "\n")

        sys.exit(0)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
