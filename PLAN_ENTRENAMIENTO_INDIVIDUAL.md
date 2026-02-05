# 🚀 PLAN DE ENTRENAMIENTO INDIVIDUAL: SAC, PPO, A2C

**Fecha:** 2026-02-05  
**Auditoría:** ✅ COMPLETADA  
**Status:** 🟢 LISTO PARA ENTRENAR

---

## 📋 PRE-ENTRENAMIENTO CHECKLIST

```
✅ PASO 1: Auditoría completada
   └─ Ejecutar: python AUDITORIA_PREENTRENAMIENTO.py
   └─ Status: ✅ PASS

✅ PASO 2: Configuración validada
   └─ Documento: CONFIGURACION_VALIDADA_PREENTRENAMIENTO.md
   └─ Status: ✅ TODOS los parámetros validados

✅ PASO 3: Data integridad verificada
   └─ OE2 archivos: 5/5 presentes
   └─ CityLearn env: 394-dim obs, 129-dim actions
   └─ Status: ✅ TODOS datos cargados

✅ PASO 4: Directorios limpios
   └─ Checkpoints: nuevos (sin compatibles viejos)
   └─ Outputs: esperando generarse
   └─ Status: ✅ LIMPIO
```

---

## 🎯 FASE 1: ENTRENAR SAC (Soft Actor-Critic)

### 1.1 Comando

```bash
# Activar venv + Ejecutar SAC
.\.venv\Scripts\Activate.ps1; python train_sac_multiobjetivo.py
```

### 1.2 Qué Sucede

```
[SAC Initialization]
├─ Cargar dataset CityLearn v2 con 5 archivos OE2
│  ├─ chargers_real_hourly_2024.csv (8760×128)
│  ├─ bess_hourly_dataset_2024.csv (8760×11)
│  ├─ demandamallhorakwh.csv (8785×1)
│  ├─ chargers_real_statistics.csv (128×4)
│  └─ pv_generation_hourly_citylearn_v2.csv (8760×11)
│
├─ Crear ambiente CityLearn v2
│  ├─ Observation: 394-dim (solar, BESS, chargers, demand, time)
│  ├─ Action: 129-dim (BESS dispatch + 128 sockets)
│  ├─ Reward: Multiobjeto (CO₂, solar, cost, EV, stability)
│  └─ Episode: 8,760 timesteps/año
│
├─ Inicializar SAC agent
│  ├─ Device: CPU (sin GPU disponible)
│  ├─ Network: [256, 256] (optimizado CPU)
│  ├─ Learning rate: 3e-4
│  ├─ Batch size: 64
│  ├─ Buffer size: 1e6
│  └─ Episodes: 50
│
└─ Entrenar por 50 episodios
   ├─ Total timesteps: ~420,000 (50 × 8,760)
   ├─ Archivar checkpoint cada 50k steps
   ├─ Guardar metrics cada episode
   ├─ Duración: 10-15 horas (CPU)
   └─ GPU ADVERTENCIA: Sin CUDA, entrenamiento LENTO
```

### 1.3 Outputs Esperados

```
checkpoints/SAC/
├─ sac_checkpoint_50000_steps.zip
├─ sac_checkpoint_100000_steps.zip
├─ ... (cada 50k steps)
└─ sac_final_model.zip ← CRÍTICO

outputs/sac_training/
├─ result_sac.json ← CRÍTICO
│  {
│    "agent": "SAC",
│    "total_timesteps": 420000,
│    "total_episodes": 50,
│    "mean_reward": (flotante),
│    "co2_avoided_kg": (flotante),
│    "solar_utilization_pct": (0-100),
│    "ev_soc_avg": (0-100),
│    "datetime": "2026-02-05T...",
│    "device": "cpu"
│  }
│
├─ timeseries_sac.csv ← CRÍTICO
│  episode, timestep, total_reward, co2_grid_kg,
│  solar_utilized_kwh, ev_satisfaction, grid_import_kwh, ...
│  1, 1, -0.5, 123.4, 456.7, 0.8, 234.5, ...
│  1, 2, -0.4, 122.1, 452.3, 0.81, 233.2, ...
│  ... (8760 filas por episodio × 50 episodios = 438,000 filas)
│
└─ trace_sac.csv ← CRÍTICO
   step, episode, reward, done, ...
   1, 1, -0.5, false
   2, 1, -0.4, false
   ... (8760 × 50 = 438,000 filas)
```

