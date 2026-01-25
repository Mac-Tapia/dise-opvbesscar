# IMPLEMENTACIÓN PASO-A-PASO: SAC TIER 2

**Duración estimada**: 2-3 horas
**Archivos a editar**: 3 principales
**Status**: INICIANDO

---

## 📋 ARCHIVOS A MODIFICAR

<!-- markdownlint-disable MD013 -->
```text
src/iquitos_citylearn/oe3/
├── rewards.py              ← CAMBIO 1: Normalización + baselines dinámicas
├── agents/sac.py           ← CAMBIO 2: Hiperparámetros + LRs
└── enriched_observables.py ← VERIFICAR: Observables incluidos
```text
<!-- markdownlint-enable MD013 -->

---

## CAMBIO 1: rewards.py - NORMALIZACIÓN ADAPTATIVA

### Paso 1.1: Agregar clase para stats adaptativas

**Ubicación**: Desp...
```

[Ver código completo en GitHub]text
<!-- markdownlint-enable MD013 -->

---

### Paso 1.2: Modificar `__init__` de `MultiObjectiveReward`

**Ubicación**: Línea ~113 en rewards.py

**Antes**:

<!-- markdownlint-disable MD013 -->
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

        self._reward_hi...
```

[Ver código completo en GitHub]python
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
        self._adaptive_stats = AdaptiveRewardStats() \
                if use_adaptive_stats else None

        self._reward_history: List[Dict[str, float]] = []
        self._max_history = 1000
```text
<!-- markdownlint-enable MD013 -->

---

### Paso 1.3: Reemplazar función `compute()` COMPLETA

**Ubicación**: Línea ~143 - ~280

**Reemplazar por**:

<!-- markdownlint-disable MD013 -->
```python
    def compute(
        self,
        grid_import_kwh: float,
        grid_export_kwh: float,
        solar_generation_kwh: float,
        ev_charging_kwh: float,
        ev_soc_avg: float,
        bess...
```

[Ver código completo en GitHub]text
<!-- markdownlint-enable MD013 -->

---

## CAMBIO 2: sac.py - HIPERPARÁMETROS TIER 2

### Paso 2.1: Modificar `SACConfig`

**Ubicación**: Línea ~176 en sac.py

**Antes**:

<!-- markdownlint-disable MD013 -->
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
    grad...
```

[Ver código completo en GitHub]python
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
```text
<!-- markdownlint-enable MD013 -->

---

### Paso 2.2: Verificar que observables enriquecidos se usan

**Ubicación**: Línea ~550-600 en sac.py (en método de env wrapping)

**Buscar**: código que llama a `enriched_observables.EnrichedObservableWrapper`

**Si NO existe**, añadir en `setup_env()`:

<!-- markdownlint-disable MD013 -->
```python
# En setup_env() method, después de crear env:

from ..en...
```

[Ver código completo en GitHub]text
<!-- markdownlint-enable MD013 -->

---

## CAMBIO 3: enriched_observables.py - VERIFICACIÓN

### Paso 3.1: Revisar que todos los features se incluyen

**Ubicación**: Método `get_enriched_state()`en enriched_observables.py (~línea
100)

**Verif icar que retorna TODOS estos keys**:

<!-- markdownlint-disable MD013 -->
```python
return {
    "is_peak_hour": is_peak,                        # 1 feature
    "is_valley_hour": is_valley,                    # 1 feature
    "hour_of_day": float(self.hour_of_day),         # 1 feature
    "bess_soc_current": float(bess_soc),            # 1 feature
    "bess_soc_target": float(soc_target),           # 1 feature
    "bess_soc_reserve_deficit": float(soc_reserve_deficit),  # 1 featur...
```

[Ver código completo en GitHub]text
<!-- markdownlint-enable MD013 -->

---

## ✅ VALIDACIÓN POST-CAMBIOS

### Test 1: Verificar sintaxis

<!-- markdownlint-disable MD013 -->
```bash
python -m py_compile src/iquitos_citylearn/oe3/rewards.py
python -m py_compile src/iquitos_citylearn/oe3/agents/sac.py
python -m py_compile src/iquitos_citylearn/oe3/enriched_observables.py
```text
<!-- markdownlint-enable MD013 -->

### Test 2: Cargar módulos

<!-- markdownlint-disable MD013 -->
```python
import sys
sys.path.insert(0, 'd:\\diseñopvbesscar')

from src.iquitos_citylearn.oe3.rewards...
```

[Ver código completo en GitHub]text
<!-- markdownlint-enable MD013 -->

### Test 3: Full env test

<!-- markdownlint-disable MD013 -->
```bash
# Cargar checkpoint SAC actual
# Ejecutar 1 episodio completo
# Verificar: sin NaN, observation shape correcto
```text
<!-- markdownlint-enable MD013 -->

---

## 🔄 ROLLBACK (si algo falla)

Si necesitas revertir:

<!-- markdownlint-disable MD013 -->
```bash
# Volver a versión anterior
git checkout HEAD -- src/iquitos_citylearn/oe3/rewards.py
git checkout HEAD -- src/iquitos_citylearn/oe3/agents/sac.py

# O si ya committeaste
git revert HEAD~1
```text
<!-- markdownlint-enable MD013 -->

---

## 📊 PRÓXIMOS PASOS

Una vez completes estos 3 cambios:

1. Commit:
`"SAC TIER 2: Normalización adaptativa + observables + hiperparámetros"`
2. Entrenar: `python -m src.train_sac_cuda --episodes=50 --device=cuda`
3. Monitorear: Reward converge más rápido?
4. Analizar: CO₂ y SOC mejoraron?

---

**Duración total**: 2-3 horas (código + test + debug)
**Riesgo**: BAJO (cambios mostly en rewards, no en core RL)
**Reversibilidad**: ALTA (git revert siempre disponible)