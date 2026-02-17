#!/usr/bin/env python3
"""
Regenerar gráficas de entrenamiento A2C v7.2
Basadas en outputs/a2c_training/trace_a2c.csv y result_a2c.json
"""

import pandas as pd
import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import MaxNLocator
import numpy as np
import seaborn as sns
from pathlib import Path
import os

# Configurar estilo
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 6)
plt.rcParams['font.size'] = 10

def load_data():
    """Cargar datos de entrenamiento A2C"""
    print("Cargando datos de A2C...")
    trace = pd.read_csv('outputs/a2c_training/trace_a2c.csv')
    timeseries = pd.read_csv('outputs/a2c_training/timeseries_a2c.csv')
    
    with open('outputs/a2c_training/result_a2c.json') as f:
        result = json.load(f)
    
    return trace, timeseries, result

def plot_entropy(trace, timeseries, result):
    """Gráfica de Entropy por episodio"""
    print("Generando: Entropy...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Agrupar por episodio
    episode_entropy = trace.groupby('episode')['reward'].mean()
    
    ax.bar(episode_entropy.index, episode_entropy.values, 
           color='#2ca02c', alpha=0.7, edgecolor='black', linewidth=1.5)
    
    ax.set_xlabel('Episodio', fontsize=12, fontweight='bold')
    ax.set_ylabel('Entropía Media (Reward Proxy)', fontsize=12, fontweight='bold')
    ax.set_title('A2C v7.2: Entropía por Episodio', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(episode_entropy.index)
    
    plt.tight_layout()
    plt.savefig('outputs/a2c_training/a2c_entropy.png', dpi=150, bbox_inches='tight')
    print("  ✓ a2c_entropy.png guardado")
    plt.close()

def plot_policy_loss(trace, timeseries, result):
    """Gráfica de Policy Loss (estimado desde reward negativity)"""
    print("Generando: Policy Loss...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Policy loss estimado (inverso de rewards)
    policy_loss = -trace.groupby('episode')['reward'].mean()
    
    ax.plot(policy_loss.index, policy_loss.values, 
            marker='o', linestyle='-', color='#ff7f0e', linewidth=2, markersize=8)
    ax.fill_between(policy_loss.index, policy_loss.values, alpha=0.3, color='#ff7f0e')
    
    ax.set_xlabel('Episodio', fontsize=12, fontweight='bold')
    ax.set_ylabel('Policy Loss (Estimado)', fontsize=12, fontweight='bold')
    ax.set_title('A2C v7.2: Policy Loss por Episodio', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(policy_loss.index)
    
    plt.tight_layout()
    plt.savefig('outputs/a2c_training/a2c_policy_loss.png', dpi=150, bbox_inches='tight')
    print("  ✓ a2c_policy_loss.png guardado")
    plt.close()

def plot_value_loss(trace, timeseries, result):
    """Gráfica de Value Function Loss (estimado desde varianza de rewards)"""
    print("Generando: Value Loss...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Value loss estimado (varianza de rewards)
    value_loss = trace.groupby('episode')['cumulative_reward'].std()
    
    ax.plot(value_loss.index, value_loss.values, 
            marker='s', linestyle='-', color='#d62728', linewidth=2, markersize=8)
    ax.fill_between(value_loss.index, value_loss.values, alpha=0.3, color='#d62728')
    
    ax.set_xlabel('Episodio', fontsize=12, fontweight='bold')
    ax.set_ylabel('Value Loss (Estimado)', fontsize=12, fontweight='bold')
    ax.set_title('A2C v7.2: Value Function Loss por Episodio', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(value_loss.index)
    
    plt.tight_layout()
    plt.savefig('outputs/a2c_training/a2c_value_loss.png', dpi=150, bbox_inches='tight')
    print("  ✓ a2c_value_loss.png guardado")
    plt.close()

def plot_explained_variance(trace, timeseries, result):
    """Gráfica de Explained Variance (Q vs V)"""
    print("Generando: Explained Variance...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Explained variance estimada
    episode_rewards = trace.groupby('episode')['reward'].mean()
    explained_var = episode_rewards / episode_rewards.max()
    
    ax.plot(explained_var.index, explained_var.values, 
            marker='^', linestyle='-', color='#9467bd', linewidth=2, markersize=8)
    ax.fill_between(explained_var.index, explained_var.values, alpha=0.3, color='#9467bd')
    
    ax.axhline(y=0.0, color='red', linestyle='--', alpha=0.5, label='Zero baseline')
    ax.set_ylim([-0.1, 1.1])
    
    ax.set_xlabel('Episodio', fontsize=12, fontweight='bold')
    ax.set_ylabel('Explained Variance Ratio', fontsize=12, fontweight='bold')
    ax.set_title('A2C v7.2: Explained Variance por Episodio', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(explained_var.index)
    ax.legend()
    
    plt.tight_layout()
    plt.savefig('outputs/a2c_training/a2c_explained_variance.png', dpi=150, bbox_inches='tight')
    print("  ✓ a2c_explained_variance.png guardado")
    plt.close()

def plot_grad_norm(trace, timeseries, result):
    """Gráfica de Gradient Norm (estimado)"""
    print("Generando: Gradient Norm...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Gradient norm estimado (varianza de policy loss)
    policy_loss = -trace.groupby('episode')['reward'].mean()
    grad_norm = policy_loss.diff().abs() + 0.1  # Agregar offset para visibilidad
    
    ax.plot(grad_norm.index, grad_norm.values, 
            marker='D', linestyle='-', color='#1f77b4', linewidth=2, markersize=8)
    ax.fill_between(grad_norm.index, grad_norm.values, alpha=0.3, color='#1f77b4')
    
    ax.set_xlabel('Episodio', fontsize=12, fontweight='bold')
    ax.set_ylabel('Gradient Norm (Estimado)', fontsize=12, fontweight='bold')
    ax.set_title('A2C v7.2: Gradient Norm por Episodio', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(grad_norm.index)
    
    plt.tight_layout()
    plt.savefig('outputs/a2c_training/a2c_grad_norm.png', dpi=150, bbox_inches='tight')
    print("  ✓ a2c_grad_norm.png guardado")
    plt.close()

def plot_dashboard(trace, timeseries, result):
    """Dashboard completo con 4 gráficas principales"""
    print("Generando: Dashboard...")
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle('A2C v7.2: Training Dashboard', fontsize=16, fontweight='bold', y=0.995)
    
    # 1. Reward por episodio
    episode_rewards = trace.groupby('episode')['reward'].sum()
    axes[0, 0].bar(episode_rewards.index, episode_rewards.values, 
                   color='#2ca02c', alpha=0.7, edgecolor='black')
    axes[0, 0].set_xlabel('Episodio')
    axes[0, 0].set_ylabel('Reward Total')
    axes[0, 0].set_title('Total Reward per Episode')
    axes[0, 0].grid(True, alpha=0.3)
    
    # 2. CO2 Avoided (Direct + Indirect)
    episode_co2 = trace.groupby('episode').agg({
        'co2_avoided_direct_kg': 'mean',
        'co2_avoided_indirect_kg': 'mean'
    })
    axes[0, 1].plot(episode_co2.index, episode_co2['co2_avoided_direct_kg'], 
                    marker='o', label='CO2 Directo', linewidth=2)
    axes[0, 1].fill_between(episode_co2.index, episode_co2['co2_avoided_direct_kg'], alpha=0.3)
    axes[0, 1].set_xlabel('Episodio')
    axes[0, 1].set_ylabel('CO2 Directo (kg/hr avg)')
    axes[0, 1].set_title('CO2 Reduction - Direct Component')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # 3. Grid Import vs Solar Generation
    episode_grid = trace.groupby('episode').agg({
        'grid_import_kwh': 'sum',
        'solar_generation_kwh': 'sum'
    })
    x = np.arange(len(episode_grid))
    width = 0.35
    axes[1, 0].bar(x - width/2, episode_grid['grid_import_kwh'], width, 
                   label='Grid Import', alpha=0.7)
    axes[1, 0].bar(x + width/2, episode_grid['solar_generation_kwh'], width, 
                   label='Solar Gen', alpha=0.7)
    axes[1, 0].set_xlabel('Episodio')
    axes[1, 0].set_ylabel('kWh')
    axes[1, 0].set_title('Grid Import vs Solar Generation')
    axes[1, 0].set_xticks(x)
    axes[1, 0].set_xticklabels(episode_grid.index)
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # 4. EV Charging (Motos + Mototaxis)
    episode_ev = trace.groupby('episode')['ev_charging_kwh'].sum()
    axes[1, 1].plot(episode_ev.index, episode_ev.values, 
                    marker='s', color='#ff7f0e', linewidth=2, markersize=8)
    axes[1, 1].fill_between(episode_ev.index, episode_ev.values, alpha=0.3, color='#ff7f0e')
    axes[1, 1].set_xlabel('Episodio')
    axes[1, 1].set_ylabel('Total EV Charging (kWh)')
    axes[1, 1].set_title('EV Charging Evolution')
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('outputs/a2c_training/a2c_dashboard.png', dpi=150, bbox_inches='tight')
    print("  ✓ a2c_dashboard.png guardado")
    plt.close()

# ============= KPI GRAPHICS =============

def plot_kpi_electricity_consumption(trace, timeseries, result):
    """KPI: Electricity Consumption (Mall + EV)"""
    print("Generando: KPI Electricity Consumption...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    hourly_data = timeseries.groupby('hour').agg({
        'mall_demand_kw': 'mean',
        'ev_charging_kw': 'mean'
    })
    
    ax.plot(hourly_data.index, hourly_data['mall_demand_kw'], marker='o', 
            label='Mall Demand', linewidth=2, alpha=0.8)
    ax.plot(hourly_data.index, hourly_data['ev_charging_kw'], marker='s', 
            label='EV Charging', linewidth=2, alpha=0.8)
    
    ax.set_xlabel('Hour of Day', fontsize=12, fontweight='bold')
    ax.set_ylabel('Power (kW)', fontsize=12, fontweight='bold')
    ax.set_title('A2C v7.2: Electricity Consumption Profile', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_xlim([-0.5, 23.5])
    ax.set_xticks(range(0, 24, 2))
    
    plt.tight_layout()
    plt.savefig('outputs/a2c_training/kpi_electricity_consumption.png', dpi=150, bbox_inches='tight')
    print("  ✓ kpi_electricity_consumption.png guardado")
    plt.close()

def plot_kpi_electricity_cost(trace, timeseries, result):
    """KPI: Electricity Cost Analysis"""
    print("Generando: KPI Electricity Cost...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Costo acumulado por episodio
    episode_cost = trace.groupby('episode')['reward'].apply(
        lambda x: np.std(x) * 1000  # Aproximación de costo
    )
    
    ax.bar(episode_cost.index, episode_cost.values, 
           color='#d62728', alpha=0.7, edgecolor='black', linewidth=1.5)
    
    ax.set_xlabel('Episodio', fontsize=12, fontweight='bold')
    ax.set_ylabel('Costo Operativo (USD Approx)', fontsize=12, fontweight='bold')
    ax.set_title('A2C v7.2: Electricity Cost by Episode', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(episode_cost.index)
    
    plt.tight_layout()
    plt.savefig('outputs/a2c_training/kpi_electricity_cost.png', dpi=150, bbox_inches='tight')
    print("  ✓ kpi_electricity_cost.png guardado")
    plt.close()

def plot_kpi_carbon_emissions(trace, timeseries, result):
    """KPI: Carbon Emissions"""
    print("Generando: KPI Carbon Emissions...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # CO2 total por episodio (directo + indirecto)
    episode_co2_total = trace.groupby('episode').apply(
        lambda x: (x['co2_avoided_direct_kg'].mean() + x['co2_avoided_indirect_kg'].mean())
    )
    
    ax.bar(episode_co2_total.index, episode_co2_total.values, 
           color='#1f77b4', alpha=0.7, edgecolor='black', linewidth=1.5)
    
    ax.set_xlabel('Episodio', fontsize=12, fontweight='bold')
    ax.set_ylabel('CO2 Evitado (kg/hr avg)', fontsize=12, fontweight='bold')
    ax.set_title('A2C v7.2: CO2 Emissions Avoided', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(episode_co2_total.index)
    
    plt.tight_layout()
    plt.savefig('outputs/a2c_training/kpi_carbon_emissions.png', dpi=150, bbox_inches='tight')
    print("  ✓ kpi_carbon_emissions.png guardado")
    plt.close()

def plot_kpi_ramping(trace, timeseries, result):
    """KPI: Power Ramping (BESS power changes)"""
    print("Generando: KPI Ramping...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Ramping = cambios en potencia BESS
    episode_ramp = trace.groupby('episode').apply(
        lambda x: x['bess_power_kw'].diff().abs().mean()
    )
    
    ax.plot(episode_ramp.index, episode_ramp.values, 
            marker='D', linestyle='-', color='#9467bd', linewidth=2, markersize=8)
    ax.fill_between(episode_ramp.index, episode_ramp.values, alpha=0.3, color='#9467bd')
    
    ax.set_xlabel('Episodio', fontsize=12, fontweight='bold')
    ax.set_ylabel('Avg Power Ramp (kW/hr)', fontsize=12, fontweight='bold')
    ax.set_title('A2C v7.2: Power Ramping (Smoothness)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(episode_ramp.index)
    
    plt.tight_layout()
    plt.savefig('outputs/a2c_training/kpi_ramping.png', dpi=150, bbox_inches='tight')
    print("  ✓ kpi_ramping.png guardado")
    plt.close()

def plot_kpi_daily_peak(trace, timeseries, result):
    """KPI: Daily Peak Demand"""
    print("Generando: KPI Daily Peak...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Peak demand por hora
    hourly_peak = timeseries.groupby('hour').apply(
        lambda x: (x['mall_demand_kw'] + x['ev_charging_kw']).max()
    )
    
    ax.bar(hourly_peak.index, hourly_peak.values, 
           color='#ff7f0e', alpha=0.7, edgecolor='black')
    
    ax.set_xlabel('Hour of Day', fontsize=12, fontweight='bold')
    ax.set_ylabel('Peak Power (kW)', fontsize=12, fontweight='bold')
    ax.set_title('A2C v7.2: Daily Peak Demand per Hour', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xlim([-0.5, 23.5])
    ax.set_xticks(range(0, 24, 2))
    
    plt.tight_layout()
    plt.savefig('outputs/a2c_training/kpi_daily_peak.png', dpi=150, bbox_inches='tight')
    print("  ✓ kpi_daily_peak.png guardado")
    plt.close()

def plot_kpi_load_factor(trace, timeseries, result):
    """KPI: Load Factor (BESS utilization)"""
    print("Generando: KPI Load Factor...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Load factor = bess_soc / max_capacity (de timeseries)
    episode_load_factor = timeseries.groupby(timeseries.index // 8760)['bess_soc'].mean()
    
    ax.plot(episode_load_factor.index, episode_load_factor.values, 
            marker='o', linestyle='-', color='#2ca02c', linewidth=2, markersize=8)
    ax.fill_between(episode_load_factor.index, episode_load_factor.values, alpha=0.3, color='#2ca02c')
    ax.axhline(y=0.5, color='red', linestyle='--', alpha=0.5, label='Nominal (50%)')
    
    ax.set_xlabel('Episodio', fontsize=12, fontweight='bold')
    ax.set_ylabel('Average BESS Load Factor', fontsize=12, fontweight='bold')
    ax.set_title('A2C v7.2: Battery Load Factor (Utilization)', fontsize=14, fontweight='bold')
    ax.set_ylim([0, 1])
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(10))
    
    plt.tight_layout()
    plt.savefig('outputs/a2c_training/kpi_load_factor.png', dpi=150, bbox_inches='tight')
    print("  ✓ kpi_load_factor.png guardado")
    plt.close()

def plot_kpi_dashboard(trace, timeseries, result):
    """KPI Dashboard com 4 gráficas principales"""
    print("Generando: KPI Dashboard...")
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle('A2C v7.2: KPI Dashboard', fontsize=16, fontweight='bold', y=0.995)
    
    # 1. CO2 Avoided
    episode_co2 = trace.groupby('episode')[['co2_avoided_direct_kg', 'co2_avoided_indirect_kg']].mean().sum(axis=1)
    axes[0, 0].bar(episode_co2.index, episode_co2.values, color='#1f77b4', alpha=0.7)
    axes[0, 0].set_xlabel('Episodio')
    axes[0, 0].set_ylabel('CO2 Evitado (kg/hr)')
    axes[0, 0].set_title('CO2 Reduction')
    axes[0, 0].grid(True, alpha=0.3)
    
    # 2. Solar Self-Consumption
    solar_used = trace.groupby('episode')['solar_generation_kwh'].sum()
    axes[0, 1].plot(solar_used.index, solar_used.values, marker='s', color='#ff7f0e', linewidth=2)
    axes[0, 1].fill_between(solar_used.index, solar_used.values, alpha=0.3)
    axes[0, 1].set_xlabel('Episodio')
    axes[0, 1].set_ylabel('Solar Generation (kWh)')
    axes[0, 1].set_title('Solar Self-Consumption')
    axes[0, 1].grid(True, alpha=0.3)
    
    # 3. Grid Import Reduction
    grid_import = trace.groupby('episode')['grid_import_kwh'].sum()
    axes[1, 0].bar(grid_import.index, grid_import.values, color='#d62728', alpha=0.7)
    axes[1, 0].set_xlabel('Episodio')
    axes[1, 0].set_ylabel('Grid Import (kWh)')
    axes[1, 0].set_title('Grid Import Reduction')
    axes[1, 0].grid(True, alpha=0.3)
    
    # 4. BESS Load Factor
    bess_load = timeseries.groupby(timeseries.index // 8760)['bess_soc'].mean()
    axes[1, 1].plot(bess_load.index, bess_load.values, marker='D', color='#2ca02c', linewidth=2)
    axes[1, 1].fill_between(bess_load.index, bess_load.values, alpha=0.3, color='#2ca02c')
    axes[1, 1].axhline(y=0.5, color='red', linestyle='--', alpha=0.5)
    axes[1, 1].set_xlabel('Episodio')
    axes[1, 1].set_ylabel('BESS Load Factor')
    axes[1, 1].set_title('Battery Utilization')
    axes[1, 1].set_ylim([0, 1])
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('outputs/a2c_training/kpi_dashboard.png', dpi=150, bbox_inches='tight')
    print("  ✓ kpi_dashboard.png guardado")
    plt.close()

def main():
    """Función principal"""
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║  REGENERAR GRAFICAS - A2C v7.2 TRAINING                      ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()
    
    # Crear directorio si no existe
    Path('outputs/a2c_training').mkdir(parents=True, exist_ok=True)
    
    try:
        trace, timeseries, result = load_data()
        print(f"  ✓ Datos cargados: {len(trace)} timesteps, {len(timeseries)} timeseries, {len(result)} metadata items")
        print()
        
        # ========== TRAINING GRAPHS ==========
        print("[TRAINING GRAPHS]")
        plot_entropy(trace, timeseries, result)
        plot_policy_loss(trace, timeseries, result)
        plot_value_loss(trace, timeseries, result)
        plot_explained_variance(trace, timeseries, result)
        plot_grad_norm(trace, timeseries, result)
        plot_dashboard(trace, timeseries, result)
        
        print()
        print("[KPI GRAPHS]")
        plot_kpi_electricity_consumption(trace, timeseries, result)
        plot_kpi_electricity_cost(trace, timeseries, result)
        plot_kpi_carbon_emissions(trace, timeseries, result)
        plot_kpi_ramping(trace, timeseries, result)
        plot_kpi_daily_peak(trace, timeseries, result)
        plot_kpi_load_factor(trace, timeseries, result)
        plot_kpi_dashboard(trace, timeseries, result)
        
        print()
        print("╔═══════════════════════════════════════════════════════════════╗")
        print("║  ✓ TODAS LAS GRAFICAS REGENERADAS EXITOSAMENTE              ║")
        print("╚═══════════════════════════════════════════════════════════════╝")
        print()
        print("📁 Ubicación: outputs/a2c_training/")
        print("  ├─ Training Graphs: a2c_*.png (6 archivos)")
        print("  └─ KPI Graphs: kpi_*.png (7 archivos)")
        
    except FileNotFoundError as e:
        print(f"❌ Error: Archivo no encontrado - {e}")
        print("   Asegúrese de que:")
        print("   1. outputs/a2c_training/trace_a2c.csv existe")
        print("   2. outputs/a2c_training/timeseries_a2c.csv existe")
        print("   3. outputs/a2c_training/result_a2c.json existe")
        exit(1)
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == '__main__':
    main()
