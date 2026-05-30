"""
Rutas canónicas OE2 — fuente única de verdad (Single Source of Truth).

Define las rutas de entrada y salida de cada módulo OE2 para que:
  - bess.py, chargers.py, solar_pvlib.py escriban AQUÍ
  - data_loader.py lea DESDE AQUÍ
  - configs/default.yaml referencie ESTAS rutas
  - Los tests validen consistencia sin hardcodear paths

Arquitectura de datos:
  data/oe2/            ← fuentes primarias (datasets generados por OE2)
  data/interim/oe2/    ← fallbacks (si primaria no existe o es más antigua)
  data/iquitos_ev_mall/ ← salida final procesada para agentes RL (CityLearn v2)
"""
from __future__ import annotations

from pathlib import Path

# ============================================================================
# RAÍZ DEL PROYECTO
# ============================================================================
# Se resuelve en runtime para que funcione desde cualquier CWD
PROJECT_ROOT = Path(__file__).resolve().parents[4]  # src/dimensionamiento/oe2/_paths.py → root

# ============================================================================
# DIRECTORIO OE2 PRIMARIO — salida de los generadores OE2
# ============================================================================
OE2_DATA_DIR = Path("data/oe2")

# ============================================================================
# RUTAS CANÓNICAS DE ENTRADA/SALIDA POR MÓDULO
# Estas son las rutas que cada módulo OE2 ESCRIBE y que data_loader LEE.
# ============================================================================

# --- Solar (generacionsolar/disenopvlib/solar_pvlib.py) ---
SOLAR_OUTPUT_DIR = OE2_DATA_DIR / "Generacionsolar"
SOLAR_CANONICAL_CSV = SOLAR_OUTPUT_DIR / "pv_generation_citylearn2024.csv"
SOLAR_CERTIFICATION_JSON = SOLAR_OUTPUT_DIR / "CERTIFICACION_SOLAR_DATASET_2024.json"
# NOTA: pv_generation_hourly_citylearn_v2.csv es DEPRECATED — usar SOLAR_CANONICAL_CSV

# --- BESS (disenobess/bess.py) ---
BESS_OUTPUT_DIR = OE2_DATA_DIR / "bess"
BESS_CANONICAL_CSV = BESS_OUTPUT_DIR / "bess_ano_2024.csv"
BESS_DAILY_CSV = BESS_OUTPUT_DIR / "bess_daily_balance_24h.csv"
BESS_RESULTS_JSON = BESS_OUTPUT_DIR / "bess_results.json"

# --- Chargers (disenocargadoresev/chargers.py) ---
CHARGERS_OUTPUT_DIR = OE2_DATA_DIR / "chargers"
CHARGERS_CANONICAL_CSV = CHARGERS_OUTPUT_DIR / "chargers_ev_ano_2024_v3.csv"
CHARGERS_DAILY_CSV = CHARGERS_OUTPUT_DIR / "chargers_ev_dia_2024_v3.csv"
CHARGERS_STATS_CSV = CHARGERS_OUTPUT_DIR / "chargers_real_statistics.csv"

# --- Mall Demand (dato externo, no generado por OE2) ---
MALL_DEMAND_DIR = OE2_DATA_DIR / "demandamallkwh"
MALL_DEMAND_CANONICAL_CSV = MALL_DEMAND_DIR / "demandamallhorakwh.csv"

# ============================================================================
# DIRECTORIOS DE FALLBACK (interim) — si primary no existe
# Sólo para compatibilidad; NO usar para escritura nueva.
# ============================================================================
INTERIM_OE2_DIR = Path("data/interim/oe2")
INTERIM_SOLAR_PATHS: list[Path] = [
    SOLAR_CANONICAL_CSV,                                              # primaria primero
    INTERIM_OE2_DIR / "solar" / "pv_generation_hourly_citylearn_v2.csv",  # fallback
    SOLAR_OUTPUT_DIR / "pv_generation_hourly_citylearn_v2.csv",     # fallback legacy
]
INTERIM_BESS_PATH = INTERIM_OE2_DIR / "bess" / "bess_hourly_dataset_2024.csv"
INTERIM_CHARGERS_PATHS: list[Path] = [
    CHARGERS_CANONICAL_CSV,
    INTERIM_OE2_DIR / "chargers" / "chargers_real_hourly_2024.csv",
]

# ============================================================================
# DIRECTORIO DE SALIDA FINAL — datasets procesados para CityLearn v2 / agentes RL
# Escrito por data_loader.save_citylearn_dataset()
# ============================================================================
CITYLEARN_OUTPUT_DIR = Path("data/iquitos_ev_mall")

# Dataset de factores de emisión CO₂ horarios (todo el sistema)
# Generado por data_loader.generate_co2_emissions_dataset()
CO2_EMISSIONS_CSV = CITYLEARN_OUTPUT_DIR / "co2_emissions.csv"

# Dataset de tarifas OSINERGMIN + mecanismo compensación SSAA (Electro Oriente Iquitos)
# Generado por data_loader.generate_tariffs_dataset()
# Columnas: tarifa energía HP/HFP, cargo potencia, AAPP, mecanismo compensación, ahorro social
TARIFFS_OSINERGMIN_CSV = CITYLEARN_OUTPUT_DIR / "tariffs_osinergmin.csv"

# ============================================================================
# CONSTANTES CLAVE VERIFICADAS
# ============================================================================
BESS_CAPACITY_KWH: float = 2000.0   # Verificado en bess_ano_2024.csv (max soc_kwh)
N_CHARGERS: int = 19                 # Verificado en chargers_ev_ano_2024_v3.csv
N_SOCKETS: int = N_CHARGERS * 2      # 38 sockets totales
SOLAR_PV_KWP: float = 4050.0        # kWp diseño nominal (PVWatts pdc0=4162 kWp, max 3245.9 kW)
SOLAR_HOURLY_ROWS: int = 8760        # 365 días × 24 h = año completo

# ============================================================================
# API PÚBLICA
# ============================================================================
__all__ = [
    "OE2_DATA_DIR",
    "SOLAR_OUTPUT_DIR", "SOLAR_CANONICAL_CSV", "SOLAR_CERTIFICATION_JSON",
    "BESS_OUTPUT_DIR", "BESS_CANONICAL_CSV", "BESS_DAILY_CSV", "BESS_RESULTS_JSON",
    "CHARGERS_OUTPUT_DIR", "CHARGERS_CANONICAL_CSV", "CHARGERS_DAILY_CSV", "CHARGERS_STATS_CSV",
    "MALL_DEMAND_DIR", "MALL_DEMAND_CANONICAL_CSV",
    "INTERIM_OE2_DIR", "INTERIM_SOLAR_PATHS", "INTERIM_BESS_PATH", "INTERIM_CHARGERS_PATHS",
    "CITYLEARN_OUTPUT_DIR", "CO2_EMISSIONS_CSV",
    "BESS_CAPACITY_KWH", "N_CHARGERS", "N_SOCKETS", "SOLAR_PV_KWP", "SOLAR_HOURLY_ROWS",
]
