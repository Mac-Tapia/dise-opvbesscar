#!/usr/bin/env python3
"""
Visualización de Peak Shaving Factor vs Mall Demand.
Muestra cómo el beneficio CO2 de BESS varía según carga del mall.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Crear figura con mejor estilo
plt.style.use('seaborn-v0_8-darkgrid')
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Peak Shaving Factor for BESS CO₂ Reduction\nImplementación en SAC/A2C/PPO', 
             fontsize=16, fontweight='bold', y=0.995)

# Rango de demandas del mall
mall_kw_range = np.linspace(0, 5000, 1000)

def calculate_peak_shaving_factor(mall_kw):
    """Calcula factor de peak shaving según demanda."""
    factors = np.zeros_like(mall_kw_range)
    for i, m in enumerate(mall_kw_range):
        if m > 2000.0:
            factors[i] = 1.0 + (m - 2000.0) / max(1.0, m) * 0.5
        else:
            factors[i] = 0.5 + (m / 2000.0) * 0.5
    return factors

factors = calculate_peak_shaving_factor(mall_kw_range)

# ========== AX1: Factor vs Mall Demand ==========
ax = axes[0, 0]
ax.plot(mall_kw_range, factors, linewidth=3, color='#2ecc71', label='Peak Shaving Factor')
ax.axvline(2000, color='red', linestyle='--', linewidth=2, label='Baseline/Peak Threshold (2000 kW)')
ax.axhline(1.0, color='orange', linestyle=':', linewidth=1.5, alpha=0.7)
ax.fill_between(mall_kw_range, factors, 0.5, where=(mall_kw_range <= 2000), 
                alpha=0.2, color='blue', label='Baseline Zone')
ax.fill_between(mall_kw_range, factors, 1.0, where=(mall_kw_range > 2000), 
                alpha=0.2, color='red', label='Peak Shaving Zone')
ax.set_xlabel('Mall Demand (kW)', fontsize=11, fontweight='bold')
ax.set_ylabel('Peak Shaving Factor', fontsize=11, fontweight='bold')
ax.set_title('Factor de beneficio CO₂ según carga mall', fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3)
ax.legend(loc='lower right', fontsize=10)
ax.set_xlim(0, 5000)
ax.set_ylim(0.4, 1.3)

# ========== AX2: CO2 Benefit vs Mall Demand (BESS 50 kW discharge) ==========
ax = axes[0, 1]
bess_discharge = 50.0  # kW
co2_factor = 0.4521  # kg CO2/kWh
bess_co2_benefit = bess_discharge * factors * co2_factor

ax.plot(mall_kw_range, bess_co2_benefit, linewidth=3, color='#3498db', label='BESS CO₂ Benefit')
ax.axvline(2000, color='red', linestyle='--', linewidth=2, label='Baseline/Peak Threshold')
ax.fill_between(mall_kw_range, bess_co2_benefit, 0, alpha=0.2, color='#3498db')
ax.set_xlabel('Mall Demand (kW)', fontsize=11, fontweight='bold')
ax.set_ylabel('CO₂ Evitado por BESS (kg/h)', fontsize=11, fontweight='bold')
ax.set_title(f'CO₂ Evitado por BESS Descargando {bess_discharge} kW', fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3)
ax.legend(loc='upper left', fontsize=10)
ax.set_xlim(0, 5000)

# ========== AX3: Comparison Solar vs BESS ==========
ax = axes[1, 0]
solar_co2 = 100 * co2_factor  # 100 kW solar
bess_co2 = bess_discharge * factors * co2_factor

x_pos = np.arange(len([1000, 2000, 2500, 3000, 3500, 4000]))
mall_values = [1000, 2000, 2500, 3000, 3500, 4000]
factors_values = np.array([calculate_peak_shaving_factor(np.array([m]))[0] for m in mall_values])
bess_values = bess_discharge * factors_values * co2_factor

width = 0.35
ax.bar(x_pos - width/2, [solar_co2]*len(mall_values), width, label='Solar (100 kW)', 
       color='#f39c12', alpha=0.8)
ax.bar(x_pos + width/2, bess_values, width, label=f'BESS ({bess_discharge} kW)', 
       color='#3498db', alpha=0.8)
ax.set_xlabel('Mall Demand Scenario', fontsize=11, fontweight='bold')
ax.set_ylabel('CO₂ Evitado (kg/h)', fontsize=11, fontweight='bold')
ax.set_title('Comparación: Solar vs BESS Benefit por Demanda', fontsize=12, fontweight='bold')
ax.set_xticks(x_pos)
ax.set_xticklabels([f'{m}\nkW' for m in mall_values], fontsize=9)
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3, axis='y')

# ========== AX4: Factor Improvement vs Baseline ==========
ax = axes[1, 1]
baseline_factor = 0.75  # factor @ 1000 kW
improvement = ((factors_values - baseline_factor) / baseline_factor) * 100

colors = ['green' if f < 1.0 else 'red' for f in factors_values]
bars = ax.bar(x_pos, improvement, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
ax.axhline(0, color='black', linestyle='-', linewidth=1)
ax.axvline(1, color='red', linestyle='--', linewidth=2, alpha=0.5)  # x=2000 position
ax.set_xlabel('Mall Demand Scenario', fontsize=11, fontweight='bold')
ax.set_ylabel('Improvement vs Baseline @ 1000kW (%)', fontsize=11, fontweight='bold')
ax.set_title('Peak Shaving Benefit: % Improvement vs Baseline', fontsize=12, fontweight='bold')
ax.set_xticks(x_pos)
ax.set_xticklabels([f'{m}\nkW' for m in mall_values], fontsize=9)

# Añadir valores en top de barras
for i, (bar, val) in enumerate(zip(bars, improvement)):
    height = bar.get_height()
    label_y = height + (2 if height > 0 else -5)
    ax.text(bar.get_x() + bar.get_width()/2, label_y, f'{val:.1f}%',
            ha='center', va='bottom' if height > 0 else 'top', fontsize=9, fontweight='bold')

ax.grid(True, alpha=0.3, axis='y')
ax.set_ylim(min(improvement) - 10, max(improvement) + 10)

# Adjustar layout
plt.tight_layout()

# Guardar figura
output_dir = Path('outputs/analysis')
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / 'peak_shaving_factor_analysis.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"✅ Figura guardada: {output_path}")

# Crear tabla de referencia
print("\n" + "="*80)
print("PEAK SHAVING FACTOR REFERENCE TABLE")
print("="*80)
print(f"{'Mall Demand':>15} | {'Peak Shaving':>15} | {'BESS CO₂':>15} | {'%vs Baseline':>15}")
print(f"{'(kW)':>15} | {'Factor':>15} | {'(kg/h @ 50kW)':>15} | {'@ 1000kW':>15}")
print("-"*80)

for mall_kw in [500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000]:
    factor = calculate_peak_shaving_factor(np.array([mall_kw]))[0]
    bess_benefit = bess_discharge * factor * co2_factor
    improvement = ((factor - baseline_factor) / baseline_factor) * 100
    print(f"{mall_kw:>15.0f} | {factor:>15.4f} | {bess_benefit:>15.2f} | {improvement:>+14.1f}%")

print("="*80)
print("\n📊 Reference Table:")
print("  • Factor @ 1000 kW (baseline): 0.7500")
print("  • Factor @ 2000 kW (transition): 1.0000")
print("  • Factor @ 3000 kW (peak): 1.1667 (+55.6% vs baseline)")
print("  • Factor @ 4000 kW (peak): 1.2500 (+66.7% vs baseline)")
print("\n💡 Interpretation:")
print("  - En picos: BESS descargando evita encender diesel generator")
print("  - En baseline: BESS aún reduce imports pero con beneficio menor")
print("  - Máximo beneficio teórico: 1.5x factor (cuando mall muy > 2000 kW)")

plt.show()
