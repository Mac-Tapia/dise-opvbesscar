#!/usr/bin/env python3
"""Script dedicado para entrenar agentes RL (SAC, PPO, A2C) sin evaluar.

Este script permite:
- Entrenar agentes por separado antes de la evaluación
- Guardar modelos entrenados para uso posterior
- Experimentar con diferentes hiperparámetros
- Visualizar progreso de entrenamiento

Uso:
    python -m scripts.run_oe3_train_agents --config configs/default.yaml --agents SAC PPO A2C
    python -m scripts.run_oe3_train_agents --config configs/default.yaml --agents SAC --episodes 20
"""

from __future__ import annotations

import argparse
from pathlib import Path
import json
import logging

from iquitos_citylearn.utils.logging import setup_logging
from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
from iquitos_citylearn.oe3.agents import (
    make_sac,
    make_ppo,
    make_a2c,
    SACConfig,
    PPOConfig,
    A2CConfig,
)
from scripts._common import load_all

logger = logging.getLogger(__name__)


def _make_env(schema_path: Path):
    """Crea el ambiente CityLearn desde el schema."""
    from citylearn.citylearn import CityLearnEnv  # type: ignore
    try:
        return CityLearnEnv(schema=str(schema_path))
    except TypeError:
        return CityLearnEnv(schema_path=str(schema_path))


def train_sac(
    env,
    config: SACConfig,
    checkpoint_dir: Path,
    progress_dir: Path,
) -> None:
    """Entrena agente SAC y guarda el modelo."""
    logger.info("=" * 60)
    logger.info("ENTRENANDO AGENTE SAC")
    logger.info("=" * 60)
    logger.info(f"Episodios: {config.episodes}")
    logger.info(f"Dispositivo: {config.device}")
    logger.info(f"Batch size: {config.batch_size}")
    logger.info(f"Learning rate: {config.learning_rate}")
    logger.info("=" * 60)
    
    agent = make_sac(env, config=config)
    
    # Mostrar información del dispositivo
    device_info = agent.get_device_info()
    logger.info(f"Device info: {json.dumps(device_info, indent=2)}")
    
    # Entrenar
    agent.learn(episodes=config.episodes)
    
    # Guardar modelo final
    if config.checkpoint_dir:
        final_path = Path(config.checkpoint_dir) / "sac_final"
        agent.save(str(final_path))
        logger.info(f"✓ Modelo SAC guardado en: {final_path}")
    
    logger.info("✓ Entrenamiento SAC completado\n")


def train_ppo(
    env,
    config: PPOConfig,
    checkpoint_dir: Path,
    progress_dir: Path,
) -> None:
    """Entrena agente PPO y guarda el modelo."""
    logger.info("=" * 60)
    logger.info("ENTRENANDO AGENTE PPO")
    logger.info("=" * 60)
    logger.info(f"Timesteps: {config.train_steps}")
    logger.info(f"Dispositivo: {config.device}")
    logger.info(f"Batch size: {config.batch_size}")
    logger.info(f"Learning rate: {config.learning_rate}")
    logger.info(f"N steps: {config.n_steps}")
    logger.info("=" * 60)
    
    agent = make_ppo(env, config=config)
    
    # Mostrar información del dispositivo
    device_info = agent.get_device_info()
    logger.info(f"Device info: {json.dumps(device_info, indent=2)}")
    
    # Entrenar
    agent.learn(total_timesteps=config.train_steps)
    
    # Guardar modelo final
    if config.checkpoint_dir:
        final_path = Path(config.checkpoint_dir) / "ppo_final"
        agent.save(str(final_path))
        logger.info(f"✓ Modelo PPO guardado en: {final_path}")
    
    logger.info("✓ Entrenamiento PPO completado\n")


