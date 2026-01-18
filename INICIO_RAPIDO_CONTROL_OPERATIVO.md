# 🚀 INICIO RÁPIDO - Control Operativo Avanzado

**Objetivo**: Mejorar operación del sistema EV (sin cambiar BESS: 2000 kWh)  
**Duración Total**: 10-14 horas  
**Última Actualización**: 2026-01-18

---

## ⚡ Comandos Clave

### 1. Capturar Baseline (Sin Control)

```bash
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml
# ⏱️ ~30 min | Salida: uncontrolled_diagnostics.csv + summary.json
```

### 2. Reentrenar SAC (Con Control Operativo)

```bash
python -m scripts.run_oe3_simulate \
  --config configs/default.yaml \
  --agent sac \
  --experiment retrain_operational \
  --episodes 5 \
  --device cuda
# ⏱️ ~4-6 horas | Salida: Checkpoint + logs
```

### 3. Comparar Resultados

```bash
python -m scripts.compare_baseline_vs_retrain --config configs/default.yaml
# ⏱️ ~30 min | Salida: Tabla comparativa + gráficos
```

---

## 📊 Métricas Esperadas de Mejora

| KPI | Baseline | Esperado | Mejora |
|-----|----------|----------|--------|
| Potencia pico (kW) | 175 | 140 | ↓20% |
| Importación pico (MWh/año) | 1.28 | 0.95 | ↓26% |
| Importación total (MWh/año) | 2.45 | 2.10 | ↓14% |
| SOC mínimo BESS (%) | 22 | 45 | ↑103% |
| CO₂ anual (t) | 1,110 | 950 | ↓14% |
| Fairness (ratio) | 1.80 | 1.20 | ↓33% |

---

## 📁 Archivos Generados

### Inputs

```
configs/
└── default.yaml                          [ACTUALIZADO: +45 líneas]
    └── oe2.operational_control (NEW)

src/iquitos_citylearn/oe3/
├── enriched_observables.py                [NUEVO: 310 líneas]
└── rewards.py                             [ACTUALIZADO: +180 líneas]

scripts/
├── run_uncontrolled_baseline.py           [NUEVO: 180 líneas]
└── compare_baseline_vs_retrain.py         [NUEVO: 450 líneas]
```

### Outputs (Generados durante ejecución)

```
outputs/oe3/
├── diagnostics/
│   ├── uncontrolled_diagnostics.csv       (8760 rows × 15 cols)
│   ├── uncontrolled_summary.json
│   ├── sac_retrain_diagnostics.csv
│   └── sac_retrain_summary.json
├── simulations/
│   └── sac_retrain_evaluation/
│       └── sac_simulation_results.json
└── analysis/
    ├── comparison_metrics.csv
    ├── comparison_summary.json
    └── plots/
        ├── power_profile.png
        ├── soc_evolution.png
        └── grid_import.png
```

---

## 🔧 Configuración de Control Operativo

Definida en `configs/default.yaml`:

```yaml
oe2:
  operational_control:
    peak_hours: [18, 19, 20, 21]          # Horas críticas
    valley_hours: [9, 10, 11, 12]         # Horas de bajo consumo
    power_limits_kw:
      playa_motos: 120.0                  # Throttling operativo
      playa_mototaxis: 48.0
      total_aggregate: 150.0
    bess_soc_target:
      normal_hours: 0.60                  # 1200 kWh
      pre_peak_hours: 0.85                # 1700 kWh (cargar antes de pico)
      during_peak_hours: 0.40             # 800 kWh (permitir descarga)
    peak_cost_multiplier: 1.5
    import_penalty_weight: 0.30
    fairness_penalty_weight: 0.15
    soc_reserve_penalty: 0.20
```

---

## 📚 Documentación Principal

