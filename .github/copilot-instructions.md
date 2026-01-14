# Instrucciones Copilot - Infraestructura EV Iquitos CityLearn

## Resumen del Proyecto

Pipeline científico para diseño de infraestructura de carga inteligente de motos y mototaxis eléctricas en Iquitos, Perú (lat=-3.75, lon=-73.25, tz=America/Lima). Objetivo: Reducir emisiones de CO₂ mediante energía solar, BESS y agentes RL.

**Tres Objetivos Específicos (OE)**:

- **OE1**: Ubicación estratégica - Determinar viabilidad técnica del sitio Mall de Iquitos (20,637 m² techados, 60m de subestación Santa Rosa, 900 motos + 130 mototaxis pico a las 19:00h)
- **OE2**: Dimensionamiento técnico - Sistema PV solar (4162 kWp DC), BESS (2000 kWh), 128 cargadores distribuidos en 2 playas (112 motos @ 2kW + 16 mototaxis @ 3kW)
- **OE3**: Agente inteligente - Evaluar agentes RL (SAC, PPO, A2C) con CityLearn para maximizar eficiencia operativa y reducción cuantificable de CO₂

**Contexto Iquitos**: Red eléctrica aislada térmica (290k tCO₂/año, 0.4521 kg/kWh). Parque vehicular: 61k mototaxis + 70.5k motos generan 95% de 270k tCO₂/año del transporte.

## Arquitectura y Flujo de Datos

### Pipeline de Ejecución

Secuencia orquestada por [run_pipeline.py](../scripts/run_pipeline.py) ejecutando submódulos con `subprocess.check_call`:

```
run_pipeline.py (usa sys.executable para garantizar Python 3.11)
    ├── run_oe2_solar.py       → Perfil PV anual (pvlib + PVGIS TMY) → data/interim/oe2/solar/
    ├── run_oe2_chargers.py    → 128 perfiles individuales de cargadores → data/interim/oe2/chargers/
    ├── run_oe1_location.py    → Validación del sitio Mall de Iquitos → reports/oe1/
    ├── run_oe2_bess.py        → BESS 2000kWh/1200kW modo fijo → data/interim/oe2/bess/
    ├── run_oe3_build_dataset.py → Consolidación → dataset CityLearn (2 schemas)
    ├── run_oe3_simulate.py    → Entrenamiento RL + evaluación multi-agente
    └── run_oe3_co2_table.py   → Tablas comparativas (anual + 20 años VPN)
```

**Dependencias de etapas**: OE2 (solar/chargers/bess) debe completarse antes de OE3 (build_dataset). No hay dependencias entre módulos OE2.

### Flujo de Artefactos y Transformaciones

```
OE2 Sizing (dimensionamiento técnico)
│
├─ data/interim/oe2/solar/
│   ├─ solar_results.json (SolarSizingOutput: 4162kWp, 3972 MWh/año)
│   └─ pv_profile_hourly.csv (8760 timesteps, pvlib clear-sky)
│
├─ data/interim/oe2/chargers/
│   ├─ chargers_results.json (ChargersSizingOutput: 128 units, 272kW total)
│   └─ charger_<tipo>_<id>.csv (perfiles individuales, 112 MOTO + 16 MOTOTAXI)
│
├─ data/interim/oe2/bess/
│   ├─ bess_results.json (BessSizingOutput: 2000kWh, DoD 0.8, C-rate 0.6)
│   └─ bess_soc_timeseries.csv (SOC horario, modo fijo sin RL)
│
└─▶ data/interim/oe2/citylearn/ (consolidación pre-CityLearn)
    └─▶ data/processed/citylearn/iquitos_ev_mall/
        ├─ schema_grid_only.json    (baseline: 2 buildings sin PV/BESS)
        ├─ schema_pv_bess.json      (sistema completo: 2 buildings con PV+BESS)
        ├─ carbon_intensity.csv     (0.4521 kg/kWh constante)
        └─ charger_*.csv (128 archivos)
            └─▶ outputs/oe3/simulations/
                ├─ <agent>_grid_only.json
                ├─ <agent>_pv_bess.json
                └─▶ analyses/oe3/
                    ├─ co2_comparison_table.{csv,md}
                    ├─ agent_episode_summary.{csv,md}
                    └─ training/<AGENT>_training_metrics.csv
```

