# Manual de Ejecución — pvbesscar

**Versión:** 2026-05-31 | **Branch:** `smartcharger` | **Python:** 3.11 (estrictamente)

---

## Arquitectura y flujo de trabajo

El proyecto tiene dos fases encadenadas. Cada fase produce artefactos que consume la siguiente.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  FASE OE2 — Dimensionamiento (ejecutar una sola vez o si cambian datos) │
│                                                                          │
│  Fuentes reales de Iquitos 2024                                         │
│    solar_pvlib.py    → data/oe2/Generacionsolar/pv_generation_*.csv    │
│    chargers.py       → data/oe2/chargers/chargers_ev_ano_2024_v3.csv   │
│    bess.py           → data/oe2/bess/bess_ano_2024.csv                 │
│    [externo]         → data/oe2/demandamallkwh/demandamallhorakwh.csv  │
│         │                                                               │
│         ▼  scripts/generate_oe2_datasets.py                            │
│    data_loader.py (OE2DataLoader)                                       │
│         │   valida schema, raise OE2ValidationError si hay error        │
│         ▼                                                               │
│    data/iquitos_ev_mall/                                                │
│      solar_generation.csv      (8,760 h)                               │
│      bess_timeseries.csv        (8,760 h)                               │
│      chargers_timeseries.csv    (8,760 h)                               │
│      mall_demand.csv            (8,760 h)                               │
│      dataset_config_v7.json     ready_for_citylearn_v2=True            │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  FASE OE3 — Control RL (entrenamiento y análisis)                       │
│                                                                          │
│    src/citylearnv2/env_factory.py                                       │
│      create_iquitos_env_for_sb3()                                       │
│         → CityLearnEnv + IquitosEVChargingWrapper                      │
│         → obs_dim=18, action_dim=3                                      │
│         → reward CO2_DUAL_FOCUS v8.1 (7 componentes, suma=1.0)         │
│         │                                                               │
│         ▼  scripts/train/train_{a2c,ppo,sac}_citylearn.py              │
│    checkpoints/{A2C,PPO,SAC}_CityLearn/                                 │
│      {agent}_final.zip      ← política entrenada (SB3)                 │
│      vecnormalize.pkl       ← estadísticas de normalización             │
│         │                                                               │
│         ▼  scripts/reporting/run_all_oe3.py                            │
│    outputs/                                                             │
│      {agent}_training/trace_{agent}.csv   (50 ep × 8,760 h)           │
│      {agent}_training/{agent}_episodios_history.csv                    │
│      estadistica_oe3/reporte_estadistico_oe3.md                        │
│      docx/graficas/*.png   (31 figuras tesis)                          │
│    reports/oe3/                                                         │
│      agents_comparison_canonical.json   ← fuente canónica              │
│      AGENTES_RL_COMPARATIVA_CANONICA.md                                │
│      CO2_DIRECTO_INDIRECTO_TRACE_OE3.md                                │
│      CONTROL_OPERATIVO_BESS_EV_OE3.md                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

**Acción de control (3D):** `[bess_action ∈ [−1,+1],  ev_motos_frac ∈ [0,1],  ev_mototaxis_frac ∈ [0,1]]`
**Observación (18D):** tiempo(5) + solar(2) + BESS(1) + red(3) + EV(5) + tarifa(2)
**Sistema:** 4,162 kWp solar | 2,000 kWh / 400 kW BESS | 38 sockets | 0.4521 kg CO₂/kWh

---

## Modos de ejecución automática

Un solo comando corre el modo deseado:

```powershell
# Modo rápido: verifica datos + reportes OE3 (checkpoints ya entrenados)  ~2 min
python scripts/run_project.py --mode quick

# Solo análisis OE3 (estadísticas + figuras + tablas)                     ~1 min
python scripts/run_project.py --mode analysis

# Entrenar un agente específico
python scripts/run_project.py --mode train --agent A2C   # ~22 min CPU
python scripts/run_project.py --mode train --agent PPO   # ~23 min CPU
python scripts/run_project.py --mode train --agent SAC   # ~172 min CPU
python scripts/run_project.py --mode train --agent all   # ~4 h CPU

# Pipeline completo (OE2 + entrena 3 agentes + análisis OE3)              ~5 h CPU
python scripts/run_project.py --mode full

# Suite de 106 tests                                                       ~5 s
python scripts/run_project.py --mode test
```

---

## Módulo 0 — Preparación del entorno

### Requisitos previos
- Python **3.11** (3.12/3.13 rompen `stable_baselines3==2.7.1`)
- GPU CUDA opcional — acelera SAC ×8-10 (auto-detectado)

### Instalación inicial

```powershell
git clone https://github.com/Mac-Tapia/dise-opvbesscar.git
cd dise-opvbesscar
git checkout smartcharger

# Python 3.11 obligatorio
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows
# source .venv/bin/activate           # Linux/Mac

pip install -r requirements.txt
```

### Verificación del entorno

```powershell
python -m pytest tests/ -q
# Resultado esperado: 106 passed in ~1.3s
```

---

## Módulo 1 — Datos OE2 (dimensionamiento)

### ¿Cuándo ejecutar?
Solo si los datos fuente de Iquitos cambian. Los archivos generados ya están en el repo.

### Verificar que los datos están correctos

```powershell
python scripts/verification/verify_citylearn_data.py
```

**Salida esperada:**
```
OK  Solar PV:    8760 filas | 5,819,332 kWh/año
OK  Cargadores:  8760 filas | 821 cols (38 sockets × varias métricas)
OK  BESS:        8760 filas | SOC max=1.0, min=0.20
OK  Mall:        8760 filas | 12,368,653 kWh/año
```

### Regenerar dataset si cambian los datos fuente

```powershell
# Pipeline completo (orden: solar → cargadores → BESS → data_loader)
python scripts/generate_oe2_datasets.py

# Solo data_loader (si los CSV de OE2 ya existen)
python scripts/generate_oe2_datasets.py --loader-only

# Saltar cálculo solar (usar pv_generation_citylearn2024.csv existente)
python scripts/generate_oe2_datasets.py --skip-solar
```

### Módulos OE2 internos (no llamar directamente salvo debugging)

| Script | Función |
|---|---|
| `src/dimensionamiento/oe2/solar_pvlib.py` | Genera 8,760 h de generación PV (PVWatts + bifacial) |
| `src/dimensionamiento/oe2/disenocargadoresev/chargers.py` | Simula llegada estocástica de 270 motos + 39 mototaxis/día en 38 sockets |
| `src/dimensionamiento/oe2/bess.py` | Calcula SOC BESS horario (usa solar + demanda real) |
| `src/dataset_builder_citylearn/data_loader.py` | OE2DataLoader: valida schema y escribe `data/iquitos_ev_mall/` |

---

## Módulo 2 — Entorno de simulación CityLearn v2

El entorno combina los 4 CSV de OE2 con el wrapper de carga EV.

### Componentes del entorno

```
src/citylearnv2/env_factory.py
  create_iquitos_env()            ← uso directo Python
  create_iquitos_env_for_sb3()    ← uso con stable-baselines3 (VecEnv)

src/citylearnv2/ev_charging_wrapper.py
  IquitosEVChargingWrapper        ← mapea acción 3D a 38 sockets
  Reward CO2_DUAL_FOCUS v8.1 (suma = 1.00):
    W_DIRECT_CO2   = 0.20  (OE3-1 CO₂ directa ICE→EV)
    W_INDIRECT_CO2 = 0.30  (OE3-2 CO₂ indirecta grid import)
    W_EV_COMPLETE  = 0.35  (OE3-3 carga EV satisfecha ← mayor prioridad)
    W_BESS_SOLAR   = 0.07  (BESS carga con solar, no diesel)
    W_SOLAR        = 0.04  (autoconsumo PV)
    W_GRID_STABLE  = 0.02  (suavizado rampas)
    W_COST         = 0.02  (tarifa HP OSINERGMIN)
```

### Verificar entorno

```powershell
# Smoke test con agente aleatorio (1 episodio)
python examples/single_building/run.py --random-agent

# Tests de integración del entorno (72 tests)
python -m pytest tests/integration/ -v
```

---

## Módulo 3 — Entrenamiento de agentes RL

### Arquitectura de los agentes

| Agente | Algoritmo | Tipo | Actor/Critic | Parámetros clave |
|---|---|---|---|---|
| A2C | Advantage Actor-Critic | On-policy | Compartido | `n_steps=2048`, `lr=7e-4` |
| PPO | Proximal Policy Optimization | On-policy | Compartido | `n_steps=2048`, `clip=0.2`, `lr=3e-4` |
| SAC | Soft Actor-Critic | Off-policy | Separado | `buffer=100k`, `target_entropy=-3.0`, `lr=1e-4` |

**Diferencia clave:** A2C y PPO son on-policy (aprenden del episodio actual).
SAC es off-policy (reutiliza experiencias pasadas en replay buffer).

### Ejecución por agente

```powershell
# Baseline sin RL (referencia F1)
python scripts/train/run_baseline.py

# A2C — agente seleccionado (on-policy, 22 min CPU)
python scripts/train/train_a2c_citylearn.py

# PPO — segundo mejor (on-policy, 23 min CPU)
python scripts/train/train_ppo_citylearn.py

# SAC — off-policy, buffer de replay, 172 min CPU
# Requiere VecNormalize para convergencia estable (v8.2 reentrenado 2026-05-30)
python scripts/train/train_sac_citylearn.py
```

### Checkpoints y reanudación automática

```
checkpoints/{AGENT}_CityLearn/
  {agent}_XXXXX_steps.zip      ← checkpoint cada episodio (auto-guardado)
  {agent}_XXXXX_steps.pkl      ← VecNormalize stats del paso X
  {agent}_final.zip            ← política final ep50
  vecnormalize.pkl             ← estadísticas finales de normalización
```

Si el entrenamiento se interrumpe, **reanuda automáticamente** desde el checkpoint más reciente.
El paso acumulado continúa (`reset_num_timesteps=False`).

### Verificar consistencia de los tres agentes

```powershell
python scripts/train/test_consistency_sac_ppo_a2c.py
```

---

## Módulo 4 — Análisis OE3

### Cadena completa (un comando)

```powershell
python scripts/reporting/run_all_oe3.py
```

Ejecuta 5 pasos en orden y verifica 11 archivos de salida:

| Paso | Script | Salida |
|---|---|---|
| 1 | `analizar_co2_trace_oe3.py` | `reports/oe3/CO2_DIRECTO_INDIRECTO_TRACE_OE3.md` |
| 2 | `demostracion_estadistica_oe3.py` | `outputs/estadistica_oe3/reporte_estadistico_oe3.md` + PNG |
| 3 | `control_operativo_bess_ev_oe3.py` | `reports/oe3/CONTROL_OPERATIVO_BESS_EV_OE3.md` + PNG |
| 4 | `comparativa_agentes_co2_trace.py` | 6 PNGs de convergencia y comparativa |
| 5 | `generar_tablas_oe3.py` | 2 tablas PNG canónicas |

### Scripts individuales

```powershell
# CO₂ directo + indirecto desde traces (50 eps × 8,760 h × 3 agentes)
python scripts/analysis/analizar_co2_trace_oe3.py

# Pruebas estadísticas inferenciales completas
# Mann-Whitney U (independiente) + Wilcoxon (pareado) + Kruskal-Wallis + Dunn Bonferroni
# Cohen d + Cliff delta + Bootstrap IC 95% (B=10,000)
python scripts/analysis/demostracion_estadistica_oe3.py

# Patrón BESS/EV/pico por hora (SOC, grid import, carga EV por h00-h23)
python scripts/analysis/control_operativo_bess_ev_oe3.py

# Figuras comparativas de convergencia reward y CO₂
python scripts/reporting/comparativa_agentes_co2_trace.py

# Tablas PNG canónicas (para Word/presentación)
python scripts/reporting/generar_tablas_oe3.py
```

### Resultados canónicos

```
reports/oe3/agents_comparison_canonical.json   ← fuente única de verdad
  selected_agent: "A2C"
  ranking: ["A2C", "PPO", "SAC"]
  A2C: CO₂ evitado 122,980,987 kg (50 eps) | EV 4,307,304 equiv. | 9/9 criterios
  PPO: F2 mínimo puntual 3,657,484 kg/año (lectura complementaria)
  SAC: inferior en todos los criterios (p < 10⁻⁸, Mann-Whitney)
```

---

## Módulo 5 — Inferencia con agente entrenado

Carga el checkpoint A2C y ejecuta un episodio completo (8,760 h = 1 año simulado).

```python
from pathlib import Path
import pickle
from stable_baselines3 import A2C
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from src.citylearnv2.env_factory import create_iquitos_env_for_sb3

ROOT = Path(".")

# 1. Crear entorno
raw_env = create_iquitos_env_for_sb3()
vec_env = DummyVecEnv([lambda: raw_env])

# 2. Cargar VecNormalize (obligatorio — sin esto las observaciones no están escaladas)
vec_env = VecNormalize.load(
    ROOT / "checkpoints" / "A2C_CityLearn" / "vecnormalize.pkl",
    vec_env,
)
vec_env.training = False   # modo evaluación: no actualizar media/std

# 3. Cargar política
model = A2C.load(ROOT / "checkpoints" / "A2C_CityLearn" / "a2c_final.zip", env=vec_env)

# 4. Ejecutar episodio
obs = vec_env.reset()
total_reward, total_co2_avoided, step = 0.0, 0.0, 0
while True:
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, done, info = vec_env.step(action)
    total_reward += float(reward[0])
    step += 1
    if done[0]:
        break

print(f"Episodio completado: {step} pasos | Reward total: {total_reward:.1f}")
```

---

## Módulo 6 — Tests de verificación

```powershell
# Suite completa (106 tests) — OE2 + integración
python -m pytest tests/ -v

# Solo OE2 (datos, schema, cargadores)
python -m pytest tests/oe2/ -v

# Solo integración (entorno Gymnasium, reward, energy balance)
python -m pytest tests/integration/ -v

# Test específico más crítico (38 sockets OE2)
python -m pytest tests/oe2/test_chargers_config.py::test_iquitos_charger_set_matches_oe2_design -v
```

---

## Módulo 7 — Control de versiones y actualización

### Después de reentrenar un agente

```powershell
# 1. Regenerar cadena OE3
python scripts/reporting/run_all_oe3.py

# 2. Stagear archivos relevantes
git add reports/oe3/ outputs/estadistica_oe3/
git add checkpoints/A2C_CityLearn/vecnormalize.pkl   # si cambió

# 3. Commit
git commit -m "feat(oe3): retrain A2C ep50 — CO2 avoided 2,459,620 kg/ep"
git push origin smartcharger
```

### Archivos que siempre deben estar versionados

```
reports/oe3/agents_comparison_canonical.json   ← fuente canónica
reports/oe3/agents_comparison_canonical.csv
reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md
reports/oe3/CO2_DIRECTO_INDIRECTO_TRACE_OE3.md
reports/oe3/CONTROL_OPERATIVO_BESS_EV_OE3.md
reports/metodologia/METODOLOGIA_INVESTIGACION_OE3.md
outputs/estadistica_oe3/reporte_estadistico_oe3.md
outputs/estadistica_oe3/tabla_completa_estadistica_oe3.csv
checkpoints/{A2C,PPO,SAC}_CityLearn/vecnormalize.pkl
```

### Archivos que NO se versionan (grandes, regenerables)

```
outputs/*_training/trace_*.csv        (trazas de 438k filas)
outputs/*_training/timeseries_*.csv
checkpoints/**/*.zip                   (modelos SB3, hasta 14 MB cada uno)
checkpoints/**/*.pkl                   (excepto vecnormalize.pkl final)
```

---

## Referencia rápida

| Tarea | Comando |
|---|---|
| Verificar todo el proyecto | `python scripts/run_project.py --mode quick` |
| Solo reportes OE3 | `python scripts/run_project.py --mode analysis` |
| Entrenar A2C | `python scripts/run_project.py --mode train --agent A2C` |
| Pipeline completo | `python scripts/run_project.py --mode full` |
| Tests | `python scripts/run_project.py --mode test` |
| Verificar datos OE2 | `python scripts/verification/verify_citylearn_data.py` |
| Smoke test entorno | `python examples/single_building/run.py --random-agent` |
| Consultar agente canónico | `python -c "import json; d=json.load(open('reports/oe3/agents_comparison_canonical.json')); print(d['metadata']['selected_agent'])"` |
