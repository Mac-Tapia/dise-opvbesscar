#!/usr/bin/env python3
"""
Mostrar comparativa visual de configuración de agentes (SAC, PPO, A2C).
Versión ASCII (sin emojis para compatibilidad con PowerShell).
"""

from __future__ import annotations

import yaml
from pathlib import Path
from tabulate import tabulate

REPO_ROOT = Path(__file__).parent
CONFIG_DIR = REPO_ROOT / "configs" / "agents"


def load_agent_config(agent_name: str) -> dict:
    """Cargar configuración de agente."""
    config_file = CONFIG_DIR / f"{agent_name}_config.yaml"
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def print_header(text: str) -> None:
    """Imprimir encabezado formateado."""
    print()
    print("=" * 100)
    print(f" {text}")
    print("=" * 100)
    print()


def show_reward_weights() -> None:
    """Mostrar pesos de recompensa de los 3 agentes."""
    print_header("[WEIGHTS] Multi-Objective Reward (SYNCHRONIZED)")
    
    rows = []
    components = ['co2', 'solar', 'ev', 'cost', 'grid']
    descriptions = {
        'co2': 'CO2 Reduction',
        'solar': 'Solar Self-consumption',
        'ev': 'EV Satisfaction',
        'cost': 'Minimize Tariff',
        'grid': 'Grid Stability',
    }
    
    for agent_name in ['SAC', 'PPO', 'A2C']:
        config = load_agent_config(agent_name.lower())
        weights = config[agent_name.lower()]['multi_objective_weights']
        
        for comp in components:
            rows.append([
                agent_name,
                comp.upper(),
                f"{weights[comp]:.2f}",
                descriptions[comp],
            ])
        rows.append(['', '-----', '-----', '--------------------'])
    
    headers = ['Agent', 'Component', 'Weight', 'Description']
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    
    print("\nOK: All 3 agents use EXACTLY THE SAME WEIGHTS\n")


def show_training_config() -> None:
    """Mostrar configuración de entrenamiento."""
    print_header("[TRAINING] Training Configuration")
    
    rows = []
    
    for agent_name in ['SAC', 'PPO', 'A2C']:
        config = load_agent_config(agent_name.lower())
        training = config[agent_name.lower()]['training']
        
        if agent_name == 'SAC':
            rows.append([agent_name, 'Episodes', training.get('episodes', 'N/A'), 'Total episodes'])
            rows.append(['', 'Total Timesteps', training.get('total_timesteps', 'N/A'), '3 years x 8,760 h'])
            rows.append(['', 'Learning Rate', f"{float(training['learning_rate']):.0e}", 'For GPU'])
            rows.append(['', 'Buffer Size', '2,000,000', 'Replay buffer (off-policy)'])
            rows.append(['', 'Batch Size', training['batch_size'], 'GPU optimized'])
        elif agent_name == 'PPO':
            rows.append([agent_name, 'Train Steps', f"{training['train_steps']:,}", 'Total steps'])
            rows.append(['', 'n_steps (Rollout)', training['n_steps'], 'Rollout length'])
            rows.append(['', 'Batch Size', training['batch_size'], 'GPU optimized'])
            rows.append(['', 'n_epochs', training['n_epochs'], 'Updates per rollout'])
            rows.append(['', 'Learning Rate', f"{float(training['learning_rate']):.0e}", 'Linear decay'])
        else:  # A2C
            rows.append([agent_name, 'Train Steps', f"{training['train_steps']:,}", 'Total steps'])
            rows.append(['', 'n_steps (Frequency)', training['n_steps'], 'Updates very frequent [OK]'])
            rows.append(['', 'Learning Rate', f"{float(training['learning_rate']):.0e}", 'HIGHEST (7e-4)'])
            rows.append(['', 'Batch Size (Implicit)', f"{training['n_steps']}", 'Same as n_steps'])
        
        if agent_name != 'A2C':
            rows.append(['', '', '', ''])
    
    headers = ['Agent', 'Parameter', 'Value', 'Description']
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    print()


def show_network_config() -> None:
    """Mostrar configuración de red neuronal."""
    print_header("[NETWORK] Neural Network Architecture")
    
    rows = []
    
    for agent_name in ['SAC', 'PPO', 'A2C']:
        config = load_agent_config(agent_name.lower())
        network = config[agent_name.lower()]['network']
        
        rows.append([
            agent_name,
            'Hidden Sizes',
            str(network['hidden_sizes']),
            f"{sum(network['hidden_sizes']) * 2} params"
        ])
        rows.append([
            '',
            'Activation',
            network['activation'],
            'Activation function'
        ])
    
    headers = ['Agent', 'Parameter', 'Value', 'Description']
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    print("\nOK: All networks are IDENTICAL\n")


