# 📑 INDICE COMPLETO - Docker Pipeline OE2→OE3

**Fecha**: Enero 2026  
**Estado**: ✅ Sistema listo para producción  
**Tiempo de ejecución**: OE2 (~15 min) + OE3 (~2-6h GPU | 12-24h CPU)

---

## 📚 Documentación

### 🚀 INICIO AQUÍ

- **[EJECUTAR_DOCKER.md](./EJECUTAR_DOCKER.md)** ← **COMIENZA AQUÍ**
  - Guía rápida en español
  - Comandos de inicio inmediato
  - FAQ y troubleshooting

### 🔧 Documentación Técnica

- **[DOCKER_GUIDE.md](./DOCKER_GUIDE.md)**
  - Especificaciones completas
  - Configuración avanzada
  - Monitoreo en vivo

---

## 🗂️ Archivos de Configuración

### Docker

```text
Dockerfile                 Multi-stage build optimizado (Python 3.11)
docker-compose.yml         Stack CPU (servicios pipeline + monitor)
docker-compose.gpu.yml     Stack GPU (NVIDIA runtime)
.dockerignore              Optimización de build
```bash

### Scripts de Lanzamiento

```bash
docker-run.ps1             PowerShell (RECOMENDADO para Windows) ⭐
docker-run.bat             Batch alternativo (Windows)
docker-entrypoint.sh       Script de entrada del contenedor
launch_docker.py           Python launcher con validaciones interactivas
```bash

### Configuración del Proyecto

```text
configs/default.yaml       Parámetros OE2 + OE3 (editable)
pyproject.toml            Dependencias Python
requirements.txt          Packages necesarios
```bash

---

## 🎯 FLUJO DE EJECUCIÓN

```text
┌─────────────────────────────────────────────────────────┐
│ 1. PREPARACIÓN                                          │
│    - Verificar Docker instalado y corriendo            │
│    - Verificar disk space (30+ GB)                     │
│    - Verificar GPU (opcional, recomendado)            │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 2. BUILD DOCKER IMAGE                                  │
│    - Multi-stage build (builder → runtime)             │
│    - Python 3.11 slim base                             │
│    - Optimización de capas con caché                   │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 3. OE2: DIMENSIONAMIENTO (15-30 min)                   │
│   ├─ solar_pvlib.py          → 8760 profiles           │
│   ├─ chargers.py             → 128 demand CSVs         │
│   └─ bess.py                 → Battery config           │
│   OUTPUT: data/interim/oe2/{solar,chargers,bess}/      │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 4. OE3: ENTRENAMIENTO RL (2-6h GPU | 12-24h CPU)       │
│   ├─ dataset_builder.py      → CityLearn schemas       │
│   ├─ simulate.py             → SAC|PPO|A2C training    │
│   │   ├─ SAC (PyTorch 1000+)  → 33.1% CO₂ reducción   │
│   │   ├─ PPO (stable-b3)      → 32.8% reducción       │
│   │   └─ A2C (stable-b3)      → 32.5% reducción       │
│   └─ co2_table.py            → Report generation      │
│   OUTPUT: outputs/oe3/checkpoints/*.zip                │
│            outputs/oe3/results/*.json                  │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 5. RESULTADOS FINALES                                  │
│    - simulation_summary.json (métricas principales)     │
│    - co2_comparison.json (tabla comparativa)            │
│    - *.zip checkpoints (modelos entrenados)            │
│    - Gráficas: reward curves, CO₂ impact              │
└─────────────────────────────────────────────────────────┘
```bash

---

## 🚀 COMANDOS RÁPIDOS

### **OPCIÓN A: PowerShell (RECOMENDADO)**

