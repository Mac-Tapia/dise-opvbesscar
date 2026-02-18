"""Source code for pvbesscar project - EV Charging Optimization with BESS & Solar PV.

Proyecto pvbesscar optimiza la carga de 38 sockets EV (270 motos + 39 mototaxis/día) 
usando generación solar PV (4,050 kWp) + almacenamiento (2,000 kWh) mediante agentes 
de control inteligente (RL: SAC/PPO/A2C) para minimizar emisiones CO2 en grid aislado.

Tres fases principales:
1. OE2 (Dimensionamiento): Infraestructura solar, BESS, cargadores en src/dimensionamiento/oe2/
2. OE3 (Dataset CityLearn): Simulación 8,760 horas en src/dataset_builder_citylearn/
3. OE4 (Control RL): Agentes entrenados en src/agents/ con SAC/PPO/A2C

Ubicación: Iquitos, Perú (3.75°S, 73.27°O)
Factor CO2: 0.4521 kg CO2/kWh (grid térmico diesel aislado)
"""

from __future__ import annotations

__version__ = "5.5"
__author__ = "pvbesscar Team"
__year__ = "2026"

# Carpetas principales del proyecto
__all__ = [
    # OE2: Dimensionamiento
    "dimensionamiento",
    # OE3: Dataset y CityLearn v2
    "dataset_builder_citylearn",
    # OE4: Agentes RL
    "agents",
    # Línea base y ejecución
    "baseline",
    # Utilidades compartidas
    "utils",
    # Callbacks de entrenamiento
    "training_callbacks",
]

# Metadatos OE2 v5.5
OE2_CONFIG = {
    "version": "5.5",
    "bess": {
        "capacity_nominal_kwh": 2000,
        "capacity_usable_kwh": 1600,
        "power_kw": 400,
        "dod": 0.80,
        "soc_min": 0.20,
        "efficiency": 0.95,
        "technology": "LiFePO4",
    },
    "pv": {
        "capacity_kwp": 4050,
        "location": "Iquitos, Perú",
        "latitude": -3.75,
        "longitude": -73.27,
        "energy_annual_mwh": 1217.3,
    },
    "chargers": {
        "total": 19,
        "sockets": 38,
        "motos": 30,
        "mototaxis": 8,
        "power_per_socket_kw": 7.4,
        "total_power_kw": 281.2,
    },
    "demand": {
        "motos_daily": 270,
        "mototaxis_daily": 39,
        "energy_annual_kwh": 352887,
    },
}

# Metadatos OE3: CityLearn v2
CITYLEARN_CONFIG = {
    "version": 2,
    "episode_length_hours": 8760,
    "timestep_seconds": 3600,
    "observations_dimension": 394,
    "actions_dimension": 39,  # 1 BESS + 38 sockets
    "reward_function": "multiobjective",
}

# Metadatos OE4: Agentes RL
AGENTS_CONFIG = {
    "algorithms": ["SAC", "PPO", "A2C"],
    "framework": "stable-baselines3",
    "total_timesteps_default": 26280,  # ~1 year at 1-hour timesteps
    "checkpoints_dir": "checkpoints/",
    "training_device": "cuda",  # or "cpu"
}

# Factores ambientales
ENVIRONMENTAL_FACTORS = {
    "co2_grid_kg_per_kwh": 0.4521,  # Red diesel aislada Iquitos
    "tariff_hp_soles_per_kwh": 0.45,  # 18:00-22:59
    "tariff_hfp_soles_per_kwh": 0.28,  # resto
    "co2_reduction_per_kwh_moto": 0.87,  # vs gasolina
    "co2_reduction_per_kwh_mototaxi": 0.47,  # vs gasolina
}
