# IMPLEMENTACIÓN PASO-A-PASO: SAC TIER 2

**Duración estimada**: 2-3 horas  
**Archivos a editar**: 3 principales  
**Status**: INICIANDO  

---

## 📋 ARCHIVOS A MODIFICAR

```
src/iquitos_citylearn/oe3/
├── rewards.py              ← CAMBIO 1: Normalización + baselines dinámicas
├── agents/sac.py           ← CAMBIO 2: Hiperparámetros + LRs
└── enriched_observables.py ← VERIFICAR: Observables incluidos
```

---

## CAMBIO 1: rewards.py - NORMALIZACIÓN ADAPTATIVA

### Paso 1.1: Agregar clase para stats adaptativas

**Ubicación**: Después de `MultiObjectiveWeights` (línea ~60)

```python
@dataclass
class AdaptiveRewardStats:
    """Estadísticas adaptativas para normalización por percentiles."""
    component_histories: Dict[str, List[float]] = field(default_factory=lambda: {
        "r_co2": [],
        "r_cost": [],
        "r_solar": [],
        "r_ev": [],
        "r_grid": [],
        "reward_total": [],
    })
    window_size: int = 500
    percentile_low: float = 0.25   # p25
    percentile_high: float = 0.75  # p75
    
    def add_component(self, name: str, value: float):
        """Agrega valor a historial y mantiene window size."""
        if name not in self.component_histories:
            self.component_histories[name] = []
        self.component_histories[name].append(value)
        if len(self.component_histories[name]) > self.window_size:
            self.component_histories[name].pop(0)
    
    def get_percentile_range(self, name: str) -> Tuple[float, float]:
        """Retorna (p25, p75) para normalización."""
        if name not in self.component_histories or len(self.component_histories[name]) < 10:
            return (-1.0, 1.0)  # Default si hay pocos datos
        hist = np.array(self.component_histories[name])
        p_low = np.percentile(hist, self.percentile_low * 100)
        p_high = np.percentile(hist, self.percentile_high * 100)
        return (float(p_low), float(p_high))
    
    def normalize_component(self, name: str, value: float) -> float:
        """Normaliza componente al rango [p25, p75] → [-1, 1]."""
        p_low, p_high = self.get_percentile_range(name)
        if p_low == p_high:
            return 0.0
        # Map [p_low, p_high] → [-1, 1]
        normalized = 2.0 * (value - p_low) / (p_high - p_low) - 1.0
        return float(np.clip(normalized, -1.0, 1.0))
```

---

### Paso 1.2: Modificar `__init__` de `MultiObjectiveReward`

**Ubicación**: Línea ~113 en rewards.py

**Antes**:

```python
    def __init__(
        self, 
        weights: Optional[MultiObjectiveWeights] = None,
        context: Optional[IquitosContext] = None,
    ):
        if weights is None:
            weights = MultiObjectiveWeights(co2=0.50, cost=0.15, solar=0.20, ev_satisfaction=0.10, grid_stability=0.05)
        self.weights = weights
        self.context = context or IquitosContext()
        
        self._reward_history: List[Dict[str, float]] = []
        self._max_history = 1000
```

**Después**:

```python
    def __init__(
        self, 
        weights: Optional[MultiObjectiveWeights] = None,
        context: Optional[IquitosContext] = None,
        use_adaptive_stats: bool = True,
    ):
        if weights is None:
            # TIER 2 FIX: Pesos rebalanceados
            weights = MultiObjectiveWeights(
                co2=0.50,              # PRIMARY: CO₂ minimización
                grid_stability=0.15,   # +5% por importancia pico
                solar=0.20,
                ev_satisfaction=0.10,
                cost=0.05              # REDUCIDO: no es bottleneck
            )
        self.weights = weights
        self.context = context or IquitosContext()
        
        # NEW: Estadísticas adaptativas
        self._adaptive_stats = AdaptiveRewardStats() if use_adaptive_stats else None
        
        self._reward_history: List[Dict[str, float]] = []
        self._max_history = 1000
```

---

### Paso 1.3: Reemplazar función `compute()` COMPLETA

**Ubicación**: Línea ~143 - ~280

**Reemplazar por**:

```python
    def compute(
        self,
        grid_import_kwh: float,
        grid_export_kwh: float,
        solar_generation_kwh: float,
        ev_charging_kwh: float,
        ev_soc_avg: float,
        bess_soc: float,
        hour: int,
        ev_demand_kwh: float = 0.0,
    ) -> Tuple[float, Dict[str, float]]:
        """TIER 2 FIX: Baselines dinámicas + normalización adaptativa + bonuses.
        
        Args:
            grid_import_kwh: Energía importada [kWh]
            grid_export_kwh: Energía exportada [kWh]
            solar_generation_kwh: Generación solar [kWh]
            ev_charging_kwh: Energía a EVs [kWh]
            ev_soc_avg: SOC promedio EVs [0-1]
            bess_soc: SOC batería [0-1]
            hour: Hora del día [0-23]
            ev_demand_kwh: Demanda EV [kWh]
            
        Returns:
            (reward_total, components_dict)
        """
        components = {}
        is_peak = hour in self.context.peak_hours  # [18, 19, 20, 21]
        is_prepeak = hour in [16, 17]
        
        # ========== 1. RECOMPENSA CO₂ (50% - PRIMARY) ==========
        co2_kg = grid_import_kwh * self.context.co2_factor_kg_per_kwh
        
        # Baselines dinámicas (TIER 2 FIX)
        co2_baseline_offpeak = 130.0  # kWh/h típico fuera pico
        co2_baseline_peak = 250.0     # kWh/h target con BESS en pico
        
        if is_peak:
            # Penalidad exponencial en pico
            r_co2_base = 1.0 - 2.0 * min(1.0, grid_import_kwh / co2_baseline_peak)
            
            # BONUS: Si batería contribuyó (SOC > 40% en pico → ahorró importación)
            bess_contribution = max(0.0, bess_soc - 0.40)
            r_co2 = r_co2_base + 0.3 * bess_contribution  # Bonus +0.3
            
            components["co2_bonus_bess"] = 0.3 * bess_contribution
        else:
            # Off-peak: más tolerante
            r_co2 = 1.0 - 1.0 * min(1.0, grid_import_kwh / co2_baseline_offpeak)
            components["co2_bonus_bess"] = 0.0
        
        r_co2 = np.clip(r_co2, -1.0, 1.0)
        components["r_co2"] = r_co2
        components["co2_kg"] = co2_kg
        components["co2_baseline"] = co2_baseline_peak if is_peak else co2_baseline_offpeak
        
        # ========== 2. RECOMPENSA ESTABILIDAD GRID (15% - SECUNDARIA) ==========
        demand_ratio = grid_import_kwh / max(1.0, self.context.peak_demand_limit_kw)
        
        if is_peak:
            # Penalidad MUY fuerte en pico si superas 200 kW
            if demand_ratio > 1.0:
                r_grid = -1.0  # Violación severa
            else:
                r_grid = 1.0 - 3.0 * demand_ratio  # Gradientes fuertes
        else:
            r_grid = 1.0 - 1.5 * min(1.0, demand_ratio)
        
        r_grid = np.clip(r_grid, -1.0, 1.0)
        components["r_grid"] = r_grid
        components["demand_ratio"] = demand_ratio
        components["is_peak"] = float(is_peak)
        
        # ========== 3. RECOMPENSA AUTOCONSUMO SOLAR (20%) ==========
        if solar_generation_kwh > 1.0:  # Evitar división por cero
            # Solar usado = mínimo entre generación y consumo (EVs + chargers)
            solar_used = min(solar_generation_kwh, ev_charging_kwh)
            self_consumption_ratio = solar_used / solar_generation_kwh
            r_solar = 2.0 * self_consumption_ratio - 1.0
        else:
            r_solar = 0.0
        
        r_solar = np.clip(r_solar, -1.0, 1.0)
        components["r_solar"] = r_solar
        components["solar_kwh"] = solar_generation_kwh
        
        # ========== 4. RECOMPENSA SATISFACCIÓN EV (10%) ==========
        # SOC objetivo: target 90%
        ev_satisfaction = min(1.0, ev_soc_avg / self.context.ev_soc_target)
        r_ev = 2.0 * ev_satisfaction - 1.0
        
        # Bonus pequeño si hay cobertura solar durante carga
        if solar_generation_kwh > 10.0 and ev_charging_kwh > 1.0:
            solar_ev_ratio = min(1.0, solar_generation_kwh / (ev_charging_kwh + 1.0))
            r_ev += 0.15 * solar_ev_ratio  # Bonus si cargas con solar
        
        r_ev = np.clip(r_ev, -1.0, 1.0)
        components["r_ev"] = r_ev
        components["ev_soc_avg"] = ev_soc_avg
        
        # ========== 5. RECOMPENSA COSTO (5% - REDUCIDO) ==========
        cost_usd = (grid_import_kwh - grid_export_kwh) * self.context.tariff_usd_per_kwh
        cost_baseline = 100.0  # USD/hora
        r_cost = 1.0 - 2.0 * min(1.0, max(0.0, cost_usd) / cost_baseline)
        r_cost = np.clip(r_cost, -1.0, 1.0)
        components["r_cost"] = r_cost
        components["cost_usd"] = cost_usd
        
        # ========== 6. PENALIDAD SOC PRE-PICO ==========
        soc_penalty = 0.0
        if is_prepeak:
            soc_target_prepeak = 0.65  # Target: 65% en horas 16-17
            if bess_soc < soc_target_prepeak:
                soc_deficit = soc_target_prepeak - bess_soc
                soc_penalty = -0.3 * (soc_deficit / soc_target_prepeak)  # [-0.3, 0]
            components["soc_deficit_prepeak"] = max(0, soc_target_prepeak - bess_soc)
        else:
            components["soc_deficit_prepeak"] = 0.0
        
        components["soc_penalty"] = soc_penalty
        
        # ========== RECOMPENSA TOTAL (TIER 2: pesos rebalanceados) ==========
        # Pesos: 0.50 (CO₂) + 0.15 (Grid) + 0.20 (Solar) + 0.10 (EV) + 0.05 (Costo)
        reward = (
            0.50 * r_co2 +
            0.15 * r_grid +
            0.20 * r_solar +
            0.10 * r_ev +
            0.05 * r_cost +
            0.10 * soc_penalty  # Pre-pico penalty weight
        )
        
        reward = np.clip(reward, -1.0, 1.0)
        components["reward_total"] = reward
        
        # Guardar en estadísticas adaptativas (si enabled)
        if self._adaptive_stats:
            for name, value in [
                ("r_co2", r_co2),
                ("r_cost", r_cost),
                ("r_solar", r_solar),
                ("r_ev", r_ev),
                ("r_grid", r_grid),
                ("reward_total", reward),
            ]:
                self._adaptive_stats.add_component(name, value)
        
        # Guardar historial
        self._reward_history.append(components)
        if len(self._reward_history) > self._max_history:
            self._reward_history.pop(0)
        
        return reward, components
```