### 1.4 Validación Post-SAC

```bash
# Ejecutar validador
python VALIDADOR_OUTPUTS_POSTENTRENAMIENTO.py

# Salida esperada:
# ✅ SAC PASS
#   Checkpoint: ✓ válido (XX MB)
#   Result JSON: ✓ válido (9 keys)
#   Timeseries: ✓ válido (438,000 filas)
#   Trace: ✓ válido (438,000 filas)

# Si FAIL: revisar outputs/sac_training/ directamente
ls -lah outputs/sac_training/
```

### 1.5 Métricas de Éxito SAC

| Métrica | Baseline | Target | Unidad |
|---------|----------|--------|--------|
| **CO₂ reduction** | 321,782 | <240,000 | kg/año |
| **Solar util** | N/A | 60-75 | % |
| **EV satisfaction** | N/A | >85 | % |
| **Mean reward** | N/A | >-10 | reward |
| **Convergence** | N/A | ~40 episodios | episodes |

---

## 🎯 FASE 2: ENTRENAR PPO (Proximal Policy Optimization)

### 2.1 Comando

```bash
# Después de completar SAC exitosamente
.\.venv\Scripts\Activate.ps1; python train_ppo_a2c_multiobjetivo.py
# (Sin argumentos - selecciona PPO por defecto)
```

### 2.2 Diferencias vs SAC

| Aspecto | SAC | PPO |
|--------|-----|-----|
| **Tipo** | Off-policy | On-policy |
| **Estabilidad** | Media | Alta |
| **Velocidad** | Lenta (replay) | Media |
| **BESS** | Excelente | Bueno |
| **CPU perf** | OK | Mejor |
| **Batch size** | 64 | 64 |
| **N steps** | - | 512 |
| **N epochs** | - | 10 |

### 2.3 Outputs PPO

```
checkpoints/PPO/
└─ ppo_final_model.zip

outputs/ppo_training/
├─ result_ppo.json
├─ timeseries_ppo.csv  (8760×50 = 438,000 filas)
└─ trace_ppo.csv       (8760×50 = 438,000 filas)
```

### 2.4 Duración PPO

- Entrenamiento: 8-12 horas (CPU, más rápido que SAC)
- Checkpoint: cada 100k steps
- Total timesteps: ~420,000

### 2.5 Métricas Esperadas PPO

| Métrica | SAC | PPO Target |
|---------|-----|-----------|
| **CO₂ reduction** | -25% | >28% |
| **Solar util** | 60% | 65% |
| **EV satisfaction** | 85% | 88% |

---

## 🎯 FASE 3: ENTRENAR A2C (Advantage Actor-Critic)

### 3.1 Comando

```bash
# Después de completar PPO exitosamente
.\.venv\Scripts\Activate.ps1; python train_ppo_a2c_multiobjetivo.py A2C
# O simplemente presionar cuando pida seleccionar agent si detecta parámetro A2C
```

### 3.2 Diferencias vs SAC/PPO

| Aspecto | SAC | PPO | A2C |
|--------|-----|-----|-----|
| **Tipo** | Off-policy | On-policy | On-policy |
| **Network** | Twin Q-networks | Single | Single |
| **Complejidad** | Alta | Media | BAJA |
| **CPU perf** | OK | Media | EXCELENTE |
| **Convergencia** | Lenta | Media | RÁPIDA |
| **Estabilidad** | Media | Alta | Baja-Media |

### 3.3 Outputs A2C

