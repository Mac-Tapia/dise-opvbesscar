# Proyecto Iquitos EV + PV/BESS (OE2 → OE3)

Este repositorio contiene el pipeline de dimensionamiento (OE2) y control
inteligente (OE3) para un sistema de carga de motos y mototaxis eléctricos con
integración fotovoltaica y BESS en Iquitos, Perú.

## Alcance

- **OE2 (dimensionamiento):** PV 4,050 kWp (Kyocera KS20) con inversor Eaton
  - Xpert1670 (2 unidades, 31 módulos por string, 6,472 strings, 200,632 módulos
    - totales), BESS 2 MWh/1.2 MW y 128 cargadores (112 motos @2 kW, 16 mototaxis
      - @3 kW).
- **OE3 (control RL):** Agentes SAC/PPO/A2C en CityLearn v2 para minimizar CO₂,
  - costo y picos, maximizando uso solar y satisfacción EV.
- **Reducción CO₂ anual (capacidad OE2):**
  - Directa: 3,081.20 tCO₂/año (gasolina → EV).
  - Indirecta: 3,626.66 tCO₂/año (PV/BESS desplaza red).
  - Neta: 6,707.86 tCO₂/año. Emisiones con PV/BESS: 2,501.49 tCO₂/año.

## 🚀 Estado Actual (2026-01-26)

**✅ Proyecto 100% limpio**: 0 errores Pyright (Phase 5 completada)
- Pipeline OE3 ejecutándose en background (dataset + baseline + 3 agentes)
- Datasets validados: 8,760 horas (hourly), 128 chargers, solar real
- Checkpoints acumulables: SAC → PPO → A2C (reset_num_timesteps=False)
- GPU CUDA activada (RTX 4060, 8-12 horas estimadas)

## Requisitos

- **Python 3.11+** (activar `.venv`).
- **Dependencias**: 
  - `pip install -r requirements.txt` (base)
  - `pip install -r requirements-training.txt` (RL con GPU)
- **Herramientas**: `git`, `poetry` (opcional), Docker (despliegues)
- **GPU** (recomendado): CUDA 11.8+, torch con soporte GPU (10x más rápido)

## Estructura clave

- `configs/default.yaml`: parámetros OE2/OE3 (PV, BESS, flota, recompensas).
- `scripts/run_oe2_solar.py`: dimensionamiento PV (pvlib + PVGIS).
- `data/interim/oe2/`: artefactos de entrada OE2 (solar, BESS, chargers).
- `reports/oe2/co2_breakdown/`: tablas de reducción de CO₂.
- `src/iquitos_citylearn/oe3/`: agentes y dataset builder CityLearn.
- `COMPARACION_BASELINE_VS_RL.txt`: resumen cuantitativo baseline vs RL.

## Uso rápido

<!-- markdownlint-disable MD013 -->
```bash
# Activar entorno
python -m venv .venv
./.venv/Scripts/activate  # en Windows

# Pipeline OE3 COMPLETO (dataset + baseline + 3 agentes)
python -m scripts.run_oe3_simulate --config configs/default.yaml

# O solo dataset builder (validar datos)
python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# O solo baseline (referencia sin control)
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml

# Comparar resultados (después del entrenamiento)
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```bash
<!-- markdownlint-enable MD013 -->

## Referencias de resultados

- CO₂: `reports/oe2/co2_breakdown/oe2_co2_breakdown.json`
- Solar (Eaton Xpert1670): `data/interim/oe2/solar/solar_results.json` y
  - `solar_technical_report.md`
- Documentación RL: `docs/INFORME_UNICO_ENTRENAMIENTO_TIER2.md`,
  - `COMPARACION_BASELINE_VS_RL.txt`

## 📖 Documentación Consolidada

**Comienza aquí:**
- **[INICIO_RAPIDO.md](INICIO_RAPIDO.md)** - Setup 5 minutos (Python 3.11, venv, primeros comandos)
- **[QUICKSTART.md](QUICKSTART.md)** - Guía en inglés

**Ejecución y Monitoreo:**
- **[COMANDOS_RAPIDOS.md](COMANDOS_RAPIDOS.md)** - Comandos del día a día (dataset, baseline, training, comparación)
- **[MONITOREO_EJECUCION.md](MONITOREO_EJECUCION.md)** - Monitorear pipeline en tiempo real
- **[PIPELINE_EJECUTABLE_DOCUMENTACION.md](PIPELINE_EJECUTABLE_DOCUMENTACION.md)** - Detalles del pipeline OE3

**Resultados y Configuración:**
- **[RESUMEN_EJECUTIVO_FINAL.md](RESUMEN_EJECUTIVO_FINAL.md)** - KPIs: CO₂, solar, costos (Phase 5)
- **[CONFIGURACIONES_OPTIMAS_AGENTES_OE3.md](CONFIGURACIONES_OPTIMAS_AGENTES_OE3.md)** - Hiperparámetros SAC/PPO/A2C
- **[ESTADO_ACTUAL.md](ESTADO_ACTUAL.md)** - Timeline completo y hitos completados

