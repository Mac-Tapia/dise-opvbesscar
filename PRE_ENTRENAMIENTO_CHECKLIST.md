# ✅ CHECKLIST FINAL PRE-ENTRENAMIENTO

**27 de enero de 2026 - Cero errores Pylance**

---

## 🟢 VERIFICACIÓN CRÍTICA

```bash
# 1. Python version
python --version  # Debe mostrar Python 3.11.9

# 2. Pylance errors
# Abrir VS Code → Problems → debe estar VACÍO ✓

# 3. Dataset validation
python -c "import pandas as pd; df=pd.read_csv('data/interim/oe2/solar/pv_generation_timeseries.csv'); assert len(df)==8760; print('✓ Solar 8,760 rows OK')"

# 4. Chargers validation
python -c "import json; c=json.load(open('data/interim/oe2/chargers/individual_chargers.json')); assert len(c)==32; print('✓ Chargers 32 (128 sockets) OK')"

# 5. UTF-8 encoding
$env:PYTHONIOENCODING='utf-8'; python -c "print('✓ UTF-8 OK')"
```

**Resultado esperado:**
```
Python 3.11.9
✓ Solar 8,760 rows OK
✓ Chargers 32 (128 sockets) OK
✓ UTF-8 OK
✓ No hay errores en Problems
```

---

## ✅ Paso 2: Verificar Modelo Existente

```bash
python validate_a2c_mall_demand.py
```

**Salida esperada**:
```
Loading trained model from: checkpoints/A2C/a2c_mall_demand_2024.zip
✓ Model loaded correctly
✓ Predictions working:
    Timestep 0: action shape (128,), range [0.000-1.000]
    Timestep 1: action shape (128,), range [0.000-1.000]
    ...
✓ Validation passed!
```

---

## ✅ Paso 3: Entrenar (Primeras 100 Timesteps Test)

```bash
python -c "
import numpy as np
from stable_baselines3 import A2C
from iquitos_citylearn.envs.a2c_gymnasium_env import A2CGymnasiumEnv

# Test rápido: crear env y entrenar 100 steps
env = A2CGymnasiumEnv()
model = A2C('MlpPolicy', env, learning_rate=3e-4, verbose=1)
model.learn(total_timesteps=100)
print('\n✓ Training works correctly')
"
```

**Salida esperada**:
```
| timestep   | time/fps   | approx_kl | clip_fraction | loss | mean_reward |
|------------|------------|-----------|---------------|------|-------------|
| 100        | 1250       | 0.002     | 0.010         | 1.23 | -0.45       |

✓ Training works correctly
```

---

## ✅ Paso 4: Ejecutar Entrenamiento Completo

Una vez verificados pasos 1-3:

```bash
python train_a2c_local_data_only.py
```

**Salida esperada** (al final):
```
Episode 1: Completed 8760 timesteps
Total timesteps trained: 8760
Checkpoint saved: checkpoints/A2C/a2c_mall_demand_2024.zip
Training completed successfully!
```

---

## ⚠️ Si hay ERROR

### Error: "No such file or directory: weather.csv"
```bash
ls data/processed/citylearn/iquitos_ev_mall/
# Si directorio no existe:
python scripts/run_oe3_build_dataset.py --config configs/default.yaml
```

### Error: "Observation space mismatch"
```bash
# Asegurar que el checkpoint es compatible con env actual
rm checkpoints/A2C/a2c_mall_demand_2024.zip
# Reentrenar desde cero
python train_a2c_local_data_only.py
```

### Error: "Out of memory" (GPU)
```bash
# Usar CPU
export DEVICE=cpu
python train_a2c_local_data_only.py

# O reducir batch_size en código
```

---

## 📊 Monitoreo en Vivo

Mientras entrena, en otra terminal:

```bash
# Ver timesteps completados
watch -n 5 'tail -50 checkpoints/A2C/*.log 2>/dev/null || echo "Training..."'

# O ejecutar análisis en paralelo
python analyze_a2c_24hours.py
```

---

## 🎯 Checklist Final

- [ ] Paso 1: Datos verificados (8760 rows en solar + building)
- [ ] Paso 2: Modelo carga sin errores
- [ ] Paso 3: Training test (100 steps) funciona
- [ ] Paso 4: Entrenamiento completo ejecutándose
- [ ] Análisis ejecutado
- [ ] Resultados guardados en outputs/

---

**Si TODO está ✓**, ya puedes dejar corriendo:
```bash
python train_a2c_local_data_only.py
```

Tiempo esperado: 30-120 min (depende GPU/CPU)  
Output: `checkpoints/A2C/a2c_mall_demand_2024.zip` + logs
