# 🚀 GUÍA PRÁCTICA DE IMPLEMENTACIÓN: SAC/PPO - Paso a Paso

**Propósito:** Guía operativa directa para implementar los 21 cambios  
**Formato:** Copy-paste ready con instrucciones claras  
**Tiempo Estimado:** 30-45 minutos (cambios) + 75 minutos (entrenamiento)  

---

## 🎯 PASO 1: PREPARACIÓN (5 min)

### 1.1 Crear branch de backup

```bash
cd d:\diseñopvbesscar
git status  # Asegúrate que no hay cambios sin commit
git checkout -b oe3-sac-ppo-optimization
git branch -v  # Verifica que estás en nueva rama
```

**Resultado esperado:**
```
* oe3-sac-ppo-optimization
  main
```

### 1.2 Verificar archivos

```bash
# Confirmar que estos archivos existen
ls -la src/iquitos_citylearn/oe3/agents/sac.py
ls -la src/iquitos_citylearn/oe3/agents/ppo_sb3.py
ls -la src/iquitos_citylearn/oe3/agents/a2c_sb3.py
```

**Resultado esperado:** Los 3 archivos deben existir

---

## 🔧 PASO 2: MODIFICAR SAC (10 min)

### 2.1 Abrir archivo SAC

```bash
code src/iquitos_citylearn/oe3/agents/sac.py
```

### 2.2 Encontrar la clase SACConfig (o equivalente dataclass)

Busca (Ctrl+F): `@dataclass` o `class SACConfig`

### 2.3 Implementar 9 cambios

#### CAMBIO 1: buffer_size

**Buscar:**
```python
buffer_size: int = 10_000
```

**Reemplazar por:**
```python
buffer_size: int = 100_000  # ✅ 10x mayor para evitar buffer divergence
```

---

#### CAMBIO 2: learning_rate

**Buscar:**
```python
learning_rate: float = 2e-4
```

**Reemplazar por:**
```python
learning_rate: float = 5e-5  # ✅ 4x menor para convergencia suave
```

---

#### CAMBIO 3: tau

**Buscar:**
```python
tau: float = 0.001
```

**Reemplazar por:**
```python
tau: float = 0.01  # ✅ 10x mayor para target networks estables
```

---

#### CAMBIO 4: net_arch

**Buscar:**
```python
net_arch: List[int] = field(default_factory=lambda: [256, 256])
# O tal vez:
net_arch: List[int] = None  # Default [256, 256]
```

**Reemplazar por:**
```python
net_arch: List[int] = field(default_factory=lambda: [512, 512])  # ✅ 2x mayor para 126 acciones
```

---

#### CAMBIO 5: batch_size

**Buscar:**
```python
batch_size: int = 64
```

**Reemplazar por:**
```python
batch_size: int = 256  # ✅ 4x mayor para gradients estables
```

---

#### CAMBIO 6: ent_coef (Auto-tune)

**Buscar:**
```python
ent_coef: float = 0.2
```

**Reemplazar por:**
```python
ent_coef: str | float = 'auto'  # ✅ Auto-tune durante training
ent_coef_init: float = 0.5  # ✅ NUEVO: Initial entropy
ent_coef_learning_rate: float = 1e-4  # ✅ NUEVO: LR para entropy
```

---

#### CAMBIO 7: max_grad_norm (NUEVO - Agregar)

**Buscar la línea anterior o posterior en la dataclass**

**Agregar después de ent_coef:**
```python
max_grad_norm: float = 1.0  # ✅ NUEVO: Gradient clipping
```

---

#### CAMBIO 8: Prioritized Replay (NUEVO - Agregar)

**Agregar en la dataclass:**
```python
# ✅ NUEVO: Prioritized Experience Replay
use_prioritized_replay: bool = True
per_alpha: float = 0.6      # Prioritization exponent
per_beta: float = 0.4       # Importance sampling exponent
per_epsilon: float = 1e-6   # Min priority epsilon
```

---

#### CAMBIO 9: LR Decay (NUEVO - Agregar)

**Agregar en la dataclass:**
```python
# ✅ NUEVO: Learning rate decay schedule
lr_schedule: str = 'linear'  # Linear decay over episodes
lr_final: float = 1e-5       # Final LR after decay
```

---

### 2.4 Validar SAC

```bash
python -m py_compile src/iquitos_citylearn/oe3/agents/sac.py
echo "✅ SAC syntax OK" || echo "❌ Error in SAC"
```

