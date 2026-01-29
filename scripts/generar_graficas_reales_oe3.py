#!/usr/bin/env python3
"""
Generador de Gráficas Reales - Sistema OE3
Utiliza datos de checkpoints y simulaciones reales
"""

from __future__ import annotations

import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')
plt.style.use('seaborn-v0_8-darkgrid')

COLORS = {'SAC': '#FF6B6B', 'PPO': '#4ECDC4', 'A2C': '#45B7D1', 'Uncontrolled': '#95E1D3'}
OUTPUT_DIR = Path("outputs/oe3/simulations")
TRAINING_DIR = Path("analyses/oe3/training")
GRAPHICS_DIR = TRAINING_DIR / "graphics"
GRAPHICS_DIR.mkdir(exist_ok=True, parents=True)


def load_real_data():
    """Cargar datos reales de simulaciones"""
    print("\n[DATOS] Cargando datos reales de simulaciones...")

    data = {}
    available_agents = []
    missing_agents = []

    # Intentar cargar todos los agentes posibles
    all_agents = ['SAC', 'PPO', 'A2C']

    for agent in all_agents:
        result_file = OUTPUT_DIR / f"result_{agent}.json"
        ts_file = OUTPUT_DIR / f"timeseries_{agent}.csv"

        if result_file.exists() and ts_file.exists():
            try:
                with open(result_file) as f:
                    data[agent] = {
                        'result': json.load(f),
                        'timeseries': pd.read_csv(ts_file)
                    }
                available_agents.append(agent)
                print(f"  OK {agent}: Datos de simulacion cargados")
            except Exception as e:
                print(f"  ⚠️  {agent}: Error cargando ({str(e)[:30]}...)")
                missing_agents.append(agent)
        else:
            missing_agents.append(agent)
            print(f"  ⚠️  {agent}: NO tiene datos de simulación (archivos faltantes)")

    # Cargar baseline
    baseline_result = OUTPUT_DIR / "result_Uncontrolled.json"
    baseline_ts = OUTPUT_DIR / "timeseries_Uncontrolled.csv"
    if baseline_result.exists() and baseline_ts.exists():
        with open(baseline_result) as f:
            data['Uncontrolled'] = {
                'result': json.load(f),
                'timeseries': pd.read_csv(baseline_ts)
            }
        print(f"  OK Uncontrolled (Baseline): Cargado")

    # Cargar métricas de entrenamiento (de checkpoints)
    metrics = {}
    for agent in all_agents:
        metrics_file = TRAINING_DIR / f"{agent}_training_metrics.csv"
        if metrics_file.exists():
            metrics[agent] = pd.read_csv(metrics_file)
            print(f"  OK {agent}: Metricas de entrenamiento cargadas")

    # Mostrar resumen de agentes disponibles
    print(f"\n  [INFO] Resumen:")
    print(f"     Agentes CON simulación: {', '.join(available_agents) if available_agents else 'Ninguno'}")
    print(f"     Agentes SIN simulación: {', '.join(missing_agents) if missing_agents else 'Ninguno'}")
    print(f"     Baseline: Uncontrolled\n")

    return data, metrics, available_agents


