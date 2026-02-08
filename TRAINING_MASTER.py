#!/usr/bin/env python3
"""
TRAINING_PPO_MASTER: Limpieza automática + Training PPO nuevo
================================================================================
SOLO PARA PPO - Garantiza entrenamiento fresco sin datos anteriores.
Ejecuta: python TRAINING_MASTER.py
"""

import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime

print("=" * 80)
print("🚀 TRAINING PPO MULTIOBJETIVO - NUEVO Y LIMPIO")
print("=" * 80)
print("   ✅ SOLO PARA PPO (stable-baselines3)")
print("   ✅ Limpieza automática de checkpoints anteriores")
print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ============================================================================
# PASO 1: LIMPIAR CHECKPOINTS ANTIGUOS
# ============================================================================
print("[PASO 1] Limpiando checkpoints PPO antiguos...")
print("-" * 80)

checkpoint_dir = Path("checkpoints/PPO")
output_dir = Path("outputs/ppo_training")

# Limpiar checkpoints
if checkpoint_dir.exists():
    try:
        shutil.rmtree(checkpoint_dir)
        print(f"  ✅ Eliminado: {checkpoint_dir}")
    except Exception as e:
        print(f"  ⚠️  Error eliminando checkpoints: {e}")

# Crear directorio limpio
checkpoint_dir.mkdir(parents=True, exist_ok=True)
print(f"  ✅ Creado limpio: {checkpoint_dir}")

# Limpiar outputs
if output_dir.exists():
    try:
        shutil.rmtree(output_dir)
        print(f"  ✅ Eliminado: {output_dir}")
    except Exception as e:
        print(f"  ⚠️  Error eliminando outputs: {e}")

# Crear directorio limpio
output_dir.mkdir(parents=True, exist_ok=True)
print(f"  ✅ Creado limpio: {output_dir}")

# Limpiar logs antiguos
log_files = list(Path(".").glob("train_ppo_*.log"))
for log_file in log_files:
    try:
        log_file.unlink()
        print(f"  ✅ Eliminado log: {log_file.name}")
    except Exception as e:
        print(f"  ⚠️  Error eliminando {log_file}: {e}")

print()
print("  ✅ PASO 1 COMPLETADO: Sistema limpio")
print()

# ============================================================================
# PASO 2: LIMPIAR SOLO PPO (NO SAC, A2C)
# ============================================================================
print("[PASO 1B] Verificación: ¿Otros agentes presentes?")
print("-" * 80)

other_agents = {
    "SAC": Path("checkpoints/SAC"),
    "A2C": Path("checkpoints/A2C"),
}

for agent_name, agent_path in other_agents.items():
    if agent_path.exists():
        print(f"  ⚠️  {agent_name}: presente (no tocado)")
    else:
        print(f"  ✓ {agent_name}: no presente")

print()
print("  ✅ Solo PPO limpiado - otros agentes intactos")
print()

# ============================================================================
# PASO 3: VALIDAR DATASET
# ============================================================================
print("[PASO 2] Validando dataset OE2...")
print("-" * 80)

dataset_files = [
    Path("data/interim/oe2/solar/pv_generation_timeseries.csv"),
    Path("data/interim/oe2/chargers/chargers_hourly_dataset.csv"),
    Path("data/interim/oe2/bess/bess_hourly_dataset_2024.csv"),
    Path("data/interim/oe2/mall/mall_demand_hourly.csv"),
]

all_exist = True
for dataset_file in dataset_files:
    if dataset_file.exists():
        print(f"  ✅ {dataset_file.name}")
    else:
        print(f"  ❌ FALTA: {dataset_file.name}")
        all_exist = False

if all_exist:
    print()
    print("  ✅ PASO 2 COMPLETADO: Todos los datasets presentes")
else:
    print()
    print("  ⚠️  Algunos datasets faltantes. Continuando...")

print()

# ============================================================================
# PASO 3: LANZAR TRAINING PPO NUEVO
# ============================================================================
print("[PASO 3] LANZANDO TRAINING PPO CON ESCENARIOS DE CARGA")
print("-" * 80)
print()
print("  🎯 CONFIGURACIÓN PPO:")
print("    Agente: PPO (on-policy, stable-baselines3)")
print("    Episodes: 10 × 8,760 horas = 87,600 timesteps")
print("    Device: CUDA (si disponible)")
print("    Duración: ~5-7 horas en GPU RTX 4060")
print()
print("  📊 Nuevas métricas integradas:")
print("    - Vehículos por SOC: 10%, 20%, 30%, 50%, 70%, 80%, 100%")
print("    - Reward bonus: Priorizar 100% > 80% > 70%...")
print()
print("  ⚡ Escenarios de carga (simultáneos):")
print("    - OFF-PEAK (2-6 AM): 28 vehículos, 65 kWh/h")
print("    - PEAK AFTERNOON (14-18 PM): 59 vehículos, 120 kWh/h")
print("    - PEAK EVENING (18-23 PM): 99 vehículos, 195 kWh/h")
print("    - EXTREME PEAK (19-20 PM): 131 vehículos, 252 kWh/h")
print()
print("-" * 80)
print()

try:
    # Ejecutar training
    result = subprocess.run(
        [sys.executable, "train_ppo_multiobjetivo.py"],
        check=False
    )
    
    print()
    print("=" * 80)
    if result.returncode == 0:
        print("✅ TRAINING PPO COMPLETADO EXITOSAMENTE")
        print()
        print("📁 Resultados guardados en:")
        print("  ✓ checkpoints/PPO/latest.zip")
        print("    → Modelo PPO entrenado (10 episodios completos)")
        print("  ✓ outputs/ppo_training/logs.csv")
        print("    → Métricas por cada 1,000 steps")
        print("  ✓ outputs/ppo_training/training_evolution.csv")
        print("    → Resumen por episodio + métricas SOC")
        print()
        print("🔍 Próximos pasos:")
        print("  1. Cargar y evaluar modelo:")
        print("     from stable_baselines3 import PPO")
        print("     model = PPO.load('checkpoints/PPO/latest.zip')")
        print()
        print("  2. Generar gráficos de convergencia:")
        print("     python scripts/plot_training.py")
        print()
        print("  3. Comparar con baselines:")
        print("     python execute_baselines_simple.py")
    else:
        print(f"⚠️  Training finalizó con código: {result.returncode}")
    print("=" * 80)
    
except KeyboardInterrupt:
    print()
    print("⚠️  Training interrumpido por usuario")
    sys.exit(130)
except Exception as e:
    print()
    print(f"❌ Error en training: {e}")
    sys.exit(1)

print()
print(f"Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
