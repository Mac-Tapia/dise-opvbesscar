"""Ejemplo de integración de baselines en entrenamientos de agentes (OE2 v5.4).

Este archivo muestra how to integrate baseline calculations and comparisons
en los entrenamientos de SAC, PPO y A2C usando datos OE2 v5.4 validados.

Pasos:
1. setup_agent_training_with_baselines() inicia tracking de baselines
2. Agent trains normally with CityLearn environment
3. register_training_results() registra métricas finales
4. compare_and_report() compara contra baselines y genera reporte
"""

from __future__ import annotations

import logging
from typing import Any, Dict
from pathlib import Path

# Import baseline integration
from src.baseline.agent_baseline_integration import setup_agent_training_with_baselines
from src.baseline.citylearn_baseline_integration import BaselineCityLearnIntegration

logger = logging.getLogger(__name__)


class AgentTrainerWithBaseline:
    """Wrapper para entrenar agentes con tracking de baselines."""
    
    def __init__(
        self,
        agent_name: str,
        agent_class: Any,  # e.g., SAC, PPO, A2C
        env: Any,  # CityLearn environment
        training_config: Dict[str, Any],
        output_dir: str = 'outputs/agent_training',
    ):
        """Initialize trainer with baseline integration.
        
        Args:
            agent_name: Name of agent ('SAC', 'PPO', 'A2C')
            agent_class: Agent class to train
            env: CityLearn environment
            training_config: Training configuration
            output_dir: Output directory
        """
        self.agent_name = agent_name
        self.agent_class = agent_class
        self.env = env
        self.training_config = training_config
        self.output_dir = Path(output_dir)
        
        # Setup baseline integration
        self.baseline_integration = setup_agent_training_with_baselines(
            agent_name=agent_name,
            output_dir=str(self.output_dir / agent_name.lower()),
            baseline_dir=str(self.output_dir / 'baselines')
        )
        
        # Register training config in baseline tracker
        self.baseline_integration.log_training_config(training_config)
        
        self.agent = None
    
    def train(self, total_timesteps: int, **kwargs) -> Any:
        """Train the agent.
        
        Args:
            total_timesteps: Total timesteps for training
            **kwargs: Additional arguments for agent.learn()
        
        Returns:
            Trained agent
        """
        logger.info(f"[{self.agent_name}] Starting training ({total_timesteps} timesteps)...")
        
        # Create agent
        self.agent = self.agent_class(
            policy='MlpPolicy',
            env=self.env,
            **self.training_config
        )
        
        # Train
        self.agent.learn(
            total_timesteps=total_timesteps,
            **kwargs
        )
        
        logger.info(f"[{self.agent_name}] Training completed")
        return self.agent
    
    def evaluate_on_env(self) -> Dict[str, float]:
        """Evaluate agent on environment and extract CO2/grid metrics.
        
        Returns:
            Dict with 'co2_kg', 'grid_import_kwh', 'solar_generation_kwh'
        """
        if self.agent is None:
            raise ValueError(f"[{self.agent_name}] Agent not trained yet")
        
        logger.info(f"[{self.agent_name}] Evaluating on environment...")
        
        obs = self.env.reset()
        done = False
        episode_co2 = 0.0
        episode_grid_import = 0.0
        episode_solar = 0.0
        
        while not done:
            action, _ = self.agent.predict(obs, deterministic=True)
            obs, reward, done, info = self.env.step(action)
            
            # Extract metrics from info if available
            if isinstance(info, dict):
                if 'co2_kg' in info:
                    episode_co2 += info['co2_kg']
                if 'grid_import_kwh' in info:
                    episode_grid_import += info['grid_import_kwh']
                if 'solar_generation_kwh' in info:
                    episode_solar += info['solar_generation_kwh']
        
        return {
            'co2_kg': episode_co2,
            'grid_import_kwh': episode_grid_import,
            'solar_generation_kwh': episode_solar,
        }
    
    def register_results_and_compare(self) -> Dict[str, float]:
        \"\"\"Evaluate agent, register results, and compare against baselines.
        
        Returns:
            Comparison dict from baseline_integration.compare_and_report()
        \"\"\"
        # Evaluate
        metrics = self.evaluate_on_env()
        
        # Register in baseline integration
        self.baseline_integration.register_training_results(
            co2_kg=metrics['co2_kg'],
            grid_import_kwh=metrics['grid_import_kwh'],
            solar_generation_kwh=metrics['solar_generation_kwh'],
            additional_metrics={
                'training_timesteps': self.training_config.get('total_timesteps', 'unknown'),
                'learning_rate': self.training_config.get('learning_rate', 'default'),
            }
        )
        
        # Compare against baselines
        comparison = self.baseline_integration.compare_and_report()
        
        # Save logs
        self.baseline_integration.save_training_log()
        
        return comparison