def train_a2c(
    env,
    config: A2CConfig,
    checkpoint_dir: Path,
    progress_dir: Path,
) -> None:
    """Entrena agente A2C y guarda el modelo."""
    logger.info("=" * 60)
    logger.info("ENTRENANDO AGENTE A2C")
    logger.info("=" * 60)
    logger.info(f"Timesteps: {config.train_steps}")
    logger.info(f"Dispositivo: {config.device}")
    logger.info(f"N steps: {config.n_steps}")
    logger.info(f"Learning rate: {config.learning_rate}")
    logger.info(f"Entropy coef: {config.ent_coef}")
    logger.info("=" * 60)
    
    agent = make_a2c(env, config=config)
    
    # Entrenar
    agent.learn(total_timesteps=config.train_steps)
    
    # Guardar modelo final
    if config.checkpoint_dir:
        final_path = Path(config.checkpoint_dir) / "a2c_final"
        agent.save(str(final_path))
        logger.info(f"✓ Modelo A2C guardado en: {final_path}")
    
    logger.info("✓ Entrenamiento A2C completado\n")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Entrena agentes RL para control de carga EV con PV+BESS"
    )
    ap.add_argument("--config", default="configs/default.yaml", help="Config file path")
    ap.add_argument(
        "--agents",
        nargs="+",
        default=["SAC", "PPO", "A2C"],
        help="Agents to train (SAC, PPO, A2C)",
    )
    ap.add_argument(
        "--episodes",
        type=int,
        help="Override episodes for training (applies to SAC and episode-based agents)",
    )
    ap.add_argument(
        "--timesteps",
        type=int,
        help="Override timesteps for training (applies to PPO and A2C)",
    )
    ap.add_argument(
        "--device",
        help="Device to use (cuda, cuda:0, cuda:1, mps, cpu, auto)",
    )
    args = ap.parse_args()

    setup_logging()
    cfg, rp = load_all(args.config)

    # Build dataset
    logger.info("Construyendo dataset CityLearn...")
    built = build_citylearn_dataset(
        cfg=cfg,
        raw_dir=rp.raw_dir,
        interim_dir=rp.interim_dir,
        processed_dir=rp.processed_dir,
    )

    dataset_dir = built.dataset_dir
    schema_pv = dataset_dir / "schema_pv_bess.json"
    
    if not schema_pv.exists():
        raise FileNotFoundError(f"Schema no encontrado: {schema_pv}")

    # Setup directories
    training_dir = rp.analyses_dir / "oe3" / "training"
    training_dir.mkdir(parents=True, exist_ok=True)
    progress_dir = training_dir / "progress"
    progress_dir.mkdir(parents=True, exist_ok=True)

    # Get config
    project_seed = int(cfg["project"].get("seed", 42))
    eval_cfg = cfg["oe3"]["evaluation"]
    sac_cfg = eval_cfg.get("sac", {})
    ppo_cfg = eval_cfg.get("ppo", {})
    a2c_cfg = eval_cfg.get("a2c", {})

    # Override from CLI args
    device = args.device or "auto"
    
    # SAC config
    sac_episodes = args.episodes or int(sac_cfg.get("episodes", 5))
    sac_device = device if args.device else sac_cfg.get("device", "auto")
    sac_checkpoint_freq = int(sac_cfg.get("checkpoint_freq_steps", 8760))
    sac_prefer_citylearn = bool(sac_cfg.get("prefer_citylearn", False))
    
    # PPO config
    ppo_episodes = ppo_cfg.get("episodes")
    if args.timesteps:
        ppo_timesteps = args.timesteps
    elif ppo_episodes is not None:
        ppo_timesteps = int(ppo_episodes) * 8760
    else:
        ppo_timesteps = int(ppo_cfg.get("timesteps", 17520))
    ppo_device = device if args.device else ppo_cfg.get("device", "auto")
    ppo_checkpoint_freq = int(ppo_cfg.get("checkpoint_freq_steps", 8760))
    ppo_target_kl = ppo_cfg.get("target_kl", 0.015)
    ppo_kl_adaptive = bool(ppo_cfg.get("kl_adaptive", True))
    ppo_log_interval = int(ppo_cfg.get("log_interval", 1000))
    
    # A2C config
    a2c_episodes = a2c_cfg.get("episodes")
    if args.timesteps:
        a2c_timesteps = args.timesteps
    elif a2c_episodes is not None:
        a2c_timesteps = int(a2c_episodes) * 8760
    else:
        a2c_timesteps = int(a2c_cfg.get("timesteps", 17520))
    a2c_device = device if args.device else a2c_cfg.get("device", "auto")
    a2c_checkpoint_freq = int(a2c_cfg.get("checkpoint_freq_steps", 8760))
    a2c_n_steps = int(a2c_cfg.get("n_steps", 256))
    a2c_learning_rate = float(a2c_cfg.get("learning_rate", 3e-4))
    a2c_entropy_coef = float(a2c_cfg.get("entropy_coef", 0.01))

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("CONFIGURACIÓN DE ENTRENAMIENTO")
    logger.info("=" * 60)
    logger.info(f"Schema: {schema_pv}")
    logger.info(f"Training dir: {training_dir}")
    logger.info(f"Agentes a entrenar: {', '.join(args.agents)}")
    logger.info(f"Seed: {project_seed}")
    logger.info("=" * 60 + "\n")

    # Train each agent
    trained_models = {}
    
    for agent_name in args.agents:
        agent_lower = agent_name.lower()
        
        # Create fresh environment for each agent
        env = _make_env(schema_pv)
        
        if agent_lower == "sac":
            sac_progress_path = progress_dir / "sac_progress.csv"
            if sac_progress_path.exists():
                sac_progress_path.unlink()
            
            sac_checkpoint_dir = training_dir / "checkpoints" / "sac"
            sac_checkpoint_dir.mkdir(parents=True, exist_ok=True)
            
            config = SACConfig(
                episodes=sac_episodes,
                batch_size=256,
                learning_rate=3e-4,
                gamma=0.99,
                tau=0.005,
                hidden_sizes=(256, 256),
                device=sac_device,
                checkpoint_dir=str(sac_checkpoint_dir),
                checkpoint_freq_steps=sac_checkpoint_freq,
                progress_path=str(sac_progress_path),
                prefer_citylearn=sac_prefer_citylearn,
                seed=project_seed,
                save_final=True,
            )
            
            train_sac(env, config, sac_checkpoint_dir, progress_dir)
            trained_models["SAC"] = str(sac_checkpoint_dir / "sac_final.zip")
            
        elif agent_lower == "ppo":
            ppo_progress_path = progress_dir / "ppo_progress.csv"
            if ppo_progress_path.exists():
                ppo_progress_path.unlink()
            
            ppo_checkpoint_dir = training_dir / "checkpoints" / "ppo"
            ppo_checkpoint_dir.mkdir(parents=True, exist_ok=True)
            
            config = PPOConfig(
                train_steps=ppo_timesteps,
                n_steps=2048,
                batch_size=64,
                n_epochs=10,
                learning_rate=3e-4,
                lr_schedule="linear",
                gamma=0.99,
                gae_lambda=0.95,
                clip_range=0.2,
                ent_coef=0.01,
                hidden_sizes=(256, 256),
                device=ppo_device,
                checkpoint_dir=str(ppo_checkpoint_dir),
                checkpoint_freq_steps=ppo_checkpoint_freq,
                progress_path=str(ppo_progress_path),
                target_kl=ppo_target_kl,
                kl_adaptive=ppo_kl_adaptive,
                log_interval=ppo_log_interval,
                seed=project_seed,
                save_final=True,
            )
            
            train_ppo(env, config, ppo_checkpoint_dir, progress_dir)
            trained_models["PPO"] = str(ppo_checkpoint_dir / "ppo_final.zip")
            
        elif agent_lower == "a2c":
            a2c_progress_path = progress_dir / "a2c_progress.csv"
            if a2c_progress_path.exists():
                a2c_progress_path.unlink()
            
            a2c_checkpoint_dir = training_dir / "checkpoints" / "a2c"
            a2c_checkpoint_dir.mkdir(parents=True, exist_ok=True)
            
            config = A2CConfig(
                train_steps=a2c_timesteps,
                n_steps=a2c_n_steps,
                learning_rate=a2c_learning_rate,
                gamma=0.99,
                gae_lambda=1.0,
                ent_coef=a2c_entropy_coef,
                hidden_sizes=(256, 256),
                device=a2c_device,
                checkpoint_dir=str(a2c_checkpoint_dir),
                checkpoint_freq_steps=a2c_checkpoint_freq,
                progress_path=str(a2c_progress_path),
                seed=project_seed,
                save_final=True,
            )
            
            train_a2c(env, config, a2c_checkpoint_dir, progress_dir)
            trained_models["A2C"] = str(a2c_checkpoint_dir / "a2c_final.zip")
            
        else:
            logger.warning(f"Agente desconocido: {agent_name}. Opciones válidas: SAC, PPO, A2C")

    # Save summary
    summary = {
        "schema": str(schema_pv),
        "training_dir": str(training_dir),
        "seed": project_seed,
        "trained_agents": list(trained_models.keys()),
        "models": trained_models,
        "config": {
            "sac": {
                "episodes": sac_episodes,
                "device": sac_device,
                "checkpoint_freq": sac_checkpoint_freq,
            },
            "ppo": {
                "timesteps": ppo_timesteps,
                "device": ppo_device,
                "checkpoint_freq": ppo_checkpoint_freq,
            },
            "a2c": {
                "timesteps": a2c_timesteps,
                "device": a2c_device,
                "checkpoint_freq": a2c_checkpoint_freq,
            },
        },
    }
    
    summary_path = training_dir / "training_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    
    logger.info("\n" + "=" * 60)
    logger.info("RESUMEN DE ENTRENAMIENTO")
    logger.info("=" * 60)
    logger.info(f"Agentes entrenados: {', '.join(trained_models.keys())}")
    logger.info(f"Modelos guardados en: {training_dir / 'checkpoints'}")
    logger.info(f"Progreso guardado en: {progress_dir}")
    logger.info(f"Resumen: {summary_path}")
    logger.info("=" * 60)
    logger.info("✓ Entrenamiento completado exitosamente")


if __name__ == "__main__":
    main()
