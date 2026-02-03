# 🚀 Pipelines Individuales - Guía de Uso

## Estructura de Scripts

```
scripts/
├── run_baseline1_solar.py      # Baseline CON solar (4,050 kWp)
├── run_baseline2_nosolar.py    # Baseline SIN solar (0 kWp)
├── run_agent_sac.py            # Agente SAC (Soft Actor-Critic)
├── run_agent_ppo.py            # Agente PPO (Proximal Policy Opt.)
├── run_agent_a2c.py            # Agente A2C (Advantage Actor-Critic)
├── compare_all_results.py      # Tabla comparativa final
└── run_all_pipelines.py        # Ejecuta todos en secuencia
```

## Uso Individual

### 1️⃣ Baseline 1: Con Solar (4,050 kWp)
```bash
python -m scripts.run_baseline1_solar
```
- **Salida**: `outputs/baselines/baseline1_with_solar/`
- **CO₂ esperado**: ~190,000 kg/año (carbono-negativo)

### 2️⃣ Baseline 2: Sin Solar (0 kWp)
```bash
python -m scripts.run_baseline2_nosolar
```
- **Salida**: `outputs/baselines/baseline2_without_solar/`
- **CO₂ esperado**: ~640,000 kg/año

### 3️⃣ Agente SAC
```bash
# Evaluación (usa checkpoint existente)
python -m scripts.run_agent_sac

# Entrenar desde cero
python -m scripts.run_agent_sac --train --episodes 5

# Continuar entrenamiento
python -m scripts.run_agent_sac --resume --episodes 3
```
- **Checkpoint**: `checkpoints/sac/sac_final.zip`
- **Salida**: `outputs/agents/sac/`

### 4️⃣ Agente PPO
```bash
# Evaluación (usa checkpoint existente)
python -m scripts.run_agent_ppo

# Entrenar desde cero
python -m scripts.run_agent_ppo --train --timesteps 100000

# Continuar entrenamiento
python -m scripts.run_agent_ppo --resume --timesteps 50000
```
- **Checkpoint**: `checkpoints/ppo/ppo_final.zip`
- **Salida**: `outputs/agents/ppo/`

### 5️⃣ Agente A2C
```bash
# Evaluación (usa checkpoint existente)
python -m scripts.run_agent_a2c

# Entrenar desde cero
python -m scripts.run_agent_a2c --train --timesteps 100000

# Continuar entrenamiento
python -m scripts.run_agent_a2c --resume --timesteps 50000
```
- **Checkpoint**: `checkpoints/a2c/a2c_final.zip`
- **Salida**: `outputs/agents/a2c/`

### 6️⃣ Tabla Comparativa
```bash
# Formato tabla (consola)
python -m scripts.compare_all_results

# Formato Markdown
python -m scripts.compare_all_results --format markdown

# Formato CSV
python -m scripts.compare_all_results --format csv

# Formato JSON
python -m scripts.compare_all_results --format json
```
- **Salida**: `outputs/comparison_summary.json`

## Pipeline Completo

### Ejecutar todo
```bash
python -m scripts.run_all_pipelines
```

### Solo baselines
```bash
python -m scripts.run_all_pipelines --skip-agents
```

### Solo agentes (evaluación)
```bash
python -m scripts.run_all_pipelines --skip-baselines
```

## Estructura de Resultados

```
outputs/
├── baselines/
│   ├── baseline1_with_solar/
│   │   ├── baseline1_summary.json
│   │   ├── result_uncontrolled.json
│   │   └── timeseries_uncontrolled.csv
│   └── baseline2_without_solar/
│       ├── baseline2_summary.json
│       ├── result_uncontrolled.json
│       └── timeseries_uncontrolled.csv
├── agents/
│   ├── sac/
│   │   ├── sac_summary.json
│   │   ├── result_sac.json
│   │   └── timeseries_sac.csv
│   ├── ppo/
│   │   ├── ppo_summary.json
│   │   ├── result_ppo.json
│   │   └── timeseries_ppo.csv
│   └── a2c/
│       ├── a2c_summary.json
│       ├── result_a2c.json
│       └── timeseries_a2c.csv
└── comparison_summary.json
```

## Métricas CO₂ (3 Componentes)

| Métrica | Descripción |
|---------|-------------|
| `co2_emitido_grid_kg` | Emisiones por importación de grid (× 0.4521 kg/kWh) |
| `co2_reduccion_indirecta_kg` | Reducción por solar + BESS (evita importar) |
| `co2_reduccion_directa_kg` | Reducción por EVs (evita gasolina, × 2.146 kg/kWh) |
| `co2_neto_kg` | Emitido - Ind. - Dir. (< 0 = carbono-negativo) |

## Secuencia Recomendada

```bash
# 1. Verificar dataset existe
python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# 2. Ejecutar baselines
python -m scripts.run_baseline1_solar
python -m scripts.run_baseline2_nosolar

# 3. Entrenar agentes (si no hay checkpoints)
python -m scripts.run_agent_sac --train --episodes 3
python -m scripts.run_agent_ppo --train --timesteps 100000
python -m scripts.run_agent_a2c --train --timesteps 100000

# 4. Evaluar agentes
python -m scripts.run_agent_sac
python -m scripts.run_agent_ppo
python -m scripts.run_agent_a2c

# 5. Generar tabla comparativa
python -m scripts.compare_all_results
```

## Notas

- Todos los scripts usan `configs/default.yaml` por defecto
- Los checkpoints se guardan en `checkpoints/{sac,ppo,a2c}/`
- Los tiempos de ejecución son:
  - Baselines: ~10 segundos cada uno
  - Evaluación agentes: ~30-60 segundos cada uno
  - Entrenamiento: variable según parámetros
