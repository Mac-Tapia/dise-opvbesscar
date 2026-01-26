# 🚀 Lanzar Entrenamiento OE3 - AHORA

## ✅ Estado Actual

- **Código**: 0 errores Pyright (Phase 5 ✓)
- **Agentes**: Ultra-optimizados (SAC, PPO, A2C) ✓
- **GPU**: RTX 4060 al máximo ✓
- **Datasets**: Validados (8,760 hrs, 128 chargers) ✓
- **Configuración**: `configs/default.yaml` finalizada ✓

---

## 🎯 Lanzar Pipeline Completo (5-8 horas)

```bash
# Windows PowerShell
py -3.11 -m scripts.run_oe3_simulate --config configs/default.yaml
```

**Qué ocurre**:
1. **Dataset Builder** (3-5 min)
   - Carga datos OE2 (solar hourly 8,760 hrs, chargers, BESS)
   - Genera schema CityLearn v2
   
2. **Baseline** (10-15 min)
   - Referencia sin control RL
   - Baseline CO₂: ~10,200 kg/año
   
3. **SAC Training** (1.5-2 h)
   - Off-policy, sample-efficient
   - Esperado: ~7,300 kg/año (-33%)
   - Checkpoint: `checkpoints/SAC/latest.zip`
   
4. **PPO Training** (1.5-2 h)
   - On-policy, estable
   - Esperado: ~7,100 kg/año (-36%) ⭐
   - Checkpoint: `checkpoints/PPO/latest.zip`
   
5. **A2C Training** (1.5-2 h)
   - On-policy, rápido
   - Esperado: ~7,500 kg/año (-30%)
   - Checkpoint: `checkpoints/A2C/latest.zip`
   
6. **Comparación Final** (<1 min)
   - Tabla CO₂ vs baseline
   - Archivo: `outputs/oe3_simulations/simulation_summary.json`

---

## 📊 Resultados Esperados

| Agente | CO₂ (kg/año) | Reducción | GPU VRAM | Tiempo |
|--------|-------------|-----------|----------|--------|
| Baseline | 10,200 | — | — | 10-15 min |
| SAC | 7,300 | -33% | 6.8 GB | 35-45 min |
| PPO | 7,100 | -36% ⭐ | 6.2 GB | 40-50 min |
| A2C | 7,500 | -30% | 6.5 GB | 30-35 min |

---

## 🔧 Opciones Alternativas

### Solo Dataset (validar datos OE2)
```bash
py -3.11 -m scripts.run_oe3_build_dataset --config configs/default.yaml
```
Duración: ~3-5 min

### Solo Baseline (referencia sin RL)
```bash
py -3.11 -m scripts.run_uncontrolled_baseline --config configs/default.yaml
```
Duración: ~10-15 min

### Comparar Resultados (después del entrenamiento)
```bash
py -3.11 -m scripts.run_oe3_co2_table --config configs/default.yaml
```
Duración: <1 min

---

## 🖥️ Monitoreo en Tiempo Real

En otra terminal (mientras corre el entrenamiento):

```bash
python scripts/monitor_training_live_2026.py
```

Muestra:
- Agente actual
- Episodio
- Reward
- Total timesteps
- Temperatura GPU

---

## ⚙️ Configuraciones Especializadas

### SAC (Exploración máxima)
```yaml
batch_size: 1024
buffer_size: 10_000_000
learning_rate: 1.0e-3
entropy_coef: 0.20      # Máxima
```

### PPO (Máxima estabilidad)
```yaml
batch_size: 512
n_epochs: 25
learning_rate: 3.0e-4
target_kl: 0.003       # Estricto
```

### A2C (Velocidad)
```yaml
batch_size: 1024
learning_rate: 2.0e-3
n_steps: 16
```

---

## 📂 Outputs

Después del entrenamiento (5-8 horas):

```
outputs/oe3_simulations/
├── simulation_summary.json          # Resumen CO₂, solar, costos
├── SAC_timeseries.csv               # SAC step-by-step
├── PPO_timeseries.csv               # PPO step-by-step
├── A2C_timeseries.csv               # A2C step-by-step
└── COMPARISON_TABLE.txt             # Tabla final

checkpoints/
├── SAC/latest.zip                   # Modelo SAC final
├── PPO/latest.zip                   # Modelo PPO final (mejor)
└── A2C/latest.zip                   # Modelo A2C final
```

---

## ✨ Próximos Pasos (Después del entrenamiento)

1. **Validar resultados**
   ```bash
   py -3.11 -m scripts.run_oe3_co2_table --config configs/default.yaml
   ```

2. **Inspeccionar checkpoints**
   ```bash
   python -c "from stable_baselines3 import PPO; m=PPO.load('checkpoints/PPO/latest.zip'); print(f'Total timesteps: {m.num_timesteps}')"
   ```

3. **Deploy FastAPI (modelo serving)**
   ```bash
   docker-compose -f docker-compose.fastapi.yml up -d
   # Acceder a: http://localhost:8000/docs
   ```

4. **Scale con Kubernetes**
   ```bash
   kubectl apply -f docker/k8s-deployment.yaml
   ```

---

## 🐛 Troubleshooting Rápido

| Problema | Solución |
|----------|----------|
| "ModuleNotFoundError" | `pip install -r requirements-training.txt` |
| GPU out of memory | Reducir batch_size en `configs/default.yaml` |
| Python version | Usar `py -3.11` no `python` |
| Dataset error (128 chargers) | Verificar `data/interim/oe2/chargers/individual_chargers.json` |

---

## 📝 Git Status

**Commit más reciente**: `2ca39f5f` (README updated with agent configs)  
**Branch**: `main`  
**Remote**: GitHub synchronized ✓

---

## 🎬 ¡LISTO! Ejecutar:

```bash
py -3.11 -m scripts.run_oe3_simulate --config configs/default.yaml
```

**Tiempo estimado**: 5-8 horas en RTX 4060  
**Monitorear**: `python scripts/monitor_training_live_2026.py` (otra terminal)  
**Resultado esperado**: PPO con -36% CO₂ (7,100 kg/año)

---

*Actualizado: 2026-01-26*  
*Estado: ✅ Listo para lanzar*
