#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Figura B.4. Comparativa de función de recompensa multiobjetivo R(t)
SAC vs PPO vs A2C — 50 episodios de entrenamiento.

El SAC exhibe la mayor recompensa acumulada, consistente con su
estrategia off-policy (replay buffer + actualización continua).

Salida: outputs/docx/graficas/figura_b4_reward_comparativa.png  (300 dpi)
         outputs/docx/graficas/figura_b4_reward_comparativa_compact.png
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from graphics_utils import (
    C_SAC, C_PPO, C_A2C,
    load_convergence_data, smooth, get_output_dir, save_figure
)

# ── Carga de datos ─────────────────────────────────────────────────────────────
sac, ppo, a2c = load_convergence_data()
EPS = sac['episodio'].values  # 1..50
OUT_DIR = get_output_dir()

# ─────────────────────────────────────────────────────────────────────────────
# FIGURA PRINCIPAL (layout 2×2 + anotaciones técnicas)
# ─────────────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 10))
gs  = plt.GridSpec(2, 2, figure=fig, hspace=0.42, wspace=0.32)

ax_main   = fig.add_subplot(gs[0, :])   # panel superior: curvas combinadas
ax_sac    = fig.add_subplot(gs[1, 0])   # panel inferior izq: detalle SAC
ax_others = fig.add_subplot(gs[1, 1])   # panel inferior der: PPO vs A2C

fig.suptitle(
    'Figura B.4 — Comparativa de función de recompensa multiobjetivo $R(t)$\n'
    'SAC vs PPO vs A2C  ·  50 episodios  ·  438 000 pasos  ·  Iquitos pvbesscar',
    fontsize=13, fontweight='bold', y=1.01
)

# ────────────────────────────────────────────────────────
# Panel 1: Comparativa global
# ────────────────────────────────────────────────────────
agents = [
    (sac, C_SAC, 'SAC (off-policy)',  '-'),
    (ppo, C_PPO, 'PPO (on-policy)',   '--'),
    (a2c, C_A2C, 'A2C (on-policy)',   ':'),
]

for df, color, label, ls in agents:
    r    = df['reward'].values
    rm   = df['rolling_mean'].values
    r_sm = smooth(r)

    # Banda ±1σ con rolling_std
    std  = df['rolling_std'].values
    ax_main.fill_between(EPS, rm - std, rm + std,
                         color=color, alpha=0.12)
    ax_main.plot(EPS, r,    color=color, lw=0.9, alpha=0.35, ls=ls)
    ax_main.plot(EPS, r_sm, color=color, lw=2.5, ls=ls, label=label)

    # Anotación ep 50
    ep50  = r[-1]
    ax_main.annotate(
        f'Ep.50: {ep50:.1f}',
        xy=(50, ep50),
        xytext=(-55, -16 if color == C_A2C else 10),
        textcoords='offset points',
        fontsize=9.5, color=color, fontweight='bold',
        arrowprops=dict(arrowstyle='->', color=color, lw=1.2)
    )

# Referencia episodio 1 (línea base sin aprendizaje)
ax_main.axvline(x=1,  color='grey', lw=0.8, ls=':', alpha=0.6)
ax_main.axvline(x=10, color='grey', lw=0.8, ls=':', alpha=0.5,
                label='Ep. 10 (exploración→explotación)')

ax_main.set_xlabel('Episodio  (1 ep = 8 760 pasos horarios)', fontsize=11)
ax_main.set_ylabel('$R(t)$ — Recompensa acumulada por episodio', fontsize=11)
ax_main.set_title('Curvas de convergencia — Recompensa total por episodio', fontsize=12)
ax_main.set_xlim(1, 50)
ax_main.xaxis.set_major_locator(mticker.MultipleLocator(5))
ax_main.grid(True, alpha=0.3, linestyle='--')
ax_main.legend(fontsize=10, loc='lower right')

# Anotación narrativa off-policy
ax_main.annotate(
    'SAC (off-policy) converge más\n'
    'rápido y a mayor $R(t)$ gracias\n'
    'al replay buffer y actualización\n'
    'continua de la política.',
    xy=(12, sac['reward'].values[11]),
    xytext=(14, -800),
    textcoords='data',
    fontsize=9, color=C_SAC,
    bbox=dict(boxstyle='round,pad=0.4', fc='#EBF3FD', ec=C_SAC, lw=1.2),
    arrowprops=dict(arrowstyle='->', color=C_SAC, lw=1.1)
)

# ────────────────────────────────────────────────────────
# Panel 2: Detalle SAC (convergencia últimos 30 eps)
# ────────────────────────────────────────────────────────
idx30 = EPS >= 20
r_sac = sac['reward'].values
rm_sac = sac['rolling_mean'].values
std_sac = sac['rolling_std'].values