**Correcciones Técnicas:**
- **[CORRECCIONES_COMPLETAS_FINAL.md](CORRECCIONES_COMPLETAS_FINAL.md)** - Phase 5: Pyright 100% limpio
- **[CORRECCIONES_ERRORES_2026-01-26.md](CORRECCIONES_ERRORES_2026-01-26.md)** - Detalles de fixes

**Documentación Adicional (Raíz):**
- [COMANDOS_EJECUTABLES.md](COMANDOS_EJECUTABLES.md) - Scripts antiguos (referencia)
- [ENTREGA_FINAL.md](ENTREGA_FINAL.md) - Resumen de fases
- [INDICE_MAESTRO_DOCUMENTACION.md](INDICE_MAESTRO_DOCUMENTACION.md) - Índice completo
- [STATUS_ACTUAL_2026_01_25.md](STATUS_ACTUAL_2026_01_25.md) - Timeline (26 de enero)
- [CONTRIBUTING.md](CONTRIBUTING.md) - Estándares de código

**Archivos de Referencia:**
- `configs/default.yaml` - Parámetros OE2/OE3 (solar, BESS, flota, rewards)
- `data/interim/oe2/` - Artefactos de entrada OE2 (solar, BESS, chargers)
- `outputs/oe3_simulations/` - Resultados RL (simulation_summary.json, CSVs)
- `checkpoints/{SAC,PPO,A2C}/` - Modelos entrenados (zip format)

## Despliegue y Monitoreo

### Local (Desarrollo)
```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
# Monitorear en tiempo real con:
python scripts/monitor_training_live_2026.py
```

### Docker
```bash
# GPU training (CUDA)
docker-compose -f docker-compose.gpu.yml up -d

# FastAPI server (modelo serving)
docker-compose -f docker-compose.fastapi.yml up -d
# Accede: http://localhost:8000/docs
```

### Kubernetes
```bash
kubectl apply -f docker/k8s-deployment.yaml
kubectl scale deployment rl-agent-server --replicas 5
```

## Troubleshooting

| Problema | Solución |
|----------|----------|
| "128 chargers not found" | Verificar `data/interim/oe2/chargers/individual_chargers.json` con 32 chargers × 4 sockets |
| Solar timeseries <> 8,760 filas | Downsample PVGIS 15-min: `df.resample('h').mean()` |
| GPU out of memory | Reducir `n_steps` (PPO: 2048→1024), `batch_size` (128→64) |
| Reward explosion (NaN) | Verificar MultiObjectiveWeights suma=1.0, observables escaladas |
| Checkpoint incompatible | Restart from scratch si cambió agent class signature |

## Flujo de trabajo (OE2 → OE3)

### Fase 1: OE2 (Dimensionamiento - COMPLETADA)
- Generación solar: PVGIS TMY → pvlib (Kyocera KS20 + Eaton Xpert1670)
- BESS fijo: 2 MWh / 1.2 MW, DoD 80%, eff 95%
- 128 chargers: 32 físicos × 4 tomas (112 motos @2kW + 16 mototaxis @3kW = 272 kW)
- Artefactos: `data/interim/oe2/solar/`, `chargers/`, `bess/`

### Fase 2: OE3 Dataset Builder (VALIDADA)
- Valida 8,760 horas (hourly exacto, no 15-min)
- Carga perfiles reales de playas (Playa_Motos.csv, Playa_Mototaxis.csv)
- Genera schema CityLearn v2 con 534-dim obs, 126-dim actions
- Output: `data/processed/citylearn/iquitos_ev_mall/schema.json` + 128 CSVs

### Fase 3: Baseline Simulation (EJECUTADO)
- Control sin RL (chargers siempre ON)
- Referencia CO₂, picos, costos, satisfacción EV
- Durá ~10-15 min, output: `outputs/oe3_simulations/uncontrolled_*.csv`

### Fase 4: Entrenamientos RL (EN EJECUCIÓN)
- **SAC** (off-policy): ~2-3 horas / 5 episodios
- **PPO** (on-policy): ~2-3 horas / 5 episodios (aprende sobre SAC)
- **A2C** (simple): ~2-3 horas / 5 episodios (aprende sobre PPO)
- GPU: CUDA 11.8, RTX 4060 (~8-12 horas total)
- Checkpoints: `checkpoints/{SAC,PPO,A2C}/latest.zip`

### Fase 5: Evaluación y Comparación (PENDIENTE)
- Métricas: CO₂, costos, autoconsumo solar, picos, satisfacción EV
- Reportes: `outputs/oe3_simulations/simulation_summary.json`
- Comando: `python -m scripts.run_oe3_co2_table`

## Objetivos