def plot_training_metrics(metrics: dict) -> None:
    """Gráficas de métricas de entrenamiento de los 3 agentes"""
    print("\n[GRAFICAS] Generando graficas de entrenamientos (3 agentes)...")

    # Gráfica 1: Mean Reward por Agente
    fig, ax = plt.subplots(figsize=(12, 6))  # noqa: F841
    for agent in ['SAC', 'PPO', 'A2C']:
        if agent in metrics and len(metrics[agent]) > 0:
            ax.plot(metrics[agent].index, metrics[agent]['mean_reward'],
                   color=COLORS[agent], linewidth=2.5, marker='o',
                   markersize=10, label=agent)

    ax.set_title('Mean Reward - Comparativa de 3 Agentes', fontsize=14, fontweight='bold')
    ax.set_xlabel('Episodio')
    ax.set_ylabel('Mean Reward')
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    output_path = GRAPHICS_DIR / "training_mean_reward_3agentes.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  OK Mean Reward: {output_path.name}")
    plt.close()

    # Gráfica 2: CO2 por Episodio
    fig, ax = plt.subplots(figsize=(12, 6))  # noqa: F841
    for agent in ['SAC', 'PPO', 'A2C']:
        if agent in metrics and len(metrics[agent]) > 0:
            ax.plot(metrics[agent].index, metrics[agent]['episode_co2_kg'],
                   color=COLORS[agent], linewidth=2.5, marker='s',
                   markersize=10, label=agent)

    ax.set_title('CO₂ por Episodio - Comparativa de 3 Agentes', fontsize=14, fontweight='bold')
    ax.set_xlabel('Episodio')
    ax.set_ylabel('CO₂ (kg)')
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    output_path = GRAPHICS_DIR / "training_co2_3agentes.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  OK CO2: {output_path.name}")
    plt.close()

    # Gráfica 3: Grid Import por Episodio
    fig, ax = plt.subplots(figsize=(12, 6))
    for agent in ['SAC', 'PPO', 'A2C']:
        if agent in metrics and len(metrics[agent]) > 0:
            ax.plot(metrics[agent].index, metrics[agent]['episode_grid_kwh'],
                   color=COLORS[agent], linewidth=2.5, marker='^',
                   markersize=10, label=agent)

    ax.set_title('Grid Import por Episodio - Comparativa de 3 Agentes', fontsize=14, fontweight='bold')
    ax.set_xlabel('Episodio')
    ax.set_ylabel('Grid Import (kWh)')
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    output_path = GRAPHICS_DIR / "training_grid_3agentes.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  OK Grid Import: {output_path.name}")
    plt.close()

    # Gráfica 4: Solar Utilizado por Episodio
    fig, ax = plt.subplots(figsize=(12, 6))
    for agent in ['SAC', 'PPO', 'A2C']:
        if agent in metrics and len(metrics[agent]) > 0:
            ax.plot(metrics[agent].index, metrics[agent]['episode_solar_kwh'],
                   color=COLORS[agent], linewidth=2.5, marker='d',
                   markersize=10, label=agent)

    ax.set_title('Solar Utilizado por Episodio - Comparativa de 3 Agentes', fontsize=14, fontweight='bold')
    ax.set_xlabel('Episodio')
    ax.set_ylabel('Solar (kWh)')
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    output_path = GRAPHICS_DIR / "training_solar_3agentes.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  OK Solar: {output_path.name}")
    plt.close()


def plot_real_energy_data(data):
    """Gráficas basadas en datos reales de simulación"""
    print("\n⚡ Generando gráficas de energía (datos reales)...")

    # Gráfica 1: Grid Import Acumulado Real
    fig, ax = plt.subplots(figsize=(14, 6))
    for agent in ['SAC', 'A2C', 'Uncontrolled']:
        if agent in data and data[agent]['timeseries'] is not None:
            df = data[agent]['timeseries']
            cumsum = df['grid_import_kwh'].cumsum() / 1000
            ax.plot(range(len(cumsum)), cumsum, label=agent,
                   color=COLORS[agent], linewidth=2.5)

    ax.set_title('Grid Import Acumulado - Datos Reales del Año', fontsize=14, fontweight='bold')
    ax.set_xlabel('Hora del Año')
    ax.set_ylabel('Grid Import Acumulado (MWh)')
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    output_path = GRAPHICS_DIR / "energy_grid_import_real.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  OK Grid Import Real: {output_path.name}")
    plt.close()

    # Gráfica 2: CO₂ Acumulado Real (basado en grid_import × carbon_intensity)
    fig, ax = plt.subplots(figsize=(14, 6))
    for agent in ['SAC', 'A2C', 'Uncontrolled']:
        if agent in data and data[agent]['timeseries'] is not None:
            df = data[agent]['timeseries']
            # CO₂ = grid_import_kwh × carbon_intensity_kg_per_kwh
            co2_hourly = df['grid_import_kwh'] * df['carbon_intensity_kg_per_kwh']
            cumsum_co2 = co2_hourly.cumsum()
            ax.plot(range(len(cumsum_co2)), cumsum_co2, label=agent,
                   color=COLORS[agent], linewidth=2.5)

    ax.set_title('CO₂ Acumulado Real - Datos Reales del Año', fontsize=14, fontweight='bold')
    ax.set_xlabel('Hora del Año')
    ax.set_ylabel('CO₂ Acumulado (kg)')
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    output_path = GRAPHICS_DIR / "energy_co2_real.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  OK CO2 Real: {output_path.name}")
    plt.close()

    # Gráfica 3: Solar Generado y Utilizado
    fig, ax = plt.subplots(figsize=(14, 6))
    for agent in ['SAC', 'A2C', 'Uncontrolled']:
        if agent in data and data[agent]['timeseries'] is not None:
            df = data[agent]['timeseries']
            cumsum = df['pv_generation_kwh'].cumsum() / 1000
            ax.plot(range(len(cumsum)), cumsum, label=agent,
                   color=COLORS[agent], linewidth=2.5)

    ax.set_title('Solar Generado Acumulado - Datos Reales del Año', fontsize=14, fontweight='bold')
    ax.set_xlabel('Hora del Año')
    ax.set_ylabel('Solar Generado (MWh)')
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    output_path = GRAPHICS_DIR / "energy_solar_generation_real.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  OK Solar Real: {output_path.name}")
    plt.close()

    # Gráfica 4: EV Charging Acumulado
    fig, ax = plt.subplots(figsize=(14, 6))
    for agent in ['SAC', 'A2C', 'Uncontrolled']:
        if agent in data and data[agent]['timeseries'] is not None:
            df = data[agent]['timeseries']
            cumsum = df['ev_charging_kwh'].cumsum() / 1000
            ax.plot(range(len(cumsum)), cumsum, label=agent,
                   color=COLORS[agent], linewidth=2.5)

    ax.set_title('Carga EV Acumulada - Datos Reales del Año', fontsize=14, fontweight='bold')
    ax.set_xlabel('Hora del Año')
    ax.set_ylabel('EV Charging (MWh)')
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    output_path = GRAPHICS_DIR / "energy_ev_charging_real.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  OK EV Charging Real: {output_path.name}")
    plt.close()


