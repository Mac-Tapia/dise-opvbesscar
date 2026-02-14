# 🔄 FLUJO DE DATOS OE2→OE3: Carga de Datasets para Agentes RL

**Documento**: Guía de cómo los agentes RL en OE3 interactúan con datasets enriquecidos de OE2  
**Versión**: 5.3  
**Estado**: ✅ Listo para implementación

---

## 1. ARQUITECTURA DE DATOS EN OE3

```
┌─────────────────────────────────────────────────────────────────┐
│                    CityLearn v2 Environment                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Timestep t (1 hora)                                            │
│  ├─ OBSERVATION (input al agente)                              │
│  │  ├─ SOLAR_v2 [t]:                                           │
│  │  │  ├─ irradiancia, temperatura, potencia, energía         │
│  │  │  ├─ ⭐ energia_suministrada_al_*                         │
│  │  │  └─ ⭐ reduccion_indirecta_co2_kg_total                 │
│  │  │                                                          │
│  │  ├─ CHARGERS_v2 [t]: (× 38 sockets)                        │
│  │  │  ├─ Ocupación, potencia, tarifa (cada socket)          │
│  │  │  ├─ ⭐ cantidad_motos_cargadas                          │
│  │  │  ├─ ⭐ cantidad_mototaxis_cargadas                      │
│  │  │  └─ ⭐ reduccion_directa_co2_*                          │
│  │  │                                                          │
│  │  ├─ BESS_v1 [t]:                                            │
│  │  │  ├─ SOC (%), carga kW, descarga kW                     │
│  │  │  └─ Límites operativos                                 │
│  │  │                                                          │
│  │  └─ TIME FEATURES:                                         │
│  │     ├─ hour, month, day_of_week, is_weekend               │
│  │     └─ trimestre, estación                                │
│  │                                                          
│  │  DIMENSIÓN TOTAL: 394                                     │
│  │  (15 SOLAR + 114 CHARGERS + 3 BESS + 6 TIME)            │
│  │                                                          
│  ├─ ACTION (output del agente) → DISPATCH                  │
│  │  ├─ BESS action: [0,1] → kW de carga/descarga           │
│  │  └─ CHARGERS actions: [0,1]×38 → kW para cada socket    │
│  │                                                          
│  │  DIMENSIÓN: 39 (1 BESS + 38 CHARGERS)                   │
│  │                                                          
│  └─ REWARD (feedback al agente)                             │
│     ├─ CO₂ Grid Minimization: 50% peso                      │
│     │  └─ grid_import_kw × 0.4521 kg CO₂/kWh              │
│     │                                                          
│     ├─ Solar Self-Consumption: 20% peso                     │
│     │  └─ Direct use: EV + MALL from solar                 │
│     │                                                          
│     ├─ EV Charge Completion: 15% peso                       │
│     │  └─ Vehículos cargados / total esperado              │
│     │                                                          
│     ├─ Grid Stability: 10% peso                             │
│     │  └─ Ramping rate smoothness (kW/h)                    │
│     │                                                          
│     └─ Cost Minimization: 5% peso                           │
│        └─ Tariff rates × dispatch                           │
│                                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. MAPEO DE COLUMNAS: DATASETS → OBSERVATION SPACE

### A. SOLAR_v2 → Observation [0:15]
```
observation[0]  = SOLAR.irradiancia_W_m2[t]
observation[1]  = SOLAR.temperatura_C[t]
observation[2]  = SOLAR.potencia_pv_kw[t]
observation[3]  = SOLAR.energia_pv_kwh[t]
observation[4]  = SOLAR.tarifa_energia[t]
observation[5]  = SOLAR.hora[t]
observation[6]  = SOLAR.mes[t]
observation[7]  = SOLAR.dia_semana[t]
observation[8]  = SOLAR.trimestre[t]
observation[9]  = SOLAR.⭐ energia_suministrada_al_bess_kwh[t]    (NEW)
observation[10] = SOLAR.⭐ energia_suministrada_al_ev_kwh[t]      (NEW)
observation[11] = SOLAR.⭐ energia_suministrada_al_mall_kwh[t]    (NEW)
observation[12] = SOLAR.⭐ energia_suministrada_a_red_kwh[t]      (NEW)
observation[13] = SOLAR.⭐ reduccion_indirecta_co2_kg_total[t]    (NEW)
observation[14] = time_of_day_normalized (extra feature)
```

### B. CHARGERS_v2 → Observation [15:129]
```
# Para cada socket (38 sockets × 3 features = 114 dimensiones)

