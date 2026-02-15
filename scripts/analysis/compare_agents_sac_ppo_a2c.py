#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COMPARAR AGENTES SAC vs PPO vs A2C - Analisis Completo
================================================================================
Script para comparar el desempeno, eficiencia y salud de los tres agentes RL
entrenados para optimizacion de carga EV en Iquitos, Peru.

METRICAS COMPARADAS:
====================
1. DESEMPENO:
   - Eval episodic return vs environment steps (sample efficiency)
   - Success rate (% episodios con reward > threshold)
   - Episodic length

2. EFICIENCIA:
   - Wall-clock time (tiempo real de entrenamiento)
   - Sample efficiency (return por timestep)

3. SALUD INTERNA (especifica por algoritmo):
   - SAC: actor_loss, critic_loss, alpha, entropy, mean_Q
   - PPO: KL, clip_fraction, entropy, value_loss, explained_variance
   - A2C: entropy, value_loss, explained_variance, grad_norm

4. COMPARACION CARA A CARA:
   - Sample efficiency: Return vs Steps (3 curvas)
   - Estabilidad: Variance/IC sombreado
   - Distribucion final: Boxplot del return final

Referencias:
  [1] Henderson et al. (2018) "Deep Reinforcement Learning That Matters"
  [2] Stable-Baselines3 Documentation
  [3] CityLearn v2 Benchmark

Uso:
  python scripts/analysis/compare_agents_sac_ppo_a2c.py
  python scripts/analysis/compare_agents_sac_ppo_a2c.py --output-dir outputs/comparison
================================================================================
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use('Agg')  # Backend sin GUI
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Configurar warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# ============================================================================
# CONFIGURACION
# ============================================================================

@dataclass
class AgentMetrics:
    """Contenedor de metricas para un agente."""
    name: str
    color: str
    marker: str
    
    # Metricas de desempeno
    steps: List[int] = field(default_factory=list)
    returns: List[float] = field(default_factory=list)
    episode_lengths: List[int] = field(default_factory=list)
    
    # Metricas de salud (genericas)
    entropy: List[float] = field(default_factory=list)
    value_loss: List[float] = field(default_factory=list)
    
    # Metricas especificas SAC
    actor_loss: List[float] = field(default_factory=list)
    critic_loss: List[float] = field(default_factory=list)
    alpha: List[float] = field(default_factory=list)
    mean_q: List[float] = field(default_factory=list)
    
    # Metricas especificas PPO
    kl_divergence: List[float] = field(default_factory=list)
    clip_fraction: List[float] = field(default_factory=list)
    explained_variance: List[float] = field(default_factory=list)
    
    # Metricas especificas A2C
    policy_loss: List[float] = field(default_factory=list)
    grad_norm: List[float] = field(default_factory=list)
    
    # Metadata
    wall_clock_time_s: float = 0.0
    total_timesteps: int = 0
    final_return: float = 0.0
    
    # KPIs CityLearn
    co2_emissions: List[float] = field(default_factory=list)
    electricity_cost: List[float] = field(default_factory=list)
    ramping: List[float] = field(default_factory=list)


# Colores y estilos por agente
AGENT_STYLES = {
    'SAC': {'color': '#2ecc71', 'marker': 'o', 'linestyle': '-'},   # Verde
    'PPO': {'color': '#3498db', 'marker': 's', 'linestyle': '--'},  # Azul
    'A2C': {'color': '#e74c3c', 'marker': '^', 'linestyle': '-.'},  # Rojo
}


# ============================================================================
# CARGA DE DATOS
# ============================================================================

