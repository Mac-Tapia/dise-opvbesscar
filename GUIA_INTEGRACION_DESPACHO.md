# Guía de Integración: Despacho de Prioridades en Simulador SAC

## Resumen de Cambios Necesarios

El módulo `dispatch_priorities.py` proporciona:

- ✅ Clase `EnergyDispatcher`: Motor de decisión con 5 prioridades
- ✅ Dataclasses: `DispatchState`, `DispatchPlan`, `DispatchPriorities`
- ✅ Funciones: `validate_dispatch_plan()`, `compute_dispatch_reward_bonus()`

**Sin modificar capacidades:** BESS 2000 kWh, Solar 4162 kWp, Chargers 272 kW (operativo 150 kW)

---

## Archivo: `run_oe3_simulate.py` (Script Principal)

### Cambio 1: Importar módulo de despacho

**Ubicación:** Línea ~10 (sección imports)

```python
# Imports existentes
from src.iquitos_citylearn.oe3.agents import ...
from src.iquitos_citylearn.oe3.rewards import ...

# AGREGAR:
from src.iquitos_citylearn.oe3.dispatch_priorities import (
    EnergyDispatcher, 
    DispatchState, 
    DispatchPriorities,
    validate_dispatch_plan,
    compute_dispatch_reward_bonus,
)
```

---

## Archivo: `simulate.py` (Núcleo del Simulador)

### Cambio 2: Inicializar despachador en `run_single_simulation()`

**Ubicación:** Función `run_single_simulation()`, sección inicialización (~línea 150)

```python
def run_single_simulation(env, agent, config, agent_name):
    """..."""
    
    # Inicialización existente
    timestep = 0
    episode_rewards = []
    actions_log = []
    observations_log = []
    
    # AGREGAR: Inicializar despachador
    dispatch_config = config.get("oe2", {}).get("dispatch_rules", {})
    if dispatch_config.get("enabled", False):
        dispatcher = EnergyDispatcher(
            DispatchPriorities(
                pv_night_threshold_kwh=dispatch_config.get(
                    "priority_3_bess_to_ev", {}
                ).get("pv_night_threshold_kwh", 0.1),
                pv_day_threshold_kwh=dispatch_config.get(
                    "priority_1_pv_to_ev", {}
                ).get("pv_threshold_kwh", 0.5),
                bess_soc_max_percent=dispatch_config.get(
                    "priority_2_pv_to_bess", {}
                ).get("bess_soc_max_percent", 95.0),
                bess_soc_min_percent=dispatch_config.get(
                    "priority_3_bess_to_ev", {}
                ).get("bess_soc_min_percent", 20.0),
                bess_power_max_kw=dispatch_config.get(
                    "priority_2_pv_to_bess", {}
                ).get("bess_power_max_kw", 1200.0),
                ev_power_limit_kw=dispatch_config.get(
                    "priority_1_pv_to_ev", {}
                ).get("ev_power_limit_kw", 150.0),
                mall_power_max_kw=dispatch_config.get(
                    "priority_4_bess_to_mall", {}
                ).get("mall_power_max_kw", 500.0),
            )
        )
        use_dispatch = True
    else:
        dispatcher = None
        use_dispatch = False
    
    # Continuar con resto de inicialización...
```

### Cambio 3: Integrar despacho en loop de simulación

**Ubicación:** Dentro del loop `for obs in env.reset()...` (~línea 200)

