"""
AUDITORÍA Y PLAN DE LIMPIEZA - 18-enero-2026

Estado: Identificar duplicados, conflictos y consolidar
"""

# ARCHIVOS ENCONTRADOS
TRAINING_SCRIPTS = {
    "train_tier2_v2_gpu.py": {
        "estado": "PRODUCCIÓN - MANTENER",
        "versión": "V2 mejorada",
        "características": ["GPU optimizado", "Entropy 0.01 fijo", "LR dinámico", "Wrapper V2"],
        "target_agents": ["A2C", "PPO", "SAC"],
    },
    "train_tier2_gpu_real.py": {
        "estado": "DUPLICADO - ELIMINAR",
        "razón": "Superado por train_tier2_v2_gpu.py",
        "versión": "V1 sin mejorasV2",
    },
    "train_tier2_cpu.py": {
        "estado": "DUPLICADO - ELIMINAR",
        "razón": "CPU fallback, V1 sin mejoras",
        "versión": "V1",
    },
    "train_tier2_final.py": {
        "estado": "DUPLICADO - ELIMINAR",
        "razón": "Intento fallido con Unicode",
        "versión": "V1",
    },
    "train_tier2_serial_fixed.py": {
        "estado": "DUPLICADO - ELIMINAR",
        "razón": "Intento temprano, errores de parámetros",
        "versión": "V0.5",
    },
    "train_tier2_serial_2ep.py": {
        "estado": "DUPLICADO - ELIMINAR",
        "razón": "Similar a serial_fixed",
        "versión": "V0.5",
    },
    "train_tier2_2ep.py": {
        "estado": "DUPLICADO - ELIMINAR",
        "razón": "Intento temprano",
        "versión": "V0.5",
    },
    "train_sac_simple.py": {
        "estado": "REVISAR - POTENCIAL MANTENER",
        "razón": "SAC individual, útil para debug",
        "recomendación": "Actualizar a V2 si es útil, sino eliminar",
    },
    "train_agents_serial_gpu.py": {
        "estado": "REVISAR",
        "razón": "Script serial antiguo",
    },
    "train_agents_serial_auto.py": {
        "estado": "REVISAR",
        "razón": "Script serial antiguo",
    },
    "scripts/train_agents_serial.py": {
        "estado": "REVISAR",
        "razón": "Script serial en carpeta scripts/",
    },
}

# MÉTRICAS A VERIFICAR
METRICS_CHECKLIST = {
    "rewards.py": {
        "✓ MultiObjectiveWeights": "Definido",
        "✓ r_co2": "Normalizado [-1, 1]",
        "✓ r_cost": "Normalizado [-1, 1]",
        "✓ r_solar": "Normalizado [-1, 1]",
        "✓ r_ev": "Normalizado [-1, 1]",
        "✓ r_grid": "Normalizado [-1, 1]",
        "✓ reward_total": "Clipeado [-1, 1]",
    },
    "rewards_improved_v2.py": {
        "✓ ImprovedWeights": "Definido",
        "✓ Peak power penalty": "Explícito",
        "✓ SOC reserve penalty": "Explícito",
        "✓ Import peak penalty": "Explícito",
        "✓ Fairness penalty": "Explícito",
        "✓ reward_total": "Clipeado [-1, 1]",
    },
    "simulate.py": {
        "✓ SimulationResult": "Con métricas CO2, reward",
        "✓ agent.learn()": "Usa timesteps correctos",
        "✓ env.step()": "Captura rewards",
    },
}

# ROLES Y CONTROL POR AGENTE
AGENT_ROLES = {
    "A2C (Advantage Actor-Critic)": {
        "rol": "Exploración equilibrada, convergencia estable",
        "control": "n_steps=1024, lr=2.5e-4, ent_coef=0.01",
        "objetivo": "Minimizar CO2 + maximizar autoconsumo",
        "restricción": "SOC pre-pico >= 0.85",
        "métrica": "r_co2 + r_soc_reserve",
    },
    "PPO (Proximal Policy Optimization)": {
        "rol": "Optimización robusta con clipping",
        "control": "batch=256, n_epochs=15, clip_range=0.2, use_sde=True",
        "objetivo": "Minimizar CO2 + maximizar autoconsumo",
        "restricción": "Power pico <= 150 kW (18-21h)",
        "métrica": "r_co2 + r_peak_power_penalty",
    },
    "SAC (Soft Actor-Critic)": {
        "rol": "Exploración continua con entropy regulado",
        "control": "batch=256, lr=2.5e-4, ent_coef=0.01",
        "objetivo": "Minimizar importación en pico",
        "restricción": "Fairness playas >= 0.67 (max/min)",
        "métrica": "r_import_peak + r_fairness",
    },
}

# LIMPIEZA PROPUESTA
CLEANUP_PLAN = {
    "ELIMINAR": [
        "train_tier2_gpu_real.py",
        "train_tier2_cpu.py",
        "train_tier2_final.py",
        "train_tier2_serial_fixed.py",
        "train_tier2_serial_2ep.py",
        "train_tier2_2ep.py",
    ],
    "REVISAR": [
        "train_sac_simple.py",
        "train_agents_serial_gpu.py",
        "train_agents_serial_auto.py",
        "scripts/train_agents_serial.py",
    ],
    "MANTENER": [
        "train_tier2_v2_gpu.py",  # Producción
    ],
    "DOCUMENTAR": [
        "TIER2_V2_IMPROVEMENTS.md",
        "compare_tier2_v1_vs_v2.py",
    ],
}

print(__doc__)
print("\nESTADO DE ARCHIVOS:")
for name, info in TRAINING_SCRIPTS.items():
    print(f"\n{name}:")
    for key, val in info.items():
        print(f"  {key}: {val}")

print("\n" + "="*80)
print("PLAN DE LIMPIEZA PROPUESTO")
print("="*80)

print("\nA ELIMINAR (7 archivos):")
for f in CLEANUP_PLAN["ELIMINAR"]:
    print(f"  - {f}")

print("\nA REVISAR (4 archivos):")
for f in CLEANUP_PLAN["REVISAR"]:
    print(f"  - {f}")

print("\nA MANTENER (1 archivo):")
for f in CLEANUP_PLAN["MANTENER"]:
    print(f"  - {f}")

print("\nMÉTRICAS VERIFICADAS:")
for module, metrics in METRICS_CHECKLIST.items():
    print(f"\n{module}:")
    for metric, status in metrics.items():
        print(f"  {metric}: {status}")

print("\nROLES Y CONTROL POR AGENTE:")
for agent, role_info in AGENT_ROLES.items():
    print(f"\n{agent}:")
    for key, val in role_info.items():
        print(f"  {key}: {val}")
