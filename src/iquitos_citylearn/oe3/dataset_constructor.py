"""
Constructor de dataset para CityLearn sin dependencias de esquema externo.

Genera:
1. Ambiente de simulación con perfiles horarios
2. Observables enriquecidas (solar, carga EV, BESS)
3. Configuración de recompensas multi-objetivo
4. Estructura compatible con training de RL
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Any, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class DatasetConfig:
    """Configuración del dataset a construir."""
    n_timesteps: int = 8760  # 1 año
    n_chargers: int = 128  # Total de sockets (32 chargers × 4 sockets)
    n_controllable_chargers: int = 126  # 2 reservados para baseline
    observation_dim: int = 394  # Solar(1) + demand(1) + BESS(1) + Mall(1) + charger_demand(128) + charger_power(128) + charger_occ(128) + time(4) + grid(2)
    action_dim: int = 126  # Continuous setpoints para cargadores
    carbon_intensity_kg_per_kwh: float = 0.4521  # Iquitos (diesel thermal)
    tariff_usd_per_kwh: float = 0.20

    # Reward weights
    reward_co2_weight: float = 0.50
    reward_solar_weight: float = 0.20
    reward_cost_weight: float = 0.10
    reward_ev_weight: float = 0.10
    reward_grid_weight: float = 0.10


@dataclass
class DatasetMetadata:
    """Metadatos del dataset construido."""
    dataset_dir: Path
    timestamp: str
    n_timesteps: int
    n_chargers_controllable: int
    observation_dim: int
    action_dim: int
    carbon_intensity: float
    tariff: float
    solar_annual_kwh: float
    charger_annual_kwh: float
    mall_annual_kwh: float
    bess_capacity_kwh: float
    bess_power_kw: float


class DatasetBuilder:
    """Construcción robusta de dataset para training."""

    def __init__(self, config: DatasetConfig = None):
        self.config = config or DatasetConfig()
        self.data = {}

    def build(
        self,
        solar_ts: pd.Series,
        charger_profiles: Dict[str, pd.Series],
        mall_ts: pd.Series,
        bess_config: Dict[str, float],
        output_dir: Path | str,
    ) -> DatasetMetadata:
        """
        Construir dataset completo.

        Args:
            solar_ts: Solar generation timeseries (8,760 horas)
            charger_profiles: Dict {charger_id -> Series 8,760}
            mall_ts: Mall demand timeseries (8,760 horas)
            bess_config: {'capacity_kwh': ..., 'power_kw': ...}
            output_dir: Directorio para guardar dataset
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"=== Construyendo Dataset ===")
        logger.info(f"Output: {output_dir}")

        # 1. Normalizar timeseries a 8,760 horas
        self._validate_timeseries(solar_ts, "Solar")
        self._validate_timeseries(mall_ts, "Mall")

        # 2. Construir matriz de chargers (8,760 × 128)
        charger_matrix = self._build_charger_matrix(charger_profiles)

        # 3. Crear observables horarias
        observations = self._create_observations(
            solar_ts, charger_matrix, mall_ts, bess_config
        )

        # 4. Crear metadata
        metadata = DatasetMetadata(
            dataset_dir=output_dir,
            timestamp=pd.Timestamp.now().isoformat(),
            n_timesteps=self.config.n_timesteps,
            n_chargers_controllable=self.config.n_controllable_chargers,
            observation_dim=self.config.observation_dim,
            action_dim=self.config.action_dim,
            carbon_intensity=self.config.carbon_intensity_kg_per_kwh,
            tariff=self.config.tariff_usd_per_kwh,
            solar_annual_kwh=float(solar_ts.sum()),
            charger_annual_kwh=float(charger_matrix.sum().sum()),
            mall_annual_kwh=float(mall_ts.sum()),
            bess_capacity_kwh=bess_config.get('capacity_kwh', 2000),
            bess_power_kw=bess_config.get('power_kw', 1200),
        )

        # 5. Guardar datos
        self._save_dataset(
            output_dir,
            solar_ts,
            charger_matrix,
            mall_ts,
            observations,
            metadata
        )

        logger.info(f"✓ Dataset construido exitosamente")
        logger.info(f"  - Solar annual: {metadata.solar_annual_kwh:.0f} kWh")
        logger.info(f"  - Charger annual: {metadata.charger_annual_kwh:.0f} kWh")
        logger.info(f"  - Mall annual: {metadata.mall_annual_kwh:.0f} kWh")
        logger.info(f"  - Observations shape: {observations.shape}")

        return metadata

    def _validate_timeseries(self, ts: pd.Series, name: str):
        """Validar timeseries."""
        if len(ts) != 8760:
            raise ValueError(f"{name} timeseries length {len(ts)} != 8760")
        if ts.min() < 0:
            raise ValueError(f"{name} has negative values: min={ts.min()}")
        logger.info(f"✓ {name} validado: {ts.sum():.0f} kWh/año")

    def _build_charger_matrix(self, profiles: Dict[str, pd.Series]) -> pd.DataFrame:
        """Construir matriz (8,760 × 128) de cargadores."""
        logger.info(f"Construyendo matriz de cargadores: {len(profiles)} perfiles")

        # Si tenemos 32 perfiles individuales, expandir a 128 (4 sockets cada uno)
        if len(profiles) == 32:
            expanded_profiles = {}
            for charger_id, profile in profiles.items():
                if len(profile) != 8760:
                    # Ajustar longitud
                    if len(profile) < 8760:
                        profile = pd.Series(
                            np.pad(profile.values, (0, 8760-len(profile)), mode='edge'),
                            index=pd.date_range('2024-01-01', periods=8760, freq='h')
                        )
                    else:
                        profile = profile.iloc[:8760]

                # Cada charger físico = 4 sockets (diferenciar por distribución)
                base_power = profile.values / 4  # Dividir entre sockets
                for socket in range(4):
                    socket_id = f"{charger_id}_socket{socket}"
                    # Pequeña variación entre sockets (±5%)
                    variation = 1.0 + np.random.normal(0, 0.05)
                    expanded_profiles[socket_id] = base_power * variation

            matrix = pd.DataFrame(expanded_profiles)[:8760]
        else:
            # Ya tenemos 128 perfiles
            matrix_data = {}
            for i, (charger_id, profile) in enumerate(profiles.items()):
                if len(profile) != 8760:
                    if len(profile) < 8760:
                        profile = pd.Series(
                            np.pad(profile.values, (0, 8760-len(profile)), mode='edge'),
                            index=pd.date_range('2024-01-01', periods=8760, freq='h')
                        )
                    else:
                        profile = profile.iloc[:8760]

                matrix_data[f"charger_{i:03d}"] = profile.values

            matrix = pd.DataFrame(matrix_data)[:8760]

        # Asegurar exactamente 128 columnas
        while len(matrix.columns) < 128:
            # Duplicar últimas con variación
            last_col = matrix.iloc[:, -1].values * np.random.uniform(0.9, 1.1)
            matrix[f"charger_{len(matrix.columns):03d}"] = last_col

        matrix = matrix.iloc[:, :128]  # Mantener solo 128

        logger.info(f"✓ Matriz cargadores: {matrix.shape}")
        return matrix

    def _create_observations(
        self,
        solar: pd.Series,
        chargers: pd.DataFrame,
        mall: pd.Series,
        bess_config: Dict,
    ) -> np.ndarray:
        """Crear observables enriquecidas."""
        logger.info("Creando observables enriquecidas...")

        n_timesteps = len(solar)
        observations = np.zeros((n_timesteps, self.config.observation_dim))

        # Índices para llenar
        idx = 0

        # 1. Solar generation (1)
        observations[:, idx] = solar.values
        idx += 1

        # 2. Total demand (1)
        total_charger_demand = chargers.sum(axis=1).values
        total_demand = total_charger_demand + mall.values
        observations[:, idx] = total_demand
        idx += 1

        # 3. BESS SOC simulado (1) - comenzar en 50%
        bess_soc = np.ones(n_timesteps) * 0.5
        observations[:, idx] = bess_soc
        idx += 1

        # 4. Mall demand (1)
        observations[:, idx] = mall.values
        idx += 1

        # 5. Charger demands (128)
        charger_demands = chargers.values
        observations[:, idx:idx+128] = charger_demands
        idx += 128

        # 6. Charger powers actual (128)
        observations[:, idx:idx+128] = charger_demands  # Mismo que demand para baseline
        idx += 128

        # 7. Charger occupancy (128) - estimado como ocupado si demand > 0.1
        charger_occupancy = (charger_demands > 0.1).astype(float)
        observations[:, idx:idx+128] = charger_occupancy
        idx += 128

        # 8. Time features
        # Hour of day [0, 23]
        hours = np.tile(np.arange(24), n_timesteps // 24 + 1)[:n_timesteps]
        observations[:, idx] = hours
        idx += 1

        # Month [0, 11]
        days = np.repeat(np.arange(365), 24)[:n_timesteps]
        months = (days // 30).astype(int) % 12
        observations[:, idx] = months
        idx += 1

        # Day of week [0, 6]
        dow = (days % 7).astype(int)
        observations[:, idx] = dow
        idx += 1

        # Is peak hours [0, 1]
        is_peak = ((hours >= 18) & (hours <= 22)).astype(float)
        observations[:, idx] = is_peak
        idx += 1

        # 9. Grid state
        # Carbon intensity
        observations[:, idx] = self.config.carbon_intensity_kg_per_kwh
        idx += 1

        # Tariff
        observations[:, idx] = self.config.tariff_usd_per_kwh
        idx += 1

        # Verificar dimensión total
        assert idx == self.config.observation_dim, f"Observation dim mismatch: {idx} != {self.config.observation_dim}"

        logger.info(f"✓ Observables creadas: {observations.shape}")
        return observations

    def _save_dataset(
        self,
        output_dir: Path,
        solar: pd.Series,
        chargers: pd.DataFrame,
        mall: pd.Series,
        observations: np.ndarray,
        metadata: DatasetMetadata,
    ):
        """Guardar dataset en archivos."""
        logger.info("Guardando dataset...")

        # CSV files
        solar.to_csv(output_dir / "solar_generation_hourly.csv", header=['kW'])
        chargers.to_csv(output_dir / "chargers_demand_hourly.csv")
        mall.to_csv(output_dir / "mall_demand_hourly.csv", header=['kW'])

        # Observations
        obs_df = pd.DataFrame(observations)
        obs_df.to_csv(output_dir / "observations_raw.csv", index=False)

        # Config
        config_dict = {
            'observation_dim': self.config.observation_dim,
            'action_dim': self.config.action_dim,
            'n_chargers': self.config.n_chargers,
            'n_controllable_chargers': self.config.n_controllable_chargers,
            'n_timesteps': self.config.n_timesteps,
            'carbon_intensity_kg_per_kwh': self.config.carbon_intensity_kg_per_kwh,
            'tariff_usd_per_kwh': self.config.tariff_usd_per_kwh,
            'reward_weights': {
                'co2': self.config.reward_co2_weight,
                'solar': self.config.reward_solar_weight,
                'cost': self.config.reward_cost_weight,
                'ev': self.config.reward_ev_weight,
                'grid': self.config.reward_grid_weight,
            }
        }

        with open(output_dir / "dataset_config.json", 'w') as f:
            json.dump(config_dict, f, indent=2)

        # Metadata
        metadata_dict = asdict(metadata)
        metadata_dict['dataset_dir'] = str(metadata_dict['dataset_dir'])
        with open(output_dir / "dataset_metadata.json", 'w') as f:
            json.dump(metadata_dict, f, indent=2)

        logger.info(f"✓ Dataset guardado en {output_dir}")
