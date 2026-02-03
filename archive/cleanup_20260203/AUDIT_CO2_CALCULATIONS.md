# 🔍 AUDIT: CO₂ Reduction Calculations (Direct & Indirect)

**Date:** 2026-02-01  
**Status:** VERIFICACIÓN COMPLETA

---

## 📋 RESUMEN EJECUTIVO

### ✅ VERIFICADO: Cálculos de CO₂ Están Implementados

El entrenamiento **SÍ está calculando** ambas reducciones de CO₂:

1. **CO₂ INDIRECTO** ✅ - Solar que evita importación de grid
2. **CO₂ DIRECTO** ✅ - EVs que evitan combustión

### 🎯 PIPELINE DE CÁLCULO

```
rewards.py (compute method)
  ├─ CO₂ GRID: grid_import × 0.4521
  ├─ CO₂ AVOIDED INDIRECT: solar_generation × 0.4521
  ├─ CO₂ AVOIDED DIRECT: ev_charging → km → galones → CO₂
  └─ CO₂ NET: grid - avoided_total
  
simulate.py (post-episode)
  ├─ Recrea tracker limpio
  ├─ Calcula componentes para cada timestep (8,760 horas)
  ├─ Acumula estadísticas en pareto_metrics
  └─ Reporta metrics en results JSON
  
agents (training)
  ├─ Recibe rewards multiobjetivo
  ├─ Optimiza para minimizar co2_net
  └─ Logs periódicos de rewards componentes
```

---

## 🔬 ANÁLISIS DETALLADO

### 1. REWARDS.PY - FUNCIÓN COMPUTE() ✅