- Minimizar CO₂ anual (directo: gasolina → EV; indirecto: PV/BESS desplaza red).
- Reducir costos y picos de red sin sacrificar satisfacción EV.
- Maximizar autoconsumo solar y estabilidad de red.

## Arquitectura Técnica Clave

### Observación (534-dim)
```
Building energy: 4
  - Solar generation, total demand, grid import, BESS SOC

Chargers: 512 (128 × 4)
  - Demand, power, occupancy, battery per charger

Time features: 4
  - Hour, month, day of week, peak flag

Grid state: 2
  - Carbon intensity, electricity tariff
```

### Acción (126-dim, continuous [0,1])
- 126 chargers controlables (128 - 2 reserved)
- Setpoint normalizados: action_i × charger_max_power = power_delivered

### Agentes (Stable-Baselines3)
- **SAC**: Off-policy, entropy, faster convergence (sparse rewards)
- **PPO**: On-policy, clipped objective, more stable
- **A2C**: Simple, on-policy, fast wall-clock (CPU/GPU)

### Redes (MLP)
```
Input (534) → Dense(1024, relu) → Dense(1024, relu) → Output(126, tanh)
```

## Resultados Esperados (Phase 5)

### Dataset Validado ✅
- **Solar**: 8,760 horas (hourly), 1,933 kWh/año/kWp, pico ~11:00 AM local
- **Demanda**: 12,368,025 kWh/año (real del mall)
- **Chargers**: 128 individuales (112 motos 2kW + 16 mototaxis 3kW)
- **BESS**: 4,520 kWh @ 2,712 kW (OE2 resultado)

### Baseline (Referencia)
- CO₂: ~10,200 kg/año (sin control, grid import máximo)
- Autoconsumo solar: ~40% (mucha pérdida)
- Satisfacción EV: 100% (siempre cargando)

### Agentes RL (Esperado después entrenamiento)
- **SAC**: CO₂ -26% (~7,500 kg/año), solar +65%
- **PPO**: CO₂ -29% (~7,200 kg/año), solar +68%
- **A2C**: CO₂ -24% (~7,800 kg/año), solar +60%

### Función Multi-Objetivo
```yaml
Pesos (normalizados):
  co2_emissions: 0.50        # Minimizar CO₂ (prioritario)
  cost_minimization: 0.15    # Reducir costos
  solar_fraction: 0.20       # Autoconsumo solar
  ev_satisfaction: 0.10      # Satisfacción EV
  grid_stability: 0.05       # Estabilidad red
```

## Despliegue y Monitoreo

### Local (Desarrollo)
```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml
# Monitorear en tiempo real con:
python scripts/monitor_training_live_2026.py
```

### Docker
```bash
# GPU training (CUDA)
docker-compose -f docker-compose.gpu.yml up -d

# FastAPI server (modelo serving)
docker-compose -f docker-compose.fastapi.yml up -d
# Accede: http://localhost:8000/docs
```

### Kubernetes
```bash
kubectl apply -f docker/k8s-deployment.yaml
kubectl scale deployment rl-agent-server --replicas 5
```

## Troubleshooting

| Problema | Solución |
|----------|----------|
| "128 chargers not found" | Verificar `data/interim/oe2/chargers/individual_chargers.json` con 32 chargers × 4 sockets |
| Solar timeseries <> 8,760 filas | Downsample PVGIS 15-min: `df.resample('h').mean()` |
| GPU out of memory | Reducir `n_steps` (PPO: 2048→1024), `batch_size` (128→64) |
| Reward explosion (NaN) | Verificar MultiObjectiveWeights suma=1.0, observables escaladas |
| Checkpoint incompatible | Restart from scratch si cambió agent class signature |

## Próximos Pasos

1. **Monitor entrenamiento**: Esperar completación pipeline (8-12 horas GPU)
   - Ver `MONITOREO_EJECUCION.md` para scripts de monitoreo
   
2. **Revisar resultados**: `outputs/oe3_simulations/simulation_summary.json`
   - CO₂ reducción, autoconsumo solar, costos, satisfacción EV
   
3. **Ajustar rewards** (si es necesario):
   - Editar `MultiObjectiveWeights` en `src/iquitos_citylearn/oe3/rewards.py`
   - Restart entrenamiento con nuevos pesos
   
4. **Desplegar agente óptimo**:
   - Cargar checkpoint `checkpoints/{SAC,PPO,A2C}/latest.zip`
   - FastAPI server + Docker para producción
   
5. **Validar en Iquitos**:
   - Recolectar datos reales del mall
   - Reentrenar con datos actuales si es necesario
   - Monitoreo continuo de CO₂ vs baseline

## Contacto & Contribuciones

- **Autor**: Mac-Tapia (pvbesscar project)
- **Rama principal**: `main` (GitHub: Mac-Tapia/dise-opvbesscar)
- **Estándares**: Ver [CONTRIBUTING.md](CONTRIBUTING.md)
- **Python 3.11+**: Requerido (type hints habilitados con `from __future__ import annotations`)