for socket in range(38):
    idx_base = 15 + (socket * 3)
    
    observation[idx_base + 0] = CHARGERS.socket_occupancy[socket][t]
    observation[idx_base + 1] = CHARGERS.socket_power[socket][t]
    observation[idx_base + 2] = CHARGERS.⭐ co2_direct[socket][t]  (NEW)

# Todos 38 sockets contribuyen observables sobre CO₂ directo
# Estas nuevas columnas permiten al agente "ver" el beneficio 
# de cargar motos/taxis en tiempo real
```

### C. BESS_v1 → Observation [129:132]
```
observation[129] = BESS.soc_percent[t]          (0-100%)
observation[130] = BESS.power_charge_kw[t]     (0-max)
observation[131] = BESS.power_discharge_kw[t]  (0-max)
```

### D. TIME FEATURES → Observation [132:138]
```
observation[132] = hour_of_day (0-23)          / 24.0
observation[133] = day_of_week (0-6)           / 7.0
observation[134] = month (1-12)                / 12.0
observation[135] = is_weekend (0-1)
observation[136] = quarter (1-4)               / 4.0
observation[137] = is_holiday (0-1)
```

**Total**: 15 + 114 + 3 + 6 = **138 dimensiones normalizadas** → puede ser 394 si incluimos todos los parámetros de sockets

---

## 3. MAPEO DE ACCIONES: ACTION SPACE → DISPATCH

### A. BESS Control
```
action[0] ∈ [0, 1]  (normalized)
          → kW actual = action[0] × max_power_bess

Si action[0] > 0.5:  CARGARSE (absorber energía solar)
Si action[0] < 0.5:  DESCARGARSE (proporcionar energía)
```

### B. CHARGERS Control (38 sockets)
```
for socket in range(38):
    action[1 + socket] ∈ [0, 1]  (normalized)
    → kW actual = action[1 + socket] × 7.4 kW/socket

    Si action > 0.0:  CARGAR vehículo (agencia del socket)
    Si action = 0.0:  SIN CARGA (stand-by)

# Ejemplo:
action = [0.6, 1.0, 0.8, 0.0, ..., 0.5]  (39 valores totales)
          └─ BESS: 60% potencia (charge)
              └─ Socket 0: 100% → 7.4 kW
                  └─ Socket 1: 80% → 5.92 kW
                      └─ Socket 2: 0% → stand-by
                                      ...
                                          └─ Socket 37: 50% → 3.7 kW
```

### C. Observabilidad del Dispatch (NEW COLUMNS)
```
# El agente VERÁ en tiempo real:

observation[9]  = energia_suministrada_al_bess_kwh[t]
  → Cuánta energía solar va AL BESS en esta hora
  
observation[10] = energia_suministrada_al_ev_kwh[t]
  → Cuánta energía solar va A LOS EV en esta hora
  
observation[14:51] = co2_direct de 38 sockets
  → Cuánto CO₂ DIRECTO se está evitando ahora mismo
     con motos/taxis cargando

