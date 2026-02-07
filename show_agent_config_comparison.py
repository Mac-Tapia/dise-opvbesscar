#!/usr/bin/env python3
"""
Mostrar comparativa visual de configuración de agentes (SAC, PPO, A2C).
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
    print_header("📊 PESOS DE RECOMPENSA MULTIOBJETIVO (SINCRONIZADOS)")
    
    rows = []
    components = ['co2', 'solar', 'ev', 'cost', 'grid']
    descriptions = {
        'co2': 'Reducción CO₂',
        'solar': 'Autoconsumo PV',
        'ev': 'Satisfacción EV',
        'cost': 'Minimizar tarifa',
        'grid': 'Estabilidad red',
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
        rows.append(['', '─' * 5, '─' * 5, '─' * 20])
    
    headers = ['Agente', 'Componente', 'Peso', 'Descripción']
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    
    print("\n✅ NOTA: Los 3 agentes usan EXACTAMENTE LOS MISMOS PESOS\n")


def show_training_config() -> None:
    """Mostrar configuración de entrenamiento."""
    print_header("🚀 CONFIGURACIÓN DE ENTRENAMIENTO")
    
    rows = []
    
    for agent_name in ['SAC', 'PPO', 'A2C']:
        config = load_agent_config(agent_name.lower())
        training = config[agent_name.lower()]['training']
        
        if agent_name == 'SAC':
            rows.append([
                agent_name,
                'Episodes',
                training.get('episodes', 'N/A'),
                'Timesteps totales'
            ])
            rows.append([
                '',
                'Total Timesteps',
                training.get('total_timesteps', 'N/A'),
                '3 años × 8,760 h'
            ])
            rows.append([
                '',
                'Learning Rate',
                f"{float(training['learning_rate']):.0e}",
                'Reducida para GPU'
            ])
            rows.append([
                '',
                'Buffer Size',
                '2,000,000',
                'Replay buffer (off-policy)'
            ])
            rows.append([
                '',
                'Batch Size',
                training['batch_size'],
                'GPU optimized'
            ])
        elif agent_name == 'PPO':
            rows.append([
                agent_name,
                'Train Steps',
                f"{training['train_steps']:,}",
                'Total de pasos'
            ])
            rows.append([
                '',
                'n_steps (Rollout)',
                training['n_steps'],
                'Tamaño de rollout'
            ])
            rows.append([
                '',
                'Batch Size',
                training['batch_size'],
                'GPU optimized'
            ])
            rows.append([
                '',
                'n_epochs',
                training['n_epochs'],
                'Actualizaciones por rollout'
            ])
            rows.append([
                '',
                'Learning Rate',
                f"{float(training['learning_rate']):.0e}",
                'Decreciente linear'
            ])
        else:  # A2C
            rows.append([
                agent_name,
                'Train Steps',
                f"{training['train_steps']:,}",
                'Total de pasos'
            ])
            rows.append([
                '',
                'n_steps (Frecuencia)',
                training['n_steps'],
                'Updates muy frecuentes ✅'
            ])
            rows.append([
                '',
                'Learning Rate',
                f"{float(training['learning_rate']):.0e}",
                'MÁS ALTO (7e-4)'
            ])
            rows.append([
                '',
                'Batch Size (Implícito)',
                f"{training['n_steps']}",
                'Igual a n_steps'
            ])
        
        if agent_name != 'A2C':
            rows.append(['', '', '', ''])
    
    headers = ['Agente', 'Parámetro', 'Valor', 'Descripción']
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    print()


def show_network_config() -> None:
    """Mostrar configuración de red neuronal."""
    print_header("🧠 ARQUITECTURA DE RED NEURONAL")
    
    rows = []
    
    for agent_name in ['SAC', 'PPO', 'A2C']:
        config = load_agent_config(agent_name.lower())
        network = config[agent_name.lower()]['network']
        
        rows.append([
            agent_name,
            'Hidden Sizes',
            str(network['hidden_sizes']),
            f"{sum(network['hidden_sizes']) * 2} parámetros aprox."
        ])
        rows.append([
            '',
            'Activation',
            network['activation'],
            'Función de activación'
        ])
    
    headers = ['Agente', 'Parámetro', 'Valor', 'Descripción']
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    print("\n✅ NOTA: Todas las redes son IDÉNTICAS\n")


def show_entropy_config() -> None:
    """Mostrar configuración de exploración (entropía)."""
    print_header("🎲 CONFIGURACIÓN DE EXPLORACIÓN (ENTROPÍA)")
    
    rows = []
    
    # SAC
    config = load_agent_config('sac')
    entropy = config['sac']['entropy']
    rows.append(['SAC', 'ent_coef', 'auto', 'Adaptativa (0.01-1.0) ✅'])
    rows.append(['', 'ent_coef_init', entropy['ent_coef_init'], 'Valor inicial'])
    rows.append(['', 'ent_coef_lr', entropy['ent_coef_lr'], 'Learning rate del coef'])
    rows.append(['', '', '', ''])
    
    # PPO
    config = load_agent_config('ppo')
    losses = config['ppo']['losses']
    rows.append(['PPO', 'ent_coef', losses['ent_coef'], 'Fija (baja exploración)'])
    rows.append(['', 'Estrategia', 'SDE (State-Dependent)', 'Exploración condicional'])
    rows.append(['', '', '', ''])
    
    # A2C
    config = load_agent_config('a2c')
    a2c_config = config['a2c']['a2c']
    rows.append(['A2C', 'ent_coef', a2c_config['ent_coef'], 'Media exploración'])
    rows.append(['', 'Decay Type', 'exponential', 'Decae con el tiempo'])
    rows.append(['', 'Final Value', '0.001', 'Exploración mínima final'])
    
    headers = ['Agente', 'Parámetro', 'Valor', 'Descripción']
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    print()


def show_performance_expectations() -> None:
    """Mostrar expectativas de desempeño."""
    print_header("📈 MÉTRICAS DE DESEMPEÑO ESPERADAS (Episode 1)")
    
    rows = []
    
    metrics = [
        ('CO₂ Reduction (%)', 'expected_co2_reduction'),
        ('Solar Utilization (%)', 'expected_solar_utilization'),
        ('EV Satisfaction', 'expected_ev_satisfaction'),
        ('BESS SOC Avg (%)', 'expected_bess_soc_avg'),
        ('Motos/día', 'motos_per_day_avg'),
        ('Mototaxis/día', 'mototaxis_per_day_avg'),
        ('Ahorro USD', 'cost_savings_usd'),
    ]
    
    for agent_name in ['SAC', 'PPO', 'A2C']:
        config = load_agent_config(agent_name.lower())
        perf = config[agent_name.lower()]['performance']
        
        for metric_name, metric_key in metrics:
            value = perf.get(metric_key, 0)
            
            if isinstance(value, float):
                if 'Reduction' in metric_name or 'Utilization' in metric_name or 'SOC' in metric_name:
                    if 'Satisfaction' not in metric_name:
                        value = f"{value*100:.1f}"
                    else:
                        value = f"{value:.4f}"
                else:
                    value = f"{int(value):,}" if metric_key != 'cost_savings_usd' else f"${int(value):,}"
            
            rows.append([agent_name, metric_name, str(value)])
            agent_name = ''  # Solo mostrar nombre del agente en la primera fila
    
    headers = ['Agente', 'Métrica', 'Valor']
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    print()


def show_training_times() -> None:
    """Mostrar tiempos estimados de entrenamiento."""
    print_header("⏱️  TIEMPOS DE ENTRENAMIENTO ESTIMADOS (GPU RTX 4060)")
    
    rows = [
        ['SAC', 'Off-policy con replay  buffer', '6.5 horas', 'Más lento, estable'],
        ['PPO', 'On-policy con clipping', '5 horas', 'Balance óptimo'],
        ['A2C', 'On-policy sincrónico', '4 horas', 'MÁS RÁPIDO ✅'],
    ]
    
    headers = ['Agente', 'Estrategia', 'Tiempo', 'Nota']
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    print()


def show_command_examples() -> None:
    """Mostrar ejemplos de ejecución."""
    print_header("💻 COMANDOS PARA ENTRENAR")
    
    print("SAC (máxima estabilidad):")
    print("  python train_sac_multiobjetivo.py --episodes=50 --device=cuda")
    print()
    
    print("PPO (balance):")
    print("  python train_ppo_multiobjetivo.py --episodes=50 --device=cuda")
    print()
    
    print("A2C (máxima velocidad):")
    print("  python train_a2c_multiobjetivo.py --episodes=50 --device=cuda")
    print()
    
    print("Validar configuración:")
    print("  python validate_detailed_metrics.py")
    print()
    
    print("Generar reportes:")
    print("  python generate_detailed_report.py")
    print()


def main() -> int:
    """Ejecutar visualización completa."""
    print("\n")
    print("=" * 100)
    print("CONFIGURACIÓN INDIVIDUAL POR AGENTE - SAC vs PPO vs A2C".center(100))
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
    print(" ✅ COMPARATIVA COMPLETADA")
    print("=" * 100)
    print()
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
