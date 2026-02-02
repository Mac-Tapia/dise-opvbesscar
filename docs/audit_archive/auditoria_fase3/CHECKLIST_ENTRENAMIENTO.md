# ✅ CHECKLIST DE EJECUCIÓN - ENTRENAMIENTO OE3 (2026-02-01)

**Fecha:** 2026-02-01  
**Status:** ✅ Limpiezas completadas, sistema listo para entrenamiento  
**Versión:** Final 1.0  

---

## 🎯 ANTES DE EMPEZAR

### ✅ Verificación Pre-Training (5 min)

```bash
# 1. Navegar al directorio
cd d:\diseñopvbesscar

# 2. Verificar Python 3.11 EXACTO
python --version  # Debe ser 3.11.x (REQUERIDO)

# 3. Verificar ambiente
pip list | findstr -E "citylearn|torch|stable-baselines3"

# 4. Verificar datos OE2 (solar, BESS, chargers)
Test-Path data\interim\oe2\solar\pv_generation_timeseries.csv
# Resultado: True (debe existir con 8760 filas exactas)

# 5. Validar imports del sistema
python -c "from src.iquitos_citylearn.oe3 import simulate, make_sac, make_ppo, make_a2c; print('✅ All imports OK')"
# Resultado: ✅ All imports OK

# 6. Verificar GPU (opcional)
python -c "import torch; print(f'GPU Available: {torch.cuda.is_available()}')"
```

---

## 🚀 OPCIÓN 1: ENTRENAMIENTO COMPLETO (Recomendado)

### Pipeline: Dataset → Baseline → SAC → PPO → A2C

```bash
# PASO 1: Construir dataset CityLearn
python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# PASO 2: Ejecutar training completo en secuencia
python -m scripts.run_training_sequence --config configs/default.yaml

# PASO 3: Generar tabla de resultados comparativos
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

**Tiempo total:** ~40 minutos (GPU RTX 4060)  
**Salidas:** 
- `checkpoints/{SAC,PPO,A2C}/` - Modelos entrenados
- `outputs/oe3_simulations/result_*.json` - Métricas por agente
- `outputs/oe3_simulations/timeseries_*.csv` - Datos horarios

---

## 🤖 OPCIÓN 2: ENTRENAMIENTOS INDIVIDUALES

### Si prefieres entrenar agentes por separado:

```bash
# DATASET (ejecutar primero - 1 vez)
python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# BASELINE (sin control RL, para comparación)
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml

# Entrenar SAC (off-policy, mejor muestra eficiencia)
python -m scripts.run_sac_only --config configs/default.yaml --sac-episodes 10

# Entrenar PPO (on-policy, más estable)
python -m scripts.run_ppo_only --config configs/default.yaml --ppo-timesteps 100000

# Entrenar A2C (on-policy simple, benchmark)
python -m scripts.run_a2c_only --config configs/default.yaml --a2c-timesteps 100000

# Tabla de resultados
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

**Ventaja:** Puedes controlar cada agente por separado  
**Desventaja:** Más tiempo total

---

## ⚡ OPCIÓN 3: DEMO RÁPIDA (5 minutos)

### Para validar que todo funciona:

```bash
# Dataset (1 min)
python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# Baseline + SAC pequeño (4 min)
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml
python -m scripts.run_sac_only --config configs/default.yaml --sac-episodes 1

# Verificar resultados
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

**Propósito:** Validar pipeline funciona sin hacer entrenamiento completo

---

## 📊 MONITOREO EN VIVO (OPCIONAL)

### Terminal 1: Ejecutar training
```bash
python -m scripts.run_training_sequence --config configs/default.yaml
```

### Terminal 2: Ver uso de GPU (cada 1 segundo)
```bash
nvidia-smi -l 1
```

### Terminal 3: Ver checkpoints siendo creados
```bash
watch -n 5 "Get-ChildItem -Path checkpoints -Recurse | Sort-Object LastWriteTime -Descending | Select-Object -First 10"
```

---

## 🎛️ CONFIGURACIÓN (configs/default.yaml)

### Parámetros principales para ajustar:

```yaml
# RL TRAINING
oe3:
  training:
    sac:
      episodes: 10                      # Aumentar a 20 para más convergencia
      batch_size: 512                   # GPU out of mem? Reducir a 256
      learning_rate: 5e-5               # Defecto: bien calibrado
    
    ppo:
      timesteps: 100000                 # Aumentar a 200000 para mejor convergencia
      n_steps: 1024                     # Defecto: bien calibrado
      batch_size: 128
    
    a2c:
      timesteps: 100000                 # Similar a PPO
      n_steps: 256
      learning_rate: 3e-4

