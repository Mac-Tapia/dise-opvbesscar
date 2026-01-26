#!/usr/bin/env python3
"""
VERIFICACIÓN RÁPIDA: Configuraciones de Agentes
================================================
Verifica que todos los agentes estén correctamente configurados
antes de iniciar el entrenamiento.

Uso: python scripts/verificar_agentes.py
"""

import sys
from pathlib import Path

# Agregar src al path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

def verificar_imports():
    """Verifica que todos los módulos se puedan importar."""
    print("🔍 Verificando imports...")

    try:
        from iquitos_citylearn.oe3.agents import (
            SACConfig, SACAgent, make_sac,
            PPOConfig, PPOAgent, make_ppo,
            A2CConfig, A2CAgent, make_a2c,
        )
        from iquitos_citylearn.oe3.rewards import (
            MultiObjectiveReward,
            MultiObjectiveWeights,
            IquitosContext,
        )
        print("  ✅ Todos los imports exitosos")
        return True
    except ImportError as e:
        print(f"  ❌ Error de import: {e}")
        return False

def verificar_configs():
    """Verifica las configuraciones de cada agente."""
    print("\n📋 Verificando configuraciones...")

    from iquitos_citylearn.oe3.agents import SACConfig, PPOConfig, A2CConfig
    from iquitos_citylearn.oe3.rewards import MultiObjectiveWeights

    configs = {
        "SAC": SACConfig(),
        "PPO": PPOConfig(),
        "A2C": A2CConfig(),
    }

    weights = MultiObjectiveWeights()

    print("\n  Pesos de Recompensa Multiobjetivo:")
    print(f"    - CO₂:           {weights.co2:.2f} (PRIMARY)")
    print(f"    - Solar:         {weights.solar:.2f}")
    print(f"    - Costo:         {weights.cost:.2f}")
    print(f"    - EV:            {weights.ev_satisfaction:.2f}")
    print(f"    - Grid:          {weights.grid_stability:.2f}")
    print(f"    - Total:         {weights.co2 + weights.solar + weights.cost + weights.ev_satisfaction + weights.grid_stability:.2f}")

    print("\n  Configuraciones de Agentes:")

    for name, cfg in configs.items():
        print(f"\n  {name}:")
        print(f"    - Learning Rate:      {cfg.learning_rate:.2e}")
        if hasattr(cfg, 'batch_size'):
            print(f"    - Batch Size:         {cfg.batch_size}")
        if hasattr(cfg, 'n_steps'):
            print(f"    - N Steps:            {cfg.n_steps}")
        if hasattr(cfg, 'hidden_sizes'):
            print(f"    - Hidden Sizes:       {cfg.hidden_sizes}")
        if hasattr(cfg, 'activation'):
            print(f"    - Activation:         {cfg.activation}")
        if hasattr(cfg, 'ent_coef'):
            print(f"    - Entropy Coef:       {cfg.ent_coef:.3f}")

        # Verificar normalización
        norm_obs = getattr(cfg, 'normalize_observations', False)
        norm_rew = getattr(cfg, 'normalize_rewards', False)
        print(f"    - Norm Observations:  {'✅' if norm_obs else '❌'}")
        print(f"    - Norm Rewards:       {'✅' if norm_rew else '❌'}")

        # Verificar pesos multiobjetivo
        w_co2 = getattr(cfg, 'weight_co2', 0.0)
        w_solar = getattr(cfg, 'weight_solar', 0.0)
        w_cost = getattr(cfg, 'weight_cost', 0.0)
        w_ev = getattr(cfg, 'weight_ev_satisfaction', 0.0)
        w_grid = getattr(cfg, 'weight_grid_stability', 0.0)
        total_weight = w_co2 + w_solar + w_cost + w_ev + w_grid

        if total_weight > 0:
            print(f"    - Pesos (CO₂/Solar/Cost/EV/Grid): {w_co2:.2f}/{w_solar:.2f}/{w_cost:.2f}/{w_ev:.2f}/{w_grid:.2f}")

        # Verificar checkpoints
        ckpt_freq = getattr(cfg, 'checkpoint_freq_steps', 0)
        print(f"    - Checkpoint Freq:    {ckpt_freq} steps {'✅' if ckpt_freq > 0 else '❌'}")

    print("\n  ✅ Todas las configuraciones verificadas")
    return True

