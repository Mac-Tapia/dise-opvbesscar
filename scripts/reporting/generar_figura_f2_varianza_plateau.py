#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comparación de varianza entre agentes — distribución de F₂ en el plateau (ep 36–50).
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
from scipy.stats import gaussian_kde
from graphics_utils import (
    C_SAC, C_PPO, C_A2C,
    load_training_data, get_output_dir, save_figure
)

# ── Carga — plateau ep 36–50 ──────────────────────────────────────────────────
sac_df, ppo_df, a2c_df = load_training_data()
OUT_DIR = get_output_dir()

# σ calculado sobre 50 episodios completos
sac_pl = sac_df['co2_control_kg'].values
ppo_pl = ppo_df['co2_control_kg'].values
a2c_pl = a2c_df['co2_control_kg'].values

# Subconjunto plateau (ep 36-50)
sac_plateau = sac_df.loc[sac_df['episodio'] >= 36, 'co2_control_kg'].values
ppo_plateau = ppo_df.loc[ppo_df['episodio'] >= 36, 'co2_control_kg'].values
a2c_plateau = a2c_df.loc[a2c_df['episodio'] >= 36, 'co2_control_kg'].values

# Estadísticos verificados
for lbl, arr in [('SAC', sac_pl), ('PPO', ppo_pl), ('A2C', a2c_pl)]:
    print(f'{lbl}  σ={np.std(arr, ddof=1):>10,.0f} kg  '
          f'μ={np.mean(arr):>13,.0f} kg  min={np.min(arr):>13,.0f}  max={np.max(arr):>13,.0f}')

agents = [
    dict(label='SAC\n(off-policy)', arr=sac_pl, color=C_SAC,
         sigma=89_475,  interp='Exploración activa\n(replay buffer off-policy)'),
    dict(label='PPO\n(on-policy)',  arr=ppo_pl, color=C_PPO,
         sigma=113_816, interp='Mayor inestabilidad\n(on-policy, updates ruidosos)'),
    dict(label='A2C\n(on-policy)', arr=a2c_pl, color=C_A2C,
         sigma=12_011,  interp='⚠ Baja varianza =\nEstancamiento, no calidad'),
]
# Nota: σ se calcula sobre 50 episodios completos (incluye fase de descenso)

# ─────────────────────────────────────────────────────────────────────────────
# FIGURA COMPLETA  (violin + boxplot + scatter + σ subplot)
# ─────────────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 10))
gs  = plt.GridSpec(2, 3, figure=fig, hspace=0.50, wspace=0.35)

ax_vio  = fig.add_subplot(gs[0, :2])   # violines comparativos
ax_sig  = fig.add_subplot(gs[0, 2])    # barras de sigma
ax_sac  = fig.add_subplot(gs[1, 0])    # serie temporal SAC plateau
ax_ppo  = fig.add_subplot(gs[1, 1])    # serie temporal PPO plateau
ax_a2c  = fig.add_subplot(gs[1, 2])    # serie temporal A2C plateau

fig.suptitle(
    'Comparación de varianza entre agentes — distribución de $F_2$ (50 episodios, plateau indicado ep. 36–50)\n'
    'SAC: σ=89,475 kg  ·  PPO: σ=113,816 kg  ·  '
    'A2C: σ=12,011 kg (baja varianza = estancamiento, no calidad)\n'
    'Fuente: elaboración propia en Python  ·  Iquitos, Perú  ·  σ calculado sobre 50 episodios completos',
    fontsize=11, fontweight='bold', y=1.02
)

# ── Panel violines ─────────────────────────────────────────────────────────────
positions = [1, 2, 3]
arrays    = [a['arr'] for a in agents]
colors_v  = [a['color'] for a in agents]

# Violines con los 50 episodios completos
vp = ax_vio.violinplot(arrays, positions=positions,
                        showmeans=True, showmedians=True, showextrema=True,
                        widths=0.55)

# Colorear cada violín
for body, color in zip(vp['bodies'], colors_v):
    body.set_facecolor(color)
    body.set_alpha(0.38)
    body.set_edgecolor(color)
    body.set_linewidth(1.5)

for partname in ('cmeans', 'cmedians', 'cbars', 'cmins', 'cmaxes'):
    vp[partname].set_color('#333333')
    vp[partname].set_linewidth(1.2)