```python
    for obs in env.reset():  # Existente
        observations_log.append(obs)
        
        # ========== SECCIÓN NUEVA: EVALUACIÓN DESPACHO ==========
        if use_dispatch and dispatcher:
            # Extraer estado del ambiente para despacho
            try:
                # Obtener potencias del último step
                current_hour = int(env.time_step % 24)
                
                # PV generada: (típicamente primer building)
                pv_power_kw = obs[0].get("pv", 0) if isinstance(obs[0], dict) else 0
                
                # Demanda EV (segundo building)
                ev_demand_kw = obs[1].get("electrical_load", 0) if len(obs) > 1 and isinstance(obs[1], dict) else 0
                
                # BESS SOC
                bess_soc_percent = obs[0].get("battery_soc", 60) if isinstance(obs[0], dict) else 60
                bess_capacity_kwh = 2000  # Fijo
                
                # Mall demand (si aplica)
                mall_demand_kw = obs[0].get("facility_electric_load", 0) if isinstance(obs[0], dict) else 0
                
                # Crear estado para despachador
                dispatch_state = DispatchState(
                    hour=current_hour,
                    is_peak_hour=current_hour in [18, 19, 20, 21],
                    pv_power_kw=max(0, pv_power_kw),
                    bess_soc_percent=bess_soc_percent,
                    bess_capacity_kwh=bess_capacity_kwh,
                    bess_power_available_kw=1200,  # Potencia máxima disponible
                    ev_demand_kw=max(0, ev_demand_kw),
                    mall_demand_kw=max(0, mall_demand_kw),
                    ev_power_limit_kw=150.0,
                    bess_soc_target_percent=85.0 if 16 <= current_hour <= 17 else 60.0,
                )
                
                # Calcular plan de despacho
                dispatch_plan = dispatcher.dispatch(dispatch_state)
                
                # Validar plan
                is_valid, validation_msg = validate_dispatch_plan(
                    dispatch_plan, dispatch_state, dispatcher.priorities
                )
                
                if not is_valid:
                    logger.warning(f"T{timestep} Invalid dispatch: {validation_msg}")
                    logger.warning(f"  Plan: {dispatch_plan}")
                
                # Registrar plan para análisis post-simulación
                actions_log.append({
                    "timestep": timestep,
                    "hour": current_hour,
                    "dispatch_plan": {
                        "pv_to_ev_kw": dispatch_plan.pv_to_ev_kw,
                        "pv_to_bess_kw": dispatch_plan.pv_to_bess_kw,
                        "pv_to_mall_kw": dispatch_plan.pv_to_mall_kw,
                        "bess_to_ev_kw": dispatch_plan.bess_to_ev_kw,
                        "bess_to_mall_kw": dispatch_plan.bess_to_mall_kw,
                        "grid_import_kw": dispatch_plan.grid_import_kw,
                        "priority_sequence": dispatch_plan.priority_sequence,
                    },
                    "state": {
                        "pv_power_kw": dispatch_state.pv_power_kw,
                        "ev_demand_kw": dispatch_state.ev_demand_kw,
                        "bess_soc_percent": dispatch_state.bess_soc_percent,
                        "mall_demand_kw": dispatch_state.mall_demand_kw,
                    }
                })
                
            except Exception as e:
                logger.error(f"Error evaluating dispatch at T{timestep}: {e}")
                import traceback
                traceback.print_exc()
        
        # ========== FIN SECCIÓN DESPACHO ==========
        
        # Obtener acción del agente (existente)
        actions = agent.predict(obs, deterministic=False)
        
        # ... resto del loop (existente)
```

### Cambio 4: Incluir recompensa de despacho

**Ubicación:** Cálculo de reward (~línea 250)

```python
        # Rewards existentes
        reward = np.mean([env.reward()])  # O lo que sea el método actual
        
        # AGREGAR: Bonus de despacho
        if use_dispatch and dispatcher and 'dispatch_plan' in actions_log[-1]:
            dispatch_rewards = compute_dispatch_reward_bonus(
                dispatch_plan=dispatch_plan,
                state=dispatch_state,
                co2_factor_kg_kwh=config.get("oe3", {}).get("grid", {}).get(
                    "carbon_intensity_kg_per_kwh", 0.4521
                ),
            )
            
            # Blender: agregar bonus de despacho al reward base
            dispatch_bonus = dispatch_rewards.get("total_dispatch_reward", 0)
            reward = reward + dispatch_bonus  # O usar peso: reward + 0.1 * dispatch_bonus
            
            logger.debug(f"T{timestep} Dispatch bonus: {dispatch_bonus:.4f}")
        
        # Continuar con resto del cálculo de rewards...
```

---

## Archivo: `rewards.py` (Recompensas)

### Cambio 5: Exportar función de recompensas con despacho

**Ubicación:** Función `compute_with_operational_penalties()` ya existe

Solo verificar que esté disponible para importación:

```python
# En rewards.py, al final:
def create_dispatch_aware_rewards(
    base_reward: float,
    dispatch_plan: "DispatchPlan",
    dispatch_state: "DispatchState",
    config: Dict[str, Any],
) -> float:
    """
    Blender de reward base con bonus de despacho.
    
    Args:
        base_reward: Reward calculado por CityLearn
        dispatch_plan: Plan ejecutado
        dispatch_state: Estado en que se calculó
        config: Configuración con pesos
    
    Returns:
        Reward blendido: base + operacional_bonus
    """
    dispatch_rewards = compute_dispatch_reward_bonus(dispatch_plan, dispatch_state)
    
    weight = config.get("oe2", {}).get("dispatch_rules", {}).get(
        "reward_blend_weight", 0.1  # Peso relativo del bonus
    )
    
    return base_reward + weight * dispatch_rewards.get("total_dispatch_reward", 0)
```

---

## Archivo: `configs/default.yaml` (Configuración)

Ya actualizado con sección `dispatch_rules`. Verificar:

```yaml
oe2:
  dispatch_rules:
    enabled: true  # ← DEBE SER true para activar
    description: "Cascada de prioridades FV→EV→BESS→MALL"
    priority_1_pv_to_ev:
      enabled: true
      pv_threshold_kwh: 0.5
      ev_power_limit_kw: 150.0
    # ... resto de prioridades ...
```