```
checkpoints/A2C/
└─ a2c_final_model.zip

outputs/a2c_training/
├─ result_a2c.json
├─ timeseries_a2c.csv  (438,000 filas)
└─ trace_a2c.csv       (438,000 filas)
```

### 3.4 Duración A2C

- Entrenamiento: 6-10 horas (CPU, MÁS RÁPIDO)
- Checkpoint: cada 50k steps
- Total timesteps: ~420,000

### 3.5 Métricas Esperadas A2C

| Métrica | SAC | PPO | A2C Target |
|---------|-----|-----|-----------|
| **CO₂ reduction** | -25% | -28% | >25% |
| **Solar util** | 60% | 65% | 62% |
| **EV satisfaction** | 85% | 88% | 85% |
| **Wall-clock time** | 10-15h | 8-12h | **6-10h** ← FASTER |

---

## 📊 PLAN TEMPORAL

```
DAY 1 (Día actual)
├─ 09:00 - Auditoría pre-entrenamiento (✅ COMPLETADA)
├─ 10:00 - Validar configuración (✅ COMPLETADA)
└─ 11:00 - Comenzar SAC training

DAY 1-2 (Evening)
├─ 22:00 - SAC still running (~11 horas elapsed)
├─ 23:00 - Sleep...

DAY 2 (Morning)
├─ 08:00 - SAC TERMINATED (duration: 15h @ CPU)
├─ 08:15 - Validar outputs SAC
├─ 08:30 - Comenzar PPO training
└─ 19:30 - PPO TERMINATED (duration: 11h)

DAY 2-3 (Evening)
├─ 19:45 - Validar outputs PPO
├─ 20:00 - Comenzar A2C training
└─ 02:00 - A2C TERMINATED (duration: 6h)

DAY 3 (Morning)
├─ 08:00 - Validar outputs A2C
├─ 08:30 - Comparar métricas SAC vs PPO vs A2C
├─ 09:00 - ENTRENAMIENTO COMPLETADO ✅
└─ 10:00 - Análisis resultados finales
```

---

## ✅ VALIDACIÓN COMPLETA

### Post-SAC Training

```bash
# 1. Ejecutar validador
python VALIDADOR_OUTPUTS_POSTENTRENAMIENTO.py

# 2. Verificar archivos
ls -la checkpoints/SAC/sac_final_model.zip
ls -la outputs/sac_training/result_sac.json

# 3. Inspeccionar result_sac.json
cat outputs/sac_training/result_sac.json | python -m json.tool

# 4. Verificar timeseries (primeras 5 líneas)
head -5 outputs/sac_training/timeseries_sac.csv

# 5. Contar filas
wc -l outputs/sac_training/timeseries_sac.csv
# Esperado: 438,001 (438,000 data + 1 header)
```

### Post-PPO Training

```bash
# Mismo que SAC pero con archivos ppo_*
python VALIDADOR_OUTPUTS_POSTENTRENAMIENTO.py
# Verificar: PPO PASS
```

### Post-A2C Training

```bash
# Mismo que PPO pero con archivos a2c_*
python VALIDADOR_OUTPUTS_POSTENTRENAMIENTO.py
# Verificar: A2C PASS
```

---

## 🔒 Garantías Implementadas

✅ **Datos obligatorios:** 5 archivos OE2 MUST-LOAD (no fallback)  
✅ **Pesos correctos:** co2=0.30, solar=0.20, cost=0.10, ev=0.30, stability=0.10  
✅ **Ambiente real:** 394-dim obs con TODOS datos, 129-dim actions  
✅ **Outputs garantizados:** Si entrenamiento completa, archivos existirán  
✅ **Validación post-training:** Script automático verificará integridad  
✅ **No hay conflictos:** Checkpoints previos NO existen (nuevo training)  

---

## ⚠️ ADVERTENCIAS IMPORTANTES

### GPU No Disponible

```
Sistema actual: CPU mode
└─ Entrenamiento LENTO (6-15 horas por agente)
└─ Total estima: 24-37 horas para 3 agentes
└─ Recomendación: Ejecutar durante noche/fin de semana
```