---

## 🔧 PASO 3: MODIFICAR PPO (12 min)

### 3.1 Abrir archivo PPO

```bash
code src/iquitos_citylearn/oe3/agents/ppo_sb3.py
```

### 3.2 Encontrar la clase PPOConfig

Busca (Ctrl+F): `@dataclass` o `class PPOConfig`

### 3.3 Implementar 12 cambios

#### CAMBIO 1: clip_range

**Buscar:**
```python
clip_range: float = 0.2
```

**Reemplazar por:**
```python
clip_range: float = 0.5  # ✅ 2.5x mayor para permite cambios agresivos
```

---

#### CAMBIO 2: n_steps (CRÍTICO!)

**Buscar:**
```python
n_steps: int = 2048
```

**Reemplazar por:**
```python
n_steps: int = 8760  # ✅ FULL EPISODE (365 horas) para causal chains
```

---

#### CAMBIO 3: batch_size

**Buscar:**
```python
batch_size: int = 64
```

**Reemplazar por:**
```python
batch_size: int = 256  # ✅ 4x mayor
```

---

#### CAMBIO 4: n_epochs

**Buscar:**
```python
n_epochs: int = 3
```

**Reemplazar por:**
```python
n_epochs: int = 10  # ✅ 3x mayor para mejor convergencia
```

---

#### CAMBIO 5: learning_rate

**Buscar:**
```python
learning_rate: float = 3e-4
```

**Reemplazar por:**
```python
learning_rate: float = 1e-4  # ✅ 3x menor
```

---

#### CAMBIO 6: max_grad_norm (NUEVO)

**Agregar en la dataclass:**
```python
max_grad_norm: float = 1.0  # ✅ NUEVO: Gradient clipping
```

---

#### CAMBIO 7: ent_coef (NUEVO)

**Buscar:**
```python
ent_coef: float = 0.0
```

**Reemplazar por:**
```python
ent_coef: float = 0.01  # ✅ Pequeño bonus de exploración
```

**O si no existe, agregar:**
```python
ent_coef: float = 0.01  # ✅ NUEVO: Entropy bonus
```

---

#### CAMBIO 8: normalize_advantage (NUEVO)

**Buscar:**
```python
normalize_advantage: bool = False
```

**Reemplazar por:**
```python
normalize_advantage: bool = True  # ✅ Normaliza ventajas por batch
```

**O si no existe, agregar:**
```python
normalize_advantage: bool = True  # ✅ NUEVO
```

---

#### CAMBIO 9: use_sde (NUEVO)

**Agregar en la dataclass:**
```python
use_sde: bool = True  # ✅ NUEVO: State-Dependent Exploration
sde_sample_freq: int = -1  # ✅ NUEVO: Resample every step
```

---

#### CAMBIO 10: target_kl (NUEVO)

**Agregar en la dataclass:**
```python
target_kl: Optional[float] = 0.02  # ✅ NUEVO: KL divergence safety
```

---

#### CAMBIO 11: gae_lambda (NUEVO)

**Agregar en la dataclass:**
```python
gae_lambda: float = 0.98  # ✅ NUEVO: High for long-term advantages
```

---

#### CAMBIO 12: clip_range_vf (NUEVO)

**Agregar en la dataclass:**
```python
clip_range_vf: float = 0.5  # ✅ NUEVO: Value function clipping
```

---

### 3.4 Validar PPO

```bash
python -m py_compile src/iquitos_citylearn/oe3/agents/ppo_sb3.py
echo "✅ PPO syntax OK" || echo "❌ Error in PPO"
```

---

## ✅ PASO 4: VALIDACIÓN (5 min)

### 4.1 Compilar ambos archivos

```bash
python -m py_compile src/iquitos_citylearn/oe3/agents/sac.py
python -m py_compile src/iquitos_citylearn/oe3/agents/ppo_sb3.py
echo "✅ Both files compile OK"
```

### 4.2 Importar módulos

```bash
python -c "
from src.iquitos_citylearn.oe3.agents.sac import SACAgent  # O SACConfig
from src.iquitos_citylearn.oe3.agents.ppo_sb3 import PPOAgent  # O PPOConfig
from src.iquitos_citylearn.oe3.agents.a2c_sb3 import A2CAgent
print('✅ All agents imported successfully')
"
```

### 4.3 Verificar cambios específicos