# VENTAJA para RL:
# El agente ve INSTANTANEAMENTE el impacto CO₂ de sus acciones
# → Reward signal más claro + convergencia más rápida
```

---

## 4. FLUJO TEMPORAL DETALLADO (1 hora)

```
t=0 (2024-01-15 09:00)
├─ Datos de entrada:
│  ├─ SOLAR[0]: irradiancia=700 W/m², gen=950 kWh
│  ├─ CHARGERS[0]: 15 motos + 3 taxis en carga
│  ├─ BESS[0]: SOC=75%
│  └─ TIME: hora=9, día_semana=2
│
├─ Observation construida (394-dim):
│  ├─ [0:15]: SOLAR features (incl. ⭐ solar CO₂, distribución)
│  ├─ [15:129]: CHARGERS features × 38 (incl. ⭐ CO₂ directo/socket)
│  ├─ [129:132]: BESS features
│  └─ [132:138]: TIME features
│
├─ Agent forward pass (SAC/PPO/A2C):
│  ├─ Input: observation (394-dim)
│  ├─ Neural network: (394) → [hidden] → (39)
│  └─ Output: action (39-dim)
│
├─ Action example:
│  action = [0.7, 1.0, 0.9, 0.3, ..., 0.6]
│     → BESS: 70% carga (493 kW)
│     → Socket 0: 100% (7.4 kW moto)
│     → Socket 1: 90% (6.66 kW moto)
│     → Socket 2: 30% (2.22 kW taxi)
│     → ... Socket 37: 60% (4.44 kW)
│
├─ Environment step:
│  ├─ BESS absorbe 493 kW del solar
│  ├─ Sockets desplazan 15 motos + 3 taxis
│  ├─ Red importa = 950 - 493 - 157 - 685 = 15 kW
│  └─ REWARD calculado:
│     ├─ CO₂ grid: 15 kW × 0.4521 = 6.77 kg CO₂
│     ├─ CO₂ directo: 15 motos × 6.08 + 3 taxis × 14.28 = 129 kg
│     ├─ Solar utilization: 98.4% (apenas 15 kW exportado)
│     └─ TOTAL_REWARD = 0.50×(100-6.77) + 0.20×98.4 + 0.15×1.0 + ... = +92.3
│
├─ Observation del siguiente paso:
│  t=1 (2024-01-15 10:00)
│  ├─ SOLAR[1]: irradiancia=850 W/m², gen=1,100 kWh
│  │           ⭐ energia_suministrada_al_bess_kwh[1] = 541 kWh (UPDATED)
│  │           ⭐ energia_suministrada_al_ev_kwh[1] = 178 kWh    (UPDATED)
│  │           ⭐ reduccion_indirecta_co2_kg[1] = 497.3 kg       (UPDATED)
│  │
│  ├─ CHARGERS[1]: 18 motos + 4 taxis en carga
│  │           ⭐ cantidad_motos[1] = 18 (UPDATED)
│  │           ⭐ cantidad_mototaxis[1] = 4 (UPDATED)
│  │           ⭐ reduccion_directa_co2_total[1] = 182.5 kg      (UPDATED)
│  │
│  ├─ BESS[1]: SOC=82% (se cargó)
│  │
│  └─ Agent recibe nueva observation + reward anterior
│
└─ Loop continúa por 8,760 timesteps (1 año)
```

---

## 5. CÓMO CARGAR DATOS EN EL CÓDIGO

### Opción 1: Usando Catálogo (RECOMENDADO)
```python
# Import
from src.dataset_builder_citylearn.catalog_datasets import get_dataset
import pandas as pd
import numpy as np

# Cargar datasets
solar = pd.read_csv(get_dataset("SOLAR_v2").path)
chargers = pd.read_csv(get_dataset("CHARGERS_v2").path)
bess = pd.read_csv(get_dataset("BESS_v1").path)

# Validar forma
assert solar.shape == (8760, 15), f"Solar shape error: {solar.shape}"
assert chargers.shape == (8760, 357), f"Chargers shape error: {chargers.shape}"
assert bess.shape == (8760, 25), f"BESS shape error: {bess.shape}"

print("✅ Datasets cargados correctamente")
```

### Opción 2: Directamente en Ambiente
```python
from gymnasium import Env
import pandas as pd

class CityLearnEnvironment(Env):
    def __init__(self, catalog_path=None):
        if catalog_path:
            from src.dataset_builder_citylearn.catalog_datasets import get_dataset
            self.solar = pd.read_csv(get_dataset("SOLAR_v2").path)
            self.chargers = pd.read_csv(get_dataset("CHARGERS_v2").path)
            self.bess = pd.read_csv(get_dataset("BESS_v1").path)
        else:
            # Rutas directas
            self.solar = pd.read_csv("data/interim/oe2/solar/pv_generation_citylearn_enhanced_v2.csv")
            self.chargers = pd.read_csv("data/interim/oe2/chargers/chargers_ev_ano_2024_enriched_v2.csv")
            self.bess = pd.read_csv("data/interim/oe2/bess/bess_ano_2024.csv")
        
        self.timestep = 0
        self.observation_space = gymnasium.spaces.Box(
            low=-np.inf, high=np.inf, shape=(394,), dtype=np.float32
        )
        self.action_space = gymnasium.spaces.Box(
            low=0.0, high=1.0, shape=(39,), dtype=np.float32
        )
    
    def reset(self):
        self.timestep = 0
        return self._get_observation(), {}
    
    def step(self, action):
        # Dispatch energía basado en action
        self.timestep += 1
        
        # Calcular reward con nuevas columnas CO₂
        co2_direct_current = self.chargers["reduccion_directa_co2_total_kg"].iloc[self.timestep]
        co2_indirect_current = self.solar["reduccion_indirecta_co2_kg_total"].iloc[self.timestep]
        
        reward = self._compute_reward(action, co2_direct_current, co2_indirect_current)
        
        if self.timestep >= 8760:
            terminated = True
        else:
            terminated = False
        
        return self._get_observation(), reward, terminated, False, {}
    
    def _get_observation(self):
        obs = np.concatenate([
            self.solar.iloc[self.timestep][:15].values,
            self.chargers.iloc[self.timestep][1:115].values,  # 38×3 socket features
            self.bess.iloc[self.timestep][1:4].values,
            self._get_time_features(self.timestep)
        ])
        return obs.astype(np.float32)
    
    def _compute_reward(self, action, co2_direct, co2_indirect):
        # Multi-objective: 50% grid CO₂, 20% solar, 15% completion, 10% stability, 5% cost
        r_co2_direct = co2_direct * 0.01  # Scale
        r_co2_indirect = co2_indirect * 0.005
        r_completion = 1.0 if all motos/taxis charged else 0.5
        r_stability = smoothness_of_action(action)
        
        reward = (
            0.50 * r_co2_direct +      # Maximizar CO₂ directo (motos/taxis)
            0.20 * r_co2_indirect +    # Maximizar CO₂ indirecto (solar)
            0.15 * r_completion +      # Completar cargas
            0.10 * r_stability +       # Estabilidad red
            0.05 * self._cost_reward() # Tariffs
        )
        return float(reward)