# REWARD WEIGHTS
  rewards:
    co2_weight: 0.75                    # 75% = minimizar CO₂ (PRIMARY)
    solar_weight: 0.20                  # 20% = maximizar autoconsumo solar
    cost_weight: 0.05                   # 5% = minimizar costo
    # Total: 100%

# GRID CONSTANTS
  grid:
    carbon_intensity_kg_per_kwh: 0.4521 # Grid Iquitos (térmica)
    tariff_usd_per_kwh: 0.20           # Tarifa eléctrica
```

---

## ✅ CHECKLIST POST-TRAINING

Después de ejecutar el training:

```
✅ Verificar checkpoints creados:
   [ ] checkpoints/sac/sac_final.zip
   [ ] checkpoints/ppo/ppo_final.zip
   [ ] checkpoints/a2c/a2c_final.zip

✅ Verificar resultados en outputs:
   [ ] outputs/oe3_simulations/result_sac.json
   [ ] outputs/oe3_simulations/result_ppo.json
   [ ] outputs/oe3_simulations/result_a2c.json
   [ ] outputs/oe3_simulations/result_uncontrolled.json

✅ Verificar timeseries (datos horarios):
   [ ] outputs/oe3_simulations/timeseries_sac.csv (8760 rows)
   [ ] outputs/oe3_simulations/timeseries_ppo.csv (8760 rows)
   [ ] outputs/oe3_simulations/timeseries_a2c.csv (8760 rows)

✅ Tabla de comparación:
   [ ] outputs/oe3_simulations/co2_comparison.csv
```

---

## 📈 INTERPRETAR RESULTADOS

### Archivo: result_*.json

```json
{
  "agent": "sac",
  "carbon_kg": 7200000,              ← CO₂ total (menor = mejor)
  "grid_import_kwh": 350000,         ← Importación grid (menor = mejor)
  "pv_generation_kwh": 3300000,      ← Solar disponible
  "ev_charging_kwh": 150000,         ← EVs cargadas
  "reward_total_mean": 0.65          ← Recompensa promedio (0.65 = bueno)
}
```

### Comparar agentes

```
CO₂ Reduction vs Baseline:
  SAC:  -26% → ✅ Excelente (off-policy eficiente)
  PPO:  -24% → ✅ Bueno (on-policy estable)
  A2C:  -22% → ✅ Aceptable (simple baseline)
  
Si todos tienen reducción positiva → ✅ Sistema funciona correctamente
```

---

## 🚨 TROUBLESHOOTING

| Problema | Solución |
|----------|----------|
| `ModuleNotFoundError: No module named 'src'` | `cd d:\diseñopvbesscar` antes de ejecutar |
| `Error: Python 3.12 not supported` | Instalar Python 3.11 EXACTO de python.org |
| `CUDA out of memory` | Reducir batch_size: `512 → 256 → 128` en config.yaml |
| `Solar timeseries must have 8760 rows` | Verificar `pv_generation_timeseries.csv` tiene exactamente 8760 filas |
| `No chargers found` | Verificar `data/interim/oe2/chargers/individual_chargers.json` existe |
| `Checkpoint not found` | Usar `--reset-checkpoints true` para iniciar desde cero |
| `Schema validation error` | Ejecutar `run_oe3_build_dataset` nuevamente (regenerar schema) |

---

## 🎓 DOCUMENTACIÓN ADICIONAL

Después de completar el training, puedes consultar:

- **Flujo de trabajo:** [FLUJO_TRABAJO_TRAINING_ACTUAL.md](FLUJO_TRABAJO_TRAINING_ACTUAL.md)
- **Inicio rápido:** [QUICKSTART.md](QUICKSTART.md)
- **Instalación:** [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)
- **Copilot instructions:** [.github/copilot-instructions.md](.github/copilot-instructions.md)

---

## 💡 TIPS DE OPTIMIZACIÓN

1. **Entrenar en GPU:** Agregar `--device cuda:0` en comandos
2. **Resume checkpoints:** Usar `--reset-checkpoints false` para continuar entrenamientos
3. **Checkpoints frecuentes:** Modificar `checkpoint_freq_steps` en config.yaml
4. **Monitoreo en vivo:** Usar [monitor_training_live.py](scripts/monitor_training_live.py)
5. **Guardar resultados:** Salidas automáticamente en `outputs/oe3_simulations/`

---

## ✨ STATUS FINAL

✅ Sistema limpio y optimizado  
✅ Scripts esenciales en `scripts/`  
✅ Configuración centralizada en `config.yaml`  
✅ Documentación clara y accesible  
✅ **LISTO PARA ENTRENAMIENTO INMEDIATO**  

---

**Última actualización:** 2026-02-01  
**Responsable:** OE3 Optimization Module  
**Versión:** 1.0 - Limpieza y Optimización Final
