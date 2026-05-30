#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comparativa directa de F₂ (CO₂ controlado) entre agentes SAC, PPO, A2C.
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from matplotlib.patches import FancyArrowPatch
from graphics_utils import (
    C_SAC, C_PPO, C_A2C, C_BL, C_DIFF,
    load_training_data, get_output_dir, save_figure
)

# ── Carga ──────────────────────────────────────────────────────────────────────
sac, ppo, a2c = load_training_data()
OUT_DIR = get_output_dir()

# Extracción de mínimos
sac_min_val = float(sac['co2_control_kg'].min())
ppo_min_val = float(ppo['co2_control_kg'].min())
a2c_min_val = float(a2c['co2_control_kg'].min())
bl_val      = float(sac['co2_baseline_kg'].mean())

sac_min_ep  = int(sac.loc[sac['co2_control_kg'].idxmin(), 'episodio'])
ppo_min_ep  = int(ppo.loc[ppo['co2_control_kg'].idxmin(), 'episodio'])
a2c_min_ep  = int(a2c.loc[a2c['co2_control_kg'].idxmin(), 'episodio'])

# Reducciones vs baseline
red_sac = (bl_val - sac_min_val) / bl_val * 100
red_ppo = (bl_val - ppo_min_val) / bl_val * 100
red_a2c = (bl_val - a2c_min_val) / bl_val * 100

agent_rows = [
    {'name': 'SAC', 'value': sac_min_val, 'episode': sac_min_ep, 'reduction': red_sac, 'color': C_SAC},
    {'name': 'PPO', 'value': ppo_min_val, 'episode': ppo_min_ep, 'reduction': red_ppo, 'color': C_PPO},
    {'name': 'A2C', 'value': a2c_min_val, 'episode': a2c_min_ep, 'reduction': red_a2c, 'color': C_A2C},
]
best_agent = min(agent_rows, key=lambda row: row['value'])


def pair_label(name_a: str, val_a: float, name_b: str, val_b: float) -> str:
    """Etiqueta comparativa para pares de agentes; menor F2 es mejor."""
    if np.isclose(val_a, val_b):
        return f'{name_a} = {name_b}\n0 kg/año'
    winner, loser = (name_a, name_b) if val_a < val_b else (name_b, name_a)
    return f'{winner} menor que {loser}\n{abs(val_a - val_b):,.0f} kg/año'


def delta_vs_best_text(row: dict) -> str:
    delta = row['value'] - best_agent['value']
    return 'óptimo' if np.isclose(delta, 0.0) else f'+{delta:,.0f} kg'

# ─────────────────────────────────────────────────────────────────────────────
# Datos para barras
# ─────────────────────────────────────────────────────────────────────────────
agentes     = ['SAC\n(off-policy)', 'PPO\n(on-policy)', 'A2C\n(on-policy)']
valores_kg  = [sac_min_val, ppo_min_val, a2c_min_val]
colores     = [C_SAC, C_PPO, C_A2C]
epis        = [sac_min_ep, ppo_min_ep, a2c_min_ep]
reducciones = [red_sac, red_ppo, red_a2c]

# ─────────────────────────────────────────────────────────────────────────────
# FIGURA COMPLETA  (panel izq: barras absolutas | panel der: reducción vs BL)
# ─────────────────────────────────────────────────────────────────────────────
fig, (ax_abs, ax_red) = plt.subplots(1, 2, figsize=(15, 7.5),
                                      gridspec_kw={'width_ratios': [3, 2]})
fig.suptitle(
    'Figura — Comparativa directa de $F_2$ (CO₂ controlado) entre agentes SAC · PPO · A2C\n'
    'Fuente: elaboración propia en Python  ·  Iquitos, Perú  ·  Factor CO₂: 0.4521 kg/kWh',
    fontsize=12, fontweight='bold', y=1.01
)

# ── Panel izquierdo: barras absolutas ─────────────────────────────────────────
x = np.arange(len(agentes))
bars = ax_abs.bar(x, valores_kg, width=0.50, color=colores, edgecolor='white',
                  linewidth=1.5, zorder=3)

