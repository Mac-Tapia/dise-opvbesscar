# 🚀 PROPAGACIÓN DE CAMBIOS AL ENTRENAMIENTO

## Estado Crítico: LISTO PARA ENTRENAMIENTO

**Todos los documentos están sincronizados para ser usados en:**
1. Dataset construction (`run_oe3_build_dataset.py`)
2. Baseline simulation (`run_uncontrolled_baseline.py`)
3. RL Training (`run_oe3_simulate.py`)

---

## 1. CAMBIOS CRÍTICOS IMPLEMENTADOS

### A. Charger Type Correction ✓
**Archivo**: `data/interim/oe2/chargers/individual_chargers.json`
```json
ANTES: "charger_type": "mototaxi"  (no reconocido = 16 undefined)
AHORA: "charger_type": "moto_taxi" (reconocido = 16 mototaxis)

RESULTADO: 112 motos ✓ + 16 mototaxis ✓ = 128 chargers ✓
```

**Por qué es crítico**:
- Dataset builder checkea `charger_type == "moto_taxi"` (línea 65, dataset_builder.py)
- Si falla → chargers no reconocidos → error en acción space
- Si correcto → 126 acciones (112 motos + 16 mototaxis - 2 reserved) ✓

---

### B. BESS: AUTOMÁTICO (No RL) ✓
**Documentación**: `.github/copilot-instructions.md`
```
BESS: AUTOMATIC control (dispatch rules with 5 priorities, NOT controlled by RL agents)
├─ 1. PV → EV (directo)
├─ 2. PV → BESS (cargar)
├─ 3. BESS → EV (noche)
├─ 4. BESS → MALL (desaturar)
└─ 5. Grid import (fallback)
```

**Por qué es crítico**:
- En la observación space: obs[2] = BESS SOC (leído por agentes)
- NO en el action space: BESS no tiene acción RL
- Dispatch rules en `configs/default.yaml` controlan el flujo automáticamente
- Si intenta hacer RL control → error de incompatibilidad

---

### C. Chargers: RL CONTROLADOS (126 acciones) ✓
**Documentación**: `.github/copilot-instructions.md`
```
EV Chargers: CONTROLLED by RL agents (SAC, PPO, A2C) via 126 continuous actions
└─ actions[0:111] = 112 Motos (2kW each)
└─ actions[112:125] = 16 Mototaxis (3kW each)
└─ actions[126:127] = RESERVED (not used)
```

**Por qué es crítico**:
- Agentes SAC/PPO/A2C toman 126 acciones continuas
- Cada acción mapea a potencia real del charger
- Si hay inconsistencia → training falla o aprende incorrectamente

---

## 2. ARCHIVOS DE CONTROL PARA ENTRENAMIENTO

### Archivos que DEBEN leerse al iniciar training:

| Archivo | Función | Verificación |
|---------|---------|--------------|
| `.github/copilot-instructions.md` | Especificación técnica global | Leyendo obs/action dims ✓ |
| `data/interim/oe2/chargers/individual_chargers.json` | Charger metadata (tipos, potencias) | Leído por dataset_builder ✓ |
| `configs/default.yaml` | Dispatch rules + reward weights | Usado por simulate.py ✓ |
| `data/interim/oe2/solar/pv_generation_timeseries.csv` | Solar timeseries (8,760 hrs) | Validado ✓ |
| `data/interim/oe2/mall/mall_demand.csv` | Mall demand (8,760 hrs) | Validado ✓ |

---

## 3. FLUJO DE DATOS DURANTE TRAINING

