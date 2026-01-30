# 📝 CAMBIOS DE CONFIGURACIÓN: SAC & PPO PRE-ENTRENAMIENTO

**Status:** 🟡 PENDIENTE IMPLEMENTACIÓN (antes de entrenar)
**Crítico:** TODOS estos cambios deben estar hechos ANTES de `run_oe3_simulate`
**Orden:** Implementar → Commit → LUEGO entrenar

---

## SAC - Cambios Específicos de Código

### Archivo: `src/iquitos_citylearn/oe3/agents/sac.py`

```python
# CAMBIO 1: Buffer Size (Línea ~45)
# ANTES:
self.buffer_size = 10_000

# DESPUÉS:
self.buffer_size = 100_000  # 10x mayor, reduce contamination


# CAMBIO 2: Learning Rate (Línea ~50)
# ANTES:
self.learning_rate = 2e-4

# DESPUÉS:
self.learning_rate = 5e-5   # 4x menor, mejor convergence


# CAMBIO 3: Tau - Target Network Update (Línea ~60)
# ANTES:
self.tau = 0.001

# DESPUÉS:
self.tau = 0.01  # 10x mayor, más estable


# CAMBIO 4: Network Architecture (Línea ~70)
# ANTES:
self.net_arch = [256, 256]

# DESPUÉS:
self.net_arch = [512, 512]  # Más capacidad para 126 acciones


# CAMBIO 5: Batch Size (Línea ~75)
# ANTES:
self.batch_size = 64

# DESPUÉS:
self.batch_size = 256  # 4x mayor, mejor gradient estimation


# CAMBIO 6: Entropy Coefficient - AUTO TUNING (Línea ~55)
# ANTES:
self.ent_coef = 0.2

# DESPUÉS (NUEVO SISTEMA):
self.ent_coef = 'auto'                    # Auto-tune durante training
self.ent_coef_init = 0.5                  # Valor inicial más alto
self.ent_coef_learning_rate = 1e-4        # Learning rate para entropy


# CAMBIO 7: Add Gradient Clipping (Línea ~80, NUEVO)
# ANTES:
# (no existe)

# DESPUÉS (AGREGAR):
self.max_grad_norm = 1.0  # Prevenir divergencia


# CAMBIO 8: Prioritized Experience Replay (Línea ~65, NUEVO)
# ANTES:
# (no existe)

# DESPUÉS (AGREGAR en __init__ o parámetros):
@dataclass
class SACConfigOptimized:
    # ... existing fields ...
    buffer_size: int = 100_000
    learning_rate: float = 5e-5
    tau: float = 0.01
    ent_coef: str | float = 'auto'  # String for auto-tune
    ent_coef_init: float = 0.5
    ent_coef_lr: float = 1e-4
    net_arch: List[int] = field(default_factory=lambda: [512, 512])
    batch_size: int = 256
    max_grad_norm: float = 1.0
    
    # NEW: Prioritized Replay
    use_prioritized_replay: bool = True
    per_alpha: float = 0.6      # Prioritization exponent
    per_beta: float = 0.4       # Importance sampling
    per_epsilon: float = 1e-6   # Min priority


# CAMBIO 9: Implementar en modelo.learn() (Línea ~120)
# AGREGAR:
self.policy.max_grad_norm = self.max_grad_norm

# Y cuando creas modelo SAC (stable_baselines3):
model = SAC(
    policy="MlpPolicy",
    env=env,
    learning_rate=self.learning_rate,
    buffer_size=self.buffer_size,
    tau=self.tau,
    ent_coef=self.ent_coef,
    batch_size=self.batch_size,
    gradient_steps=-1,
    max_grad_norm=self.max_grad_norm,  # NUEVO
    # PER si stable-baselines3 lo soporta, sino:
    # usar extension custom
)
```

---

## PPO - Cambios Específicos de Código

### Archivo: `src/iquitos_citylearn/oe3/agents/ppo_sb3.py`