```powershell
# 1. Abrir PowerShell como Administrador en la carpeta del proyecto

# 2. Permitir scripts
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

# 3. Ejecutar (elegir uno):

# ➤ Pipeline completo OE2→OE3
.\docker-run.ps1 -Action run

# ➤ Solo OE3 (asume OE2 completado)
.\docker-run.ps1 -Action run -SkipOE2

# ➤ Con GPU NVIDIA
.\docker-run.ps1 -Action run -GPU

# ➤ En background (detached)
.\docker-run.ps1 -Action run -Detach

# ➤ Ver logs en vivo
.\docker-run.ps1 -Action logs

# ➤ Parar
.\docker-run.ps1 -Action stop
```bash

### **OPCIÓN B: Docker Compose**

```bash
# Build + iniciar
docker-compose up -d

# Con GPU
docker-compose -f docker-compose.gpu.yml up -d

# Ver logs
docker-compose logs -f iquitos-pipeline

# Parar
docker-compose down
```bash

### **OPCIÓN C: Python Launcher**

```bash
# Lanzador interactivo con validaciones
python launch_docker.py

# Auto-run (sin prompts)
python launch_docker.py --auto --gpu
```bash

---

## 📊 RESULTADOS ESPERADOS

### Salida OE2

```bash
✓ Solar profiles: 8760 timesteps × 4162 kWp
✓ Annual generation: 8.042 GWh
✓ Chargers: 128 demand profiles loaded
✓ BESS: 2000 kWh configured (DoD=0.7-0.95)
```bash

### Salida OE3 - Tabla Comparativa Agentes

```text
┌────────────────────┬────────────────────┬──────────────┐
│ Agent              │ CO₂ (kg)           │ Reduction    │
├────────────────────┼────────────────────┼──────────────┤
│ Baseline (sin PV)  │ 11,282,200         │ 0%           │
│ SAC (BEST) ✅      │  7,547,021         │ 33.1%        │
│ PPO                │  7,578,734         │ 32.8%        │
│ A2C                │  7,615,072         │ 32.5%        │
│ Uncontrolled       │  7,601,155         │ 32.7%        │
│ NoControl          │ 11,196,421         │ 0.8%         │
└────────────────────┴────────────────────┴──────────────┘

Ahorros económicos: ~$1.2M/año @ $0.16/kWh
```bash

### Archivos de Salida

```text
outputs/oe3/
├── results/
│   ├── simulation_summary.json          (métricas principales)
│   ├── co2_comparison.json              (tabla CSV)
│   ├── training_logs/                   (logs por agente)
│   └── episode_rewards.csv              (rewards por episodio)
├── checkpoints/
│   ├── SAC/*_step_1000.zip              (checkpoints intermedios)
│   ├── PPO/*_final.zip                  (modelo final)
│   └── A2C/*_final.zip
└── visualizations/
    ├── reward_curves.png
    ├── co2_impact_comparison.png
    └── cumulative_emission_reduction.png
```bash

---

## ⚙️ CONFIGURACIÓN PERSONALIZADA

### Editar `configs/default.yaml`

```yaml
# OE2: Dimensionamiento técnico
oe2:
  solar:
    target_dc_kw: 4162           # Capacidad PV en kWp
    latitude: -3.74              # Iquitos
    longitude: -73.27
  
  chargers:
    motos_count: 112             # 2 kW cada una
    mototaxis_count: 16          # 3 kW cada una
  
  bess:
    capacity_kwh: 2000           # Batería
    efficiency: 0.88              # Rendimiento round-trip
    dod_min: 0.05                # Profundidad descarga mínima
    dod_max: 0.95                # Máxima

# OE3: Parámetros de entrenamiento RL
oe3:
  agents: ["SAC", "PPO", "A2C"]  # Agentes a entrenar
  episodes: 5                     # Episodios por agente
  episode_timesteps: 8760         # Horas por episodio (año)
  device: cuda                    # cuda | cpu | mps
  use_amp: true                   # Mixed precision (GPU)
  
  # Reward weights (suma = 1.0)
  reward_weights:
    co2: 0.50          # Minimizar emisiones (PRIMARIO)
    cost: 0.15         # Minimizar costo electricidad
    solar: 0.20        # Maximizar auto-consumo
    ev: 0.10           # Satisfacción carga EV
    grid: 0.05         # Estabilidad red
```bash

