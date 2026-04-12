"""
OE3 Dashboards — Evidencia para selección del agente IA
Objetivo: Reducción cuantificable de CO₂ en Iquitos mediante gestión
inteligente de recarga de motos y mototaxis eléctricas.
"""
from __future__ import annotations

import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

# ── Rutas ──────────────────────────────────────────────────────────────────────
import os
BASE = Path(os.environ.get('PVBESSCAR_ROOT', r'd:\diseñopvbesscar'))
JSON = BASE / 'outputs' / 'ppo_training' / 'ppo_training_summary.json'
OUT  = BASE / 'outputs' / 'ppo_training'

with open(JSON, encoding='utf-8') as f:
    data = json.load(f)

ev  = data['training_evolution']
rc  = data['reward_components_avg']
vm  = data['vehicle_charging']
out = OUT

n   = 50
eps = list(range(1, n + 1))

def s(lst: list) -> np.ndarray:
    return np.array(lst if lst else [0] * n, dtype=float)

def smooth(v: np.ndarray, w: int = 5) -> np.ndarray:
    return np.convolve(np.array(v), np.ones(w) / w, mode='same')

rewards     = s(ev['episode_rewards'])
grid_import = s(ev['episode_grid_import'])
motos       = s(vm['motos_charged_per_episode'])
mototaxis_c = s(vm['mototaxis_charged_per_episode'])
sock_util   = s(ev['episode_socket_utilization'])
ev_peak     = s(ev['episode_ev_charging_peak'])
bess_dis    = s(ev['episode_bess_discharge_kwh'])
bess_chg    = s(ev['episode_bess_charge_kwh'])
solar_kwh   = s(ev['episode_solar_kwh'])

# ── Constantes del proyecto ────────────────────────────────────────────────────
CO2_FACTOR   = 0.4521     # kg CO₂/kWh  generación termoeléctrica Iquitos
CO2_DIR_TON  = 330.03     # tCO₂/año  directo (flota EV vs gasolina)
CO2_IND_TON  = 3_749.05   # tCO₂/año  indirecto (solar vs termoeléctrico)
MOTOS_TARGET = 270 * 365  # 98,550 vehículo-eventos/año
MOTO_TARGET  = 39 * 365   # 14,235 vehículo-eventos/año

# CO₂ ADICIONAL del agente: reducción de importación vs baseline Ep.1
co2_agent_ton = (grid_import[0] - grid_import) * CO2_FACTOR / 1000
total_co2 = CO2_DIR_TON + CO2_IND_TON + co2_agent_ton[-1]


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD OE3-A: Reducción CO₂ Cuantificable — Iquitos
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 3, figsize=(19, 11))
fig.patch.set_facecolor('#F8F9FA')
fig.suptitle(
    'OE3 — Reducción Cuantificable de CO₂  |  Ciudad de Iquitos, Perú\n'
    'Infraestructura de Carga Inteligente: 38 Sockets · 4,050 kWp Solar · BESS 2,000 kWh · Agente PPO',
    fontsize=12, fontweight='bold', color='#1A252F'
)

# (0,0) Desglose CO₂ total — barras por componente
ax = axes[0, 0]
ax.set_facecolor('#FDFEFE')
cats  = ['Directo\n(Vehicular)', 'Indirecto\n(Solar→Grid)', 'Agente IA\n(Opt. PPO)']
vals  = [CO2_DIR_TON, CO2_IND_TON, co2_agent_ton[-1]]
cols  = ['#E67E22', '#9B59B6', '#27AE60']
bars  = ax.bar(cats, vals, color=cols, alpha=0.85, edgecolor='white', linewidth=1.5, width=0.5)
for bar, val in zip(bars, vals):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 25,
            f'{val:.0f} tCO₂/año', ha='center', va='bottom', fontsize=9.5, fontweight='bold')
