# 🚀 FLUJO DE TRABAJO: ENTRENAMIENTO COMPLETO OE3 (2026-02-01)

**Estado:** ✅ Limpio, Optimizado y Documentado  
**Última actualización:** 2026-02-01  
**Responsable:** OE3 Optimization Module  

---

## 📋 FLUJO PRINCIPAL: Dataset → Entrenamiento Completo

```
┌─────────────────────────────────────────────────────────────────┐
│                    PIPELINE DE ENTRENAMIENTO                    │
└─────────────────────────────────────────────────────────────────┘

PASO 1: VERIFICACIÓN DEL AMBIENTE
  └─→ scripts/_common.py → load_config() + load_paths()
      Valida Python 3.11, carga YAML config, establece paths

PASO 2: CONSTRUCCIÓN DEL DATASET
  └─→ scripts/run_oe3_build_dataset.py → build_citylearn_dataset()
      ├─ Lee datos OE2 (solar, BESS, chargers, demanda)
      ├─ Descarga template CityLearn
      ├─ Genera 8,760 timesteps (1 año horario)
      ├─ Crea 128 CSVs individuales de chargers
      └─ Output: processed/citylearn/dataset_name/schema.json

PASO 3: ENTRENAMIENTO DE AGENTES (Opción A: SECUENCIAL)
  └─→ scripts/run_training_sequence.py
      ├─ SAC   (10 episodios) → checkpoint cada 1000 steps
      ├─ PPO   (100K timesteps) → checkpoint cada 1000 steps
      ├─ A2C   (100K timesteps) → checkpoint cada 1000 steps
      └─ Baseline (sin control, 1 episodio)

PASO 4: ENTRENAMIENTO DE AGENTES (Opción B: INDIVIDUAL)
  ├─→ scripts/run_sac_only.py
  ├─→ scripts/run_ppo_only.py
  ├─→ scripts/run_a2c_only.py
  └─→ scripts/run_uncontrolled_baseline.py

PASO 5: ANÁLISIS DE RESULTADOS
  └─→ scripts/run_oe3_co2_table.py
      ├─ Tabla resumen (CO₂, costo, solar)
      ├─ Reducción porcentual vs baseline
      └─ Reporte final: outputs/oe3_simulations/results_summary.csv
```

---

## 🔧 COMANDO RÁPIDO PARA LANZAR TODO

### Opción 1: Pipeline Completo (Recomendado)
```bash
cd d:\diseñopvbesscar
python -m scripts.run_training_sequence \
    --config configs/default.yaml \
    --reset-checkpoints false
```

**Tiempo estimado:** 30-45 minutos (GPU RTX 4060)

### Opción 2: Dataset + Baseline + Un Agente
```bash
# Construir dataset
python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# Baseline (sin control)
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml

# SAC solamente
python -m scripts.run_sac_only --config configs/default.yaml
```

### Opción 3: Entrenar en Secuencia (Mejor para Debug)
```bash
python -m scripts.run_training_sequence \
    --config configs/default.yaml \
    --agents sac ppo a2c \
    --reset-checkpoints false
```

---

## 📁 ARCHIVOS ESENCIALES EN scripts/

### 🎯 Entrada Principal (3 scripts de arranque)

| Script | Propósito | Uso |
|--------|-----------|-----|
| `_common.py` | Carga config y paths (importado por otros) | `from scripts._common import load_all` |
| `run_oe3_build_dataset.py` | Construye dataset CityLearn | `python -m scripts.run_oe3_build_dataset` |
| `run_training_sequence.py` | Entrena SAC→PPO→A2C en secuencia | `python -m scripts.run_training_sequence` |

### 🤖 Entrenamientos Individuales (4 scripts)

| Script | Agente | Uso |
|--------|--------|-----|
| `run_sac_only.py` | SAC (off-policy) | `python -m scripts.run_sac_only` |
| `run_ppo_only.py` | PPO (on-policy) | `python -m scripts.run_ppo_only` |
| `run_a2c_only.py` | A2C (on-policy, simple) | `python -m scripts.run_a2c_only` |
| `run_uncontrolled_baseline.py` | Baseline (sin control) | `python -m scripts.run_uncontrolled_baseline` |

### 📊 Análisis de Resultados (1 script)

| Script | Propósito |
|--------|-----------|
| `run_oe3_co2_table.py` | Tabla comparativa de CO₂ entre agentes |

---

## 🎯 ESTRUCTURA DE DIRECTORIOS

```
d:\diseñopvbesscar/
├── scripts/                          ← 🔴 ÚNICO LUGAR PARA SCRIPTS DE EJECUCIÓN
│   ├── _common.py                    ← Configuración centralizada
│   ├── run_oe3_build_dataset.py     ← Construcción dataset
│   ├── run_training_sequence.py     ← Pipeline completo
│   ├── run_sac_only.py              ← Entrenamientos individuales
│   ├── run_ppo_only.py
│   ├── run_a2c_only.py
│   ├── run_uncontrolled_baseline.py
│   ├── run_oe3_co2_table.py         ← Análisis
│   └── ... (otros scripts auxiliares)
│
├── src/iquitos_citylearn/           ← Código fuente
│   ├── __init__.py
│   ├── config.py                    ← Centralizado
│   ├── oe3/                         ← 🎯 MÓDULO PRINCIPAL
│   │   ├── __init__.py              ← 50+ exports (sincronizado)
│   │   ├── simulate.py              ← Orquestador principal
│   │   ├── agents/                  ← 6 agentes (limpios)
│   │   ├── rewards.py               ← Multi-objetivo
│   │   ├── dataset_builder.py       ← CityLearn schema
│   │   └── ... (15 más módulos)
│   └── oe2/                         ← Datos OE2
│
├── configs/
│   └── default.yaml                 ← Configuración principal
│
├── data/
│   ├── raw/
│   ├── interim/oe2/                 ← Inputs OE2
│   └── processed/citylearn/         ← Dataset construido
│
├── outputs/
│   └── oe3_simulations/             ← Resultados
│
├── checkpoints/                      ← Checkpoints de agentes
│   ├── sac/
│   ├── ppo/
│   └── a2c/
│
├── README.md                         ← 📖 Documentación general
├── INSTALLATION_GUIDE.md             ← 🛠️ Instalación
├── QUICKSTART.md                     ← ⚡ Inicio rápido
└── requirements.txt                  ← Dependencias
```