def example_sac_training_with_baseline():
    \"\"\"Example: Train SAC with baseline integration.\"\"\"
    from stable_baselines3 import SAC  # type: ignore
    from src.citylearnv2.dataset_builder import build_citylearn_env_from_oe2
    
    logger.info(\"\\nExampling SAC training with baseline integration...\")
    
    # Build environment from OE2 v5.4 data
    env = build_citylearn_env_from_oe2()
    
    # Training config
    training_config = {
        'learning_rate': 3e-4,
        'batch_size': 256,
        'gamma': 0.99,
        'total_timesteps': 100000,
    }
    
    # Create trainer with baseline integration
    trainer = AgentTrainerWithBaseline(
        agent_name='SAC',
        agent_class=SAC,
        env=env,
        training_config=training_config,
        output_dir='outputs/agent_training'
    )
    
    # Train
    agent = trainer.train(total_timesteps=training_config['total_timesteps'])
    
    # Evaluate and compare
    comparison = trainer.register_results_and_compare()
    
    logger.info(\"\\nTraining with baseline integration complete!\")
    
    return agent, comparison


def example_ppo_training_with_baseline():
    \"\"\"Example: Train PPO with baseline integration.\"\"\"
    from stable_baselines3 import PPO  # type: ignore
    from src.citylearnv2.dataset_builder import build_citylearn_env_from_oe2
    
    logger.info(\"\\nExample: PPO training with baseline integration...\")
    
    # Build environment
    env = build_citylearn_env_from_oe2()
    
    # Training config
    training_config = {
        'learning_rate': 1e-3,
        'n_steps': 2048,
        'batch_size': 64,
        'n_epochs': 10,
        'total_timesteps': 100000,
    }
    
    # Create trainer
    trainer = AgentTrainerWithBaseline(
        agent_name='PPO',
        agent_class=PPO,
        env=env,
        training_config=training_config,
        output_dir='outputs/agent_training'
    )
    
    # Train
    agent = trainer.train(total_timesteps=training_config['total_timesteps'])
    
    # Evaluate and compare
    comparison = trainer.register_results_and_compare()
    
    logger.info(\"\\nPPO training with baseline integration complete!\")
    
    return agent, comparison


def compute_all_baselines():
    \"\"\"Compute baselines independently (if needed before training).\"\"\"
    logger.info(\"\\nComputing all baselines independently...\")
    
    integration = BaselineCityLearnIntegration(output_dir='outputs/baselines')
    integration.compute_baselines()
    integration.print_summary()
    
    logger.info(\"✅ Baselines computed and saved\")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )
    
    # Compute baselines first
    compute_all_baselines()
    
    # Example: Train SAC
    # agent, comparison = example_sac_training_with_baseline()
    
    # Example: Train PPO
    # agent, comparison = example_ppo_training_with_baseline()
    
    print(\"\\n✅ Integration examples ready. Uncomment example_*_training_with_baseline() to run.\")
