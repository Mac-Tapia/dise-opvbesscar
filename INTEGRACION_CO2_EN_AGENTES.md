# Integración de Reducción CO2 en Agentes RL (Fase 7-8)

**Status:** ✅ Framework listo, Integración pendiente

---

## Resumen Ejecutivo

Se ha implementado un **marco de trabajo dual-scope para reducción de emisiones CO2** que permite a los agentes RL (SAC/PPO/A2C) optimizar simultáneamente:

### Dos Tipos de Emisiones

```
DIRECTO (Scope 2):
├─ Grid import: 0.4521 kg CO2/kWh
├─ Penalidad en pico (18-21h): 2x
└─ Estrategia: Maximizar FV directo (P1)

INDIRECTO (Scope 1):
├─ BESS carga/descarga: 5% pérdida × 0.4521 kg CO2/kWh
├─ Autodescarga: ~0.1% diaria
├─ Degradación: 0.05 kg CO2/ciclo + 0.01 kg CO2/día
└─ Estrategia: Optimizar SOC y ciclos
```

### Objetivo Anual

```
Reducción: 11.28M kg (baseline) → 7.00M kg
           ↓38% vs uncontrolled

Por estrategia:
├─ Maximización solar (50%): 2.8M kg evitado
├─ Minimización grid (30%): 1.8M kg evitado
├─ Eficiencia BESS (15%): 0.9M kg evitado
└─ Reducción costo (5%): 0.3M kg evitado
```

---

## 1. Componentes Implementados

### 1.1 Módulo CO2

**Archivo:** `src/iquitos_citylearn/oe3/co2_emissions.py` (500+ líneas)

```python
from src.iquitos_citylearn.oe3.co2_emissions import (
    CO2EmissionCalculator,
    CO2EmissionFactors,
    create_co2_reward_component,
)

# Uso
calc = CO2EmissionCalculator(cfg["oe3"]["co2_emissions"])
emissions = calc.calculate_timestep_emissions(
    pv_power_kw=200,
    grid_import_kw=50,
    bess_soc=60,
    hour=19  # Pico
)

# Retorna
print(emissions.grid_import_kg)        # Scope 2
print(emissions.total_indirect_kg)     # Scope 1
print(emissions.solar_avoided_kg)      # Beneficio
```

### 1.2 Configuración

**Archivo:** `configs/default.yaml` (sección `oe3.co2_emissions`)

```yaml
oe3:
  co2_emissions:
    # Factores de emisión
    grid_import_factor_kg_kwh: 0.4521   # Iquitos grid factor
    bess_charging_efficiency: 0.95       # 5% pérdida
    
    # Degradación
    bess_cycling_co2_per_cycle: 0.05     # kg CO2/ciclo
    bess_calendar_aging_kg_per_day: 0.01 # kg CO2/día
    
    # Estrategia de reducción
    reduction_strategies:
      direct_solar_maximization:
        weight: 0.50  # Prioridad P1
      grid_import_minimization:
        weight: 0.30  # Penalidad en pico 2x
      bess_efficiency_optimization:
        weight: 0.15  # Ciclos óptimos
      cost_reduction:
        weight: 0.05  # Colateral
    
    # Target anual
    annual_co2_budget_kg: 7000000  # 7M kg
    
    # Componentes de reward
    reward_components:
      base_weight: 0.80           # CityLearn base
      co2_direct_weight: 0.12     # Scope 2
      co2_indirect_weight: 0.08   # Scope 1
```

### 1.3 Documentación

**Archivo:** `CO2_REDUCTION_DIRECTA_INDIRECTA.md` (10 secciones)

- Explicación Scope 1 vs 2
- Estrategias por agente
- Arquitectura de rewards blendidos
- Integración en SAC/PPO/A2C
- Monitoreo y reportes
- Parámetros configurables

---

## 2. Pendiente: Integración en Pipeline

### 2.1 Integración en `rewards.py`

