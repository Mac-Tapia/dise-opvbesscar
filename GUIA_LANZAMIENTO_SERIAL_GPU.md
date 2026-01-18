# ✓ LANZAMIENTO DE ENTRENAMIENTO SERIAL - GPU MÁXIMO

## Estado de Verificación

✅ **Todos los requisitos están listos:**

### OE2 (Preparación de datos)

- ✅ Solar: 8760h profile + PV sizing
- ✅ BESS: 2000 kWh + hourly simulation
- ✅ Chargers: 128 profiles (112 motos 2kW + 16 mototaxis 3kW)

### OE3 (Dataset)

- ✅ Dataset CityLearn construido: `data/processed/citylearn/iquitos_ev_mall/`
  - 2 buildings (Grid + PV/BESS)
  - 128 charger profiles
  - 17 Weather files
  - Schemas JSON válidos

### GPU

- ✅ CUDA disponible
- ✅ Memoria GPU suficiente
- ✅ Variables de entorno optimizadas

---

## 🚀 LANZAR ENTRENAMIENTO

### Opción 1: PowerShell (RECOMENDADO)

```powershell
# Activar venv primero
.venv\Scripts\Activate.ps1

# Ejecutar entrenamiento
.\train_agents_serial.ps1
```

### Opción 2: Python directo

```bash
# Activar venv
.venv\Scripts\activate

# Ejecutar
python train_agents_serial_gpu.py
```

### Opción 3: Script clásico de OE3

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml --skip-dataset
```

---

## 📊 Orden de Entrenamiento (SERIAL)

El script `train_agents_serial_gpu.py` ejecuta:

1. **SAC** (Soft Actor-Critic)
   - Device: CUDA
   - Episodes: 5
   - Batch: 65,536 (máximo)
   - AMP: Enabled
   - Tiempo estimado: 1.5-2h

2. **PPO** (Proximal Policy Optimization)
   - Device: CPU (más estable)
   - Episodes: 5
   - n_steps: 16,384
   - Tiempo estimado: 2-2.5h

3. **A2C** (Advantage Actor-Critic)
   - Device: CUDA
   - Episodes: 5
   - n_steps: 32,768
   - AMP: Enabled
   - Tiempo estimado: 1.5-2h

**Total estimado: 5-6.5 horas**

---

## 📈 Monitoreo en Tiempo Real

### Ver checkpoints mientras entrena

```bash
python monitor_checkpoints.py
```

### Ver archivos de training

```bash
ls -lah outputs/oe3/checkpoints/SAC/
ls -lah outputs/oe3/checkpoints/PPO/
ls -lah outputs/oe3/checkpoints/A2C/
```

---

## ✓ Resultados Esperados

### Después de completar

**Archivo: `outputs/oe3/simulations/simulation_summary.json`**

```json
{
  "best_agent": "SAC",
  "pv_bess_uncontrolled": {
    "carbon_kg": 7847032,
    "simulated_years": 1,
    ...
  },
  "pv_bess_results": {
    "SAC": { "carbon_kg": 7547021 },
    "PPO": { "carbon_kg": 7578734 },
    "A2C": { "carbon_kg": 7615072 }
  },
  "reductions": {
    "SAC": { "reduction_pct": 0.0381 },
    ...
  }
}
```

**Archivo: `outputs/oe3/simulations/co2_comparison.md`**
Tabla comparativa con reducciones %

---

## 🛠️ Configuración de Hiperparámetros

Editar `configs/default.yaml` → sección `oe3.evaluation`:

```yaml
evaluation:
  agents:
    - SAC
    - PPO
    - A2C
  
  sac:
    episodes: 5           # ← Aumentar para mejor convergencia
    batch_size: 65536     # ← Máximo recomendado
    device: cuda          # GPU
    use_amp: true         # Mixed Precision
  
  ppo:
    episodes: 5
    device: cpu           # CPU para estabilidad
    batch_size: 16384
  
  a2c:
    episodes: 5
    device: cuda          # GPU
    use_amp: true
```

---

## ⚠️ Troubleshooting

### GPU no detectada

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

- Si False → Instalar CUDA Toolkit compatible

### Memory error (OOM)

- Reducir `batch_size` en config
- Reducir `n_steps` para PPO/A2C
- Usar `device: cpu`

### Entrenamiento lento

- Verificar `use_amp: true` en config
- Aumentar `batch_size`
- Reducir `log_interval`

### Reanudar entrenamiento interrumpido

```bash
python -m scripts.run_oe3_simulate --config configs/default.yaml --skip-dataset --skip-uncontrolled
```

Los checkpoints se detectan automáticamente.

---

## 📋 Checklist Pre-Lanzamiento

- ✅ `.venv\Scripts\activate` ejecutado
- ✅ `configs/default.yaml` verificado
- ✅ `data/interim/oe2/` completo (solar, bess, chargers)
- ✅ `data/processed/citylearn/iquitos_ev_mall/` existe
- ✅ GPU disponible: `python -c "import torch; print(torch.cuda.is_available())"`
- ✅ Espacio disco: ~20 GB (checkpoints + outputs)

---

## 📞 Comandos Útiles

```bash
# Ver status de entrenamiento actual
python show_training_status.py

# Monitorear memoria GPU
nvidia-smi -l 1

# Limpiar checkpoints viejos
rm -rf outputs/oe3/checkpoints/

# Resetear simulación (cuidado!)
rm outputs/oe3/simulations/*

# Ver logs detallados
tail -f analyses/oe3/training/*.log
```

---

## ✨ Siguiente: Post-Entrenamiento

Una vez completado, ejecutar:

```bash
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

Para generar tabla final de CO₂ y reducciones.

---

**Estado: LISTO PARA LANZAMIENTO** ✅
Fecha: 2025-01-15
