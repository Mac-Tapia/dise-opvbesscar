# MONITOREO DE ENTRENAMIENTO A2C - GUÍA RÁPIDA

## Estado Actual
✅ **Entrenamiento A2C en ejecución** (background)
✅ **Datos OE2 compilados** (Solar, Chargers 38, BESS, Mall)
✅ **Monitor A2C activo** (monitorear_a2c.ps1 - cada 10 seg)

## Progreso Actual
```
Step: 25,000+ / 87,600 (28.5%+)
Episodio: 2+
Reward promedio: ~2,490 kg
Velocidad: ~560 timesteps/seg
ETA: ~2 minutos
```

## Comandos para Monitorear

### 1. Ver las últimas 20 líneas (INSTANTÁNEO)
```powershell
Get-Content entrenamiento_a2c.log -Tail 20
```

### 2. Ver solo líneas de progreso
```powershell
Select-String "Step" entrenamiento_a2c.log | Select-Object -Last 10
```

### 3. Ver métricas A2C (Entropy, Loss, etc)
```powershell
Select-String "Entropy:|Loss:|Expl\.Var" entrenamiento_a2c.log | Select-Object -Last 5
```

### 4. Ver solo errores/warnings
```powershell
Select-String "WARNING|ERROR" entrenamiento_a2c.log
```

### 5. Monitoreo en vivo (ACTUALIZA CADA 10 SEG) - YA CORRIENDO
```powershell
powershell -ExecutionPolicy Bypass -File monitorear_a2c.ps1
```

## Información de Entrenamiento

| Item | Valor |
|------|-------|
| **Algoritmo** | A2C (Actor-Critic on-policy) |
| **Network** | 256×256 (policy + value heads) |
| **Total Timesteps** | 87,600 (10 episodios × 8,760h) |
| **Velocidad esperada** | 600-650 timesteps/seg (GPU) |
| **Duración total** | ~2-3 minutos |
| **Archivo de log** | `entrenamiento_a2c.log` |
| **Checkpoints** | `checkpoints/A2C/` (cada 2,000 steps) |
| **Outputs** | `outputs/a2c_training/` |
| **GPU** | RTX 4060 (8GB VRAM, CUDA enabled) |

## Dimensiones del Problema

### Observaciones (156-dim)
- Energy (8): grid, solar, BESS, mall, chargers aggregate
- Sockets (114): 38 sockets × 3 values (power, SOC, status)
- Vehicles (16): motos/taxis por nivel SOC (7 niveles)
- Time features (6): hour, month, day_of_week, holiday, etc
- System comms (12): reservation msgs, priority flags, etc

### Acciones (39-dim)
- BESS control (1): power setpoint [-1, +1] (discharge to charge)
- Sockets (38): power setpoints [0, 1] per socket

### Reward Components (Multiobjetivo)
- **CO2 Grid (35%)**: kg CO2/kWh × grid imports
- **Solar Usage (20%)**: direct PV consumption bonus
- **EV Satisfaction (30%)**: motos/taxis at target SOC
- **Cost (10%)**: minimize tariff expenses
- **Grid Stability (5%)**: smooth power ramping

## Métricas A2C Esperadas

### Policy & Value Metrics
- **Entropy**: ~0.5-2.0 (exploración, mayor = más aleatorio)
- **Policy Loss**: Cercano a 0 (actor mejorando)
- **Value Loss**: <50 (predicción de valor OK)
- **Explained Variance**: 0.3-0.9 (qué tan bien predice el crítico)
- **KL Divergence**: Bajo (<0.1 = estable)

### Performance Metrics
- **Reward Promedio**: 2,000-4,000 kg (goal: maximizar CO2 evitado)
- **Timesteps/seg**: 600+
- **Episodes**: 0-10 (10 episodios = 1 año entero)

## Qué Esperar en el Log

```
[PROGRESO]
Step  10,000/87,600 ( 11.4%) | Ep=1 | R_avg=2337.16 | 603 sps | ETA=2.1min

[METRICAS A2C CADA ~5 EPISODIOS]
[A2C] Step   10,240:
         Entropy: 0.512  | Policy Loss: -0.0043  | Value Loss: 18.23
         Expl.Var: 0.45  | Grad Norm: 0.082

[WARNINGS SI PROBLEMAS]
[A2C WARNING] Entropy baja: 0.05 (colapso exploración)
[A2C WARNING] Value loss alta: 142 (>100)
```

## Si el Entrenamiento se Detiene

```powershell
# Ver últimas 50 líneas completas
Get-Content entrenamiento_a2c.log | Select-Object -Last 50

# Reiniciar (después de revisar error)
python launch_a2c_training.py > entrenamiento_a2c.log 2>&1
```

## Archivos Finales Esperados (tras ~2-3 min)

```
checkpoints/A2C/
  ├─ a2c_model_2000_steps.zip
  ├─ a2c_model_4000_steps.zip
  ├─ a2c_model_...
  └─ a2c_model_87600_steps.zip (final)

outputs/a2c_training/
  ├─ result_a2c.json (estadísticas finales)
  ├─ timeseries_a2c.csv (datos por timestep)
  ├─ a2c_entropy.png
  ├─ a2c_policy_loss.png
  ├─ a2c_value_loss.png
  ├─ a2c_explained_variance.png
  ├─ a2c_grad_norm.png
  ├─ a2c_dashboard.png
  ├─ a2c_kpi_solar.png
  ├─ a2c_kpi_ev_satisfaction.png
  └─ a2c_kpi_co2.png (+ 3 more KPI plots)
```

---
_Monitoreo A2C v1.0 | 2026-02-14 | RTX 4060 GPU_