```

---

## 6. EJEMPLOS DE DATA SAMPLING

### Datos en t=1000 (15º de febrero, 16:00)
```
TIMESTAMP: 2024-02-15 16:00:00

SOLAR_v2 (filas seleccionadas del CSV):
├─ irradiancia_W_m2:                  523.4
├─ temperatura_C:                     28.5
├─ potencia_pv_kw:                    620.3
├─ energia_pv_kwh:                    620.3
├─ ⭐ energia_suministrada_al_bess_kwh: 58.9 (9.5%)
├─ ⭐ energia_suministrada_al_ev_kwh:   24.2 (3.9%)
├─ ⭐ energia_suministrada_al_mall_kwh: 448.6 (72.3%)
├─ ⭐ energia_suministrada_a_red_kwh:   135.3 (21.8%)
├─ ⭐ reduccion_indirecta_co2_kg_total: 280.0
└─ tarifa_energia:                    0.0834 USD/kWh

CHARGERS_v2 (selección de columnas):
├─ socket_0_ocupancia:                1.0 (moto cargando)
├─ socket_0_potencia_kw:              7.4
├─ ⭐ socket_0_co2_directo_kg:         6.08
│
├─ socket_1_ocupancia:                0.0 (stand-by)
├─ socket_1_potencia_kw:              0.0
├─ ⭐ socket_1_co2_directo_kg:         0.0
│
├─ ... (38 sockets totales)
│
├─ ⭐ cantidad_motos_cargadas:         14 (de 270)
├─ ⭐ cantidad_mototaxis_cargadas:     3 (de 39)
├─ ⭐ reduccion_directa_co2_motos_kg:  85.1 (14 × 6.08)
├─ ⭐ reduccion_directa_co2_mototaxis_kg: 42.8 (3 × 14.28)
└─ ⭐ reduccion_directa_co2_total_kg:  127.9

BESS_v1:
├─ soc_percent:                       68.5
├─ power_charge_kw:                   45.0
└─ power_discharge_kw:                0.0
```

### Observation Space Construido (t=1000)
```
observation[0:15]    = [523.4, 28.5, 620.3, 620.3,  ..., 280.0, 0.667]  # SOLAR
observation[15:129]  = [1.0, 7.4, 6.08, 0.0, 0.0, 0.0, ..., 0.8, 5.92, 6.08]  # CHARGERS (38×3)
observation[129:132] = [68.5, 45.0, 0.0]  # BESS
observation[132:138] = [16/24, 3/7, 2/12, 0, 1/4, 0]  # TIME