# Línea baseline horizontal
ax_abs.axhline(bl_val, color=C_BL, lw=2.0, ls='--', alpha=0.85, zorder=2,
               label=f'Baseline (sin control): {bl_val/1e6:.3f} M kg/año')

# Área sombreada reducción
for i, (bar, val) in enumerate(zip(bars, valores_kg)):
    ax_abs.fill_between(
        [bar.get_x(), bar.get_x() + bar.get_width()],
        val, bl_val,
        alpha=0.08, color=colores[i], zorder=1
    )

# Etiquetas sobre barras
for i, (bar, val, ep, red) in enumerate(zip(bars, valores_kg, epis, reducciones)):
    ax_abs.text(
        bar.get_x() + bar.get_width() / 2,
        val + 15_000,
        f'{val/1e6:.4f} M kg\n(ep. {ep}  ·  −{red:.1f}% vs BL)',
        ha='center', va='bottom', fontsize=10, fontweight='bold', color=colores[i]
    )

# ── Flechas de diferencia SAC → PPO y SAC → A2C ──────────────────────────────
# Cotada entre barra SAC y PPO
y_cota_1 = min(sac_min_val, ppo_min_val) - 140_000
ax_abs.annotate(
    '', xy=(x[0], sac_min_val - 30_000),
    xytext=(x[1], ppo_min_val - 30_000),
    arrowprops=dict(arrowstyle='<->', color=C_DIFF, lw=2.0,
                    connectionstyle='arc3,rad=0.0')
)
ax_abs.text(
    (x[0] + x[1]) / 2, min(sac_min_val, ppo_min_val) - 90_000,
    pair_label('SAC', sac_min_val, 'PPO', ppo_min_val),
    ha='center', va='top', fontsize=10, color=C_DIFF, fontweight='bold',
    bbox=dict(boxstyle='round,pad=0.35', fc='#F4ECF7', ec=C_DIFF, lw=1.2, alpha=0.95)
)

# Cotada entre barra SAC y A2C
ax_abs.annotate(
    '', xy=(x[0], sac_min_val - 200_000),
    xytext=(x[2], a2c_min_val - 200_000),
    arrowprops=dict(arrowstyle='<->', color='#404040', lw=1.8,
                    connectionstyle='arc3,rad=0.0')
)
ax_abs.text(
    (x[0] + x[2]) / 2, sac_min_val - 270_000,
    pair_label('SAC', sac_min_val, 'A2C', a2c_min_val),
    ha='center', va='top', fontsize=10, color='#404040', fontweight='bold',
    bbox=dict(boxstyle='round,pad=0.35', fc='#F5F5F5', ec='#404040', lw=1.2, alpha=0.95)
)

ax_abs.set_xticks(x)
ax_abs.set_xticklabels(agentes, fontsize=12)
ax_abs.set_ylabel('$F_2$ — CO₂ anual mínimo logrado (kg CO₂/año)', fontsize=11)
ax_abs.set_title('$F_2$ mínimo absoluto por agente vs Baseline', fontsize=12, fontweight='bold')
ax_abs.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v/1e6:.3f} M'))
y_min_ax = min(valores_kg) - 400_000
y_max_ax = bl_val + 250_000
ax_abs.set_ylim(y_min_ax, y_max_ax)
ax_abs.grid(True, axis='y', alpha=0.3, linestyle='--', zorder=0)
ax_abs.legend(fontsize=10, loc='upper left')
ax_abs.spines[['top', 'right']].set_visible(False)

# ── Panel derecho: reducción porcentual vs baseline ────────────────────────────
bar_red = ax_red.barh(agentes[::-1], reducciones[::-1], color=colores[::-1],
                       height=0.45, edgecolor='white', linewidth=1.5, zorder=3)

# Etiquetas
for bar, red, val in zip(bar_red, reducciones[::-1], valores_kg[::-1]):
    ax_red.text(
        bar.get_width() + 0.3,
        bar.get_y() + bar.get_height() / 2,
        f'−{red:.1f}%  ({val/1e6:.4f} M kg)',
        va='center', fontsize=10, fontweight='bold',
        color=bar.get_facecolor()
    )

