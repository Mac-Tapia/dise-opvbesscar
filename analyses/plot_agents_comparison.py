#!/usr/bin/env python3
"""
Módulo de Graficación Comparativa: SAC vs PPO vs A2C
======================================================

Genera visualizaciones completas de los tres agentes RL para comparación:
- CO₂ directo/indirecto temporal 
- Vehículos cargados
- BESS y energía solar
- Gráficas agregadas mensuales

**Autor**: Auditoría CO₂ Metodología 2026-02-18
**Entrada**: result_sac.json, result_ppo.json, result_a2c.json
**Salida**: PNG files en outputs/

"""

import json
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
import warnings
warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG GLOBAL
# ═══════════════════════════════════════════════════════════════════════════════

AGENTS = ['SAC', 'PPO', 'A2C']
COLORS = {
    'SAC': '#1f77b4',    # Azul
    'PPO': '#ff7f0e',    # Naranja
    'A2C': '#2ca02c'     # Verde
}
OUTPUT_DIR = Path('outputs')
OUTPUT_DIR.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def load_results() -> Dict[str, Dict[str, Any]]:
    """
    Carga los JSON de resultados de los tres agentes.
    
    Returns:
        Dict con estructura:
        {
            'SAC': {...},
            'PPO': {...},
            'A2C': {...}
        }
    """
    results = {}
    
    for agent in AGENTS:
        agent_lower = agent.lower()
        paths = [
            Path(f'outputs/{agent_lower}_training/result_{agent_lower}.json'),
            Path(f'outputs/{agent_lower}/result_{agent_lower}.json'),
            Path(f'checkpoints/{agent}/result_{agent_lower}.json'),
            Path(f'result_{agent_lower}.json'),
        ]
        
        loaded = False
        for path in paths:
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        results[agent] = json.load(f)
                    print(f'✓ Cargado: {path}')
                    loaded = True
                    break
                except Exception as e:
                    print(f'  [Error] {path}: {e}')
        
        if not loaded:
            print(f'✗ NO ENCONTRADO: result_{agent_lower}.json')
            results[agent] = {
                'summary_metrics': {},
                'training_evolution': {},
                'monthly_summary': {}
            }
    
    return results

# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICA 1: CO₂ DIRECTO COMPARADO
# ═══════════════════════════════════════════════════════════════════════════════

