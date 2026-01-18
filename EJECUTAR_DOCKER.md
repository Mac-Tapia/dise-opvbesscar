# 🐳 GUÍA DE EJECUCIÓN DOCKER - Iquitos CityLearn Pipeline OE2→OE3

**Última actualización**: Enero 2026  
**Estado**: ✅ Listo para producción

---

## 🎯 Resumen Rápido

Esta construcción Docker automatiza completamente el pipeline OE2→OE3 del proyecto Iquitos:

- **OE2**: Dimensionamiento técnico (solar PV 4162 kWp + BESS 2000 kWh + 128 cargadores)
- **OE3**: Entrenamiento de agentes RL (SAC/PPO/A2C) en CityLearn

---

## 📦 Archivos Creados

| Archivo | Propósito |
| --------- | ----------- |
| `Dockerfile` | Construcción optimizada de imagen Python 3.11 |
| `docker-compose.yml` | Stack de servicios CPU |
| `docker-compose.gpu.yml` | Stack optimizado para GPU NVIDIA |
| `docker-entrypoint.sh` | Script de entrada del contenedor |
| `.dockerignore` | Optimización de build (excluir archivos) |
| `docker-run.ps1` | Script PowerShell para control (recomendado Windows) |
| `docker-run.bat` | Script Batch como alternativa Windows |
| `DOCKER_GUIDE.md` | Documentación técnica completa |

---

## 🚀 INICIO RÁPIDO

### **OPCIÓN A: PowerShell (RECOMENDADO para Windows)**

```powershell
# 1. Abre PowerShell en el directorio raíz del proyecto
cd d:\diseñopvbesscar

# 2. Ejecuta con permisos de administrador
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 3. Build + Pipeline completo OE2→OE3
.\docker-run.ps1 -Action run

# 4. O con GPU (si disponible)
.\docker-run.ps1 -Action run -GPU

# 5. O solo OE3 (asumiendo OE2 completado)
.\docker-run.ps1 -Action run -SkipOE2 -Detach
```

### **OPCIÓN B: Docker Compose CLI**

```bash
# Build + iniciar
docker-compose up -d

# Ver logs en vivo
docker-compose logs -f iquitos-pipeline

# Detener
docker-compose down
```

### **OPCIÓN C: Docker Manual**

```bash
# Build
docker build -t iquitos-citylearn:latest .

# Ejecutar
docker run -it --rm \
  -v %CD%/data:/app/data \
  -v %CD%/outputs:/app/outputs \
  -v %CD%/configs:/app/configs:ro \
  iquitos-citylearn:latest
```

---

## ⚙️ CONFIGURACIÓN

### Archivo: `configs/default.yaml`

```yaml
# OE2: Dimensionamiento
oe2:
  solar:
    target_dc_kw: 4162           # Sistema PV en kWp
    inverter_efficiency: 0.97
  chargers:
    motos_count: 112             # 2 kW cada una
    mototaxis_count: 16          # 3 kW cada una
  bess:
    capacity_kwh: 2000
    dod_min: 0.05
    dod_max: 0.95

# OE3: Entrenamiento RL
oe3:
  agents: ["SAC", "PPO", "A2C"]
  episodes: 5
  device: cuda                   # cuda | cpu | mps
  use_amp: true                  # Mixed precision (GPU)
```

---

## 📊 ESTRUCTURA DE EJECUCIÓN

### OE2 (Parallelizable - 15 min aprox)

```bash
├─ solar_pvlib.py     → 8760h profiles (irradiance, temp, etc)
├─ chargers.py        → 128 demand profiles (2-3 kW each)
└─ bess.py            → Battery config (2000 kWh, DoD 0.7-0.95)
```

### OE3 (Sequential - 2-6h con GPU, 12-24h CPU)

```bash
├─ dataset_builder.py → CityLearn schemas (validation: 128 CSVs)
├─ simulate.py        → Train SAC|PPO|A2C agents
│  ├─ SAC: 1000+ lines PyTorch (BEST: 33.1% CO₂ reduction)
│  ├─ PPO: stable-baselines3 wrapper
│  └─ A2C: stable-baselines3 wrapper
└─ co2_table.py       → Generate impact report
```

---

## 📁 DIRECTORIOS Y SALIDAS

```text
d:\diseñopvbesscar/
├── data/
│   └── interim/
│       └── oe2/
│           ├── solar/        ← 8760 hora profiles (CSV)
│           ├── chargers/     ← 128 archivos demand (CSV)
│           └── bess/         ← Battery config
│
├── outputs/
│   └── oe3/
│       ├── checkpoints/
│       │   ├── SAC/
│       │   │   ├── *_step_1000.zip
│       │   │   └── *_final.zip
│       │   ├── PPO/
│       │   └── A2C/
│       ├── results/
│       │   ├── simulation_summary.json    ← Resultados principales
│       │   ├── co2_comparison.json        ← Tabla CO₂ (33.1% reducción)
│       │   └── training_logs/
│       └── visualizations/
│           ├── reward_curves.png
│           └── co2_impact.png
```

---

## 🎮 COMANDOS PRINCIPALES

### Build

```powershell
# Solo construir imagen
.\docker-run.ps1 -Action build

# Reconstruir desde cero (sin caché)
docker build --no-cache -t iquitos-citylearn:latest .
```

### Run (Pipeline Completo)

```powershell
# OE2 + OE3 (modo interactivo)
.\docker-run.ps1 -Action run

# En background
.\docker-run.ps1 -Action run -Detach

# Solo OE3 (asume OE2 ya ejecutado)
.\docker-run.ps1 -Action run -SkipOE2
```