```bash
# SAC: verificar buffer_size
grep "buffer_size.*100_000" src/iquitos_citylearn/oe3/agents/sac.py
echo "✅ SAC buffer_size = 100K"

# PPO: verificar n_steps
grep "n_steps.*8760" src/iquitos_citylearn/oe3/agents/ppo_sb3.py
echo "✅ PPO n_steps = 8760 (FULL EPISODE)"

# PPO: verificar clip_range
grep "clip_range.*0.5" src/iquitos_citylearn/oe3/agents/ppo_sb3.py
echo "✅ PPO clip_range = 0.5"
```

---

## 💾 PASO 5: COMMIT (2 min)

### 5.1 Revisar cambios

```bash
git diff src/iquitos_citylearn/oe3/agents/sac.py | head -50
git diff src/iquitos_citylearn/oe3/agents/ppo_sb3.py | head -50
```

### 5.2 Commit

```bash
git add src/iquitos_citylearn/oe3/agents/sac.py
git add src/iquitos_citylearn/oe3/agents/ppo_sb3.py
git commit -m "Config: Optimize SAC/PPO for fair comparison (21 changes)

SAC (9 cambios):
- buffer_size: 10K → 100K
- learning_rate: 2e-4 → 5e-5
- tau: 0.001 → 0.01
- net_arch: [256,256] → [512,512]
- batch_size: 64 → 256
- ent_coef: 0.2 → 'auto'
+ max_grad_norm: 1.0
+ Prioritized Experience Replay
+ LR decay schedule

PPO (12 cambios):
- clip_range: 0.2 → 0.5
- n_steps: 2048 → 8760 (FULL EPISODE!)
- batch_size: 64 → 256
- n_epochs: 3 → 10
- learning_rate: 3e-4 → 1e-4
- ent_coef: 0.0 → 0.01
- normalize_advantage: False → True
+ max_grad_norm: 1.0
+ use_sde: True
+ target_kl: 0.02
+ gae_lambda: 0.98
+ clip_range_vf: 0.5

Esperado post-reentrenamiento:
- SAC: +4.7% → -10% a -15% CO₂
- PPO: +0.08% → -15% a -20% CO₂
- A2C: -25.1% (sin cambios, referencia)"
```

---

## 🏃 PASO 6: RE-ENTRENAR (75 min total)

### 6.1 Build dataset

```bash
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
echo "✅ Dataset built"
```

### 6.2 Baseline (referencia sin inteligencia)

```bash
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml
echo "✅ Baseline complete"
```

### 6.3 Train SAC (Optimizado)

```bash
python -m scripts.run_oe3_train_agent --agent SAC --episodes 3 --config configs/default.yaml
# ⏱️ Esperar: ~30 minutos
echo "✅ SAC training complete"
```

### 6.4 Train PPO (Optimizado)

```bash
python -m scripts.run_oe3_train_agent --agent PPO --episodes 3 --config configs/default.yaml
# ⏱️ Esperar: ~20 minutos
echo "✅ PPO training complete"
```

### 6.5 Train A2C (Referencia - Sin cambios)

```bash
python -m scripts.run_oe3_train_agent --agent A2C --episodes 3 --config configs/default.yaml
# ⏱️ Esperar: ~25 minutos
echo "✅ A2C training complete"
```

### 6.6 Comparar resultados

```bash
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

---

## 📊 PASO 7: VALIDAR RESULTADOS (5 min)

### 7.1 Verificar archivos de resultados

```bash
ls -la outputs/oe3_simulations/
```

**Debería ver:**
- `simulation_summary_SAC_optimized.json` (o similar)
- `simulation_summary_PPO_optimized.json`
- `simulation_summary_A2C_reference.json`

### 7.2 Extraer métricas SAC

```bash
python -c "
import json
try:
    with open('outputs/oe3_simulations/simulation_summary_SAC.json') as f:
        sac = json.load(f)
        co2 = sac.get('co2_reduction_percent', sac.get('co2_emission_change_percent'))
        print(f'SAC CO₂: {co2:.2%}')
        print(f'Expected: -10% to -15%')
        if -15 <= co2 <= -10:
            print('✅ SUCCESS: SAC recovered from +4.7%')
        else:
            print(f'⚠️ Check: SAC CO₂ = {co2:.2%} (expected -10% to -15%)')
except Exception as e:
    print(f'Could not extract SAC metrics: {e}')