---

## ✅ CHECKLIST DE VERIFICACIÓN PRE-TRAINING

Antes de lanzar el entrenamiento:

```bash
# 1. Verificar Python 3.11
python --version  # Debe ser 3.11.x

# 2. Verificar environment
cd d:\diseñopvbesscar
pip list | findstr citylearn

# 3. Verificar OE2 data
Test-Path d:\diseñopvbesscar\data\interim\oe2\solar\pv_generation_timeseries.csv
# Debe mostrar True + exactamente 8760 filas

# 4. Verificar imports del sistema
python -c "from src.iquitos_citylearn.oe3 import simulate, make_sac, make_ppo, make_a2c; print('✅ All imports OK')"

# 5. Verificar GPU (opcional)
python -c "import torch; print(f'GPU: {torch.cuda.is_available()}')"
```

---

## 🎯 OPCIONES DE CONFIGURACIÓN

Editar `configs/default.yaml` para:

```yaml
# RL Agent Training
oe3:
  training:
    sac:
      episodes: 10              # Episodios de entrenamiento
      batch_size: 512           # Batch size
      learning_rate: 5e-5       # Tasa de aprendizaje
    ppo:
      timesteps: 100000         # Total timesteps
      n_steps: 1024             # Steps por update
      batch_size: 128
    a2c:
      timesteps: 100000
      n_steps: 256
      learning_rate: 3e-4

# Reward Configuration
  rewards:
    co2_weight: 0.75            # CO₂ minimization (primary)
    solar_weight: 0.20          # Solar self-consumption
    cost_weight: 0.05           # Cost minimization

# Grid Constants
  grid:
    carbon_intensity_kg_per_kwh: 0.4521  # Iquitos factor
    tariff_usd_per_kwh: 0.20
```

---

## 📊 SALIDAS ESPERADAS

Después de ejecutar el pipeline:

```
outputs/oe3_simulations/
├── timeseries_sac.csv          ← Datos horarios (SAC)
├── timeseries_ppo.csv          ← Datos horarios (PPO)
├── timeseries_a2c.csv          ← Datos horarios (A2C)
├── timeseries_uncontrolled.csv ← Datos horarios (Baseline)
├── result_sac.json             ← Métricas finales
├── result_ppo.json
├── result_a2c.json
└── result_uncontrolled.json

Ejemplo de result_*.json:
{
  "agent": "sac",
  "carbon_kg": 7200000,          ← CO₂ total (kg/año)
  "grid_import_kwh": 350000,     ← Importación grid
  "pv_generation_kwh": 3300000,  ← Generación solar
  "solar_direct_kwh": 2100000,   ← Solar directo a cargas
  "reward_total_mean": 0.65      ← Recompensa promedio
}
```

---

## 🔍 MONITOREO EN VIVO (Opcional)

Para ver progreso en tiempo real:

```bash
# Terminal 1: Lanzar entrenamiento
python -m scripts.run_training_sequence --config configs/default.yaml

# Terminal 2: Monitorear GPU (Windows)
nvidia-smi -l 1  # Actualiza cada segundo

# Terminal 3: Ver checkpoints
watch -n 5 "ls -lh checkpoints/sac/"
```

---

## 🚨 TROUBLESHOOTING

| Problema | Solución |
|----------|----------|
| `ImportError: No module named src` | `cd d:\diseñopvbesscar` y verificar PYTHONPATH |
| `ModuleNotFoundError: 'citylearn'` | `pip install citylearn>=2.5.0` |
| `Error: Solar timeseries must be 8760 rows` | Verificar `pv_generation_timeseries.csv` tiene exactamente 8760 filas |
| `GPU out of memory` | Reducir `batch_size` en config.yaml (512→256 o 128) |
| `Checkpoint not found` | `--reset-checkpoints true` para empezar desde cero |

---

## 📞 REFERENCIA RÁPIDA

```bash
# Build dataset
python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# Train all (SAC + PPO + A2C + Baseline)
python -m scripts.run_training_sequence --config configs/default.yaml

# Train SAC only
python -m scripts.run_sac_only --config configs/default.yaml --sac-episodes 10

# Train PPO only
python -m scripts.run_ppo_only --config configs/default.yaml --ppo-timesteps 100000

# Train A2C only
python -m scripts.run_a2c_only --config configs/default.yaml --a2c-timesteps 100000

# Generate results table
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

---

## ✨ STATUS

✅ **Pipeline limpio y funcional**  
✅ **Flujo de trabajo documentado**  
✅ **Todos los scripts necesarios en place**  
✅ **Configuración centralizada**  
✅ **Ready para production training**  

**Última actualización:** 2026-02-01