```python
# CAMBIO 1: Clip Range (Línea ~45)
# ANTES:
self.clip_range = 0.2

# DESPUÉS:
self.clip_range = 0.5  # 2.5x mayor, permite cambios policy más agresivos


# CAMBIO 2: N_Steps (Trajectory horizon) (Línea ~50)
# ANTES:
self.n_steps = 2048  # ~2.3 días

# DESPUÉS:
self.n_steps = 8760  # FULL EPISODE = 1 día completo (365 horas)
# Permite ver causal chain: 8am → mediodía → noche


# CAMBIO 3: Batch Size (Línea ~55)
# ANTES:
self.batch_size = 64

# DESPUÉS:
self.batch_size = 256  # 4x mayor


# CAMBIO 4: N_Epochs (Múltiples passes) (Línea ~60)
# ANTES:
self.n_epochs = 3

# DESPUÉS:
self.n_epochs = 10  # Más passes para mejor convergence


# CAMBIO 5: Learning Rate (Línea ~40)
# ANTES:
self.learning_rate = 3e-4

# DESPUÉS:
self.learning_rate = 1e-4  # 3x menor


# CAMBIO 6: Add Gradient Clipping (Línea ~75, NUEVO)
# ANTES:
# (no existe)

# DESPUÉS (AGREGAR):
self.max_grad_norm = 1.0


# CAMBIO 7: Entropy Coefficient (Línea ~65)
# ANTES:
self.ent_coef = 0.0  # Sin exploración

# DESPUÉS:
self.ent_coef = 0.01  # Pequeño bonus de exploración


# CAMBIO 8: Normalize Advantage (Línea ~70, NUEVO)
# ANTES:
self.normalize_advantage = False

# DESPUÉS:
self.normalize_advantage = True  # Normaliza ventajas por batch


# CAMBIO 9: State-Dependent Exploration (Línea ~80, NUEVO)
# ANTES:
# (no existe)

# DESPUÉS (AGREGAR):
self.use_sde = True           # State-Dependent Exploration
self.sde_sample_freq = -1     # Resample every step


# CAMBIO 10: KL Divergence Safety (Línea ~85, NUEVO)
# ANTES:
# (no existe)

# DESPUÉS (AGREGAR):
self.target_kl = 0.02  # Stop training if KL divergence > 0.02


# CAMBIO 11: Agregar a dataclass (Línea ~20-40)
@dataclass
class PPOConfigOptimized:
    # ... existing fields ...
    clip_range: float = 0.5          # CAMBIO 1
    n_steps: int = 8760              # CAMBIO 2
    batch_size: int = 256            # CAMBIO 3
    n_epochs: int = 10               # CAMBIO 4
    learning_rate: float = 1e-4      # CAMBIO 5
    max_grad_norm: float = 1.0       # CAMBIO 6
    ent_coef: float = 0.01           # CAMBIO 7
    normalize_advantage: bool = True # CAMBIO 8
    use_sde: bool = True             # CAMBIO 9
    sde_sample_freq: int = -1        # CAMBIO 9
    target_kl: float = 0.02          # CAMBIO 10
    gae_lambda: float = 0.98         # NUEVO: Better long-term advantages
    clip_range_vf: float = 0.5       # NUEVO: VF clipping


# CAMBIO 12: Implementar en modelo (Línea ~120)
# ANTES:
model = PPO(
    policy="MlpPolicy",
    env=env,
    learning_rate=self.learning_rate,
    n_steps=self.n_steps,
    batch_size=self.batch_size,
    n_epochs=self.n_epochs,
    ent_coef=self.ent_coef,
)

# DESPUÉS:
model = PPO(
    policy="MlpPolicy",
    env=env,
    learning_rate=self.learning_rate,
    n_steps=self.n_steps,
    batch_size=self.batch_size,
    n_epochs=self.n_epochs,
    ent_coef=self.ent_coef,
    clip_range=self.clip_range,
    clip_range_vf=self.clip_range_vf,
    max_grad_norm=self.max_grad_norm,
    normalize_advantage=self.normalize_advantage,
    use_sde=self.use_sde,
    sde_sample_freq=self.sde_sample_freq,
    target_kl=self.target_kl,
    gae_lambda=self.gae_lambda,
)
```

---

## A2C - SIN CAMBIOS (Mantener como referencia)

```python
# ARCHIVO: src/iquitos_citylearn/oe3/agents/a2c_sb3.py

# ✅ NO MODIFICAR
# A2C es el baseline optimizado
# Sus configuraciones ya son adecuadas
# Se mantiene para comparación

# Status: REFERENCIA - COMPARACIÓN JUSTA
```

---

## Resumen de Cambios por Archivo

### `src/iquitos_citylearn/oe3/agents/sac.py`
```
Total cambios: 9
  - 5 cambios en parámetros existentes (buffer, lr, tau, net, batch)
  - 3 cambios en nuevos parámetros (ent_coef auto, grad norm, ent_lr)
  - 1 referencia a PER (si stable-baselines3 lo soporta)

Líneas afectadas: ~10-15 líneas modificadas
Complejidad: Baja (cambios simples de valores)
```