ax.set_title('CO₂ Evitado por Componente\n(año de operación final)', fontsize=10, fontweight='bold')
ax.set_ylabel('tCO₂ por año'); ax.set_ylim(0, 4_300)
ax.text(0.5, 0.97, f'TOTAL: {total_co2:.0f} tCO₂/año evitado',
        transform=ax.transAxes, ha='center', va='top', fontsize=11,
        fontweight='bold', color='#1A7A40',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#EAFAF1', edgecolor='#27AE60'))
ax.grid(alpha=0.3, axis='y')

# (0,1) CO₂ adicional evitado por el agente — evolución 50 episodios
ax = axes[0, 1]
ax.set_facecolor('#FDFEFE')
ax.plot(eps, co2_agent_ton, color='#BDC3C7', alpha=0.5, linewidth=1)
ax.plot(eps, smooth(co2_agent_ton), color='#27AE60', linewidth=2.5,
        label='CO₂ adicional PPO (tCO₂/año)')
ax.fill_between(eps, 0, smooth(co2_agent_ton), alpha=0.15, color='#27AE60')
ax.axhline(0, color='gray', linewidth=0.8, linestyle=':')
ax.set_title('CO₂ Adicional Evitado por Agente PPO\n(vs. sin gestión IA — baseline Ep.1)', fontsize=10, fontweight='bold')
ax.set_xlabel('Episodio de Entrenamiento'); ax.set_ylabel('tCO₂/año adicional evitado')
ax.text(0.98, 0.05,
        f'Ep.50: {co2_agent_ton[-1]:.0f} tCO₂/año\n'
        f'Factor Iquitos: {CO2_FACTOR} kg/kWh',
        transform=ax.transAxes, ha='right', va='bottom', fontsize=8.5,
        bbox=dict(boxstyle='round', facecolor='#EAFAF1', alpha=0.85))
ax.legend(fontsize=8); ax.grid(alpha=0.3)

# (0,2) Grid import: termoeléctrico evitado
ax = axes[0, 2]
ax.set_facecolor('#FDFEFE')
ax.plot(eps, grid_import / 1000, color='#E74C3C', alpha=0.3, linewidth=1)
ax.plot(eps, smooth(grid_import / 1000), color='#E74C3C', linewidth=2.5,
        label='Grid import (MWh/año)')
ax.fill_between(eps, grid_import[0] / 1000, smooth(grid_import / 1000),
                where=smooth(grid_import / 1000) < grid_import[0] / 1000,
                alpha=0.2, color='#27AE60', label=f'Reducción por IA')
ax.axhline(grid_import[0] / 1000, color='#E74C3C', linewidth=1.5, linestyle='--', alpha=0.7,
           label=f'Sin gestión IA ({grid_import[0] / 1000:.0f} MWh/año)')
pct = (grid_import[0] - grid_import[-1]) / grid_import[0] * 100
saved_mwh = (grid_import[0] - grid_import[-1]) / 1000
ax.text(0.98, 0.97,
        f'Reducción: −{pct:.1f}%\n'
        f'Ahorro: {saved_mwh:.0f} MWh/año\n'
        f'≡ {saved_mwh * CO2_FACTOR:.0f} tCO₂/año',
        transform=ax.transAxes, ha='right', va='top', fontsize=8.5,
        bbox=dict(boxstyle='round', facecolor='#EAFAF1', alpha=0.9, edgecolor='#27AE60'))
ax.set_title('Importación Red Termoeléctrica Iquitos\n(↓ = menos CO₂ por generación térmica)', fontsize=10, fontweight='bold')
ax.set_xlabel('Episodio'); ax.set_ylabel('MWh/año importado')
ax.legend(fontsize=7.5); ax.grid(alpha=0.3)

# (1,0) Convergencia reward — aprendizaje del agente
ax = axes[1, 0]
ax.set_facecolor('#FDFEFE')
ax.plot(eps, rewards, color='#BDC3C7', alpha=0.5, linewidth=1)
ax.plot(eps, smooth(rewards), color='#2C3E50', linewidth=2.5, label='Reward PPO suavizado')
ax.fill_between(eps, 0, smooth(rewards), where=smooth(rewards) > 0,
                alpha=0.12, color='#27AE60')
ax.fill_between(eps, smooth(rewards), 0, where=smooth(rewards) < 0,
                alpha=0.12, color='#E74C3C')
ax.axhline(0, color='#7F8C8D', linewidth=0.8, linestyle=':')
z = np.polyfit(eps, rewards, 1)
ax.plot(eps, np.poly1d(z)(eps), '--', color='#E74C3C', linewidth=1.5, alpha=0.7,
        label=f'Tendencia (+{z[0]:.0f}/ep)')
ax.set_title('Convergencia Agente PPO\n(evidencia de aprendizaje continuo)', fontsize=10, fontweight='bold')
ax.set_xlabel('Episodio'); ax.set_ylabel('Reward acumulado anual')
ax.legend(fontsize=8)
ax.text(0.02, 0.97,
        f'Ep.1:  {rewards[0]:.0f}\nEp.50: {rewards[-1]:.0f}\n'
        f'Mejora: +{rewards[-1] - rewards[0]:.0f} (+{(rewards[-1] - rewards[0]) / abs(rewards[0]) * 100:.0f}%)',
        transform=ax.transAxes, va='top', fontsize=8.5,
        bbox=dict(boxstyle='round', facecolor='#EBF5FB', alpha=0.9, edgecolor='#2980B9'))
ax.grid(alpha=0.3)

# (1,1) Pie: proporciones CO₂
ax = axes[1, 1]
ax.set_facecolor('#FDFEFE')
sizes  = [CO2_DIR_TON, CO2_IND_TON, co2_agent_ton[-1]]
labels = [
    f'Directo vehicular\n{CO2_DIR_TON:.0f} tCO₂/año ({CO2_DIR_TON / total_co2 * 100:.1f}%)',
    f'Indirecto solar\n{CO2_IND_TON:.0f} tCO₂/año ({CO2_IND_TON / total_co2 * 100:.1f}%)',
    f'Agente IA (optimización)\n{co2_agent_ton[-1]:.0f} tCO₂/año ({co2_agent_ton[-1] / total_co2 * 100:.1f}%)',
]
wedges, _ = ax.pie(sizes, colors=['#E67E22', '#9B59B6', '#27AE60'],
                   startangle=90, wedgeprops=dict(edgecolor='white', linewidth=2))
ax.legend(wedges, labels, loc='lower center', bbox_to_anchor=(0.5, -0.22),
          fontsize=7.5, framealpha=0.9)
ax.set_title(f'Composición CO₂ Total Evitado\n{total_co2:.0f} tCO₂/año — Iquitos',
             fontsize=10, fontweight='bold')

# (1,2) Comparativa Sin IA vs Con PPO
ax = axes[1, 2]
ax.set_facecolor('#FDFEFE')
metricas   = ['Grid Import\n(MWh/año)', 'Reward\n(norm.)', 'CO₂ Agente\n(tCO₂/año)']
ep1_raw    = [grid_import[0] / 1000, max(abs(rewards[0]), 1), 0.1]
ep50_raw   = [grid_import[-1] / 1000, rewards[-1], co2_agent_ton[-1]]
max_v      = [max(ep1_raw[i], ep50_raw[i]) for i in range(3)]
ep1_norm   = [v / max_v[i] * 100 for i, v in enumerate(ep1_raw)]
ep50_norm  = [v / max_v[i] * 100 for i, v in enumerate(ep50_raw)]
x = np.arange(len(metricas))
w = 0.32
b1 = ax.bar(x - w / 2, ep1_norm,  w, color='#E74C3C', alpha=0.85, label='Sin IA (Ep.1)',  edgecolor='white', linewidth=1.2)
b2 = ax.bar(x + w / 2, ep50_norm, w, color='#27AE60', alpha=0.85, label='Con IA (Ep.50)', edgecolor='white', linewidth=1.2)
labels_ep1  = [f'{grid_import[0]/1000:.0f}', f'{rewards[0]:.0f}', '—']
labels_ep50 = [f'{grid_import[-1]/1000:.0f}', f'{rewards[-1]:.0f}', f'{co2_agent_ton[-1]:.0f}']
for bar, lbl in zip(b1, labels_ep1):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
            lbl, ha='center', va='bottom', fontsize=7.5, color='#C0392B')
