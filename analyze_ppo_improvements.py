#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis de Mejora Continua - PPO v7.4
Evalúa métricas de entrenamiento y genera recomendaciones
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json

print("\n" + "="*90)
print("ANÁLISIS DE MEJORA CONTINUA - PPO v7.4".center(90))
print("="*90 + "\n")

# Cargar datos
ts_df = pd.read_csv('outputs/ppo_training/timeseries_ppo.csv')
trace_df = pd.read_csv('outputs/ppo_training/trace_ppo.csv')

with open('outputs/ppo_training/result_ppo.json', 'r') as f:
    result = json.load(f)

# ============================================================================
# 1. METRICAS DE ENTRENAMIENTO
# ============================================================================
print("📊 [1] METRICAS DE ENTRENAMIENTO".ljust(90, "-"))

training_evo = result.get('training_evolution', {})
if training_evo:
    avg_reward = np.mean(training_evo.get('episode_rewards', []))
    avg_co2_avoided = np.mean(training_evo.get('episode_co2_avoided_total', []))
    avg_solar = np.mean(training_evo.get('episode_solar_kwh', []))
    avg_grid = np.mean(training_evo.get('episode_grid_import', []))
    
    print(f"  • Reward promedio (10 episodios): {avg_reward:.2f}")
    print(f"  • CO2 evitado promedio: {avg_co2_avoided:,.0f} kg")
    print(f"  • Solar aprovechado promedio: {avg_solar:,.0f} kWh")
    print(f"  • Grid import promedio: {avg_grid:,.0f} kWh")

# ============================================================================
# 2. ANALISIS DE ENTROPY (Exploración)
# ============================================================================
print("\n🔍 [2] ANÁLISIS DE ENTROPÍA (Exploración)".ljust(90, "-"))

entropy_data_raw = ts_df.groupby('episode')['entropy'].agg(['mean', 'std', 'min', 'max'])
entropy_data = entropy_data_raw[entropy_data_raw['mean'] > 0]  # Filtrar ceros
print(f"\n  Entropía por episodio (solo donde hay datos):")
for episode, row in entropy_data.iterrows():
    if row['mean'] > 0:
        print(f"    Ep {int(episode):2d}: mean={row['mean']:7.3f}, std={row['std']:6.3f}, min={row['min']:7.3f}, max={row['max']:7.3f}")

entropy_nonzero = ts_df[ts_df['entropy'] > 0]['entropy']
overall_entropy_mean = entropy_nonzero.mean()
overall_entropy_std = entropy_nonzero.std()
print(f"\n  • Promedio (datos no-cero): {overall_entropy_mean:.3f} ± {overall_entropy_std:.3f}")
print(f"  • Rango: {entropy_nonzero.min():.3f} a {entropy_nonzero.max():.3f}")

# ============================================================================
# 3. METRICAS DE KL DIVERGENCE (Estabilidad de Política)
# ============================================================================
print("\n⚖️  [3] KL DIVERGENCE (Estabilidad política)".ljust(90, "-"))

kl_data = ts_df.groupby('episode')['approx_kl'].agg(['mean', 'std', 'max'])
print(f"\n  KL divergence por episodio:")
for episode, row in kl_data.iterrows():
    if row['mean'] > 0:
        print(f"    Ep {int(episode):2d}: mean={row['mean']:.6f}, std={row['std']:.6f}, max={row['max']:.6f}")

kl_high = (ts_df['approx_kl'] > 0.02).sum()
kl_pct = (kl_high / len(ts_df)) * 100
print(f"\n  • KL > 0.02 (threshold de estabilidad): {kl_high} veces ({kl_pct:.2f}%)")
print(f"  • Si > 5%: Política inestable, considerar LR menor")

# ============================================================================
# 4. CLIP FRACTION (Agresividad de Updates)
# ============================================================================
print("\n✂️  [4] CLIP FRACTION (Agresividad de updates)".ljust(90, "-"))

clip_data = ts_df.groupby('episode')['clip_fraction'].agg(['mean', 'std'])
print(f"\n  Clip fraction por episodio:")
for episode, row in clip_data.iterrows():
    if row['mean'] > 0:
        print(f"    Ep {int(episode):2d}: mean={row['mean']:.4f}, std={row['std']:.4f}")

clip_high = (ts_df['clip_fraction'] > 0.3).sum()
clip_pct = (clip_high / len(ts_df)) * 100
print(f"\n  • Clip > 0.3 (muy agresivo): {clip_high} veces ({clip_pct:.2f}%)")
if clip_pct < 5:
    print(f"  ✓ Clip fraction saludable (< 5%)")
else:
    print(f"  ⚠️ Considerar reducir clip_range o aumentar batch_size")

# ============================================================================
# 5. EXPLAINED VARIANCE (Calidad del Value Function)
# ============================================================================
print("\n🧠 [5] EXPLAINED VARIANCE (Value Function)".ljust(90, "-"))

