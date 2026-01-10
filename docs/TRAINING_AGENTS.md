# Guía de Entrenamiento de Agentes RL

Esta guía describe cómo entrenar agentes de Reinforcement Learning (SAC, PPO, A2C) para el control de carga de vehículos eléctricos con infraestructura PV+BESS en Iquitos.

## Arquitectura de Agentes

El proyecto incluye tres agentes RL avanzados:

| Agente | Algoritmo | Características | Uso Recomendado |
|--------|-----------|----------------|-----------------|
| **SAC** | Soft Actor-Critic | • Aprendizaje off-policy<br>• Maximización de entropía<br>• Replay buffer eficiente | Control continuo estable |
| **PPO** | Proximal Policy Optimization | • Aprendizaje on-policy<br>• Clipping para estabilidad<br>• GAE para ventajas | Entrenamiento robusto y rápido |
| **A2C** | Advantage Actor-Critic | • Aprendizaje on-policy<br>• Sincrónico<br>• Menor memoria | Prototipado rápido |

Todos los agentes tienen soporte para:
- **GPU/CUDA**: Entrenamiento acelerado en NVIDIA GPUs
- **MPS**: Soporte para Apple Silicon (M1/M2/M3)
- **Checkpointing**: Guardado automático durante entrenamiento
- **Progress tracking**: Monitoreo en tiempo real

## Entrenamiento Independiente

### Script Dedicado: `run_oe3_train_agents.py`

Este script permite entrenar agentes por separado antes de la evaluación:

```bash
# Entrenar todos los agentes con configuración por defecto
python -m scripts.run_oe3_train_agents --config configs/default.yaml

# Entrenar solo SAC y PPO
python -m scripts.run_oe3_train_agents --agents SAC PPO

# Entrenar con más episodios (SAC)
python -m scripts.run_oe3_train_agents --agents SAC --episodes 20

# Entrenar con más timesteps (PPO, A2C)
python -m scripts.run_oe3_train_agents --agents PPO A2C --timesteps 50000

# Forzar uso de GPU
python -m scripts.run_oe3_train_agents --device cuda

# Usar CPU (útil para debugging)
python -m scripts.run_oe3_train_agents --device cpu
```

## Configuración

Ver `configs/default.yaml` para configuración completa de hiperparámetros.

## Referencias

- [Stable-Baselines3 Documentation](https://stable-baselines3.readthedocs.io/)
- [CityLearn Documentation](https://intelligent-environments-lab.github.io/CityLearn/)