def load_agent_metrics(agent_name: str, output_dir: Path) -> Optional[AgentMetrics]:
    """
    Carga metricas de un agente desde archivos de salida.
    
    Busca en:
    - outputs/{agent}_training/metrics.csv
    - outputs/{agent}_training/training_log.json
    - checkpoints/{agent}/metadata.json
    """
    agent_lower = agent_name.lower()
    possible_dirs = [
        output_dir / f'{agent_lower}_training',
        output_dir.parent / f'{agent_lower}_training',
        Path(f'outputs/{agent_lower}_training'),
    ]
    
    metrics = AgentMetrics(
        name=agent_name,
        color=AGENT_STYLES[agent_name]['color'],
        marker=AGENT_STYLES[agent_name]['marker'],
    )
    
    data_found = False
    
    for agent_dir in possible_dirs:
        if not agent_dir.exists():
            continue
        
        # Buscar CSV de metricas
        metrics_csv = agent_dir / 'metrics.csv'
        if metrics_csv.exists():
            df = pd.read_csv(metrics_csv)
            data_found = True
            
            # Extraer columnas disponibles
            if 'step' in df.columns or 'timestep' in df.columns:
                col = 'step' if 'step' in df.columns else 'timestep'
                metrics.steps = df[col].tolist()
            
            if 'return' in df.columns or 'episode_return' in df.columns:
                col = 'return' if 'return' in df.columns else 'episode_return'
                metrics.returns = df[col].tolist()
            
            if 'entropy' in df.columns:
                metrics.entropy = df['entropy'].tolist()
            
            if 'value_loss' in df.columns:
                metrics.value_loss = df['value_loss'].tolist()
            
            # SAC especifico
            if 'actor_loss' in df.columns:
                metrics.actor_loss = df['actor_loss'].tolist()
            if 'critic_loss' in df.columns:
                metrics.critic_loss = df['critic_loss'].tolist()
            if 'alpha' in df.columns:
                metrics.alpha = df['alpha'].tolist()
            if 'mean_q' in df.columns:
                metrics.mean_q = df['mean_q'].tolist()
            
            # PPO especifico
            if 'kl_divergence' in df.columns or 'approx_kl' in df.columns:
                col = 'kl_divergence' if 'kl_divergence' in df.columns else 'approx_kl'
                metrics.kl_divergence = df[col].tolist()
            if 'clip_fraction' in df.columns:
                metrics.clip_fraction = df['clip_fraction'].tolist()
            if 'explained_variance' in df.columns:
                metrics.explained_variance = df['explained_variance'].tolist()
            
            # A2C especifico
            if 'policy_loss' in df.columns:
                metrics.policy_loss = df['policy_loss'].tolist()
            if 'grad_norm' in df.columns:
                metrics.grad_norm = df['grad_norm'].tolist()
            
            # KPIs CityLearn
            if 'co2_emissions' in df.columns:
                metrics.co2_emissions = df['co2_emissions'].tolist()
            if 'electricity_cost' in df.columns:
                metrics.electricity_cost = df['electricity_cost'].tolist()
        
        # Buscar JSON de metadatos
        json_files = list(agent_dir.glob('*.json'))
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if 'wall_clock_time' in data:
                    metrics.wall_clock_time_s = data['wall_clock_time']
                if 'total_timesteps' in data:
                    metrics.total_timesteps = data['total_timesteps']
                if 'final_return' in data:
                    metrics.final_return = data['final_return']
            except (json.JSONDecodeError, KeyError):
                pass
        
        if data_found:
            break
    
    if not data_found:
        print(f'  [!]  No se encontraron datos para {agent_name}')
        return None
    
    # Calcular metricas derivadas
    if metrics.returns:
        metrics.final_return = np.mean(metrics.returns[-10:]) if len(metrics.returns) >= 10 else metrics.returns[-1]
    if metrics.steps:
        metrics.total_timesteps = max(metrics.steps)
    
    print(f'  [OK] {agent_name}: {len(metrics.returns)} episodios, {metrics.total_timesteps:,} steps')
    return metrics


def generate_synthetic_data_for_demo() -> Dict[str, AgentMetrics]:
    """
    Genera datos sinteticos para demostracion si no hay datos reales.
    Basado en comportamiento tipico de SAC/PPO/A2C en problemas de control.
    """
    print('  ℹ️  Generando datos sinteticos para demostracion...')
    
    np.random.seed(42)
    n_points = 100
    steps = np.linspace(0, 87600, n_points).astype(int)  # 10 episodios
    
    agents = {}
    
    # SAC: Tipicamente mejor sample efficiency, curva mas suave
    sac = AgentMetrics(name='SAC', color=AGENT_STYLES['SAC']['color'], marker='o')
    sac.steps = steps.tolist()
    base_return = -500 + 400 * (1 - np.exp(-steps / 30000))  # Curva de aprendizaje
    sac.returns = (base_return + np.random.normal(0, 30, n_points)).tolist()
    sac.entropy = (2.0 * np.exp(-steps / 50000) + 0.5 + np.random.normal(0, 0.1, n_points)).tolist()
    sac.alpha = (0.2 * np.exp(-steps / 40000) + 0.05 + np.random.normal(0, 0.01, n_points)).tolist()
    sac.actor_loss = (-0.5 + np.random.normal(0, 0.2, n_points)).tolist()
    sac.critic_loss = (5.0 * np.exp(-steps / 30000) + 0.5 + np.random.normal(0, 0.3, n_points)).tolist()
    sac.mean_q = (100 + 200 * (1 - np.exp(-steps / 25000)) + np.random.normal(0, 20, n_points)).tolist()
    sac.wall_clock_time_s = 3600 * 5  # 5 horas
    sac.total_timesteps = 87600
    sac.final_return = float(np.mean(sac.returns[-10:]))
    agents['SAC'] = sac
    
    # PPO: On-policy, menos sample efficient pero estable
    ppo = AgentMetrics(name='PPO', color=AGENT_STYLES['PPO']['color'], marker='s')
    ppo.steps = steps.tolist()
    base_return = -550 + 380 * (1 - np.exp(-steps / 35000))  # Mas lento que SAC
    ppo.returns = (base_return + np.random.normal(0, 40, n_points)).tolist()
    ppo.entropy = (3.0 * np.exp(-steps / 60000) + 0.3 + np.random.normal(0, 0.15, n_points)).tolist()
    ppo.kl_divergence = (0.02 + np.random.exponential(0.01, n_points)).tolist()
    ppo.clip_fraction = (0.1 + 0.15 * np.exp(-steps / 40000) + np.random.normal(0, 0.03, n_points)).tolist()
    ppo.value_loss = (10.0 * np.exp(-steps / 25000) + 1.0 + np.random.normal(0, 0.5, n_points)).tolist()
    ppo.explained_variance = (0.3 + 0.6 * (1 - np.exp(-steps / 30000)) + np.random.normal(0, 0.05, n_points)).tolist()
    ppo.wall_clock_time_s = 3600 * 4  # 4 horas
    ppo.total_timesteps = 87600
    ppo.final_return = float(np.mean(ppo.returns[-10:]))
    agents['PPO'] = ppo
    
    # A2C: Mas rapido pero con mas varianza
    a2c = AgentMetrics(name='A2C', color=AGENT_STYLES['A2C']['color'], marker='^')
    a2c.steps = steps.tolist()
    base_return = -600 + 350 * (1 - np.exp(-steps / 40000))  # Mas lento y con mas varianza
    a2c.returns = (base_return + np.random.normal(0, 60, n_points)).tolist()
    a2c.entropy = (2.5 * np.exp(-steps / 45000) + 0.4 + np.random.normal(0, 0.2, n_points)).tolist()
    a2c.value_loss = (8.0 * np.exp(-steps / 20000) + 0.8 + np.random.normal(0, 0.4, n_points)).tolist()
    a2c.explained_variance = (0.2 + 0.5 * (1 - np.exp(-steps / 35000)) + np.random.normal(0, 0.08, n_points)).tolist()
    a2c.policy_loss = (-1.0 + np.random.normal(0, 0.3, n_points)).tolist()
    a2c.grad_norm = (2.0 + np.random.exponential(0.5, n_points)).tolist()
    a2c.wall_clock_time_s = 3600 * 3  # 3 horas (mas rapido)
    a2c.total_timesteps = 87600
    a2c.final_return = float(np.mean(a2c.returns[-10:]))
    agents['A2C'] = a2c
    
    return agents