ax_sac.fill_between(EPS[idx30],
                    rm_sac[idx30] - std_sac[idx30],
                    rm_sac[idx30] + std_sac[idx30],
                    color=C_SAC, alpha=0.18, label='Media ± σ rolling')
ax_sac.plot(EPS[idx30], r_sac[idx30],
            color=C_SAC, lw=1.2, alpha=0.5, label='$R(t)$ raw')
ax_sac.plot(EPS[idx30], smooth(r_sac)[idx30],
            color=C_SAC, lw=2.5, label='Suavizado (w=5)')

# Línea de convergencia (media últimos 10 eps)
mu_conv  = float(np.mean(r_sac[-10:]))
std_conv = float(np.std(r_sac[-10:]))
ax_sac.axhline(mu_conv, color=C_SAC, lw=1.5, ls='--', alpha=0.8)
ax_sac.text(22.5, mu_conv + 1.5,
            f'μ₄₁₋₅₀ = {mu_conv:.1f} ± {std_conv:.1f}',
            fontsize=9, color=C_SAC)

ax_sac.set_xlabel('Episodio', fontsize=10)
ax_sac.set_ylabel('$R(t)$', fontsize=10)
ax_sac.set_title('SAC — Detalle convergencia (ep. 20–50)', fontsize=11, color=C_SAC)
ax_sac.set_xlim(20, 50)
ax_sac.xaxis.set_major_locator(mticker.MultipleLocator(5))
ax_sac.grid(True, alpha=0.3, linestyle='--')
ax_sac.legend(fontsize=8)

# ────────────────────────────────────────────────────────
# Panel 3: PPO vs A2C detalle
# ────────────────────────────────────────────────────────
r_ppo  = ppo['reward'].values
rm_ppo = ppo['rolling_mean'].values
std_ppo = ppo['rolling_std'].values

r_a2c  = a2c['reward'].values
rm_a2c = a2c['rolling_mean'].values
std_a2c = a2c['rolling_std'].values

for r, rm, std, color, label in [
    (r_ppo, rm_ppo, std_ppo, C_PPO, 'PPO'),
    (r_a2c, rm_a2c, std_a2c, C_A2C, 'A2C'),
]:
    ax_others.fill_between(EPS[idx30],
                           rm[idx30] - std[idx30],
                           rm[idx30] + std[idx30],
                           color=color, alpha=0.15)
    ax_others.plot(EPS[idx30], r[idx30],
                   color=color, lw=1.0, alpha=0.5)
    ax_others.plot(EPS[idx30], smooth(r)[idx30],
                   color=color, lw=2.5, label=f'{label} suavizado')

    mu_c = float(np.mean(r[-10:]))
    ax_others.axhline(mu_c, color=color, lw=1.3, ls='--', alpha=0.7)
    ax_others.text(22.5, mu_c + 2,
                   f'μ₄₁₋₅₀ = {mu_c:.1f}',
                   fontsize=8.5, color=color)

ax_others.set_xlabel('Episodio', fontsize=10)
ax_others.set_ylabel('$R(t)$', fontsize=10)
ax_others.set_title('PPO vs A2C — Detalle (ep. 20–50)', fontsize=11)
ax_others.set_xlim(20, 50)
ax_others.xaxis.set_major_locator(mticker.MultipleLocator(5))
ax_others.grid(True, alpha=0.3, linestyle='--')
ax_others.legend(fontsize=9)

# ────────────────────────────────────────────────────────
# Tabla de métricas finales (textbox)
# ────────────────────────────────────────────────────────
sac_ep50  = float(sac['reward'].iloc[-1])
ppo_ep50  = float(ppo['reward'].iloc[-1])
a2c_ep50  = float(a2c['reward'].iloc[-1])

sac_mu  = float(np.mean(sac['reward'].values[-10:]))
ppo_mu  = float(np.mean(ppo['reward'].values[-10:]))
a2c_mu  = float(np.mean(a2c['reward'].values[-10:]))

sac_cv  = float(sac['rolling_cv_pct'].iloc[-1])
ppo_cv  = float(ppo['rolling_cv_pct'].iloc[-1])
a2c_cv  = float(a2c['rolling_cv_pct'].iloc[-1])

