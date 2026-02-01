#!/usr/bin/env python3
"""
Generador de Gráficas - Sistema OE3 RL Training
Regenera todas las gráficas desde datos de entrenamiento
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')
plt.style.use('seaborn-v0_8-darkgrid')

COLORS = {'SAC': '#FF6B6B', 'PPO': '#4ECDC4', 'A2C': '#45B7D1', 'Baseline': '#95E1D3'}
OUTPUT_DIR = Path("outputs/oe3/simulations")
TRAINING_DIR = Path("analyses/oe3/training")
GRAPHICS_DIR = TRAINING_DIR / "graphics"
GRAPHICS_DIR.mkdir(exist_ok=True, parents=True)


def plot_training_metrics():
    """Gráficas de métricas de entrenamiento por episodio"""
    print("\n📊 Generando gráficas de métricas de entrenamiento...")

    for agent in ['SAC', 'PPO', 'A2C']:
        metrics_file = TRAINING_DIR / f"{agent}_training_metrics.csv"
        if not metrics_file.exists():
            print(f"  ⚠️  {agent}: No encontrado")
            continue

        df = pd.read_csv(metrics_file)
        if df.empty:
            print(f"  ⚠️  {agent}: Sin datos")
            continue

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f'{agent} - Métricas de Entrenamiento', fontsize=16, fontweight='bold')

        # Mean Reward
        if 'mean_reward' in df.columns:
            axes[0, 0].plot(df.index, df['mean_reward'], color=COLORS[agent], linewidth=2.5,
                          marker='o', markersize=8)
            axes[0, 0].fill_between(df.index, df['mean_reward'], alpha=0.3, color=COLORS[agent])
            axes[0, 0].set_title('Mean Reward')
            axes[0, 0].set_xlabel('Episodio')
            axes[0, 0].set_ylabel('Reward')
            axes[0, 0].grid(True, alpha=0.3)

        # CO₂
        if 'episode_co2_kg' in df.columns:
            axes[0, 1].plot(df.index, df['episode_co2_kg'], color=COLORS[agent], linewidth=2.5,
                          marker='s', markersize=8)
            axes[0, 1].fill_between(df.index, df['episode_co2_kg'], alpha=0.3, color=COLORS[agent])
            axes[0, 1].set_title('CO₂ por Episodio')
            axes[0, 1].set_xlabel('Episodio')
            axes[0, 1].set_ylabel('CO₂ (kg)')
            axes[0, 1].grid(True, alpha=0.3)

        # Grid Import
        if 'episode_grid_kwh' in df.columns:
            axes[1, 0].plot(df.index, df['episode_grid_kwh'], color=COLORS[agent], linewidth=2.5,
                          marker='^', markersize=8)
            axes[1, 0].fill_between(df.index, df['episode_grid_kwh'], alpha=0.3, color=COLORS[agent])
            axes[1, 0].set_title('Grid Import')
            axes[1, 0].set_xlabel('Episodio')
            axes[1, 0].set_ylabel('Grid (kWh)')
            axes[1, 0].grid(True, alpha=0.3)

        # Solar
        if 'episode_solar_kwh' in df.columns:
            axes[1, 1].plot(df.index, df['episode_solar_kwh'], color=COLORS[agent], linewidth=2.5,
                          marker='d', markersize=8)
            axes[1, 1].fill_between(df.index, df['episode_solar_kwh'], alpha=0.3, color=COLORS[agent])
            axes[1, 1].set_title('Solar Utilizado')
            axes[1, 1].set_xlabel('Episodio')
            axes[1, 1].set_ylabel('Solar (kWh)')
            axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()
        output_path = GRAPHICS_DIR / f"{agent}_training_metrics.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"  ✅ {agent}: {output_path.name}")
        plt.close()


def plot_training_metrics_combined():
    """Gráfica combinada de entrenamientos de los 3 agentes"""
    print("\n📊 Generando gráfica combinada de entrenamientos (3 agentes)...")

    all_data = {}
    for agent in ['SAC', 'PPO', 'A2C']:
        metrics_file = TRAINING_DIR / f"{agent}_training_metrics.csv"
        if metrics_file.exists():
            all_data[agent] = pd.read_csv(metrics_file)

    if len(all_data) < 3:
        print("  ⚠️  No hay datos completos para los 3 agentes")
        return

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Comparativa de Entrenamientos - SAC vs PPO vs A2C', fontsize=18, fontweight='bold')

    # Mean Reward
    ax = axes[0, 0]
    for agent, df in all_data.items():
        if 'mean_reward' in df.columns:
            ax.plot(df.index, df['mean_reward'], color=COLORS[agent], linewidth=3,
                   marker='o', markersize=10, label=agent)
    ax.set_title('Mean Reward por Episodio', fontsize=14, fontweight='bold')
    ax.set_xlabel('Episodio', fontsize=12)
    ax.set_ylabel('Reward', fontsize=12)
    ax.legend(fontsize=12, loc='best')
    ax.grid(True, alpha=0.3)

    # CO₂
    ax = axes[0, 1]
    for agent, df in all_data.items():
        if 'episode_co2_kg' in df.columns:
            ax.plot(df.index, df['episode_co2_kg'], color=COLORS[agent], linewidth=3,
                   marker='s', markersize=10, label=agent)
    ax.set_title('CO₂ por Episodio (kg)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Episodio', fontsize=12)
    ax.set_ylabel('CO₂ (kg)', fontsize=12)
    ax.legend(fontsize=12, loc='best')
    ax.grid(True, alpha=0.3)

    # Grid Import
    ax = axes[1, 0]
    for agent, df in all_data.items():
        if 'episode_grid_kwh' in df.columns:
            ax.plot(df.index, df['episode_grid_kwh'], color=COLORS[agent], linewidth=3,
                   marker='^', markersize=10, label=agent)
    ax.set_title('Grid Import por Episodio (kWh)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Episodio', fontsize=12)
    ax.set_ylabel('Grid Import (kWh)', fontsize=12)
    ax.legend(fontsize=12, loc='best')
    ax.grid(True, alpha=0.3)

    # Solar
    ax = axes[1, 1]
    for agent, df in all_data.items():
        if 'episode_solar_kwh' in df.columns:
            ax.plot(df.index, df['episode_solar_kwh'], color=COLORS[agent], linewidth=3,
                   marker='d', markersize=10, label=agent)
    ax.set_title('Solar Utilizado por Episodio (kWh)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Episodio', fontsize=12)
    ax.set_ylabel('Solar (kWh)', fontsize=12)
    ax.legend(fontsize=12, loc='best')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    output_path = GRAPHICS_DIR / "training_metrics_combined.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✅ Combinada: {output_path.name}")
    plt.close()
    ax.set_ylabel('CO₂ (kg)')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    output_path = GRAPHICS_DIR / "energy_co2_cumulative.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✅ CO₂: {output_path.name}")
    plt.close()


def plot_comparison_bars():
    """Gráficas comparativas con barras"""
    print("\n📈 Generando gráficas comparativas...")

    results = {}
    for agent in ['SAC', 'PPO', 'A2C']:
        result_file = OUTPUT_DIR / f"result_{agent}.json"
        if result_file.exists():
            with open(result_file) as f:
                results[agent] = json.load(f)

    if not results:
        print("  ⚠️  Sin datos de resultados")
        return

    agents_list = list(results.keys())

    # Grid Import
    fig, ax = plt.subplots(figsize=(10, 6))
    grid_values = [results[a].get('grid_import_kwh', 0) for a in agents_list]
    bars = ax.bar(agents_list, grid_values, color=[COLORS[a] for a in agents_list], alpha=0.7)
    ax.set_title('Grid Import Anual', fontsize=14, fontweight='bold')
    ax.set_ylabel('kWh')
    ax.grid(True, alpha=0.3, axis='y')
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height, f'{int(height):,}',
               ha='center', va='bottom')
    plt.tight_layout()
    output_path = GRAPHICS_DIR / "comparison_grid_import.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✅ Grid: {output_path.name}")
    plt.close()

    # CO₂
    fig, ax = plt.subplots(figsize=(10, 6))
    co2_values = [results[a].get('carbon_kg', 0) for a in agents_list]
    bars = ax.bar(agents_list, co2_values, color=[COLORS[a] for a in agents_list], alpha=0.7)
    ax.set_title('CO₂ Anual', fontsize=14, fontweight='bold')
    ax.set_ylabel('kg')
    ax.grid(True, alpha=0.3, axis='y')
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height, f'{int(height):,}',
               ha='center', va='bottom')
    plt.tight_layout()
    output_path = GRAPHICS_DIR / "comparison_co2.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✅ CO₂: {output_path.name}")
    plt.close()

    # EV Charging
    fig, ax = plt.subplots(figsize=(10, 6))
    ev_values = [results[a].get('ev_charging_kwh', 0) for a in agents_list]
    bars = ax.bar(agents_list, ev_values, color=[COLORS[a] for a in agents_list], alpha=0.7)
    ax.set_title('EV Charging Anual', fontsize=14, fontweight='bold')
    ax.set_ylabel('kWh')
    ax.grid(True, alpha=0.3, axis='y')
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height, f'{int(height):,}',
               ha='center', va='bottom')
    plt.tight_layout()
    output_path = GRAPHICS_DIR / "comparison_ev_charging.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✅ EV: {output_path.name}")
    plt.close()


def plot_performance_summary():
    """Gráficas de performance"""
    print("\n🎯 Generando gráficas de performance...")

    results = {}
    for agent in ['SAC', 'PPO', 'A2C']:
        result_file = OUTPUT_DIR / f"result_{agent}.json"
        if result_file.exists():
            with open(result_file) as f:
                results[agent] = json.load(f)

    if not results:
        return

    # Matriz de Performance
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle('Performance - Comparativa', fontsize=14, fontweight='bold')

    metrics = [('grid_import_kwh', 'Grid (kWh)'),
               ('carbon_kg', 'CO₂ (kg)'),
               ('ev_charging_kwh', 'EV (kWh)')]

    agents_list = list(results.keys())
    for ax, (metric, title) in zip(axes, metrics):
        values = [results[a].get(metric, 0) for a in agents_list]
        bars = ax.bar(agents_list, values, color=[COLORS[a] for a in agents_list], alpha=0.7)
        ax.set_title(title)
        ax.grid(True, alpha=0.3, axis='y')
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height, f'{int(height):,}',
                   ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    output_path = GRAPHICS_DIR / "performance_summary.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✅ Performance: {output_path.name}")
    plt.close()

    # Reward Components
    fig, ax = plt.subplots(figsize=(12, 6))
    components = ['reward_co2_mean', 'reward_cost_mean', 'reward_solar_mean',
                 'reward_ev_mean', 'reward_grid_mean']
    x_pos = np.arange(len(agents_list))
    width = 0.15

    for i, component in enumerate(components):
        values = [results[a].get(component, 0) for a in agents_list]
        ax.bar(x_pos + i*width, values, width,
              label=component.replace('reward_', '').replace('_mean', ''))

    ax.set_title('Componentes de Reward', fontsize=14, fontweight='bold')
    ax.set_xlabel('Agente')
    ax.set_ylabel('Valor')
    ax.set_xticks(x_pos + width * 2)
    ax.set_xticklabels(agents_list)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    output_path = GRAPHICS_DIR / "reward_components.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✅ Rewards: {output_path.name}")
    plt.close()


def main():
    """Main execution"""
    print()
    print('╔' + '═'*76 + '╗')
    print('║' + ' REGENERACIÓN DE GRÁFICAS - SISTEMA OE3 '.center(76) + '║')
    print('╚' + '═'*76 + '╝')
    print()

    try:
        plot_training_metrics()
        plot_comparison_bars()
        plot_performance_summary()

        print()
        print('✅ GRÁFICAS GENERADAS EXITOSAMENTE')
        print('=' * 80)
        print(f'Ubicación: analyses/oe3/training/graphics/')
        print()
        graphics = list(sorted(GRAPHICS_DIR.glob('*.png')))
        print(f'Total: {len(graphics)} gráficas generadas:')
        for png_file in graphics:
            print(f'  ✅ {png_file.name}')
        print()
        print('🟢 TODAS LAS GRÁFICAS LISTAS Y DISPONIBLES')
        print()

    except Exception as e:
        print(f'\n❌ ERROR: {str(e)}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