for bar, lbl in zip(b2, labels_ep50):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
            lbl, ha='center', va='bottom', fontsize=7.5, color='#1A7A40', fontweight='bold')
ax.set_xticks(x); ax.set_xticklabels(metricas, fontsize=8)
ax.set_ylabel('Valor normalizado (%)'); ax.set_ylim(0, 118)
ax.set_title('Sin IA vs Agente PPO\n(métricas OE3 — final del entrenamiento)', fontsize=10, fontweight='bold')
ax.legend(fontsize=8.5); ax.grid(alpha=0.3, axis='y')

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(out / 'oe3_reduccion_co2_iquitos.png', dpi=160, bbox_inches='tight', facecolor='#F8F9FA')
plt.close()
print('✓ oe3_reduccion_co2_iquitos.png')


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD OE3-B: Gestión Inteligente Recarga Motos y Mototaxis
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 3, figsize=(19, 11))
fig.patch.set_facecolor('#F8F9FA')
fig.suptitle(
    'OE3 — Gestión Inteligente de Recarga  |  270 Motos + 39 Mototaxis Eléctricas · Iquitos\n'
    'Agente PPO: 50 episodios × 8,760 pasos (1 año de operación por episodio)',
    fontsize=12, fontweight='bold', color='#1A252F'
)

