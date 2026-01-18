# Control Operativo Avanzado - Plan de Ejecución

**Objetivo**: Mejorar la operación del sistema de carga EV (sin cambiar capacidad del BESS) mediante:

- Control operativo inteligente (scheduling, throttling, reservas dinámicas)
- Penalizaciones de recompensa para cumplir restricciones operacionales
- Comparación contra baseline "sin control"

---

## 1. Baseline Uncontrolled (Estado Actual)

### 1.1 Script: `run_uncontrolled_baseline.py`

**Propósito**: Capturar estado de referencia sin inteligencia de control.

**Salidas**:

- `outputs/oe3/diagnostics/uncontrolled_diagnostics.csv`: 8760 timesteps con:
  - Potencia EV por playa (motos, mototaxis, total)
  - Importación de red (horaria, acumulada diaria)
  - SOC BESS (%, potencia)
  - Generación solar
  - Flags de pico (18-21h) / valle
  - Sesiones atendidas en pico

- `outputs/oe3/diagnostics/uncontrolled_summary.json`: Resumen estadístico

**Ejecución**:

```bash
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml
```

**Métricas clave a capturar**:

- Potencia pico máxima EV: ~ 150-180 kW (sin control)
- Importación anual: ~ 2.2-2.5 M kWh (dependencia de red)
- Importación en pico (18-21h): ~ 1.1-1.3 M kWh (crítico)
- SOC mínimo BESS: ~ 20-30% (bajo)
- Desequilibrio playas (ratio): ~ 1.5-2.0 (motos > mototaxis)

---

## 2. Enriquecimiento de Observables (OE3 Dataset)

### 2.1 Nuevos Observables Integrados

**En `enriched_observables.py`**:

```python
OperationalConstraints:
  - peak_hours: [18, 19, 20, 21]
  - valley_hours: [9, 10, 11, 12]
  - power_limits_kw: { playa_motos: 120, playa_mototaxis: 48, total_aggregate: 150 }
  - bess_soc_target: { normal: 0.60, pre_peak: 0.85, during_peak: 0.40 }

EnrichedObservableWrapper.get_enriched_state():
  - is_peak_hour, is_valley_hour
  - bess_soc_current, bess_soc_target, bess_soc_reserve_deficit
  - pv_power_available_kw, pv_power_ratio
  - grid_import_kw
  - ev_power_total_kw, ev_power_motos_kw, ev_power_mototaxis_kw
  - ev_power_fairness_ratio
  - pending_sessions_motos, pending_sessions_mototaxis
```

### 2.2 Configuración en `default.yaml`

```yaml
oe2:
  operational_control:
    peak_hours: [18, 19, 20, 21]
    valley_hours: [9, 10, 11, 12]
    power_limits_kw:
      playa_motos: 120.0          # Throttling operativo
      playa_mototaxis: 48.0
      total_aggregate: 150.0
    bess_soc_target:
      normal_hours: 0.60
      pre_peak_hours: 0.85        # Carga estratégica antes de pico
      during_peak_hours: 0.40
    peak_cost_multiplier: 1.5
    import_penalty_weight: 0.30
    fairness_penalty_weight: 0.15
    soc_reserve_penalty: 0.20
```

---

## 3. Ajuste de Recompensas (Funciones Multiobjetivo)

### 3.1 Versión Original (Baseline)

```python
MultiObjectiveWeights:
  - co2: 0.50
  - cost: 0.15
  - solar: 0.20
  - ev_satisfaction: 0.10
  - grid_stability: 0.05
  - operational_penalties: 0.00  # Sin penalizaciones
```

### 3.2 Versión Mejorada (Reentreno)

```python
MultiObjectiveWeights (include_operational=True):
  - co2: 0.45
  - cost: 0.12
  - solar: 0.18
  - ev_satisfaction: 0.08
  - grid_stability: 0.05
  - operational_penalties: 0.12  # NUEVA: penalizaciones operacionales

compute_with_operational_penalties():
  R_total = w_base * R_base + w_op * R_operational
  
  R_operational = sum([
    -max(0, soc_target - soc_actual) * weight_soc,      # Reserva SOC
    -max(0, p_total - p_limit) * weight_power,          # Pico en horas pico
    -fairness_excess * weight_fairness,                 # Desequilibrio
    -import_peak * weight_import,                       # Importación en pico
  ])
```

---

## 4. Constraints en Simulador

### 4.1 Throttling de Potencia por Playa

```python
# En agent.predict() o environment.step():
power_motos_requested = observations["ev_power_motos_kw"]
power_motos_limited = min(power_motos_requested, constraints.power_limits_kw["playa_motos"])

power_mototaxis_requested = observations["ev_power_mototaxis_kw"]
power_mototaxis_limited = min(power_mototaxis_requested, constraints.power_limits_kw["playa_mototaxis"])

# Validar límite agregado
total_power = power_motos_limited + power_mototaxis_limited
if total_power > constraints.power_limits_kw["total_aggregate"]:
    # Prorratear reducción
    scale = constraints.power_limits_kw["total_aggregate"] / total_power
    power_motos_limited *= scale
    power_mototaxis_limited *= scale
```

### 4.2 Reserva SOC Pre-Pico

```python
# En agent.predict():
hour = observations["hour_of_day"]
bess_soc = observations["bess_soc_current"]

if hour in [16, 17]:  # Pre-pico
    soc_target_min = constraints.bess_soc_target["pre_peak_hours"]  # 0.85
    if bess_soc < soc_target_min:
        # Acción = cargar BESS prioritariamente
        action_bess_discharge = -1.0  # Cargar (acción negativa)
elif hour in [18, 19, 20, 21]:  # Pico
    soc_target_min = constraints.bess_soc_target["during_peak_hours"]  # 0.40
    # Permitir descarga controlada si hay EVs pendientes
```