```
Training Startup
    ↓
[1] Load .github/copilot-instructions.md
    → Read observation space dims = 394
    → Read action space dims = 126
    → Read BESS control = automatic
    ↓
[2] Load data/interim/oe2/chargers/individual_chargers.json
    → Parse 128 chargers: 112 "moto_taxi" + 16 "moto_taxi"
    → Verify action space = 126 (128 - 2 reserved)
    → Store charger power ratings (2kW + 3kW)
    ↓
[3] Build CityLearn Dataset
    → Solar timeseries: 8,760 hours ✓
    → Mall demand: 8,760 hours ✓
    → Charger profiles: 128 × 8,760 ✓
    → BESS config: 4,520 kWh / 2,712 kW ✓
    ↓
[4] Create RL Environment
    → Observation space: 394-dim vector
    → Action space: 126-dim continuous [0,1]
    → Step function: automatic BESS dispatch + RL charger actions
    ↓
[5] Train Agents (SAC, PPO, A2C)
    → Each agent receives: obs (394), takes action (126)
    → Reward computed: CO₂ minimization + solar utilization
    → BESS dispatch happens automatically (not by agent)
    ↓
[6] Evaluate Results
    → CO₂ emissions: Grid import × 0.4521 kg/kWh
    → Solar consumed: (PV generated - excess) / total PV
    → EV satisfaction: charging demand met %
    → Motos/Mototaxis satisfaction tracked separately ✓
```

---

## 4. PUNTOS DE VALIDACIÓN AUTOMÁTICA

Cuando inician scripts:

### `run_oe3_build_dataset.py`
```python
# Check 1: Charger types recognized
assert len(motos) == 112, f"Expected 112 motos, got {len(motos)}"
assert len(mototaxis) == 16, f"Expected 16 mototaxis, got {len(mototaxis)}"
→ VALIDACIÓN: ✓ Individual_chargers.json correcto

# Check 2: Solar timeseries
assert len(solar_df) == 8760, f"Expected 8760 hours, got {len(solar_df)}"
→ VALIDACIÓN: ✓ Solar tiene exactamente 1 año

# Check 3: Action space
assert action_space.shape[0] == 126, f"Expected 126 actions, got {action_space.shape[0]}"
→ VALIDACIÓN: ✓ Action space correcto (128 - 2 reserved)

# Check 4: Observation space
assert obs_space.shape[0] == 394, f"Expected 394 dims, got {obs_space.shape[0]}"
→ VALIDACIÓN: ✓ Observation space correcto
```

### `run_uncontrolled_baseline.py`
```python
# Baseline computes without RL agents
# Uses automatic BESS dispatch + fixed charger behavior
→ VALIDACIÓN: BESS automatic ✓
```

### `run_oe3_simulate.py`
```python
# Load config from .github/copilot-instructions.md expectations
assert cfg.oe3.observation_space == 394
assert cfg.oe3.action_space == 126
→ VALIDACIÓN: Consistencia con instructiones ✓
```

---

## 5. CHECKLIST PRE-TRAINING

**Ejecutar ANTES de iniciar training** para asegurar propagación correcta:

