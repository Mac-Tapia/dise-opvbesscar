# 🔧 IMPLEMENTACIÓN: FIX #1 - Conectar SAC ↔ Config YAML
# src/iquitos_citylearn/oe3/agents/sac.py - NUEVAS FUNCIONES

from typing import Dict, Any
from pathlib import Path

def load_config(config_path: Path | None = None) -> Dict[str, Any]:
    """Carga configuración desde YAML (delegado a config.py)."""
    from iquitos_citylearn.config import load_config as _load_config
    return _load_config(config_path)


def _extract_sac_config_from_yaml(cfg_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Extrae configuración SAC desde dict cargado de YAML.

    IMPORTANTE: Este diccionario se pasa a SACConfig(**dict)
    para inicializar el dataclass con valores de YAML en lugar de hardcoded defaults.

    Prioridades:
    1. oe3.sac.* (configuración específica de SAC)
    2. oe3.reward.* (configuración de recompensas multiobjetivo)
    3. oe3.grid.* (factores de CO₂)
    4. oe2.ev_fleet.* (configuración de demanda EV)
    5. oe2.bess.* (configuración de batería)
    """
    oe3_cfg = cfg_dict.get("oe3", {})
    oe2_cfg = cfg_dict.get("oe2", {})

    sac_section = oe3_cfg.get("sac", {})
    reward_section = oe3_cfg.get("reward", {})
    grid_section = oe3_cfg.get("grid", {})
    ev_fleet_section = oe2_cfg.get("ev_fleet", {})
    bess_section = oe2_cfg.get("bess", {})

    # ✅ CONSTRUCCIÓN DE DICCIONARIO: Todos los parámetros mapeados desde YAML
    extracted = {
        # === SAC Hiperparámetros ===
        "episodes": sac_section.get("episodes", 50),
        "batch_size": sac_section.get("batch_size", 256),
        "buffer_size": sac_section.get("buffer_size", 100000),
        "learning_rate": sac_section.get("learning_rate", 5e-5),
        "gamma": sac_section.get("gamma", 0.99),
        "tau": sac_section.get("tau", 0.01),
        "ent_coef": sac_section.get("ent_coef", "auto"),
        "ent_coef_init": sac_section.get("ent_coef_init", 0.1),
        "ent_coef_lr": sac_section.get("ent_coef_lr", 1e-5),

        # === Red Neuronal ===
        "hidden_sizes": tuple(sac_section.get("hidden_sizes", [256, 256])),
        "activation": sac_section.get("activation", "relu"),

        # === GPU/CUDA ===
        "device": sac_section.get("device", "auto"),
        "use_amp": sac_section.get("use_amp", True),
        "pin_memory": sac_section.get("pin_memory", True),

        # === Estabilidad Numérica ===
        "clip_gradients": sac_section.get("clip_gradients", True),
        "max_grad_norm": sac_section.get("max_grad_norm", 0.5),
        "warmup_steps": sac_section.get("warmup_steps", 5000),
        "gradient_accumulation_steps": sac_section.get("gradient_accumulation_steps", 1),

        # === Multiobjetivo Pesos (CRÍTICO) ===
        "weight_co2": reward_section.get("weight_co2", 0.50),
        "weight_cost": reward_section.get("weight_cost", 0.15),
        "weight_solar": reward_section.get("weight_solar", 0.20),
        "weight_ev_satisfaction": reward_section.get("weight_ev_satisfaction", 0.10),
        "weight_grid_stability": reward_section.get("weight_grid_stability", 0.05),

        # === CO₂ y Grid Factores (CRÍTICO) ===
        "co2_target_kg_per_kwh": grid_section.get("carbon_intensity_kg_per_kwh", 0.4521),
        "co2_conversion_factor": grid_section.get("ev_co2_conversion_kg_per_kwh", 2.146),
        "cost_target_usd_per_kwh": grid_section.get("tariff_usd_per_kwh", 0.20),

        # === EV Fleet (CRÍTICO) ===
        "ev_demand_constant_kw": ev_fleet_section.get("ev_demand_constant_kw", 50.0),
        "ev_soc_target": ev_fleet_section.get("ev_soc_target", 0.90),

        # === BESS / Límites Operacionales ===
        "peak_demand_limit_kw": sac_section.get("peak_demand_limit_kw", 200.0),

        # === Logging y Checkpoints ===
        "verbose": sac_section.get("verbose", 0),
        "log_interval": sac_section.get("log_interval", 500),
        "checkpoint_freq_steps": sac_section.get("checkpoint_freq_steps", 1000),
        "save_final": sac_section.get("save_final", True),
        "progress_interval_episodes": sac_section.get("progress_interval_episodes", 1),

        # === Reproducibilidad ===
        "seed": sac_section.get("seed", 42),
        "deterministic_cuda": sac_section.get("deterministic_cuda", False),

        # === Normalización ===
        "normalize_observations": sac_section.get("normalize_observations", True),
        "normalize_rewards": sac_section.get("normalize_rewards", True),
        "reward_scale": sac_section.get("reward_scale", 0.5),
        "clip_obs": sac_section.get("clip_obs", 5.0),
    }

    logger.info("[SAC Config] Extracted %d parameters from YAML", len(extracted))
    return extracted


def make_sac_with_yaml_config(
    env: Any,
    config_path: Path | None = None,
    config: Optional[SACConfig] = None,
    **kwargs
) -> SACAgent:
    """Factory mejorada que CARGA configuración desde YAML.

    PRIORIDADES:
    1. config explícito → usa tal cual
    2. config.yaml en config_path → carga YAML
    3. kwargs → crea SACConfig(kwargs)
    4. defaults → SACConfig()

    Args:
        env: Gymnasium environment
        config_path: Ruta a config.yaml (e.g., Path("configs/default.yaml"))
        config: SACConfig explícito (si no es None, ignora YAML)
        **kwargs: Parámetros adicionales

    Returns:
        SACAgent listo para entrenar
    """

    # ✅ PRIORIDAD 1: Config explícito
    if config is not None:
        logger.info("[make_sac] PRIORIDAD 1: Usando config explícito (parámetro)")
        return SACAgent(env, config)

    # ✅ PRIORIDAD 2: Cargar YAML
    if config_path is None:
        config_path = Path("configs/default.yaml")

    if config_path.exists():
        logger.info("[make_sac] PRIORIDAD 2: Cargando config desde YAML: %s", config_path)
        try:
            yaml_dict = load_config(config_path)
            extracted_params = _extract_sac_config_from_yaml(yaml_dict)

            # Mergear kwargs sobre YAML (kwargs tiene prioridad)
            extracted_params.update(kwargs)

            cfg = SACConfig(**extracted_params)
            logger.info("[make_sac] ✅ SACConfig creado desde YAML con %d parámetros", len(extracted_params))
            return SACAgent(env, cfg)
        except Exception as e:
            logger.warning("[make_sac] Error cargando YAML (%s), usando kwargs/defaults: %s", config_path, e)

    # ✅ PRIORIDAD 3: Kwargs
    if kwargs:
        logger.info("[make_sac] PRIORIDAD 3: Creando SACConfig desde kwargs (%d parámetros)", len(kwargs))
        cfg = SACConfig(**kwargs)
        return SACAgent(env, cfg)

    # ✅ PRIORIDAD 4: Defaults
    logger.info("[make_sac] PRIORIDAD 4: Usando SACConfig defaults")
    return SACAgent(env, SACConfig())


# ✅ ALIAS para compatibilidad con código existente
# Ahora make_sac() carga YAML automáticamente si config=None
def make_sac(
    env: Any,
    config: Optional[SACConfig] = None,
    **kwargs
) -> SACAgent:
    """Wrapper que automatiza carga de YAML.

    CAMBIO: Si config=None y no hay kwargs explícitos, intenta cargar
    de YAML antes de usar defaults.
    """
    return make_sac_with_yaml_config(env, config_path=None, config=config, **kwargs)