ax_red.set_xlabel('Reducción de CO₂ vs Baseline (%)', fontsize=11)
ax_red.set_title('Reducción relativa de $F_2$ vs Baseline\n(sin control de agente RL)',
                 fontsize=12, fontweight='bold')
ax_red.set_xlim(0, max(reducciones) + 10)
ax_red.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:.1f}%'))
ax_red.grid(True, axis='x', alpha=0.3, linestyle='--', zorder=0)
ax_red.spines[['top', 'right']].set_visible(False)

delta_lines = [
    f"  {row['name']}: {delta_vs_best_text(row)}"
    for row in sorted(agent_rows, key=lambda item: item['value'])
]
resumen = (
    f"Agente óptimo F₂:\n"
    f"  {best_agent['name']} = {best_agent['value']:,.0f} kg CO₂/año\n"
    f"  ep. {best_agent['episode']} · −{best_agent['reduction']:.1f}% vs BL\n\n"
    f"Diferencia vs óptimo:\n"
    + "\n".join(delta_lines) + "\n\n"
    f"Factor CO₂: 0.4521 kg/kWh\n"
    f"Red Iquitos (generación térmica)"
)
ax_red.text(
    0.04, 0.04, resumen,
    transform=ax_red.transAxes, fontsize=9, family='monospace',
    verticalalignment='bottom',
    bbox=dict(boxstyle='round,pad=0.5', fc='white', ec='#AAAAAA', lw=1.0, alpha=0.93)
)

fig.tight_layout(pad=2.5)
path_full = OUT_DIR / 'figura_f2_comparativa_directa.png'
fig.savefig(path_full, dpi=300, bbox_inches='tight')
plt.close(fig)
print(f'✓  Figura comparativa F₂ (completa) → {path_full}')

# ─────────────────────────────────────────────────────────────────────────────
# FIGURA COMPACTA  (1 panel barras + anotaciones de diferencia)
# ─────────────────────────────────────────────────────────────────────────────
fig2, ax = plt.subplots(figsize=(11, 6.5))

# Incluir baseline como 4ª barra en gris
agentes_c  = ['Baseline\n(sin control)', 'SAC\n(off-policy)', 'PPO\n(on-policy)', 'A2C\n(on-policy)']
valores_c  = [bl_val, sac_min_val, ppo_min_val, a2c_min_val]
colores_c  = ['#AAAAAA', C_SAC, C_PPO, C_A2C]
epis_c     = ['—', sac_min_ep, ppo_min_ep, a2c_min_ep]
reduc_c    = [0.0, red_sac, red_ppo, red_a2c]

xc = np.arange(len(agentes_c))
bars2 = ax.bar(xc, valores_c, width=0.55, color=colores_c,
               edgecolor='white', linewidth=1.8, zorder=3)

# Etiquetas sobre barras
for i, (bar, val, ep, red) in enumerate(zip(bars2, valores_c, epis_c, reduc_c)):
    lbl = (f'{val/1e6:.4f} M kg/año'
           if i == 0
           else f'{val/1e6:.4f} M kg/año\n(ep. {ep}  ·  −{red:.1f}%)')
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        val + 25_000,
        lbl,
        ha='center', va='bottom', fontsize=9.5, fontweight='bold',
        color=colores_c[i]
    )

# Línea de baseline
ax.axhline(bl_val, color='#AAAAAA', lw=1.5, ls='--', alpha=0.6, zorder=2)

# ── Diferencia SAC–PPO (flecha horizontal con corchetes) ──────────────────────
y_d1 = sac_min_val - 120_000
ax.annotate('', xy=(xc[1], y_d1), xytext=(xc[2], y_d1),
            arrowprops=dict(arrowstyle='<->', color=C_DIFF, lw=2.2,
                            connectionstyle='arc3,rad=0.0'))