# ============================================================================
# FUNCIONES DE GRAFICAS
# ============================================================================

def smooth(data: List[float], window: int = 10) -> np.ndarray:
    """Suavizado con media movil."""
    if len(data) < window:
        return np.array(data)
    return pd.Series(data).rolling(window=window, center=True, min_periods=1).mean().values


def plot_sample_efficiency(agents: Dict[str, AgentMetrics], output_dir: Path) -> None:
    """
    Grafica 1: Sample Efficiency - Return vs Steps
    Curva principal de comparacion entre los tres agentes.
    """
    fig, ax = plt.subplots(figsize=(12, 7))
    
    for name, metrics in agents.items():
        if not metrics.returns or not metrics.steps:
            continue
        
        steps_k = np.array(metrics.steps) / 1000
        returns = np.array(metrics.returns)
        
        # Linea principal (suavizada)
        smoothed = smooth(returns.tolist(), window=5)
        ax.plot(steps_k, smoothed, 
                color=metrics.color,
                linestyle=AGENT_STYLES[name]['linestyle'],
                linewidth=2.5,
                label=f'{name} (final: {metrics.final_return:.1f})')
        
        # Banda de confianza (std movil)
        if len(returns) > 10:
            std = pd.Series(returns).rolling(window=10, center=True, min_periods=1).std().values
            ax.fill_between(steps_k, smoothed - std, smoothed + std, 
                           color=metrics.color, alpha=0.15)
    
    ax.set_xlabel('Environment Steps (K)', fontsize=12)
    ax.set_ylabel('Episode Return', fontsize=12)
    ax.set_title('Sample Efficiency: Return vs Training Steps\n(SAC vs PPO vs A2C)', fontsize=14)
    ax.legend(loc='lower right', fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='gray', linestyle=':', alpha=0.5)
    
    # Anotar mejor agente
    final_returns = {n: m.final_return for n, m in agents.items() if m.returns}
    if final_returns:
        best = max(final_returns, key=final_returns.get)
        ax.annotate(f'Best: {best}', xy=(0.98, 0.98), xycoords='axes fraction',
                   fontsize=10, ha='right', va='top',
                   bbox=dict(boxstyle='round', facecolor=AGENT_STYLES[best]['color'], alpha=0.3))
    
    plt.tight_layout()
    plt.savefig(output_dir / '01_sample_efficiency.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  [OK] 01_sample_efficiency.png')


