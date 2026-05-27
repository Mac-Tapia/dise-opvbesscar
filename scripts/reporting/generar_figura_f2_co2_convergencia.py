#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convergencia de los tres agentes (SAC, PPO, A2C) — F₂ (kg CO₂/año) por episodio.
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
from graphics_utils import (
    C_SAC, C_PPO, C_A2C,
    load_training_data, smooth, get_output_dir, save_figure
)

# ── Carga ─────────────────────────────────────────────────────────────────────
sac, ppo, a2c = load_training_data()
EPS = sac['episodio'].values
OUT_DIR = get_output_dir()

# F₂ = CO₂ total anual bajo control (M kg)
f2_sac = sac['co2_control_kg'].values / 1e6
f2_ppo = ppo['co2_control_kg'].values / 1e6
f2_a2c = a2c['co2_control_kg'].values / 1e6

# ── Mínimos verificados ────────────────────────────────────────────────────────
sac_min_ep  = int(EPS[np.argmin(f2_sac)])   # ep 48
ppo_min_ep  = int(EPS[np.argmin(f2_ppo)])   # ep 40
a2c_min_ep  = int(EPS[np.argmin(f2_a2c)])   # ep 3
sac_min_val = float(np.min(f2_sac))
ppo_min_val = float(np.min(f2_ppo))
a2c_min_val = float(np.min(f2_a2c))

# ─────────────────────────────────────────────────────────────────────────────
# FIGURA COMPLETA (4 paneles)
# ─────────────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(17, 11))
gs  = plt.GridSpec(2, 3, figure=fig, hspace=0.46, wspace=0.33)

ax_main = fig.add_subplot(gs[0, :])   # panel superior: comparativa global
ax_sac  = fig.add_subplot(gs[1, 0])   # detalle SAC
ax_ppo  = fig.add_subplot(gs[1, 1])   # detalle PPO
ax_a2c  = fig.add_subplot(gs[1, 2])   # detalle A2C

fig.suptitle(
    'Convergencia de emisiones CO₂ — $F_2$ (kg CO₂/año) por episodio\n'
    'SAC vs PPO vs A2C  ·  50 episodios  ·  438 000 pasos  ·  Iquitos pvbesscar  ·  '
    'Fuente: elaboración propia en Python',
    fontsize=12, fontweight='bold', y=1.01
)

# ─────────────────────────────────────────────────────────────────────────────
# Panel Superior: comparativa global
# ─────────────────────────────────────────────────────────────────────────────
agents_main = [
    (f2_sac, C_SAC, 'SAC (off-policy)', '-',  sac_min_ep, sac_min_val),
    (f2_ppo, C_PPO, 'PPO (on-policy)',  '--', ppo_min_ep, ppo_min_val),
    (f2_a2c, C_A2C, 'A2C (on-policy)', ':',  a2c_min_ep, a2c_min_val),
]

for f2, color, label, ls, min_ep, min_val in agents_main:
    f2_sm = smooth(f2)
    ax_main.plot(EPS, f2,    color=color, lw=0.9, alpha=0.30, ls=ls)
    ax_main.plot(EPS, f2_sm, color=color, lw=2.5, ls=ls, label=label)
    # Marcador de mínimo
    ax_main.plot(min_ep, min_val, 'o', color=color, ms=8, zorder=5,
                 markeredgecolor='white', markeredgewidth=1.5)
    offset_x = -18 if color != C_A2C else 4
    offset_y = 10  if color == C_PPO else -22
    ax_main.annotate(
        f'Mín ep.{min_ep}\n{min_val:.3f} M kg',
        xy=(min_ep, min_val),
        xytext=(offset_x, offset_y if color != C_SAC else -26),
        textcoords='offset points',
        fontsize=9, color=color, fontweight='bold',
        arrowprops=dict(arrowstyle='->', color=color, lw=1.2),
        bbox=dict(boxstyle='round,pad=0.25', fc='white', ec=color, lw=0.8, alpha=0.85)
    )

# Línea de referencia baseline (co2_baseline promedio)
bl_sac = float(sac['co2_baseline_kg'].mean()) / 1e6
ax_main.axhline(bl_sac, color='#D62728', lw=1.4, ls='-.', alpha=0.7,
                label=f'Baseline sin control: {bl_sac:.2f} M kg')