def plot_co2_directo_comparison(results: Dict[str, Dict], output_dir: Path) -> None:
    """Barra comparativa: CO₂ directo evitado por agente."""
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    values = []
    for agent in AGENTS:
        try:
            val = results[agent].get('summary_metrics', {}).get('total_co2_directo_kg', 0.0)
            values.append(float(val))
        except:
            values.append(0.0)
    
    bars = ax.bar(AGENTS, values, color=[COLORS[a] for a in AGENTS], alpha=0.8, edgecolor='black', linewidth=1.5)
    
    ax.set_ylabel('CO₂ Directo Evitado (kg/año)', fontsize=12, fontweight='bold')
    ax.set_title('Reducción CO₂ Directo (EV): SAC vs PPO vs A2C', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Agregar valores en barras
    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:,.0f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'plot_co2_directo_comparison.png', dpi=150, bbox_inches='tight')
    print('✓ Guardado: plot_co2_directo_comparison.png')
    plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICA 2: CO₂ INDIRECTO (SOLAR + BESS)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_co2_indirecto_comparison(results: Dict[str, Dict], output_dir: Path) -> None:
    """Barra apilada: CO₂ indirecto (solar + BESS)."""
    
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(AGENTS))
    width = 0.35
    
    solar_values = []
    bess_values = []
    
    for agent in AGENTS:
        metrics = results[agent].get('summary_metrics', {})
        solar = float(metrics.get('total_co2_indirecto_solar_kg', 0.0))
        bess = float(metrics.get('total_co2_indirecto_bess_kg', 0.0))
        solar_values.append(solar)
        bess_values.append(bess)
    
    bars1 = ax.bar(x - width/2, solar_values, width, label='Solar', alpha=0.8, 
                   color='#FFD700', edgecolor='black', linewidth=1.5)
    bars2 = ax.bar(x + width/2, bess_values, width, label='BESS', alpha=0.8,
                   color='#87CEEB', edgecolor='black', linewidth=1.5)
    
    ax.set_ylabel('CO₂ Indirecto Evitado (kg/año)', fontsize=12, fontweight='bold')
    ax.set_title('Reducción CO₂ Indirecto (Solar + BESS): SAC vs PPO vs A2C', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(AGENTS)
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Agregar valores en barras
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:,.0f}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'plot_co2_indirecto_comparison.png', dpi=150, bbox_inches='tight')
    print('✓ Guardado: plot_co2_indirecto_comparison.png')
    plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICA 3: CO₂ TOTAL EVITADO (ANUAL)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_co2_total_comparison(results: Dict[str, Dict], output_dir: Path) -> None:
    """Barra comparativa: CO₂ total evitado (directo + indirecto)."""
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    total_co2 = []
    for agent in AGENTS:
        metrics = results[agent].get('summary_metrics', {})
        total = float(metrics.get('total_co2_avoided_kg', 0.0))
        if total == 0.0:
            # Calcular manualmente si no está disponible
            direct = float(metrics.get('total_co2_directo_kg', 0.0))
            solar = float(metrics.get('total_co2_indirecto_solar_kg', 0.0))
            bess = float(metrics.get('total_co2_indirecto_bess_kg', 0.0))
            total = direct + solar + bess
        total_co2.append(total)
    
    bars = ax.bar(AGENTS, total_co2, color=[COLORS[a] for a in AGENTS], alpha=0.85, 
                  edgecolor='black', linewidth=2)
    
    ax.set_ylabel('CO₂ Total Evitado (kg/año)', fontsize=12, fontweight='bold')
    ax.set_title('CO₂ TOTAL Evitado (Directo + Indirecto): SAC vs PPO vs A2C', 
                 fontsize=14, fontweight='bold', pad=20)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim(0, max(total_co2) * 1.15)
    
    # Agregar valores y porcentajes
    baseline = total_co2[0]  # SAC como baseline
    for bar, val in zip(bars, total_co2):
        height = bar.get_height()
        pct_diff = ((val - baseline) / baseline * 100) if baseline > 0 else 0
        label_str = f'{val:,.0f}\nkg'
        if abs(pct_diff) > 0.5:
            label_str += f'\n({pct_diff:+.1f}%)'
        ax.text(bar.get_x() + bar.get_width()/2., height + max(total_co2)*0.02,
                label_str, ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'plot_co2_total_comparison.png', dpi=150, bbox_inches='tight')
    print('✓ Guardado: plot_co2_total_comparison.png')
    plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICA 4: VEHÍCULOS CARGADOS (MOTOS + MOTOTAXIS)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_vehicles_charged_comparison(results: Dict[str, Dict], output_dir: Path) -> None:
    """Barra apilada: Vehículos cargados por agente."""
    
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(AGENTS))
    width = 0.35
    
    motos_values = []
    taxis_values = []
    
    for agent in AGENTS:
        metrics = results[agent].get('summary_metrics', {})
        motos = float(metrics.get('max_motos_charged', 0.0))
        taxis = float(metrics.get('max_mototaxis_charged', 0.0))
        motos_values.append(motos)
        taxis_values.append(taxis)
    
    bars1 = ax.bar(x - width/2, motos_values, width, label='Motos (270/día)', 
                   alpha=0.8, color='#FF6B6B', edgecolor='black', linewidth=1.5)
    bars2 = ax.bar(x + width/2, taxis_values, width, label='Mototaxis (39/día)',
                   alpha=0.8, color='#4ECDC4', edgecolor='black', linewidth=1.5)
    
    ax.set_ylabel('Máximo Vehículos Cargados (periodo)', fontsize=12, fontweight='bold')
    ax.set_title('Vehículos Cargados: SAC vs PPO vs A2C', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(AGENTS)
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Agregar valores en barras
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'plot_vehicles_charged_comparison.png', dpi=150, bbox_inches='tight')
    print('✓ Guardado: plot_vehicles_charged_comparison.png')
    plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICA 5: EVOLUCIÓN CO₂ DIRECTO POR EPISODIO
# ═══════════════════════════════════════════════════════════════════════════════