ax.text((xc[1] + xc[2]) / 2, y_d1 - 55_000,
        pair_label('SAC', sac_min_val, 'PPO', ppo_min_val),
        ha='center', va='top', fontsize=10, color=C_DIFF, fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.35', fc='#F4ECF7', ec=C_DIFF, lw=1.2, alpha=0.95))

# ── Diferencia SAC–A2C ────────────────────────────────────────────────────────
y_d2 = sac_min_val - 270_000
ax.annotate('', xy=(xc[1], y_d2), xytext=(xc[3], y_d2),
            arrowprops=dict(arrowstyle='<->', color='#404040', lw=2.0,
                            connectionstyle='arc3,rad=0.0'))
ax.text((xc[1] + xc[3]) / 2, y_d2 - 55_000,
        pair_label('SAC', sac_min_val, 'A2C', a2c_min_val),
        ha='center', va='top', fontsize=10, color='#404040', fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.35', fc='#F5F5F5', ec='#404040', lw=1.2, alpha=0.95))

ax.set_xticks(xc)
ax.set_xticklabels(agentes_c, fontsize=11)
ax.set_ylabel('$F_2$ — CO₂ anual mínimo (kg CO₂/año)', fontsize=11)
ax.set_title(
    'Comparativa directa de $F_2$ (CO₂ controlado, kg CO₂/año) entre agentes\n'
    f'{best_agent["name"]} logra el mínimo absoluto  ·  '
    'Fuente: elaboración propia en Python  ·  Iquitos, Perú  ·  50 episodios',
    fontsize=11, fontweight='bold'
)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v/1e6:.3f} M'))
ax.set_ylim(min(valores_kg) - 550_000, bl_val + 400_000)
ax.grid(True, axis='y', alpha=0.3, linestyle='--', zorder=0)
ax.spines[['top', 'right']].set_visible(False)

# Cuadro datos en esquina superior derecha
info_lines = [
    f"{'Agente':<9} {'F₂ mínimo':>14}  {'Δ vs óptimo':>14}  {'% reducción':>11}",
    f"{'─'*58}",
    f"{'Baseline':<9} {bl_val:>12,.0f} kg  {'—':>14}  {'—':>11}",
]
for row in agent_rows:
    info_lines.append(
        f"{row['name']:<9} {row['value']:>12,.0f} kg  "
        f"{delta_vs_best_text(row):>14}  −{row['reduction']:>8.1f}%"
    )
info2 = "\n".join(info_lines)
ax.text(
    0.50, 0.98, info2,
    transform=ax.transAxes, fontsize=8.5, family='monospace',
    verticalalignment='top', ha='left',
    bbox=dict(boxstyle='round,pad=0.5', fc='white', ec='#AAAAAA', lw=1.0, alpha=0.95)
)

fig2.tight_layout()
path_compact = OUT_DIR / 'figura_f2_comparativa_directa_compact.png'
fig2.savefig(path_compact, dpi=300, bbox_inches='tight')
plt.close(fig2)
print(f'✓  Figura comparativa F₂ (compacta)  → {path_compact}')

# ── Resumen consola ────────────────────────────────────────────────────────────
print()
print('═══ Comparativa directa F₂ ═══')
print(f'  SAC  mín ep.{sac_min_ep:>2}: {sac_min_val:>13,.0f} kg CO₂/año  −{red_sac:.1f}% vs BL')
print(f'  PPO  mín ep.{ppo_min_ep:>2}: {ppo_min_val:>13,.0f} kg CO₂/año  −{red_ppo:.1f}% vs BL')
print(f'  A2C  mín ep.{a2c_min_ep:>2}: {a2c_min_val:>13,.0f} kg CO₂/año  −{red_a2c:.1f}% vs BL')
print(f'  Baseline:      {bl_val:>13,.0f} kg CO₂/año')
print(f'  ─────────────────────────────────────────────────')
print(f'  Óptimo: {best_agent["name"]} ep.{best_agent["episode"]} -> {best_agent["value"]:,.0f} kg CO₂/año')
for row in sorted(agent_rows, key=lambda item: item['value']):
    delta = row['value'] - best_agent['value']
    print(f'  Δ {row["name"]} vs óptimo: {delta:>10,.0f} kg/año')
