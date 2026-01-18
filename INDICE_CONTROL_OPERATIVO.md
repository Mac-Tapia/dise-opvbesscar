# 📑 ÍNDICE DE ARCHIVOS - Control Operativo Avanzado

**Proyecto**: Iquitos EV Smart Charging Infrastructure  
**Subsistema**: Control Operativo (OE3)  
**Fecha**: 2026-01-18

---

## 🎯 Documentos Principales (Para Leer)

### Orden de Lectura Recomendado

1. **[RESUMEN_EJECUTIVO_CONTROL_OPERATIVO.md](RESUMEN_EJECUTIVO_CONTROL_OPERATIVO.md)** ⭐ EMPEZAR AQUÍ
   - Visión general de 2 páginas
   - Métrica de éxito y beneficios
   - Cronograma estimado
   - **Lectura**: 5-10 min

2. **[INICIO_RAPIDO_CONTROL_OPERATIVO.md](INICIO_RAPIDO_CONTROL_OPERATIVO.md)** ⚡ REFERENCIA RÁPIDA
   - Comandos clave (3 pasos)
   - Validaciones rápidas
   - Troubleshooting
   - **Lectura**: 5 min | **Búsqueda**: O(1)

3. **[PLAN_CONTROL_OPERATIVO.md](PLAN_CONTROL_OPERATIVO.md)** 📖 ESTRATEGIA
   - Plan detallado de 8 fases
   - Descripción de cada componente
   - Tablas de métricas
   - **Lectura**: 15-20 min

4. **[GUIA_IMPLEMENTACION_CONTROL_OPERATIVO.md](GUIA_IMPLEMENTACION_CONTROL_OPERATIVO.md)** 🔧 PASO A PASO
   - Instrucciones detalladas
   - Validaciones en cada fase
   - Comandos con ejemplos
   - **Lectura**: 30-45 min

5. **[RESUMEN_MAESTRO_CAMBIOS.md](RESUMEN_MAESTRO_CAMBIOS.md)** 📝 REFERENCIA TÉCNICA
   - Changelog completo
   - Matriz de cambios
   - Validaciones técnicas
   - **Lectura**: 15-20 min

---

## 💻 Código Nuevo/Modificado

### Configuración

| Archivo | Tipo | Cambios | Líneas |
|---------|------|---------|--------|
| **[configs/default.yaml](configs/default.yaml)** | Modificado | +`oe2.operational_control` | +45 |

**Sección nueva en YAML**:

```yaml
oe2:
  operational_control:
    peak_hours: [18, 19, 20, 21]
    valley_hours: [9, 10, 11, 12]
    power_limits_kw: {...}
    bess_soc_target: {...}
    peak_cost_multiplier: 1.5
    ...
```

---

### Código Core (src/iquitos_citylearn/oe3/)

#### Nuevo: Observables Enriquecidos

| Archivo | Líneas | Clases | Funciones |
|---------|--------|--------|-----------|
| **[enriched_observables.py](src/iquitos_citylearn/oe3/enriched_observables.py)** | 310 | 2 | 2 |

**Contenido**:

- `OperationalConstraints`: Carga límites desde config
- `EnrichedObservableWrapper`: Enriquece estado con flags, targets, etc.
- `compute_operational_penalties()`: Calcula penalizaciones

**Ejemplo uso**:

```python
from iquitos_citylearn.oe3.enriched_observables import OperationalConstraints
constraints = OperationalConstraints.from_config(cfg)
state = wrapper.get_enriched_state(...)  # Dict enriquecido
penalties = compute_operational_penalties(state, constraints)
```

#### Modificado: Recompensas

| Archivo | Cambios | Líneas nuevas | Métodos actualizados |
|---------|---------|---------------|---------------------|
| **[rewards.py](src/iquitos_citylearn/oe3/rewards.py)** | +operacional_penalties | +180 | 4 |

**Cambios**:

- ✅ `MultiObjectiveWeights.operational_penalties` (+1 campo)
- ✅ `__post_init__()`: Normalizar con nuevo peso
- ✅ `compute_with_operational_penalties()`: **Nueva función**
- ✅ `create_iquitos_reward_weights(include_operational=False)`: Parámetro nuevo

**Pesos predefinidos con operacional=True**:

```python
"co2_focus": {
    co2: 0.45, cost: 0.12, solar: 0.18, ev: 0.08, 
    grid: 0.05, operational: 0.12  ← NUEVO
}
```

---

### Scripts de Ejecución (scripts/)

#### Nuevo: Capturar Baseline