def plot_comparison_results(data):
    """Gráficas comparativas finales"""
    print("\n📈 Generando gráficas comparativas (resultados finales)...")

    # Preparar datos
    results = {}
    for agent in ['SAC', 'A2C', 'Uncontrolled']:
        if agent in data:
            results[agent] = data[agent]['result']

    agents_list = list(results.keys())

    # Gráfica 1: Grid Import Final
    fig, ax = plt.subplots(figsize=(10, 6))
    grid_values = [results[a].get('grid_import_kwh', 0) for a in agents_list]
    bars = ax.bar(agents_list, grid_values, color=[COLORS[a] for a in agents_list], alpha=0.8, width=0.6)
    ax.set_title('Grid Import Anual - Resultados Finales', fontsize=14, fontweight='bold')
    ax.set_ylabel('kWh')
    ax.grid(True, alpha=0.3, axis='y')
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{int(height):,}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    plt.tight_layout()
    output_path = GRAPHICS_DIR / "comparison_grid_import_final.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  OK Grid Import Final: {output_path.name}")
    plt.close()

    # Gráfica 2: CO₂ Anual
    fig, ax = plt.subplots(figsize=(10, 6))
    co2_values = [results[a].get('carbon_kg', 0) for a in agents_list]
    bars = ax.bar(agents_list, co2_values, color=[COLORS[a] for a in agents_list], alpha=0.8, width=0.6)
    ax.set_title('CO₂ Anual - Resultados Finales', fontsize=14, fontweight='bold')
    ax.set_ylabel('kg CO₂')
    ax.grid(True, alpha=0.3, axis='y')
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{int(height):,}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    plt.tight_layout()
    output_path = GRAPHICS_DIR / "comparison_co2_final.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  OK CO2 Final: {output_path.name}")
    plt.close()

    # Gráfica 3: EV Charging
    fig, ax = plt.subplots(figsize=(10, 6))
    ev_values = [results[a].get('ev_charging_kwh', 0) for a in agents_list]
    bars = ax.bar(agents_list, ev_values, color=[COLORS[a] for a in agents_list], alpha=0.8, width=0.6)
    ax.set_title('EV Charging Anual - Resultados Finales', fontsize=14, fontweight='bold')
    ax.set_ylabel('kWh')
    ax.grid(True, alpha=0.3, axis='y')
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{int(height):,}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    plt.tight_layout()
    output_path = GRAPHICS_DIR / "comparison_ev_charging_final.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  OK EV Charging Final: {output_path.name}")
    plt.close()

    # Gráfica 4: Matriz de 3 KPIs
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle('Resultados Finales - Comparativa Integrada', fontsize=14, fontweight='bold')

    metrics = [
        ('grid_import_kwh', 'Grid Import (kWh)'),
        ('carbon_kg', 'CO₂ (kg)'),
        ('ev_charging_kwh', 'EV Charging (kWh)')
    ]

    for ax, (metric, title) in zip(axes, metrics):
        values = [results[a].get(metric, 0) for a in agents_list]
        bars = ax.bar(agents_list, values, color=[COLORS[a] for a in agents_list], alpha=0.8, width=0.6)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height):,}', ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    output_path = GRAPHICS_DIR / "comparison_kpis_matrix.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  OK Matriz KPIs: {output_path.name}")
    plt.close()


