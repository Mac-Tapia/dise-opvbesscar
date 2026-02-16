# MONITOREO DE ENTRENAMIENTO PPO - GUÍA RÁPIDA

## Estado Actual
✅ **Entrenamiento PPO ejecutándose** (background)
✅ **Datos OE2 compilados** (Solar, Chargers 38, BESS, Mall)
✅ **Monitor PPO activo** (monitorear_ppo_nuevo.ps1 - cada 10 seg)

## Progreso Actual
```
Steps       : 26,000+ / 87,600 (96.8%+)
Episodio    : 2+
CO2 Grid    : 1,444,907 kg
CO2 Evitado : 4,201,147 kg
Velocidad   : ~600-700 timesteps/seg
```

## Comandos para Monitorear

### 1. Ver las últimas 20 líneas (INSTANTÁNEO)
```powershell
Get-Content entrenamiento_ppo.log -Tail 20
```

### 2. Ver solo líneas de progreso por episodio
```powershell
Select-String "Steps:|COMPLETADO" entrenamiento_ppo.log | Select-Object -Last 15
```

### 3. Ver contabilidad CO2
```powershell
Select-String "CO2_grid:|CO2_evitado:|Reduccion" entrenamiento_ppo.log | Select-Object -Last 10
```

### 4. Ver solo errores/warnings
```powershell
Select-String "WARNING|ERROR" entrenamiento_ppo.log
```

### 5. Monitoreo en vivo (ACTUALIZA CADA 10 SEG) - YA CORRIENDO
```powershell
powershell -ExecutionPolicy Bypass -File monitorear_ppo_nuevo.ps1
```

### 6. Seguimiento en tiempo real (continuously tail)
```powershell
Get-Content entrenamiento_ppo.log -Wait -Tail 30
```

## Información de Entrenamiento

| Item | Valor | Detalles |
|------|-------|---------|
| **Algoritmo** | PPO | Proximal Policy Optimization |
| **Network** | 256×256 | Policy & value heads |
| **Learning Rate** | 3e-4 | Según config |
| **n_steps** | 2048 | Rollout buffer |
| **n_epochs** | 10 | Updates por rollout |
| **batch_size** | 128 | Gradient batch |
| **Total Timesteps** | 87,600 | 10 episodios × 8,760h |
| **Velocidad esperada** | 600-700 timesteps/seg | GPU RTX 4060 |
| **Duración total** | ~2-3 minutos | Desde inicio |
| **Archivo de log** | `entrenamiento_ppo.log` | Salida completa |
| **Checkpoints** | `checkpoints/PPO/` | Modelos guardados |
| **Outputs** | `outputs/ppo_training/` | Resultados + gráficos |
| **GPU** | RTX 4060 (8GB VRAM) | CUDA enabled |

## Dimensiones del Problema PPO

### Observación Space (394-dim CityLearn v2)
- Building energy (8): grid, solar, BESS, mall import/export
- EV sockets (114): 38 sockets × 3 (power, SOC, active)
- Vehicle fleet (16): motos/taxis por nivel de SOC
- Time features (6): hour, month, day_of_week, holiday, etc
- System comms (12): reservation msgs, priority flags
- **Total: 156 "collapsed" dimensions tras normalización**

### Action Space (39-dim)
- BESS control (1): continuous power setpoint [-1,+1]
- Socket control (38): continuous power [0,1] per socket
- **Traducido a:** BESS kW + 38 socket kW

### Reward Multiobjetivo (CO2_FOCUS preset)
- **CO2 Grid (35%)**: Minimize grid imports × 0.4521 kg CO2/kWh
- **Solar Usage (20%)**: Maximize PV self-consumption
- **EV Satisfaction (30%)**: Motos/taxis reach 90% SOC by deadline
- **Cost (10%)**: Minimize total energy cost (tariff-aware)
- **Grid Stability (5%)**: Smooth power ramping

## Métricas PPO Esperadas

### RL Training Metrics
- **KL Divergence**: <0.05 (policy change control, healthy)
- **Clipping Fraction**: 5-30% (PPO clipping working)
- **Policy Loss**: Cercano a 0 (actor improving)
- **Value Loss**: <50-100 (critic converging)
- **Explained Variance**: 0.4-0.9 (value prediction quality)
- **Entropy**: 0.5-2.0 (exploration level)

### Energy/CO2 Metrics
- **CO2 Grid**: Grid import kg CO2 (minimize target)
- **CO2 Evitado**: Avoided CO2 via solar+BESS (maximize)
- **Solar Util**: PV utilization % (ideal >65%)
- **BESS Efficiency**: (discharge kWh) / (charge kWh)

### Fleet Metrics
- **Motos Cargados**: Motorcycles at target SOC per peak
- **Taxis Cargados**: Taxi vans at target SOC per peak
- **EV Charging Power**: Total Power to vehicles

## Salida Expected en Log

```
[EPISODIO COMPLETADO]
    Reward acumulado: 8,257.92

[CONTABILIDAD CO2]
    Grid Import CO2: 1,489,391 kg
    Reducido Indirecto: 3,952,802 kg (solar/BESS avoidance)
    Reducido Directo: 356,734 kg (EV renewable)
    Reduccion Total: 4,309,536 kg

[ENERGIA]
    Solar Aprovechado: 8,292,514 kWh
    EV Cargado: 299,290 kWh
    Grid Import: 3,294,375 kWh

[FLOTA MOVILIDAD]
    Motos cargadas (max): 28 / 112 (2,685 diarias)
    Taxis cargados (max): 7 / 16 (388 diarias)

[BESS]
    Descarga: 677,836 kWh
    Carga: 790,716 kWh
```

## Si el Entrenamiento se Detiene

```powershell
# Ver últimas 50 líneas completas
Get-Content entrenamiento_ppo.log | Select-Object -Last 50

# Verificar si está corriendo
Get-Process python | Where-Object { $_.CommandLine -match "train_ppo" }

# Reiniciar (después de revisar error)
python launch_ppo_training.py > entrenamiento_ppo.log 2>&1
```

## Archivos Finales Esperados (tras ~2-3 min)

```
checkpoints/PPO/
  ├─ ppo_model_2000_steps.zip
  ├─ ppo_model_4000_steps.zip
  ├─ ppo_model_...
  └─ ppo_model_87600_steps.zip (final)

outputs/ppo_training/
  ├─ result_ppo.json (estadísticas finales)
  ├─ timeseries_ppo.csv (datos por timestep)
  ├─ trace_ppo.csv (trazabilidad completa)
  ├─ ppo_entropy.png
  ├─ ppo_policy_loss.png
  ├─ ppo_value_loss.png
  ├─ ppo_kl_divergence.png
  ├─ ppo_clipping.png
  ├─ ppo_explained_variance.png
  ├─ ppo_dashboard.png (6 plots combined)
  ├─ ppo_kpi_solar.png
  ├─ ppo_kpi_ev_satisfaction.png
  ├─ ppo_kpi_co2.png
  ├─ ppo_kpi_cost.png
  ├─ ppo_kpi_grid_stability.png
  └─ ppo_kpi_dashboard.png
```

---
_Monitoreo PPO v1.0 | 2026-02-14 | RTX 4060 GPU | 87,600 timesteps_
