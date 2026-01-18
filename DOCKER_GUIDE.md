# Docker Pipeline - Iquitos CityLearn OE2→OE3

Construcción y ejecución automatizada del pipeline de análisis de infraestructura de carga inteligente de vehículos eléctricos.

## 📋 Requisitos Previos

- **Docker**: >= 20.10
- **Docker Compose**: >= 1.29
- **GPU Support (Opcional)**: NVIDIA Docker Runtime (para aceleración CUDA)
- **Espacio en disco**: >= 50GB (datos + checkpoints)
- **RAM**: >= 16GB recomendado

## 🚀 Quick Start

### Opción 1: PowerShell (Windows Recomendado)

```powershell
# Build + ejecutar pipeline completo
.\docker-run.ps1 -Action run

# Con soporte GPU
.\docker-run.ps1 -Action run -GPU

# Ejecutar en background
.\docker-run.ps1 -Action run -Detach

# Solo OE3 (asumiendo OE2 ya completado)
.\docker-run.ps1 -Action run -SkipOE2
```

### Opción 2: Docker Compose

```bash
# Build e iniciar servicios
docker-compose up -d

# Con GPU
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

# Ver logs en vivo
docker-compose logs -f iquitos-pipeline

# Detener
docker-compose down
```

### Opción 3: Docker Directo

```bash
# Build
docker build -t iquitos-citylearn:latest .

# Ejecutar con datos persistentes
docker run -it --rm \
  -v %CD%/data:/app/data \
  -v %CD%/outputs:/app/outputs \
  -v %CD%/configs:/app/configs:ro \
  iquitos-citylearn:latest

# Con GPU
docker run -it --rm --gpus all \
  -v %CD%/data:/app/data \
  -v %CD%/outputs:/app/outputs \
  iquitos-citylearn:latest
```

## 📊 Estructura de Ejecución

### Pipeline OE2 (Dimensionamiento Técnico)

```bash
1. run_oe2_solar.py     → Solar PV 8760h profiles
2. run_oe2_chargers.py  → 128 EV charger profiles
3. run_oe2_bess.py      → 2000 kWh BESS configuration
```

### Pipeline OE3 (Evaluación RL)

```bash
1. run_oe3_build_dataset.py → CityLearn schemas
2. run_oe3_simulate.py      → SAC|PPO|A2C training
3. run_oe3_co2_table.py     → CO₂ impact report
```

## 🎯 Configuración

### Archivo: `configs/default.yaml`

```yaml
# OE2: Dimensionamiento
oe2:
  solar:
    target_dc_kw: 4162        # kWp del sistema PV
    inverter_efficiency: 0.97
  chargers:
    motos: 112                # 2 kW c/u
    mototaxis: 16             # 3 kW c/u
  bess:
    capacity_kwh: 2000        # Batería
    dod_min: 0.05
    dod_max: 0.95

# OE3: Entrenamiento RL
oe3:
  agents: [SAC, PPO, A2C]     # Agentes a entrenar
  episodes: 5                 # Episodios por agente
  device: cuda                # cuda | cpu | mps
  use_amp: true               # Mixed precision
```

## 📁 Directorios de Salida

```text
outputs/
├── oe3/
│   ├── checkpoints/
│   │   ├── SAC/
│   │   │   ├── *_step_1000.zip
│   │   │   └── *_final.zip
│   │   ├── PPO/
│   │   └── A2C/
│   ├── results/
│   │   ├── simulation_summary.json
│   │   ├── co2_comparison.json
│   │   └── training_logs/
│   └── visualizations/
│       ├── reward_curves.png
│       └── co2_impact.png

data/
├── interim/
│   ├── oe2/
│   │   ├── solar/      (8760 profiles)
│   │   ├── chargers/   (128 CSV files)
│   │   └── bess/
│   └── processed/
└── raw/
```

## 🔧 Uso Avanzado

### Reanudar Entrenamiento Interrumpido

```powershell
# Detecta automáticamente último checkpoint
.\docker-run.ps1 -Action run -SkipOE2
```

### Monitoreo en Vivo

```bash
# Terminal 1: Ejecutar pipeline
docker-compose up

# Terminal 2: Ver logs
docker logs -f iquitos-pipeline

# Terminal 3: Monitorizar checkpoints
docker exec iquitos-pipeline python monitor_checkpoints.py
```

### Limitaciones de GPU

```bash
# Usar GPU específica
docker run --gpus '"device=0"' ...

# Limitar memoria GPU
docker run --gpus all --memory 32g ...
```

## ⚙️ Optimizaciones

### CPU-only (más lento pero funcional)

```yaml
# configs/default.yaml
device: cpu
use_amp: false
```

### Multi-GPU (si disponible)

```bash
# Modifica docker-compose.gpu.yml
docker-compose -f docker-compose.gpu.yml up
```

### Caché de Build

```bash
# Reutiliza capas previas
docker build --cache-from iquitos-citylearn:latest -t iquitos-citylearn:latest .
```

## 🐛 Troubleshooting

### Docker no encontrado

```powershell
# Asegúrate de que Docker Desktop esté corriendo
```

### GPU no detectada

```bash
# Verifica nvidia-docker
nvidia-docker version

# Reinstala runtime
docker run --rm --gpus all ubuntu nvidia-smi
```

### Espacio en disco insuficiente

```bash
# Limpia imágenes dangling
docker image prune -a --force
```

### Out of Memory

```yaml
# Reduce episode length en configs/default.yaml
oe3:
  episode_timesteps: 8760  # Reducir si es necesario
```

## 📈 Resultados Esperados

| Métrica | Valor | Unidad |
| --------- | ------- | -------- |
| Solar generada | 8.042 | GWh/año |
| CO₂ baseline | 11,282,200 | kg |
| CO₂ con SAC | 7,547,021 | kg |
| Reducción | 33.1% | % |
| Tiempo entrenamiento SAC | 2-4 | horas (GPU) |

## 🛠️ Mantenimiento

### Limpiar recursos Docker

```powershell
.\docker-run.ps1 -Action clean

# O manual:
docker system prune -a --volumes
```

### Reconstruir desde cero

```bash
docker-compose down -v
docker image rm iquitos-citylearn:latest
docker-compose up --build
```

## 📞 Soporte

- Logs detallados: `outputs/oe3/training_logs/`
- Checkpoints: `outputs/oe3/checkpoints/*/`
- Configuración: [configs/default.yaml](../configs/default.yaml)