def plot_reduction_vs_baseline(data):
    """Gráficas de reducción vs baseline"""
    print("\n🎯 Generando gráficas de reducción vs baseline...")

    results = {}
    for agent in ['SAC', 'A2C', 'Uncontrolled']:
        if agent in data:
            results[agent] = data[agent]['result']

    if 'Uncontrolled' not in results:
        print("  ⚠️  No hay baseline para comparar")
        return

    baseline_co2 = results['Uncontrolled'].get('carbon_kg', 1)
    baseline_grid = results['Uncontrolled'].get('grid_import_kwh', 1)

    agents_list = ['SAC', 'A2C']

    # Gráfica 1: Reducción de CO₂
    fig, ax = plt.subplots(figsize=(10, 6))
    co2_reductions = []
    for agent in agents_list:
        if agent in results:
            agent_co2 = results[agent].get('carbon_kg', 0)
            reduction = ((baseline_co2 - agent_co2) / baseline_co2) * 100
            co2_reductions.append(reduction)

    bars = ax.bar(agents_list, co2_reductions, color=[COLORS[a] for a in agents_list], alpha=0.8, width=0.6)
    ax.set_title('Reduccion de CO2 vs Baseline', fontsize=14, fontweight='bold')
    ax.set_ylabel('Reduccion (%)')
    ax.set_ylim(0, 50)
    ax.grid(True, alpha=0.3, axis='y')
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{height:.1f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')
    plt.tight_layout()
    output_path = GRAPHICS_DIR / "reduction_co2_vs_baseline.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  OK Reduccion CO2: {output_path.name}")
    plt.close()

    # Gráfica 2: Reducción de Grid Import
    fig, ax = plt.subplots(figsize=(10, 6))
    grid_reductions = []
    for agent in agents_list:
        if agent in results:
            agent_grid = results[agent].get('grid_import_kwh', 0)
            reduction = ((baseline_grid - agent_grid) / baseline_grid) * 100
            grid_reductions.append(reduction)

    bars = ax.bar(agents_list, grid_reductions, color=[COLORS[a] for a in agents_list], alpha=0.8, width=0.6)
    ax.set_title('Reduccion de Grid Import vs Baseline', fontsize=14, fontweight='bold')
    ax.set_ylabel('Reduccion (%)')
    ax.set_ylim(0, 50)
    ax.grid(True, alpha=0.3, axis='y')
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{height:.1f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')
    plt.tight_layout()
    output_path = GRAPHICS_DIR / "reduction_grid_vs_baseline.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  ✅ Reducción Grid: {output_path.name}")
    plt.close()


def main():
    """Main execution"""
    print()
    print('╔' + '═'*76 + '╗')
    print('║' + ' GRÁFICAS REALES - SISTEMA OE3 (Checkpoints + Simulaciones) '.center(76) + '║')
    print('╚' + '═'*76 + '╝')
    print()

    try:
        # Cargar datos reales
        data, metrics, available_agents = load_real_data()

        # Generar gráficas
        plot_training_metrics(metrics)
        plot_real_energy_data(data)
        plot_comparison_results(data)
        plot_reduction_vs_baseline(data)

        print()
        print('✅ GRÁFICAS REALES GENERADAS EXITOSAMENTE')
        print('=' * 80)
        print(f'Ubicación: analyses/oe3/training/graphics/')
        print()
        graphics = list(sorted(GRAPHICS_DIR.glob('*.png')))
        print(f'Total: {len(graphics)} gráficas')
        for png_file in graphics:
            print(f'  ✅ {png_file.name}')
        print()
        print('🟢 TODAS LAS GRÁFICAS BASADAS EN DATOS REALES')
        print()

    except Exception as e:
        print(f'\n❌ ERROR: {str(e)}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
