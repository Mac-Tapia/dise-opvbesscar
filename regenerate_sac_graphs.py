#!/usr/bin/env python3
"""
Regenerar gráficas de entrenamiento SAC v9.0
Basadas en outputs/sac_training/trace_sac.csv
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
    """Cargar datos de entrenamiento SAC"""
    print("Cargando datos de SAC...")
    trace = pd.read_csv('outputs/sac_training/trace_sac.csv')
    
    with open('outputs/sac_training/result_sac.json') as f:
        result = json.load(f)
    
    return trace, result

def plot_cumulative_reward(trace):
    """Gráfica de Cumulative Reward"""
    print("Generando: Cumulative Reward...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Filtrar valores válidos
    if 'cumulative_reward' in trace.columns:
        valid_data = trace[trace['cumulative_reward'].notna()].copy()
    else:
        valid_data = trace.copy()
        valid_data['cumulative_reward'] = trace['reward'].cumsum()
    
    if len(valid_data) > 0:
        # Línea de cumulative reward
        ax.plot(valid_data.index, valid_data['cumulative_reward'], 
                label='Cumulative Reward', color='#1f77b4', linewidth=1.5, alpha=0.8)
        
        # Media móvil de reward instantáneo (100 timesteps)
        if 'reward' in trace.columns:
            ma_instant = trace['reward'].rolling(window=100).mean()
            ax.plot(trace.index, ma_instant, 
                    label='Reward (100-step MA)', color='darkblue', linewidth=2, alpha=0.6)
        
        ax.set_xlabel('Timestep', fontsize=11, fontweight='bold')
        ax.set_ylabel('Cumulative Reward', fontsize=11, fontweight='bold')
        ax.set_title('Reward Accumulation During SAC v9.0 Training', fontsize=13, fontweight='bold')
        ax.legend(loc='upper left', fontsize=10)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('outputs/sac_training/sac_cumulative_reward.png', dpi=150, bbox_inches='tight')
    print("  ✓ Guardado: sac_cumulative_reward.png")
    plt.close()

def plot_co2_avoided(trace):
    """Gráfica de CO2 Avoided (cumulative)"""
    print("Generando: CO2 Avoided...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Filtrar valores válidos
    if 'co2_grid_kg' in trace.columns:
        valid_data = trace[trace['co2_grid_kg'].notna()].copy()
    else:
        plt.close()
        print("  ⚠ No CO2 data found")
        return
    
    if len(valid_data) > 0:
        # CO2 evitado acumulativo (sum of all grid CO2 avoided)
        cumsum_co2 = valid_data['co2_grid_kg'].cumsum()
        ax.plot(valid_data.index, cumsum_co2 / 1e6, 
                label='Cumulative CO2 Avoided', color='#d62728', linewidth=1.5, alpha=0.8)
        
        # Media móvil
        if len(valid_data) > 100:
            ma = valid_data['co2_grid_kg'].rolling(window=100).mean()
            ax.plot(valid_data.index, ma, 
                    label='Moving Avg CO2 (100 steps)', color='darkred', linewidth=2, alpha=0.6)
        
        ax.set_xlabel('Timestep', fontsize=11, fontweight='bold')
        ax.set_ylabel('CO2 Avoided (M kg)', fontsize=11, fontweight='bold')
        ax.set_title('CO2 Avoided During SAC v9.0 Training', fontsize=13, fontweight='bold')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('outputs/sac_training/sac_co2_avoided.png', dpi=150, bbox_inches='tight')
    print("  ✓ Guardado: sac_co2_avoided.png")
    plt.close()

def plot_solar_generation(trace):
    """Gráfica de Solar Generation y utilization"""
    print("Generando: Solar Generation...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Filtrar valores válidos
    if 'solar_generation_kwh' in trace.columns:
        valid_data = trace[trace['solar_generation_kwh'] > 0].copy()
    else:
        plt.close()
        print("  ⚠ No solar data found")
        return
    
    if len(valid_data) > 0:
        # Línea de generación solar
        ax.plot(valid_data.index, valid_data['solar_generation_kwh'], 
                label='Solar Generation', color='#2ca02c', linewidth=1.5, alpha=0.8)
        
        # Acumulativo solar
        cumsum_solar = valid_data['solar_generation_kwh'].cumsum()
        ax2 = ax.twinx()
        ax2.plot(valid_data.index, cumsum_solar / 1e6, 
                label='Cumulative Solar', color='darkgreen', linewidth=2, alpha=0.6, linestyle='--')
        ax2.set_ylabel('Cumulative Solar (M kWh)', fontsize=11, fontweight='bold')
        
        ax.set_xlabel('Timestep', fontsize=11, fontweight='bold')
        ax.set_ylabel('Solar Generation (kWh)', fontsize=11, fontweight='bold')
        ax.set_title('Solar Generation During SAC v9.0 Training', fontsize=13, fontweight='bold')
        ax.legend(loc='upper left', fontsize=10)
        ax2.legend(loc='upper center', fontsize=10)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('outputs/sac_training/sac_solar_generation.png', dpi=150, bbox_inches='tight')
    print("  ✓ Guardado: sac_solar_generation.png")
    plt.close()

def plot_bess_management(trace):
    """Gráfica de BESS SOC (State of Charge) management"""
    print("Generando: BESS Management...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Filtrar valores válidos
    if 'bess_soc' in trace.columns:
        valid_data = trace[trace['bess_soc'].notna()].copy()
    else:
        plt.close()
        print("  ⚠ No BESS data found")
        return
    
    if len(valid_data) > 0:
        # Línea de BESS SOC
        ax.plot(valid_data.index, valid_data['bess_soc'], 
                label='BESS SOC %', color='#ff7f0e', linewidth=1.5, alpha=0.8)
        
        # Zonas de operación
        ax.axhspan(0, 20, alpha=0.1, color='red', label='Critical (<20%)')
        ax.axhspan(20, 50, alpha=0.1, color='yellow', label='Low (20-50%)')
        ax.axhspan(50, 100, alpha=0.1, color='green', label='Healthy (>50%)')
        
        # Media móvil
        if len(valid_data) > 100:
            ma = valid_data['bess_soc'].rolling(window=100).mean()
            ax.plot(valid_data.index, ma, 
                    label='Moving Avg (100 steps)', color='darkorange', linewidth=2, alpha=0.6)
        
        ax.set_xlabel('Timestep', fontsize=11, fontweight='bold')
        ax.set_ylabel('BESS SOC (%)', fontsize=11, fontweight='bold')
        ax.set_title('BESS State of Charge During SAC v9.0 Training', fontsize=13, fontweight='bold')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_ylim([0, 105])
    
    plt.tight_layout()
    plt.savefig('outputs/sac_training/sac_bess_management.png', dpi=150, bbox_inches='tight')
    print("  ✓ Guardado: sac_bess_management.png")
    plt.close()

def plot_grid_import(trace):
    """Gráfica de Grid Import optimization"""
    print("Generando: Grid Import...")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Filtrar valores válidos
    if 'grid_import_kwh' in trace.columns:
        valid_data = trace[trace['grid_import_kwh'].notna()].copy()
    else:
        plt.close()
        print("  ⚠ No grid import data found")
        return
    
    if len(valid_data) > 0:
        # Línea de grid import
        ax.plot(valid_data.index, valid_data['grid_import_kwh'], 
                label='Grid Import', color='#9467bd', linewidth=1, alpha=0.6)
        
        # Media móvil (500 timesteps para ver tendencia)
        if len(valid_data) > 500:
            ma = valid_data['grid_import_kwh'].rolling(window=500).mean()
            ax.plot(valid_data.index, ma, 
                    label='Moving Avg (500 steps)', color='purple', linewidth=2.5, alpha=0.8)
        
        ax.set_xlabel('Timestep', fontsize=11, fontweight='bold')
        ax.set_ylabel('Grid Import (kWh)', fontsize=11, fontweight='bold')
        ax.set_title('Grid Import Optimization During SAC v9.0 Training', fontsize=13, fontweight='bold')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('outputs/sac_training/sac_grid_import.png', dpi=150, bbox_inches='tight')
    print("  ✓ Guardado: sac_grid_import.png")
    plt.close()

def plot_dashboard(trace, result):
    """Dashboard integrado con múltiples métricas SAC"""
    print("Generando: Dashboard SAC...")
    
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    # 1. Reward por episodio
    ax1 = fig.add_subplot(gs[0, 0])
    if 'episode' in trace.columns:
        episode_rewards = trace.groupby('episode')['reward'].mean()
        ax1.bar(episode_rewards.index, episode_rewards.values, color='skyblue', alpha=0.7)
        ax1.set_xlabel('Episode', fontweight='bold')
        ax1.set_ylabel('Avg Reward', fontweight='bold')
        ax1.set_title('Reward by Episode', fontweight='bold', fontsize=11)
        ax1.grid(True, alpha=0.3, axis='y')
    
    # 2. Cumulative Reward
    ax2 = fig.add_subplot(gs[0, 1])
    if 'cumulative_reward' in trace.columns:
        valid_cum = trace[trace['cumulative_reward'].notna()]
        if len(valid_cum) > 0:
            ax2.plot(valid_cum.index, valid_cum['cumulative_reward'], color='blue', linewidth=1.5, alpha=0.8)
            ax2.set_ylabel('Cumulative Reward', fontweight='bold')
            ax2.set_title('Cumulative Reward', fontweight='bold', fontsize=11)
            ax2.grid(True, alpha=0.3)
    
    # 3. CO2 Avoided
    ax3 = fig.add_subplot(gs[0, 2])
    if 'co2_grid_kg' in trace.columns:
        valid_co2 = trace[trace['co2_grid_kg'].notna()]
        if len(valid_co2) > 0:
            cumsum_co2 = valid_co2['co2_grid_kg'].cumsum()
            ax3.plot(valid_co2.index, cumsum_co2 / 1e6, color='red', linewidth=1.5, alpha=0.8)
            ax3.set_ylabel('CO2 Avoided (M kg)', fontweight='bold')
            ax3.set_title('CO2 Reduction', fontweight='bold', fontsize=11)
            ax3.grid(True, alpha=0.3)
    
    # 4. Solar Generation
    ax4 = fig.add_subplot(gs[1, 0])
    if 'solar_generation_kwh' in trace.columns:
        valid_solar = trace[trace['solar_generation_kwh'] > 0]
        if len(valid_solar) > 0:
            ax4.plot(valid_solar.index, valid_solar['solar_generation_kwh'], color='green', linewidth=1.5, alpha=0.8)
            ax4.set_ylabel('Solar Generation (kWh)', fontweight='bold')
            ax4.set_title('Solar Output', fontweight='bold', fontsize=11)
            ax4.grid(True, alpha=0.3)
    
    # 5. EV Charging
    ax5 = fig.add_subplot(gs[1, 1])
    if 'ev_charging_kwh' in trace.columns:
        valid_ev = trace[trace['ev_charging_kwh'].notna()]
        if len(valid_ev) > 0:
            cumsum_ev = valid_ev['ev_charging_kwh'].cumsum()
            ax5.plot(valid_ev.index, cumsum_ev / 1e6, color='orange', linewidth=1.5, alpha=0.8)
            ax5.set_ylabel('Cumulative EV Energy (M kWh)', fontweight='bold')
            ax5.set_title('EV Charging Progress', fontweight='bold', fontsize=11)
            ax5.grid(True, alpha=0.3)
    
    # 6. BESS SOC
    ax6 = fig.add_subplot(gs[1, 2])
    if 'bess_soc' in trace.columns:
        valid_bess = trace[trace['bess_soc'].notna()]
        if len(valid_bess) > 0:
            ax6.plot(valid_bess.index, valid_bess['bess_soc'], color='purple', linewidth=1.5, alpha=0.8)
            ax6.axhspan(0, 20, alpha=0.1, color='red')
            ax6.axhspan(50, 100, alpha=0.1, color='green')
            ax6.set_ylabel('BESS SOC (%)', fontweight='bold')
            ax6.set_title('Battery Management', fontweight='bold', fontsize=11)
            ax6.grid(True, alpha=0.3)
            ax6.set_ylim([0, 105])
    
    # 7. Grid Import
    ax7 = fig.add_subplot(gs[2, 0])
    if 'grid_import_kwh' in trace.columns:
        valid_grid = trace[trace['grid_import_kwh'].notna()]
        if len(valid_grid) > 0:
            ax7.plot(valid_grid.index, valid_grid['grid_import_kwh'], color='navy', linewidth=0.5, alpha=0.5)
            if len(valid_grid) > 500:
                ma = valid_grid['grid_import_kwh'].rolling(window=500).mean()
                ax7.plot(valid_grid.index, ma, color='darkblue', linewidth=2, alpha=0.8)
            ax7.set_ylabel('Grid Import (kWh)', fontweight='bold')
            ax7.set_xlabel('Timestep', fontweight='bold')
            ax7.set_title('Grid Import Trend', fontweight='bold', fontsize=11)
            ax7.grid(True, alpha=0.3)
    
    # 8. Reward Trend
    ax8 = fig.add_subplot(gs[2, 1])
    if 'reward' in trace.columns:
        valid_reward = trace[trace['reward'].notna()]
        if len(valid_reward) > 0:
            ax8.plot(valid_reward.index, valid_reward['reward'], color='cyan', linewidth=0.5, alpha=0.5)
            if len(valid_reward) > 500:
                ma = valid_reward['reward'].rolling(window=500).mean()
                ax8.plot(valid_reward.index, ma, color='darkblue', linewidth=2, alpha=0.8)
            ax8.set_ylabel('Reward', fontweight='bold')
            ax8.set_xlabel('Timestep', fontweight='bold')
            ax8.set_title('Reward Convergence', fontweight='bold', fontsize=11)
            ax8.grid(True, alpha=0.3)
    
    # 9. Resumen textual
    ax9 = fig.add_subplot(gs[2, 2])
    ax9.axis('off')
    
    # Calcular estadísticas
    total_episodes = trace['episode'].max() + 1 if 'episode' in trace.columns else 1
    total_steps = len(trace)
    mean_reward = trace['reward'].mean() if 'reward' in trace.columns else 0
    
    # CO2
    total_co2 = trace['co2_grid_kg'].sum() if 'co2_grid_kg' in trace.columns else 0
    
    # Solar
    total_solar = trace['solar_generation_kwh'].sum() if 'solar_generation_kwh' in trace.columns else 0
    
    # EV
    total_ev = trace['ev_charging_kwh'].sum() if 'ev_charging_kwh' in trace.columns else 0
    
    # BESS
    mean_bess = trace['bess_soc'].mean() if 'bess_soc' in trace.columns else 0
    
    summary_text = f"""
