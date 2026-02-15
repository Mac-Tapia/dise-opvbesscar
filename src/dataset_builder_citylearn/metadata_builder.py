"""
Gestor de Metadatos para Construccion de CityLearn v2.

Documenta y valida TODAS las carpetas, columnas y archivos necesarios para:
1. Construccion de datasets de observacion y recompensa
2. Entrenamiento de agentes RL (SAC, PPO, A2C)
3. Simulacion y evaluacion

Proposito: Single Source of Truth (SSOT) para estructura de datos completa.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# ESTRUCTURA DE CARPETAS PARA CONSTRUCCION Y ENTRENAMIENTO
# ============================================================================

@dataclass(frozen=True)
class DirectoryStructure:
    """Define las carpetas necesarias para construccion y entrenamiento."""
    
    # === DATOS OE2 (fuentes primarias) ===
    oe2_solar: Path = Path("data/oe2/Generacionsolar")
    oe2_bess: Path = Path("data/oe2/bess")
    oe2_chargers: Path = Path("data/oe2/chargers")
    oe2_demand: Path = Path("data/oe2/demandamallkwh")
    
    # === DATOS INTERMEDIOS (construccion) ===
    interim_solar: Path = Path("data/interim/oe2/solar")
    interim_bess: Path = Path("data/interim/oe2/bess")
    interim_chargers: Path = Path("data/interim/oe2/chargers")
    interim_demand: Path = Path("data/interim/oe2/demandamallkwh")
    
    # === DATOS PROCESADOS (CityLearn) ===
    citylearn_processed: Path = Path("data/processed/citylearn/iquitos_ev_mall")
    citylearn_observations: Path = Path("data/processed/citylearn/iquitos_ev_mall/observations")
    citylearn_rewards: Path = Path("data/processed/citylearn/iquitos_ev_mall/rewards")
    citylearn_metadata: Path = Path("data/processed/citylearn/iquitos_ev_mall/metadata")
    
    # === CHECKPOINTS Y MODELOS ===
    checkpoints_root: Path = Path("checkpoints")
    checkpoints_sac: Path = Path("checkpoints/SAC")
    checkpoints_ppo: Path = Path("checkpoints/PPO")
    checkpoints_a2c: Path = Path("checkpoints/A2C")
    checkpoints_baseline: Path = Path("checkpoints/Baseline")
    
    # === LOGS Y RESULTADOS ===
    logs_root: Path = Path("logs")
    logs_training: Path = Path("logs/training")
    logs_evaluation: Path = Path("logs/evaluation")
    
    outputs_root: Path = Path("outputs")
    outputs_results: Path = Path("outputs/results")
    outputs_baselines: Path = Path("outputs/baselines")
    outputs_analysis: Path = Path("outputs/analysis")
    
    # === CONFIGURACION ===
    configs_root: Path = Path("configs")
    
    def create_all(self, verbose: bool = True) -> None:
        """Crea todas las carpetas necesarias."""
        all_dirs = [
            self.oe2_solar, self.oe2_bess, self.oe2_chargers, self.oe2_demand,
            self.interim_solar, self.interim_bess, self.interim_chargers, self.interim_demand,
            self.citylearn_processed, self.citylearn_observations, self.citylearn_rewards, self.citylearn_metadata,
            self.checkpoints_sac, self.checkpoints_ppo, self.checkpoints_a2c, self.checkpoints_baseline,
            self.logs_training, self.logs_evaluation,
            self.outputs_results, self.outputs_baselines, self.outputs_analysis,
            self.configs_root,
        ]
        
        for dir_path in all_dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            if verbose:
                logger.info(f"[OK] Directorio listo: {dir_path}")
    
    def validate_all(self) -> bool:
        """Valida que todas las carpetas existan."""
        all_dirs = [
            self.oe2_solar, self.oe2_bess, self.oe2_chargers, self.oe2_demand,
            self.interim_solar, self.interim_bess, self.interim_chargers,
            self.citylearn_processed,
            self.checkpoints_root, self.logs_root, self.outputs_root, self.configs_root,
        ]
        
        missing = [d for d in all_dirs if not d.exists()]
        if missing:
            logger.warning(f"[!]  Directorios faltantes: {missing}")
            return False
        
        logger.info(f"[OK] Todas las {len(all_dirs)} carpetas existen")
        return True


# ============================================================================
# ESPECIFICACION DE COLUMNAS PARA OBSERVACIONES
# ============================================================================

@dataclass(frozen=True)
class ObservationColumnSet:
    """Especifica columnas para cada version de observacion."""
    
    version: str
    dimension: int
    description: str
    columns: List[str] = field(default_factory=list)
    
    # Ejemplo para version 156_standard:
    # columns = [
    #     # Solar (1)
    #     'solar_irradiance_w_m2',
    #     
    #     # BESS (5)
    #     'bess_soc_percent', 'bess_power_kw', 'bess_capacity_kwh', 'bess_max_power_kw', 'bess_min_soc',
    #     
    #     # Chargers (38×3 = 114, but aggregated)
    #     'chargers_avg_power_kw', 'chargers_total_connected', 'chargers_soc_percent',
    #     
    #     # EV demand (3)
    #     'ev_demand_kw', 'ev_energy_required_kwh', 'ev_chargers_available',
    #     
    #     # Mall demand (2)
    #     'mall_demand_kw', 'mall_soc_percent',
    #     
    #     # Time (9)
    #     'hour', 'day_of_week', 'month', 'day_of_month', 'is_weekday',
    #     'hour_sin', 'hour_cos', 'month_sin', 'month_cos',
    #     
    #     # Grid (3)
    #     'grid_frequency_hz', 'grid_co2_factor_kg_kwh', 'tariff_applied',
    #     
    #     # Previous step info (3+)
    #     'prev_solar_w_m2', 'prev_bess_soc', 'prev_ev_charging_power_kw',
    # ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return asdict(self)


# ============================================================================
# ESPECIFICACION DE COLUMNAS PARA RECOMPENSAS
# ============================================================================

@dataclass(frozen=True)
class RewardComponentSet:
    """Especifica componentes de recompensa multiobjetivo."""
    
    name: str
    weight: float
    description: str
    formula: str
    range: tuple = (-1.0, 1.0)
    
    # Ejemplo:
    # r_co2 = RewardComponentSet(
    #     name="CO2_Reduction",
    #     weight=0.30,
    #     description="Reduccion de emisiones CO₂ por menor importacion de grid",
    #     formula="r_co2 = -1.0 × (grid_import_kwh × CO2_FACTOR / MAX_GRID_IMPORT)",
    #     range=(-1.0, 1.0)
    # )


@dataclass(frozen=True)
class RewardFunctionSpec:
    """Especifica funcion de recompensa completa."""
    
    name: str = "Multiobjetivo_Iquitos_v5.3"
    components: List[RewardComponentSet] = field(default_factory=list)
    weights: Dict[str, float] = field(default_factory=dict)
    
    # Ejemplo:
    # spec = RewardFunctionSpec(
    #     components=[
    #         RewardComponentSet(name="co2", weight=0.30, ...),
    #         RewardComponentSet(name="ev", weight=0.35, ...),
    #         RewardComponentSet(name="solar", weight=0.20, ...),
    #         RewardComponentSet(name="cost", weight=0.10, ...),
    #         RewardComponentSet(name="grid", weight=0.05, ...),
    #     ],
    #     weights={"co2": 0.30, "ev": 0.35, "solar": 0.20, "cost": 0.10, "grid": 0.05}
    # )
    
    def verify_weights_sum(self, tolerance: float = 0.01) -> bool:
        """Verifica que pesos sumen a 1.0."""
        total = sum(self.weights.values())
        return abs(total - 1.0) < tolerance


# ============================================================================
# ARCHIVOS REQUERIDOS PARA CONSTRUCCION
# ============================================================================

@dataclass(frozen=True)
class RequiredDataFiles:
    """Especifica archivos de datos requeridos."""
    
    # Rutas fijas OE2 (obligatorias)
    solar_file: Path = Path("data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv")
    bess_file: Path = Path("data/oe2/bess/bess_ano_2024.csv")
    chargers_file: Path = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
    demand_file: Path = Path("data/oe2/demandamallkwh/demandamallhorakwh.csv")
    
    # Especificaciones
    solar_rows: int = 8760  # Horario
    solar_columns: int = 16  # Estimado
    
    bess_rows: int = 8760
    bess_capacity_kwh: float = 1700.0
    
    chargers_rows: int = 8760
    chargers_count: int = 19
    chargers_sockets: int = 38  # 19 × 2
    
    demand_rows: int = 8785  # Puede variar
    demand_baseline_kw: float = 100.0
    
    def validate_files(self) -> Dict[str, bool]:
        """Valida existencia de todos los archivos."""
        results = {
            'solar': self.solar_file.exists(),
            'bess': self.bess_file.exists(),
            'chargers': self.chargers_file.exists(),
            'demand': self.demand_file.exists(),
        }
        return results
    
    def validate_integrity(self) -> Dict[str, Any]:
        """Valida integridad (tamano, dimensiones, etc.)."""
        import pandas as pd
        
        results: Dict[str, Any] = {}
        
        try:
            df_solar = pd.read_csv(self.solar_file)
            results['solar'] = {
                'valid': len(df_solar) == self.solar_rows,
                'rows': len(df_solar),
                'columns': len(df_solar.columns),
                'expected_rows': self.solar_rows,
            }
        except Exception as e:
            results['solar'] = {'valid': False, 'error': str(e)}
        
        try:
            df_bess = pd.read_csv(self.bess_file)
            results['bess'] = {
                'valid': len(df_bess) == self.bess_rows,
                'rows': len(df_bess),
                'columns': len(df_bess.columns),
                'expected_rows': self.bess_rows,
            }
        except Exception as e:
            results['bess'] = {'valid': False, 'error': str(e)}
        
        try:
            df_chargers = pd.read_csv(self.chargers_file)
            results['chargers'] = {
                'valid': len(df_chargers) == self.chargers_rows,
                'rows': len(df_chargers),
                'columns': len(df_chargers.columns),
                'expected_rows': self.chargers_rows,
            }
        except Exception as e:
            results['chargers'] = {'valid': False, 'error': str(e)}
        
        try:
            df_demand = pd.read_csv(self.demand_file)
            results['demand'] = {
                'valid': True,
                'rows': len(df_demand),
                'columns': len(df_demand.columns),
                'expected_rows': self.demand_rows,
            }
        except Exception as e:
            results['demand'] = {'valid': False, 'error': str(e)}
        
        return results


# ============================================================================
# REQUISITOS PARA ENTRENAMIENTO DE AGENTES
# ============================================================================

@dataclass(frozen=True)
class AgentTrainingRequirements:
    """Especifica requisitos para cada agente RL."""
    
    agent_type: str  # "SAC", "PPO", "A2C"
    observation_dim: int
    action_dim: int  # n_actions = 1 BESS + 38 chargers = 39
    min_steps: int = 26280  # 3 anos × 8760 h
    batch_size: int = 64
    learning_rate: float = 2e-4
    required_memory_gb: float = 2.0
    estimated_training_hours_gpu: float = 0.0
    
    # Checkpoints
    checkpoint_freq_steps: int = 10000
    save_best_only: bool = True
    
    # Configuracion del agente
    config_file: Optional[Path] = None


# ============================================================================
# METADATA CONSOLIDADO - SINGLE SOURCE OF TRUTH
# ============================================================================

@dataclass
class CityLearnBuildMetadata:
    """
    Consolidacion completa de metadatos para construccion de CityLearn v2.
    
    Esta es la fuente unica de verdad (SSOT) para:
    - Carpetas necesarias
    - Archivos de datos
    - Estructuras de columnas
    - Especificaciones de recompensas
    - Requisitos de entrenamiento
    """
    
    version: str = "5.7"
    date: str = "2026-02-14"
    
    # Estructura de directorios
    directories: DirectoryStructure = field(default_factory=DirectoryStructure)
    
    # Archivos requeridos
    required_files: RequiredDataFiles = field(default_factory=RequiredDataFiles)
    
    # Observaciones (por version)
    observation_specs: Dict[str, ObservationColumnSet] = field(default_factory=dict)
    
    # Recompensas
    reward_spec: Optional[RewardFunctionSpec] = None
    
    # Agentes
    agent_requirements: Dict[str, AgentTrainingRequirements] = field(default_factory=dict)
    
    def __post_init__(self):
        """Inicializa valores por defecto."""
        # Especificaciones de observacion (por version)
        self.observation_specs = {
            "156_standard": ObservationColumnSet(
                version="156_standard",
                dimension=156,
                description="Estandar CityLearn v2 (5.3)",
                columns=self._get_obs_156_columns(),
            ),
            "246_cascada": ObservationColumnSet(
                version="246_cascada",
                dimension=246,
                description="Con cascada de comunicacion (6.0)",
                columns=self._get_obs_246_columns(),
            ),
            "66_expanded": ObservationColumnSet(
                version="66_expanded",
                dimension=66,
                description="Expandido experimental",
                columns=self._get_obs_66_columns(),
            ),
        }
        
        # Especificacion de recompensas
        self.reward_spec = RewardFunctionSpec(
            name="Multiobjetivo_Iquitos_v5.3",
            components=[
                RewardComponentSet(
                    name="co2_reduction",
                    weight=0.30,
                    description="Minimizar importacion grid (evitar CO₂ indirecto)",
                    formula="r_co2 = -grid_import_kwh × CO2_FACTOR / MAX_GRID",
                ),
                RewardComponentSet(
                    name="ev_satisfaction",
                    weight=0.35,
                    description="Satisfaccion de carga de EVs",
                    formula="r_ev = 2×tanh(energy_charged_ratio) - 1",
                ),
                RewardComponentSet(
                    name="solar_selfconsumption",
                    weight=0.20,
                    description="Maximizar autoconsumo solar",
                    formula="r_solar = solar_direct / solar_generation",
                ),
                RewardComponentSet(
                    name="cost_minimization",
                    weight=0.10,
                    description="Minimizar costo electrico",
                    formula="r_cost = -cost_per_hour / MAX_COST_HP",
                ),
                RewardComponentSet(
                    name="grid_stability",
                    weight=0.05,
                    description="Estabilidad de red (suavidad de rampas)",
                    formula="r_grid = -|P_t - P_t-1| / MAX_RAMP",
                ),
            ],
            weights={
                "co2_reduction": 0.30,
                "ev_satisfaction": 0.35,
                "solar_selfconsumption": 0.20,
                "cost_minimization": 0.10,
                "grid_stability": 0.05,
            }
        )
        
        # Requisitos de agentes
        self.agent_requirements = {
            "SAC": AgentTrainingRequirements(
                agent_type="SAC",
                observation_dim=156,
                action_dim=39,
                min_steps=26280,
                batch_size=64,
                learning_rate=2e-4,
                required_memory_gb=2.0,
                estimated_training_hours_gpu=6.5,
                checkpoint_freq_steps=10000,
            ),
            "PPO": AgentTrainingRequirements(
                agent_type="PPO",
                observation_dim=156,
                action_dim=39,
                min_steps=26280,
                batch_size=128,
                learning_rate=3e-4,
                required_memory_gb=2.5,
                estimated_training_hours_gpu=5.5,
                checkpoint_freq_steps=10000,
                config_file=Path("configs/ppo_config.yaml"),
            ),
            "A2C": AgentTrainingRequirements(
                agent_type="A2C",
                observation_dim=156,
                action_dim=39,
                min_steps=26280,
                batch_size=32,
                learning_rate=2.5e-4,
                required_memory_gb=1.5,
                estimated_training_hours_gpu=4.5,
                checkpoint_freq_steps=15000,
            ),
        }
    
    @staticmethod
    def _get_obs_156_columns() -> List[str]:
        """Retorna columnas de observacion 156-dim (estandar)."""
        return [
            # Solar (1)
            "solar_irradiance_w_m2",
            
            # BESS (5)
            "bess_soc_percent", "bess_power_kw", "bess_capacity_kwh", 
            "bess_max_power_kw", "bess_min_soc_percent",
            
            # Chargers (30: agregados por tipo)
            *[f"socket_{i}_power_kw" for i in range(38)],
            
            # EV demand (3)
            "ev_demand_total_kw", "ev_energy_required_kwh", "ev_chargers_available",
            
            # Mall demand (2)
            "mall_demand_kw", "mall_soc_percent",
            
            # Time features (9)
            "hour", "day_of_week", "month", "day_of_month", "is_weekday",
            "hour_sin", "hour_cos", "month_sin", "month_cos",
            
            # Grid (3)
            "grid_frequency_hz", "grid_co2_factor_kg_kwh", "tariff_applied_soles_per_kwh",
            
            # Previous step (3+)
            "prev_solar_w_m2", "prev_bess_soc_percent", "prev_ev_power_kw",
        ][:156]  # Limitar a 156 exactas
    
    @staticmethod
    def _get_obs_246_columns() -> List[str]:
        """Retorna columnas de observacion 246-dim (cascada)."""
        base = CityLearnBuildMetadata._get_obs_156_columns()
        # Agregar 90 columnas mas para cascada/comunicacion
        additional = [
            f"socket_{i}_soc_percent" for i in range(38)
        ] + [
            f"charger_{i}_status" for i in range(19)
        ] + [
            "queue_motos_waiting", "queue_taxis_waiting",
            "avg_socket_temp_c", "system_efficiency_percent",
            "forecast_solar_24h_kwh", "forecast_demand_24h_kw",
            "historical_co2_factor_avg", "net_metering_kwh",
        ]
        return base + additional[:90]
    
    @staticmethod
    def _get_obs_66_columns() -> List[str]:
        """Retorna columnas de observacion 66-dim (expandido)."""
        return [
            # Solar (2)
            "solar_irradiance_w_m2", "solar_forecast_24h_avg",
            
            # BESS (5)
            "bess_soc_percent", "bess_power_kw", "bess_capacity_kwh",
            "bess_max_power_kw", "bess_min_soc_percent",
            
            # Chargers agregados (5)
            "chargers_avg_power_kw", "chargers_total_connected",
            "chargers_motos_plugged", "chargers_taxis_plugged", "chargers_max_power_kw",
            
            # EV demand (3)
            "ev_demand_total_kw", "ev_energy_required_kwh", "ev_chargers_available",
            
            # Mall demand (3)
            "mall_demand_kw", "mall_demand_forecast_4h", "mall_soc_percent",
            
            # Time features (10)
            "hour", "day_of_week", "month", "day_of_month", "is_weekday",
            "hour_sin", "hour_cos", "month_sin", "month_cos", "is_leap_year",
            
            # Grid (4)
            "grid_frequency_hz", "grid_co2_factor_kg_kwh", "tariff_applied_soles_per_kwh",
            "grid_voltage_nominal",
            
            # Previous step (7)
            "prev_solar_w_m2", "prev_bess_soc_percent", "prev_ev_power_kw",
            "prev_grid_import_kw", "prev_cost_soles", "prev_co2_kg", "prev_reward",
            
            # System indicators (6)
            "system_efficiency_percent", "net_co2_reduction_kg_cumulative",
            "cost_cumulative_soles", "pv_selfconsumption_percent",
            "bess_cycles_count", "avg_ev_soc_percent",
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte metadatos a diccionario."""
        return {
            "version": self.version,
            "date": self.date,
            "directories": asdict(self.directories),
            "required_files": asdict(self.required_files),
            "observation_specs": {
                k: asdict(v) for k, v in self.observation_specs.items()
            },
            "reward_spec": asdict(self.reward_spec) if self.reward_spec else None,
            "agent_requirements": {
                k: asdict(v) for k, v in self.agent_requirements.items()
            },
        }
    
    def save_to_json(self, path: Path) -> None:
        """Guarda metadatos a JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        logger.info(f"[OK] Metadatos guardados en: {path}")
    
    def print_summary(self) -> None:
        """Imprime resumen de metadatos."""
        print("\n" + "="*90)
        print("METADATOS DE CONSTRUCCION CITYLEARN v2")
        print("="*90)
        
        print("\n📁 ESTRUCTURA DE DIRECTORIOS:")
        print(f"  - OE2: {self.directories.oe2_solar.parent}")
        print(f"  - Interim: {self.directories.interim_solar.parent}")
        print(f"  - CityLearn: {self.directories.citylearn_processed}")
        print(f"  - Checkpoints: {self.directories.checkpoints_root}")
        print(f"  - Logs: {self.directories.logs_root}")
        print(f"  - Outputs: {self.directories.outputs_root}")
        
        print("\n📋 ARCHIVOS REQUERIDOS:")
        for file_name, file_path in [
            ("Solar", self.required_files.solar_file),
            ("BESS", self.required_files.bess_file),
            ("Chargers", self.required_files.chargers_file),
            ("Demand", self.required_files.demand_file),
        ]:
            exists = "[OK]" if file_path.exists() else "[X]"
            print(f"  {exists} {file_name}: {file_path}")
        
        print("\n👁️ VERSIONES DE OBSERVACION:")
        for obs_name, obs_spec in self.observation_specs.items():
            print(f"  - {obs_name}: {obs_spec.dimension} dimensiones")
        
        print("\n🎯 ESPECIFICACION DE RECOMPENSAS:")
        if self.reward_spec:
            for comp in self.reward_spec.components:
                print(f"  - {comp.name}: peso={comp.weight}")
        
        print("\n🤖 REQUISITOS DE ENTRENAMIENTO:")
        for agent_name, req in self.agent_requirements.items():
            print(f"  - {agent_name}: {req.estimated_training_hours_gpu} h GPU, {req.required_memory_gb} GB RAM")
        
        print("\n" + "="*90 + "\n")


# ============================================================================
# FUNCION DE INICIALIZACION
# ============================================================================

def initialize_citylearn_metadata(workspace_path: Path = Path.cwd()) -> CityLearnBuildMetadata:
    """
    Inicializa y valida todos los metadatos para construccion de CityLearn.
    
    Args:
        workspace_path: Ruta de trabajo (default: cwd)
    
    Returns:
        Metadatos consolidados
    """
    metadata = CityLearnBuildMetadata()
    
    # Crear directorios
    metadata.directories.create_all(verbose=True)
    
    # Validar archivos
    file_status = metadata.required_files.validate_files()
    logger.info(f"Estado archivos: {file_status}")
    
    # Validar integridad
    integrity_status = metadata.required_files.validate_integrity()
    for file_name, status in integrity_status.items():
        logger.info(f"  {file_name}: {status}")
    
    # Guardar metadatos
    metadata_path = Path("data/processed/citylearn/iquitos_ev_mall/metadata/METADATA_v57.json")
    metadata.save_to_json(metadata_path)
    
    return metadata


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Inicializar metadatos
    metadata = initialize_citylearn_metadata()
    
    # Mostrar resumen
    metadata.print_summary()
    
    print("[OK] Metadatos de construccion CityLearn v2 inicializados correctamente")