### Si Entrenamiento Falla

```
Posibles causas:
1. Memoria RAM insuficiente
   → Reducir: batch_size = 32, buffer_size = 500k
   
2. Datos OE2 faltando
   → Verificar: python VERIFICAR_DATOS_REALES_5_OBLIGATORIOS.py
   
3. CityLearn env error
   → Verificar: python VERIFICAR_CITYLEARN_CONFIG.py
   
4. GPU out of memory (si hubiera GPU)
   → Reducir: network_arch = [128, 128]
```

---

## 📈 COMPARATIVA ESPERADA (3 Agentes)

```
╔════════════════════════════════════════════════════╗
║         SAC        │       PPO        │      A2C   ║
╠════════════════════════════════════════════════════╣
║ CO₂: -25%          │ CO₂: -28%        │ CO₂: -25%  ║
║ Solar: 60%         │ Solar: 65%       │ Solar: 62% ║
║ EV sat: 85%        │ EV sat: 88%      │ EV sat: 85%║
║ Time: 10-15h       │ Time: 8-12h      │ Time: 6-10h║
║ Stability: Medium  │ Stability: High  │ Stability: M║
╚════════════════════════════════════════════════════╝

RECOMENDACIÓN PRODUCCIÓN:
→ Use better of PPO/SAC based on CO₂ reduction
→ A2C como fallback ultra-rápido si se repite entrenamiento
```

---

## 🚀 INICIO ENTRENAMIENTO

```bash
# FASE 1: SAC
echo "═══════════════════════════════════════════"
echo "FASE 1: SAC TRAINING"
echo "═══════════════════════════════════════════"
.\.venv\Scripts\Activate.ps1; python train_sac_multiobjetivo.py

# Esperar ~10-15 horas...

echo ""
echo "✅ SAC COMPLETADO"
echo "Validando outputs..."
python VALIDADOR_OUTPUTS_POSTENTRENAMIENTO.py

# FASE 2: PPO
echo "═══════════════════════════════════════════"
echo "FASE 2: PPO TRAINING"
echo "═══════════════════════════════════════════"
.\.venv\Scripts\Activate.ps1; python train_ppo_a2c_multiobjetivo.py

# Espererar ~8-12 horas...

echo ""
echo "✅ PPO COMPLETADO"
python VALIDADOR_OUTPUTS_POSTENTRENAMIENTO.py

# FASE 3: A2C
echo "═══════════════════════════════════════════"
echo "FASE 3: A2C TRAINING"
echo "═══════════════════════════════════════════"
.\.venv\Scripts\Activate.ps1; python train_ppo_a2c_multiobjetivo.py

# Esperar ~6-10 horas...

echo ""
echo "✅ A2C COMPLETADO"
python VALIDADOR_OUTPUTS_POSTENTRENAMIENTO.py

echo ""
echo "═══════════════════════════════════════════"
echo "✅ ENTRENAMIENTO COMPLETO - 3 AGENTES LISTOS"
echo "═══════════════════════════════════════════"
```

---

## 📋 DOCUMENTACIÓN GENERADA

| Documento | Propósito |
|-----------|----------|
| `AUDITORIA_PREENTRENAMIENTO.py` | Verificar sistema antes de entrenar |
| `CONFIGURACION_VALIDADA_PREENTRENAMIENTO.md` | Spec de configuración |
| `VALIDADOR_OUTPUTS_POSTENTRENAMIENTO.py` | Verificar outputs después |
| `PLAN_ENTRENAMIENTO_INDIVIDUAL.md` | este archivo |

---

## ✅ READY TO START

```
Estado: 🟢 LISTO PARA ENTRENAR

✓ Auditoría completada
✓ Configuración validada
✓ Data verificada (5/5 OE2 archivos)
✓ Checkpoints limpios
✓ Outputs directorios creados
✓ Pesos multiobjetivo correctos
✓ Rewards functions implementadas

Siguiente paso: Ejecutar FASE 1 (SAC)
  python train_sac_multiobjetivo.py
```

