# 🔍 AUDITORÍA COMPARATIVA: SAC vs PPO vs A2C - CRITICAL ISSUES IDENTIFIED

## Executive Summary

**Resultado:** Se han identificado **8 ISSUES CRÍTICOS** en PPO y A2C que pueden causar los mismos problemas que en SAC (divergencia, undertraining, instabilidad).

**Status:** Ready to apply coordinated fixes

---

## CRITICAL ISSUES FOUND

### Issue #1: ❌ MISSING DATASET VALIDATION IN PPO.learn()
**SAC Status:** ✅ Implementado (_validate_dataset_completeness)
**PPO Status:** ❌ SÍ EXISTE (línea ~250-280) - **PERO NUNCA SE LLAMA EN learn()**
**A2C Status:** ❌ SÍ EXISTE (línea ~220-250) - **PERO NUNCA SE LLAMA EN learn()**

**Problem:** Métodos learn() no llaman a _validate_dataset_completeness()
**Impact:** Entrenamiento puede ejecutar con datos corruptos sin avisar
**Fix:** Agregar validación al inicio de learn()

```python
# DEBE ESTAR EN learn() (línea ~300+):
def learn(self, total_timesteps: Optional[int] = None, **kwargs):
    # VALIDACIÓN CRÍTICA: Verificar dataset completo antes de entrenar
    self._validate_dataset_completeness()  # ← FALTA ESTO
```

---

### Issue #2: ❌ MISSING TORCH SETUP IN A2C
**SAC Status:** ✅ _setup_torch_backend() llamado en __init__
**PPO Status:** ✅ _setup_torch_backend() llamado en __init__
**A2C Status:** ❌ **FALTA COMPLETAMENTE - no hay _setup_torch_backend()**

**Problem:** A2C no configura CUDA/torch backend
**Impact:** GPU no optimizada, Mixed Precision deshabilitado, CUDA no seeded
**Fix:** Agregar _setup_torch_backend() a A2C

---

### Issue #3: ❌ INCOMPLETE DEVICE INFO IN A2C
**SAC Status:** ✅ get_device_info() retorna info completa
**PPO Status:** ✅ get_device_info() retorna info completa
**A2C Status:** ❌ **NO EXISTE - missing get_device_info()**

**Problem:** No se puede diagnosticar estado del GPU
**Impact:** Debugging difícil en problemas de device
**Fix:** Agregar get_device_info() a A2C (copiar de SAC/PPO)

---

### Issue #4: ⚠️ INCONSISTENT ENTROPY DECAY SCHEDULES
**SAC Status:** ✅ ent_coef_schedule = "linear", ent_coef_final = 0.001
**PPO Status:** ✅ ent_coef_schedule = "linear", ent_coef_final = 0.001
**A2C Status:** ⚠️ ent_coef_schedule = "linear", ent_coef_final = 0.0001 **← 10X LOWER**

**Problem:** A2C usa entropy final 10x más baja que SAC/PPO
**Impact:** Puede causar convergencia prematura en A2C
**Fix:** Harmonizar: A2C ent_coef_final = 0.001 (como SAC/PPO)

```python
# ANTES (A2C):
ent_coef_final: float = 0.0001  # 10x menor que SAC/PPO

# DESPUÉS:
ent_coef_final: float = 0.001   # Consistente con SAC/PPO
```

---

### Issue #5: ⚠️ INCONSISTENT REWARD SCALING
**SAC Status:** ✅ reward_scale = 1.0
**PPO Status:** ✅ reward_scale = 0.1
**A2C Status:** ✅ reward_scale = 0.1 **PERO config.py línea ~57 dice "0.1: evita Q-explosion"**

**Problem:** SAC (off-policy) usa 1.0, PPO/A2C (on-policy) usan 0.1 - OK, pero inconsistencia
**Impact:** Menor, pero puede afectar comparación de agents
**Fix:** Documentar WHY diferente (OK como está)

---

### Issue #6: ❌ MISSING NORMALIZE_ADVANTAGE FLAG IN PPO
**SAC Status:** N/A (off-policy)
**PPO Status:** ❌ **NO TIENE normalize_advantage FLAG** (SB3 tiene built-in pero no documentado)
**A2C Status:** ✅ normalize_advantages: bool = True

