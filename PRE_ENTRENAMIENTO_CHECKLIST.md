# 🚀 VERIFICACIÓN RÁPIDA PRE-ENTRENAMIENTO

**Ejecuta esto antes de lanzar el entrenamiento principal**

---

## ✅ Paso 1: Verificar Datos

```bash
python -c "
import pandas as pd
import numpy as np

# Solar
solar = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/weather.csv')
print(f'Solar: {len(solar)} rows (should be 8760)')

# Building demand (mall 2024)
building = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/Building_1.csv')
print(f'Building: {len(building)} rows (should be 8760)')
print(f'Non-shiftable load: min={building[\"non_shiftable_load\"].min():.0f}kW, max={building[\"non_shiftable_load\"].max():.0f}kW')

# Chargers
import glob
chargers = glob.glob('data/processed/citylearn/iquitos_ev_mall/Electric*_*.csv')
print(f'Chargers: {len(chargers)} files (should be 512 = 128*4)')

print('\n✓ Datos verificados')
"
```

**Salida esperada**:
```
Solar: 8760 rows (should be 8760)
Building: 8760 rows (should be 8760)
Non-shiftable load: min=788kW, max=2101kW
Chargers: 512 files (should be 512 = 128*4)

✓ Datos verificados
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
