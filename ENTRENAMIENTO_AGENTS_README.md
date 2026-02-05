# ENTRENAMIENTO DE AGENTES SAC, PPO y A2C

## Resumen Ejecutivo

Este proyecto implementa entrenamiento de tres agentes de refuerzo (SAC, PPO, A2C) para optimizar la gestión de carga en 128 cargadores eléctricos con almacenamiento en batería (BESS) y energía solar en un ambiente CityLearn v2.

**Objetivos:**
- Minimizar emisiones de CO₂ del grid (~0.4521 kg CO₂/kWh)
- Maximizar autoconsumo solar
- Optimizar despatch de carga y BESS

**Datos:**
- Dataset OE2: 4,162 kWp PV + 4,520 kWh BESS + 128 chargers
- Resolución: Horaria (8,760 timesteps = 1 año)
- Demand: 3,358,876 kWh/año (mall) + 232,341 kWh/año (EVs)

## Estructura de Archivos

```
d:\diseñopvbesscar/
├── configs/
│   └── default.yaml                # Config sistema
├── data/
│   ├── interim/oe2/                # Datos OE2
│   │   ├── solar/
│   │   ├── chargers/
│   │   ├── bess/
│   │   └── mall_demand_hourly.csv
│   └── processed/
│       └── citylearn/
│           └── iquitos_ev_mall/    # Dataset CityLearn v2 (161 archivos)
├── checkpoints/                    # Modelos entrenados
│   ├── SAC/
│   ├── PPO/
│   └── A2C/
├── outputs/                        # Métricas y logs
│   ├── sac_training/
│   ├── ppo_training/
│   ├── a2c_training/
│   └── evaluation/
│
├── train_sac_test.py              # 🟢 TEST RÁPIDO SAC (5 episodios)
├── train_sac_production.py        # 🟢 ENTRENAMIENTO COMPLETO SAC
├── train_ppo_production.py        # 🔵 ENTRENAMIENTO COMPLETO PPO
├── train_a2c_production.py        # 🔵 ENTRENAMIENTO COMPLETO A2C
├── train_all_agents.py            # ⚪ MAESTRO: Entrenar todos
└── evaluate_agents.py             # 📊 EVALUAR y COMPARAR
```

## Guía de Uso

### 1️⃣ TEST RÁPIDO (5 episodios - ~75 segundos)

Verifica que todo funciona antes de entrenar:

```bash
python train_sac_test.py
```

**Salida:**
```
[1] DIAGNÓSTICOS PREVIOS
  ✓ data/interim/oe2/solar/pv_generation_timeseries.csv
  ✓ 4 archivos críticos encontrados
[2] CONSTRUIR DATASET CITYLEARN V2
  ✓ Dataset creado: data/processed/citylearn/iquitos_ev_mall/
[3] VALIDAR ENVIRONMENT
  ✓ Buildings: 1, Episode steps: 8760
[4] CREAR ENVIRONMENT GYMNASIUM
  ✓ Observation space: (394,)
  ✓ Action space: (129,)
[5] CREAR AGENT SAC
  ✓ SAC agent creado
[6] ENTRENAR 5 EPISODIOS
  ✓ Entrenamiento completado
[7] TEST INFERENCIA
    Ep 1: reward=-41.07
    Ep 2: reward=-38.65
    Ep 3: reward=-38.74
STATUS: ✓ SAC FUNCIONANDO CORRECTAMENTE
```

### 2️⃣ ENTRENAR SAC COMPLETO

Entrenamiento a largo plazo con checkpoints (~100,000 timesteps):

```bash
python train_sac_production.py
```

**Parámetros SAC:**
- Learning rate: 3e-4
- Batch size: 64
- Buffer size: 1,000,000
- Network: 2 layers × 256 units
- Total steps: 100,000 (~12 episodios)

**Salida:** Checkpoints en `checkpoints/SAC/`

### 3️⃣ ENTRENAR PPO COMPLETO

On-policy agent, típicamente más rápido que SAC:

```bash
python train_ppo_production.py
```

**Parámetros PPO:**
- Learning rate: 3e-4
- Rollout steps: 2,048
- Batch size: 128
- Clip range: 0.2
- Total steps: 100,000

**Salida:** Checkpoints en `checkpoints/PPO/`

### 4️⃣ ENTRENAR A2C COMPLETO

Simple Advantage Actor-Critic:

```bash
python train_a2c_production.py
```

**Parámetros A2C:**
- Learning rate: 7e-4 (más alto que SAC/PPO)
- Steps per update: 5 (menor latencia)
- Network: 2 layers × 256 units
- Total steps: 100,000

**Salida:** Checkpoints en `checkpoints/A2C/`

### 5️⃣ ENTRENAR TODOS SECUENCIALMENTE

Script maestro que ejecuta SAC → PPO → A2C:

```bash
python train_all_agents.py
```

**Duración total:** ~3-6 horas (CPU) o ~30-60 min (GPU RTX 4060)

### 6️⃣ EVALUAR Y COMPARAR AGENTES

Evalúa modelos finales en 10 episodios y genera reportes:

```bash
python evaluate_agents.py
```