# Scatter (jitter) de puntos individuales
rng = np.random.default_rng(42)
ep_labels = np.arange(36, 51)  # 15 puntos
for pos, ag in zip(positions, agents):
    jitter = rng.uniform(-0.10, 0.10, size=len(ag['arr']))
    sc = ax_vio.scatter(pos + jitter, ag['arr'], color=ag['color'],
                        s=38, zorder=5, alpha=0.80, edgecolors='white', linewidths=0.6)

# Etiquetas σ sobre cada violín
for pos, ag in zip(positions, agents):
    mu  = float(np.mean(ag['arr']))
    sig = float(np.std(ag['arr'], ddof=1))
    ax_vio.text(pos, np.max(ag['arr']) + 20_000,
                f'σ={sig:,.0f} kg\nμ={mu/1e6:.4f} M kg',
                ha='center', va='bottom', fontsize=9.5, fontweight='bold',
                color=ag['color'],
                bbox=dict(boxstyle='round,pad=0.3', fc='white',
                           ec=ag['color'], lw=0.9, alpha=0.90))

ax_vio.set_xticks(positions)
ax_vio.set_xticklabels([a['label'] for a in agents], fontsize=12)
ax_vio.set_ylabel('$F_2$ — CO₂ bajo control (kg CO₂/año)', fontsize=11)
ax_vio.set_title('Distribución de $F_2$ — 50 episodios completos · Violín + puntos individuales\n'
                 '(banda gris: plateau ep. 36–50  ·  σ calculado sobre los 50 ep.)',
                 fontsize=11)
ax_vio.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v/1e6:.4f} M'))
ax_vio.grid(True, axis='y', alpha=0.30, linestyle='--')
ax_vio.spines[['top', 'right']].set_visible(False)

# Banda horizontal indicando el rango del plateau ep.36-50
for pos, pl_arr, ag in zip(positions,
                           [sac_plateau, ppo_plateau, a2c_plateau], agents):
    ax_vio.fill_between([pos - 0.30, pos + 0.30],
                        float(np.min(pl_arr)), float(np.max(pl_arr)),
                        color=ag['color'], alpha=0.18, zorder=1)

# Nota interpretativa A2C
ax_vio.text(3.35, float(np.mean(a2c_pl)),
            '⚠ Estancamiento\n(no calidad)',
            fontsize=9, color=C_A2C, style='italic', va='center',
            bbox=dict(boxstyle='round,pad=0.3', fc='#EDFAED', ec=C_A2C, lw=0.9))

# ── Panel barras σ ────────────────────────────────────────────────────────────
sigmas   = [float(np.std(a['arr'], ddof=1)) for a in agents]
sig_lbls = [a['label'].replace('\n', ' ') for a in agents]

bars_s = ax_sig.bar(sig_lbls, sigmas, color=colors_v, width=0.50,
                     edgecolor='white', linewidth=1.5, zorder=3)

for bar, sig, ag in zip(bars_s, sigmas, agents):
    ax_sig.text(bar.get_x() + bar.get_width() / 2,
                sig + 1_500,
                f'{sig:,.0f} kg',
                ha='center', va='bottom', fontsize=10.5, fontweight='bold',
                color=ag['color'])

# Anotación A2C baja σ
ax_sig.annotate(
    '⚠ Baja σ =\nestancamiento',
    xy=(2, sigmas[2]),
    xytext=(1.3, sigmas[2] + 35_000),
    fontsize=9, color=C_A2C, style='italic',
    arrowprops=dict(arrowstyle='->', color=C_A2C, lw=1.2),
    bbox=dict(boxstyle='round,pad=0.3', fc='#EDFAED', ec=C_A2C, lw=0.9)
)

ax_sig.set_ylabel('Desviación estándar σ (kg CO₂/año)', fontsize=10)
ax_sig.set_title('σ por agente\nen plateau ep. 36–50', fontsize=11)
ax_sig.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v/1e3:.0f}k'))
ax_sig.set_ylim(0, max(sigmas) * 1.45)
ax_sig.grid(True, axis='y', alpha=0.30, linestyle='--', zorder=0)
ax_sig.spines[['top', 'right']].set_visible(False)

# ── Paneles series temporales plateau ─────────────────────────────────────────
eps_pl = np.arange(36, 36 + len(sac_pl))