ax_main.set_xlabel('Episodio  (1 ep = 8 760 pasos horarios  ·  Δt = 1 h)', fontsize=11)
ax_main.set_ylabel('$F_2$ — CO₂ anual bajo control (millones kg CO₂/año)', fontsize=11)
ax_main.set_title('Curvas de convergencia CO₂ — todos los agentes vs baseline',
                  fontsize=12)
ax_main.set_xlim(1, 50)
ax_main.xaxis.set_major_locator(mticker.MultipleLocator(5))
ax_main.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:.2f}'))
ax_main.grid(True, alpha=0.3, linestyle='--')
ax_main.legend(fontsize=10, loc='upper right')

# Región explotación (eps > 10)
ax_main.axvspan(1, 3, color='grey', alpha=0.07)
ax_main.text(1.3, float(np.max(f2_sac[0:5])) * 0.995,
             'Exploración', fontsize=8, color='grey', va='top')

# Caja comparativa
sac_ep50 = float(f2_sac[-1])
ppo_ep50 = float(f2_ppo[-1])
a2c_ep50 = float(f2_a2c[-1])

tabla = (
    f"{'Agente':<8}  {'F₂ ep50':>10}  {'F₂ min':>10}  {'ep min':>6}  {'Δ vs BL':>9}\n"
    f"{'─'*54}\n"
    f"SAC      {sac_ep50:>8.3f} M  {sac_min_val:>8.3f} M  ep {sac_min_ep:>2}  "
    f"{(bl_sac - sac_min_val)/bl_sac*100:>6.1f}%↓\n"
    f"PPO      {ppo_ep50:>8.3f} M  {ppo_min_val:>8.3f} M  ep {ppo_min_ep:>2}  "
    f"{(bl_sac - ppo_min_val)/bl_sac*100:>6.1f}%↓\n"
    f"A2C      {a2c_ep50:>8.3f} M  {a2c_min_val:>8.3f} M  ep {a2c_min_ep:>2}  "
    f"{(bl_sac - a2c_min_val)/bl_sac*100:>6.1f}%↓\n"
    f"{'─'*54}\n"
    f"Factor CO₂: 0.4521 kg/kWh  ·  Red Iquitos (térmica)"
)
ax_main.text(
    0.01, 0.99, tabla,
    transform=ax_main.transAxes,
    fontsize=8.2, family='monospace',
    verticalalignment='top',
    bbox=dict(boxstyle='round,pad=0.5', fc='#FAFAFA', ec='#CCCCCC', lw=1.0, alpha=0.93)
)

# ─────────────────────────────────────────────────────────────────────────────
# Paneles inferiores: detalle por agente
# ─────────────────────────────────────────────────────────────────────────────
def _panel_detalle(ax, f2, color, label, min_ep, min_val, zoom_from: int, ls='-'):
    """Dibuja detalle de convergencia para un agente."""
    mask = EPS >= zoom_from
    f2_sm = smooth(f2)

    ax.plot(EPS[mask], f2[mask],    color=color, lw=1.0, alpha=0.38, ls=ls, label='F₂ raw')
    ax.plot(EPS[mask], f2_sm[mask], color=color, lw=2.4, ls=ls, label=f'Suavizado (w=5)')

    # Mínimo si está en el rango
    if min_ep >= zoom_from:
        ax.plot(min_ep, min_val, 'o', color=color, ms=9, zorder=5,
                markeredgecolor='white', markeredgewidth=1.8)
        ax.annotate(
            f'Mín ep.{min_ep}\n{min_val:.3f} M kg',
            xy=(min_ep, min_val),
            xytext=(8, 10), textcoords='offset points',
            fontsize=9, color=color, fontweight='bold',
            arrowprops=dict(arrowstyle='->', color=color, lw=1.1),
            bbox=dict(boxstyle='round,pad=0.25', fc='white', ec=color, lw=0.8)
        )

    # Línea de tendencia horizontal (media últimos 10 eps en rango)
    mu_last = float(np.mean(f2[-10:]))
    ax.axhline(mu_last, color=color, lw=1.3, ls='--', alpha=0.65)
    ax.text(zoom_from + 0.5, mu_last * 1.0002,
            f'μ(ult.10)={mu_last:.3f} M',
            fontsize=8.5, color=color)

    ax.set_xlabel('Episodio', fontsize=10)
    ax.set_ylabel('$F_2$ (M kg CO₂/año)', fontsize=10)
    ax.set_title(f'{label} — Detalle ep. {zoom_from}–50',
                 fontsize=11, color=color, fontweight='bold')
    ax.set_xlim(zoom_from, 50)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(5))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:.3f}'))
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=8.5, loc='upper right')