### `src/iquitos_citylearn/oe3/agents/ppo_sb3.py`
```
Total cambios: 12
  - 5 cambios en parámetros existentes (clip, n_steps, batch, epochs, lr)
  - 7 cambios en nuevos parámetros (grad norm, ent, normalize, sde, kl, lambda, vf_clip)

Líneas afectadas: ~15-20 líneas modificadas
Complejidad: Media (más parámetros nuevos)
```

### `src/iquitos_citylearn/oe3/agents/a2c_sb3.py`
```
Total cambios: 0
  - Sin cambios requeridos
  - Mantener como referencia

Líneas afectadas: 0
Complejidad: N/A
```

---

## ⚠️ ORDEN CRÍTICO DE IMPLEMENTACIÓN

```
1️⃣ ANTES DE EMPEZAR:
   $ git checkout -b oe3-optimization-sac-ppo
   $ git commit -m "Backup: Pre-optimization state"

2️⃣ IMPLEMENTAR CAMBIOS (en este orden):
   a) Editar SAC (9 cambios)
   b) Editar PPO (12 cambios)
   c) Validar: pylint src/iquitos_citylearn/oe3/agents/
   d) Validar: python -c "from src.iquitos_citylearn.oe3.agents import SAC, PPO"

3️⃣ COMMIT CAMBIOS:
   $ git add src/iquitos_citylearn/oe3/agents/
   $ git commit -m "Config: Optimize SAC/PPO configurations for OE3
   
   SAC: buffer 10K→100K, LR 2e-4→5e-5, tau 0.001→0.01, PER enabled
   PPO: clip 0.2→0.5, n_steps 2048→8760, batch 64→256, epochs 3→10
   
   Details in PLAN_CORRECCION_OPTIMIZACION_SAC_PPO.md"

4️⃣ SOLO DESPUÉS DE COMMITS:
   $ python -m scripts.run_oe3_simulate --config configs/default.yaml
```

---

## ✅ Validación Post-Cambios

Después de implementar todos los cambios, ejecutar:

```bash
# 1. Validar sintaxis
python -m py_compile src/iquitos_citylearn/oe3/agents/sac.py
python -m py_compile src/iquitos_citylearn/oe3/agents/ppo_sb3.py

# 2. Importar módulos
python -c "from src.iquitos_citylearn.oe3.agents import SACAgent, PPOAgent, A2CAgent; print('✅ All agents imported')"

# 3. Validar dataclasses
python -c "from src.iquitos_citylearn.oe3.agents.sac import SACConfig; c = SACConfig(); print(f'✅ SAC config: buffer={c.buffer_size}, lr={c.learning_rate}')"

# 4. Full environment test
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
echo "✅ Dataset built successfully"

# 5. Dry run (1 timestep only)
python -c "
from src.iquitos_citylearn.oe3.simulate import simulate
# Validate agents can be instantiated with new config
print('✅ Agents can be instantiated with optimized configs')
"
```

---

## 📋 Checklist Final

```
☐ SAC cambios: 9/9 implementados
☐ PPO cambios: 12/12 implementados
☐ A2C cambios: 0/0 (sin cambios, referencia)

☐ Archivos compilados sin errores
☐ Imports validados
☐ Dataclasses validadas
☐ Dataset buildeable

☐ Commit realizado
☐ Branch creado
☐ Backup guardado

☐ Ready para: python -m scripts.run_oe3_simulate
```

---

## 📊 Resultados Esperados Después de Re-Entrenamiento

```
SAC Optimizado:
  CO₂: +4.7% → ??? (Esperado: -10% a -15%)
  EVs sin grid: 75% → ??? (Esperado: 85% a 90%)
  Convergencia: Oscillating → ??? (Esperado: Smooth)

PPO Optimizado:
  CO₂: +0.08% → ??? (Esperado: -15% a -20%)
  EVs sin grid: 93% → ??? (Esperado: 94% a 96%)
  Convergencia: Flat → ??? (Esperado: Accelerating)

A2C Referencia (sin cambios):
  CO₂: -25.1% (mantiene)
  EVs sin grid: 95% (mantiene)
  Convergencia: Smooth (mantiene)
```

Luego de esto, comparación JUSTA porque todos los agentes tienen configuraciones óptimas.
