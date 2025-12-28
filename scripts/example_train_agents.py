#!/usr/bin/env python3
"""Script de ejemplo para verificar que el entrenamiento de agentes funciona correctamente.

Este script demuestra cómo:
1. Entrenar agentes con episodios mínimos (para pruebas rápidas)
2. Verificar que los modelos se guardan correctamente
3. Cargar modelos pre-entrenados

Uso:
    python -m scripts.example_train_agents
"""

from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def verify_training_setup():
    """Verifica que la configuración de entrenamiento sea correcta."""
    print("=" * 60)
    print("VERIFICACIÓN DE SETUP DE ENTRENAMIENTO")
    print("=" * 60)
    
    # Verificar imports
    try:
        from iquitos_citylearn.oe3.agents import make_sac, make_ppo, make_a2c
        from iquitos_citylearn.oe3.agents import SACConfig, PPOConfig, A2CConfig
        from iquitos_citylearn.oe3.agents import detect_device
        print("✓ Imports de agentes exitosos")
    except ImportError as e:
        print(f"✗ Error importando agentes: {e}")
        return False
    
    # Verificar device
    device = detect_device()
    print(f"✓ Dispositivo detectado: {device}")
    
    # Verificar métodos save/load
    from iquitos_citylearn.oe3.agents import SACAgent, PPOAgent, A2CAgent
    
    for agent_name, agent_class in [("SAC", SACAgent), ("PPO", PPOAgent), ("A2C", A2CAgent)]:
        if not hasattr(agent_class, 'save'):
            print(f"✗ {agent_name} no tiene método save")
            return False
        if not hasattr(agent_class, 'load'):
            print(f"✗ {agent_name} no tiene método load")
            return False
        print(f"✓ {agent_name} tiene métodos save/load")
    
    print("=" * 60)
    print("✓ Setup verificado correctamente")
    print("=" * 60)
    return True


def example_minimal_training():
    """Ejemplo de entrenamiento mínimo para testing."""
    print("\n" + "=" * 60)
    print("EJEMPLO: Entrenamiento Mínimo (1 episodio)")
    print("=" * 60)
    
    print("""
Este ejemplo entrena agentes con configuración mínima para verificar
que el pipeline funciona correctamente:

SAC: 1 episodio (8760 pasos)
PPO: 8760 timesteps (1 año simulado)
A2C: 8760 timesteps (1 año simulado)

Para ejecutar:

    python -m scripts.run_oe3_train_agents \\
        --config configs/default.yaml \\
        --agents SAC \\
        --episodes 1

    python -m scripts.run_oe3_train_agents \\
        --agents PPO A2C \\
        --timesteps 8760 \\
        --device cpu

Archivos de salida:
    analyses/oe3/training/checkpoints/sac/sac_final.zip
    analyses/oe3/training/checkpoints/ppo/ppo_final.zip
    analyses/oe3/training/checkpoints/a2c/a2c_final.zip
    analyses/oe3/training/progress/sac_progress.csv
    analyses/oe3/training/sac_training_metrics.csv
    analyses/oe3/training/sac_training.png
    """)
    
    print("=" * 60)


def example_production_training():
    """Ejemplo de entrenamiento para producción."""
    print("\n" + "=" * 60)
    print("EJEMPLO: Entrenamiento Producción")
    print("=" * 60)
    
    print("""
Este ejemplo muestra configuración recomendada para entrenamiento
productivo con GPU:

SAC: 10 episodios (87600 pasos = 10 años simulados)
PPO: 87600 timesteps (10 años simulados)
A2C: 87600 timesteps (10 años simulados)

Para ejecutar:

    # Con GPU (recomendado)
    python -m scripts.run_oe3_train_agents \\
        --config configs/default.yaml \\
        --agents SAC PPO A2C \\
        --episodes 10 \\
        --device cuda

    # Sin GPU (más lento)
    python -m scripts.run_oe3_train_agents \\
        --agents SAC PPO A2C \\
        --episodes 5 \\
        --device cpu

Tiempo estimado:
    - Con GPU (NVIDIA GTX 1080 o superior): ~30-60 min por agente
    - Con CPU (Intel i7 o superior): ~2-4 horas por agente

Archivos de salida:
    analyses/oe3/training/checkpoints/{agent}/{agent}_final.zip
    analyses/oe3/training/checkpoints/{agent}/{agent}_step_8760.zip
    analyses/oe3/training/checkpoints/{agent}/{agent}_step_17520.zip
    analyses/oe3/training/progress/{agent}_progress.csv
    analyses/oe3/training/{agent}_training_metrics.csv
    analyses/oe3/training/{agent}_training.png
    analyses/oe3/training/training_summary.json
    """)
    
    print("=" * 60)