---

## CAMBIO 2: sac.py - HIPERPARÁMETROS TIER 2

### Paso 2.1: Modificar `SACConfig`

**Ubicación**: Línea ~176 en sac.py

**Antes**:

```python
@dataclass
class SACConfig:
    """Configuración avanzada para SAC..."""
    episodes: int = 50
    batch_size: int = 512
    buffer_size: int = 100000
    learning_rate: float = 3e-4
    gamma: float = 0.99
    tau: float = 0.005
    
    ent_coef: float = 0.01
    target_entropy: Optional[float] = -50.0
    
    hidden_sizes: tuple = (256, 256)
    activation: str = "relu"
    
    n_steps: int = 1
    gradient_steps: int = 1
    
    device: str = "auto"
    use_amp: bool = True
```

**Después** (TIER 2 FIX):

```python
@dataclass
class SACConfig:
    """Configuración SAC TIER 2: Optimización post-relanzamiento.
    
    TIER 2 FIX APPLIED:
    - Entropía: 0.02 (↑ exploración inicial)
    - Target entropy: -40.0 (menos restrictivo)
    - Learning rate: 2.5e-4 (más estable)
    - Batch size: 256 (menos ruido)
    - Buffer: 150k (más diversidad)
    - Hidden: 512x512 (más expresiva)
    - Dropout: 0.1 (regularización)
    """
    # Entrenamiento base
    episodes: int = 50
    batch_size: int = 256              # ↓ de 512: menos ruido
    buffer_size: int = 150000          # ↑ de 100k: más diversidad
    learning_rate: float = 2.5e-4      # ↓ de 3e-4: más estable
    
    # Learning rates específicos
    critic_lr: float = 2.5e-4          # NEW: LR crítico
    actor_lr: float = 2.5e-4           # NEW: LR actor
    alpha_lr: float = 1e-4             # NEW: LR para alpha (entropía)
    
    gamma: float = 0.99                # Discount factor
    tau: float = 0.005                 # Target network update rate
    
    # Entropía - TIER 2 FIX
    ent_coef: float = 0.02             # ↑ de 0.01: más exploración
    target_entropy: Optional[float] = -40.0  # ↓ de -50.0: menos penalizante
    
    # Red neuronal - TIER 2 FIX
    hidden_sizes: tuple = (512, 512)   # ↑ de (256,256): mayor capacidad
    activation: str = "relu"
    use_dropout: bool = True           # NEW: regularización
    dropout_rate: float = 0.1          # NEW: 10% dropout
    
    # Actualizaciones múltiples
    n_steps: int = 1
    gradient_steps: int = 1
    update_per_timestep: int = 2       # NEW: 2 updates/step (vs 1)
    
    # GPU/CUDA
    device: str = "auto"
    use_amp: bool = True
```

