# 🚀 EJECUCIÓN DEL PIPELINE COMPLETO - GUÍA RÁPIDA

## **COMANDO PRINCIPAL (Una sola línea)**

```bash
cd d:\diseñopvbesscar && .venv\Scripts\python.exe scripts/run_full_pipeline.py
```

## **¿Qué hace el pipeline?**

1. **PASO 1: Construcción de Dataset**
   - Carga artefactos OE2 (solar, chargers, BESS)
   - Genera 128 perfiles de carga de chargers
   - Crea schema CityLearn compatible
   - **Duración esperada**: 30-60 segundos

2. **PASO 2: Cálculo de Baseline**
   - Calcula referencia SIN control inteligente
   - Suma energía real de 128 chargers
   - Calcula CO₂ based on dataset real
   - **Duración esperada**: 10-20 segundos
   - **Resultado**: baseline_reference.json (~536,634 kg CO₂/año)

3. **PASO 3: Entrenamiento REAL de Agentes**
   - Entrena PPO con CityLearn real
   - Entrena SAC con CityLearn real
   - Entrena A2C con CityLearn real
   - Cada agente: 1 episodio de 8,760 timesteps
   - **Duración esperada**: 15-30 minutos total (CPU) o 5-10 minutos (GPU)
   - **Resultado**: training_summary_*.json con rewards de cada agente

4. **PASO 4: Comparación (opcional)**
   - Compara baseline vs agentes entrenados
   - Genera análisis de mejora

## **SALIDA ESPERADA**

Al terminar, deberías ver en `outputs/oe3_simulations/`:

```
baseline_reference.json           ← Referencia sin control
training_summary_YYYYMMDD_HHMMSS.json  ← Resultados entrenamiento
comparison_*.json                 ← Análisis comparativo (si aplica)
```

### **Contenido de baseline_reference.json**
```json
{
  "scenario": "baseline_no_control",
  "num_chargers": 128,
  "energy_kwh": 1186980,
  "co2_total_kg": 536634,
  "grid_import_kwh": 1186980,
  "carbon_intensity_kg_per_kwh": 0.451
}
```

### **Contenido de training_summary_*.json**
```json
{
  "timestamp": "2025-01-09 ...",
  "ppo": {
    "agent": "PPO",
    "episodes": 1,
    "completed_episodes": 1,
    "rewards_per_episode": [...],
    "mean_reward": -123.45,
    "total_time": 450.2,
    "success": true
  },
  "sac": {...},
  "a2c": {...}
}
```

---

## **REQUISITOS PREVIOS**

✅ Python 3.11+ instalado  
✅ Virtual environment `.venv` activo  
✅ Dependencias instaladas: `pip install -r requirements.txt`  
✅ Dataset OE2 en `data/interim/oe2/`  

### **Verificar requisitos**
```bash
# Ver si venv existe
dir .venv\Scripts\python.exe

# Ver si dependencias están OK
.venv\Scripts\pip list | findstr "citylearn stable-baselines3"
```

---

## **OPCIONES DE CUSTOMIZACIÓN**

### **Entrenar más episodios**

Editar `scripts/train_agents_real_v2.py`, línea ~430:
```python
episodes = 1  # Cambiar a 2, 3, 5, etc.
```

Luego ejecutar:
```bash
.venv\Scripts\python.exe scripts/train_agents_real_v2.py
```

### **Saltarse algunos pasos**

```bash
# Solo dataset + baseline (sin entrenamiento)
.venv\Scripts\python.exe scripts/build_dataset.py
.venv\Scripts\python.exe scripts/baseline_robust.py

# Solo entrenamiento (si dataset ya existe)
.venv\Scripts\python.exe scripts/train_agents_real_v2.py

# Solo comparación (si ambos resultados existen)
.venv\Scripts\python.exe scripts/compare_baseline_vs_agents.py
```

---

## **SOLUCIÓN DE PROBLEMAS**

