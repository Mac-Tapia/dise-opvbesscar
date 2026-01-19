"""
COMPARATIVA VISUAL: TIER 2 V1 vs V2
====================================

Visualización de las mejoras implementadas en el sistema de recompensas
y observables para optimización RL en Iquitos EV charging.

Generado: 18-enero-2026
"""

# Recompensas por hora en día típico (visualización)
print("\n" + "="*90)
print("COMPARATIVA: Impacto de recompensa CO₂ por hora (V1 vs V2)")
print("="*90)

import numpy as np

hours = list(range(24))
# V1: penalización 1.0x fuera pico, 2.0x en pico
v1_co2_factors = [1.0]*24
for h in [18, 19, 20, 21]:
    v1_co2_factors[h] = 2.0

# V2: penalización 1.2x fuera pico, 2.5x en pico
v2_co2_factors = [1.2]*24
for h in [18, 19, 20, 21]:
    v2_co2_factors[h] = 2.5

print("\nHora | V1 Factor | V2 Factor | Mejora | Tipo")
print("-" * 50)
for h, v1, v2 in zip(hours, v1_co2_factors, v2_co2_factors):
    mejora = ((v2 - v1) / v1 * 100) if v1 > 0 else 0
    tipo = ["PICO" if h in [18,19,20,21] else "Pre-Pico" if h in [16,17] else "Valle" if h in [9,10,11] else "Normal"][0]
    print(f"{h:2d}  |   {v1:.1f}x    |   {v2:.1f}x    | +{mejora:5.1f}% | {tipo}")

print("\n" + "="*90)
print("COMPARATIVA: Observables disponibles")
print("="*90)

observables_v1 = [
    "grid_import_kwh",
    "solar_generation_kwh", 
    "ev_charging_kwh",
    "ev_soc_avg",
    "bess_soc",
]

observables_v2_new = [
    "is_peak_hour (flag 0/1)",
    "is_pre_peak (flag 0/1)",
    "is_valley_hour (flag 0/1)",
    "hour_of_day (0-23)",
    "bess_soc_current",
    "bess_soc_target (dinámico)",
    "bess_soc_reserve_deficit",
    "pv_power_available_kw",
    "pv_power_ratio (FV / EV_total)",
    "grid_import_power_kw",
    "ev_power_total_kw",
    "ev_power_motos_kw",
    "ev_power_mototaxis_kw",
    "ev_power_fairness_ratio (max/min)",
    "pending_sessions_motos",
    "pending_sessions_mototaxis",
]

print("\nV1 (Básicos):")
for obs in observables_v1:
    print(f"  ✓ {obs}")

print(f"\nV2 (NUEVOS - {len(observables_v2_new)} adicionales):")
for obs in observables_v2_new:
    print(f"  ✓ {obs}")

print(f"\nTotal V1: {len(observables_v1)}")
print(f"Total V2: {len(observables_v1) + len(observables_v2_new)}")

print("\n" + "="*90)
print("COMPARATIVA: Pesos y Penalizaciones")
print("="*90)

import pandas as pd

data = {
    "Componente": [
        "CO₂ Priority",
        "Solar Secondary", 
        "Costo Reducido",
        "EV Satisfaction",
        "Grid Stability",
        "Peak Power Penalty",
        "SOC Reserve Penalty",
        "Import Peak Penalty",
        "Fairness Penalty",
        "Entropy Coef",
        "LR Normal",
        "LR Pico",
    ],
    "V1": ["0.50", "0.20", "0.15", "0.10", "0.05", "Implícito", "Fijo 0.65", "Implícito", "N/A", "0.02", "2.5e-4", "2.5e-4"],
    "V2": ["0.55↑", "0.20", "0.10↓", "0.10", "0.05", "0.30 Explícito", "Dinámico", "0.25 Explícito", "0.10 Explícito", "0.01 FIJO↓", "2.5e-4", "1.5e-4↓"],
}

df = pd.DataFrame(data)
print(df.to_string(index=False))

print("\n" + "="*90)
print("PENALIZACIONES EXPLÍCITAS EN V2")
print("="*90)

penalties = {
    "Peak Power": {
        "Condición": "EV power > 150 kW durante 18-21h",
        "Penalidad": "-0.30 (máximo)",
        "Fórmula": "-(power_excess / limit) * weight"
    },
    "SOC Reserve": {
        "Condición": "BESS SOC < target pre-pico (16-17h)",
        "Penalidad": "-0.20 (máximo)",
        "Fórmula": "-(soc_deficit / soc_target) * weight"
    },
    "Import Peak": {
        "Condición": "Grid import > 100 kWh durante pico",
        "Penalidad": "-0.25 (máximo)",
        "Fórmula": "-(import_excess / baseline) * weight"
    },
    "Fairness": {
        "Condición": "Ratio playas > 1.5 (máx/mín potencia)",
        "Penalidad": "-0.10 (máximo)",
        "Fórmula": "-(fairness_excess / threshold) * weight"
    }
}

for penalty_name, details in penalties.items():
    print(f"\n{penalty_name}:")
    for key, val in details.items():
        print(f"  {key}: {val}")

print("\n" + "="*90)
print("HORAS CRÍTICAS - TARGETS DINÁMICOS")
print("="*90)

targets = {
    "Hora": ["0-8 (Noche)", "9-11 (Valle)", "12-15 (Normal)", "16-17 (Pre-pico)", "18-21 (PICO)", "22-23 (Noche)"],
    "SOC Target": ["0.60", "0.60", "0.60", "0.85↑", "0.40↓", "0.60"],
    "CO₂ Penalty": ["1.2x", "1.2x", "1.2x", "1.5x", "2.5x↑", "1.2x"],
    "Power Limit": ["200 kW", "200 kW", "200 kW", "200 kW", "150 kW HARD", "200 kW"],
}

df_targets = pd.DataFrame(targets)
print(df_targets.to_string(index=False))

print("\n" + "="*90)
print("EFECTOS ESPERADOS EN ENTRENAMIENTO")
print("="*90)

effects = {
    "Métrica": [
        "Importación en pico",
        "Cumplimiento reserva SOC",
        "Equidad entre playas",
        "Exploración del agente",
        "Estabilidad crítica",
        "Convergencia",
    ],
    "V1": [
        "200-300 kWh/h",
        "60-70%",
        "Bajo control",
        "Exploración alta (0.02)",
        "Inestable post-pico",
        "Lenta",
    ],
    "V2 Esperado": [
        "150-200 kWh/h↓",
        "85-95%↑",
        "Mejor (~1.3 ratio)",
        "Controlada (0.01)",
        "Más estable",
        "Más rápida",
    ]
}

df_effects = pd.DataFrame(effects)
print(df_effects.to_string(index=False))

print("\n" + "="*90)
print("CÓMO EJECUTAR ENTRENAMIENTO V2")
print("="*90)

exec_cmd = """
# Opción 1: Script listo (RECOMENDADO)
python train_tier2_v2_gpu.py

# Opción 2: Manual con config custom
from src.iquitos_citylearn.oe3.tier2_v2_config import TIER2V2Config
from src.iquitos_citylearn.oe3.rewards_wrapper_v2 import ImprovedRewardWrapper

config = TIER2V2Config(
    co2_weight=0.60,  # Ajuste si es necesario
    peak_power_penalty=0.35,  # Aumentar para penalización más fuerte
)
env = ImprovedRewardWrapper(env, config=config)
"""

print(exec_cmd)

print("\n" + "="*90)
print("✓ Comparativa completada - Ready for TIER 2 V2 training!")
print("="*90 + "\n")