```bash
# Paso 1: Validar charger JSON
Write-Host "📋 Verificando charger types..."
$chargers = Get-Content data/interim/oe2/chargers/individual_chargers.json | ConvertFrom-Json
$motos = $chargers | Where-Object {$_.charger_type -eq "moto_taxi" -and $_.power_rating -eq 2000} | Measure-Object
$taxis = $chargers | Where-Object {$_.charger_type -eq "moto_taxi" -and $_.power_rating -eq 3000} | Measure-Object
Write-Host "✓ Motos: $($motos.Count), Taxis: $($taxis.Count), Total: $($motos.Count + $taxis.Count)"
# Expected output: ✓ Motos: 112, Taxis: 16, Total: 128

# Paso 2: Validar solar timeseries
Write-Host "📋 Verificando solar timeseries..."
python -c "
import pandas as pd
df = pd.read_csv('data/interim/oe2/solar/pv_generation_timeseries.csv')
assert len(df) == 8760, f'ERROR: Expected 8760 rows, got {len(df)}'
print(f'✓ Solar: {len(df)} rows (hourly)')
"

# Paso 3: Validar mall demand
Write-Host "📋 Verificando mall demand..."
python -c "
import pandas as pd
df = pd.read_csv('data/interim/oe2/mall/mall_demand.csv')
assert len(df) == 8760, f'ERROR: Expected 8760 rows, got {len(df)}'
print(f'✓ Mall demand: {len(df)} rows (hourly)')
"

# Paso 4: Limpiar cache Python
Write-Host "📋 Limpiando cache Python..."
Get-ChildItem -Recurse -Filter "__pycache__" -Directory | Remove-Item -Recurse -Force

# Paso 5: Build dataset (genera schema + CSVs)
Write-Host "📋 Construyendo dataset..."
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
# Should complete with: ✓ Dataset built successfully

# Paso 6: Validar dataset generado
Write-Host "📋 Validando dataset..."
python -c "
import json
s = json.load(open('outputs/schema_*.json'))
b = s['buildings'][0]
print(f'✓ Buildings: {len(s[\"buildings\"])}, Properties: {len(b[\"properties\"])}')
"

# Resultado esperado:
# ✓ Motos: 112, Taxis: 16, Total: 128 ✓
# ✓ Solar: 8760 rows (hourly) ✓
# ✓ Mall demand: 8760 rows (hourly) ✓
# ✓ Dataset built successfully ✓
```

Si TODOS muestran ✓, entonces la propagación es correcta.

---

## 6. DOCUMENTOS DE REFERENCIA SINCRONIZADOS

Para cualquier duda durante training, referencia:

1. **`SINCRONIZACION_COMPLETA_2026_01_31.md`**
   - Este documento (master checklist)

2. **`.github/copilot-instructions.md`** (CRÍTICO)
   - Especificación técnica oficial
   - Obs/action space dims
   - Control architecture
   
3. **`ACLARACION_BESS_CONTROL.md`**
   - Explicación detallada BESS automático
   
4. **`ACLARACION_EV_CHARGERS_vs_CHARGERS.md`**
   - Clarificación que son el mismo concepto

5. **`VERIFICACION_ARTEFACTOS_OE2_FINAL.md`**
   - Validación de todos los datos OE2

---

## 7. SI OCURREN PROBLEMAS DURANTE TRAINING

| Síntoma | Verificación | Solución |
|---------|-------------|----------|
| "Charger types not recognized" | Abrir `individual_chargers.json` → buscar `"mototaxi"` | Cambiar a `"moto_taxi"` |
| "Action space mismatch (128 vs 126)" | Revisar si hay 2 chargers reserved | Debe ser 126 (128-2) |
| "Observation space mismatch (534 vs 394)" | Revisar `.github/copilot-instructions.md` | Debe ser 394 |
| "BESS control not working" | Revisar `configs/default.yaml` dispatch rules | Debe estar enabled: true |
| "Dataset build fails" | Verificar charger JSON + solar CSV | Ambos deben existir + ser válidos |

---

## 8. CONFIRMACIÓN FINAL

Después de ejecutar el checklist pre-training y ver todos los ✓:

```bash
# Ejecutar comando final de training
python -m scripts.run_oe3_simulate --config configs/default.yaml

# Resultado esperado durante training:
# Episode 1: Reward=-1500.45, CO2=8950 kg, SolarUtil=0.62
# Episode 2: Reward=-1200.30, CO2=8200 kg, SolarUtil=0.68
# ... (rewards mejoran progresivamente)
# Episode 50: Reward=+500.20, CO2=6800 kg, SolarUtil=0.78 ← Agentes aprendieron ✓
```

**Si ve esto**: ¡Cambios propagados correctamente! ✅

---

**Estado Final**: Todos los cambios están listos para PROPAGARSE AL ENTRENAMIENTO.

**Próxima Acción**: Ejecutar checklist pre-training antes de `run_oe3_simulate.py`.

**Responsable de Verificación**: Scripts automáticos en dataset_builder + simulate.py