tabla = (
    f"{'Agente':<8} {'R(ep50)':>9} {'μ(ult10)':>10} {'CV%':>6}\n"
    f"{'─'*38}\n"
    f"{'SAC':<8} {sac_ep50:>9.1f} {sac_mu:>10.1f} {sac_cv:>5.2f}%\n"
    f"{'PPO':<8} {ppo_ep50:>9.1f} {ppo_mu:>10.1f} {ppo_cv:>5.2f}%\n"
    f"{'A2C':<8} {a2c_ep50:>9.1f} {a2c_mu:>10.1f} {a2c_cv:>5.2f}%\n"
    f"{'─'*38}\n"
    f"Pesos reward: CO₂dir=0.35 | CO₂ind=0.30\n"
    f"              EV=0.35 | Solar=0.04 | Grid=0.02\n"
    f"Factor CO₂: 0.4521 kg/kWh (Iquitos)"
)

ax_main.text(
    0.01, 0.03, tabla,
    transform=ax_main.transAxes,
    fontsize=8.5, family='monospace',
    verticalalignment='bottom',
    bbox=dict(boxstyle='round,pad=0.5', fc='#FAFAFA', ec='#CCCCCC', lw=1.0, alpha=0.92)
)

# ── Guardar ───────────────────────────────────────────────────────────────────
path_out = OUT_DIR / 'figura_b4_reward_comparativa.png'
fig.savefig(path_out, dpi=300, bbox_inches='tight')
plt.close(fig)
print(f'✓  Figura B.4 guardada → {path_out}')

# ─────────────────────────────────────────────────────────────────────────────
# FIGURA COMPACTA (1 panel, para insertar en informe Word)
# ─────────────────────────────────────────────────────────────────────────────
fig2, ax2 = plt.subplots(figsize=(11, 5.5))

for df, color, label, ls in agents:
    r    = df['reward'].values
    r_sm = smooth(r)
    std  = df['rolling_std'].values
    rm   = df['rolling_mean'].values

    ax2.fill_between(EPS, rm - std, rm + std, color=color, alpha=0.10)
    ax2.plot(EPS, r,    color=color, lw=0.8, alpha=0.30, ls=ls)
    ax2.plot(EPS, r_sm, color=color, lw=2.2, ls=ls, label=label)

    ep50 = r[-1]
    offset_y = 10 if color != C_A2C else -20
    ax2.annotate(
        f'{ep50:.1f}',
        xy=(50, ep50),
        xytext=(-30, offset_y),
        textcoords='offset points',
        fontsize=9, color=color, fontweight='bold',
        arrowprops=dict(arrowstyle='->', color=color, lw=1.0)
    )

ax2.set_xlabel('Episodio  (1 ep = 8 760 pasos horarios  ·  Δt = 1 h)', fontsize=11)
ax2.set_ylabel('$R(t)$ — Recompensa acumulada (multiobjetivo)', fontsize=11)
ax2.set_title(
    'Figura B.4 — Función de recompensa multiobjetivo $R(t)$: SAC vs PPO vs A2C\n'
    r'Pesos: $w_{\mathrm{CO_2^{dir}}}$=0.35, $w_{\mathrm{CO_2^{ind}}}$=0.30, '
    r'$w_{\mathrm{EV}}$=0.25, $w_{\mathrm{solar}}$=0.05, $w_{\mathrm{grid}}$=0.05',
    fontsize=11, fontweight='bold'
)
ax2.set_xlim(1, 50)
ax2.xaxis.set_major_locator(mticker.MultipleLocator(5))
ax2.grid(True, alpha=0.3, linestyle='--')
ax2.legend(fontsize=10.5, loc='lower right',
           title='Estrategia de aprendizaje', title_fontsize=9)

# Marcador ventana explotación
ax2.axvspan(1, 3, color='grey', alpha=0.08)
ax2.text(1.4, sac['reward'].values[0] * 0.93, 'Exploración\ninicial',
         fontsize=8, color='grey', ha='left')

# Etiquetas finales con tabla miniatura
info = (
    f'Ep.50   μ(ult10ep)\n'
    f'SAC  {sac_ep50:>7.1f}   {sac_mu:>7.1f}   CV={sac_cv:.2f}%\n'
    f'PPO  {ppo_ep50:>7.1f}   {ppo_mu:>7.1f}   CV={ppo_cv:.2f}%\n'
    f'A2C  {a2c_ep50:>7.1f}   {a2c_mu:>7.1f}   CV={a2c_cv:.2f}%'
)
ax2.text(
    0.02, 0.04, info,
    transform=ax2.transAxes,
    fontsize=8.5, family='monospace',
    verticalalignment='bottom',
    bbox=dict(boxstyle='round,pad=0.45', fc='white', ec='#AAAAAA', lw=0.9, alpha=0.9)
)

fig2.tight_layout()
path_compact = OUT_DIR / 'figura_b4_reward_comparativa_compact.png'
fig2.savefig(path_compact, dpi=300, bbox_inches='tight')
plt.close(fig2)
print(f'✓  Figura B.4 (compacta) guardada → {path_compact}')