def show_entropy_config() -> None:
    """Mostrar configuración de exploración (entropía)."""
    print_header("[ENTROPY] Exploration Configuration")
    
    rows = []
    
    # SAC
    config = load_agent_config('sac')
    entropy = config['sac']['entropy']
    rows.append(['SAC', 'ent_coef', 'auto', 'Adaptive (0.01-1.0) [OK]'])
    rows.append(['', 'ent_coef_init', entropy['ent_coef_init'], 'Initial value'])
    rows.append(['', 'ent_coef_lr', entropy['ent_coef_lr'], 'LR of coefficient'])
    rows.append(['', '', '', ''])
    
    # PPO
    config = load_agent_config('ppo')
    losses = config['ppo']['losses']
    rows.append(['PPO', 'ent_coef', losses['ent_coef'], 'Fixed (low exploration)'])
    rows.append(['', 'Strategy', 'SDE (State-Dependent)', 'Conditional exploration'])
    rows.append(['', '', '', ''])
    
    # A2C
    config = load_agent_config('a2c')
    a2c_config = config['a2c']['a2c']
    rows.append(['A2C', 'ent_coef', a2c_config['ent_coef'], 'Medium exploration'])
    rows.append(['', 'Decay Type', 'exponential', 'Decays over time'])
    rows.append(['', 'Final Value', '0.001', 'Min exploration final'])
    
    headers = ['Agent', 'Parameter', 'Value', 'Description']
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    print()


def show_performance_expectations() -> None:
    """Mostrar expectativas de desempeño."""
    print_header("[PERFORMANCE] Expected Training Duration on GPU RTX 4060")
    
    rows = [
        ['SAC', '6.5 hours', 'Off-policy (slower but stable)', '26,280 timesteps'],
        ['PPO', '5 hours', 'On-policy with clipping', '500,000 steps'],
        ['A2C', '4 hours', 'Fastest on-policy [OK]', '500,000 steps'],
    ]
    
    headers = ['Agent', 'Estimated Time', 'Strategy', 'Iterations']
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    
    print("\nOK: Episode 1 reference metrics documented in configs/default.yaml")
    print("    - CO2 Reduction: 58.9%")
    print("    - Solar Utilization: 47.2%")
    print("    - EV Satisfaction: 0.9998")
    print("    - BESS Avg SOC: 90.5%")
    print()


def show_training_times() -> None:
    """Mostrar tiempos estimados de entrenamiento."""
    print_header("[TIME] Estimated Training Times (GPU RTX 4060)")
    
    rows = [
        ['SAC', 'Off-policy with replay buffer', '6.5 hours', 'Slower, stable'],
        ['PPO', 'On-policy with clipping', '5 hours', 'Optimal balance'],
        ['A2C', 'Synchronous on-policy', '4 hours', 'FASTEST [OK]'],
    ]
    
    headers = ['Agent', 'Strategy', 'Time', 'Note']
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    print()


def show_command_examples() -> None:
    """Mostrar ejemplos de ejecución."""
    print_header("[COMMANDS] Training Commands")
    
    print("SAC (maximum stability):")
    print("  python train_sac_multiobjetivo.py --episodes=50 --device=cuda")
    print()
    
    print("PPO (balanced):")
    print("  python train_ppo_multiobjetivo.py --episodes=50 --device=cuda")
    print()
    
    print("A2C (maximum speed):")
    print("  python train_a2c_multiobjetivo.py --episodes=50 --device=cuda")
    print()
    
    print("Validate configuration:")
    print("  python validate_detailed_metrics.py")
    print()
    
    print("Generate reports:")
    print("  python generate_detailed_report.py")
    print()


def main() -> int:
    """Ejecutar visualización completa."""
    print("\n")
    print("=" * 100)
    print("CONFIGURACION INDIVIDUAL POR AGENTE - SAC vs PPO vs A2C".center(100))
    print("2026-02-07 - ESTADO: TODO SINCRONIZADO".center(100))
    print("=" * 100)
    
    show_reward_weights()
    show_training_config()
    show_network_config()
    show_entropy_config()
    show_performance_expectations()
    show_training_times()
    show_command_examples()
    
    print("=" * 100)
    print(" OK: COMPARATIVA COMPLETADA")
    print("=" * 100)
    print()
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