def plot_entropy_comparison(agents: Dict[str, AgentMetrics], output_dir: Path) -> None:
    """
    Grafica 2: Entropy vs Steps (comun a los tres)
    Medida de exploracion durante el entrenamiento.
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for name, metrics in agents.items():
        if not metrics.entropy or not metrics.steps:
            continue
        
        steps_k = np.array(metrics.steps[:len(metrics.entropy)]) / 1000
        entropy = np.array(metrics.entropy)
        
        smoothed = smooth(entropy.tolist(), window=5)
        ax.plot(steps_k, smoothed,
                color=metrics.color,
                linestyle=AGENT_STYLES[name]['linestyle'],
                linewidth=2,
                label=f'{name}')
    
    ax.set_xlabel('Environment Steps (K)', fontsize=12)
    ax.set_ylabel('Entropy', fontsize=12)
    ax.set_title('Entropy vs Training Steps\n(Medida de exploracion - menor = mas deterministico)', fontsize=14)
    ax.legend(loc='upper right', fontsize=11)
    ax.grid(True, alpha=0.3)
    
    # Linea de warning (entropy muy baja)
    ax.axhline(y=0.1, color='red', linestyle=':', alpha=0.5, label='Warning: Entropy < 0.1')
    
    plt.tight_layout()
    plt.savefig(output_dir / '02_entropy_comparison.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  [OK] 02_entropy_comparison.png')


def plot_value_loss_comparison(agents: Dict[str, AgentMetrics], output_dir: Path) -> None:
    """
    Grafica 3: Value Loss vs Steps (PPO y A2C principalmente)
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    has_data = False
    for name, metrics in agents.items():
        data = metrics.value_loss if metrics.value_loss else metrics.critic_loss
        if not data or not metrics.steps:
            continue
        
        has_data = True
        steps_k = np.array(metrics.steps[:len(data)]) / 1000
        values = np.array(data)
        
        smoothed = smooth(values.tolist(), window=5)
        ax.plot(steps_k, smoothed,
                color=metrics.color,
                linestyle=AGENT_STYLES[name]['linestyle'],
                linewidth=2,
                label=f'{name}')
    
    if not has_data:
        plt.close(fig)
        return
    
    ax.set_xlabel('Environment Steps (K)', fontsize=12)
    ax.set_ylabel('Value/Critic Loss', fontsize=12)
    ax.set_title('Value/Critic Loss vs Training Steps\n(Que tan bien el critico predice returns)', fontsize=14)
    ax.legend(loc='upper right', fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_yscale('log')  # Log scale para mejor visualizacion
    
    plt.tight_layout()
    plt.savefig(output_dir / '03_value_loss_comparison.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  [OK] 03_value_loss_comparison.png')


def plot_final_return_boxplot(agents: Dict[str, AgentMetrics], output_dir: Path) -> None:
    """
    Grafica 4: Boxplot/Violin del return final (ultimo 10% del entrenamiento)
    """
    fig, ax = plt.subplots(figsize=(10, 7))
    
    data_for_plot = []
    labels = []
    colors = []
    
    for name, metrics in agents.items():
        if not metrics.returns:
            continue
        
        # Ultimo 10% de los returns
        n_final = max(1, len(metrics.returns) // 10)
        final_returns = metrics.returns[-n_final:]
        
        data_for_plot.append(final_returns)
        labels.append(name)
        colors.append(metrics.color)
    
    if not data_for_plot:
        plt.close(fig)
        return
    
    # Crear violin plot
    parts = ax.violinplot(data_for_plot, positions=range(len(labels)), showmeans=True, showmedians=True)
    
    # Colorear cada violin
    for i, pc in enumerate(parts['bodies']):
        pc.set_facecolor(colors[i])
        pc.set_alpha(0.6)
    
    # Anadir boxplot superpuesto
    bp = ax.boxplot(data_for_plot, positions=range(len(labels)), widths=0.15, 
                    patch_artist=True, showfliers=False)
    for i, patch in enumerate(bp['boxes']):
        patch.set_facecolor(colors[i])
        patch.set_alpha(0.8)
    
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=12)
    ax.set_ylabel('Episode Return', fontsize=12)
    ax.set_title('Distribucion de Returns Finales\n(Ultimo 10% del entrenamiento)', fontsize=14)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Anotar medias
    for i, data in enumerate(data_for_plot):
        mean_val = np.mean(data)
        std_val = np.std(data)
        ax.annotate(f'μ={mean_val:.1f}\nσ={std_val:.1f}', 
                   xy=(i, mean_val), xytext=(i + 0.3, mean_val),
                   fontsize=9, ha='left')
    
    plt.tight_layout()
    plt.savefig(output_dir / '04_final_return_distribution.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  [OK] 04_final_return_distribution.png')


def plot_wall_clock_comparison(agents: Dict[str, AgentMetrics], output_dir: Path) -> None:
    """
    Grafica 5: Wall-clock time comparison (eficiencia computacional)
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    names = []
    times_hours = []
    returns_per_hour = []
    colors = []
    
    for name, metrics in agents.items():
        if metrics.wall_clock_time_s <= 0:
            continue
        
        names.append(name)
        hours = metrics.wall_clock_time_s / 3600
        times_hours.append(hours)
        
        # Return por hora de entrenamiento
        rph = metrics.final_return / max(hours, 0.001)
        returns_per_hour.append(rph)
        colors.append(metrics.color)
    
    if not names:
        plt.close(fig)
        return
    
    # Subplot 1: Tiempo total
    bars1 = ax1.bar(names, times_hours, color=colors, alpha=0.7, edgecolor='black')
    ax1.set_ylabel('Wall-clock Time (hours)', fontsize=12)
    ax1.set_title('Training Time Comparison', fontsize=14)
    ax1.grid(True, alpha=0.3, axis='y')
    
    for bar, time in zip(bars1, times_hours):
        ax1.annotate(f'{time:.1f}h', xy=(bar.get_x() + bar.get_width()/2, time),
                    xytext=(0, 3), textcoords='offset points', ha='center', fontsize=10)
    
    # Subplot 2: Return por hora (eficiencia)
    bars2 = ax2.bar(names, returns_per_hour, color=colors, alpha=0.7, edgecolor='black')
    ax2.set_ylabel('Final Return / Hour', fontsize=12)
    ax2.set_title('Training Efficiency\n(Higher = Better)', fontsize=14)
    ax2.grid(True, alpha=0.3, axis='y')
    
    for bar, rph in zip(bars2, returns_per_hour):
        ax2.annotate(f'{rph:.1f}', xy=(bar.get_x() + bar.get_width()/2, rph),
                    xytext=(0, 3), textcoords='offset points', ha='center', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_dir / '05_wall_clock_comparison.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  [OK] 05_wall_clock_comparison.png')


def plot_sac_specific(metrics: AgentMetrics, output_dir: Path) -> None:
    """
    Grafica 6: Metricas especificas de SAC
    - Alpha (temperatura)
    - Mean Q-value
    - Actor/Critic loss
    """
    if not metrics.steps:
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    steps_k = np.array(metrics.steps) / 1000
    
    # Alpha
    ax = axes[0, 0]
    if metrics.alpha:
        alpha = np.array(metrics.alpha[:len(steps_k)])
        ax.plot(steps_k[:len(alpha)], smooth(alpha.tolist()), color='#9b59b6', linewidth=2)
        ax.axhline(y=0.01, color='red', linestyle=':', alpha=0.7, label='Warning: alpha < 0.01')
    ax.set_xlabel('Steps (K)')
    ax.set_ylabel('Alpha (alpha)')
    ax.set_title('SAC: Entropy Temperature (alpha)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Mean Q-value
    ax = axes[0, 1]
    if metrics.mean_q:
        q = np.array(metrics.mean_q[:len(steps_k)])
        ax.plot(steps_k[:len(q)], smooth(q.tolist()), color='#e67e22', linewidth=2)
        ax.axhline(y=1000, color='red', linestyle=':', alpha=0.7, label='Warning: Q > 1000')
    ax.set_xlabel('Steps (K)')
    ax.set_ylabel('Mean Q-value')
    ax.set_title('SAC: Mean Q-value')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Actor Loss
    ax = axes[1, 0]
    if metrics.actor_loss:
        al = np.array(metrics.actor_loss[:len(steps_k)])
        ax.plot(steps_k[:len(al)], smooth(al.tolist()), color='#27ae60', linewidth=2)
    ax.set_xlabel('Steps (K)')
    ax.set_ylabel('Actor Loss')
    ax.set_title('SAC: Actor Loss')
    ax.grid(True, alpha=0.3)
    
    # Critic Loss
    ax = axes[1, 1]
    if metrics.critic_loss:
        cl = np.array(metrics.critic_loss[:len(steps_k)])
        ax.plot(steps_k[:len(cl)], smooth(cl.tolist()), color='#c0392b', linewidth=2)
    ax.set_xlabel('Steps (K)')
    ax.set_ylabel('Critic Loss')
    ax.set_title('SAC: Critic Loss')
    ax.grid(True, alpha=0.3)
    
    fig.suptitle('SAC-Specific Metrics', fontsize=16, y=1.02)
    plt.tight_layout()
    plt.savefig(output_dir / '06_sac_specific_metrics.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  [OK] 06_sac_specific_metrics.png')


def plot_ppo_specific(metrics: AgentMetrics, output_dir: Path) -> None:
    """
    Grafica 7: Metricas especificas de PPO
    - KL divergence
    - Clip fraction
    - Explained variance
    """
    if not metrics.steps:
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    steps_k = np.array(metrics.steps) / 1000
    
    # KL Divergence
    ax = axes[0, 0]
    if metrics.kl_divergence:
        kl = np.array(metrics.kl_divergence[:len(steps_k)])
        ax.plot(steps_k[:len(kl)], smooth(kl.tolist()), color='#3498db', linewidth=2)
        ax.axhline(y=0.02, color='orange', linestyle=':', alpha=0.7, label='Target KL')
        ax.axhline(y=0.03, color='red', linestyle=':', alpha=0.7, label='Warning: KL > 0.03')
    ax.set_xlabel('Steps (K)')
    ax.set_ylabel('KL Divergence')
    ax.set_title('PPO: Approximate KL Divergence')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Clip Fraction
    ax = axes[0, 1]
    if metrics.clip_fraction:
        cf = np.array(metrics.clip_fraction[:len(steps_k)])
        ax.plot(steps_k[:len(cf)], smooth(cf.tolist()) * 100, color='#e74c3c', linewidth=2)
        ax.axhline(y=30, color='red', linestyle=':', alpha=0.7, label='Warning: > 30%')
    ax.set_xlabel('Steps (K)')
    ax.set_ylabel('Clip Fraction (%)')
    ax.set_title('PPO: Clip Fraction')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Explained Variance
    ax = axes[1, 0]
    if metrics.explained_variance:
        ev = np.array(metrics.explained_variance[:len(steps_k)])
        ax.plot(steps_k[:len(ev)], smooth(ev.tolist()), color='#2ecc71', linewidth=2)
        ax.axhline(y=0, color='red', linestyle=':', alpha=0.7, label='Random baseline')
        ax.axhline(y=1, color='green', linestyle=':', alpha=0.7, label='Perfect')
    ax.set_xlabel('Steps (K)')
    ax.set_ylabel('Explained Variance')
    ax.set_title('PPO: Explained Variance')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_ylim(-0.5, 1.1)
    
    # Value Loss
    ax = axes[1, 1]
    if metrics.value_loss:
        vl = np.array(metrics.value_loss[:len(steps_k)])
        ax.plot(steps_k[:len(vl)], smooth(vl.tolist()), color='#9b59b6', linewidth=2)
    ax.set_xlabel('Steps (K)')
    ax.set_ylabel('Value Loss')
    ax.set_title('PPO: Value Loss')
    ax.grid(True, alpha=0.3)
    
    fig.suptitle('PPO-Specific Metrics', fontsize=16, y=1.02)
    plt.tight_layout()
    plt.savefig(output_dir / '07_ppo_specific_metrics.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  [OK] 07_ppo_specific_metrics.png')


def plot_a2c_specific(metrics: AgentMetrics, output_dir: Path) -> None:
    """
    Grafica 8: Metricas especificas de A2C
    - Policy loss
    - Grad norm
    - Explained variance
    """
    if not metrics.steps:
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    steps_k = np.array(metrics.steps) / 1000
    
    # Policy Loss
    ax = axes[0, 0]
    if metrics.policy_loss:
        pl = np.array(metrics.policy_loss[:len(steps_k)])
        ax.plot(steps_k[:len(pl)], smooth(pl.tolist()), color='#e74c3c', linewidth=2)
    ax.set_xlabel('Steps (K)')
    ax.set_ylabel('Policy Loss')
    ax.set_title('A2C: Policy Loss')
    ax.grid(True, alpha=0.3)
    
    # Gradient Norm
    ax = axes[0, 1]
    if metrics.grad_norm:
        gn = np.array(metrics.grad_norm[:len(steps_k)])
        ax.plot(steps_k[:len(gn)], smooth(gn.tolist()), color='#f39c12', linewidth=2)
        ax.axhline(y=0.5, color='orange', linestyle=':', alpha=0.7, label='max_grad_norm')
    ax.set_xlabel('Steps (K)')
    ax.set_ylabel('Gradient Norm')
    ax.set_title('A2C: Gradient Norm (pre-clipping)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Explained Variance
    ax = axes[1, 0]
    if metrics.explained_variance:
        ev = np.array(metrics.explained_variance[:len(steps_k)])
        ax.plot(steps_k[:len(ev)], smooth(ev.tolist()), color='#2ecc71', linewidth=2)
        ax.axhline(y=0, color='red', linestyle=':', alpha=0.7, label='Random baseline')
    ax.set_xlabel('Steps (K)')
    ax.set_ylabel('Explained Variance')
    ax.set_title('A2C: Explained Variance')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.set_ylim(-0.5, 1.1)
    
    # Value Loss
    ax = axes[1, 1]
    if metrics.value_loss:
        vl = np.array(metrics.value_loss[:len(steps_k)])
        ax.plot(steps_k[:len(vl)], smooth(vl.tolist()), color='#9b59b6', linewidth=2)
    ax.set_xlabel('Steps (K)')
    ax.set_ylabel('Value Loss')
    ax.set_title('A2C: Value Loss')
    ax.grid(True, alpha=0.3)
    
    fig.suptitle('A2C-Specific Metrics', fontsize=16, y=1.02)
    plt.tight_layout()
    plt.savefig(output_dir / '08_a2c_specific_metrics.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  [OK] 08_a2c_specific_metrics.png')


def plot_dashboard_comparison(agents: Dict[str, AgentMetrics], output_dir: Path) -> None:
    """
    Grafica 9: Dashboard resumen de comparacion
    """
    fig = plt.figure(figsize=(16, 12))
    
    # Crear grid de subplots
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)
    
    # 1. Sample Efficiency (grande, arriba)
    ax1 = fig.add_subplot(gs[0, :])
    for name, metrics in agents.items():
        if not metrics.returns or not metrics.steps:
            continue
        steps_k = np.array(metrics.steps) / 1000
        smoothed = smooth(metrics.returns, window=5)
        ax1.plot(steps_k, smoothed, color=metrics.color,
                linestyle=AGENT_STYLES[name]['linestyle'],
                linewidth=2, label=name)
    ax1.set_xlabel('Steps (K)')
    ax1.set_ylabel('Return')
    ax1.set_title('Sample Efficiency: Return vs Steps')
    ax1.legend(loc='lower right')
    ax1.grid(True, alpha=0.3)
    
    # 2. Entropy
    ax2 = fig.add_subplot(gs[1, 0])
    for name, metrics in agents.items():
        if not metrics.entropy:
            continue
        steps_k = np.array(metrics.steps[:len(metrics.entropy)]) / 1000
        ax2.plot(steps_k, smooth(metrics.entropy), color=metrics.color,
                linestyle=AGENT_STYLES[name]['linestyle'], linewidth=1.5)
    ax2.set_xlabel('Steps (K)')
    ax2.set_ylabel('Entropy')
    ax2.set_title('Entropy')
    ax2.grid(True, alpha=0.3)
    
    # 3. Value/Critic Loss
    ax3 = fig.add_subplot(gs[1, 1])
    for name, metrics in agents.items():
        data = metrics.value_loss if metrics.value_loss else metrics.critic_loss
        if not data:
            continue
        steps_k = np.array(metrics.steps[:len(data)]) / 1000
        ax3.plot(steps_k, smooth(data), color=metrics.color,
                linestyle=AGENT_STYLES[name]['linestyle'], linewidth=1.5)
    ax3.set_xlabel('Steps (K)')
    ax3.set_ylabel('Loss')
    ax3.set_title('Value/Critic Loss')
    ax3.grid(True, alpha=0.3)
    ax3.set_yscale('log')
    
    # 4. Final Return Bar
    ax4 = fig.add_subplot(gs[1, 2])
    names = [n for n, m in agents.items() if m.returns]
    returns = [m.final_return for n, m in agents.items() if m.returns]
    colors = [AGENT_STYLES[n]['color'] for n in names]
    bars = ax4.bar(names, returns, color=colors, alpha=0.7, edgecolor='black')
    ax4.set_ylabel('Final Return')
    ax4.set_title('Final Return Comparison')
    ax4.grid(True, alpha=0.3, axis='y')
    for bar, ret in zip(bars, returns):
        ax4.annotate(f'{ret:.0f}', xy=(bar.get_x() + bar.get_width()/2, ret),
                    xytext=(0, 3), textcoords='offset points', ha='center', fontsize=9)
    
    # 5-7. Metricas especificas resumidas
    # SAC: Alpha
    ax5 = fig.add_subplot(gs[2, 0])
    if 'SAC' in agents and agents['SAC'].alpha:
        m = agents['SAC']
        steps_k = np.array(m.steps[:len(m.alpha)]) / 1000
        ax5.plot(steps_k, smooth(m.alpha), color=m.color, linewidth=1.5)
    ax5.set_xlabel('Steps (K)')
    ax5.set_ylabel('Alpha')
    ax5.set_title('SAC: Alpha (alpha)')
    ax5.grid(True, alpha=0.3)
    
    # PPO: KL + Clip
    ax6 = fig.add_subplot(gs[2, 1])
    if 'PPO' in agents:
        m = agents['PPO']
        if m.kl_divergence:
            steps_k = np.array(m.steps[:len(m.kl_divergence)]) / 1000
            ax6.plot(steps_k, smooth(m.kl_divergence), color='blue', 
                    linewidth=1.5, label='KL')
        if m.clip_fraction:
            steps_k = np.array(m.steps[:len(m.clip_fraction)]) / 1000
            ax6_twin = ax6.twinx()
            ax6_twin.plot(steps_k, smooth([c*100 for c in m.clip_fraction]), 
                         color='orange', linewidth=1.5, label='Clip %')
            ax6_twin.set_ylabel('Clip %', color='orange')
    ax6.set_xlabel('Steps (K)')
    ax6.set_ylabel('KL', color='blue')
    ax6.set_title('PPO: KL & Clip Fraction')
    ax6.grid(True, alpha=0.3)
    
    # A2C: Grad Norm
    ax7 = fig.add_subplot(gs[2, 2])
    if 'A2C' in agents and agents['A2C'].grad_norm:
        m = agents['A2C']
        steps_k = np.array(m.steps[:len(m.grad_norm)]) / 1000
        ax7.plot(steps_k, smooth(m.grad_norm), color=m.color, linewidth=1.5)
    ax7.set_xlabel('Steps (K)')
    ax7.set_ylabel('Grad Norm')
    ax7.set_title('A2C: Gradient Norm')
    ax7.grid(True, alpha=0.3)
    
    fig.suptitle('Comparison Dashboard: SAC vs PPO vs A2C\nEV Charging Optimization - Iquitos, Peru', 
                fontsize=16, y=1.02)
    
    plt.savefig(output_dir / '09_comparison_dashboard.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  [OK] 09_comparison_dashboard.png')


def generate_summary_table(agents: Dict[str, AgentMetrics], output_dir: Path) -> None:
    """
    Genera tabla resumen en CSV y texto.
    """
    rows = []
    
    for name, m in agents.items():
        row = {
            'Agent': name,
            'Final Return': f'{m.final_return:.1f}' if m.final_return else 'N/A',
            'Total Steps': f'{m.total_timesteps:,}' if m.total_timesteps else 'N/A',
            'Wall Time (h)': f'{m.wall_clock_time_s / 3600:.1f}' if m.wall_clock_time_s > 0 else 'N/A',
            'Final Entropy': f'{m.entropy[-1]:.3f}' if m.entropy else 'N/A',
        }
        
        # Metricas especificas
        if name == 'SAC':
            row['Final Alpha'] = f'{m.alpha[-1]:.4f}' if m.alpha else 'N/A'
            row['Final Q'] = f'{m.mean_q[-1]:.1f}' if m.mean_q else 'N/A'
        elif name == 'PPO':
            row['Final KL'] = f'{m.kl_divergence[-1]:.4f}' if m.kl_divergence else 'N/A'
            row['Avg Clip%'] = f'{np.mean(m.clip_fraction)*100:.1f}%' if m.clip_fraction else 'N/A'
            row['Final ExpVar'] = f'{m.explained_variance[-1]:.3f}' if m.explained_variance else 'N/A'
        elif name == 'A2C':
            row['Final ExpVar'] = f'{m.explained_variance[-1]:.3f}' if m.explained_variance else 'N/A'
            row['Avg GradNorm'] = f'{np.mean(m.grad_norm):.2f}' if m.grad_norm else 'N/A'
        
        rows.append(row)
    
    # Guardar CSV
    df = pd.DataFrame(rows)
    csv_path = output_dir / 'comparison_summary.csv'
    df.to_csv(csv_path, index=False)
    print(f'  [OK] comparison_summary.csv')
    
    # Imprimir tabla
    print('\n' + '=' * 80)
    print('RESUMEN COMPARATIVO: SAC vs PPO vs A2C')
    print('=' * 80)
    print(df.to_string(index=False))
    print('=' * 80)
    
    # Determinar ganador
    returns = {n: m.final_return for n, m in agents.items() if m.final_return != 0}
    if returns:
        best = max(returns, key=returns.get)
        print(f'\n🏆 MEJOR AGENTE POR RETURN: {best} ({returns[best]:.1f})')
    
    # Mas eficiente
    efficiency = {n: m.final_return / (m.wall_clock_time_s / 3600) 
                 for n, m in agents.items() 
                 if m.wall_clock_time_s > 0 and m.final_return != 0}
    if efficiency:
        most_efficient = max(efficiency, key=efficiency.get)
        print(f'⚡ MAS EFICIENTE (return/hora): {most_efficient} ({efficiency[most_efficient]:.1f})')


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Comparar SAC vs PPO vs A2C')
    parser.add_argument('--output-dir', type=str, default='outputs/comparison',
                       help='Directorio de salida para graficas')
    parser.add_argument('--use-synthetic', action='store_true',
                       help='Usar datos sinteticos para demo')
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print('=' * 80)
    print('COMPARACION DE AGENTES: SAC vs PPO vs A2C')
    print('EV Charging Optimization - Iquitos, Peru')
    print('=' * 80)
    print(f'Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'Output: {output_dir}')
    print()
    
    # Cargar metricas
    print('[1] CARGANDO METRICAS DE AGENTES')
    print('-' * 80)
    
    agents: Dict[str, AgentMetrics] = {}
    
    if args.use_synthetic:
        agents = generate_synthetic_data_for_demo()
    else:
        for agent_name in ['SAC', 'PPO', 'A2C']:
            metrics = load_agent_metrics(agent_name, output_dir.parent)
            if metrics:
                agents[agent_name] = metrics
        
        # Si no hay datos, generar sinteticos
        if not agents:
            print('  [!]  No se encontraron datos de entrenamiento.')
            print('  ℹ️  Generando datos sinteticos para demostracion...')
            agents = generate_synthetic_data_for_demo()
    
    print()
    
    # Generar graficas
    print('[2] GENERANDO GRAFICAS DE COMPARACION')
    print('-' * 80)
    
    # Graficas comparativas
    plot_sample_efficiency(agents, output_dir)
    plot_entropy_comparison(agents, output_dir)
    plot_value_loss_comparison(agents, output_dir)
    plot_final_return_boxplot(agents, output_dir)
    plot_wall_clock_comparison(agents, output_dir)
    
    # Graficas especificas por algoritmo
    if 'SAC' in agents:
        plot_sac_specific(agents['SAC'], output_dir)
    if 'PPO' in agents:
        plot_ppo_specific(agents['PPO'], output_dir)
    if 'A2C' in agents:
        plot_a2c_specific(agents['A2C'], output_dir)
    
    # Dashboard resumen
    plot_dashboard_comparison(agents, output_dir)
    
    print()
    
    # Generar tabla resumen
    print('[3] RESUMEN FINAL')
    print('-' * 80)
    generate_summary_table(agents, output_dir)
    
    print()
    print(f'[OK] Comparacion completa. Graficas guardadas en: {output_dir}')
    print()
    print('Graficas generadas:')
    print('  01_sample_efficiency.png       - Return vs Steps (curva principal)')
    print('  02_entropy_comparison.png      - Entropy vs Steps')
    print('  03_value_loss_comparison.png   - Value/Critic Loss')
    print('  04_final_return_distribution.png - Boxplot returns finales')
    print('  05_wall_clock_comparison.png   - Tiempo de entrenamiento')
    print('  06_sac_specific_metrics.png    - Alpha, Q-values, Actor/Critic loss')
    print('  07_ppo_specific_metrics.png    - KL, Clip fraction, Explained var')
    print('  08_a2c_specific_metrics.png    - Policy loss, Grad norm, Explained var')
    print('  09_comparison_dashboard.png    - Dashboard resumen completo')
    print('  comparison_summary.csv         - Tabla numerica')


if __name__ == '__main__':
    main()
