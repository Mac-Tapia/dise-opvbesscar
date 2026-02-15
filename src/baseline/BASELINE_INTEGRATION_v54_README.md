# Baseline Integration para CityLearn v2 (OE2 v5.4)

Integración completa de cálculos de baseline con entrenamientos de agentes RL (SAC, PPO, A2C) usando datasets limpios y validados OE2 v5.4.

## Resumen de Cambios (2026-02-13)

### ✅ Módulos Actualizados

| Módulo | Cambios | Estado |
|--------|---------|--------|
| `baseline_calculator.py` | Reemplazado con v2 (datos reales OE2 v5.4) | ✅ ACTUALIZADO |
| `baseline_definitions.py` | Actualizado con BESS v5.4 (1,700 kWh) | ✅ ACTUALIZADO |
| `no_control.py` | Revisado (compatible con CityLearn) | ✅ COMPATIBLE |
| `baseline_simulator.py` | Revisado (compatible con CityLearn) | ✅ COMPATIBLE |
| **NUEVO** `citylearn_baseline_integration.py` | Integración con CityLearn v2 | ✅ NUEVO |
| **NUEVO** `agent_baseline_integration.py` | Integración con entrenamientos de agentes | ✅ NUEVO |
| **NUEVO** `example_agent_training_with_baseline.py` | Ejemplos de uso | ✅ NUEVO |

### 📊 Datos Utilizados (OE2 v5.4)

```
✓ Solar: pv_generation_kwh → bess_simulation_hourly.csv (8,760 horas validadas)
✓ EV demand: ev_demand_kwh → bess_simulation_hourly.csv (chargers v3 procesadas)
✓ Mall demand: mall_demand_kwh → bess_simulation_hourly.csv (limpiadas, 8,760 horas exactas)
✓ BESS: 1,700 kWh / 400 kW (eficiencia 95%)
✓ CO₂ grid: 0.4521 kg CO₂/kWh (Iquitos diesel B5, OSINERGMIN)
```

## Cálculos Base (OE2 v5.4)

### Baseline 1: CON SOLAR (4,050 kWp) - REFERENCIA PARA AGENTES RL

```
Configuración:
  - Solar PV: 4,050 kWp
  - BESS: 1,700 kWh / 400 kW (95% eficiencia)
  - Control: SIN CONTROL (uncontrolled - baseline)
  
Resultados Anuales:
  - Generación solar: ~6.2 GWh/año
  - Importación grid: ~11.7 GWh/año (EV + Mall)
  - CO₂ grid: ~5,289 kg/año (~5.3 t/año)
  - CO₂ evitado solar: ~2,722 kg/año (~2.7 t/año)
  - CO₂ neto: ~2,567 kg/año (~2.6 t/año)

→ OBJETIVO RL: Reducir este 2.6 t/año
```

### Baseline 2: SIN SOLAR (0 kWp) - PEOR CASO

```
Configuración:
  - Solar PV: 0 kWp (sin energía renovable)
  - BESS: 1,700 kWh (no hay PV para cargarla)
  - Control: SIN CONTROL
  
Resultados Anuales:
  - Generación solar: 0 kWh/año
  - Importación grid: ~13.9 GWh/año (100% carga)
  - CO₂ grid: ~6,289 kg/año (~6.3 t/año)

→ BRECHA SOLAR: 6.3 - 5.3 = 1.0 t CO₂/año (14% reducción con PV)
```

## Uso en Entrenamientos de Agentes

### 1. Compute Baselines (Antes del Entrenamiento)

```python
from src.baseline.citylearn_baseline_integration import initialize_baselines_for_training

# Compute y guardar baselines
integration = initialize_baselines_for_training()
# Outputs: outputs/baselines/{baseline_con_solar.json, baseline_sin_solar.json, ...}
```

### 2. Entrenar Agente con Tracking de Baseline

```python
from src.baseline.agent_baseline_integration import setup_agent_training_with_baselines
from stable_baselines3 import SAC
from src.citylearnv2.dataset_builder import build_citylearn_env_from_oe2

# Setup baseline integration
baseline_integration = setup_agent_training_with_baselines(
    agent_name='SAC',  # or 'PPO', 'A2C'
    output_dir='outputs/agent_training',
    baseline_dir='outputs/baselines'
)

# Build environment (usa OE2 v5.4 data automatically)
env = build_citylearn_env_from_oe2()

# Train agent normally
agent = SAC('MlpPolicy', env)
agent.learn(total_timesteps=100000)

# Register results
baseline_integration.register_training_results(
    co2_kg=7500.0,  # Agent's CO2 emissions
    grid_import_kwh=3000000.0,  # Agent's grid import
    solar_generation_kwh=6200000.0  # Solar generated
)

# Compare vs baselines → Generates report
comparison = baseline_integration.compare_and_report()
```

### 3. Wrapper Simplificado (Recomendado)

```python
from src.baseline.example_agent_training_with_baseline import AgentTrainerWithBaseline
from stable_baselines3 import SAC

# Create trainer with automatic baseline integration
trainer = AgentTrainerWithBaseline(
    agent_name='SAC',
    agent_class=SAC,
    env=env,
    training_config={
        'learning_rate': 3e-4,
        'batch_size': 256,
        'total_timesteps': 100000,
    },
    output_dir='outputs/agent_training'
)

# Train
agent = trainer.train(total_timesteps=100000)

# Evaluate and compare (all in one)
comparison = trainer.register_results_and_compare()
# → Prints comparison report
# → Saves outputs/agent_training/sac/sac_vs_baseline.json
# → Saves outputs/agent_training/sac/sac_training_log.json
```