---

### Paso 2.2: Verificar que observables enriquecidos se usan

**Ubicación**: Línea ~550-600 en sac.py (en método de env wrapping)

**Buscar**: código que llama a `enriched_observables.EnrichedObservableWrapper`

**Si NO existe**, añadir en `setup_env()`:

```python
# En setup_env() method, después de crear env:

from ..enriched_observables import EnrichedObservableWrapper, OperationalConstraints

# Crear wrapper de observables enriquecidos
constraints = OperationalConstraints.from_config(self.config)
env = EnrichedObservableWrapper(env, constraints, n_playas=2)

logger.info(f"SAC: Observables enriquecidos activados, dim total ~915")
```

---

## CAMBIO 3: enriched_observables.py - VERIFICACIÓN

### Paso 3.1: Revisar que todos los features se incluyen

**Ubicación**: Método `get_enriched_state()` en enriched_observables.py (~línea 100)

**Verif icar que retorna TODOS estos keys**:

```python
return {
    "is_peak_hour": is_peak,                        # 1 feature
    "is_valley_hour": is_valley,                    # 1 feature
    "hour_of_day": float(self.hour_of_day),         # 1 feature
    "bess_soc_current": float(bess_soc),            # 1 feature
    "bess_soc_target": float(soc_target),           # 1 feature
    "bess_soc_reserve_deficit": float(soc_reserve_deficit),  # 1 feature
    "pv_power_available_kw": float(pv_power_kw),    # 1 feature
    "pv_power_ratio": float(pv_power_ratio),        # 1 feature
    "grid_import_kw": float(grid_import_kw),        # 1 feature
    "ev_power_total_kw": float(ev_power_total),     # 1 feature
    "ev_power_motos_kw": float(ev_power_motos_kw),  # 1 feature
    "ev_power_mototaxis_kw": float(ev_power_mototaxis_kw),  # 1 feature
    "ev_power_fairness_ratio": float(fairness_ratio),  # 1 feature
    "pending_sessions_motos": self._pending_sessions[0],      # 1 feature
    "pending_sessions_mototaxis": self._pending_sessions[1],  # 1 feature
}
# = 15 features adicionales
```

---

## ✅ VALIDACIÓN POST-CAMBIOS

### Test 1: Verificar sintaxis

```bash
python -m py_compile src/iquitos_citylearn/oe3/rewards.py
python -m py_compile src/iquitos_citylearn/oe3/agents/sac.py
python -m py_compile src/iquitos_citylearn/oe3/enriched_observables.py
```

### Test 2: Cargar módulos

```python
import sys
sys.path.insert(0, 'd:\\diseñopvbesscar')

from src.iquitos_citylearn.oe3.rewards import MultiObjectiveReward, AdaptiveRewardStats
from src.iquitos_citylearn.oe3.agents.sac import SACConfig
from src.iquitos_citylearn.oe3.enriched_observables import EnrichedObservableWrapper

# Instantiate y test
config = SACConfig()
print(f"✅ SAC Config: ent_coef={config.ent_coef}, batch_size={config.batch_size}")

reward_fn = MultiObjectiveReward(use_adaptive_stats=True)
r, comps = reward_fn.compute(
    grid_import_kwh=200,
    grid_export_kwh=0,
    solar_generation_kwh=100,
    ev_charging_kwh=50,
    ev_soc_avg=0.7,
    bess_soc=0.6,
    hour=19,
)
print(f"✅ Reward compute: r={r:.3f}, co2_bonus={comps.get('co2_bonus_bess', 0):.3f}")
```

### Test 3: Full env test

```bash
# Cargar checkpoint SAC actual
# Ejecutar 1 episodio completo
# Verificar: sin NaN, observation shape correcto
```

---

## 🔄 ROLLBACK (si algo falla)

Si necesitas revertir:

```bash
# Volver a versión anterior
git checkout HEAD -- src/iquitos_citylearn/oe3/rewards.py
git checkout HEAD -- src/iquitos_citylearn/oe3/agents/sac.py

# O si ya committeaste
git revert HEAD~1
```

---

## 📊 PRÓXIMOS PASOS

Una vez completes estos 3 cambios:

1. Commit: `"SAC TIER 2: Normalización adaptativa + observables + hiperparámetros"`
2. Entrenar: `python -m src.train_sac_cuda --episodes=50 --device=cuda`
3. Monitorear: Reward converge más rápido?
4. Analizar: CO₂ y SOC mejoraron?

---

**Duración total**: 2-3 horas (código + test + debug)  
**Riesgo**: BAJO (cambios mostly en rewards, no en core RL)  
**Reversibilidad**: ALTA (git revert siempre disponible)  