def _panel_serie(ax, eps, arr, color, label, sigma_ref):
    mu   = float(np.mean(arr))
    sig  = float(np.std(arr, ddof=1))
    ax.fill_between(eps, mu - sig, mu + sig, color=color, alpha=0.15,
                    label=f'μ ± σ')
    ax.fill_between(eps, mu - 2*sig, mu + 2*sig, color=color, alpha=0.07,
                    label='μ ± 2σ')
    ax.plot(eps, arr, color=color, lw=2.2, marker='o', ms=5,
            markeredgecolor='white', markeredgewidth=1.0, zorder=4)
    ax.axhline(mu, color=color, lw=1.4, ls='--', alpha=0.70, label=f'μ = {mu/1e6:.4f} M kg')
    ax.set_xlabel('Episodio', fontsize=10)
    ax.set_ylabel('$F_2$ (M kg CO₂/año)', fontsize=10)
    ax.set_title(f'{label}\nσ = {sig:,.0f} kg',
                 fontsize=11, color=color, fontweight='bold')
    ax.set_xlim(eps[0], eps[-1])
    ax.xaxis.set_major_locator(mticker.MultipleLocator(3))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v/1e6:.4f}'))
    ax.grid(True, alpha=0.30, linestyle='--')
    ax.legend(fontsize=8, loc='upper right')
    ax.spines[['top', 'right']].set_visible(False)

eps_all = np.arange(1, 51)
_panel_serie(ax_sac, eps_all, sac_pl, C_SAC, 'SAC (off-policy)', 89_475)
_panel_serie(ax_ppo, eps_all, ppo_pl, C_PPO, 'PPO (on-policy)',  113_816)
_panel_serie(ax_a2c, eps_all, a2c_pl, C_A2C, 'A2C (on-policy)',  12_011)

# Sombrear plateau en cada panel
for ax_p in [ax_sac, ax_ppo, ax_a2c]:
    ax_p.axvspan(36, 50, color='grey', alpha=0.10, label='Plateau ep.36–50')
    ax_p.set_xlim(1, 50)
    ax_p.legend(fontsize=8, loc='upper right')

# Nota en A2C sobre estancamiento
ax_a2c.text(0.05, 0.15,
            'Oscilación mínima:\npolítica convergida\npero subóptima',
            transform=ax_a2c.transAxes, fontsize=8.5, color=C_A2C, style='italic',
            bbox=dict(boxstyle='round,pad=0.3', fc='#EDFAED', ec=C_A2C, lw=0.9))

path_full = OUT_DIR / 'figura_f2_varianza_plateau.png'
fig.savefig(path_full, dpi=300, bbox_inches='tight')
plt.close(fig)
print(f'✓  Figura varianza plateau (completa) → {path_full}')

# ─────────────────────────────────────────────────────────────────────────────
# FIGURA COMPACTA  (violin + σ cuadro + interpretación)
# ─────────────────────────────────────────────────────────────────────────────
fig2, ax2 = plt.subplots(figsize=(12, 6.5))

# Violines: 50 episodios completos (incluye descenso)
vp2 = ax2.violinplot(arrays, positions=positions,
                      showmeans=True, showmedians=True, showextrema=True,
                      widths=0.60)

for body, color in zip(vp2['bodies'], colors_v):
    body.set_facecolor(color)
    body.set_alpha(0.35)
    body.set_edgecolor(color)
    body.set_linewidth(1.6)

for partname in ('cmeans', 'cmedians', 'cbars', 'cmins', 'cmaxes'):
    vp2[partname].set_color('#333333')
    vp2[partname].set_linewidth(1.2)

for pos, ag in zip(positions, agents):
    jitter = rng.uniform(-0.12, 0.12, size=len(ag['arr']))
    ax2.scatter(pos + jitter, ag['arr'], color=ag['color'],
                s=42, zorder=5, alpha=0.85, edgecolors='white', linewidths=0.7)

# Σ y μ encima de cada violín
for pos, ag in zip(positions, agents):
    sig = float(np.std(ag['arr'], ddof=1))
    mu  = float(np.mean(ag['arr']))
    ax2.text(pos, np.max(ag['arr']) + 18_000,
             f'σ = {sig:,.0f} kg\nμ = {mu/1e6:.4f} M kg',
             ha='center', va='bottom', fontsize=10, fontweight='bold', color=ag['color'],
             bbox=dict(boxstyle='round,pad=0.32', fc='white', ec=ag['color'], lw=1.0, alpha=0.92))

