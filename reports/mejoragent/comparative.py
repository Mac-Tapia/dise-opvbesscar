#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COMPARATIVE.PY - Análisis Comparativo de Agentes RL (SAC, PPO, A2C)
=====================================================================
Determina el MEJOR AGENTE basado en:
  1. Mayor reducción de CO2 (objetivo principal)
  2. Eficiencia energética
  3. Métricas de entrenamiento

Gráficas generadas:
  - Return de evaluación vs Environment Steps
  - CO2 evitado comparativo (directo + indirecto)
  - Episode length vs Steps
  - Return vs Wall-clock time
  - Dashboard comparativo completo

Autor: pvbesscar Team
Fecha: 2026-02-15
"""
from __future__ import annotations

import json
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use('Agg')  # Backend sin GUI
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec

warnings.filterwarnings('ignore')

# ===== CONFIGURACIÓN =====
WORKSPACE_ROOT = Path(__file__).parent.parent.parent
OUTPUTS_DIR = WORKSPACE_ROOT / 'outputs'
REPORTS_DIR = Path(__file__).parent
GRAPHS_DIR = REPORTS_DIR / 'graphs'
GRAPHS_DIR.mkdir(parents=True, exist_ok=True)

# Colores por agente
AGENT_COLORS = {
    'SAC': '#2ecc71',   # Verde
    'PPO': '#3498db',   # Azul
    'A2C': '#e74c3c',   # Rojo
}

AGENT_MARKERS = {
    'SAC': 'o',
    'PPO': 's',
    'A2C': '^',
}


def load_agent_results() -> Dict[str, Dict]:
    """Cargar resultados de los 3 agentes."""
    results = {}
    
    # Rutas de los archivos de resultados
    paths = {
        'PPO': OUTPUTS_DIR / 'ppo_training' / 'result_ppo.json',
        'A2C': OUTPUTS_DIR / 'a2c_training' / 'result_a2c.json',
        'SAC': OUTPUTS_DIR / 'sac_training' / 'result_sac.json',
    }
    
    for agent, path in paths.items():
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                results[agent] = json.load(f)
            print(f'  [OK] {agent}: {path.name} cargado')
        else:
            print(f'  [!] {agent}: {path.name} NO encontrado')
            results[agent] = {}
    
    return results


def extract_metrics(results: Dict[str, Dict]) -> Dict[str, Dict]:
    """Extraer métricas normalizadas de cada agente."""
    metrics = {}
    
    for agent, data in results.items():
        if not data:
            continue
            
        m = {
            'agent': agent,
            'timesteps': 0,
            'episodes': 0,
            'episode_rewards': [],
            'co2_grid_kg': [],
            'co2_avoided_direct_kg': [],
            'co2_avoided_indirect_kg': [],
            'solar_kwh': [],
            'grid_import_kwh': [],
            'ev_charging_kwh': [],
            'bess_discharge_kwh': [],
            'bess_charge_kwh': [],
            'motos_charged': [],
            'mototaxis_charged': [],
            # Resumen
            'total_co2_avoided_kg': 0,
            'total_co2_avoided_direct_kg': 0,
            'total_co2_avoided_indirect_kg': 0,
            'total_cost_usd': 0,
        }
        
        # Extraer según estructura del agente
        if agent in ['PPO', 'A2C']:
            # Estructura PPO/A2C
            training = data.get('training', {})
            evolution = data.get('training_evolution', {})
            summary = data.get('summary_metrics', {})
            
            m['timesteps'] = training.get('total_timesteps', 0)
            m['episodes'] = len(evolution.get('episode_rewards', []))
            
            # Convertir a float para evitar errores de formato
            def to_float_list(arr):
                return [float(x) if x is not None else 0.0 for x in arr]
            
            m['episode_rewards'] = to_float_list(evolution.get('episode_rewards', []))
            m['co2_grid_kg'] = to_float_list(evolution.get('episode_co2_grid', []))
            m['co2_avoided_direct_kg'] = to_float_list(evolution.get('episode_co2_avoided_direct', []))
            m['co2_avoided_indirect_kg'] = to_float_list(evolution.get('episode_co2_avoided_indirect', []))
            m['solar_kwh'] = to_float_list(evolution.get('episode_solar_kwh', []))
            m['grid_import_kwh'] = to_float_list(evolution.get('episode_grid_import', []))
            m['ev_charging_kwh'] = to_float_list(evolution.get('episode_ev_charging', []))
            m['bess_discharge_kwh'] = to_float_list(evolution.get('episode_bess_discharge_kwh', []))
            m['bess_charge_kwh'] = to_float_list(evolution.get('episode_bess_charge_kwh', []))
            m['motos_charged'] = to_float_list(evolution.get('episode_motos_charged', []))
            m['mototaxis_charged'] = to_float_list(evolution.get('episode_mototaxis_charged', []))
            
            # Resumen
            m['total_co2_avoided_kg'] = summary.get('total_co2_avoided_kg', 0)
            m['total_co2_avoided_direct_kg'] = summary.get('total_co2_avoided_direct_kg', 0)
            m['total_co2_avoided_indirect_kg'] = summary.get('total_co2_avoided_indirect_kg', 0)
            m['total_cost_usd'] = summary.get('total_cost_usd', 0)
            
        elif agent == 'SAC':
            # Estructura SAC
            def to_float_list(arr):
                return [float(x) if x is not None else 0.0 for x in arr]
            
            m['timesteps'] = data.get('total_timesteps', 0)
            m['episodes'] = data.get('episodes_completed', 0)
            
            m['episode_rewards'] = to_float_list(data.get('episode_rewards', []))
            m['co2_grid_kg'] = to_float_list(data.get('episode_co2_grid_kg', []))
            m['solar_kwh'] = to_float_list(data.get('episode_solar_kwh', []))
            m['grid_import_kwh'] = to_float_list(data.get('episode_grid_import_kwh', []))
            m['ev_charging_kwh'] = to_float_list(data.get('episode_ev_charging_kwh', []))
            m['bess_discharge_kwh'] = to_float_list(data.get('episode_bess_discharge_kwh', []))
            m['bess_charge_kwh'] = to_float_list(data.get('episode_bess_charge_kwh', []))
            
            # Para SAC, calcular CO2 evitado desde los datos de episodios
            # Usar factor CO2 Iquitos: 0.4521 kg/kWh
            CO2_FACTOR = 0.4521
            if m['solar_kwh']:
                # CO2 indirecto = solar usado × factor
                m['co2_avoided_indirect_kg'] = [s * CO2_FACTOR for s in m['solar_kwh']]
                m['total_co2_avoided_indirect_kg'] = sum(m['co2_avoided_indirect_kg'])
            
            # CO2 directo = EV cargado × factor EV (estimado)
            EV_CO2_FACTOR = 0.87  # kg CO2/kWh promedio motos
            if m['ev_charging_kwh']:
                m['co2_avoided_direct_kg'] = [e * EV_CO2_FACTOR for e in m['ev_charging_kwh']]
                m['total_co2_avoided_direct_kg'] = sum(m['co2_avoided_direct_kg'])
            
            m['total_co2_avoided_kg'] = m['total_co2_avoided_direct_kg'] + m['total_co2_avoided_indirect_kg']
        
        metrics[agent] = m
    
    return metrics


def determine_best_agent(metrics: Dict[str, Dict]) -> Tuple[str, Dict]:
    """Determinar el mejor agente basado en CO2 evitado."""
    best_agent = None
    best_co2 = 0
    ranking = []
    
    for agent, m in metrics.items():
        co2 = m.get('total_co2_avoided_kg', 0)
        ranking.append({
            'agent': agent,
            'co2_avoided_total_kg': co2,
            'co2_avoided_direct_kg': m.get('total_co2_avoided_direct_kg', 0),
            'co2_avoided_indirect_kg': m.get('total_co2_avoided_indirect_kg', 0),
            'episodes': m.get('episodes', 0),
            'timesteps': m.get('timesteps', 0),
        })
        
        if co2 > best_co2:
            best_co2 = co2
            best_agent = agent
    
    # Ordenar por CO2
    ranking.sort(key=lambda x: x['co2_avoided_total_kg'], reverse=True)
    
    return best_agent, {'ranking': ranking, 'best_co2_kg': best_co2}


def plot_episode_rewards(metrics: Dict[str, Dict], save_path: Path) -> None:
    """Gráfica 1: Return de evaluación vs Environment Steps."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for agent, m in metrics.items():
        rewards = m.get('episode_rewards', [])
        if not rewards:
            continue
        
        # Convertir a float (por si vienen como strings)
        rewards = [float(r) for r in rewards]
            
        episodes = len(rewards)
        steps_per_ep = m['timesteps'] / max(episodes, 1)
        steps = [i * steps_per_ep for i in range(episodes)]
        
        # Media móvil
        window = max(1, episodes // 10)
        rewards_smooth = pd.Series(rewards).rolling(window=window, min_periods=1).mean()
        
        ax.plot(steps, rewards_smooth, 
                color=AGENT_COLORS[agent], 
                label=f'{agent} (final: {rewards[-1]:.2f})',
                linewidth=2,
                marker=AGENT_MARKERS[agent],
                markersize=4,
                markevery=max(1, len(steps)//10))
        
        # Banda de variabilidad
        rewards_std = pd.Series(rewards).rolling(window=window, min_periods=1).std().fillna(0)
        ax.fill_between(steps, 
                        rewards_smooth - rewards_std, 
                        rewards_smooth + rewards_std,
                        color=AGENT_COLORS[agent], 
                        alpha=0.2)
    
    ax.set_xlabel('Environment Steps', fontsize=12)
    ax.set_ylabel('Episode Return (media móvil)', fontsize=12)
    ax.set_title('Return de Evaluación vs Environment Steps', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(left=0)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'    [OK] {save_path.name}')


def plot_co2_comparison(metrics: Dict[str, Dict], save_path: Path) -> None:
    """Gráfica 2: CO2 evitado comparativo (barras agrupadas)."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Subplot 1: Total CO2 por tipo
    agents = list(metrics.keys())
    x = np.arange(len(agents))
    width = 0.35
    
    direct = [metrics[a].get('total_co2_avoided_direct_kg', 0) / 1e6 for a in agents]
    indirect = [metrics[a].get('total_co2_avoided_indirect_kg', 0) / 1e6 for a in agents]
    
    ax1 = axes[0]
    bars1 = ax1.bar(x - width/2, direct, width, label='CO2 Directo (EV)', 
                    color=[AGENT_COLORS[a] for a in agents], alpha=0.8)
    bars2 = ax1.bar(x + width/2, indirect, width, label='CO2 Indirecto (Solar/BESS)',
                    color=[AGENT_COLORS[a] for a in agents], alpha=0.5, hatch='//')
    
    ax1.set_ylabel('CO2 Evitado (millones kg)', fontsize=11)
    ax1.set_xlabel('Agente', fontsize=11)
    ax1.set_title('CO2 Evitado por Tipo', fontsize=12, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(agents, fontsize=11)
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Añadir valores en barras
    for bar, val in zip(bars1, direct):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height(), 
                f'{val:.1f}M', ha='center', va='bottom', fontsize=9)
    for bar, val in zip(bars2, indirect):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height(), 
                f'{val:.1f}M', ha='center', va='bottom', fontsize=9)
    
    # Subplot 2: CO2 total (ranking)
    ax2 = axes[1]
    totals = [metrics[a].get('total_co2_avoided_kg', 0) / 1e6 for a in agents]
    colors = [AGENT_COLORS[a] for a in agents]
    
    # Ordenar por total
    sorted_data = sorted(zip(agents, totals, colors), key=lambda x: x[1], reverse=True)
    agents_sorted, totals_sorted, colors_sorted = zip(*sorted_data)
    
    bars = ax2.barh(agents_sorted, totals_sorted, color=colors_sorted, edgecolor='black')
    
    # Destacar el mejor
    bars[0].set_edgecolor('gold')
    bars[0].set_linewidth(3)
    
    ax2.set_xlabel('CO2 Total Evitado (millones kg)', fontsize=11)
    ax2.set_title('🏆 RANKING CO2 EVITADO', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='x')
    
    for bar, val in zip(bars, totals_sorted):
        ax2.text(val + 0.5, bar.get_y() + bar.get_height()/2, 
                f'{val:.2f}M kg', va='center', fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'    [OK] {save_path.name}')


def plot_co2_evolution(metrics: Dict[str, Dict], save_path: Path) -> None:
    """Gráfica 3: Evolución de CO2 evitado por episodio."""
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))
    
    # Subplot 1: CO2 directo acumulado
    ax1 = axes[0]
    for agent, m in metrics.items():
        co2_direct = m.get('co2_avoided_direct_kg', [])
        if co2_direct:
            cumsum = np.cumsum(co2_direct) / 1e6
            episodes = range(len(cumsum))
            ax1.plot(episodes, cumsum, 
                    color=AGENT_COLORS[agent],
                    label=f'{agent} ({cumsum[-1]:.2f}M kg)',
                    linewidth=2,
                    marker=AGENT_MARKERS[agent],
                    markersize=4,
                    markevery=max(1, len(cumsum)//10))
    
    ax1.set_xlabel('Episodio', fontsize=11)
    ax1.set_ylabel('CO2 Directo Evitado Acumulado (M kg)', fontsize=11)
    ax1.set_title('Evolución CO2 Directo (EV vs Gasolina)', fontsize=12, fontweight='bold')
    ax1.legend(loc='lower right')
    ax1.grid(True, alpha=0.3)
    
    # Subplot 2: CO2 indirecto acumulado
    ax2 = axes[1]
    for agent, m in metrics.items():
        co2_indirect = m.get('co2_avoided_indirect_kg', [])
        if co2_indirect:
            cumsum = np.cumsum(co2_indirect) / 1e6
            episodes = range(len(cumsum))
            ax2.plot(episodes, cumsum,
                    color=AGENT_COLORS[agent],
                    label=f'{agent} ({cumsum[-1]:.2f}M kg)',
                    linewidth=2,
                    marker=AGENT_MARKERS[agent],
                    markersize=4,
                    markevery=max(1, len(cumsum)//10))
    
    ax2.set_xlabel('Episodio', fontsize=11)
    ax2.set_ylabel('CO2 Indirecto Evitado Acumulado (M kg)', fontsize=11)
    ax2.set_title('Evolución CO2 Indirecto (Solar/BESS reemplaza Grid)', fontsize=12, fontweight='bold')
    ax2.legend(loc='lower right')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'    [OK] {save_path.name}')


def plot_energy_metrics(metrics: Dict[str, Dict], save_path: Path) -> None:
    """Gráfica 4: Métricas de energía (Solar, Grid, BESS)."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Solar kWh por episodio
    ax1 = axes[0, 0]
    for agent, m in metrics.items():
        solar = m.get('solar_kwh', [])
        if solar:
            cumsum = np.cumsum(solar) / 1e6
            ax1.plot(range(len(cumsum)), cumsum,
                    color=AGENT_COLORS[agent],
                    label=f'{agent}',
                    linewidth=2)
    ax1.set_title('Solar Utilizado Acumulado', fontsize=11, fontweight='bold')
    ax1.set_xlabel('Episodio')
    ax1.set_ylabel('GWh')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Grid Import
    ax2 = axes[0, 1]
    for agent, m in metrics.items():
        grid = m.get('grid_import_kwh', [])
        if grid:
            cumsum = np.cumsum(grid) / 1e6
            ax2.plot(range(len(cumsum)), cumsum,
                    color=AGENT_COLORS[agent],
                    label=f'{agent}',
                    linewidth=2)
    ax2.set_title('Grid Import Acumulado', fontsize=11, fontweight='bold')
    ax2.set_xlabel('Episodio')
    ax2.set_ylabel('GWh')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # BESS Discharge
    ax3 = axes[1, 0]
    for agent, m in metrics.items():
        bess = m.get('bess_discharge_kwh', [])
        if bess:
            cumsum = np.cumsum(bess) / 1e6
            ax3.plot(range(len(cumsum)), cumsum,
                    color=AGENT_COLORS[agent],
                    label=f'{agent}',
                    linewidth=2)
    ax3.set_title('BESS Descarga Acumulada', fontsize=11, fontweight='bold')
    ax3.set_xlabel('Episodio')
    ax3.set_ylabel('GWh')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # EV Charging
    ax4 = axes[1, 1]
    for agent, m in metrics.items():
        ev = m.get('ev_charging_kwh', [])
        if ev:
            cumsum = np.cumsum(ev) / 1e6
            ax4.plot(range(len(cumsum)), cumsum,
                    color=AGENT_COLORS[agent],
                    label=f'{agent}',
                    linewidth=2)
    ax4.set_title('EV Charging Acumulado', fontsize=11, fontweight='bold')
    ax4.set_xlabel('Episodio')
    ax4.set_ylabel('GWh')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'    [OK] {save_path.name}')


def plot_vehicle_charging(metrics: Dict[str, Dict], save_path: Path) -> None:
    """Gráfica 5: Vehículos cargados (motos y mototaxis)."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Motos
    ax1 = axes[0]
    for agent, m in metrics.items():
        motos = m.get('motos_charged', [])
        if motos:
            ax1.plot(range(len(motos)), motos,
                    color=AGENT_COLORS[agent],
                    label=f'{agent} (max={max(motos)})',
                    linewidth=2,
                    alpha=0.8)
    ax1.set_title('Motos Cargadas por Episodio', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Episodio')
    ax1.set_ylabel('Motos cargadas')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=270, color='gray', linestyle='--', label='Meta diaria (270)')
    
    # Mototaxis
    ax2 = axes[1]
    for agent, m in metrics.items():
        taxis = m.get('mototaxis_charged', [])
        if taxis:
            ax2.plot(range(len(taxis)), taxis,
                    color=AGENT_COLORS[agent],
                    label=f'{agent} (max={max(taxis)})',
                    linewidth=2,
                    alpha=0.8)
    ax2.set_title('Mototaxis Cargados por Episodio', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Episodio')
    ax2.set_ylabel('Mototaxis cargados')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=39, color='gray', linestyle='--', label='Meta diaria (39)')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'    [OK] {save_path.name}')


def plot_comprehensive_dashboard(metrics: Dict[str, Dict], best_agent: str, ranking: Dict, save_path: Path) -> None:
    """Gráfica 6: Dashboard comparativo completo."""
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)
    
    # === ENCABEZADO: Mejor Agente ===
    ax_title = fig.add_subplot(gs[0, :])
    ax_title.axis('off')
    ax_title.text(0.5, 0.7, f'🏆 MEJOR AGENTE: {best_agent}', 
                  fontsize=28, fontweight='bold', ha='center', va='center',
                  color=AGENT_COLORS.get(best_agent, 'green'))
    ax_title.text(0.5, 0.3, 
                  f'CO2 Total Evitado: {ranking["best_co2_kg"]/1e6:.2f} millones kg',
                  fontsize=18, ha='center', va='center')
    
    # === RANKING ===
    ax_rank = fig.add_subplot(gs[1, 0])
    agents = [r['agent'] for r in ranking['ranking']]
    co2_vals = [r['co2_avoided_total_kg']/1e6 for r in ranking['ranking']]
    colors = [AGENT_COLORS[a] for a in agents]
    
    bars = ax_rank.barh(agents, co2_vals, color=colors, edgecolor='black')
    bars[0].set_edgecolor('gold')
    bars[0].set_linewidth(3)
    ax_rank.set_xlabel('CO2 Evitado (M kg)')
    ax_rank.set_title('RANKING CO2', fontweight='bold')
    for bar, val in zip(bars, co2_vals):
        ax_rank.text(val + 0.3, bar.get_y() + bar.get_height()/2, 
                    f'{val:.1f}M', va='center', fontsize=10)
    
    # === REWARDS ===
    ax_rewards = fig.add_subplot(gs[1, 1])
    for agent, m in metrics.items():
        rewards = m.get('episode_rewards', [])
        if rewards:
            window = max(1, len(rewards) // 5)
            smooth = pd.Series(rewards).rolling(window=window, min_periods=1).mean()
            ax_rewards.plot(smooth, color=AGENT_COLORS[agent], label=agent, linewidth=2)
    ax_rewards.set_xlabel('Episodio')
    ax_rewards.set_ylabel('Return')
    ax_rewards.set_title('Episode Returns', fontweight='bold')
    ax_rewards.legend()
    ax_rewards.grid(True, alpha=0.3)
    
    # === CO2 DESGLOSE ===
    ax_co2 = fig.add_subplot(gs[1, 2])
    x = np.arange(len(metrics))
    width = 0.4
    agents_list = list(metrics.keys())
    direct = [metrics[a].get('total_co2_avoided_direct_kg', 0)/1e6 for a in agents_list]
    indirect = [metrics[a].get('total_co2_avoided_indirect_kg', 0)/1e6 for a in agents_list]
    
    ax_co2.bar(x - width/2, direct, width, label='Directo (EV)', 
               color=[AGENT_COLORS[a] for a in agents_list], alpha=0.8)
    ax_co2.bar(x + width/2, indirect, width, label='Indirecto (Solar)', 
               color=[AGENT_COLORS[a] for a in agents_list], alpha=0.5)
    ax_co2.set_xticks(x)
    ax_co2.set_xticklabels(agents_list)
    ax_co2.set_ylabel('CO2 (M kg)')
    ax_co2.set_title('CO2 por Tipo', fontweight='bold')
    ax_co2.legend()
    
    # === ENERGÍA SOLAR ===
    ax_solar = fig.add_subplot(gs[2, 0])
    for agent, m in metrics.items():
        solar = m.get('solar_kwh', [])
        if solar:
            cumsum = np.cumsum(solar) / 1e6
            ax_solar.plot(cumsum, color=AGENT_COLORS[agent], label=agent, linewidth=2)
    ax_solar.set_xlabel('Episodio')
    ax_solar.set_ylabel('GWh')
    ax_solar.set_title('Solar Acumulado', fontweight='bold')
    ax_solar.legend()
    ax_solar.grid(True, alpha=0.3)
    
    # === GRID IMPORT ===
    ax_grid = fig.add_subplot(gs[2, 1])
    for agent, m in metrics.items():
        grid = m.get('grid_import_kwh', [])
        if grid:
            cumsum = np.cumsum(grid) / 1e6
            ax_grid.plot(cumsum, color=AGENT_COLORS[agent], label=agent, linewidth=2)
    ax_grid.set_xlabel('Episodio')
    ax_grid.set_ylabel('GWh')
    ax_grid.set_title('Grid Import Acumulado', fontweight='bold')
    ax_grid.legend()
    ax_grid.grid(True, alpha=0.3)
    
    # === TABLA RESUMEN ===
    ax_table = fig.add_subplot(gs[2, 2])
    ax_table.axis('off')
    
    table_data = []
    for agent in agents_list:
        m = metrics[agent]
        table_data.append([
            agent,
            f'{m.get("timesteps", 0):,}',
            f'{m.get("episodes", 0)}',
            f'{m.get("total_co2_avoided_kg", 0)/1e6:.2f}M',
        ])
    
    table = ax_table.table(
        cellText=table_data,
        colLabels=['Agente', 'Steps', 'Episodios', 'CO2 Evitado'],
        loc='center',
        cellLoc='center',
        colColours=['lightgray']*4
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 1.5)
    ax_table.set_title('Resumen', fontweight='bold', y=0.95)
    
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'    [OK] {save_path.name}')


def generate_report(metrics: Dict[str, Dict], best_agent: str, ranking: Dict) -> str:
    """Generar reporte de texto."""
    report = []
    report.append('=' * 80)
    report.append('REPORTE COMPARATIVO DE AGENTES RL - PVBESSCAR')
    report.append('=' * 80)
    report.append(f'Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    report.append('')
    report.append('OBJETIVO PRINCIPAL: Maximizar reducción de CO2')
    report.append('')
    
    report.append('-' * 40)
    report.append(f'🏆 MEJOR AGENTE: {best_agent}')
    report.append('-' * 40)
    report.append(f'   CO2 Total Evitado: {ranking["best_co2_kg"]/1e6:.2f} millones kg')
    report.append('')
    
    report.append('RANKING COMPLETO:')
    for i, r in enumerate(ranking['ranking'], 1):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
        report.append(f'  {medal} #{i} {r["agent"]}:')
        report.append(f'       CO2 Total:    {r["co2_avoided_total_kg"]/1e6:.2f}M kg')
        report.append(f'       CO2 Directo:  {r["co2_avoided_direct_kg"]/1e6:.2f}M kg')
        report.append(f'       CO2 Indirecto:{r["co2_avoided_indirect_kg"]/1e6:.2f}M kg')
        report.append(f'       Episodios:    {r["episodes"]}')
        report.append(f'       Steps:        {r["timesteps"]:,}')
        report.append('')
    
    report.append('MÉTRICAS DETALLADAS POR AGENTE:')
    report.append('-' * 40)
    for agent, m in metrics.items():
        report.append(f'\n{agent}:')
        report.append(f'  Timesteps:     {m.get("timesteps", 0):,}')
        report.append(f'  Episodios:     {m.get("episodes", 0)}')
        if m.get('episode_rewards'):
            report.append(f'  Reward Final:  {m["episode_rewards"][-1]:.2f}')
            report.append(f'  Reward Medio:  {np.mean(m["episode_rewards"]):.2f}')
    
    report.append('')
    report.append('=' * 80)
    report.append('FIN DEL REPORTE')
    report.append('=' * 80)
    
    return '\n'.join(report)


def main():
    """Ejecutar análisis comparativo completo."""
    print('=' * 80)
    print('ANÁLISIS COMPARATIVO DE AGENTES RL')
    print('PVBESSCAR - Optimización de Carga EV con PV/BESS')
    print('=' * 80)
    print(f'Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()
    
    # 1. Cargar resultados
    print('[1] CARGANDO RESULTADOS DE AGENTES')
    print('-' * 40)
    results = load_agent_results()
    print()
    
    # 2. Extraer métricas
    print('[2] EXTRAYENDO MÉTRICAS')
    print('-' * 40)
    metrics = extract_metrics(results)
    for agent, m in metrics.items():
        print(f'  {agent}: {m.get("episodes", 0)} episodios, {m.get("timesteps", 0):,} steps')
    print()
    
    # 3. Determinar mejor agente
    print('[3] DETERMINANDO MEJOR AGENTE (OBJETIVO: MAX CO2 EVITADO)')
    print('-' * 40)
    best_agent, ranking = determine_best_agent(metrics)
    print(f'\n  🏆 MEJOR AGENTE: {best_agent}')
    print(f'     CO2 Total Evitado: {ranking["best_co2_kg"]/1e6:.2f} millones kg')
    print()
    
    for i, r in enumerate(ranking['ranking'], 1):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
        print(f'  {medal} #{i} {r["agent"]}: {r["co2_avoided_total_kg"]/1e6:.2f}M kg CO2')
    print()
    
    # 4. Generar gráficas
    print('[4] GENERANDO GRÁFICAS COMPARATIVAS')
    print('-' * 40)
    
    # Gráfica 1: Episode Rewards vs Steps
    plot_episode_rewards(metrics, GRAPHS_DIR / '01_episode_rewards_vs_steps.png')
    
    # Gráfica 2: CO2 Comparison (barras)
    plot_co2_comparison(metrics, GRAPHS_DIR / '02_co2_comparison.png')
    
    # Gráfica 3: CO2 Evolution
    plot_co2_evolution(metrics, GRAPHS_DIR / '03_co2_evolution.png')
    
    # Gráfica 4: Energy Metrics
    plot_energy_metrics(metrics, GRAPHS_DIR / '04_energy_metrics.png')
    
    # Gráfica 5: Vehicle Charging
    plot_vehicle_charging(metrics, GRAPHS_DIR / '05_vehicle_charging.png')
    
    # Gráfica 6: Dashboard Completo
    plot_comprehensive_dashboard(metrics, best_agent, ranking, 
                                  GRAPHS_DIR / '06_comprehensive_dashboard.png')
    print()
    
    # 5. Generar reporte
    print('[5] GENERANDO REPORTE')
    print('-' * 40)
    report = generate_report(metrics, best_agent, ranking)
    
    report_path = REPORTS_DIR / 'comparative_report.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f'    [OK] {report_path.name}')
    
    # Guardar ranking como JSON
    ranking_path = REPORTS_DIR / 'agent_ranking.json'
    with open(ranking_path, 'w', encoding='utf-8') as f:
        json.dump({
            'best_agent': best_agent,
            'ranking': ranking['ranking'],
            'best_co2_kg': ranking['best_co2_kg'],
            'timestamp': datetime.now().isoformat(),
        }, f, indent=2, ensure_ascii=False)
    print(f'    [OK] {ranking_path.name}')
    print()
    
    # 6. Resumen final
    print('=' * 80)
    print('RESUMEN FINAL')
    print('=' * 80)
    print()
    print(f'  🏆 MEJOR AGENTE: {best_agent}')
    print(f'     Criterio: Mayor reducción de CO2')
    print(f'     CO2 Evitado: {ranking["best_co2_kg"]/1e6:.2f} millones kg')
    print()
    print('  ARCHIVOS GENERADOS:')
    for f in sorted(GRAPHS_DIR.glob('*.png')):
        print(f'    - graphs/{f.name}')
    print(f'    - {report_path.name}')
    print(f'    - {ranking_path.name}')
    print()
    print('=' * 80)
    
    return best_agent, ranking


if __name__ == '__main__':
    best, ranking = main()