## Estructura de Salidas

```
outputs/
├── baselines/
│   ├── baseline_con_solar.json          # CON SOLAR results
│   ├── baseline_sin_solar.json          # SIN SOLAR results
│   ├── baseline_comparison.csv          # Comparison table
│   └── baseline_summary.json           # Summary stats
│
└── agent_training/
    ├── sac/
    │   ├── sac_vs_baseline.json        # SAC vs baseline comparison
    │   └── sac_training_log.json       # Full training log
    ├── ppo/
    │   ├── ppo_vs_baseline.json
    │   └── ppo_training_log.json
    └── a2c/
        ├── a2c_vs_baseline.json
        └── a2c_training_log.json
```

## Métricas de Comparación

Para cada agente se calcula:

```json
{
  "agent": "SAC",
  "co2_improvement_pct": 25.5,              // % mejora vs CON_SOLAR
  "co2_reduction_kg": 648.0,                // kg CO2 reducidos (absoluto)
  "co2_reduction_t": 0.648,                 // t CO2 reducidos (absoluto)
  "grid_reduction_pct": 12.3,               // % reducción de importación grid
  "grid_reduction_kwh": 1440000.0,          // kWh grid import reducido
  "agent_co2_kg": 4641.0,                   // CO2 del agente (kg/año)
  "baseline_co2_kg": 5289.0,                // CO2 baseline (kg/año)
  "improvement_vs_con_solar_pct": 25.5,     // Mejora vs referencia
  "improvement_vs_sin_solar_pct": 26.1      // Mejora vs peor caso
}
```

## Integración con Entrenamientos Existentes

### En SAC, PPO, A2C Training Scripts

Agregue al inicio del entrenamiento:

```python
# At the beginning of your training script
from src.baseline.agent_baseline_integration import setup_agent_training_with_baselines

baseline_integration = setup_agent_training_with_baselines(
    agent_name='SAC',  # Adjust based on agent
    output_dir='outputs/agent_training',
    baseline_dir='outputs/baselines'
)

# ... normal training code ...

# At the end, before finishing:
baseline_integration.register_training_results(
    co2_kg=agent_evaluation_co2,
    grid_import_kwh=agent_evaluation_grid,
    solar_generation_kwh=agent_evaluation_solar
)

comparison = baseline_integration.compare_and_report()
baseline_integration.save_training_log()
```

## Verificación de Datos

### Validar que los datos están correctos

```python
from src.baseline.baseline_calculator_v2 import BaselineCalculator

calculator = BaselineCalculator()
con_solar, sin_solar = calculator.calculate_all_baselines()

print(f"CON SOLAR CO2: {con_solar['co2_t']:,.1f} t/año")
print(f"SIN SOLAR CO2: {sin_solar['co2_t']:,.1f} t/año")
print(f"Solar impact: {(sin_solar['co2_grid_kg'] - con_solar['co2_grid_kg'])/1000:.1f} t/año reduction")
```

## Troubleshooting

### Error: "BESS data not found"

```
→ Run: python src/dimensionamiento/oe2/disenobess/bess.py
→ Verify: data/oe2/bess/bess_simulation_hourly.csv exists
→ Check: Exactamente 8,760 filas (1 año completo)
```

### Error: "BESS data has X rows, expected 8,760"

```
→ Problema: Dataset incompleto o corrupto
→ Solución: Regenerar con BESS v5.4 limpio
→ Run: python src/dimensionamiento/oe2/disenobess/bess.py --clean
```

### CO2 metrics are NaN or zero

```
→ Verificar: Datos de solar/EV/mall están en bess_simulation_hourly.csv
→ Run: python -c "import pandas as pd; df = pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv'); print(df.head()); print(f'Rows: {len(df)}')"
→ Debe mostrar 8,760 filas con columnas: pv_generation_kwh, ev_demand_kwh, mall_demand_kwh
```

## Referencias

- **BESS Specification**: v5.4 (1,700 kWh / 400 kW, 95% eficiencia)
- **CO₂ Factor**: 0.4521 kg CO₂/kWh (Iquitos thermal grid, OSINERGMIN)
- **Solar Data**: PVGIS processed hourly (pv_generation_hourly_citylearn_v2.csv)
- **EV Data**: chargers_ev_ano_2024_v3.csv (19 chargers × 2 sockets = 38 actions)
- **Mall Data**: demandamallhorakwh.csv (cleaned to 8,760 hours)

## Documentación Relacionada

- `AUDITORIA_BESS_COMPLETA_2026-02-13.md` - Auditoría completa del BESS v5.4
- `data/oe2/bess/bess_simulation_hourly.csv` - Dataset principal
- `src/citylearnv2/dataset_builder/dataset_builder.py` - Construction de env CityLearn

---

**Última actualización**: 2026-02-13  
**Versión**: OE2 v5.4  
**Estado**: ✅ Completamente integrado y validado