# SAC: mínimo en ep 48 → zoom desde ep 35
_panel_detalle(ax_sac, f2_sac, C_SAC, 'SAC',
               sac_min_ep, sac_min_val, zoom_from=35)

# Anotación narrativa SAC
ax_sac.text(
    0.04, 0.10, 'Off-policy: replay\nbuffer permite\nrefinar hasta ep. 48',
    transform=ax_sac.transAxes, fontsize=8, color=C_SAC, style='italic',
    bbox=dict(boxstyle='round,pad=0.3', fc='#EBF3FD', ec=C_SAC, lw=0.8, alpha=0.85)
)

# PPO: descenso hasta ep 40 → zoom desde ep 1
_panel_detalle(ax_ppo, f2_ppo, C_PPO, 'PPO',
               ppo_min_ep, ppo_min_val, zoom_from=1, ls='--')

# Flecha descenso sostenido PPO
ax_ppo.annotate(
    '', xy=(ppo_min_ep, ppo_min_val),
    xytext=(5, float(f2_ppo[4])),
    arrowprops=dict(arrowstyle='->', color=C_PPO, lw=1.5,
                    connectionstyle='arc3,rad=-0.25')
)
ax_ppo.text(5, float(f2_ppo[4]) + 0.003, 'Descenso\nsostenido →',
            fontsize=8, color=C_PPO, style='italic')

# A2C: converge en ep 3 → zoom desde ep 1
_panel_detalle(ax_a2c, f2_a2c, C_A2C, 'A2C',
               a2c_min_ep, a2c_min_val, zoom_from=1, ls=':')

ax_a2c.text(
    0.35, 0.85, 'Convergencia\nrápida ep. 1–3\n(on-policy simple)',
    transform=ax_a2c.transAxes, fontsize=8, color=C_A2C, style='italic',
    bbox=dict(boxstyle='round,pad=0.3', fc='#EDFAED', ec=C_A2C, lw=0.8, alpha=0.85)
)

path_full = OUT_DIR / 'figura_f2_co2_convergencia.png'
fig.savefig(path_full, dpi=300, bbox_inches='tight')
plt.close(fig)
print(f'✓  Figura F₂ CO₂ (completa) guardada → {path_full}')

# ─────────────────────────────────────────────────────────────────────────────
# FIGURA COMPACTA (1 panel — apta para informe Word)
# ─────────────────────────────────────────────────────────────────────────────
fig2, ax2 = plt.subplots(figsize=(12, 6))

for f2, color, label, ls, min_ep, min_val in agents_main:
    f2_sm = smooth(f2)
    ax2.plot(EPS, f2,    color=color, lw=0.85, alpha=0.28, ls=ls)
    ax2.plot(EPS, f2_sm, color=color, lw=2.4,  ls=ls, label=label)
    ax2.plot(min_ep, min_val, 'o', color=color, ms=9, zorder=6,
             markeredgecolor='white', markeredgewidth=1.8)
    offset_y = 10 if color == C_PPO else -26
    ax2.annotate(
        f'ep.{min_ep} → {min_val:.3f} M kg',
        xy=(min_ep, min_val),
        xytext=(-30, offset_y),
        textcoords='offset points',
        fontsize=9, color=color, fontweight='bold',
        arrowprops=dict(arrowstyle='->', color=color, lw=1.1),
        bbox=dict(boxstyle='round,pad=0.25', fc='white', ec=color, lw=0.8, alpha=0.9)
    )

# Baseline
ax2.axhline(bl_sac, color='#D62728', lw=1.4, ls='-.', alpha=0.7,
            label=f'Baseline (sin agente RL): {bl_sac:.2f} M kg CO₂/año')