# (0,0) Motos cargadas por episodio
ax = axes[0, 0]
ax.set_facecolor('#FDFEFE')
ax.bar(eps, motos, color='#3498DB', alpha=0.6, label='Motos cargadas/año')
ax.plot(eps, smooth(motos), color='#1A5276', linewidth=2.5)
ax.axhline(MOTOS_TARGET, color='#E74C3C', linewidth=1.8, linestyle='--',
           label=f'Objetivo: {MOTOS_TARGET:,} (270/día × 365)')
ax.set_title('Motos Eléctricas Cargadas por Año\n(conteo real de eventos de carga completada)',
             fontsize=10, fontweight='bold')
ax.set_xlabel('Episodio'); ax.set_ylabel('Eventos de carga/año')
ax.legend(fontsize=8)
pct_m = (motos[-1] - motos[0]) / motos[0] * 100
ax.text(0.02, 0.97,
        f'Ep.1:  {motos[0]:,.0f}\nEp.50: {motos[-1]:,.0f}\nMejora: +{pct_m:.0f}%',
        transform=ax.transAxes, va='top', fontsize=8.5,
        bbox=dict(boxstyle='round', facecolor='#EBF5FB', alpha=0.9, edgecolor='#2980B9'))
ax.grid(alpha=0.3, axis='y')

# (0,1) Mototaxis cargados por episodio
ax = axes[0, 1]
ax.set_facecolor('#FDFEFE')
ax.bar(eps, mototaxis_c, color='#E67E22', alpha=0.6, label='Mototaxis cargados/año')
ax.plot(eps, smooth(mototaxis_c), color='#784212', linewidth=2.5)
ax.axhline(MOTO_TARGET, color='#E74C3C', linewidth=1.8, linestyle='--',
           label=f'Objetivo: {MOTO_TARGET:,} (39/día × 365)')
ax.set_title('Mototaxis Eléctricas Cargadas por Año\n(conteo real de eventos de carga completada)',
             fontsize=10, fontweight='bold')
ax.set_xlabel('Episodio'); ax.set_ylabel('Eventos de carga/año')
ax.legend(fontsize=8)
pct_t = (mototaxis_c[-1] - mototaxis_c[0]) / mototaxis_c[0] * 100
ax.text(0.02, 0.97,
        f'Ep.1:  {mototaxis_c[0]:,.0f}\nEp.50: {mototaxis_c[-1]:,.0f}\nMejora: +{pct_t:.0f}%',
        transform=ax.transAxes, va='top', fontsize=8.5,
        bbox=dict(boxstyle='round', facecolor='#FEF9E7', alpha=0.9, edgecolor='#F39C12'))
ax.grid(alpha=0.3, axis='y')

# (0,2) Sockets utilización — de 27% a 80%
ax = axes[0, 2]
ax.set_facecolor('#FDFEFE')
ax.plot(eps, sock_util * 100, color='#BDC3C7', alpha=0.5, linewidth=1)
ax.plot(eps, smooth(sock_util * 100), color='#3498DB', linewidth=2.5,
        label='Utilización sockets (%)')
ax.fill_between(eps, 0, smooth(sock_util * 100), alpha=0.12, color='#3498DB')
ax.axhline(56, color='#F39C12', linewidth=1.5, linestyle='--', label='56% = neutral')
ax.axhline(80, color='#27AE60', linewidth=1.8, linestyle='--', label='80% = objetivo OE3')
ax.set_ylim(0, 105)
ax.set_title('Utilización de 38 Sockets de Carga\n(15 motos + 4 mototaxis × 2 sockets @ 7.4 kW)',
             fontsize=10, fontweight='bold')
ax.set_xlabel('Episodio'); ax.set_ylabel('% utilización promedio anual')
ax.legend(fontsize=8)
ax.text(0.02, 0.97,
        f'Ep.1:  {sock_util[0]*100:.0f}%\nEp.50: {sock_util[-1]*100:.0f}%',
        transform=ax.transAxes, va='top', fontsize=8.5,
        bbox=dict(boxstyle='round', facecolor='#EAFAF1', alpha=0.9))