### Por qué 2 Edificios Separados

Arquitectura de dataset CityLearn representa **2 playas de estacionamiento físicamente distintas** en Mall de Iquitos:

- **Playa_Motos**: 112 cargadores (2 kW c/u), 3641.8 kWp PV, 1750 kWh BESS
- **Playa_Mototaxis**: 16 cargadores (3 kW c/u), 520.2 kWp PV, 250 kWh BESS

**Distribución 87.5% / 12.5%** basada en conteo de campo (900 motos vs 130 mototaxis @ 19:00h).

**Ventajas de separación**:
1. Análisis granular por tipo de vehículo (diferentes patrones de uso/potencia)
2. Comparación de esquemas de control descentralizado (RL independiente por playa)
3. Escalabilidad: Agregar nuevos edificios sin reestructurar schemas
4. Realismo: Refleja layout físico del Mall (áreas de estacionamiento separadas)

## Patrones Críticos

### Configuración y Entrada de Scripts

```python
# Todos los scripts usan _common.py (requiere Python 3.11 en tiempo de ejecución)
from scripts._common import load_all
cfg, rp = load_all(args.config)  # cfg dict, rp = RuntimePaths dataclass

# Acceso anidado: cfg["oe2"]["solar"]["target_dc_kw"], cfg["oe3"]["evaluation"]["agents"]
# Variables de entorno: GRID_CARBON_INTENSITY_KG_PER_KWH, TARIFF_USD_PER_KWH (via .env)
```

### Dataclasses de Salida

Cada módulo OE2/OE3 retorna un **dataclass frozen** serializado a JSON:

- `SolarSizingOutput` → `data/interim/oe2/solar/solar_results.json`
- `BessSizingOutput` → `data/interim/oe2/bess/bess_results.json`
- `SimulationResult` → `outputs/oe3/simulations/<agent>_*.json`

Al agregar nuevas salidas, seguir este patrón: definir `@dataclass(frozen=True)`, serializar via `asdict()`, deserializar al cargar.

## Agentes RL (OE3)

Ubicados en `src/iquitos_citylearn/oe3/agents/`. Todos implementan `predict(obs, deterministic) -> action`.

| Agente | Factory | Entrenamiento | Propósito |
|--------|---------|---------------|-----------|
| `SAC` | `make_sac(env, cfg)` | `learn(episodes)` | Soft Actor-Critic (principal) |
| `PPO` | `make_ppo(env, cfg)` | `learn(timesteps)` | Proximal Policy Opt. (stable-baselines3) |
| `A2C` | `make_a2c(env, cfg)` | `learn(timesteps)` | Advantage Actor-Critic (stable-baselines3) |
| `Uncontrolled` | `UncontrolledChargingAgent()` | Ninguno | Baseline: carga máxima siempre |
| `NoControl` | `make_no_control()` | Ninguno | Baseline: acción cero |

### Recompensas Multiobjetivo (`oe3/rewards.py`)

La clase `MultiObjectiveReward` calcula recompensa ponderada de 5 objetivos (normalizados a suma=1.0):

```yaml
# cfg["oe3"]["evaluation"]["sac"]["multi_objective_weights"]
multi_objective_weights:
  co2: 0.50      # Minimizar emisiones (Iquitos: 0.4521 kg/kWh red térmica)
  cost: 0.15     # Minimizar costo eléctrico ($0.20/kWh)
  solar: 0.20    # Maximizar autoconsumo solar
  ev: 0.10       # Satisfacción de carga EV
  grid: 0.05     # Estabilidad de red (recorte de picos)
```

### Agregar Nuevos Agentes

1. Crear `src/iquitos_citylearn/oe3/agents/mi_agente.py` con método `predict(obs, deterministic)`
2. Exportar en `agents/__init__.py`
3. Agregar a lista `cfg["oe3"]["evaluation"]["agents"]`
4. Manejar instanciación en `simulate.py` (ver patrón `_create_agent()`)

## Dataset CityLearn

`dataset_builder.py` crea datasets compatibles con CityLearn con **2 edificios separados**:

1. Descarga plantilla: `citylearn_challenge_2022_phase_all_plus_evs`
2. Crea 2 edificios representando áreas de estacionamiento separadas ("playas"):
   - **Playa_Motos**: 112 cargadores (2 kW c/u), 3641.8 kWp PV, 1750 kWh BESS
   - **Playa_Mototaxis**: 16 cargadores (3 kW c/u), 520.2 kWp PV, 250 kWh BESS
3. Sobrescribe CSVs con artefactos OE2 (series temporales PV, intensidad de carbono)
4. Genera 128 CSVs de simulación de cargadores (112 MOTO + 16 MOTOTAXI)
5. Genera dos schemas para comparación:
   - `schema_grid_only.json` → Sin PV/BESS (baseline solo red)
   - `schema_pv_bess.json` → Sistema OE2 completo con ambos edificios

### Distribución de Infraestructura (87.5% / 12.5%)

| Componente | Playa_Motos | Playa_Mototaxis | Total |
|------------|-------------|-----------------|-------|
| Cargadores | 112 (2 kW) | 16 (3 kW) | 128 |
| Potencia | 224 kW | 48 kW | 272 kW |
| PV | 3641.8 kWp | 520.2 kWp | 4162 kWp |
| BESS | 1750 kWh | 250 kWh | 2000 kWh |

## Comandos de Desarrollo

```bash
# Activar venv (Python 3.11 requerido - validado en tiempo de ejecución)
.venv\Scripts\activate  # Windows

# Pipeline completo (secuencial, ~2-6h dependiendo de episodios RL)
python -m scripts.run_pipeline --config configs/default.yaml

# Etapas individuales (para debugging o re-ejecutar desde punto específico)
python -m scripts.run_oe2_solar --config configs/default.yaml
python -m scripts.run_oe3_simulate --config configs/default.yaml

# Monitoreo de entrenamiento RL (útil para sesiones largas)
python monitor_checkpoints.py          # Vista tiempo real de checkpoints
python show_training_status.py         # Snapshot de progreso actual

# Reanudar entrenamiento interrumpido (auto-detecta último checkpoint)
python -m scripts.continue_sac_training --config configs/default.yaml
python -m scripts.continue_ppo_training --config configs/default.yaml
python -m scripts.continue_a2c_training --config configs/default.yaml

# Entrenamiento serial completo (SAC → PPO → A2C)
python -m scripts.train_agents_serial --config configs/default.yaml

# Instalar como paquete editable (necesario antes de primera ejecución)
pip install -e .
```

**Orden de ejecución típico**:
1. Ejecutar pipeline completo o por etapas (OE2 → OE3)
2. Para entrenamientos largos: usar `continue_<agent>_training.py` en lugar de re-ejecutar `run_pipeline.py`
3. Monitorear con `monitor_checkpoints.py` durante entrenamiento
4. Verificar resultados en `analyses/oe3/co2_comparison_table.csv`

## Validación (Sin Suite de Tests)

Validación mediante assertions en tiempo de ejecución - **NO ELIMINAR**:

- `solar_pvlib.py`: `len(index) == 8760` (año completo), `annual_kwh >= target * 0.95`
- `bess.py`: DoD 0.7-0.95, eficiencia 0.85-0.98
- `dataset_builder.py`: Validación de 128 archivos CSV de cargadores, schemas JSON válidos

**No hay suite de tests pytest** - el proyecto confía en:
1. Validación interna de dataclasses con constraints
2. Logging exhaustivo (`logger.info()` en todos los módulos)
3. Verificación manual de artefactos de salida (JSONs, CSVs, plots)

## Variables de Entorno

Sobrescribir via `.env`:

- `GRID_CARBON_INTENSITY_KG_PER_KWH` (default: 0.4521 kg/kWh - red térmica Iquitos)
- `TARIFF_USD_PER_KWH` (default: 0.20)

## Dependencias Clave

`pvlib` (solar), `citylearn>=2.5.0` (simulación), `torch` (RL), `stable-baselines3` (PPO/A2C)

## Checkpoints y Reanudación de Entrenamiento

Los agentes RL soportan recuperación basada en checkpoints. Se guardan cada N pasos y pueden reanudar entrenamiento interrumpido.

**Claves de configuración** (`cfg["oe3"]["evaluation"]["sac"]`):
```yaml
resume_checkpoints: true          # Habilitar reanudación desde último checkpoint
checkpoint_freq_steps: 1000       # Guardar cada 1000 pasos
save_final: true                  # Guardar modelo final como <agent>_final.zip
```