```python
# En src/iquitos_citylearn/oe3/rewards.py

from src.iquitos_citylearn.oe3.co2_emissions import CO2EmissionCalculator

class EnrichedReward:
    def __init__(self, cfg):
        self.co2_calc = CO2EmissionCalculator(cfg["oe3"]["co2_emissions"])
        self.co2_weights = cfg["oe3"]["co2_emissions"]["reward_components"]
    
    def compute(self, obs, reward_base):
        """Blendear reward base con CO2"""
        
        # Extraer señales CO2-relevantes
        grid_import = obs.get('grid_import_kw', 0)
        pv_available = obs.get('pv_kw', 0)
        bess_soc = obs.get('battery_soc', 60)
        hour = obs.get('hour', 12)
        
        # Calcular emisiones
        emissions = self.co2_calc.calculate_timestep_emissions(
            pv_power=pv_available,
            grid_import=grid_import,
            bess_soc=bess_soc,
            hour=hour
        )
        
        # Normalizar y convertir a reward
        r_direct = -emissions.grid_import_kg / 100  # Normalize
        r_indirect = -emissions.total_indirect_kg / 100
        
        # Blendear
        r_total = (
            self.co2_weights['base_weight'] * reward_base +
            self.co2_weights['co2_direct_weight'] * r_direct +
            self.co2_weights['co2_indirect_weight'] * r_indirect
        )
        
        return r_total
```

### 2.2 Integración en `simulate.py`

```python
# En src/iquitos_citylearn/oe3/simulate.py

# Agregar tracking de CO2
co2_calc = CO2EmissionCalculator(cfg["oe3"]["co2_emissions"])

for episode in range(episodes):
    obs = env.reset()
    co2_emissions_episode = []
    
    for step in range(8760):
        action = agent.predict(obs)[0]
        obs, reward, done, info = env.step(action)
        
        # Calcular CO2
        emissions = co2_calc.calculate_timestep_emissions(
            pv_power=info.get('pv_kw', 0),
            grid_import=info.get('grid_import_kw', 0),
            bess_soc=info.get('battery_soc', 60),
            hour=step % 24
        )
        
        co2_emissions_episode.append({
            'step': step,
            'direct_kg': emissions.grid_import_kg,
            'indirect_kg': emissions.total_indirect_kg,
        })
        
        if done:
            break
    
    # Reportar CO2 por episodio
    annual_co2 = sum(e['direct_kg'] + e['indirect_kg'] 
                     for e in co2_emissions_episode)
    print(f"Episode {episode}: Annual CO2 = {annual_co2:.0f} kg")
```

### 2.3 Integración en Agentes (SAC)

```python
# En src/iquitos_citylearn/oe3/agents/sac.py

class SACAgent:
    def __init__(self, cfg):
        # ... código existente ...
        self.co2_enabled = cfg.get("oe3", {}).get("co2_emissions", {}).get("enabled", True)
        if self.co2_enabled:
            from src.iquitos_citylearn.oe3.co2_emissions import CO2EmissionCalculator
            self.co2_calc = CO2EmissionCalculator(
                cfg["oe3"]["co2_emissions"]
            )
    
    def compute_reward_with_co2(self, reward_base, obs, info, hour):
        """Blend base reward with CO2 objectives"""
        if not self.co2_enabled:
            return reward_base
        
        emissions = self.co2_calc.calculate_timestep_emissions(
            pv_power=obs.get('pv_kw', 0),
            grid_import=obs.get('grid_import_kw', 0),
            bess_soc=obs.get('battery_soc', 60),
            hour=hour
        )
        
        # CO2 penalty (negative reward)
        co2_direct = -0.12 * (emissions.grid_import_kg / 100)
        co2_indirect = -0.08 * (emissions.total_indirect_kg / 100)
        
        return reward_base + co2_direct + co2_indirect
```

---

## 3. Checklist de Implementación (Fase 7-8)

### Fase 7: Integración en Pipeline

- [ ] Actualizar `rewards.py` con `EnrichedReward` + CO2
- [ ] Actualizar `simulate.py` para tracer CO2 por timestep
- [ ] Actualizar `agents/sac.py` para blendear CO2 en reward
- [ ] Actualizar `agents/ppo.py` para soporte CO2
- [ ] Actualizar `agents/a2c.py` para soporte CO2
- [ ] Tests: Verificar que reward blendido está en rango [-1, 1]

### Fase 8: Training & Validación

- [ ] Ejecutar `run_oe3_simulate.py` con `co2_enabled: true`
- [ ] Monitorear: Annual CO2 debe bajar semana a semana
- [ ] Extraer reportes: `outputs/oe3/simulation_summary.json`
- [ ] Comparar: SAC + CO2 vs SAC base (deben ser ~7% mejor)
- [ ] Validar: 38% reducción vs baseline uncontrolled
- [ ] Documentar: Resultados en `RESULTADOS_FASE_8.md`