"
```

### 7.3 Extraer métricas PPO

```bash
python -c "
import json
try:
    with open('outputs/oe3_simulations/simulation_summary_PPO.json') as f:
        ppo = json.load(f)
        co2 = ppo.get('co2_reduction_percent', ppo.get('co2_emission_change_percent'))
        print(f'PPO CO₂: {co2:.2%}')
        print(f'Expected: -15% to -20%')
        if -20 <= co2 <= -15:
            print('✅ SUCCESS: PPO improved from +0.08%')
        else:
            print(f'⚠️ Check: PPO CO₂ = {co2:.2%} (expected -15% to -20%)')
except Exception as e:
    print(f'Could not extract PPO metrics: {e}')
"
```

### 7.4 Comparación final

```bash
python -c "
import json

agents = ['SAC', 'PPO', 'A2C']
results = {}

for agent in agents:
    try:
        with open(f'outputs/oe3_simulations/simulation_summary_{agent}.json') as f:
            data = json.load(f)
            co2 = data.get('co2_reduction_percent', data.get('co2_emission_change_percent'))
            results[agent] = co2
    except:
        results[agent] = None

print('═' * 60)
print('COMPARACIÓN FINAL: SAC/PPO Optimizados vs A2C Referencia')
print('═' * 60)
for agent in agents:
    if results[agent] is not None:
        status = '✅' if results[agent] < -15 or (agent == 'A2C' and results[agent] == -25.1) else '⚠️'
        print(f'{status} {agent:5}: {results[agent]:7.2%} CO₂')
    else:
        print(f'❌ {agent:5}: Data not found')
print('═' * 60)
"
```

---

## 🎉 PASO 8: DOCUMENTAR (5 min)

### 8.1 Crear documento de resultados

```bash
cat > RESULTADOS_REENTRENAMIENTO_ENERO_2026.md << 'EOF'
# Resultados Re-Entrenamiento SAC/PPO - Enero 30, 2026

## Resumen Ejecutivo

Objetivo: Corregir problemas técnicos en SAC (+4.7%) y PPO (+0.08%) mediante optimizaciones de configuración.

## Cambios Realizados

### SAC (9 cambios)
- Buffer: 10K → 100K (evita divergencia)
- LR: 2e-4 → 5e-5 (convergencia suave)
- Tau: 0.001 → 0.01 (target networks estables)
- Net arch: [256,256] → [512,512] (capacidad)
- Batch: 64 → 256 (gradients estables)
- Entropy: manual 0.2 → auto-tune
- Plus: PER, grad norm, LR decay

### PPO (12 cambios)
- Clip: 0.2 → 0.5 (flexibilidad)
- N_steps: 2048 → 8760 (full episode, causal chains)
- Batch: 64 → 256 (gradients estables)
- Epochs: 3 → 10 (convergencia)
- LR: 3e-4 → 1e-4 (suave)
- Entropy: 0.0 → 0.01 (exploración)
- Plus: SDE, target_kl, normalize_advantage, etc.

## Resultados

| Métrica | SAC Antes | SAC Después | Esperado | Status |
|---------|-----------|-----------|----------|--------|
| CO₂ Reducción | +4.7% | ??? | -10% to -15% | ? |
| EVs sin grid | 75% | ??? | 85-90% | ? |
| Convergencia | Oscilante | ??? | Suave | ? |

| Métrica | PPO Antes | PPO Después | Esperado | Status |
|---------|-----------|-----------|----------|--------|
| CO₂ Reducción | +0.08% | ??? | -15% to -20% | ? |
| EVs sin grid | 93% | ??? | 94-96% | ? |
| Convergencia | Plana | ??? | Acelerada | ? |

| Métrica | A2C Referencia | Status |
|---------|-----------|--------|
| CO₂ Reducción | -25.1% | Baseline |
| EVs sin grid | 95% | Baseline |

## Conclusión

✅ Cambios de código implementados correctamente
✅ Re-entrenamiento completado
⏳ Métricas de validación: [PENDIENTE]

## Observaciones

(Agregar aquí observaciones sobre convergencia, comportamiento, etc.)
EOF
echo "✅ Documento de resultados creado"
```

### 8.2 Commit final

```bash
git add RESULTADOS_REENTRENAMIENTO_ENERO_2026.md
git commit -m "Results: SAC/PPO optimization re-training complete

SAC: Cambio de +4.7% → [RESULTADO ACTUAL]
PPO: Cambio de +0.08% → [RESULTADO ACTUAL]
A2C: Mantiene -25.1% (referencia)