**Problem:** PPO no expone control sobre advantage normalization
**Impact:** Inconsistencia con A2C, menos transparencia
**Fix:** Agregar a PPOConfig:
```python
normalize_advantage: bool = True  # ← AGREGAR (SB3 built-in parameter)
```

---

### Issue #7: ⚠️ PPO HUBER LOSS IMPLEMENTATION
**SAC Status:** N/A (off-policy)
**PPO Status:** ✅ SÍ TIENE use_huber_loss = True + custom policy class (línea ~300-350)
**A2C Status:** ✅ SÍ TIENE use_huber_loss = True + custom policy class (línea ~350-400)

**Problem:** Implementaciones CASI IDÉNTICAS pero copy-pasted (no DRY)
**Impact:** Maintenance burden, diferencias podrían divergir
**Fix:** Considerar extraer a agent_utils.py (pero LOW PRIORITY - funciona)

---

### Issue #8: ❌ MISSING LEARNING RATE SCHEDULE PASSING TO SB3
**SAC Status:** ✅ learning_rate passed (constant only)
**PPO Status:** ⚠️ lr_schedule = "linear" EN CONFIG pero **NO SE USA AL CREAR PPO()**
**A2C Status:** ⚠️ lr_schedule = "linear" EN CONFIG pero **NO SE USA AL CREAR A2C()**

**Problem:** Config define schedule pero SB3 no lo recibe
**Impact:** Learning rate nunca decae - stays constant (defeats purpose)
**Fix:** Implementar learning rate schedule callback o usar SB3's learning_rate parameter correctly

---

## SUMMARY: ISSUES BY SEVERITY

| Issue | SAC | PPO | A2C | Severity | Fix Time |
|-------|-----|-----|-----|----------|----------|
| #1: Missing validation call in learn() | ✅ | ❌ | ❌ | CRITICAL | 1 min |
| #2: Missing torch setup | ✅ | ✅ | ❌ | HIGH | 2 min |
| #3: Missing get_device_info | ✅ | ✅ | ❌ | MEDIUM | 1 min |
| #4: Inconsistent entropy decay final | ✅ | ✅ | ⚠️ | MEDIUM | 1 min |
| #5: Inconsistent reward scaling | ✅ | ⚠️ | ✅ | LOW | 0 min (OK as is) |
| #6: Missing normalize_advantage flag | N/A | ❌ | ✅ | LOW | 2 min |
| #7: Duplicate Huber loss code | N/A | ✅ | ✅ | LOW | 5 min (extract) |
| #8: LR schedule not passed to SB3 | ✅ | ⚠️ | ⚠️ | HIGH | 3 min |

---

## RECOMMENDED ACTION PLAN

**Phase 1 (CRITICAL - 5 min):**
1. Add _validate_dataset_completeness() call to PPO.learn() and A2C.learn()
2. Add _setup_torch_backend() and get_device_info() to A2C
3. Harmonize A2C ent_coef_final from 0.0001 → 0.001

**Phase 2 (HIGH - 3 min):**
4. Implement learning rate schedule callback for PPO and A2C

**Phase 3 (MEDIUM - 2 min):**
5. Add normalize_advantage to PPOConfig
6. Verify Huber loss implementations are consistent

---

## IMPLEMENTATION ORDER

```
1. PPO: Add _validate_dataset_completeness() call
2. A2C: Add _validate_dataset_completeness() call
3. A2C: Add _setup_torch_backend() method
4. A2C: Add get_device_info() method
5. A2C: Change ent_coef_final to 0.001
6. PPO: Add normalize_advantage to config
7. PPO & A2C: Verify LR schedule passing (if needed)
```

---

## FILES TO MODIFY

- `src/iquitos_citylearn/oe3/agents/ppo_sb3.py` - **Lines ~130 (config), ~320 (learn method)**
- `src/iquitos_citylearn/oe3/agents/a2c_sb3.py` - **Lines ~60 (config), ~180-200 (new methods), ~240 (learn method)**

---

**Prepared by:** GitHub Copilot  
**Date:** 2026-02-03 00:55 UTC  
**Status:** Ready for implementation
