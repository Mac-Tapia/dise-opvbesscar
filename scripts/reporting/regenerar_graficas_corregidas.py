#!/usr/bin/env python3
"""
Script: Regenerar gráficas corregidas de SAC, A2C y CO2 directo.

Fixes aplicados:
  1. kpi_dashboard SAC/A2C: encoding CO2 (COÔéé → CO2)
  2. sac_dashboard paneles vacíos: reconstruir desde datos del JSON por episodio
  3. a2c_dashboard flatlines: reconstruir desde datos del JSON por episodio
  4. plot_co2_directo_evolution: quitar offset matplotlib (useOffset=False + ylim desde 0)

Uso: python scripts/regenerar_graficas_corregidas.py
"""
from __future__ import annotations

import json
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

# ─── Rutas ────────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parents[1]
SAC_DIR  = BASE / 'outputs' / 'sac_training'
A2C_DIR  = BASE / 'outputs' / 'a2c_training'
PPO_DIR  = BASE / 'outputs' / 'ppo_training'
OUT_DIR  = BASE / 'outputs'

SAC_JSON  = SAC_DIR / 'result_sac.json'
A2C_JSON  = A2C_DIR / 'result_a2c.json'
PPO_JSON  = PPO_DIR / 'result_ppo.json'
BASELINE_JSON = BASE / 'checkpoints' / 'Baseline' / 'baseline_results.json'

# ─── Training stats JSONs (métricas por paso) ─────────────────────────────────
SAC_STATS = SAC_DIR / 'training_stats_SAC.json'

# ─── Helpers ──────────────────────────────────────────────────────────────────
def load_json(path: Path) -> dict:
    if not path.exists():
        print(f'  [!] No encontrado: {path}')
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def smooth(data: list, window: int = 5) -> np.ndarray:
    if len(data) < window:
        return np.array(data)
    return pd.Series(data).rolling(window=window, min_periods=1).mean().to_numpy()


def episodes_axis(n: int) -> np.ndarray:
    return np.arange(1, n + 1)