**Ubicación de checkpoints**: `outputs/oe3/checkpoints/<agent>/`
- `sac_step_1000.zip`, `sac_step_2000.zip`, ... (incrementales)
- `sac_final.zip` (al completar entrenamiento)

**Lógica de reanudación** (`simulate.py` → `_latest_checkpoint()`): Encuentra automáticamente el checkpoint de mayor paso o `*_final.zip`.

## Configuración GPU/CUDA

Los agentes auto-detectan GPU via `detect_device()` en `oe3/agents/sac.py`:
- **CUDA** (NVIDIA): Preferido, configurar `device: cuda` en config
- **MPS** (Apple Silicon): Auto-detectado
- **CPU**: Fallback cuando no hay GPU disponible

**Claves de configuración**:
```yaml
device: cuda          # Forzar CUDA (o "cpu", "mps", "auto")
use_amp: true         # Precisión mixta (más rápido en GPUs modernas)
batch_size: 1024      # Aumentar para utilización de memoria GPU
```

**Verificar GPU**: Ejecutar `python -c "import torch; print(torch.cuda.is_available())"` antes de entrenar.

## Episodios de Entrenamiento y Recomendaciones

**Config actual** (`episodes: 10`) es para **pruebas rápidas/debugging**. Para resultados de producción:

| Agente | Pruebas | Producción | Notas |
|--------|---------|------------|-------|
| SAC    | 10 eps  | 50-100 eps | `learn(episodes=N)` |
| PPO    | 87600 pasos | 438000 pasos | parámetro `timesteps` (5x) |
| A2C    | 10 eps  | 50 eps | Similar a SAC |

**Scripts de continuación** (`scripts/continue_<agent>_training.py`): Reanudar entrenamiento interrumpido desde checkpoints.

## Componente FastAPI + MongoDB

Ubicado en `docker/fastapi-mongo/`. API REST para gestión de sesiones EV y resultados de simulación:

```bash
cd docker/fastapi-mongo
docker-compose up -d --build      # Iniciar servicios
curl http://localhost:8000/health # Verificar
```

Endpoints principales:
- `POST /api/v1/sessions` → Crear sesión de carga
- `GET /api/v1/agents/comparison` → Comparar resultados CO₂ de agentes RL
- `GET /api/v1/infrastructure` → Configuración del sistema

## Convenciones de Archivos

- Scripts: `run_<etapa>_<componente>.py` (pipeline principal) | `continue_<agent>_training.py` (reanudación)
- Salidas: `*_results.json` (resumen) + `*_timeseries.csv` (horario)
- Reportes: Siempre versiones duales `.csv` + `.md`
- Logs de entrenamiento: `analyses/oe3/training/<AGENT>_training_metrics.csv`

## Debugging y Monitoreo

**Herramientas disponibles**:
- `monitor_checkpoints.py`: Vista en tiempo real de progreso de checkpoints (actualiza cada 5s)
- `show_training_status.py`: Snapshot de progreso actual sin re-ejecutar
- `TRAINING_STATUS.md`: Documento de seguimiento manual de sesiones de entrenamiento
- Logs con nivel `INFO`: Uso intensivo de `logger.info()` en todos los módulos para trazabilidad

**Puntos de verificación comunes**:
1. **Python 3.11**: `scripts/_common.py` lanza `RuntimeError` si versión incorrecta
2. **Dataclasses frozen**: Todas las salidas usan `@dataclass(frozen=True)` - no modificar post-creación
3. **Assertions críticas**: `solar_pvlib.py` verifica 8760 timesteps, `bess.py` valida DoD/eficiencia
4. **Checkpoints**: Auto-guardado cada N pasos (config `checkpoint_freq_steps`), reanudación desde más reciente

**Errores frecuentes**:
- `RuntimeError: Python 3.11 is required` → Activar venv correcto (`.venv\Scripts\activate`)
- Fallas en `dataset_builder.py` → Verificar que OE2 completó correctamente (check `data/interim/oe2/`)
- GPU no detectada → Revisar `torch.cuda.is_available()`, usar `device: cpu` en config como fallback
- `FileNotFoundError` en CSVs → Pipeline incompleto, ejecutar etapas OE2 antes de OE3
