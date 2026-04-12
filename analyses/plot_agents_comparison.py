#!/usr/bin/env python3
"""
Módulo de Graficación Comparativa: SAC vs PPO vs A2C
======================================================

Genera visualizaciones completas de los tres agentes RL para comparación.
Usa las claves REALES de result_*.json y fórmulas OE3 (Baseline vs Control Inteligente).

Claves reales en summary_metrics:
  total_co2_avoided_direct_kg     | total_co2_avoided_indirect_kg
  total_co2_avoided_kg            | max_motos_charged | max_mototaxis_charged

Claves reales en training_evolution:
  episode_rewards                 | episode_co2_avoided_direct
  episode_co2_avoided_indirect    | episode_solar_kwh
  episode_bess_discharge_kwh      | episode_motos_charged | episode_mototaxis_charged

Baseline (checkpoints/Baseline/baseline_results.json):
  co2_reduccion_directa_baseline = 330,030 kg/año (EVs vs combustión, sin optimización)
  co2_total_baseline             = 5,926,304 kg/año (total emitido sin control)

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
    'A2C': '#2ca02c',    # Verde
    'Baseline': '#d62728'  # Rojo
}
OUTPUT_DIR = Path('outputs')
OUTPUT_DIR.mkdir(exist_ok=True)

CO2_FACTOR_IQUITOS = 0.4521   # kg CO2/kWh (MINEM red diesel Iquitos)
CO2_FACTOR_MOTO    = 0.87     # kg CO2/kWh (IPCC 2006, Honda Wave 125cc)
CO2_FACTOR_MOTOTAXI = 0.54    # kg CO2/kWh (IPCC 2006, mototaxi 3-ruedas 150cc)

# Baseline cargado desde checkpoints/Baseline/baseline_results.json
BASELINE_CO2_DIRECT   = 330_030    # kg/año — reducción directa EVs vs combustión
BASELINE_CO2_INDIRECT = 0          # kg/año — sin optimización solar/BESS
BASELINE_CO2_TOTAL_AVOIDED = 330_030  # kg/año
BASELINE_CO2_EMITTED  = 5_926_304  # kg/año — total emitido en escenario sin control

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def load_results() -> Dict[str, Dict[str, Any]]:
    """
    Carga los JSON de resultados de los tres agentes y del baseline.

    Returns:
        Dict con claves 'SAC', 'PPO', 'A2C', 'Baseline'
    """
    results: Dict[str, Any] = {}

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
            results[agent] = {'summary_metrics': {}, 'training_evolution': {}, 'validation': {}, 'training': {}}

    # Cargar baseline
    baseline_path = Path('checkpoints/Baseline/baseline_results.json')
    if baseline_path.exists():
        try:
            with open(baseline_path, 'r', encoding='utf-8', errors='replace') as f:
                bl = json.load(f)
            results['Baseline'] = bl
            print(f'✓ Cargado: {baseline_path}')
        except Exception as e:
            print(f'  [Error] Baseline: {e}')
            results['Baseline'] = {}
    else:
        print(f'✗ NO ENCONTRADO: {baseline_path}')
        results['Baseline'] = {}

    return results


def _get_per_episode_co2(results: Dict, agent: str) -> Dict[str, float]:
    """
    Retorna CO2 (kg) por episodio anual para un agente usando validation si disponible,
    si no usa promedio de training_evolution.
    """
    sm = results[agent].get('summary_metrics', {})
    val = results[agent].get('validation', {})
    tr = results[agent].get('training', {})
    te = results[agent].get('training_evolution', {})
    episodes = max(tr.get('episodes', 1), 1)

    # Validación es el mejor estimador de performance en 1 año
    co2_total_val = float(val.get('mean_co2_avoided_kg', 0.0))
    co2_direct_avg = float(sm.get('total_co2_avoided_direct_kg', 0.0)) / episodes
    co2_indirect_avg = float(sm.get('total_co2_avoided_indirect_kg', 0.0)) / episodes
    co2_total_avg = float(sm.get('total_co2_avoided_kg', 0.0)) / episodes

    # Preferir validación para el total (más representativo)
    co2_total = co2_total_val if co2_total_val > 0 else co2_total_avg

    return {
        'co2_direct':   co2_direct_avg,
        'co2_indirect': co2_indirect_avg,
        'co2_total':    co2_total,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICA 1: CO₂ DIRECTO COMPARADO (por episodio anual)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_co2_directo_comparison(results: Dict[str, Dict], output_dir: Path) -> None:
    """Barra comparativa: CO₂ directo evitado por agente (1 año) + baseline."""

    fig, ax = plt.subplots(figsize=(12, 6))

    labels = AGENTS + ['Baseline']
    values = []
    for agent in AGENTS:
        v = _get_per_episode_co2(results, agent)['co2_direct']
        values.append(v)
    values.append(float(BASELINE_CO2_DIRECT))

    colors = [COLORS[a] for a in AGENTS] + [COLORS['Baseline']]
    bars = ax.bar(labels, values, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)

    ax.set_ylabel('CO₂ Directo Evitado (kg/año)', fontsize=12, fontweight='bold')
    ax.set_title('Reducción CO₂ Directo (EVs reemplazan combustión): Agentes vs Baseline',
                 fontsize=13, fontweight='bold')
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height(),
                    f'{val:,.0f}', ha='center', va='bottom', fontsize=11, fontweight='bold')

    ax.text(0.98, 0.97, f'Factor CO₂ moto: {CO2_FACTOR_MOTO} kg/kWh | mototaxi: {CO2_FACTOR_MOTOTAXI} kg/kWh\n(IPCC 2006 Tier 1)',
            transform=ax.transAxes, ha='right', va='top', fontsize=8, color='gray',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.7))

    plt.tight_layout()
    plt.savefig(output_dir / 'plot_co2_directo_comparison.png', dpi=150, bbox_inches='tight')
    print('✓ Guardado: plot_co2_directo_comparison.png')
    plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICA 2: CO₂ INDIRECTO (SOLAR + BESS) vs BASELINE
# ═══════════════════════════════════════════════════════════════════════════════

def plot_co2_indirecto_comparison(results: Dict[str, Dict], output_dir: Path) -> None:
    """Barras: CO₂ indirecto evitado por optimización solar/BESS + baseline."""

    fig, ax = plt.subplots(figsize=(12, 6))

    labels = AGENTS + ['Baseline']
    indirect_values = []
    for agent in AGENTS:
        v = _get_per_episode_co2(results, agent)['co2_indirect']
        indirect_values.append(v)
    indirect_values.append(float(BASELINE_CO2_INDIRECT))  # 0 — sin optimización

    # Calcular componente solar y BESS por ep (usando training_evolution)
    solar_values = []
    bess_values = []
    for agent in AGENTS:
        te = results[agent].get('training_evolution', {})
        tr = results[agent].get('training', {})
        episodes = max(tr.get('episodes', 1), 1)
        solar_kwh_list = te.get('episode_solar_kwh', [])
        bess_kwh_list = te.get('episode_bess_discharge_kwh', [])
        solar_kwh = float(solar_kwh_list[-1]) if solar_kwh_list else 0.0
        bess_kwh  = float(bess_kwh_list[-1]) if bess_kwh_list else 0.0
        solar_values.append(solar_kwh * CO2_FACTOR_IQUITOS)
        bess_values.append(bess_kwh * CO2_FACTOR_IQUITOS)
    solar_values.append(0.0)
    bess_values.append(0.0)

    x = np.arange(len(labels))
    width = 0.35
    colors_main = [COLORS[a] for a in AGENTS] + [COLORS['Baseline']]

    bars_main = ax.bar(x, indirect_values, width * 2, label='Total indirecto (avg/ep)',
                       color=colors_main, alpha=0.5, edgecolor='black', linewidth=1.5)
    bars_solar = ax.bar(x - width / 2, solar_values, width, label='Solar (ep_final)',
                        color='#FFD700', alpha=0.85, edgecolor='black', linewidth=1)
    bars_bess  = ax.bar(x + width / 2, bess_values,  width, label='BESS (ep_final)',
                        color='#87CEEB', alpha=0.85, edgecolor='black', linewidth=1)

    ax.set_ylabel('CO₂ Indirecto Evitado (kg/año)', fontsize=12, fontweight='bold')
    ax.set_title('CO₂ Indirecto por Optimización Solar + BESS: Agentes vs Baseline',
                 fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    for bar, val in zip(bars_main, indirect_values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height(),
                    f'{val:,.0f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_dir / 'plot_co2_indirecto_comparison.png', dpi=150, bbox_inches='tight')
    print('✓ Guardado: plot_co2_indirecto_comparison.png')
    plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICA 3: CO₂ TOTAL EVITADO (ANUAL) vs BASELINE
# ═══════════════════════════════════════════════════════════════════════════════

def plot_co2_total_comparison(results: Dict[str, Dict], output_dir: Path) -> None:
    """Barra comparativa: CO₂ total evitado/año (validación) vs baseline."""

    fig, ax = plt.subplots(figsize=(13, 7))

    labels = AGENTS + ['Baseline']
    total_co2 = []
    for agent in AGENTS:
        total_co2.append(_get_per_episode_co2(results, agent)['co2_total'])
    total_co2.append(float(BASELINE_CO2_TOTAL_AVOIDED))

    colors = [COLORS[a] for a in AGENTS] + [COLORS['Baseline']]
    bars = ax.bar(labels, total_co2, color=colors, alpha=0.85, edgecolor='black', linewidth=2)

    # Línea de emisiones totales del baseline (lo que se emite sin control)
    ax.axhline(y=BASELINE_CO2_EMITTED, color='darkred', linestyle=':', linewidth=2, alpha=0.7,
               label=f'Emisiones totales sin control: {BASELINE_CO2_EMITTED:,.0f} kg/año')

    ax.set_ylabel('CO₂ Total Evitado (kg/año)', fontsize=12, fontweight='bold')
    ax.set_title('CO₂ TOTAL Evitado (Directo + Indirecto): Control Inteligente vs Baseline',
                 fontsize=13, fontweight='bold', pad=20)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim(0, BASELINE_CO2_EMITTED * 1.08)
    ax.legend(fontsize=10)

    for bar, val in zip(bars, total_co2):
        height = bar.get_height()
        pct_emitido = (val / BASELINE_CO2_EMITTED * 100) if BASELINE_CO2_EMITTED > 0 else 0
        label_str = f'{val:,.0f} kg\n({pct_emitido:.1f}% del total\nemitido baseline)'
        ax.text(bar.get_x() + bar.get_width() / 2., height + BASELINE_CO2_EMITTED * 0.01,
                label_str, ha='center', va='bottom', fontsize=9, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_dir / 'plot_co2_total_comparison.png', dpi=150, bbox_inches='tight')
    print('✓ Guardado: plot_co2_total_comparison.png')
    plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICA 4: VEHÍCULOS CARGADOS (MOTOS + MOTOTAXIS) — max sockets/ep
# ═══════════════════════════════════════════════════════════════════════════════

def plot_vehicles_charged_comparison(results: Dict[str, Dict], output_dir: Path) -> None:
    """Barra: Máx de sockets usados simultáneamente por episodio (SAC/A2C).
    Nota: PPO registra conteo acumulado (distinta métrica), se muestra por separado."""

    fig, (ax_main, ax_ppo) = plt.subplots(1, 2, figsize=(14, 6),
                                           gridspec_kw={'width_ratios': [2, 1]})

    # SAC y A2C: max sockets simultáneos en episodio
    sac_a2c = ['SAC', 'A2C']
    x = np.arange(len(sac_a2c))
    width = 0.35
    motos_values = []
    taxis_values = []
    for agent in sac_a2c:
        sm = results[agent].get('summary_metrics', {})
        motos_values.append(float(sm.get('max_motos_charged', 0)))
        taxis_values.append(float(sm.get('max_mototaxis_charged', 0)))

    bars1 = ax_main.bar(x - width / 2, motos_values, width, label='Motos (máx sockets/ep)',
                        alpha=0.8, color='#FF6B6B', edgecolor='black', linewidth=1.5)
    bars2 = ax_main.bar(x + width / 2, taxis_values, width, label='Mototaxis (máx sockets/ep)',
                        alpha=0.8, color='#4ECDC4', edgecolor='black', linewidth=1.5)
    ax_main.axhline(y=30, color='red', linestyle='--', linewidth=1.5, alpha=0.6, label='Motos máx (30 sockets)')
    ax_main.axhline(y=8, color='teal', linestyle='--', linewidth=1.5, alpha=0.6, label='Taxis máx (8 sockets)')
    ax_main.set_ylabel('Máx Sockets Simultáneos / Episodio', fontsize=11, fontweight='bold')
    ax_main.set_title('SAC vs A2C — Sockets en uso (máx)', fontsize=12, fontweight='bold')
    ax_main.set_xticks(x)
    ax_main.set_xticklabels(sac_a2c)
    ax_main.legend(fontsize=9)
    ax_main.grid(axis='y', alpha=0.3, linestyle='--')
    ax_main.set_ylim(0, 38)
    for bars_group in [bars1, bars2]:
        for bar in bars_group:
            if bar.get_height() > 0:
                ax_main.text(bar.get_x() + bar.get_width() / 2., bar.get_height(),
                             f'{int(bar.get_height())}', ha='center', va='bottom',
                             fontsize=11, fontweight='bold')

    # PPO: conteo acumulado (diferente métrica)
    ppo_sm = results['PPO'].get('summary_metrics', {})
    ppo_motos = float(ppo_sm.get('max_motos_charged', 0))
    ppo_taxis = float(ppo_sm.get('max_mototaxis_charged', 0))
    ax_ppo.bar(['Motos', 'Taxis'], [ppo_motos, ppo_taxis],
               color=['#FF6B6B', '#4ECDC4'], alpha=0.8, edgecolor='black')
    ax_ppo.set_title('PPO — Conteo acumulado/ep\n(métrica diferente)', fontsize=11, fontweight='bold')
    ax_ppo.set_ylabel('Total vehículos cargados/ep', fontsize=10)
    ax_ppo.grid(axis='y', alpha=0.3, linestyle='--')
    for i, val in enumerate([ppo_motos, ppo_taxis]):
        ax_ppo.text(i, val, f'{int(val):,}', ha='center', va='bottom', fontsize=9, fontweight='bold')

    fig.suptitle('Vehículos Cargados: SAC vs PPO vs A2C', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_dir / 'plot_vehicles_charged_comparison.png', dpi=150, bbox_inches='tight')
    print('✓ Guardado: plot_vehicles_charged_comparison.png')
    plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICA 5: EVOLUCIÓN CO₂ DIRECTO POR EPISODIO
# ═══════════════════════════════════════════════════════════════════════════════

def plot_co2_directo_evolution(results: Dict[str, Dict], output_dir: Path) -> None:
    """Línea: Evolución de CO₂ directo evitado durante los 50 episodios."""

    fig, ax = plt.subplots(figsize=(12, 6))
    has_data = False

    for agent in AGENTS:
        # Clave real: episode_co2_avoided_direct (no episode_co2_directo_kg)
        evolution = results[agent].get('training_evolution', {}).get('episode_co2_avoided_direct', [])
        if evolution:
            episodes = range(1, len(evolution) + 1)
            ax.plot(list(episodes), evolution, marker='o', label=agent, linewidth=2.5,
                    color=COLORS[agent], markersize=4, markeredgecolor='black', markeredgewidth=0.5)
            has_data = True

    # Línea baseline (constante: reducción directa sin optimización solar)
    if has_data:
        max_eps = max(
            len(results[a].get('training_evolution', {}).get('episode_co2_avoided_direct', []))
            for a in AGENTS
        )
        ax.axhline(y=BASELINE_CO2_DIRECT, color=COLORS['Baseline'], linestyle='--',
                   linewidth=2, alpha=0.8, label=f'Baseline: {BASELINE_CO2_DIRECT:,.0f} kg/año')
        ax.set_xlabel('Episodio (1 ep = 1 año)', fontsize=12, fontweight='bold')
        ax.set_ylabel('CO₂ Directo Evitado (kg/ep)', fontsize=12, fontweight='bold')
        ax.set_title('Evolución CO₂ Directo por Episodio: SAC vs PPO vs A2C vs Baseline',
                     fontsize=13, fontweight='bold')
        ax.legend(fontsize=11, loc='best')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.ticklabel_format(useOffset=False, axis='y', style='plain')
        # Asegurar que el eje Y inicia en 0 y muestra rango completo
        all_vals = [BASELINE_CO2_DIRECT]
        for agent in AGENTS:
            ev = results[agent].get('training_evolution', {}).get('episode_co2_avoided_direct', [])
            if ev:
                all_vals.extend(ev)
        y_max = max(all_vals) * 1.15 if all_vals else BASELINE_CO2_DIRECT * 1.15
        ax.set_ylim(0, y_max)

        plt.tight_layout()
        plt.savefig(output_dir / 'plot_co2_directo_evolution.png', dpi=150, bbox_inches='tight')
        print('✓ Guardado: plot_co2_directo_evolution.png')

    plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICA 6: EVOLUCIÓN CO₂ INDIRECTO + REWARD POR EPISODIO
# ═══════════════════════════════════════════════════════════════════════════════

def plot_co2_indirecto_evolution(results: Dict[str, Dict], output_dir: Path) -> None:
    """Gráfica dual: CO₂ indirecto evitado y reward por episodio."""

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # — CO₂ INDIRECTO (clave real: episode_co2_avoided_indirect)
    for agent in AGENTS:
        evolution = results[agent].get('training_evolution', {}).get('episode_co2_avoided_indirect', [])
        if evolution:
            ax1.plot(range(1, len(evolution) + 1), evolution, marker='o', label=agent,
                     linewidth=2.5, color=COLORS[agent], markersize=4,
                     markeredgecolor='black', markeredgewidth=0.5)

    ax1.axhline(y=BASELINE_CO2_INDIRECT, color=COLORS['Baseline'], linestyle='--',
                linewidth=2, alpha=0.7, label=f'Baseline: {BASELINE_CO2_INDIRECT:,} kg/año')
    ax1.set_xlabel('Episodio (1 ep = 1 año)', fontsize=11, fontweight='bold')
    ax1.set_ylabel('CO₂ Indirecto Evitado (kg/ep)', fontsize=11, fontweight='bold')
    ax1.set_title('CO₂ Indirecto por Episodio\n(Solar + BESS vs Baseline)', fontsize=11, fontweight='bold')
    ax1.legend(fontsize=9, loc='best')
    ax1.grid(True, alpha=0.3, linestyle='--')

    # — REWARD (clave real: episode_rewards)
    for agent in AGENTS:
        rewards = results[agent].get('training_evolution', {}).get('episode_rewards', [])
        if rewards:
            ax2.plot(range(1, len(rewards) + 1), rewards, marker='s', label=agent,
                     linewidth=2.5, color=COLORS[agent], markersize=4,
                     markeredgecolor='black', markeredgewidth=0.5)

    ax2.axhline(y=0, color='gray', linestyle=':', linewidth=1.5, alpha=0.7)
    ax2.set_xlabel('Episodio (1 ep = 1 año)', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Reward Total / Episodio', fontsize=11, fontweight='bold')
    ax2.set_title('Evolución Reward por Episodio\n(Función objetivo OE3)', fontsize=11, fontweight='bold')
    ax2.legend(fontsize=9, loc='best')
    ax2.grid(True, alpha=0.3, linestyle='--')

    fig.suptitle('Convergencia Agentes RL: CO₂ Indirecto y Reward | Iquitos 2024',
                 fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_dir / 'plot_co2_indirecto_evolution.png', dpi=150, bbox_inches='tight')
    print('✓ Guardado: plot_co2_indirecto_evolution.png')
    plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICA 7: EVOLUCIÓN VEHÍCULOS POR EPISODIO
# ═══════════════════════════════════════════════════════════════════════════════

def plot_vehicles_evolution(results: Dict[str, Dict], output_dir: Path) -> None:
    """Línea: Evolución de motos/mototaxis cargados por episodio (SAC/A2C).
    PPO se muestra como anotación ya que usa conteo acumulado."""

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # SAC y A2C tienen max sockets simultáneos; PPO tiene conteo acumulado
    for agent in AGENTS:
        motos = results[agent].get('training_evolution', {}).get('episode_motos_charged', [])
        taxis = results[agent].get('training_evolution', {}).get('episode_mototaxis_charged', [])
        if not motos:
            continue
        # Para PPO normalizar a escala diaria (/ 365) para visualizar tendencia
        scale = 1.0 / 365.0 if agent == 'PPO' else 1.0
        label_suffix = '/365 días (norm.)' if agent == 'PPO' else ''
        ax1.plot(range(1, len(motos) + 1), [v * scale for v in motos],
                 marker='o', label=f'{agent}{label_suffix}', linewidth=2.5,
                 color=COLORS[agent], markersize=4,
                 markeredgecolor='black', markeredgewidth=0.5,
                 linestyle='--' if agent == 'PPO' else '-')
        ax2.plot(range(1, len(taxis) + 1), [v * scale for v in taxis],
                 marker='s', label=f'{agent}{label_suffix}', linewidth=2.5,
                 color=COLORS[agent], markersize=4,
                 markeredgecolor='black', markeredgewidth=0.5,
                 linestyle='--' if agent == 'PPO' else '-')

    ax1.axhline(y=30, color='red', linestyle=':', linewidth=2, alpha=0.6, label='Límite motos (30 sockets)')
    ax1.set_xlabel('Episodio (1 ep = 1 año)', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Motos cargadas (max o norm.)', fontsize=11, fontweight='bold')
    ax1.set_title('Motos Cargadas por Episodio', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=9, loc='best')
    ax1.grid(True, alpha=0.3, linestyle='--')

    ax2.axhline(y=8, color='teal', linestyle=':', linewidth=2, alpha=0.6, label='Límite taxis (8 sockets)')
    ax2.set_xlabel('Episodio (1 ep = 1 año)', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Mototaxis cargadas (max o norm.)', fontsize=11, fontweight='bold')
    ax2.set_title('Mototaxis Cargados por Episodio', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=9, loc='best')
    ax2.grid(True, alpha=0.3, linestyle='--')

    fig.suptitle('Evolución Vehículos Cargados por Episodio: SAC vs PPO vs A2C',
                 fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_dir / 'plot_vehicles_evolution.png', dpi=150, bbox_inches='tight')
    print('✓ Guardado: plot_vehicles_evolution.png')
    plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# GRÁFICA 8: RESUMEN TABLA COMPARATIVA
# ═══════════════════════════════════════════════════════════════════════════════

def plot_summary_table(results: Dict[str, Dict], output_dir: Path) -> None:
    """Tabla comparativa de métricas clave por agente vs baseline."""

    data = []
    for agent in AGENTS:
        val  = results[agent].get('validation', {})
        tr   = results[agent].get('training', {})
        sm   = results[agent].get('summary_metrics', {})
        eps  = max(tr.get('episodes', 1), 1)
        co2  = _get_per_episode_co2(results, agent)
        pct  = (co2['co2_total'] / BASELINE_CO2_EMITTED * 100) if BASELINE_CO2_EMITTED > 0 else 0

        data.append({
            'Agente': agent,
            'CO₂ Directo\n(kg/año)': f"{co2['co2_direct']:,.0f}",
            'CO₂ Indirecto\n(kg/año)': f"{co2['co2_indirect']:,.0f}",
            'CO₂ Total\nevitado (kg/año)': f"{co2['co2_total']:,.0f}",
            '% CO₂ evitado\nvs total baseline': f"{pct:.1f}%",
            'Reward\n(validación)': f"{val.get('mean_reward', 0):.2f}",
            'Motos max\n(sockets/ep)': f"{sm.get('max_motos_charged', 0)}",
            'Taxis max\n(sockets/ep)': f"{sm.get('max_mototaxis_charged', 0)}",
            'Duración\n(min)': f"{tr.get('duration_seconds', 0) / 60:.1f}",
        })

    # Fila baseline
    data.append({
        'Agente': 'Baseline',
        'CO₂ Directo\n(kg/año)': f"{BASELINE_CO2_DIRECT:,.0f}",
        'CO₂ Indirecto\n(kg/año)': f"{BASELINE_CO2_INDIRECT:,}",
        'CO₂ Total\nevitado (kg/año)': f"{BASELINE_CO2_TOTAL_AVOIDED:,.0f}",
        '% CO₂ evitado\nvs total baseline': f"{BASELINE_CO2_TOTAL_AVOIDED/BASELINE_CO2_EMITTED*100:.1f}%",
        'Reward\n(validación)': '—',
        'Motos max\n(sockets/ep)': '—',
        'Taxis max\n(sockets/ep)': '—',
        'Duración\n(min)': '—',
    })

    fig, ax = plt.subplots(figsize=(16, 3.5))
    ax.axis('tight')
    ax.axis('off')

    df = pd.DataFrame(data)
    table = ax.table(cellText=df.values, colLabels=df.columns, cellLoc='center',
                     loc='center', bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2.2)

    for i in range(len(df.columns)):
        table[(0, i)].set_facecolor('#40466e')
        table[(0, i)].set_text_props(weight='bold', color='white')

    row_colors = [COLORS['SAC'], COLORS['PPO'], COLORS['A2C'], COLORS['Baseline']]
    for i, color in enumerate(row_colors):
        for j in range(len(df.columns)):
            table[(i + 1, j)].set_facecolor(color)
            cell = table[(i + 1, j)]
            cell.set_alpha(0.25)
            cell.set_text_props(weight='bold')

    plt.title(
        f'Resumen Comparativo: Control Inteligente vs Baseline | Iquitos 2024\n'
        f'Baseline total emitido: {BASELINE_CO2_EMITTED:,.0f} kg CO₂/año '
        f'| Factor red: {CO2_FACTOR_IQUITOS} kg/kWh (MINEM)',
        fontsize=11, fontweight='bold', pad=15
    )
    plt.savefig(output_dir / 'plot_summary_table.png', dpi=150, bbox_inches='tight')
    print('✓ Guardado: plot_summary_table.png')
    plt.close()

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Ejecutar todas las gráficas."""

    print('\n' + '=' * 80)
    print('GENERADOR DE GRÁFICAS: SAC vs PPO vs A2C vs BASELINE')
    print('Fórmulas: CO₂ directo (IPCC 2006) + CO₂ indirecto (solar × 0.4521 kg/kWh)')
    print('=' * 80 + '\n')

    print('[1] Cargando resultados de entrenamiento...')
    results = load_results()
    print()

    print('[2] Generando gráficas comparativas...\n')

    plot_co2_directo_comparison(results, OUTPUT_DIR)
    plot_co2_indirecto_comparison(results, OUTPUT_DIR)
    plot_co2_total_comparison(results, OUTPUT_DIR)
    plot_vehicles_charged_comparison(results, OUTPUT_DIR)
    plot_co2_directo_evolution(results, OUTPUT_DIR)
    plot_co2_indirecto_evolution(results, OUTPUT_DIR)
    plot_vehicles_evolution(results, OUTPUT_DIR)
    plot_summary_table(results, OUTPUT_DIR)

    print('\n' + '=' * 80)
    print('GRÁFICAS GENERADAS EXITOSAMENTE')
    print('=' * 80)
    print(f'\nGuardadas en: {OUTPUT_DIR}/')
    print('\nArchivos:')
    for name in [
        'plot_co2_directo_comparison.png',
        'plot_co2_indirecto_comparison.png',
        'plot_co2_total_comparison.png',
        'plot_vehicles_charged_comparison.png',
        'plot_co2_directo_evolution.png',
        'plot_co2_indirecto_evolution.png',
        'plot_vehicles_evolution.png',
        'plot_summary_table.png',
    ]:
        path = OUTPUT_DIR / name
        status = '✓' if path.exists() else '✗'
        print(f'  {status} {name}')


if __name__ == '__main__':
    main()
