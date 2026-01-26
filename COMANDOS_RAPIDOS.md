# ⚡ QUICK REFERENCE - COMANDOS RÁPIDOS

## 🚀 RELANZAR PIPELINE COMPLETO

### Opción 1: Script PowerShell (Recomendado)
```powershell
cd d:\diseñopvbesscar
.\RELANZAR_PIPELINE.ps1
```

### Opción 2: Línea de comandos directa
```powershell
cd d:\diseñopvbesscar
$env:PYTHONIOENCODING='utf-8'
$env:CUDA_VISIBLE_DEVICES='0'

python -m scripts.run_oe3_simulate --config configs/default.yaml `
  2>&1 | Tee-Object -FilePath "training_pipeline_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
```

---

## 📦 SOLO CONSTRUIR DATASET

```powershell
.\RELANZAR_PIPELINE.ps1 -OnlyDataset
```

O directamente:
```powershell
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
```

---

## 📊 SOLO BASELINE (SIN RL)

```powershell
python -m scripts.run_uncontrolled_baseline --config configs/default.yaml
```

---

## 🔍 MONITOREAR EJECUCIÓN

### Ver log en tiempo real
```powershell
Get-Content -Path "training_pipeline_*.log" -Tail 50 -Wait
```

### Ver últimas 50 líneas
```powershell
Get-Content -Path "training_pipeline_*.log" -Tail 50
```

### Chequear checkpoints generados
```powershell
Get-ChildItem -Path "checkpoints\*\*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 3
```

### Ver outputs generados
```powershell
Get-ChildItem -Path "outputs\oe3_simulations\" | Format-Table Name, LastWriteTime, @{Name="Size";Expression={"{0:N0}" -f $_.Length}}
```

---

## 🧹 LIMPIAR Y RESETEAR

### Eliminar todos los checkpoints
```powershell
Remove-Item -Path "checkpoints\*" -Recurse -Force -ErrorAction SilentlyContinue
```

### Limpiar dataset
```powershell
Remove-Item -Path "data\processed\citylearn\iquitos_ev_mall\*" -Force -ErrorAction SilentlyContinue
```

### Limpiar outputs
```powershell
Remove-Item -Path "outputs\oe3_simulations\*" -Force -ErrorAction SilentlyContinue
```

### Reset completo
```powershell
Remove-Item -Path "checkpoints\*" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "outputs\*" -Recurse -Force -ErrorAction SilentlyContinue
```

---

## ✅ VERIFICACIONES PRE-EJECUCIÓN

### Verificar Python
```powershell
python --version
# Esperado: Python 3.11.x
```

### Verificar paquetes instalados
```powershell
python -c "import citylearn, stable_baselines3, torch; print('OK')"
```

### Verificar GPU disponible
```powershell
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

### Verificar dataset existente
```powershell
Test-Path "data\processed\citylearn\iquitos_ev_mall\schema.json"
# Esperado: True
```

### Contar charger CSVs
```powershell
(Get-ChildItem -Path "data\processed\citylearn\iquitos_ev_mall\charger_simulation_*.csv").Count
# Esperado: 128
```

---

## 📈 VERIFICAR RESULTADOS

### Abrir resumen de simulación
```powershell
$summary = Get-Content -Path "outputs\oe3_simulations\simulation_summary.json" | ConvertFrom-Json
$summary | Format-Table
```

### Comparar CO2 entre agentes
```powershell
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

### Ver métricas por episodio
```powershell
Get-ChildItem -Path "outputs\oe3_simulations\*_episode_rewards.csv" | 
  ForEach-Object { Write-Host "=== $($_.Name) ==="; Get-Content $_ | Select-Object -Last 5 }
```

---

## 🔧 CAMBIAR CONFIGURACIÓN

### Editar hiperparámetros
```powershell
notepad configs\default.yaml
```

Cambios comunes:
- Reducir `batch_size` de 128 a 64 (si GPU out of memory)
- Cambiar `n_episodes` de 5 a 10/20 (más entrenamiento)
- Ajustar `learning_rate` para convergencia
- Cambiar `reward_weights` para priorizar diferentes objetivos

### Aplicar cambios
```powershell
# Solo dataset
python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# Pipeline completo
.\RELANZAR_PIPELINE.ps1
```

---

## 📂 ESTRUCTURA DE DIRECTORIOS CLAVE

```
d:\diseñopvbesscar\
├── configs/
│   ├── default.yaml                    ← Configuración principal
│   └── default_optimized.yaml
├── src/iquitos_citylearn/oe3/
│   ├── dataset_builder.py              ← CORRECCIÓN SOLAR AQUÍ (línea 726)
│   ├── simulate.py                     ← Main training loop
│   ├── rewards.py                      ← Multi-objective rewards
│   └── agents/
│       ├── sac.py
│       ├── ppo_sb3.py
│       └── a2c_sb3.py
├── scripts/
│   ├── run_oe3_simulate.py             ← Entry point principal
│   ├── run_oe3_build_dataset.py
│   └── run_uncontrolled_baseline.py
├── data/processed/citylearn/iquitos_ev_mall/
│   ├── Building_1.csv                  ← Solar + Demand (8,760 horas)
│   ├── charger_simulation_001-128.csv  ← 128 chargers individuales
│   ├── schema.json                     ← Configuración CityLearn
│   └── *.csv                           ← supporting files
├── checkpoints/
│   ├── SAC/latest.zip
│   ├── PPO/latest.zip
│   └── A2C/latest.zip
├── outputs/oe3_simulations/
│   ├── simulation_summary.json         ← Resultados finales
│   ├── baseline_metrics.csv
│   └── *_episode_rewards.csv
└── RELANZAR_PIPELINE.ps1               ← Script automatizado
```

---

## 🚨 ERRORES COMUNES Y SOLUCIONES

| Error | Solución |
|-------|----------|
| "128 chargers not found" | `python -m scripts.run_oe3_build_dataset` |
| "GPU out of memory" | Reducir `batch_size` de 128 a 64 en config.yaml |
| "Solar generation too low" | Verificar que dataset_builder.py línea 726 NO multiplique por 1000 |
| "RecursionError" | Asegurar charger_simulation_*.csv sin columna `demand_kw` |
| "Module not found" | `pip install -e . -q` desde raíz del proyecto |

---

## 📞 ARCHIVOS DE REFERENCIA

- **Documentación completa:** `PIPELINE_EJECUTABLE_DOCUMENTACION.md`
- **Este archivo:** `COMANDOS_RAPIDOS.md`
- **Instrucciones Copilot:** `.github/copilot-instructions.md`
- **Log actual:** `training_pipeline_YYYYMMDD_HHmmss.log`

---

## ⏱️ DURACIONES ESTIMADAS

| Fase | GPU CUDA | CPU |
|------|----------|-----|
| Dataset builder | 3-5 min | 5-10 min |
| Baseline | 10-15 min | 15-30 min |
| SAC (5 eps) | 1-2 horas | 4-6 horas |
| PPO (5 eps) | 1-2 horas | 4-6 horas |
| A2C (5 eps) | 1-2 horas | 4-6 horas |
| **TOTAL** | **8-12 horas** | **24-48 horas** |

---

**Última actualización:** 2026-01-26  
**Estado:** ✅ LISTO PARA USAR