def plot_co2_directo_evolution(results: Dict[str, Dict], output_dir: Path) -> None:
    """Línea: Evolución de CO₂ directo durante los 10 episodios."""
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    episodes = None
    for agent in AGENTS:
        evolution = results[agent].get('training_evolution', {}).get('episode_co2_directo_kg', [])
        if evolution:
            episodes = range(1, len(evolution) + 1)
            ax.plot(episodes, evolution, marker='o', label=agent, linewidth=2.5,
                   color=COLORS[agent], markersize=6, markeredgecolor='black', markeredgewidth=0.5)
    
    if episodes:
        ax.set_xlabel('Episodio', fontsize=12, fontweight='bold')
        ax.set_ylabel('CO₂ Directo Evitado (kg)', fontsize=12, fontweight='bold')
        ax.set_title('Evolución CO₂ Directo por Episodio: SAC vs PPO vs A2C', 
                    fontsize=14, fontweight='bold')
        ax.legend(fontsize=11, loc='best')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xticks(list(range(1, len(episodes)+1)))
        
        plt.tight_layout()
        plt.savefig(output_dir / 'plot_co2_directo_evolution.png', dpi=150, bbox_inches='tight')
        print('✓ Guardado: plot_co2_directo_evolution.png')
    
    plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICA 6: EVOLUCIÓN CO₂ INDIRECTO (SOLAR + BESS)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_co2_indirecto_evolution(results: Dict[str, Dict], output_dir: Path) -> None:
    """Gráfica dual: Evolución solar y BESS separados."""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # SOLAR
    for agent in AGENTS:
        evolution = results[agent].get('training_evolution', {}).get('episode_co2_indirecto_solar_kg', [])
        if evolution:
            episodes = range(1, len(evolution) + 1)
            ax1.plot(episodes, evolution, marker='o', label=agent, linewidth=2.5,
                    color=COLORS[agent], markersize=6, markeredgecolor='black', markeredgewidth=0.5)
    
    ax1.set_xlabel('Episodio', fontsize=11, fontweight='bold')
    ax1.set_ylabel('CO₂ Solar Evitado (kg)', fontsize=11, fontweight='bold')
    ax1.set_title('CO₂ Indirecto SOLAR por Episodio', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=10, loc='best')
    ax1.grid(True, alpha=0.3, linestyle='--')
    
    # BESS
    for agent in AGENTS:
        evolution = results[agent].get('training_evolution', {}).get('episode_co2_indirecto_bess_kg', [])
        if evolution:
            episodes = range(1, len(evolution) + 1)
            ax2.plot(episodes, evolution, marker='s', label=agent, linewidth=2.5,
                    color=COLORS[agent], markersize=6, markeredgecolor='black', markeredgewidth=0.5)
    
    ax2.set_xlabel('Episodio', fontsize=11, fontweight='bold')
    ax2.set_ylabel('CO₂ BESS Evitado (kg)', fontsize=11, fontweight='bold')
    ax2.set_title('CO₂ Indirecto BESS por Episodio', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=10, loc='best')
    ax2.grid(True, alpha=0.3, linestyle='--')
    
    fig.suptitle('Evolución CO₂ Indirecto (Solar vs BESS): SAC vs PPO vs A2C',
                fontsize=14, fontweight='bold', y=1.02)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'plot_co2_indirecto_evolution.png', dpi=150, bbox_inches='tight')
    print('✓ Guardado: plot_co2_indirecto_evolution.png')
    plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICA 7: EVOLUCIÓN VEHÍCULOS POR EPISODIO
# ═══════════════════════════════════════════════════════════════════════════════

