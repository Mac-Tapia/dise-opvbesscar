#!/usr/bin/env python3
"""
Regenerar gráficas de entrenamiento PPO v9.3
Basadas en outputs/ppo_training/trace_ppo.csv
"""

import pandas as pd
import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import MaxNLocator
import numpy as np
import seaborn as sns
from pathlib import Path

# Configurar estilo
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 6)
plt.rcParams['font.size'] = 10

def load_data():
    """Cargar datos de entrenamiento"""
    print("Cargando datos...")
    trace = pd.read_csv('outputs/ppo_training/trace_ppo.csv')
    
    with open('outputs/ppo_training/result_ppo.json') as f:
        result = json.load(f)
    
    return trace, result

def plot_kl_divergence(trace):
    """Gráfica de KL Divergence por timestep"""
    print("Generando: KL Divergence...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Filtrar valores válidos
    valid_data = trace[trace['approx_kl'] > 0].copy()
    valid_data['episode'] = valid_data['episode'].astype(int)
    
    # Línea de KL por timestep
    ax.plot(valid_data.index, valid_data['approx_kl'], 
            label='KL Divergence', color='#1f77b4', linewidth=1.5, alpha=0.8)
    
    # Línea de threshold
    ax.axhline(y=0.01, color='red', linestyle='--', linewidth=2, 
               label='Threshold (0.01)', alpha=0.7)
    
    # Sombreado por episodio
    episodes = valid_data['episode'].unique()
    colors = plt.cm.Spectral(np.linspace(0, 1, len(episodes)))
    
    for i, ep in enumerate(sorted(episodes)):
        ep_data = valid_data[valid_data['episode'] == ep]
        if len(ep_data) > 0:
            start_idx = ep_data.index[0]
            end_idx = ep_data.index[-1]
            ax.axvspan(start_idx, end_idx, alpha=0.05, color=colors[i])
    
    ax.set_xlabel('Timestep', fontsize=11, fontweight='bold')
    ax.set_ylabel('KL Divergence', fontsize=11, fontweight='bold')
    ax.set_title('KL Divergence During PPO v9.3 Training', fontsize=13, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('outputs/ppo_training/ppo_kl_divergence.png', dpi=150, bbox_inches='tight')
    print("  ✓ Guardado: ppo_kl_divergence.png")
    plt.close()

def plot_clip_fraction(trace):
    """Gráfica de Clip Fraction"""
    print("Generando: Clip Fraction...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Filtrar valores válidos
    valid_data = trace[trace['clip_fraction'] >= 0].copy()
    
    # Línea de clip fraction
    ax.plot(valid_data.index, valid_data['clip_fraction'] * 100, 
            label='Clip Fraction', color='#ff7f0e', linewidth=1.5, alpha=0.8)
    
    # Zona óptima (2-5%)
    ax.axhspan(2, 5, alpha=0.1, color='green', label='Optimal Range (2-5%)')
    ax.axhline(y=0.3*100, color='red', linestyle='--', linewidth=2, 
               label='Max Threshold (30%)', alpha=0.7)
    
    ax.set_xlabel('Timestep', fontsize=11, fontweight='bold')
    ax.set_ylabel('Clip Fraction (%)', fontsize=11, fontweight='bold')
    ax.set_title('Clip Fraction During PPO v9.3 Training', fontsize=13, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_ylim([0, 35])
    
    plt.tight_layout()
    plt.savefig('outputs/ppo_training/ppo_clip_fraction.png', dpi=150, bbox_inches='tight')
    print("  ✓ Guardado: ppo_clip_fraction.png")
    plt.close()

def plot_entropy(trace):
    """Gráfica de Entropy"""
    print("Generando: Entropy...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Filtrar valores válidos
    valid_data = trace[trace['entropy'] > 0].copy()
    
    # Línea de entropy
    ax.plot(valid_data.index, valid_data['entropy'], 
            label='Policy Entropy', color='#2ca02c', linewidth=1.5, alpha=0.8)
    
    # Zona óptima (50-60)
    ax.axhspan(50, 60, alpha=0.1, color='green', label='Optimal Range (50-60)')
    
    # Media
    mean_entropy = valid_data['entropy'].mean()
    ax.axhline(y=mean_entropy, color='blue', linestyle='--', linewidth=2,
               label=f'Mean ({mean_entropy:.2f})', alpha=0.7)
    
    ax.set_xlabel('Timestep', fontsize=11, fontweight='bold')
    ax.set_ylabel('Entropy', fontsize=11, fontweight='bold')
    ax.set_title('Policy Entropy During PPO v9.3 Training', fontsize=13, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('outputs/ppo_training/ppo_entropy.png', dpi=150, bbox_inches='tight')
    print("  ✓ Guardado: ppo_entropy.png")
    plt.close()

def plot_value_metrics(trace):
    """Gráfica de Value Loss y Policy Loss"""
    print("Generando: Value Metrics...")
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    # Value Loss
    valid_value = trace[trace['value_loss'] >= 0].copy()
    axes[0].plot(valid_value.index, valid_value['value_loss'], 
                 label='Value Loss', color='#d62728', linewidth=1.5, alpha=0.8)
    axes[0].set_ylabel('Value Loss', fontsize=11, fontweight='bold')
    axes[0].set_title('Value Loss During Training', fontsize=12, fontweight='bold')
    axes[0].legend(loc='upper right', fontsize=10)
    axes[0].grid(True, alpha=0.3)
    
    # Policy Loss
    valid_policy = trace[trace['policy_loss'] < 0].copy()
    if len(valid_policy) > 0:
        axes[1].plot(valid_policy.index, valid_policy['policy_loss'], 
                     label='Policy Loss', color='#9467bd', linewidth=1.5, alpha=0.8)
        axes[1].axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.5)
        axes[1].set_ylabel('Policy Loss', fontsize=11, fontweight='bold')
        axes[1].set_title('Policy Loss During Training', fontsize=12, fontweight='bold')
        axes[1].legend(loc='upper right', fontsize=10)
        axes[1].grid(True, alpha=0.3)
    
    axes[1].set_xlabel('Timestep', fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('outputs/ppo_training/ppo_value_metrics.png', dpi=150, bbox_inches='tight')
    print("  ✓ Guardado: ppo_value_metrics.png")
    plt.close()

def plot_dashboard(trace, result):
    """Dashboard integrado con múltiples métricas"""
    print("Generando: Dashboard...")
    
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    # 1. Reward por episodio
    ax1 = fig.add_subplot(gs[0, 0])
    episode_rewards = trace.groupby('episode')['reward'].mean()
    ax1.bar(episode_rewards.index, episode_rewards.values, color='skyblue', alpha=0.7)
    ax1.set_xlabel('Episode', fontweight='bold')
    ax1.set_ylabel('Avg Reward', fontweight='bold')
    ax1.set_title('Reward by Episode', fontweight='bold', fontsize=11)
    ax1.grid(True, alpha=0.3, axis='y')
    
    # 2. CO2 evitado por episodio
    ax2 = fig.add_subplot(gs[0, 1])
    # Calcular total CO2 evitado (suma de indirecto y directo)
    trace['co2_avoided_total'] = trace['co2_avoided_indirect_kg'] + trace['co2_avoided_direct_kg']
    episode_co2 = trace.groupby('episode')['co2_avoided_total'].sum()
    ax2.bar(episode_co2.index, episode_co2.values / 1e6, color='lightgreen', alpha=0.7)
    ax2.set_xlabel('Episode', fontweight='bold')
    ax2.set_ylabel('CO2 Avoided (M kg)', fontweight='bold')
    ax2.set_title('CO2 Reduction by Episode', fontweight='bold', fontsize=11)
    ax2.grid(True, alpha=0.3, axis='y')
    
    # 3. Solar aprovechado
    ax3 = fig.add_subplot(gs[0, 2])
    episode_solar = trace.groupby('episode')['solar_generation_kwh'].sum()
    ax3.bar(episode_solar.index, episode_solar.values / 1e6, color='orange', alpha=0.7)
    ax3.set_xlabel('Episode', fontweight='bold')
    ax3.set_ylabel('Solar (M kWh)', fontweight='bold')
    ax3.set_title('Solar Generation by Episode', fontweight='bold', fontsize=11)
    ax3.grid(True, alpha=0.3, axis='y')
    
    # 4. Entropy
    ax4 = fig.add_subplot(gs[1, 0])
    valid_entropy = trace[trace['entropy'] > 0]
    ax4.plot(valid_entropy.index, valid_entropy['entropy'], color='green', linewidth=1.5, alpha=0.8)
    ax4.axhspan(50, 60, alpha=0.1, color='green')
    ax4.set_ylabel('Entropy', fontweight='bold')
    ax4.set_title('Policy Entropy', fontweight='bold', fontsize=11)
    ax4.grid(True, alpha=0.3)
    
    # 5. KL Divergence
    ax5 = fig.add_subplot(gs[1, 1])
    valid_kl = trace[trace['approx_kl'] > 0]
    ax5.plot(valid_kl.index, valid_kl['approx_kl'], color='blue', linewidth=1.5, alpha=0.8)
    ax5.axhline(y=0.01, color='red', linestyle='--', linewidth=2, alpha=0.7)
    ax5.set_ylabel('KL Divergence', fontweight='bold')
    ax5.set_title('KL Stability', fontweight='bold', fontsize=11)
    ax5.grid(True, alpha=0.3)
    
    # 6. Clip Fraction
    ax6 = fig.add_subplot(gs[1, 2])
    valid_clip = trace[trace['clip_fraction'] >= 0]
    ax6.plot(valid_clip.index, valid_clip['clip_fraction'] * 100, color='orange', linewidth=1.5, alpha=0.8)
    ax6.axhspan(2, 5, alpha=0.1, color='green')
    ax6.set_ylabel('Clip Fraction (%)', fontweight='bold')
    ax6.set_title('Clipping Rate', fontweight='bold', fontsize=11)
    ax6.grid(True, alpha=0.3)
    
    # 7. Value Loss
    ax7 = fig.add_subplot(gs[2, 0])
    valid_value = trace[trace['value_loss'] >= 0]
    ax7.plot(valid_value.index, valid_value['value_loss'], color='red', linewidth=1.5, alpha=0.8)
    ax7.set_ylabel('Value Loss', fontweight='bold')
    ax7.set_xlabel('Timestep', fontweight='bold')
    ax7.set_title('Value Function Loss', fontweight='bold', fontsize=11)
    ax7.grid(True, alpha=0.3)
    
    # 8. Explained Variance
    ax8 = fig.add_subplot(gs[2, 1])
    valid_expvar = trace[trace['explained_variance'] >= -1]
    ax8.plot(valid_expvar.index, valid_expvar['explained_variance'], color='purple', linewidth=1.5, alpha=0.8)
    ax8.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.5)
    ax8.set_ylabel('Explained Variance', fontweight='bold')
    ax8.set_xlabel('Timestep', fontweight='bold')
    ax8.set_title('Value Function Convergence', fontweight='bold', fontsize=11)
    ax8.grid(True, alpha=0.3)
    
    # 9. Resumen textual
    ax9 = fig.add_subplot(gs[2, 2])
    ax9.axis('off')
    
    # Calcular estadísticas
    total_episodes = trace['episode'].max() + 1
    total_steps = len(trace)
    mean_reward = trace['reward'].mean()
    mean_entropy = trace[trace['entropy'] > 0]['entropy'].mean()
    mean_kl = trace[trace['approx_kl'] > 0]['approx_kl'].mean()
    # Usar columnas disponibles
    if 'co2_avoided_total' in trace.columns:
        total_co2 = trace['co2_avoided_total'].sum()
    else:
        total_co2 = (trace['co2_avoided_indirect_kg'] + trace['co2_avoided_direct_kg']).sum()
    
    summary_text = f"""
PPO v9.3 TRAINING SUMMARY

Episodes: {int(total_episodes)}
Total Timesteps: {total_steps:,}

Mean Reward: {mean_reward:.4f}
Mean Entropy: {mean_entropy:.2f}
Mean KL: {mean_kl:.5f}

Total CO2 Avoided: {total_co2/1e6:.1f}M kg

Status: ✓ SUCCESS
"""
    
    ax9.text(0.1, 0.5, summary_text, fontsize=10, family='monospace',
             verticalalignment='center', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.suptitle('PPO v9.3 Training Dashboard', fontsize=14, fontweight='bold', y=0.995)
    
    plt.savefig('outputs/ppo_training/ppo_dashboard.png', dpi=150, bbox_inches='tight')
    print("  ✓ Guardado: ppo_dashboard.png")
    plt.close()

def main():
    print('='*80)
    print('REGENERANDO GRÁFICAS DE ENTRENAMIENTO PPO v9.3')
    print('='*80)
    print()
    
    # Crear directorio si no existe
    Path('outputs/ppo_training').mkdir(parents=True, exist_ok=True)
    
    # Cargar datos
    trace, result = load_data()
    
    print()
    print('Datos cargados:')
    print(f'  • Trace: {len(trace)} registros')
    print(f'  • Episodios: {int(trace["episode"].max()) + 1}')
    print()
    
    # Generar gráficas
    print('Generando gráficas...')
    print()
    
    plot_kl_divergence(trace)
    plot_clip_fraction(trace)
    plot_entropy(trace)
    plot_value_metrics(trace)
    plot_dashboard(trace, result)
    
    print()
    print('='*80)
    print('✅ TODAS LAS GRÁFICAS REGENERADAS EXITOSAMENTE')
    print('='*80)
    print()
    print('Archivos generados:')
    print('  • outputs/ppo_training/ppo_kl_divergence.png')
    print('  • outputs/ppo_training/ppo_clip_fraction.png')
    print('  • outputs/ppo_training/ppo_entropy.png')
    print('  • outputs/ppo_training/ppo_value_metrics.png')
    print('  • outputs/ppo_training/ppo_dashboard.png')
    print()

if __name__ == '__main__':
    main()