# ═══════════════════════════════════════════════════════════════════════════════
# FIX 1 y 2: SAC KPI Dashboard (encoding CO2 + datos correctos)
# ═══════════════════════════════════════════════════════════════════════════════
def regenerar_kpi_dashboard_sac(data: dict) -> None:
    ev = data.get('training_evolution', {})
    consumption = ev.get('episode_grid_import', [])       # kWh/ep proxy
    cost        = ev.get('episode_cost_usd', [])
    emissions   = ev.get('episode_co2_grid', [])          # kg CO2 grid/ep
    ramping     = ev.get('episode_grid_stability', [])    # estabilidad (proxy ramping)
    socket_util = ev.get('episode_socket_utilization', [])
    ev_charge   = ev.get('episode_ev_charging', [])

    n = max(len(consumption), len(cost), len(emissions), 2)
    steps_ep = episodes_axis(n)

    fig, axes = plt.subplots(2, 3, figsize=(16, 10))

    def plot_panel(ax, data_list, color, title, ylabel, ylim_bottom=None):
        if data_list:
            eps = episodes_axis(len(data_list))
            ax.plot(eps, data_list, color=color, alpha=0.4, linewidth=0.8, label='Raw')
            ax.plot(eps, smooth(data_list), color=color, linewidth=2, label='Smoothed')
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.set_xlabel('Episodio')
        ax.grid(True, alpha=0.3)
        ax.set_ylabel(ylabel, fontsize=9)
        if ylim_bottom is not None:
            ax.set_ylim(bottom=ylim_bottom)
        ax.ticklabel_format(useOffset=False, axis='y')
        ax.legend(fontsize=8)

    plot_panel(axes[0, 0], consumption, 'steelblue',   'Grid Import (kWh/ep)',     'kWh/episodio', 0)
    plot_panel(axes[0, 1], cost,        'forestgreen', 'Cost (USD/ep)',             'USD/episodio', 0)
    plot_panel(axes[0, 2], emissions,   'saddlebrown', 'CO2 Grid Emissions (kg/ep)', 'kg CO2/ep',  0)
    plot_panel(axes[1, 0], ramping,     'purple',      'Grid Stability (0→1)',      'Estabilidad', 0)
    plot_panel(axes[1, 1], socket_util, 'crimson',     'Socket Utilization (0→1)', 'Utilización', 0)
    plot_panel(axes[1, 2], ev_charge,   'darkorange',  'EV Charging (kWh/ep)',      'kWh/episodio', 0)

    # Calcular mejoras
    improvements = []
    for label, arr in [('Grid Import', consumption), ('CO2', emissions), ('Cost', cost)]:
        if len(arr) > 1 and arr[0] != 0:
            imp = (arr[0] - arr[-1]) / abs(arr[0]) * 100
            if imp > 0:
                improvements.append(f'{label}: {imp:.1f}%↓')

    title = 'CityLearn KPIs Dashboard - SAC Training'
    if improvements:
        title += f'\n✓ Mejoras: {", ".join(improvements)}'

    fig.suptitle(title, fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = SAC_DIR / 'kpi_dashboard.png'
    plt.savefig(out, dpi=150)
    plt.close(fig)
    print(f'  ✓ Regenerado: {out.relative_to(BASE)}')


# ═══════════════════════════════════════════════════════════════════════════════
# FIX 1 y 3: SAC Dashboard (paneles vacíos → datos por episodio)
# ═══════════════════════════════════════════════════════════════════════════════
def regenerar_sac_dashboard(data: dict, stats: dict) -> None:
    ev = data.get('training_evolution', {})

    # Métricas por episodio disponibles en result_sac.json
    rewards          = ev.get('episode_rewards', [])
    co2_avoided_dir  = ev.get('episode_co2_avoided_direct', [])
    co2_avoided_ind  = ev.get('episode_co2_avoided_indirect', [])
    grid_import      = ev.get('episode_grid_import', [])
    bess_discharge   = ev.get('episode_bess_discharge_kwh', [])
    socket_util      = ev.get('episode_socket_utilization', [])

    # Métricas por checkpoint desde training_stats_SAC.json (si existe)
    actor_loss_hist  = stats.get('actor_loss', [])
    critic_loss_hist = stats.get('critic_loss', [])
    ent_coef_hist    = stats.get('ent_coef', [])
    grad_norm_hist   = stats.get('grad_norm', [])

    fig, axes = plt.subplots(2, 3, figsize=(16, 10))

    def safe_plot(ax, data_list, color, title, use_smooth=True):
        if data_list:
            eps = episodes_axis(len(data_list))
            ax.plot(eps, data_list, color=color, alpha=0.35, linewidth=0.8)
            if use_smooth and len(data_list) >= 3:
                ax.plot(eps, smooth(data_list), color=color, linewidth=2)
        else:
            ax.text(0.5, 0.5, 'Sin datos\n(no registrado durante training)',
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=10, color='gray', style='italic')
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.set_xlabel('Episodio' if not actor_loss_hist or data_list is not actor_loss_hist else 'Checkpoint')
        ax.grid(True, alpha=0.3)
        ax.ticklabel_format(useOffset=False, axis='y')

    safe_plot(axes[0, 0], rewards,         'steelblue',  'Reward por Episodio')
    safe_plot(axes[0, 1], co2_avoided_ind, 'forestgreen','CO2 Indirecto Evitado (kg/ep)')
    safe_plot(axes[0, 2], co2_avoided_dir, 'saddlebrown','CO2 Directo Evitado (kg/ep)')
    safe_plot(axes[1, 0], grid_import,     'purple',     'Grid Import (kWh/ep)')
    safe_plot(axes[1, 1], bess_discharge,  'crimson',    'BESS Descarga (kWh/ep)')
    safe_plot(axes[1, 2], socket_util,     'darkorange', 'Socket Utilization (0→1)')

    val_reward = data.get('validation', {}).get('mean_reward', 0)
    fig.suptitle(f'SAC Training Dashboard — 50 episodios | Val Reward: {val_reward:.2f}',
                 fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = SAC_DIR / 'sac_dashboard.png'
    plt.savefig(out, dpi=150)
    plt.close(fig)
    print(f'  ✓ Regenerado: {out.relative_to(BASE)}')


# ═══════════════════════════════════════════════════════════════════════════════
# FIX 1 y 3: A2C KPI Dashboard + A2C Dashboard
# ═══════════════════════════════════════════════════════════════════════════════
def regenerar_kpi_dashboard_a2c(data: dict) -> None:
    ev = data.get('training_evolution', {})
    consumption = ev.get('episode_grid_import', [])
    cost        = ev.get('episode_cost_usd', [])
    emissions   = ev.get('episode_co2_grid', [])
    stability   = ev.get('episode_grid_stability', [])
    socket_util = ev.get('episode_socket_utilization', [])
    ev_charge   = ev.get('episode_ev_charging', [])

    fig, axes = plt.subplots(2, 3, figsize=(16, 10))

    def plot_panel(ax, data_list, color, title, ylabel, ylim_bottom=None):
        if data_list:
            eps = episodes_axis(len(data_list))
            ax.plot(eps, data_list, color=color, alpha=0.4, linewidth=0.8, label='Raw')
            ax.plot(eps, smooth(data_list), color=color, linewidth=2, label='Smoothed')
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.set_xlabel('Episodio')
        ax.grid(True, alpha=0.3)
        ax.set_ylabel(ylabel, fontsize=9)
        if ylim_bottom is not None:
            ax.set_ylim(bottom=ylim_bottom)
        ax.ticklabel_format(useOffset=False, axis='y')
        ax.legend(fontsize=8)

    plot_panel(axes[0, 0], consumption, 'steelblue',   'Grid Import (kWh/ep)',      'kWh/episodio', 0)
    plot_panel(axes[0, 1], cost,        'forestgreen', 'Cost (USD/ep)',              'USD/episodio', 0)
    plot_panel(axes[0, 2], emissions,   'saddlebrown', 'CO2 Grid Emissions (kg/ep)', 'kg CO2/ep',   0)
    plot_panel(axes[1, 0], stability,   'purple',      'Grid Stability (0→1)',       'Estabilidad', 0)
    plot_panel(axes[1, 1], socket_util, 'crimson',     'Socket Utilization (0→1)',   'Utilización', 0)
    plot_panel(axes[1, 2], ev_charge,   'darkorange',  'EV Charging (kWh/ep)',       'kWh/episodio', 0)

    improvements = []
    for label, arr in [('Grid Import', consumption), ('CO2', emissions), ('Cost', cost)]:
        if len(arr) > 1 and arr[0] != 0:
            imp = (arr[0] - arr[-1]) / abs(arr[0]) * 100
            if imp > 0:
                improvements.append(f'{label}: {imp:.1f}%↓')

    title = 'CityLearn KPIs Dashboard - A2C Training'
    if improvements:
        title += f'\n✓ Mejoras: {", ".join(improvements)}'

    fig.suptitle(title, fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = A2C_DIR / 'kpi_dashboard.png'
    plt.savefig(out, dpi=150)
    plt.close(fig)
    print(f'  ✓ Regenerado: {out.relative_to(BASE)}')


def regenerar_a2c_dashboard(data: dict) -> None:
    ev = data.get('training_evolution', {})
    rewards         = ev.get('episode_rewards', [])
    co2_avoided_dir = ev.get('episode_co2_avoided_direct', [])
    co2_avoided_ind = ev.get('episode_co2_avoided_indirect', [])
    grid_import     = ev.get('episode_grid_import', [])
    bess_discharge  = ev.get('episode_bess_discharge_kwh', [])
    socket_util     = ev.get('episode_socket_utilization', [])

    fig, axes = plt.subplots(2, 3, figsize=(16, 10))

    def safe_plot(ax, data_list, color, title):
        if data_list:
            eps = episodes_axis(len(data_list))
            ax.plot(eps, data_list, color=color, alpha=0.35, linewidth=0.8)
            if len(data_list) >= 3:
                ax.plot(eps, smooth(data_list), color=color, linewidth=2)
        else:
            ax.text(0.5, 0.5, 'Sin datos\n(no registrado durante training)',
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=10, color='gray', style='italic')
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.set_xlabel('Episodio')
        ax.grid(True, alpha=0.3)
        ax.ticklabel_format(useOffset=False, axis='y')

    safe_plot(axes[0, 0], rewards,         'steelblue',  'Reward por Episodio')
    safe_plot(axes[0, 1], co2_avoided_ind, 'forestgreen','CO2 Indirecto Evitado (kg/ep)')
    safe_plot(axes[0, 2], co2_avoided_dir, 'saddlebrown','CO2 Directo Evitado (kg/ep)')
    safe_plot(axes[1, 0], grid_import,     'purple',     'Grid Import (kWh/ep)')
    safe_plot(axes[1, 1], bess_discharge,  'crimson',    'BESS Descarga (kWh/ep)')
    safe_plot(axes[1, 2], socket_util,     'darkorange', 'Socket Utilization (0→1)')

    val_reward = data.get('validation', {}).get('mean_reward', 0)
    fig.suptitle(f'A2C Training Dashboard — 50 episodios | Val Reward: {val_reward:.2f}',
                 fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = A2C_DIR / 'a2c_dashboard.png'
    plt.savefig(out, dpi=150)
    plt.close(fig)
    print(f'  ✓ Regenerado: {out.relative_to(BASE)}')


# ═══════════════════════════════════════════════════════════════════════════════
# FIX 4: plot_co2_directo_evolution (sin offset)
# ═══════════════════════════════════════════════════════════════════════════════
def regenerar_co2_directo_evolution(sac: dict, ppo: dict, a2c: dict, baseline: dict) -> None:
    AGENTS_CFG = {
        'SAC': ('#1f77b4', sac),
        'PPO': ('#ff7f0e', ppo),
        'A2C': ('#2ca02c', a2c),
    }
    baseline_direct = (baseline.get('annual_co2_kg', {})
                                .get('co2_reduccion_directa_baseline', 330029.7))

    fig, ax = plt.subplots(figsize=(12, 6))
    has_data = False

    for agent_name, (color, data) in AGENTS_CFG.items():
        evolution = (data.get('training_evolution', {})
                        .get('episode_co2_avoided_direct', []))
        if evolution:
            eps = episodes_axis(len(evolution))
            ax.plot(list(eps), evolution, marker='o', label=agent_name, linewidth=2.5,
                    color=color, markersize=4, markeredgecolor='black', markeredgewidth=0.5)
            has_data = True

    if has_data:
        ax.axhline(y=baseline_direct, color='#d62728', linestyle='--', linewidth=2,
                   alpha=0.8, label=f'Baseline: {baseline_direct:,.0f} kg/año')
        ax.set_xlabel('Episodio (1 ep = 1 año)', fontsize=12, fontweight='bold')
        ax.set_ylabel('CO₂ Directo Evitado (kg/ep)', fontsize=12, fontweight='bold')
        ax.set_title('Evolución CO₂ Directo por Episodio: SAC vs PPO vs A2C vs Baseline',
                     fontsize=13, fontweight='bold')
        ax.legend(fontsize=11, loc='best')
        ax.grid(True, alpha=0.3, linestyle='--')

        # ── FIX CLAVE: quitar offset automático de matplotlib ──────────────
        ax.ticklabel_format(useOffset=False, axis='y', style='plain')
        # Forzar ylim desde 0 para mostrar escala real
        all_vals = [baseline_direct]
        for _, data in AGENTS_CFG.values():
            ev = data.get('training_evolution', {}).get('episode_co2_avoided_direct', [])
            all_vals.extend(ev)
        y_max = max(all_vals) * 1.15
        ax.set_ylim(0, y_max)

        # Formato de miles en eje Y
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f'{x:,.0f}')
        )

        plt.tight_layout()
        out = OUT_DIR / 'plot_co2_directo_evolution.png'
        plt.savefig(out, dpi=150, bbox_inches='tight')
        print(f'  ✓ Regenerado: {out.relative_to(BASE)}')

    plt.close()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main() -> None:
    print('=' * 60)
    print('REGENERAR GRÁFICAS CORREGIDAS — pvbesscar')
    print('=' * 60)

    sac_data  = load_json(SAC_JSON)
    a2c_data  = load_json(A2C_JSON)
    ppo_data  = load_json(PPO_JSON)
    baseline  = load_json(BASELINE_JSON)
    sac_stats = load_json(SAC_STATS) if SAC_STATS.exists() else {}

    print('\n[1/4] KPI Dashboard SAC (encoding CO2 + datos por episodio)...')
    if sac_data:
        regenerar_kpi_dashboard_sac(sac_data)
    else:
        print('  [!] Sin datos SAC')

    print('\n[2/4] SAC Dashboard (paneles desde datos de episodio)...')
    if sac_data:
        regenerar_sac_dashboard(sac_data, sac_stats)
    else:
        print('  [!] Sin datos SAC')

    print('\n[3/4] KPI Dashboard A2C (encoding CO2 + datos por episodio)...')
    if a2c_data:
        regenerar_kpi_dashboard_a2c(a2c_data)
    else:
        print('  [!] Sin datos A2C')

    print('\n[4/4] A2C Dashboard (datos por episodio)...')
    if a2c_data:
        regenerar_a2c_dashboard(a2c_data)
    else:
        print('  [!] Sin datos A2C')

    print('\n[5/5] CO2 Directo Evolution (sin offset matplotlib)...')
    regenerar_co2_directo_evolution(sac_data, ppo_data, a2c_data, baseline)

    print('\n' + '=' * 60)
    print('✓ Todas las gráficas regeneradas correctamente.')
    print('=' * 60)


if __name__ == '__main__':
    main()