def example_hyperparameter_tuning():
    """Ejemplo de ajuste de hiperparámetros."""
    print("\n" + "=" * 60)
    print("EJEMPLO: Ajuste de Hiperparámetros")
    print("=" * 60)
    
    print("""
Para experimentar con diferentes hiperparámetros, edita
configs/default.yaml:

# SAC - Para control continuo estable
oe3:
  evaluation:
    sac:
      episodes: 10              # Más episodios = mejor convergencia
      device: cuda              # Usar GPU si está disponible
      checkpoint_freq_steps: 8760
      prefer_citylearn: false   # Usar Stable-Baselines3

# PPO - Para entrenamiento robusto
    ppo:
      timesteps: 87600          # Total de pasos (10 años)
      device: cuda
      checkpoint_freq_steps: 8760
      target_kl: 0.015          # Reducir si diverge
      kl_adaptive: true         # Ajustar LR automáticamente
      log_interval: 1000

# A2C - Para prototipado rápido
    a2c:
      timesteps: 87600
      n_steps: 256              # Aumentar para más estabilidad
      learning_rate: 0.0003     # Reducir si no converge
      entropy_coef: 0.01        # Aumentar para más exploración
      device: cuda

Luego ejecutar:

    python -m scripts.run_oe3_train_agents --config configs/default.yaml
    """)
    
    print("=" * 60)


def example_load_pretrained():
    """Ejemplo de cómo cargar modelos pre-entrenados."""
    print("\n" + "=" * 60)
    print("EJEMPLO: Cargar Modelos Pre-entrenados")
    print("=" * 60)
    
    print("""
Código para cargar y usar modelos previamente entrenados:

```python
from pathlib import Path
from iquitos_citylearn.oe3.agents import make_sac, make_ppo, make_a2c
from citylearn.citylearn import CityLearnEnv

# Crear ambiente
schema_path = Path("data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json")
env = CityLearnEnv(schema=str(schema_path))

# Opción 1: Cargar SAC pre-entrenado
agent = make_sac(env)
agent.load("analyses/oe3/training/checkpoints/sac/sac_final")
print("✓ SAC cargado")

# Opción 2: Cargar PPO pre-entrenado
agent = make_ppo(env)
agent.load("analyses/oe3/training/checkpoints/ppo/ppo_final")
print("✓ PPO cargado")

# Opción 3: Cargar A2C pre-entrenado
agent = make_a2c(env)
agent.load("analyses/oe3/training/checkpoints/a2c/a2c_final")
print("✓ A2C cargado")

# Usar agente para predecir acción
obs, _ = env.reset()
action = agent.predict(obs, deterministic=True)
next_obs, reward, terminated, truncated, info = env.step(action)
```

Nota: Los modelos se guardan en formato .zip de Stable-Baselines3
    """)
    
    print("=" * 60)


def main():
    """Ejecuta todas las verificaciones y muestra ejemplos."""
    print("\n" + "=" * 70)
    print(" VERIFICACIÓN Y EJEMPLOS DE ENTRENAMIENTO DE AGENTES RL")
    print("=" * 70 + "\n")
    
    # Verificar setup
    if not verify_training_setup():
        print("\n✗ El setup tiene problemas. Instalar dependencias:")
        print("    pip install -r requirements.txt")
        print("    pip install -e .")
        return
    
    # Mostrar ejemplos
    example_minimal_training()
    example_production_training()
    example_hyperparameter_tuning()
    example_load_pretrained()
    
    print("\n" + "=" * 70)
    print("Para más información, ver: docs/TRAINING_AGENTS.md")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