---

## 🔍 MONITOREO EN VIVO

### Ver entrenamiento en progreso

```powershell
# Terminal 1: Ejecutar pipeline
.\docker-run.ps1 -Action run -GPU -Detach

# Terminal 2: Ver logs
.\docker-run.ps1 -Action logs

# Terminal 3: Monitorear checkpoints
docker exec iquitos-pipeline python monitor_checkpoints.py
```bash

### Archivo de log en vivo

```bash
outputs/oe3/training_logs/
├── SAC_episode_rewards.log
├── PPO_episode_rewards.log
├── A2C_episode_rewards.log
└── checkpoint_progression.json
```bash

---

## ❌ TROUBLESHOOTING

### Docker no está corriendo

```powershell
# Windows: Iniciar Docker Desktop
# Mac/Linux: sudo systemctl start docker
```bash

### GPU no detectada

```bash
# Verificar NVIDIA runtime
nvidia-docker run --rm nvidia/cuda:11.8.0-runtime-ubuntu22.04 nvidia-smi

# Si falla: usar CPU en docker-compose.yml
```bash

### Memoria insuficiente

```yaml
# Reducir en configs/default.yaml:
oe3:
  episode_timesteps: 4380    # Mitad del año
  batch_size: 32             # Reducir batch
```bash

### FileNotFoundError: data/interim/oe2/

```yaml
OE2 no se ejecutó. Ejecutar sin -SkipOE2:
.\docker-run.ps1 -Action run
```bash

---

## 📋 CHECKLIST PRE-EJECUCIÓN

- [ ] Docker Desktop instalado y corriendo (`docker --version`)
- [ ] Disk space >= 30 GB disponible
- [ ] `configs/default.yaml` existe y es válido
- [ ] Puertos libres (no necesarios pero recomendado)
- [ ] RAM >= 8 GB (16+ recomendado)
- [ ] GPU NVIDIA opcional pero acelera 4-6x

---

## 🎓 INFORMACIÓN ADICIONAL

### OE2: Dimensionamiento Técnico

- **Propósito**: Generar perfiles horarios (8760 horas)
- **Salida**: CSV files para OE3
- **Validaciones**: Checks de integridad en runtime

### OE3: Entrenamiento RL

- **Propósito**: Entrenar SAC/PPO/A2C para control óptimo de carga
- **Métrica primaria**: Reducción CO₂ (33.1% con SAC)
- **Métrica secundaria**: Ahorro económico (~$1.2M/año)

### Agentes RL

- **SAC (MEJOR)**: 1000+ líneas PyTorch puro
- **PPO**: Wrapper stable-baselines3
- **A2C**: Wrapper stable-baselines3
- **Baseline**: Sin control (máxima carga)

---

## 📞 REFERENCIAS RÁPIDAS

| Necesidad | Archivo |
|| --------- | ------- ||
| Ejecutar pipeline | [EJECUTAR_DOCKER.md](./EJECUTAR_DOCKER.md) ⭐ |
| Documentación técnica | [DOCKER_GUIDE.md](./DOCKER_GUIDE.md) |
| Editar parámetros | [configs/default.yaml](./configs/default.yaml) |
| Ver pipeline | [scripts/run_pipeline.py](./scripts/run_pipeline.py) |
| Resultados comparativos | [outputs/oe3/results/](./outputs/oe3/results/) |
| Modelos entrenados | [outputs/oe3/checkpoints/](./outputs/oe3/checkpoints/) |

---

## ✅ PRÓXIMO PASO

**👉 Lee [EJECUTAR_DOCKER.md](./EJECUTAR_DOCKER.md) y ejecuta:**

```powershell
# Windows PowerShell (Administrador)
.\docker-run.ps1 -Action run -GPU
```bash

¡El pipeline hará el resto automáticamente! ✨
