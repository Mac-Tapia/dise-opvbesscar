# PLAN DE ACCIÓN - CORRECCIONES INMEDIATAS
**Auditoría de código línea por línea - 2026-02-18**

---

## 📋 RESUMEN EJECUTIVO

Se identificaron **3 problemas CRÍTICOS** que afectan comparación justa de agentes:

1. **BESS_MAX_KWH desactualizado** en SAC y A2C (1700 vs 2000)
2. **Reward structure inconsistente** en SAC (single-objective vs multi-objective)
3. **Clases obsoletas** sin impacto inmediato pero that should be documented

**Tiempo estimado para corregir todo:** 15 minutos

---

## 🔴 PASO 1: Corregir BESS Capacity en SAC

**Archivo:** `scripts/train/train_sac.py`
**Línea:** ~78
**Problema:** BESS_MAX_KWH_CONST = 1700.0 (antiguo v5.4)
**Solución:** Cambiar a 2000.0 (correcto v5.8)

### Código ANTES:
```python
# Line 78 in train_sac.py
BESS_MAX_KWH_CONST: float = 1700.0  # Capacidad maxima BESS (referencia normalizacion)
```

### Código DESPUÉS:
```python
# Line 78 in train_sac.py
BESS_MAX_KWH_CONST: float = 2000.0  # Capacidad maxima BESS (referencia normalizacion) [FIXED v5.8]
```

### Comando para verificar ANTES:
```bash
grep -n "BESS_MAX_KWH_CONST.*1700" scripts/train/train_sac.py
```

### Comando para verificar DESPUÉS:
```bash
grep -n "BESS_MAX_KWH_CONST.*2000" scripts/train/train_sac.py
```

---

## 🔴 PASO 2: Corregir BESS Capacity en A2C

**Archivo:** `scripts/train/train_a2c.py`
**Línea:** ~72
**Problema:** BESS_MAX_KWH_CONST = 1700.0 (antiguo v5.4)
**Solución:** Cambiar a 2000.0 (correcto v5.8)

### Código ANTES:
```python
# Line 72 in train_a2c.py
BESS_MAX_KWH_CONST: float = 1700.0  # Capacidad maxima BESS (referencia normalizacion)
```

### Código DESPUÉS:
```python
# Line 72 in train_a2c.py
BESS_MAX_KWH_CONST: float = 2000.0  # Capacidad maxima BESS (referencia normalizacion) [FIXED v5.8]
```

### Comando para verificar:
```bash
grep -n "BESS_MAX_KWH_CONST.*1700" scripts/train/train_a2c.py
```

---

## 🔴 PASO 3: Corregir Reward Structure en SAC

**Archivo:** `scripts/train/train_sac.py`
**Línea:** ~1844 a 1858
**Problema:** Usando reward minimalista (single-objective grid_import)
**Solución:** Usar MultiObjectiveReward (como PPO/A2C)

### Código ACTUAL (INCORRECTO):
```python
# SAC Lines 1844-1858
if grid_import >= 800.0:
    reward = -0.0003
elif grid_import >= 300.0:
    reward = 0.0
else:
    reward = +0.0005

reward = float(np.clip(reward, -0.0005, 0.0005))
```

### Código CORRECTO (MULTIOBJETIVO):
```python
# SAC Lines 1844-1858 - REEMPLAZAR CON ESTO:
# Usar MultiObjectiveReward como PPO/A2C
try:
    multi_reward = self.reward_calculator.get_reward(
        solar_generation_kwh=solar_h,
        ev_charging_kwh=chargers_demand_h,
        ev_soc_avg=charger_satisfaction,
        bess_soc=bess_soc,
        hour=h % 24,
        ev_demand_kwh=chargers_demand_h
    )
    reward = multi_reward
except:
    # Fallback a simple reward si hay error
    reward = -np.clip(grid_import / 500.0, 0.0, 0.5)

reward = float(np.clip(reward, -1.0, 1.0))
```

### Comando para verificar ANTES:
```bash
grep -A5 "v9.2 RADICAL" scripts/train/train_sac.py | head -20
```

---

## ✅ PASO 4: Verificar que todos los cambios se aplicaron