| Archivo | Líneas | Propósito | Entrada | Salida |
|---------|--------|-----------|---------|--------|
| **[run_uncontrolled_baseline.py](scripts/run_uncontrolled_baseline.py)** | 180 | Capturar estado actual sin control | config.yaml | diagnostics CSV + JSON |

**Funciones principales**:

- `extract_baseline_diagnostics()`: Extrae 8760 timesteps
- `compute_baseline_summary()`: Calcula 15+ métricas

**Ejecutar**:

```bash
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml
```

**Salida**:

```
outputs/oe3/diagnostics/
├── uncontrolled_diagnostics.csv       (8760 rows × 15 cols)
└── uncontrolled_summary.json          (métricas agregadas)
```

#### Nuevo: Comparar Resultados

| Archivo | Líneas | Propósito | Entrada | Salida |
|---------|--------|-----------|---------|--------|
| **[compare_baseline_vs_retrain.py](scripts/compare_baseline_vs_retrain.py)** | 450 | Análisis comparativo | 2 × diagnostics | tabla + gráficos |

**Funciones principales**:

- `load_diagnostics()`: Carga CSV + JSON de un agente
- `extract_comparison_metrics()`: Tabla comparativa
- `create_power_profile_plot()`: Gráfico 4 subplots
- `create_soc_evolution_plot()`: Evolución SOC
- `create_grid_import_plot()`: Importación de red

**Ejecutar**:

```bash
python -m scripts.compare_baseline_vs_retrain --config configs/default.yaml
```

**Salida**:

```
outputs/oe3/analysis/
├── comparison_metrics.csv             (8+ métricas)
├── comparison_summary.json
└── plots/
    ├── power_profile.png
    ├── soc_evolution.png
    └── grid_import.png
```

---

## 📊 Archivos Generados Durante Ejecución

### Baseline (Fase 1)

```
outputs/oe3/diagnostics/
├── uncontrolled_diagnostics.csv
│   └── 8760 rows (1 year hourly)
│       Columnas: hour, day, ev_power_*, grid_import_*, bess_soc_*, etc.
│
└── uncontrolled_summary.json
    └── 12+ métricas: ev_peak_power_max_kw, grid_import_total_kwh, etc.
```

### Reentreno SAC (Fase 2)

```
outputs/oe3/
├── checkpoints/sac_retrain_operational/
│   ├── sac_retrain_operational_final.zip     (Model checkpoint)
│   ├── sac_retrain_operational_step_*.zip    (Intermediate)
│   └── logs/
│       └── training_metrics_*.json
│
└── simulations/sac_retrain_evaluation/
    ├── sac_simulation_results.json           (8760 timesteps)
    └── sac_metrics.csv
```

### Análisis (Fase 3)

```
outputs/oe3/analysis/
├── comparison_metrics.csv                    (Tabla)
├── comparison_summary.json                   (JSON detallado)
│
└── plots/
    ├── power_profile.png                     (4 subplots)
    ├── soc_evolution.png                     (Evolución SOC)
    └── grid_import.png                       (2 subplots)
```

---

## 🔗 Mapa de Dependencias

```
┌─────────────────────────────────────────────────────────┐
│                    DOCUMENTACIÓN                        │
├─────────────────────────────────────────────────────────┤
│ RESUMEN_EJECUTIVO (5 min) ┐                            │
│ INICIO_RAPIDO (5 min)     ├─ Leer primero              │
│ PLAN (20 min)             ┐                            │
│ GUIA (45 min)             ├─ Detalles paso a paso      │
│ RESUMEN_MAESTRO (20 min)  ─                            │
└─────────────────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────┐
│                    CONFIGURACIÓN                        │
├─────────────────────────────────────────────────────────┤
│ configs/default.yaml (operational_control)              │
└─────────────────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────┐
│                      CÓDIGO CORE                        │
├─────────────────────────────────────────────────────────┤
│ enriched_observables.py ◄────────────┐                │
│      ↓                               │                │
│ rewards.py ◄──────────────────────────┘                │
│      ↓                                                │
│ simulate.py (actualizar para integrar)                │
└─────────────────────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────┐
│                    SCRIPTS                              │
├─────────────────────────────────────────────────────────┤
│ run_uncontrolled_baseline.py (Fase 1)                  │
│      ↓ outputs/oe3/diagnostics/uncontrolled_*         │
│                                                       │
│ run_oe3_simulate.py (Fase 2: Reentreno SAC)           │
│      ↓ outputs/oe3/checkpoints/sac_retrain_*          │
│                                                       │
│ compare_baseline_vs_retrain.py (Fase 3)               │
│      ↓ outputs/oe3/analysis/comparison_*              │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Flujo de Ejecución

### Ejecución Normal (Recomendada)

```
1. SETUP
   └─ Activar venv
   └─ Validar configs