def plot_vehicles_evolution(results: Dict[str, Dict], output_dir: Path) -> None:
    """Línea: Evolución de motos/mototaxis cargados durante los episodios."""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # MOTOS
    for agent in AGENTS:
        evolution = results[agent].get('training_evolution', {}).get('episode_motos_charged', [])
        if evolution:
            episodes = range(1, len(evolution) + 1)
            ax1.plot(episodes, evolution, marker='o', label=agent, linewidth=2.5,
                    color=COLORS[agent], markersize=6, markeredgecolor='black', markeredgewidth=0.5)
    
    ax1.set_xlabel('Episodio', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Motos Cargadas', fontsize=11, fontweight='bold')
    ax1.set_title('Motos Cargadas por Episodio', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=10, loc='best')
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.axhline(y=270, color='red', linestyle='--', linewidth=2, alpha=0.5, label='Target (270/día)')
    
    # MOTOTAXIS
    for agent in AGENTS:
        evolution = results[agent].get('training_evolution', {}).get('episode_mototaxis_charged', [])
        if evolution:
            episodes = range(1, len(evolution) + 1)
            ax2.plot(episodes, evolution, marker='s', label=agent, linewidth=2.5,
                    color=COLORS[agent], markersize=6, markeredgecolor='black', markeredgewidth=0.5)
    
    ax2.set_xlabel('Episodio', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Mototaxis Cargados', fontsize=11, fontweight='bold')
    ax2.set_title('Mototaxis Cargados por Episodio', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=10, loc='best')
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.axhline(y=39, color='red', linestyle='--', linewidth=2, alpha=0.5, label='Target (39/día)')
    
    fig.suptitle('Evolución Vehículos Cargados: SAC vs PPO vs A2C',
                fontsize=14, fontweight='bold', y=1.02)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'plot_vehicles_evolution.png', dpi=150, bbox_inches='tight')
    print('✓ Guardado: plot_vehicles_evolution.png')
    plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICA 8: RESUMEN TABLA COMPARATIVA
# ═══════════════════════════════════════════════════════════════════════════════

def plot_summary_table(results: Dict[str, Dict], output_dir: Path) -> None:
    """Tabla comparativa de métricas clave por agente."""
    
    data = []
    for agent in AGENTS:
        metrics = results[agent].get('summary_metrics', {})
        training = results[agent].get('training', {})
        data.append({
            'Agente': agent,
            'CO₂ Directo\n(kg)': f"{metrics.get('total_co2_directo_kg', 0):,.0f}",
            'CO₂ Solar\n(kg)': f"{metrics.get('total_co2_indirecto_solar_kg', 0):,.0f}",
            'CO₂ BESS\n(kg)': f"{metrics.get('total_co2_indirecto_bess_kg', 0):,.0f}",
            'CO₂ Total\n(kg)': f"{metrics.get('total_co2_avoided_kg', 0):,.0f}",
            'Motos Max': f"{metrics.get('max_motos_charged', 0)}",
            'Taxis Max': f"{metrics.get('max_mototaxis_charged', 0)}",
            'Tiempo\n(min)': f"{training.get('duration_seconds', 0) / 60:.1f}",
        })
    
    fig, ax = plt.subplots(figsize=(14, 3))
    ax.axis('tight')
    ax.axis('off')
    
    df = pd.DataFrame(data)
    table = ax.table(cellText=df.values, colLabels=df.columns, cellLoc='center',
                    loc='center', bbox=[0, 0, 1, 1])
    
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)
    
    # Colorear header
    for i in range(len(df.columns)):
        table[(0, i)].set_facecolor('#40466e')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Colorear filas por agente
    for i, agent in enumerate(AGENTS):
        color = COLORS[agent]
        for j in range(len(df.columns)):
            table[(i+1, j)].set_facecolor(color)
            table[(i+1, j)].set_alpha(0.3)
            table[(i+1, j)].set_text_props(weight='bold')
    
    plt.title('Resumen Comparativo: SAC vs PPO vs A2C', fontsize=14, fontweight='bold', pad=20)
    plt.savefig(output_dir / 'plot_summary_table.png', dpi=150, bbox_inches='tight')
    print('✓ Guardado: plot_summary_table.png')
    plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Ejecutar todas las gráficas."""
    
    print('\n' + '='*80)
    print('GENERADOR DE GRÁFICAS: SAC vs PPO vs A2C')
    print('='*80 + '\n')
    
    # 1. Cargar resultados
    print('[1] Cargando resultados de entrenamiento...')
    results = load_results()
    print()
    
    # 2. Generar gráficas
    print('[2] Generando gráficas comparativas...\n')
    
    plot_co2_directo_comparison(results, OUTPUT_DIR)
    plot_co2_indirecto_comparison(results, OUTPUT_DIR)
    plot_co2_total_comparison(results, OUTPUT_DIR)
    plot_vehicles_charged_comparison(results, OUTPUT_DIR)
    plot_co2_directo_evolution(results, OUTPUT_DIR)
    plot_co2_indirecto_evolution(results, OUTPUT_DIR)
    plot_vehicles_evolution(results, OUTPUT_DIR)
    plot_summary_table(results, OUTPUT_DIR)
    
    print('\n' + '='*80)
    print('✅ GRÁFICAS GENERADAS EXITOSAMENTE')
    print('='*80)
    print(f'\nGuardadas en: {OUTPUT_DIR}/')
    print('\nArchivos:')
    print('  - plot_co2_directo_comparison.png')
    print('  - plot_co2_indirecto_comparison.png')
    print('  - plot_co2_total_comparison.png')
    print('  - plot_vehicles_charged_comparison.png')
    print('  - plot_co2_directo_evolution.png')
    print('  - plot_co2_indirecto_evolution.png')
    print('  - plot_vehicles_evolution.png')
    print('  - plot_summary_table.png')

if __name__ == '__main__':
    main()