def verificar_gpu():
    """Verifica disponibilidad de GPU."""
    print("\n🎮 Verificando GPU/CUDA...")

    try:
        import torch

        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
            gpu_mem_alloc = torch.cuda.memory_allocated(0) / 1024**3
            gpu_mem_reserved = torch.cuda.memory_reserved(0) / 1024**3

            print(f"  ✅ GPU disponible: {gpu_name}")
            print(f"  📊 Memoria total:    {gpu_mem_total:.1f} GB")
            print(f"  📊 Memoria usada:    {gpu_mem_alloc:.1f} GB")
            print(f"  📊 Memoria reservada: {gpu_mem_reserved:.1f} GB")
            print(f"  📊 Memoria libre:    {gpu_mem_total - gpu_mem_reserved:.1f} GB")

            # Verificar CUDA version
            print(f"  🔧 CUDA Version:     {torch.version.cuda}")
            print(f"  🔧 cuDNN Version:    {torch.backends.cudnn.version()}")

            return True
        else:
            print("  ⚠️  CUDA no disponible, se usará CPU")
            print("  ℹ️  El entrenamiento será MÁS LENTO en CPU")
            return True

    except ImportError:
        print("  ❌ PyTorch no está instalado")
        return False
    except Exception as e:
        print(f"  ❌ Error al verificar GPU: {e}")
        return False

def verificar_datos():
    """Verifica que los datos de entrenamiento existan."""
    print("\n📁 Verificando datos de entrenamiento...")

    data_dir = ROOT / "data"

    # Verificar datos OE2
    chargers_file = data_dir / "interim" / "oe2" / "chargers" / "individual_chargers.json"
    if chargers_file.exists():
        import json
        with open(chargers_file, 'r') as f:
            chargers = json.load(f)
        motos = len([c for c in chargers if c.get('playa') == 'Playa_Motos'])
        taxis = len([c for c in chargers if c.get('playa') == 'Playa_Mototaxis'])
        print(f"  ✅ Cargadores: {motos} motos + {taxis} mototaxis = {len(chargers)} total")
    else:
        print(f"  ⚠️  No encontrado: {chargers_file}")

    # Verificar dataset CityLearn
    processed_dir = data_dir / "processed" / "citylearn"
    if processed_dir.exists():
        schemas = list(processed_dir.glob("*/schema*.json"))
        if schemas:
            print(f"  ✅ Dataset CityLearn: {len(schemas)} schemas encontrados")
            for schema in schemas[:3]:  # Mostrar primeros 3
                print(f"    - {schema.parent.name}/{schema.name}")
        else:
            print(f"  ⚠️  No se encontraron schemas en {processed_dir}")
    else:
        print(f"  ⚠️  No encontrado: {processed_dir}")

    return True

def main():
    """Ejecuta todas las verificaciones."""
    print("=" * 80)
    print(" VERIFICACIÓN DE CONFIGURACIONES DE AGENTES")
    print("=" * 80)

    checks = [
        ("Imports", verificar_imports),
        ("Configuraciones", verificar_configs),
        ("GPU/CUDA", verificar_gpu),
        ("Datos", verificar_datos),
    ]

    results = []

    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Error en verificación '{name}': {e}")
            results.append((name, False))

    # Resumen final
    print("\n" + "=" * 80)
    print(" RESUMEN DE VERIFICACIÓN")
    print("=" * 80)

    all_passed = all(r[1] for r in results)

    for name, passed in results:
        status = "✅ OK" if passed else "❌ FAIL"
        print(f"  {status:<10} {name}")

    print("\n" + "=" * 80)

    if all_passed:
        print("\n✅ TODAS LAS VERIFICACIONES PASARON")
        print("\n🚀 Listo para entrenar! Ejecuta:")
        print("\n  python scripts/train_gpu_robusto.py --agent SAC --episodes 5 --device cuda")
        print("  python scripts/train_gpu_robusto.py --agent PPO --episodes 5 --device cuda")
        print("  python scripts/train_gpu_robusto.py --agent A2C --episodes 5 --device cuda")
        print("\n  O todos a la vez:")
        print("  python scripts/train_agents_serial.py --device cuda --episodes 5")
        print("\n" + "=" * 80)
        return 0
    else:
        print("\n❌ ALGUNAS VERIFICACIONES FALLARON")
        print("\nRevisa los errores arriba antes de entrenar.")
        print("=" * 80)
        return 1

if __name__ == "__main__":
    sys.exit(main())