---

## Checklist de Implementación

### Paso 1: Validar módulo `dispatch_priorities.py`

- [ ] Archivo creado sin errores de syntax
- [ ] Importable: `python -c "from src.iquitos_citylearn.oe3.dispatch_priorities import EnergyDispatcher"`

### Paso 2: Actualizar imports en `run_oe3_simulate.py`

- [ ] Agregar imports del módulo
- [ ] No hay conflictos con imports existentes

### Paso 3: Modificar `simulate.py`

- [ ] Agregar inicialización de despachador
- [ ] Agregar evaluación de estado y plan
- [ ] Agregar registro de despacho
- [ ] Blender de rewards funciona

### Paso 4: Verificar `rewards.py`

- [ ] Función de cálculo de bonus implementada
- [ ] Pesos configurables en YAML

### Paso 5: Test de integración

```bash
# 1. Verificar imports
python -c "from src.iquitos_citylearn.oe3.dispatch_priorities import *; print('✓ Imports OK')"

# 2. Verificar configuración
python -c "import yaml; cfg = yaml.safe_load(open('configs/default.yaml')); print(cfg['oe2']['dispatch_rules']['enabled'])"

# 3. Test básico (crear estado dummy y calcular despacho)
python -c "
from src.iquitos_citylearn.oe3.dispatch_priorities import EnergyDispatcher, DispatchState
d = EnergyDispatcher()
s = DispatchState(hour=18, is_peak_hour=True, pv_power_kw=100, 
                  bess_soc_percent=85, bess_capacity_kwh=2000, 
                  bess_power_available_kw=1200, ev_demand_kw=120, mall_demand_kw=300)
plan = d.dispatch(s)
print(f'✓ Despacho calculado: {plan.priority_sequence}')
"
```

### Paso 6: Ejecutar simulación con despacho

```bash
# Con despacho habilitado
python -m scripts.run_oe3_simulate \
  --config configs/default.yaml \
  --agent sac \
  --experiment dispatch_test \
  --timesteps 1000 \
  --checkpoint None

# Verificar en logs:
# - "Dispatch bonus: +X.XXX" (mensajes DEBUG)
# - "dispatch_plan" en actions_log JSON
```

---

## Troubleshooting

### Error: `ModuleNotFoundError: No module named 'dispatch_priorities'`

**Solución:** Verificar estructura de directorios:

```
src/iquitos_citylearn/oe3/
├── __init__.py
├── agents/
├── dispatch_priorities.py  ← DEBE EXISTIR AQUÍ
├── rewards.py
├── simulate.py
└── ...
```

### Error: `KeyError: 'dispatch_rules'` en config

**Solución:** Asegurar `configs/default.yaml` tiene sección `oe2.dispatch_rules` con `enabled: true`

### Rewards no muestran bonus de despacho

**Solución:**

1. Verificar `use_dispatch = True` después de inicializar
2. Verificar `dispatch_plan` no es None
3. Aumentar log level: `--log-level DEBUG`

### Validación de plan falla constantemente

**Solución:**

1. Revisar límites en `DispatchPriorities` son realistas
2. Verificar `ev_demand_kw` no supera 150 kW (agregado)
3. Confirmar `bess_soc_percent` está en [20, 95]

---

## Ejemplo de Salida Esperada

**Logs durante simulación:**

```
T0042 [Hour 18, Peak] Dispatch: P1_FV→EV:100.0kW → P3_BESS→EV:50.0kW → P5_GRID:20.0kW | Bonus: +0.0075
T0043 [Hour 19, Peak] Dispatch: P3_BESS→EV:130.0kW → P5_GRID:20.0kW | Bonus: +0.0020
T0044 [Hour 20, Peak] Dispatch: P3_BESS→EV:115.0kW → P5_GRID:35.0kW | Bonus: +0.0015
```

**JSON de salida (`outputs/oe3/simulation_summary.json`):**

```json
{
  "dispatch_statistics": {
    "avg_pv_to_ev_kw": 78.5,
    "avg_grid_import_kw": 32.3,
    "peak_hour_coverage_percent": 92.5,
    "bess_cycling_efficiency": 0.94,
    "total_dispatch_bonus_reward": 1847.23
  }
}
```

---

## Pasos Siguientes

1. ✅ Implementar cambios en `simulate.py`
2. ✅ Ejecutar test de integración (paso 5)
3. ✅ Lanzar entrenamiento SAC con despacho (Fase 7)
4. ✅ Comparar vs baseline (Fase 8)

**Tiempo esperado:**

- Cambios código: 30-45 min
- Testing: 15-30 min
- Entrenamiento SAC: 5-6 h
- Análisis comparativo: 1 h
- **Total: ~7-8 h**