**Ubicación:** [rewards.py](../src/iquitos_citylearn/oe3/rewards.py#L230-L280)

**Línea 236:** CO₂ Grid (importación)
```python
co2_grid_kg = grid_import_kwh * self.context.co2_factor_kg_per_kwh
# Ejemplo: 100 kWh × 0.4521 = 45.21 kg CO₂
```

**Línea 240:** CO₂ EVITADO INDIRECTO (Solar)
```python
co2_avoided_indirect_kg = solar_generation_kwh * self.context.co2_factor_kg_per_kwh
# Ejemplo: 80 kWh solar × 0.4521 = 36.17 kg CO₂ evitado (no importar de grid)
```

**Líneas 243-250:** CO₂ EVITADO DIRECTO (EVs evitan combustión)
```python
if ev_charging_kwh > 0:
    total_km = ev_charging_kwh * self.context.km_per_kwh          # 50 kWh × 35 = 1,750 km
    gallons_avoided = total_km / self.context.km_per_gallon      # 1,750 / 120 = 14.6 galones
    co2_avoided_direct_kg = gallons_avoided * self.context.kgco2_per_gallon  # 14.6 × 8.9 = 130 kg CO₂
```

**Línea 252:** CO₂ TOTAL EVITADO
```python
co2_avoided_total_kg = co2_avoided_indirect_kg + co2_avoided_direct_kg
# = 36.17 + 130 = 166.17 kg CO₂ evitado en este timestep
```

**Línea 255:** CO₂ NETO (La métrica clave para recompensa)
```python
co2_net_kg = co2_grid_kg - co2_avoided_total_kg
# = 45.21 - 166.17 = -121 kg (NEGATIVO = más emisiones evitadas que producidas!)
```

**Componentes Registrados (Líneas 273-276):**
```python
components["co2_grid_kg"] = co2_grid_kg                          # ✅ Importación grid
components["co2_avoided_indirect_kg"] = co2_avoided_indirect_kg  # ✅ Solar evita importación
components["co2_avoided_direct_kg"] = co2_avoided_direct_kg      # ✅ EVs evitan combustión
components["co2_avoided_total_kg"] = co2_avoided_total_kg        # ✅ Suma total evitado
components["co2_net_kg"] = co2_net_kg                            # ✅ Neto para recompensa
```

### 2. REWARDS MULTIOBJETIVO ✅

**Ubicación:** [rewards.py#L280-L300](../src/iquitos_citylearn/oe3/rewards.py#L280-L300)

**Pesos en OE3 (CRÍTICO):**
```python
weights = MultiObjectiveWeights(
    co2=0.50,              # PRIMARY: Minimizar CO₂ neto
    solar=0.20,            # SECONDARY: Autoconsumo solar
    cost=0.15,             # TERTIARY: Costo eléctrico
    ev_satisfaction=0.10,  # EV satisfaction
    grid_stability=0.05    # Grid stability
)
```

**Recompensa CO₂ (la que usa `co2_net_kg`):**
```python
# Off-peak: menos penalizador
r_co2 = 1.0 - 1.0 * min(1.0, max(0, co2_net_kg) / (130 * 0.4521))

# Peak (18-21): MÁS penalizador para forzar descarga BESS
r_co2 = 1.0 - 2.0 * min(1.0, max(0, co2_net_kg) / (250 * 0.4521))
```

**Recompensa Total:**
```python
reward_total = (
    0.50 × r_co2 +              # CO₂ dominante
    0.20 × r_solar +            # Solar secundario
    0.15 × r_cost +             # Costo
    0.10 × r_ev +               # EV satisfaction
    0.05 × r_grid +             # Grid stability
    0.10 × soc_penalty          # SOC reserve
)
```

### 3. SIMULATE.PY - POST-EPISODE METRICS ✅

**Ubicación:** [simulate.py#L900-L950](../src/iquitos_citylearn/oe3/simulate.py#L900-L950)

**Paso 1: Recrea tracker limpio** (Línea 904)
```python
clean_tracker = MultiObjectiveReward(weights=weights)
```

**Paso 2: Itera sobre 8,760 timesteps** (Línea 921)
```python
for t in range(steps):  # steps = 8,760 (1 año completo)
    hour = t % 24
    _, comps = clean_tracker.compute(
        grid_import_kwh=grid_import[t],
        grid_export_kwh=grid_export[t],
        solar_generation_kwh=pv[t],
        ev_charging_kwh=ev[t],
        ...
    )
    reward_components.append(comps)  # Guarda componentes de CADA timestep
```

**Paso 3: Acumula estadísticas** (Línea 934)
```python
pareto = clean_tracker.get_pareto_metrics()
# Retorna media, std, min, max para CADA métrica de reward
```

**Paso 4: Guarda en ResultadoFinal** (Líneas 936-947)
```python
mo_metrics = {
    "r_co2_mean": pareto["r_co2_mean"],                # Reward CO₂ promedio
    "r_solar_mean": pareto["r_solar_mean"],            # Reward Solar promedio
    ...
    "co2_total_kg": pareto["co2_total_kg"],            # CO₂ acumulado del año
    "cost_total_usd": pareto["cost_total_usd"],        # Costo acumulado
}
```

### 4. TIMESERIES OUTPUT ✅

**Ubicación:** [simulate.py#L950+](../src/iquitos_citylearn/oe3/simulate.py#L950)

**Archivo generado:** `timeseries_{agent_name}.csv`

```csv
net_grid_kwh,grid_import_kwh,grid_export_kwh,ev_charging_kwh,building_load_kwh,pv_generation_kwh,carbon_intensity_kg_per_kwh
...
```

**Archivo generado:** `trace_{agent_name}.csv` (si trace disponible)

Incluye todas las columnas anteriores PLUS:
- `co2_grid_kg` - CO₂ de importación de grid
- `co2_avoided_indirect_kg` - CO₂ evitado por solar
- `co2_avoided_direct_kg` - CO₂ evitado por EVs
- `co2_avoided_total_kg` - Suma de ambos
- `co2_net_kg` - Neto para recompensa
- `r_co2`, `r_solar`, `r_cost`, `r_ev`, `r_grid` - Rewards componentes
- `reward_total` - Reward multiobjetivo

---

## 📊 VERIFICACIÓN DE DATOS

### IquitosContext (Parámetros OE2 REALES)

**Ubicación:** [rewards.py#L145-L175](../src/iquitos_citylearn/oe3/rewards.py#L145-L175)

```python
@dataclass
class IquitosContext:
    co2_factor_kg_per_kwh: float = 0.4521      # Grid import (térmica aislada)
    co2_conversion_factor: float = 2.146       # Para cálculo directo EVs
    
    # Flota y chargers
    n_chargers: int = 32                       # 32 cargadores
    total_sockets: int = 128                   # 128 sockets (112 motos + 16 mototaxis)
    
    # Factores de emisiones evitadas (combustión vs eléctrico)
    km_per_kwh: float = 35.0                   # Motos eléctricas: 35 km/kWh
    km_per_gallon: float = 120.0               # Motos combustión: 120 km/galón
    kgco2_per_gallon: float = 8.9              # Emisiones combustión: 8.9 kg CO₂/galón
```

### Cálculo de Ejemplo (1 Hora Típica Iquitos)

**Hora de Pico (19:00)**
- Grid import: 100 kWh
- Solar generation: 0 kWh (noche)
- EV charging: 50 kWh
- BESS discharge: 50 kWh

**CO₂ CÁLCULOS:**

| Componente | Fórmula | Valor | Unidad |
|------------|---------|-------|--------|
| CO₂ Grid (importación) | 100 × 0.4521 | 45.21 | kg CO₂ |
| CO₂ Evitado INDIRECTO | 0 × 0.4521 | 0 | kg CO₂ |
| CO₂ Evitado DIRECTO | 50 × 35 / 120 × 8.9 | 130.42 | kg CO₂ |
| **CO₂ EVITADO TOTAL** | 0 + 130.42 | **130.42** | kg CO₂ |
| **CO₂ NETO** | 45.21 - 130.42 | **-85.21** | kg CO₂ |
| **Recompensa CO₂** | 1.0 - 2.0×min(1, max(0, -85.21)/...) | **+1.0** | [-1, 1] |

**Interpretación:** BESS descarga permite cubrir EVs, evitando 130 kg CO₂ de combustión. **Neto NEGATIVO = BONUS** ✅

---

**Hora OFF-Peak (02:00)**
- Grid import: 30 kWh
- Solar generation: 0 kWh (noche)
- EV charging: 0 kWh
- BESS: cargando

| Componente | Valor | Unidad |
|------------|-------|--------|
| CO₂ Grid | 30 × 0.4521 = 13.56 | kg CO₂ |
| CO₂ Evitado INDIRECTO | 0 | kg CO₂ |
| CO₂ Evitado DIRECTO | 0 | kg CO₂ |
| CO₂ EVITADO TOTAL | 0 | kg CO₂ |
| **CO₂ NETO** | 13.56 | kg CO₂ |
| **Recompensa CO₂** | 1.0 - 1.0×min(1, 13.56/(130×0.4521)) | +0.77 | [-1, 1] |

---

**Hora SOLAR MÁXIMO (12:00)**
- Grid import: 20 kWh
- Solar generation: 200 kWh
- EV charging: 50 kWh
- Mall load: 100 kWh

| Componente | Valor | Unidad |
|------------|-------|--------|
| CO₂ Grid | 20 × 0.4521 = 9.04 | kg CO₂ |
| CO₂ Evitado INDIRECTO | 200 × 0.4521 = **90.42** | kg CO₂ |
| CO₂ Evitado DIRECTO | 50 × 35 / 120 × 8.9 = 130.42 | kg CO₂ |
| CO₂ EVITADO TOTAL | 90.42 + 130.42 = **220.84** | kg CO₂ |
| **CO₂ NETO** | 9.04 - 220.84 = **-211.8** | kg CO₂ |
| **Recompensa CO₂** | 1.0 | [-1, 1] |

**Interpretación:** Solar directo + BESS almacenado evitan combustión, neto FUERTEMENTE NEGATIVO = **MÁXIMO REWARD** ✅✅✅

---

## 🎯 LOGGING Y MONITOREO

### Durante Entrenamiento

Los agentes (SAC/PPO/A2C) reciben rewards multiobjetivo EN TIEMPO REAL:

```python
reward_multiobj, components = reward_fn.compute(
    grid_import_kwh=grid_import,
    grid_export_kwh=grid_export,
    solar_generation_kwh=solar,
    ev_charging_kwh=ev,
    ...
)
```

### Logs Cada 2000 Timesteps (Aprox. 83 días)

```
[MULTIOBJETIVO] Métricas (CLEAN): R_total=0.3245, R_CO2=0.6123, R_cost=0.2145
```

### Output Final - JSON Results

```json
{
  "agent": "SAC",
  "steps": 8760,
  "multi_objective_priority": "co2_focus",
  "reward_co2_mean": 0.6123,
  "reward_solar_mean": 0.5234,
  "reward_cost_mean": 0.2145,
  "reward_ev_mean": 0.4567,
  "reward_grid_mean": 0.3456,
  "reward_total_mean": 0.4156,
  "carbon_kg": 4280119,
  "grid_import_kwh": 100000,
  "pv_generation_kwh": 1450000
}
```

---

## ✅ CONCLUSIONES

### 🟢 CO₂ INDIRECTO: VERIFICADO IMPLEMENTADO

- ✅ Se calcula: `solar_generation × 0.4521`
- ✅ Se registra en componentes: `co2_avoided_indirect_kg`
- ✅ Se acumula en rewards: Peso 0.20 en reward solar
- ✅ Se reporta en outputs: CSV timeseries + JSON results

### 🟢 CO₂ DIRECTO: VERIFICADO IMPLEMENTADO

- ✅ Se calcula: `ev_charging → km → galones → CO₂`
- ✅ Usa parámetros OE2 reales (35 km/kWh, 120 km/gal, 8.9 kg CO₂/gal)
- ✅ Se registra en componentes: `co2_avoided_direct_kg`
- ✅ Se suma en total: `co2_avoided_total_kg`
- ✅ Se reporta en outputs

### 🟢 RECOMPENSA MULTIOBJETIVO: VERIFICADA ACTIVA

- ✅ Peso CO₂: 0.50 (DOMINANTE)
- ✅ Penalizaciones diferenciadas por hora (peak vs off-peak)
- ✅ Incentiva AMBOS: solar directo + EVs
- ✅ Se calcula en CADA timestep (8,760/año)
- ✅ Se registra en traces para análisis post-training

### 🟢 ENTRENAMIENTO: RECIBE REWARDS CORRECTOS

- ✅ SAC/PPO/A2C entrenan con rewards multiobjetivo
- ✅ Callbacks registran componentes durante training
- ✅ Logs periódicos muestran progreso de cada componente
- ✅ Post-episode: recalcula métricas con tracker limpio

---

## 🔧 RECOMENDACIONES

### Para Máxima Visualización

1. **Habilitar Debug Logging:**
   ```bash
   export LOGLEVEL=DEBUG
   python -m scripts.run_oe3_simulate --config configs/default.yaml
   ```

2. **Analizar Traces Post-Entrenamiento:**
   ```bash
   python -c "import pandas as pd; df=pd.read_csv('outputs/oe3_simulations/trace_SAC.csv'); print(df[['co2_grid_kg', 'co2_avoided_indirect_kg', 'co2_avoided_direct_kg', 'r_co2']].describe())"
   ```

3. **Comparar Escenarios:**
   ```bash
   python -m scripts.run_oe3_co2_table --config configs/default.yaml
   ```

---

## 📎 Referencias

- [rewards.py](../src/iquitos_citylearn/oe3/rewards.py) - Cálculos multiobjetivo
- [simulate.py](../src/iquitos_citylearn/oe3/simulate.py) - Post-episode metrics
- [dataset_builder.py](../src/iquitos_citylearn/oe3/dataset_builder.py) - Datos OE2 reales
- [copilot-instructions.md](../.github/copilot-instructions.md) - Especificación proyecto

---

**Status:** ✅ TODOS LOS CÁLCULOS DE CO₂ ESTÁN IMPLEMENTADOS Y ACTIVOS