### GPU

```powershell
# Con GPU NVIDIA
.\docker-run.ps1 -Action run -GPU

# Docker Compose con GPU
docker-compose -f docker-compose.gpu.yml up -d
```

### Monitoreo

```powershell
# Ver logs en vivo
.\docker-run.ps1 -Action logs

# O manual
docker logs -f iquitos-pipeline
```

### Limpieza

```powershell
# Limpiar recursos Docker
.\docker-run.ps1 -Action clean

# Parar pipeline
.\docker-run.ps1 -Action stop
```

---

## ⚡ REQUISITOS MÍNIMOS

| Componente | Mínimo | Recomendado |
| ---------- | ------ | ----------- |
| **RAM** | 8 GB | 32 GB (GPU) |
| **Disco** | 30 GB | 50+ GB |
| **CPU** | 4 cores | 8+ cores |
| **GPU** | - | NVIDIA T4/V100+ |
| **Docker** | 20.10 | 29.1+ |

---

## 🔧 TROUBLESHOOTING

### ❌ "Docker is not installed"

```powershell
# Descargar Docker Desktop desde https://www.docker.com/products/docker-desktop
# Reiniciar sistema después de instalar
```

### ❌ "GPU not detected"

```bash
# Verificar nvidia-docker
nvidia-docker run --rm nvidia/cuda:11.8.0-runtime-ubuntu22.04 nvidia-smi

# Si falla, instalar nvidia-container-runtime
# Opción: usar CPU en docker-compose.yml (más lento)
```

### ❌ "Out of Memory"

```yaml
# Reducir en configs/default.yaml:
oe3:
  episode_timesteps: 4380  # De 8760
  batch_size: 64           # Reducir si es necesario
```

### ❌ "FileNotFoundError: data/interim/oe2/..."

```powershell
# OE2 no fue ejecutado. Ejecutar sin -SkipOE2:
.\docker-run.ps1 -Action run
```

### ❌ Permisos en PowerShell

```powershell
# Ejecutar como Administrador:
# (Click derecho en PowerShell → Run as Administrator)

Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
.\docker-run.ps1 -Action run
```

---

## 📈 RESULTADOS ESPERADOS

### Salida OE2 (5-15 min)

```bash
✓ Solar profiles: 8760 timesteps × 4162 kWp = 8.042 GWh/year
✓ Chargers loaded: 128 profiles (112×2kW + 16×3kW)
✓ BESS configured: 2000 kWh, DoD=[0.05, 0.95], η=0.88
```

### Salida OE3 - Comparativa Agentes (2-6h)

```text
┌─────────────────┬──────────────────┬─────────────┐
│ Agent           │ CO₂ (kg)         │ Reduction   │
├─────────────────┼──────────────────┼─────────────┤
│ Baseline        │ 11,282,200       │ 0%          │
│ SAC (BEST)      │  7,547,021       │ 33.1%  ✅   │
│ PPO             │  7,578,734       │ 32.8%       │
│ A2C             │  7,615,072       │ 32.5%       │
└─────────────────┴──────────────────┴─────────────┘

Cost Savings: ~$1.2M/año @ $0.16/kWh reduction
```

---

## 🔄 REANUDAR ENTRENAMIENTOS INTERRUMPIDOS

El sistema **auto-detecta** el último checkpoint:

```powershell
# Simplemente ejecutar de nuevo - retoma desde donde paró
.\docker-run.ps1 -Action run -SkipOE2

# Ver checkpoints disponibles
dir outputs/oe3/checkpoints/SAC/
```

---

## 🎯 PRÓXIMOS PASOS

1. **Verificar Docker**:

   ```powershell
   docker --version
   ```

2. **Iniciar Pipeline**:

   ```powershell
   .\docker-run.ps1 -Action run
   ```

3. **Monitorear**:

   ```powershell
   .\docker-run.ps1 -Action logs
   ```

4. **Revisar Resultados**:
   - `outputs/oe3/results/simulation_summary.json`
   - `outputs/oe3/results/co2_comparison.json`

---

## 📚 REFERENCIAS

| Documento | Contenido |
| --------- | ---------- |
| [DOCKER_GUIDE.md](./DOCKER_GUIDE.md) | Guía técnica completa |
| [configs/default.yaml](./configs/default.yaml) | Parámetros del proyecto |
| [scripts/run_pipeline.py](./scripts/run_pipeline.py) | Pipeline maestro |
| [COMPARATIVA_AGENTES_FINAL.md](./COMPARATIVA_AGENTES_FINAL.md) | Resultados OE3 |

---

## ❓ PREGUNTAS FRECUENTES

**P: ¿Cuánto tiempo tarda?**  
R: OE2 (~15 min) + OE3 (~2-6h con GPU, 12-24h CPU)

**P: ¿Puedo pausar y reanudar?**  
R: Sí, auto-detecta checkpoints. Solo ejecuta de nuevo.

**P: ¿Qué necesito para GPU?**  
R: Docker Desktop con NVIDIA Container Toolkit instalado

**P: ¿Puedo cambiar parámetros?**  
R: Edita `configs/default.yaml` antes de ejecutar

**P: ¿Dónde están los resultados?**  
R: `outputs/oe3/results/` - incluye JSON, logs, visualizaciones

---

**¿Preguntas?** Revisa `DOCKER_GUIDE.md` para documentación técnica detallada.