### Test script:
```bash
python << 'EOF'
import sys
sys.path.insert(0, '.')

# Test 1: BESS_MAX_KWH_CONST en SAC
with open('scripts/train/train_sac.py', 'r') as f:
    sac_content = f.read()
    if 'BESS_MAX_KWH_CONST: float = 2000.0' in sac_content:
        print("[OK] SAC BESS_MAX_KWH_CONST = 2000.0")
    else:
        print("[X] SAC BESS_MAX_KWH_CONST aun fuera de date")

# Test 2: BESS_MAX_KWH_CONST en A2C
with open('scripts/train/train_a2c.py', 'r') as f:
    a2c_content = f.read()
    if 'BESS_MAX_KWH_CONST: float = 2000.0' in a2c_content:
        print("[OK] A2C BESS_MAX_KWH_CONST = 2000.0")
    else:
        print("[X] A2C BESS_MAX_KWH_CONST aun fuera de date")

# Test 3: SAC Reward no es single-objective
if 'v9.2 RADICAL' in sac_content:
    print("[X] SAC aun usa v9.2 RADICAL (single-objective)")
else:
    print("[OK] SAC no usa v9.2 RADICAL")

EOF
```

---

## 📊 Impacto de cambios

### Antes (Estado actual):
```
SAC  BESS: 1700 kWh ❌  | Reward: single-objective ❌
PPO  BESS: 2000 kWh ✅  | Reward: multi-objective ✅  
A2C  BESS: 1700 kWh ❌  | Reward: multi-objective ✅

Resultado: Comparación INJUSTA entre agentes
```

### Después (Post-corrección):
```
SAC  BESS: 2000 kWh ✅  | Reward: multi-objective ✅  
PPO  BESS: 2000 kWh ✅  | Reward: multi-objective ✅  
A2C  BESS: 2000 kWh ✅  | Reward: multi-objective ✅  

Resultado: Comparación JUSTA - Solo el algoritmo varia
```

---

## 🚀 PRÓXIMOS PASOS (Después de correcciones críticas)

### Una vez corregidos 🔴 CRÍTICOS, proceder con 🟡 MEDIO:

1. **Crear `src/common_constants.py`**
   - Centralizar 90 líneas de constantes duplicadas
   - Importar en SAC, PPO, A2C

2. **Crear `src/dataset_columns.py`**
   - Centralizar 540 líneas de definiciones de columnas
   - Importar en SAC, PPO, A2C

3. **Estandarizar variables CO₂**
   - Usar consistentemente: `episode_co2_direct_kg`, `episode_co2_indirect_solar_kg`, `episode_co2_indirect_bess_kg`
   - Actualizar en SAC, PPO, A2C

4. **Eliminar código dead en SAC**
   - Clases: VehicleSOCState, ChargingScenario, VehicleSOCTracker
   - Variables: vehicle_simulator
   - Métodos no llamados

5. **Implementar tracking mensual en SAC/PPO**
   - Copiar implementación de A2C

---

## 📝 CHECKLIST DE VALIDACIÓN

- [ ] SAC BESS_MAX_KWH_CONST = 2000.0 (línea ~78)
- [ ] A2C BESS_MAX_KWH_CONST = 2000.0 (línea ~72)
- [ ] SAC Reward usa MultiObjectiveReward (no v9.2 RADICAL)
- [ ] Ejecutar: `python validate_code_quality.py` - Sin errores
- [ ] Ejecutar: `python scripts/train/train_sac.py --test` - Sin import errors
- [ ] Ejecutar: `python scripts/train/train_ppo.py --test` - Sin import errors
- [ ] Ejecutar: `python scripts/train/train_a2c.py --test` - Sin import errors
- [ ] Entrenamiento rápido (1 episodio) de SAC en GPU
- [ ] Entrenamiento rápido (1 episodio) de PPO en GPU
- [ ] Entrenamiento rápido (1 episodio) de A2C en GPU

---

## 🎯 BENEFICIOS

✅ **Comparación justa** entre SAC vs PPO vs A2C
✅ **BESS normalized** correctamente en los 3 agentes
✅ **Reward structure** idéntico en los 3 agentes
✅ **Auditoría CO₂** más precisa y consistente
✅ **Código limpio** facilitará futuras auditorías

---

**Tiempo estimado:** 15 minutos
**Complejidad:** TRIVIAL (3 line changes)
**Impacto:** CRÍTICO (afecta toda comparación de resultados)

---

Fin del Plan | 2026-02-18