### ❌ "Schema no encontrado"
```
✓ Solución: Ejecutar PASO 1 primero
  .venv\Scripts\python.exe scripts/build_dataset.py
```

### ❌ "No se encontraron chargers"
```
✓ Solución: Verificar carpeta
  dir data\processed\citylearn\iquitos_ev_mall\buildings\Mall_Iquitos\
  Deberías ver: charger_simulation_001.csv ... charger_simulation_128.csv
```

### ❌ Error de memoria (OOM) durante entrenamiento
```
✓ Solución 1: Reducir timesteps por episodio
  En train_agents_real_v2.py, cambiar:
  timesteps_per_episode=8760 → 4380  (medio año)

✓ Solución 2: Entrenar 1 agente a la vez
  .venv\Scripts\python.exe scripts/train_agents_real_v2.py
  (Editar main() para comentar agentes que no necesites)

✓ Solución 3: Usar CPU explícitamente
  Cambiar en train_agents_real_v2.py:
  device='auto' → device='cpu'
```

### ❌ "CUDA out of memory"
```
✓ Solución: Usar CPU en lugar de GPU
  En train_agents_real_v2.py, líneas ~155, 256, 363:
  device='auto' → device='cpu'
```

---

## **MONITOREO EN TIEMPO REAL**

Mientras se ejecuta el pipeline, puedes monitorear en otra terminal:

```bash
# Ver archivos siendo creados
dir outputs\oe3_simulations\ /s

# Ver último training result
type outputs\oe3_simulations\training_summary_*.json

# Ver tamaño de baseline
dir outputs\oe3_simulations\baseline_reference.json
```

---

## **DURACIÓN ESTIMADA**

| Componente | CPU (16GB RAM) | GPU (RTX 3060) |
|-----------|--------|--------|
| Dataset | 1 min | 1 min |
| Baseline | 10 seg | 10 seg |
| PPO (1 ep) | 5-8 min | 1-2 min |
| SAC (1 ep) | 7-10 min | 2-3 min |
| A2C (1 ep) | 3-5 min | 1-2 min |
| **TOTAL** | **16-34 min** | **5-9 min** |

---

## **ARCHIVOS IMPORTANTES**

- `scripts/run_full_pipeline.py` - Orquestador principal ✅
- `scripts/build_dataset.py` - Construcción de dataset ✅
- `scripts/baseline_robust.py` - Baseline con datos reales ✅
- `scripts/train_agents_real_v2.py` - Entrenamiento mejorado ✅
- `scripts/compare_baseline_vs_agents.py` - Comparación (opcional)

---

## **VERIFICACIÓN DE ÉXITO**

✅ Pipeline completado exitosamente si:

1. Aparecen sin errores los mensajes:
   ```
   ✅ DATASET CONSTRUCTION COMPLETED
   ✅ BASELINE COMPLETED
   ✅ TRAINING COMPLETED
   ```

2. Existen estos archivos en `outputs/oe3_simulations/`:
   - `baseline_reference.json` (< 1 KB)
   - `training_summary_YYYYMMDD_HHMMSS.json` (< 10 KB)

3. El JSON de training muestra `"success": true` para cada agente

---

## **PRÓXIMOS PASOS DESPUÉS DE LA EJECUCIÓN**

1. Examinar resultados:
   ```bash
   type outputs\oe3_simulations\training_summary_*.json
   type outputs\oe3_simulations\baseline_reference.json
   ```

2. Entrenar más episodios para mejor convergencia:
   - Editar `episodes = 5` en `train_agents_real_v2.py`
   - Re-ejecutar training

3. Ajustar hiperparámetros si rewards son muy negativos:
   - Cambiar learning rates
   - Cambiar batch sizes
   - Consultar [stable-baselines3 docs](https://stable-baselines3.readthedocs.io/)

---

**Creado**: 2025-01-09  
**Última actualización**: Pipeline versión 2 con manejo robusto de errores