---

## 4. Métricas de Éxito

### Baseline (Sin control PV/BESS)

```
Emisiones CO2 anual: 11.28M kg
Grid import: 58% del total
BESS ciclos/año: 250
```

### SAC Base (Sin optimización CO2)

```
Emisiones CO2 anual: 7.55M kg (-33% vs baseline)
Grid import: 42% del total
BESS ciclos/año: 210
```

### SAC + CO2 (Objetivo)

```
Emisiones CO2 anual: 7.00M kg (-38% vs baseline, -7% vs SAC base)
Grid import: 38% del total (otro -4%)
BESS ciclos/año: 190 (otro -10% ciclado)
```

---

## 5. Comandos de Ejecución (Fase 7-8)

### Integración

```bash
# Después de aplicar cambios
python -c "import src.iquitos_citylearn.oe3.co2_emissions; print('✅ CO2 module OK')"
```

### Training con CO2

```bash
# Habilitar CO2 en config
python -m scripts.run_oe3_simulate --config configs/default.yaml

# Monitoreo en tiempo real
python monitor_checkpoints.py

# Reanudar si se interrumpe
python -m scripts.continue_sac_training --config configs/default.yaml
```

### Validación

```bash
# Generar reportes CO2
python -m scripts.run_oe3_co2_table --config configs/default.yaml

# Comparar vs baseline
python scripts/compare_baseline_vs_retrain.py
```

---

## 6. Referencias Técnicas

### Normativa

- ISO 14064: Greenhouse gases accounting
- Scope 1: Emisiones indirectas (BESS)
- Scope 2: Emisiones directas (grid import)

### Factores Iquitos

- Grid emission factor: **0.4521 kg CO2/kWh** (grid térmico)
- Peak hour penalty: **2x** (18-21h)
- BESS efficiency: **95%** (5% pérdida por ciclo)

### Papers de Referencia

- SAC + Multi-Objective RL
- EV Charging + Grid Integration
- BESS Lifecycle Assessment

---

## 7. Notas de Implementación

### Importante: Dispatch Priorities NO cambia

```
Despacho sigue siendo P1 → P5:
P1: FV → EV directo (solar)
P2: FV → BESS
P3: BESS → EV (pico)
P4: Grid → BESS (reserva)
P5: Grid → EV (último recurso)

CO2 es REWARD layer, no dispatch layer
Dispatch decide QUÉ, CO2 reward decide CUÁNTO
```

### BESS Capacity Constrainer

```
2000 kWh fijo, NO CAMBIA
├─ Normal (0-15h, 22-23h): SOC ≥ 60% (1200 kWh)
├─ Pre-pico (16-17h): SOC ≥ 85% (1700 kWh)
└─ Pico (18-21h): SOC ≥ 40% (800 kWh)

CO2 layer RESPETA estos constraints
```

---

## 8. Troubleshooting

### Problema: CO2 no baja en training

**Causas posibles:**

1. `co2_weight` muy bajo (aumentar de 0.08 a 0.15)
2. Grid factor mal calibrado (verificar vs COES)
3. Reward clipping [-1, 1] saturando (debug blending)

**Solución:**

```yaml
# En configs/default.yaml
oe3:
  co2_emissions:
    reward_components:
      co2_direct_weight: 0.15   # Aumentar de 0.12
      co2_indirect_weight: 0.12  # Aumentar de 0.08
```

### Problema: Training más lento

**Causa:** CO2 calc es O(1) por step pero suma a overhead

**Solución:** Hacer calc cada 10 steps

```python
if step % 10 == 0:
    emissions = co2_calc.calculate_timestep_emissions(...)
else:
    emissions = last_emissions  # Interpolar
```

---

## 9. Archivos Clave Creados

| Archivo | Líneas | Status |
| --- | --- | --- |
| `co2_emissions.py` | 500+ | ✅ Listo |
| `CO2_REDUCTION_DIRECTA_INDIRECTA.md` | 400+ | ✅ Listo |
| `configs/default.yaml` (+oe3.co2_emissions) | +80 | ✅ Listo |
| `rewards.py` (integración pendiente) | - | ⏳ TODO |
| `simulate.py` (integración pendiente) | - | ⏳ TODO |

---

**Última actualización:** 2025-01-09
**Próxima fase:** Fase 7 (Integración en rewards.py + simulate.py)
**Estimado:** 2-4 horas para integración + validación