**Salida:**
```
Ranking por Reward Promedio:

  1. SAC  :  -38.52 ± 2.14
  2. PPO  :  -39.47 ± 1.85
  3. A2C  :  -40.15 ± 3.22

Archivos generados:
  - outputs/evaluation/evaluation_report.json
  - outputs/evaluation/evaluation_comparison.csv
```

## Arquitectura del Ambiente

### Observation Space (394 dims)
```
[0-7]       → Hora, mes, día de semana, timestamp (4 dims temprales)
[8-127]     → Estado de 128 cargadores (120 dims)
              30 valores por charger: SOC, potencia, disponibilidad, etc.
[128-390]   → Contextual features
              - Solar W/m²
              - Grid frequency
              - BESS SOC %
              - Demanda mall kW
              - Presencia EV por charger
```

### Action Space (129 dims)
```
[0]         → BESS power setpoint (continuous [0,1])
[1-128]     → Charger power setpoints (continuous [0,1])

Mapeo real: action * max_power → kW
            BESS:     [0, 2712] kW
            Chargers: [0, 3.5] kW cada uno
```

### Reward Function
```
Total Reward = 0.30 * CO2 reduction 
             + 0.20 * Solar self-consumption
             + 0.25 * Cost minimization
             + 0.15 * EV charge completion
             + 0.10 * Grid stability
```

## Monitoreo en Tiempo Real

### TensorBoard

Ver logs de entrenamiento en tiempo real:

```bash
# Ver todos los agents
tensorboard --logdir outputs/*/tensorboard

# Or específico
tensorboard --logdir outputs/sac_training/tensorboard
```

Abre http://localhost:6006 en el navegador

### Métricas Guardadas

Cada entrenamiento genera:
- `outputs/{agent}_training/{agent}_training_metrics.json` - Métricas finales
- `checkpoints/{agent}/` - Modelos checkpoint
- `outputs/{agent}_training/tensorboard/` - Logs para TensorBoard

Formato JSON:
```json
{
  "agent": "SAC",
  "total_timesteps": 100000,
  "total_duration_seconds": 3600,
  "episodes_trained": 11,
  "validation_rewards": [-38.52, -39.15, ...],
  "validation_mean_reward": -38.9,
  "validation_std_reward": 2.14
}
```

## Configuración del Environment

Editar `configs/default.yaml` para personalizar:

```yaml
# Parámetros del sistema
pv_nominal_power_kw: 4162
bess_capacity_kwh: 4520
bess_power_kw: 2712
n_chargers: 128
episode_time_steps: 8760

# Pesos de recompensa (multi-objetivo)
reward_weights:
  co2: 0.30
  solar: 0.20
  cost: 0.25
  ev_completion: 0.15
  grid_stability: 0.10
```

## Troubleshooting

### Error: Dataset no encontrado
```
[ERROR] data/interim/oe2/solar/pv_generation_timeseries.csv not found
```
**Solución:** Generar dataset primero
```bash
python build_citylearnv2_with_oe2.py
```

### Error: Modelo no encontrado durante evaluación
```
[ERROR] Modelo no encontrado: checkpoints/SAC/sac_final_model.zip
```
**Solución:** Entrenar primero con `train_sac_production.py`

### Entrenamiento muy lento
- Reducir `TOTAL_TIMESTEPS` en los scripts (ej: 50,000 en lugar de 100,000)
- Usar GPU: Asegurar que PyTorch detecta CUDA
  ```bash
  python -c "import torch; print(torch.cuda.is_available())"
  ```

### Memoria insuficiente
Editar configuración en scripts:
```python
'batch_size': 32,  # Reducir de 64
'buffer_size': 100000,  # Reducir de 1,000,000
'policy_kwargs': {
    'net_arch': [128, 128],  # Reducir de [256, 256]
}
```

## Comparativa de Agents

| Agent | Type      | Speed | Stabilidad | Multiobjetivo |
|-------|-----------|-------|------------|---------------|
| **SAC** | Off-policy| Medio | EXCELENTE  | EXCELENTE ✓   |
| **PPO** | On-policy | Rápido| Bueno      | Muy Bueno     |
| **A2C** | On-policy | Muy rápido | Regular | Bueno         |

**Recomendación:** SAC para máximo desempeño, PPO para balance speed/performance

## Próximos Pasos

1. **Validar en datos reales:**
   - Incorporar datos reales de carga de EVs
   - Incluir datos solares reales de PVGIS

2. **Mejorar reward function:**
   - Incluir datos CO₂ dinámicos del grid
   - Agregar constraints de estabilidad

3. **Deployment:**
   - API FastAPI para inferencia en tiempo real
   - Dashboard de monitoreo en Grafana
   - Docker container para producción

## Referencias

- **CityLearn v2.5.0:** https://github.com/intelligent-environments-lab/CityLearn
- **Stable Baselines3:** https://stable-baselines3.readthedocs.io
- **SAC Paper:** https://arxiv.org/abs/1801.01290
- **PPO Paper:** https://arxiv.org/abs/1707.06347
- **A2C:** https://arxiv.org/abs/1602.01783

## Autor

EV Charging Optimization Project - pvbesscar
Date: 2026-02-05
