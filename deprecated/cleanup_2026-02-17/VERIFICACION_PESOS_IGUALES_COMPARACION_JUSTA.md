# ✅ VERIFICACIÓN: PESOS IGUALES PARA COMPARACIÓN JUSTA

**Fecha:** 2026-02-16  
**Objetivo:** Confirmar que PPO, SAC y A2C usan **EXACTAMENTE los mismos pesos** para objetivos  
**Alcance:** Solo pesos de recompensa (otros hiperparámetros pueden variar)

---

## 📊 TABLA COMPARATIVA - PESOS DE RECOMPENSA

| Objetivo | PPO | SAC | A2C | Estado |
|----------|-----|-----|-----|--------|
| **CO2** | 0.35 | 0.35 | 0.35 ✅ | ✓ Identical |
| **Cost** | 0.10 | 0.10 | 0.10 ✅ | ✓ Identical |
| **Solar** | 0.20 | 0.20 | 0.20 ✅ | ✓ Identical |
| **Vehicles (EV Satisfaction)** | 0.30 | 0.30 | 0.30 ✅ | ✓ Identical |
| **Grid Stability** | 0.05 | 0.05 | 0.05 ✅ | ✓ Identical |
| **EV Utilization** | 0.00 | 0.00 | 0.00 ✅ | ✓ Identical |
| **TOTAL** | **1.00** | **1.00** | **1.00** ✅ | ✓ Verified |

---

## 🔍 AUDITORÍA DE CÓDIGO

### PPO (scripts/train/train_ppo_multiobjetivo.py, línea 282-288)
```python
REWARD_WEIGHTS_V6: Dict[str, float] = {
    'co2': 0.35,                   # ✅ Standard co2_focus
    'solar': 0.20,                 # ✅ Standard co2_focus
    'vehicles_charged': 0.30,      # ✅ Standard co2_focus
    'cost': 0.10,                  # ✅ Standard co2_focus
    'grid_stable': 0.05,           # ✅ Standard co2_focus
    'ev_utilization': 0.00         # ✅ Standard co2_focus
}
```

**Sincronización:** Comentarios refieren: "SINCRONIZADO SAC: ..."

---

### SAC (scripts/train/train_sac_multiobjetivo.py, línea 1408)
```python
reward_weights = create_iquitos_reward_weights(priority="co2_focus")
```

**Que expande a** (src/dataset_builder_citylearn/rewards.py, línea 852):
```python
"co2_focus": MultiObjectiveWeights(
    co2=0.35,
    cost=0.10,
    solar=0.20,
    ev_satisfaction=0.30,  # Mapped from 'vehicles_charged' in PPO/A2C
    ev_utilization=0.00,
    grid_stability=0.05
)
```

**Sincronización:** Valor pasado explícitamente en línea 1408

---

### A2C (scripts/train/train_a2c_multiobjetivo.py, línea 198-204) - **ACTUALIZADO 2026-02-16**
```python
REWARD_WEIGHTS_V6: Dict[str, float] = {
    'co2': 0.35,               # ✅ ACTUALIZADO DESDE 0.45 → 0.35 (SINCRONIZADO)
    'cost': 0.10,              # ✅ ACTUALIZADO DESDE (no existía) → 0.10 (SINCRONIZADO)
    'solar': 0.20,             # ✅ ACTUALIZADO DESDE 0.15 → 0.20 (SINCRONIZADO)
    'vehicles_charged': 0.30,  # ✅ ACTUALIZADO DESDE 0.25 → 0.30 (SINCRONIZADO)
    'grid_stable': 0.05,       # ✅ Ya era 0.05 (CORRECTO)
    'ev_utilization': 0.00     # ✅ AGREGADO (SINCRONIZADO)
}
```

**Cambios realizados:** 
- Removido: `bess_efficiency: 0.05` (no existe en SAC/PPO)
- Removido: `prioritization: 0.05` (no existe en SAC/PPO)
- Agregado: `cost: 0.10` (faltaba en A2C)
- Actualizado: `co2` (0.45 → 0.35)
- Actualizado: `solar` (0.15 → 0.20)
- Actualizado: `vehicles_charged` (0.25 → 0.30)
- Agregado: `ev_utilization: 0.00`

---

## 🎯 IMPLICACIONES

