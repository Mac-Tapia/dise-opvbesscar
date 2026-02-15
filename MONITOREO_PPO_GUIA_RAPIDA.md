# MONITOREO DE ENTRENAMIENTO PPO - GUÍA RÁPIDA

## Estado Actual
✅ **Entrenamiento en ejecución** (background)
✅ **Datos OE2 compilados** (Solar, Chargers 38, BESS, Mall)
✅ **Monitor activo** (scripts/procesos en background)

## Comandos para Monitorear

### 1. Ver las últimas 20 líneas de log (RÁPIDO)
```powershell
Get-Content entrenamiento_ppo.log -Tail 20
```

### 2. Monitoreo en vivo (ACTUALIZA CADA 10 SEG)
```powershell
powershell -ExecutionPolicy Bypass -File monitorear_ppo.ps1
```

### 3. Ver solo líneas de progreso
```powershell
Select-String "Steps:|CO2_" entrenamiento_ppo.log | Select-Object -Last 20
```

### 4. Ver solo métricas PPO
```powershell
Select-String "KL:|Entropy:|Policy" entrenamiento_ppo.log | Select-Object -Last 10
```

### 5. Ver solo advertencias
```powershell
Select-String "WARNING" entrenamiento_ppo.log
```

## Información Importante

| Item | Valor |
|------|-------|
| **Total Timesteps** | 87,600 (10 episodios × 8,760h) |
| **Velocidad esperada** | ~650-700 timesteps/seg (GPU) |
| **Duración estimada** | 2-3 minutos |
| **Archivo de log** | `entrenamiento_ppo.log` |
| **Checkpoints** | `checkpoints/PPO/` |
| **Outputs** | `outputs/ppo_training/` |
| **GPU** | RTX 4060 (8GB VRAM) |

## Qué esperar en las Métricas

### Progreso
- Incrementa de 0% a 100%
- Episodio va de 0 a 9
- Steps va de 0 a 87,600

### CO2 (Objetivo Minimizar)
- CO2_grid: Grid imports × 0.4521 kg CO2/kWh
- CO2_evitado: PV directa evitando grid

### PPO Metrics
- **Entropy**: Mayor = más exploración (ideal 0.5-1.0)
- **KL Divergence**: Menor = mejor convergencia
- **Clipping %**: 5-30% es normal
- **Policy Loss**: Debería ser cercano a 0
- **Value Loss**: Menor es mejor (idealmente <50)
- **Explained Variance**: Cercano a 1.0 = buen predictor de valor

## Si el entrenamiento se detiene

```powershell
# Ver salida completa del error
Get-Content entrenamiento_ppo.log | Select-Object -Last 50

# Reiniciar (después de revisar errores)
python launch_ppo_training.py > entrenamiento_ppo.log 2>&1
```

## Archivos Tras Completar

Tras finalizar (~2-3 min), se generarán:
- `checkpoints/PPO/ppo_model_*.zip` - Modelo entrenado
- `outputs/ppo_training/result_ppo.json` - Estadísticas
- `outputs/ppo_training/timeseries_ppo.csv` - Datos por timestep
- `outputs/ppo_training/*.png` - Gráficos (entropy, loss, etc)

---
_Monitoreo PPO v6.1 | 2026-02-14_