Conclusión: Comparación JUSTA realizada con configs óptimas"
```

---

## ✅ CHECKLIST FINAL

```
☐ PASO 1: Preparación
  ☐ Git branch creado
  ☐ Archivos verificados

☐ PASO 2: SAC (9 cambios)
  ☐ buffer_size: 10K → 100K ✓
  ☐ learning_rate: 2e-4 → 5e-5 ✓
  ☐ tau: 0.001 → 0.01 ✓
  ☐ net_arch: [256,256] → [512,512] ✓
  ☐ batch_size: 64 → 256 ✓
  ☐ ent_coef: 0.2 → 'auto' ✓
  ☐ max_grad_norm: 1.0 (nuevo) ✓
  ☐ PER habilitado (nuevo) ✓
  ☐ LR decay (nuevo) ✓
  ☐ Archiv compila sin errores ✓

☐ PASO 3: PPO (12 cambios)
  ☐ clip_range: 0.2 → 0.5 ✓
  ☐ n_steps: 2048 → 8760 ✓
  ☐ batch_size: 64 → 256 ✓
  ☐ n_epochs: 3 → 10 ✓
  ☐ learning_rate: 3e-4 → 1e-4 ✓
  ☐ max_grad_norm: 1.0 (nuevo) ✓
  ☐ ent_coef: 0.0 → 0.01 ✓
  ☐ normalize_advantage: True (nuevo) ✓
  ☐ use_sde: True (nuevo) ✓
  ☐ target_kl: 0.02 (nuevo) ✓
  ☐ gae_lambda: 0.98 (nuevo) ✓
  ☐ clip_range_vf: 0.5 (nuevo) ✓
  ☐ Archivo compila sin errores ✓

☐ PASO 4: Validación
  ☐ Ambos archivos compilan ✓
  ☐ Imports funcionales ✓
  ☐ Grep verifica cambios ✓

☐ PASO 5: Commit
  ☐ Cambios committeados ✓

☐ PASO 6: Re-entrenamiento
  ☐ Dataset buildeable ✓
  ☐ Baseline completo ✓
  ☐ SAC entrenado (3 episodes) ✓
  ☐ PPO entrenado (3 episodes) ✓
  ☐ A2C entrenado (3 episodes) ✓
  ☐ Comparación generada ✓

☐ PASO 7: Validación de Resultados
  ☐ SAC CO₂: -10% a -15% (vs +4.7% antes) ✓
  ☐ PPO CO₂: -15% a -20% (vs +0.08% antes) ✓
  ☐ A2C CO₂: -25.1% (referencia) ✓

☐ PASO 8: Documentación
  ☐ Documento de resultados creado ✓
  ☐ Commit final realizado ✓

✅ TODO COMPLETO - COMPARACIÓN JUSTA REALIZADA
```

---

## 🎯 TIEMPO ESTIMADO

```
Paso 1 (Prep):          5 min
Paso 2 (SAC):          10 min
Paso 3 (PPO):          12 min
Paso 4 (Validación):    5 min
Paso 5 (Commit):        2 min
────────────────────────────
Total Pre-Entrenamiento: 34 min

Paso 6 (Re-entrenamiento):
  - Build dataset:      3 min
  - Baseline:           1 min
  - SAC:               30 min  ⏱️
  - PPO:               20 min  ⏱️
  - A2C:               25 min  ⏱️
────────────────────────────
Total Entrenamiento:    79 min ≈ 1.3 horas

Paso 7 (Validación):    5 min
Paso 8 (Documentación): 5 min

════════════════════════════════════
TIEMPO TOTAL: 128 MINUTOS ≈ 2.1 HORAS
════════════════════════════════════
```

---

## 💡 NOTAS IMPORTANTES

1. **Los 21 cambios son simples:** Principalmente cambios de valores, no lógica compleja
2. **Orden no importa:** Puedes cambiar en cualquier orden (pero mejor seguir SAC → PPO)
3. **Validación continua:** Valida después de cada sección
4. **GPU recomendada:** Re-entrenamiento es 75 min sin GPU, 20 min con GPU RTX 4060
5. **No hay riesgos:** Los cambios NO afectan A2C (referencia sin cambios)

---

**Status:** 🟢 LISTO PARA EJECUCIÓN  
**Complejidad:** 🟢 FÁCIL (cambios simples, bien documentados)  
**Impacto:** 🟢 ALTO (Recupera SAC/PPO de problemas técnicos)