---

## 5. Reentreno de Agentes

### 5.1 SAC Mejorado (Principal)

```bash
# Fase 1: Entrenamiento con observables enriquecidos + penalizaciones
python -m scripts.run_oe3_simulate \
  --config configs/default.yaml \
  --agent sac \
  --experiment retrain_operational \
  --include_operational_penalties true \
  --episodes 10  # Más episodes para convergencia

# Checkpoints: outputs/oe3/checkpoints/sac_retrain_operational_*
```

**Cambios clave**:

- Cargar `enriched_observables.py`
- Usar `MultiObjectiveWeights(include_operational=True)`
- Llamar `compute_with_operational_penalties()` en cada step de reward

### 5.2 PPO/A2C (Validación)

```bash
python -m scripts.run_oe3_simulate \
  --config configs/default.yaml \
  --agent ppo \
  --experiment retrain_operational \
  --include_operational_penalties true

python -m scripts.run_oe3_simulate \
  --config configs/default.yaml \
  --agent a2c \
  --experiment retrain_operational \
  --include_operational_penalties true
```

---

## 6. Comparación y Documentación

### 6.1 Script: `compare_baseline_vs_retrain.py`

**Propósito**: Comparar métricas de Uncontrolled vs Agentes Reentrenados

**Salidas**:

```bash
outputs/oe3/analysis/
├── comparison_summary.json
├── comparison_metrics.csv
├── plots/
│   ├── power_profile_baseline_vs_sac.png
│   ├── soc_evolution.png
│   ├── grid_import_pico_horas.png
│   ├── fairness_distribution.png
│   └── co2_comparison_table.png
└── comparative_report.md
```

**Métricas a comparar**:

| Métrica | Uncontrolled | SAC (Retrain) | Mejora |
| --- | --- | --- | --- |
| Potencia pico máxima (kW) | 175 | <140 | ↓ 20% |
| Importación anual (MWh) | 2.45 | <2.10 | ↓ 14% |
| Importación pico (MWh) | 1.28 | <0.95 | ↓ 26% |
| SOC mínimo BESS (%) | 22 | >45 | ↑ 103% |
| Desequilibrio playas | 1.8 | <1.2 | ↓ 33% |
| CO₂ anual (t) | 1,110 | <950 | ↓ 14% |
| Costo neto (USD) | 490k | <420k | ↓ 14% |

### 6.2 Actualizar Documentación Principal

**Archivos a actualizar**:

- `DOCUMENTACION_COMPLETA.md`: Sección "Selección de Agente"
- `DIAGRAMA_TECNICO_OE2_OE3.md`: Arquitectura de control operativo

---

## 7. Cronograma de Ejecución

| Fase | Tarea | Duración | Dependencia |
| --- | --- | --- | --- |
| **1** | Capturar baseline Uncontrolled | 30 min | - |
| **2** | Enriquecer observables + config | 45 min | 1 |
| **3** | Actualizar recompensas | 45 min | 2 |
| **4** | Implementar constraints | 1 h | 3 |
| **5** | Reentrenar SAC | 4-6 h | 4 |
| **6** | Reentrenar PPO/A2C (opcional) | 3-4 h | 4 |
| **7** | Comparar y documentar | 1-2 h | 5,6 |

**Total**: 10-14 horas de ejecución

---

## 8. Notas Críticas

✅ **No se modifica**:

- Capacidad BESS: 2000 kWh
- Potencia BESS: 1200 kW
- Potencia instalada chargers: 272 kW
- Paneles solares: 4162 kWp

✅ **Se modifica (solo control operativo)**:

- Límites de carga por playa (throttling)
- Reserva dinámica de SOC
- Pesos de recompensa (penalizaciones)
- Scheduling/priorización de carga

✅ **Validación**:

- Asegurar que limite de potencia agregada <= suma de capacidades individuales
- Validar SOC nunca baja de 0% ni sube de 100%
- Verificar equilibrio energético (PV + BESS >= Carga EV + Mall + Pérdidas)

---

## 9. Archivos Clave Generados

```bash
d:\diseñopvbesscar\
├── scripts/
│   ├── run_uncontrolled_baseline.py                    [CREADO]
│   └── compare_baseline_vs_retrain.py                  [PENDIENTE]
├── src/iquitos_citylearn/oe3/
│   ├── enriched_observables.py                         [CREADO]
│   ├── rewards.py                                      [ACTUALIZADO]
│   └── simulate.py                                     [ACTUALIZAR]
├── configs/
│   └── default.yaml                                    [ACTUALIZADO]
└── outputs/oe3/
    ├── diagnostics/
    │   ├── uncontrolled_diagnostics.csv                [GENERAR]
    │   └── uncontrolled_summary.json                   [GENERAR]
    ├── simulations/
    │   └── *_retrain/                                  [GENERAR]
    └── analysis/
        └── comparison_*                                [GENERAR]
```

---

## 10. Comandos Rápidos

```bash
# Capturar baseline
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml

# Reentrena SAC
python -m scripts.run_oe3_simulate --config configs/default.yaml --agent sac --experiment retrain

# Comparar
python -m scripts.compare_baseline_vs_retrain --config configs/default.yaml
```

---

**Responsables**: RL/Control Team
**Estado**: 🟡 En Progreso (Fase 1-4 completadas, Fase 5-7 pendientes)
**Última Actualización**: 2026-01-18