SAC v9.0 TRAINING SUMMARY

Episodes: {int(total_episodes)}
Total Timesteps: {total_steps:,}

Mean Reward: {mean_reward:.4f}
Total CO2 Avoided: {total_co2/1e6:.1f}M kg
Total Solar: {total_solar/1e6:.1f}M kWh
Total EV Energy: {total_ev/1e3:.1f}k kWh
Mean BESS SOC: {mean_bess:.1f}%

Status: ✓ SUCCESS
"""
    
    ax9.text(0.1, 0.5, summary_text, fontsize=10, family='monospace',
             verticalalignment='center', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))
    
    plt.suptitle('SAC v9.0 Training Dashboard', fontsize=14, fontweight='bold', y=0.995)
    
    plt.savefig('outputs/sac_training/sac_dashboard_regenerated.png', dpi=150, bbox_inches='tight')
    print("  ✓ Guardado: sac_dashboard_regenerated.png")
    plt.close()

def main():
    print('='*80)
    print('REGENERANDO GRÁFICAS DE ENTRENAMIENTO SAC v9.0')
    print('='*80)
    print()
    
    # Crear directorio si no existe
    Path('outputs/sac_training').mkdir(parents=True, exist_ok=True)
    
    # Cargar datos
    trace, result = load_data()
    
    print()
    print('Datos cargados:')
    print(f'  • Trace: {len(trace)} registros')
    if 'episode' in trace.columns:
        print(f'  • Episodios: {int(trace["episode"].max()) + 1}')
    print(f'  • Columnas disponibles: {list(trace.columns)}')
    print()
    
    # Generar gráficas
    print('Generando gráficas...')
    print()
    
    plot_cumulative_reward(trace)
    plot_co2_avoided(trace)
    plot_solar_generation(trace)
    plot_bess_management(trace)
    plot_grid_import(trace)
    plot_dashboard(trace, result)
    
    print()
    print('='*80)
    print('✅ TODAS LAS GRÁFICAS SAC REGENERADAS EXITOSAMENTE')
    print('='*80)
    print()
    print('Archivos generados:')
    print('  • outputs/sac_training/sac_cumulative_reward.png')
    print('  • outputs/sac_training/sac_co2_avoided.png')
    print('  • outputs/sac_training/sac_solar_generation.png')
    print('  • outputs/sac_training/sac_bess_management.png')
    print('  • outputs/sac_training/sac_grid_import.png')
    print('  • outputs/sac_training/sac_dashboard_regenerated.png')
    print()

if __name__ == '__main__':
    main()