# Zona de convergencia A2C (eps 1-3)
ax2.axvspan(1, 4, color=C_A2C, alpha=0.07)
ax2.text(1.1, float(np.max(f2_a2c[:5])) - 0.015,
         'A2C converge\nep. 1–3', fontsize=8, color=C_A2C, va='top', style='italic')

# Zona descenso PPO (eps 1-40)
ax2.axvspan(1, 40, color=C_PPO, alpha=0.04)

# Zona refinamiento SAC (eps 35-48)
ax2.axvspan(35, 49, color=C_SAC, alpha=0.05)
ax2.text(35.5, sac_min_val + 0.008,
         'Refinamiento SAC', fontsize=7.5, color=C_SAC, style='italic')

ax2.set_xlabel('Episodio  (1 ep = 8 760 pasos horarios  ·  Δt = 1 h)', fontsize=11)
ax2.set_ylabel('$F_2$ — CO₂ anual bajo control (millones kg CO₂/año)', fontsize=11)
ax2.set_title(
    'Figura — Convergencia de $F_2$ (kg CO₂/año) por episodio: SAC vs PPO vs A2C\n'
    'SAC mínimo absoluto ep. 48  ·  A2C converge ep. 3  ·  '
    'PPO descenso sostenido hasta ep. 40\n'
    'Fuente: elaboración propia en Python  ·  50 episodios  ·  Iquitos, Perú',
    fontsize=10.5, fontweight='bold'
)
ax2.set_xlim(1, 50)
ax2.xaxis.set_major_locator(mticker.MultipleLocator(5))
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:.3f}'))
ax2.grid(True, alpha=0.3, linestyle='--')
ax2.legend(fontsize=10, loc='upper right',
           title='Estrategia de control', title_fontsize=9)

# Tabla mini
info = (
    f"{'':6} {'F₂ ep50':>11}  {'F₂ mín':>11}  {'ep mín':>6}  {'CO₂ evitado':>12}\n"
    f"SAC   {sac_ep50:>9.4f} M  {sac_min_val:>9.4f} M  ep {sac_min_ep:>2}  "
    f"{(bl_sac - sac_min_val)*1e6:>10,.0f} kg\n"
    f"PPO   {ppo_ep50:>9.4f} M  {ppo_min_val:>9.4f} M  ep {ppo_min_ep:>2}  "
    f"{(bl_sac - ppo_min_val)*1e6:>10,.0f} kg\n"
    f"A2C   {a2c_ep50:>9.4f} M  {a2c_min_val:>9.4f} M  ep {a2c_min_ep:>2}  "
    f"{(bl_sac - a2c_min_val)*1e6:>10,.0f} kg"
)
ax2.text(
    0.01, 0.99, info,
    transform=ax2.transAxes,
    fontsize=8.5, family='monospace',
    verticalalignment='top',
    bbox=dict(boxstyle='round,pad=0.45', fc='white', ec='#AAAAAA', lw=0.9, alpha=0.92)
)

fig2.tight_layout()
path_compact = OUT_DIR / 'figura_f2_co2_convergencia_compact.png'
fig2.savefig(path_compact, dpi=300, bbox_inches='tight')
plt.close(fig2)
print(f'✓  Figura F₂ CO₂ (compacta) guardada → {path_compact}')

# ── Resumen en consola ─────────────────────────────────────────────────────────
print()
print('═══ Resumen datos técnicos F₂ ═══')
print(f'  SAC  mín: ep {sac_min_ep:>2}  →  {sac_min_val*1e6:>12,.0f} kg CO₂/año'
      f'  (Δ {(bl_sac - sac_min_val)*1e6:>10,.0f} kg vs BL)')
print(f'  PPO  mín: ep {ppo_min_ep:>2}  →  {ppo_min_val*1e6:>12,.0f} kg CO₂/año'
      f'  (Δ {(bl_sac - ppo_min_val)*1e6:>10,.0f} kg vs BL)')
print(f'  A2C  mín: ep {a2c_min_ep:>2}  →  {a2c_min_val*1e6:>12,.0f} kg CO₂/año'
      f'  (Δ {(bl_sac - a2c_min_val)*1e6:>10,.0f} kg vs BL)')
print(f'  Baseline: {bl_sac*1e6:>15,.0f} kg CO₂/año')