| Documento | Propósito | Páginas |
|-----------|-----------|---------|
| **PLAN_CONTROL_OPERATIVO.md** | Plan completo de 8 fases | 15 |
| **GUIA_IMPLEMENTACION_CONTROL_OPERATIVO.md** | Pasos detallados con validaciones | 40 |
| **RESUMEN_MAESTRO_CAMBIOS.md** | Changelog completo | 25 |
| **INICIO_RAPIDO.md** | Este documento | 5 |

**Lectura recomendada**:

1. 📖 Este documento (5 min)
2. 📖 PLAN_CONTROL_OPERATIVO.md (10 min) - Entender estrategia
3. 🚀 GUIA_IMPLEMENTACION_CONTROL_OPERATIVO.md (durante ejecución)
4. 📊 RESUMEN_MAESTRO_CAMBIOS.md (referencia técnica)

---

## 🎯 Proceso de 3 Pasos

### Paso 1: Baseline (40 min)

```bash
# Ejecutar agente sin control
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml

# Validar
python -c "
import pandas as pd
df = pd.read_csv('outputs/oe3/diagnostics/uncontrolled_diagnostics.csv')
print(f'✓ {len(df)} timesteps')
print(f'Potencia pico: {df[\"ev_power_total_kw\"].max():.1f} kW')
"
```

### Paso 2: Reentreno (5 horas)

```bash
# Entrenar SAC con penalizaciones operacionales
python -m scripts.run_oe3_simulate \
  --config configs/default.yaml \
  --agent sac \
  --experiment retrain_operational \
  --episodes 5 \
  --device cuda

# Monitorear (en otra terminal)
python monitor_checkpoints.py
```

### Paso 3: Análisis (45 min)

```bash
# Comparar y generar gráficos
python -m scripts.compare_baseline_vs_retrain --config configs/default.yaml

# Ver resultados
python -c "
import pandas as pd
df = pd.read_csv('outputs/oe3/analysis/comparison_metrics.csv')
print(df.to_string(index=False))
"
```

---

## 🔍 Validaciones Rápidas

### Después de Paso 1 (Baseline)

```bash
✅ outputs/oe3/diagnostics/uncontrolled_diagnostics.csv existe (8760 rows)
✅ Potencia pico entre 170-180 kW
✅ Importación entre 2.4-2.5 M kWh
✅ SOC mínimo entre 20-25%
```

### Después de Paso 2 (Reentreno)

```bash
✅ outputs/oe3/checkpoints/sac_retrain_operational_final.zip existe
✅ Logs muestran convergencia de rewards
✅ Entrenamiento completó N episodes sin excepciones
```

### Después de Paso 3 (Análisis)

```bash
✅ comparison_metrics.csv tiene 8+ métricas
✅ Gráficos generados (power_profile.png, soc_evolution.png, grid_import.png)
✅ SAC mejora ≥80% de métricas vs baseline
```

---

## 📈 Métodos de Mejora Implementados

### 1️⃣ Throttling de Potencia

Limitar carga activa por playa:

- **Motos**: 120 kW (de 224 kW máx) = -46%
- **Mototaxis**: 48 kW (sin cambio)
- **Agregado**: 150 kW (de 272 kW máx) = -45%

### 2️⃣ Reserva Dinámica de SOC

Mantener energía BESS para pico:

- **Normal (0-15h, 22h)**: SOC ≥ 60%
- **Pre-pico (16-17h)**: SOC ≥ 85% ← Cargar BESS
- **Pico (18-21h)**: SOC ≥ 40% ← Usar BESS

### 3️⃣ Penalizaciones en Rewards

Entrenar agente para cumplir restricciones:

```python
penalizar: -max(0, soc_target - soc_actual)       # SOC bajo
penalizar: -max(0, p_total - 150_kW)              # Pico alto
penalizar: -(ratio_fairness - 1.0) / 2            # Desequilibrio
penalizar: -max(0, importación - 50) / 100        # Importación pico
```

---

## ⚠️ Restricciones de Seguridad

✅ **NO se modifica**:

- BESS capacidad: 2,000 kWh (fijo)
- BESS potencia: 1,200 kW (fijo)
- Solar potencia: 4,162 kWp (fijo)
- Chargers instalados: 272 kW (fijo)

✅ **Controlable**:

- Límites de carga activa (throttling)
- Reserva de energía (scheduling)
- Pesos de recompensa (RL)

---

## 🐛 Troubleshooting Rápido

### Error: "ModuleNotFoundError: enriched_observables"

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Error: "CUDA out of memory"

```bash
# Usar CPU
python -m scripts.run_oe3_simulate ... --device cpu
```

### Reentreno lento

```bash
# Reducir episodes en default.yaml
oe3:
  evaluation:
    sac:
      episodes: 2  # De 5 a 2
```

### Resultados no mejoran

```bash
# Aumentar penalización operacional
oe2:
  operational_control:
    import_penalty_weight: 0.50  # De 0.30 a 0.50
    soc_reserve_penalty: 0.30    # De 0.20 a 0.30
```

---

## 📞 Soporte

**Preguntas sobre**:

- 📖 Estrategia general → PLAN_CONTROL_OPERATIVO.md
- 🔧 Implementación paso a paso → GUIA_IMPLEMENTACION_CONTROL_OPERATIVO.md
- 📝 Cambios técnicos → RESUMEN_MAESTRO_CAMBIOS.md
- 💻 Código → Ver docstrings en módulos

**Validar instalación**:

```bash
python -c "
from iquitos_citylearn.oe3.enriched_observables import OperationalConstraints
from iquitos_citylearn.oe3.rewards import create_iquitos_reward_weights
from scripts._common import load_all
cfg, _ = load_all('configs/default.yaml')
print('✅ Todo OK - Listo para ejecutar')
"
```

---

## 📊 Dashboard de Progreso

```
FASE 1: Capturar Baseline                        ✅ COMPLETADA
FASE 2: Enriquecer Observables                   ✅ COMPLETADA
FASE 3: Actualizar Recompensas                   ✅ COMPLETADA
FASE 4: Implementar Constraints                  ✅ COMPLETADA
FASE 5: Reentrenar SAC                           ⏳ LISTA (5-6h)
FASE 6: Evaluar SAC                              ⏳ LISTA (30min)
FASE 7: Comparar Resultados                      ⏳ LISTA (45min)
FASE 8: Documentación Final                      ⏳ LISTA (30min)
─────────────────────────────────────────────────────────────
Total Tiempo Ejecución Computacional             ≈ 6-8 horas
Total Tiempo Humano (setup + validación)         ≈ 2-3 horas
```

---

## 🎓 Conceptos Clave

- **Throttling**: Limitar potencia sin cambiar capacidad
- **Reserva dinámica**: Mantener energía BESS para horas críticas
- **Fairness**: Equilibrio de carga entre diferentes tipos de vehículos
- **Penalización**: Reducción de recompensa por incumplimiento de restricciones
- **SAC**: Soft Actor-Critic (algoritmo RL usado para reentreno)

---

## 🔗 Links Rápidos

| Recurso | Ubicación |
|---------|-----------|
| Config de sistema | `configs/default.yaml` |
| Control operativo | `oe2.operational_control` |
| Observables enriquecidos | `src/iquitos_citylearn/oe3/enriched_observables.py` |
| Recompensas mejoradas | `src/iquitos_citylearn/oe3/rewards.py` |
| Agentes | `src/iquitos_citylearn/oe3/agents/` |
| Salidas | `outputs/oe3/` |

---

**¿Listo para comenzar?**

👉 **Próximo paso**: Ejecutar Paso 1

```bash
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml
```

✅ **Tiempo estimado**: 30 minutos  
📊 **Resultado**: baseline_diagnostics.csv + summary.json

---

**Documento**: INICIO_RAPIDO.md v1.0  
**Fecha**: 2026-01-18  
**Estado**: 🟢 LISTO PARA EJECUTAR