2. FASE 1: BASELINE (30 min)
   └─ python -m scripts.run_uncontrolled_baseline
   └─ Validar: uncontrolled_diagnostics.csv (8760 rows)
   └─ Validar: uncontrolled_summary.json

3. FASE 2: REENTRENO SAC (5-6 horas)
   └─ python -m scripts.run_oe3_simulate --agent sac
   └─ Monitorear: monitor_checkpoints.py (en otra terminal)
   └─ Validar: sac_retrain_operational_final.zip

4. FASE 3: ANÁLISIS (1 hora)
   └─ python -m scripts.compare_baseline_vs_retrain
   └─ Validar: comparison_metrics.csv
   └─ Validar: plots/*.png (3 gráficos)

5. DOCUMENTACIÓN (30 min)
   └─ Actualizar DOCUMENTACION_COMPLETA.md
   └─ Actualizar DIAGRAMA_TECNICO_OE2_OE3.md
   └─ Crear REPORTE_FINAL.md
```

---

## ✅ Checklist de Validación

### Después de Setup

- [ ] `enriched_observables.py` importable
- [ ] `rewards.py` con `operational_penalties`
- [ ] `default.yaml` con `oe2.operational_control`

### Después de Fase 1 (Baseline)

- [ ] `uncontrolled_diagnostics.csv` existe (8760 rows)
- [ ] Potencia pico: 170-180 kW
- [ ] Importación: 2.4-2.5 M kWh
- [ ] SOC mínimo: 20-25%

### Después de Fase 2 (Reentreno)

- [ ] Checkpoint `.zip` existe
- [ ] Logs muestran convergencia
- [ ] Sin excepciones CUDA/memoria

### Después de Fase 3 (Análisis)

- [ ] `comparison_metrics.csv` con 8+ métricas
- [ ] 3 gráficos PNG generados
- [ ] SAC mejora ≥80% de métricas vs baseline

---

## 📚 Referencias de Código

### Clase: OperationalConstraints

**Archivo**: `enriched_observables.py`

```python
@dataclass
class OperationalConstraints:
    peak_hours: List[int]
    power_limits_kw: Dict[str, float]
    bess_soc_target: Dict[str, float]
    @classmethod
    def from_config(cls, cfg: Dict) -> OperationalConstraints:
        # Carga desde default.yaml automáticamente
```

### Método: get_enriched_state()

**Archivo**: `enriched_observables.py`

```python
def get_enriched_state(self, bess_soc, pv_power_kw, ...) -> Dict:
    # Retorna 15+ observables incluyendo:
    # - is_peak_hour, is_valley_hour
    # - bess_soc_target, bess_soc_reserve_deficit
    # - ev_power_fairness_ratio
    # - pending_sessions por playa
```

### Método: compute_with_operational_penalties()

**Archivo**: `rewards.py`

```python
def compute_with_operational_penalties(
    self, 
    grid_import_kwh, ..., 
    operational_state=None
) -> Tuple[float, Dict]:
    # Retorna: (reward_total, components_dict)
    # Incluye penalizaciones por:
    # - Incumplimiento SOC target
    # - Exceso potencia en pico
    # - Desequilibrio fairness
    # - Importación alta en pico
```

---

## 🐛 Solución Rápida de Problemas

| Problema | Solución | Referencia |
|----------|----------|-----------|
| "ModuleNotFoundError" | Agregar src al PYTHONPATH | GUIA sección 3 |
| "CUDA out of memory" | Usar `--device cpu` | GUIA sección 5 |
| "Reentreno lento" | Reducir episodes en config | GUIA troubleshooting |
| "Resultados no mejoran" | Aumentar import_penalty_weight | GUIA troubleshooting |

---

## 📞 Búsqueda Rápida

**¿Cómo hago...?**

| Pregunta | Referencia |
|----------|-----------|
| Ejecutar código rápidamente | INICIO_RAPIDO_CONTROL_OPERATIVO.md |
| Entender la estrategia | PLAN_CONTROL_OPERATIVO.md |
| Paso a paso con validación | GUIA_IMPLEMENTACION_CONTROL_OPERATIVO.md |
| Ver cambios técnicos | RESUMEN_MAESTRO_CAMBIOS.md |
| Presentar a ejecutivos | RESUMEN_EJECUTIVO_CONTROL_OPERATIVO.md |

---

**Este índice versión**: 1.0  
**Fecha**: 18 enero 2026  
**Estado**: 📍 **ÍNDICE COMPLETO**

👉 **Empezar por**: [RESUMEN_EJECUTIVO_CONTROL_OPERATIVO.md](RESUMEN_EJECUTIVO_CONTROL_OPERATIVO.md)