ax.grid(alpha=0.3)

# (1,0) Total vehículos: motos + mototaxis apilado
ax = axes[1, 0]
ax.set_facecolor('#FDFEFE')
ax.bar(eps, motos, color='#3498DB', alpha=0.7, label='Motos')
ax.bar(eps, mototaxis_c, bottom=motos, color='#E67E22', alpha=0.7, label='Mototaxis')
total_veh = motos + mototaxis_c
ax.plot(eps, smooth(total_veh), color='#1A252F', linewidth=2.5, label='Total suavizado')
ax.axhline(MOTOS_TARGET + MOTO_TARGET, color='#E74C3C', linewidth=1.8, linestyle='--',
           label=f'Objetivo total {MOTOS_TARGET+MOTO_TARGET:,}/año')
ax.set_title('Total Vehículos EV Gestionados por Año\n(motos + mototaxis)',
             fontsize=10, fontweight='bold')
ax.set_xlabel('Episodio'); ax.set_ylabel('Eventos de carga/año')
ax.legend(fontsize=7.5); ax.grid(alpha=0.3, axis='y')

# (1,1) BESS como buffer de carga inteligente
ax = axes[1, 1]
ax.set_facecolor('#FDFEFE')
ax.fill_between(eps, 0, bess_chg / 1000, alpha=0.5, color='#3498DB', label='BESS carga (MWh/año)')
ax.fill_between(eps, 0, bess_dis / 1000, alpha=0.5, color='#E67E22', label='BESS descarga (MWh/año)')
ax.plot(eps, smooth(bess_chg / 1000), color='#2980B9', linewidth=2)
ax.plot(eps, smooth(bess_dis / 1000), color='#D35400', linewidth=2)
ax.set_title('BESS 2,000 kWh — Acumulación y Despacho\n(buffer inteligente para desvío punta→valle)',
             fontsize=10, fontweight='bold')
ax.set_xlabel('Episodio'); ax.set_ylabel('MWh/año')
ax.legend(fontsize=8); ax.grid(alpha=0.3)

# (1,2) Solar directo a cargas EV — eficiencia de auto-consumo
ax = axes[1, 2]
ax.set_facecolor('#FDFEFE')
# Solar aprovechado ≈ solar_kwh por episodio
ax.bar(eps, solar_kwh / 1_000, color='#F1C40F', alpha=0.7, label='Solar generado (MWh/año)')
ax.plot(eps, smooth(ev_peak / 1_000), color='#E74C3C', linewidth=2.5,
        label='EV carga punta (MWh/año)')
ax.set_title('Solar PV 4,050 kWp vs Demanda EV\n(gestión inteligente maximiza auto-consumo)',
             fontsize=10, fontweight='bold')
ax.set_xlabel('Episodio'); ax.set_ylabel('MWh/año')
ax.legend(fontsize=8); ax.grid(alpha=0.3)

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(out / 'oe3_gestion_recarga_ev.png', dpi=160, bbox_inches='tight', facecolor='#F8F9FA')
plt.close()
print('✓ oe3_gestion_recarga_ev.png')


print()
print('═' * 60)
print('RESUMEN OE3 — EVIDENCIA CUANTIFICABLE')
print('═' * 60)
print(f'CO₂ directo evitado (vehicular):  {CO2_DIR_TON:,.0f} tCO₂/año')
print(f'CO₂ indirecto evitado (solar):    {CO2_IND_TON:,.0f} tCO₂/año')
print(f'CO₂ adicional agente (opt. IA):   {co2_agent_ton[-1]:,.0f} tCO₂/año')
print(f'CO₂ TOTAL evitado:                {total_co2:,.0f} tCO₂/año')
print(f'')
print(f'Motos gestionadas/año Ep.50:      {motos[-1]:,.0f}')
print(f'Mototaxis gestionadas/año Ep.50:  {mototaxis_c[-1]:,.0f}')
print(f'Utilización sockets Ep.50:        {sock_util[-1]*100:.1f}%')
print(f'Reducción grid import:            −{(grid_import[0]-grid_import[-1])/1000:.0f} MWh/año (−{(grid_import[0]-grid_import[-1])/grid_import[0]*100:.1f}%)')
print(f'Convergencia reward:              {rewards[0]:.0f} → {rewards[-1]:.0f} (+{(rewards[-1]-rewards[0])/abs(rewards[0])*100:.0f}%)')