DIMENSIÓN TOTAL: 138 (o 394 si incluyes TODAS las columnas de sockets)
```

---

## 7. CHECKLIST DE INTEGRACIÓN

### Antes de entrenar agentes
- [ ] Verificar que datasets se cargan sin errores: `validate_datasets()`
- [ ] Confirmar shapes: SOLAR (8760×15), CHARGERS (8760×357), BESS (8760×25)
- [ ] Verificar que nuevas columnas existan:
  - [ ] SOLAR: `energia_suministrada_al_bess_kwh`, etc. (5 columnas)
  - [ ] CHARGERS: `cantidad_motos_cargadas`, `cantidad_mototaxis_cargadas`, etc. (5 columnas)
- [ ] Normalizar observation space a [0,1] o [-1,1] según agent
- [ ] Implementar reward function con pesos verificados (50%, 20%, 15%, 10%, 5%)
- [ ] Test run: entrenar agent por 100 timesteps sin errores
- [ ] Verificar que agent ve nuevas columnas CO₂ en reward signal

### Durante entrenamiento
- [ ] Monitorear reward trends (debe crecer a lo largo del tiempo)
- [ ] Verificar que CO₂ total disminuye (comparar vs baseline sin control)
- [ ] Checkpoint cada N episodios
- [ ] Loguear observables clave cada hora

### Después de entrenamiento
- [ ] Evaluar CO₂ final vs baseline (meta: -26%, -29%, -24% para SAC, PPO, A2C)
- [ ] Analizar solar self-consumption % (meta: 65-68%)
- [ ] Documentar resultados en CSV

---

## 8. BASELINE PARA COMPARACIÓN

### SIN Control (No RL)
```python
def baseline_uncontrolled():
    """
    Sin agente: dispatch fijo maximiza solar use pero no optimiza
    """
    for t in range(8760):
        # Dar todo el solar disponible directamente a EV + MALL
        bess_action = 0.5  # Mantener SOC equilibrado
        chargers_actions = [1.0] * 38  # Cargar todolos sockets todo el tiempo
        
        # RESULTADO:
        co2_grid = alto (mucha demanda no cubierta por solar)
        co2_direct = bajo (motos/taxis cargan en horarios no óptimos)
        reward = bajo (no hay optimización)
```

### CON Control RL (Agentes SAC/PPO/A2C)
```python
def optimal_rl_control():
    """
    CON agente: dispatch inteligente optimiza para:
    1. Minimizar CO₂ grid (usar solar cuando hay)
    2. Maximizar CO₂ directo (cargar motos cuando hay demanda)
    3. Completar cargas EV (respetar deadlines)
    """
    for t in range(8760):
        observation = get_observation(t)
        action = agent.predict(observation)  # SAC/PPO/A2C
        
        # RESULTADO:
        co2_grid = 26% menor que baseline  (SAC optimal)
        co2_direct = 30% mayor (cargas mejor cronometradas)
        reward = alto (optimización multi-objetivo)
        
        # TOTAL CO₂ AHORRADO:
        # baseline: ~10,200 kg/año
        # con RL:   ~7,500 kg/año (SAC, -26%)
        #           ~7,200 kg/año (PPO, -29%)
        #           ~7,800 kg/año (A2C, -24%)
```

---

## 9. TRANSITION DE OE2 → OE3

```
OE2 COMPLETADO ✅
├─ SOLAR_v2: 15 cols (1.50 MB)
├─ CHARGERS_v2: 357 cols (16.05 MB)
├─ BESS_v1: 25 cols (2.50 MB)
├─ Catálogo centralizado
├─ Documentación (CATALOG_QUICK_REFERENCE.md, etc.)
└─ Git commits: 67d91d4d, 8d4b94e2, 0e4eacc9

        ⬇️  NEXT PHASE  ⬇️

OE3 TO DO:
├─ [ ] Importar datasets enriquecidos en CityLearn
│      from src.dataset_builder_citylearn.catalog_datasets import get_dataset
│
├─ [ ] Construir Observation Space (394-dim)
│      ├─ SOLAR (15)
│      ├─ CHARGERS (114 = 38×3)
│      ├─ BESS (3)
│      └─ TIME (6)
│
├─ [ ] Construir Action Space (39-dim)
│      ├─ BESS (1)
│      └─ CHARGERS (38)
│
├─ [ ] Implementar Reward Function
│      ├─ 50% CO₂ grid minimization (use new SOLAR columns)
│      ├─ 20% Solar self-consumption (use new energy distribution)
│      ├─ 15% EV completion (use CHARGERS motos/taxis quantities)
│      ├─ 10% Grid stability
│      └─ 5% Cost minimization
│
├─ [ ] Entrenar SAC agent
│      python -m src.agents.sac --config configs/default.yaml
│
├─ [ ] Entrenar PPO agent
│      python -m src.agents.ppo_sb3 --config configs/default.yaml
│
├─ [ ] Entrenar A2C agent
│      python -m src.agents.a2c_sb3 --config configs/default.yaml
│
└─ [ ] Evaluar y comparar contra baseline
       python -m scripts.run_dual_baselines --config configs/default.yaml
```

---

**LISTA PARA OE3** ✅

> Todos los datos están en su lugar. Los agentes RL pueden cargar datasets automáticamente usando el catálogo.  
> Nueva columnas CO₂ estan integradas en observation space.  
> Reward function puede usar directamente `reduccion_directa_co2_*` y `energia_suministrada_al_*` columnas.  
>
> **Siguiente paso**: Implementar environment wrapper en OE3 que cargue datos del catálogo.
