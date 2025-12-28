# Integración del Entrenamiento de Agentes con el Pipeline

Esta guía muestra cómo integrar el entrenamiento de agentes RL en el flujo de trabajo del proyecto.

## Flujo Completo del Proyecto

```
1. OE1: Ubicación Estratégica
   ↓
2. OE2: Dimensionamiento (Solar + BESS + Chargers)
   ↓
3. OE3: Dataset CityLearn + Agentes RL
   ↓
4. Evaluación y Comparación CO₂
```

## Dos Modos de Ejecución

### Modo A: Pipeline Integrado (Por Defecto)

Todo en un solo comando. Los agentes se entrenan durante la simulación:

```bash
# Ejecutar pipeline completo
python -m scripts.run_pipeline --config configs/default.yaml
```

**Ventajas:**
- Simple, un solo comando
- Entrenamiento y evaluación en secuencia
- Ideal para pruebas rápidas

**Desventajas:**
- No se guardan modelos intermedios
- Difícil experimentar con hiperparámetros
- Entrenamiento rápido (2 episodios por defecto)

### Modo B: Entrenamiento + Evaluación Separados (Recomendado)

Entrenar primero, evaluar después. Permite más control:

```bash
# Paso 1: Ejecutar OE2 (dimensionamiento)
python -m scripts.run_oe2_solar --config configs/default.yaml
python -m scripts.run_oe2_chargers --config configs/default.yaml
python -m scripts.run_oe2_bess --config configs/default.yaml

# Paso 2: Construir dataset CityLearn
python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# Paso 3: ENTRENAR AGENTES (nuevo script)
python -m scripts.run_oe3_train_agents --config configs/default.yaml \
    --agents SAC PPO A2C \
    --episodes 10

# Paso 4: Evaluar con modelos pre-entrenados
# (Actualmente run_oe3_simulate entrena de nuevo)
# TODO: Modificar simulate.py para cargar modelos existentes
python -m scripts.run_oe3_simulate --config configs/default.yaml

# Paso 5: Generar tabla de comparación
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

**Ventajas:**
- Modelos se guardan para reutilización
- Fácil experimentar con hiperparámetros
- Entrenamiento más largo (10+ episodios)
- Métricas de entrenamiento detalladas

**Desventajas:**
- Más pasos manuales
- Requiere modificar simulate.py para cargar modelos (TODO)

## Configuración para Entrenamiento Intensivo

Editar `configs/default.yaml` para entrenamiento productivo:

```yaml
oe3:
  evaluation:
    agents: ["SAC", "PPO", "A2C"]
    
    sac:
      episodes: 10              # Aumentar a 10-20 para producción
      device: cuda              # Usar GPU
      checkpoint_freq_steps: 8760  # Guardar cada año simulado
      
    ppo:
      timesteps: 87600          # 10 años = 10 * 8760
      device: cuda
      checkpoint_freq_steps: 8760
      
    a2c:
      timesteps: 87600
      device: cuda
      checkpoint_freq_steps: 8760
```

## Estructura de Salidas

```
analyses/oe3/training/
├── checkpoints/           # Modelos entrenados
│   ├── sac/
│   │   ├── sac_step_8760.zip
│   │   ├── sac_step_17520.zip
│   │   └── sac_final.zip
│   ├── ppo/
│   │   └── ppo_final.zip
│   └── a2c/
│       └── a2c_final.zip
├── progress/              # Métricas en tiempo real
│   ├── sac_progress.csv
│   ├── ppo_progress.csv
│   └── a2c_progress.csv
├── sac_training_metrics.csv  # Historial de entrenamiento
├── sac_training.png           # Gráfica de aprendizaje
├── ppo_training_metrics.csv
├── ppo_training.png
├── a2c_training_metrics.csv
├── a2c_training.png
└── training_summary.json      # Resumen de configuración
```

## Workflow Recomendado para Investigación

### 1. Exploración Inicial (CPU, rápido)

```bash
# Entrenamiento mínimo para verificar que funciona
python -m scripts.run_oe3_train_agents \
    --agents SAC PPO A2C \
    --episodes 1 \
    --device cpu
```

### 2. Ajuste de Hiperparámetros (GPU, iterativo)

```bash
# Experimentar con configuraciones
python -m scripts.run_oe3_train_agents \
    --agents SAC \
    --episodes 5 \
    --device cuda

# Revisar métricas
cat analyses/oe3/training/sac_training_metrics.csv

# Ajustar configs/default.yaml según resultados
# Repetir hasta convergencia satisfactoria
```

### 3. Entrenamiento Final (GPU, largo)

```bash
# Entrenamiento completo para resultados finales
python -m scripts.run_oe3_train_agents \
    --agents SAC PPO A2C \
    --episodes 20 \
    --device cuda
```

### 4. Evaluación y Comparación

```bash
# Evaluar con todos los agentes
python -m scripts.run_oe3_simulate --config configs/default.yaml

# Generar tabla de comparación CO₂
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

## TODO: Mejoras Futuras

1. **Modificar `simulate.py` para cargar modelos pre-entrenados:**
   - Detectar si existen modelos en `analyses/oe3/training/checkpoints/`
   - Cargar automáticamente en lugar de entrenar de nuevo
   - Agregar flag `--use-pretrained` / `--train-fresh`

2. **Agregar early stopping basado en recompensa:**
   - Detener entrenamiento si converge antes
   - Ahorrar tiempo de cómputo

3. **Implementar tensorboard logging:**
   - Visualización en tiempo real
   - Comparación de experimentos

4. **Agregar cross-validation:**
   - Entrenar con diferentes seeds
   - Promediar resultados

## Ejemplos Completos

Ver `scripts/example_train_agents.py` para ejemplos detallados de:
- Entrenamiento mínimo
- Entrenamiento productivo
- Ajuste de hiperparámetros
- Carga de modelos pre-entrenados

## Referencias

- `scripts/run_oe3_train_agents.py` - Script de entrenamiento
- `scripts/run_oe3_simulate.py` - Script de simulación/evaluación
- `docs/TRAINING_AGENTS.md` - Guía completa de entrenamiento
- `src/iquitos_citylearn/oe3/agents/` - Implementación de agentes