# Líneas horizontales de media
for pos, ag in zip(positions, agents):
    mu = float(np.mean(ag['arr']))
    ax2.hlines(mu, pos - 0.32, pos + 0.32, colors=ag['color'], lw=2.0, ls='--', alpha=0.65)

# Banda plateau en compacta
for pos, pl_arr, ag in zip(positions,
                           [sac_plateau, ppo_plateau, a2c_plateau], agents):
    ax2.fill_between([pos - 0.32, pos + 0.32],
                     float(np.min(pl_arr)), float(np.max(pl_arr)),
                     color=ag['color'], alpha=0.22, zorder=1,
                     label='Plateau ep.36–50' if pos == 1 else None)

ax2.set_xticks(positions)
ax2.set_xticklabels([a['label'] for a in agents], fontsize=12)
ax2.set_ylabel('$F_2$ — CO₂ bajo control (kg CO₂/año)', fontsize=11)
ax2.set_title(
    'Comparación de varianza de $F_2$ — 50 episodios completos (plateau ep. 36–50 sombreado)\n'
    'SAC: σ=89,475 kg  ·  PPO: σ=113,816 kg  ·  A2C: σ=12,011 kg  ·  '
    'Fuente: elaboración propia en Python  ·  Iquitos, Perú',
    fontsize=11, fontweight='bold'
)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v/1e6:.4f} M'))
ax2.grid(True, axis='y', alpha=0.28, linestyle='--')
ax2.spines[['top', 'right']].set_visible(False)

# Cuadro interpretación en esquina superior derecha
interp_txt = (
    "Interpretación (plateau ep. 36–50)\n"
    "─────────────────────────────────────────────\n"
    "SAC  σ=  89,475 kg → Exploración activa\n"
    "                      (replay buffer off-policy)\n"
    "PPO  σ= 113,816 kg → Mayor inestabilidad\n"
    "                      (on-policy, updates ruidosos)\n"
    "A2C  σ=  12,011 kg → ⚠ ESTANCAMIENTO:\n"
    "                      política convergida pero\n"
    "                      subóptima. Baja σ ≠ calidad.\n"
    "─────────────────────────────────────────────\n"
    "F₂ absoluto: SAC < PPO < A2C  (SAC = mejor)"
)
ax2.text(
    0.67, 0.98, interp_txt,
    transform=ax2.transAxes, fontsize=8.8, family='monospace',
    verticalalignment='top',
    bbox=dict(boxstyle='round,pad=0.5', fc='#FAFAFA', ec='#AAAAAA', lw=1.0, alpha=0.95)
)

# Flecha anotación estancamiento A2C
ax2.annotate(
    '⚠ Baja σ = estancamiento\n   (no estabilidad de calidad)',
    xy=(3, float(np.mean(a2c_pl))),
    xytext=(2.35, float(np.mean(a2c_pl)) - 130_000),
    fontsize=9.5, color=C_A2C, fontweight='bold',
    arrowprops=dict(arrowstyle='->', color=C_A2C, lw=1.5),
    bbox=dict(boxstyle='round,pad=0.35', fc='#EDFAED', ec=C_A2C, lw=1.2, alpha=0.93)
)

fig2.tight_layout()
path_compact = OUT_DIR / 'figura_f2_varianza_plateau_compact.png'
fig2.savefig(path_compact, dpi=300, bbox_inches='tight')
plt.close(fig2)
print(f'✓  Figura varianza plateau (compacta)  → {path_compact}')

# ── Resumen consola ────────────────────────────────────────────────────────────
print()
print('═══ Estadísticos 50 episodios completos ═══')
for ag, arr in [('SAC', sac_pl), ('PPO', ppo_pl), ('A2C', a2c_pl)]:
    sig = np.std(arr, ddof=1)
    mu  = np.mean(arr)
    rng_v = np.max(arr) - np.min(arr)
    print(f'  {ag}  μ={mu:>13,.0f} kg  σ={sig:>10,.0f} kg  '
          f'rango={rng_v:>10,.0f} kg  cv={sig/mu*100:.2f}%')