### Antes (v9.1)
```
PPO: [0.35, 0.10, 0.20, 0.30, 0.05, 0.00] ✓ Consistente con SAC
SAC: [0.35, 0.10, 0.20, 0.30, 0.05, 0.00] ✓ co2_focus standard
A2C: [0.45, 0.15, 0.25, 0.05, 0.05, 0.05] ✗ DIFERENTE (6 objetivos distintos)
```

**Resultado:** Comparación NO JUSTA - A2C optimizaba diferentes objetivos

### Después (v9.3 - 2026-02-16)
```
PPO: [0.35, 0.10, 0.20, 0.30, 0.05, 0.00] ✓ Consistente con SAC
SAC: [0.35, 0.10, 0.20, 0.30, 0.05, 0.00] ✓ co2_focus standard
A2C: [0.35, 0.10, 0.20, 0.30, 0.05, 0.00] ✓ IGUAL A AMBOS (SINCRONIZADO)
```

**Resultado:** Comparación JUSTA - Cualquier diferencia en CO₂/solar/EV es por algoritmo, no por objetivos

---

## ✅ VALIDACIÓN DE SINCRONIZACIÓN

### Checksum de Pesos
```
PPO:  0.35 + 0.10 + 0.20 + 0.30 + 0.05 + 0.00 = 1.00 ✓
SAC:  0.35 + 0.10 + 0.20 + 0.30 + 0.05 + 0.00 = 1.00 ✓
A2C:  0.35 + 0.10 + 0.20 + 0.30 + 0.05 + 0.00 = 1.00 ✓
```

### Mapeo de Nombres
| Nombre en PPO/A2C | Nombre en SAC | Valor |
|---|---|---|
| co2 | co2 | 0.35 |
| cost | cost | 0.10 |
| solar | solar | 0.20 |
| vehicles_charged | ev_satisfaction | 0.30 |
| grid_stable | grid_stability | 0.05 |
| ev_utilization | ev_utilization | 0.00 |

---

## 🚀 PRÓXIMOS PASOS

1. ✅ **Pesos actualizados** en A2C (línea 198-204)
2. ⏳ **Limpiar checkpoints A2C** (si existen) para evitar cargar modelos con pesos antiguos
3. ⏳ **Entrenar A2C** con nuevos pesos
4. ⏳ **Comparar resultados:** PPO vs SAC vs A2C con **pesos idénticos**

### Comando de verificación (opcional)
```bash
python -c "
from scripts.train.train_ppo_multiobjetivo import REWARD_WEIGHTS_V6 as ppo_w
from scripts.train.train_a2c_multiobjetivo import REWARD_WEIGHTS_V6 as a2c_w
from dataset_builder_citylearn.rewards import create_iquitos_reward_weights

# SAC weights via function
sac_w = create_iquitos_reward_weights('co2_focus')

# Comparison
print('PPO:', dict(sorted(ppo_w.items())))
print('SAC:', {k:v for k,v in [(a,'co2',sac_w.co2),(b,'cost',sac_w.cost),(c,'solar',sac_w.solar),(d,'ev_satisfaction',sac_w.ev_satisfaction),(e,'grid_stability',sac_w.grid_stability),(f,'ev_utilization',sac_w.ev_utilization)]})
print('A2C:', dict(sorted(a2c_w.items())))
"
```

---

## 📝 NOTAS TÉCNICAS

### Razón del cambio en A2C
A2C tenía una estructura diferente (incluyó `bess_efficiency` y `prioritization`) que no existían en SAC/PPO. Para garantizar una **comparación algorítmica justa**, se normalizaron todos los objetivos al estándar `co2_focus` de SAC.

### Impacto esperado
- **A2C**: Aumentará enfoque en CO₂ (0.35 vs 0.45), reducirá en vehículos (0.30 vs 0.25)
- **Comparación**: Ahora valid para auditar qué algoritmo es mejor bajo los **mismos objetivos**
- **Resultados**: Pueden variar respecto a v9.1 de A2C, pero serán comparables con PPO/SAC

### Archivos modificados
- ✅ `scripts/train/train_a2c_multiobjetivo.py` (línea 198-204)

### Archivos SIN cambios (solo lectura)
- `src/dataset_builder_citylearn/rewards.py` (presets, solo lectura)
- `scripts/train/train_sac_multiobjetivo.py` (ya usaba co2_focus, no cambios necesarios)
- `scripts/train/train_ppo_multiobjetivo.py` (ya tenía pesos correctos, no cambios necesarios)

---

**Status:** ✅ SINCRONIZACIÓN COMPLETADA - Lista para entrenamiento comparativo