ev_data = ts_df.groupby('episode')['explained_variance'].agg(['mean', 'std'])
print(f"\n  Explained variance por episodio:")
for episode, row in ev_data.iterrows():
    if row['mean'] != 0:
        print(f"    Ep {int(episode):2d}: mean={row['mean']:.4f}, std={row['std']:.4f}")

ev_neg = (ts_df['explained_variance'] < 0).sum()
ev_neg_pct = (ev_neg / len(ts_df)) * 100
print(f"\n  • EV < 0 (crítico): {ev_neg} veces ({ev_neg_pct:.2f}%)")
if ev_neg_pct < 5:
    print(f"  ✓ Value function estable (< 5% crítico)")
else:
    print(f"  ⚠️ Value function inestable, revisar arquitectura")

# ============================================================================
# 6. POLICY Y VALUE LOSS
# ============================================================================
print("\n💥 [6] POLICY & VALUE LOSS (Convergencia)".ljust(90, "-"))

policy_loss = ts_df.groupby('episode')['policy_loss'].agg(['mean', 'std'])
value_loss = ts_df.groupby('episode')['value_loss'].agg(['mean', 'std'])

print(f"\n  Policy Loss por episodio:")
for episode, row in policy_loss.iterrows():
    if row['mean'] > 0:
        print(f"    Ep {int(episode):2d}: mean={row['mean']:10.6f}, std={row['std']:10.6f}")

print(f"\n  Value Loss por episodio:")
for episode, row in value_loss.iterrows():
    if row['mean'] > 0:
        print(f"    Ep {int(episode):2d}: mean={row['mean']:10.6f}, std={row['std']:10.6f}")

# ============================================================================
# 7. CO2 BREAKDOWN (Eficiencia de Control)
# ============================================================================
print("\n🌿 [7] CO2 BREAKDOWN (Eficiencia control)".ljust(90, "-"))

co2_grid = ts_df['co2_grid_kg'].sum()
co2_indirect = ts_df['co2_avoided_indirect_kg'].sum()
co2_direct = ts_df['co2_avoided_direct_kg'].sum()

print(f"\n  CO2 Grid Import: {co2_grid:,.0f} kg")
print(f"  CO2 Avoided Indirecto: {co2_indirect:,.0f} kg (Solar/BESS evita grid)")
print(f"  CO2 Avoided Directo: {co2_direct:,.0f} kg (EV combustible)")
print(f"  Total CO2 Reducido: {co2_indirect + co2_direct:,.0f} kg")

reduccion_pct = (co2_indirect + co2_direct) / (co2_grid + co2_indirect + co2_direct) * 100
print(f"  Porcentaje reducción: {reduccion_pct:.1f}%")

# ============================================================================
# 8. SOCKET ANALYSIS
# ============================================================================
print("\n🔌 [8] UTILIZACIÓN DE SOCKETS".ljust(90, "-"))

ev_charging = ts_df['ev_charging_kwh'].sum()
total_energy = ts_df['solar_generation_kwh'].sum() + ts_df['grid_import_kwh'].sum()

print(f"\n  EV Charging total: {ev_charging:,.0f} kWh")
print(f"  Energía total disponible: {total_energy:,.0f} kWh")
print(f"  Ratio carga/disponible: {(ev_charging/total_energy)*100:.1f}%")

# ============================================================================
# 9. RECOMENDACIONES
# ============================================================================
print("\n" + "="*90)
print("🚀 RECOMENDACIONES PARA MEJORA CONTINUA".center(90))
print("="*90)

recommendations = []

# Entropía
if overall_entropy_mean > 100:
    recommendations.append("  ⚠️  Entropía muy alta (>100) - Política demasiado exploratoria")
    recommendations.append("      → Reducir ent_coef de 0.02 a 0.01 en próximo entrenamiento")
elif overall_entropy_mean < 10:
    recommendations.append("  ⚠️  Entropía muy baja (<10) - Política muy determinística, poco aprendizaje")
    recommendations.append("      → Aumentar ent_coef de 0.02 a 0.03")
else:
    recommendations.append("  ✓ Entropía óptima - política con buen balance exploración/explotación")

# KL
if kl_pct > 10:
    recommendations.append("  ⚠️  KL divergence frecuentemente alto - Política inestable")
    recommendations.append("      → Reducir learning_rate o aumentar target_kl")
else:
    recommendations.append("  ✓ KL divergence saludable")

# Explained Variance
if ev_neg_pct > 10:
    recommendations.append("  ⚠️  Explained Variance frecuentemente negativa - Value function fallando")
    recommendations.append("      → Aumentar network size o cambiar arquitectura")
else:
    recommendations.append("  ✓ Value function convergiendo correctamente")

# CO2
if reduccion_pct < 50:
    recommendations.append("  ⚠️  CO2 reducción < 50% - Control subóptimo")
    recommendations.append("      → Aumentar co2_weight en reward de 0.35 a 0.50")
else:
    recommendations.append("  ✓ Reducción de CO2 significativa")

for rec in recommendations:
    print(rec)

print("\n" + "="*90 + "\n")
