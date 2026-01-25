#!/usr/bin/env python3
"""
Visualización completa de rutas Docker - Proyecto Iquitos EV Smart Charging
"""

print("\n" + "="*100)
print("🐳 RUTA COMPLETA DOCKER - PROYECTO IQUITOS EV SMART CHARGING")
print("="*100 + "\n")

# Ruta 1: Windows Host
print("┌─ CAPA 1: WINDOWS HOST (Sistema Operativo)")
print("│")
print("│  🖥️  C:\\Users\\Lenovo Legion\\")
print("│      └── AppData\\Local\\")
print("│          └── Docker\\")
print("│              └── wsl\\data\\")
print("│")
print("└─ Localización: Máquina física (SSD/HDD local)")
print()

# Ruta 2: Proyecto
print("┌─ CAPA 2: PROYECTO LOCAL (Windows filesystem)")
print("│")
print("│  📁 d:\\diseñopvbesscar\\  ← TU PROYECTO AQUÍ")
print("│     ├── data/")
print("│     │   └── interim/")
print("│     │       └── oe2/")
print("│     │           ├── solar/")
print("│     │           ├── bess/")
print("│     │           └── chargers/")
print("│     ├── outputs/")
print("│     │   └── oe3/")
print("│     │       ├── simulations/  ← RESULTADOS SAC/PPO/A2C")
print("│     │       ├── graphics/")
print("│     │       └── checkpoints/")
print("│     ├── configs/")
print("│     │   └── default.yaml")
print("│     ├── scripts/")
print("│     ├── src/")
print("│     ├── Dockerfile")
print("│     └── docker-compose.yml")
print("│")
print("└─ Localización: d:\\ (Disco duro Windows)")
print()

# Ruta 3: Docker Desktop
print("┌─ CAPA 3: DOCKER DESKTOP (Virtualizador)")
print("│")
print("│  🐳 Docker Desktop 29.1.3")
print("│  ├── Engine: npipe:////./pipe/docker_engine")
print("│  ├── Context: desktop-linux (ACTIVO)")
print("│  └── Backend: WSL 2")
print("│")
print("└─ Localización: C:\\Program Files\\Docker\\")
print()

# Ruta 4: WSL 2
print("┌─ CAPA 4: WSL 2 (Linux Virtual Machine)")
print("│")
print("│  🐧 Ubuntu (Running)")
print("│  ├── Kernel: Linux (WSL 2)")
print("│  ├── Filesystem: /root/.wsl/")
print("│  └── Mount Points:")
print("│      └── /mnt/c/ → C:\\ (acceso a Windows)")
print("│")
print("└─ Localización: Máquina virtual Hyper-V")
print()

# Ruta 5: Docker Image
print("┌─ CAPA 5: DOCKER IMAGE (Contenedor Template)")
print("│")
print("│  📦 iquitos-citylearn:latest (22.3 GB)")
print("│  ├── Base: python:3.11-slim")
print("│  ├── Builder stage: compilación de dependencias")
print("│  └── Runtime stage: Python + ML libraries")
print("│")
print("└─ Localización: /var/lib/docker/images/ (WSL storage)")
print()

# Ruta 6: Docker Container
print("┌─ CAPA 6: DOCKER CONTAINER (Proceso Ejecutable)")
print("│")
print("│  🚀 Instancia en ejecución")
print("│  ├── ID: <container-id>")
print("│  ├── Status: Running (cuando está activo)")
print("│  ├── GPU: NVIDIA CUDA 12.7 (--gpus all)")
print("│  └── Filesystem:")
print("│      ├── /app/")
print("│      ├── /app/data/")
print("│      ├── /app/outputs/")
print("│      ├── /app/configs/")
print("│      ├── /app/scripts/")
print("│      └── /app/src/")
print("│")
print("└─ Localización: Proceso en WSL 2")
print()

# Ruta 7: Volúmenes Montados
print("┌─ CAPA 7: VOLÚMENES MONTADOS (Bind Mounts)")
print("│")
print("│  📂 Host (Windows) ↔ Container (Linux)")
print("│")
print("│  ✓ d:\\diseñopvbesscar\\data")
print("│    └─→ /app/data (read-write)")
print("│")
print("│  ✓ d:\\diseñopvbesscar\\outputs")
print("│    └─→ /app/outputs (read-write)")
print("│")
print("│  ✓ d:\\diseñopvbesscar\\configs")
print("│    └─→ /app/configs (read-only)")
print("│")
print("│  ✓ d:\\diseñopvbesscar\\scripts")
print("│    └─→ /app/scripts (read-only)")
print("│")
print("└─ Localización: Conexión filesystem entre Windows ↔ WSL 2 ↔ Container")
print()

# Ruta 8: Ejecución
print("┌─ CAPA 8: EJECUCIÓN (Python Script)")
print("│")
print("│  🐍 Comando dentro del container:")
print("│  python -m scripts.run_oe3_simulate --config configs/default.yaml")
print("│")
print("│  Proceso:")
print("│  ├── Lee: /app/configs/default.yaml")
print("│  ├── Lee: /app/data/interim/oe2/ (solar, BESS, chargers)")
print("│  ├── Entrena: SAC/PPO/A2C agents")
print("│  ├── GPU: NVIDIA CUDA 12.7")
print("│  └── Escribe: /app/outputs/oe3/simulations/")
print("│")
print("└─ Localización: Adentro del container (Linux environment)")
print()

# Ruta 9: Resultados
print("┌─ CAPA 9: RESULTADOS (Output Files)")
print("│")
print("│  📊 Archivos generados en el container:")
print("│  /app/outputs/oe3/simulations/")
print("│  ├── sac_results.json")
print("│  ├── ppo_results.json")
print("│  ├── a2c_results.json")
print("│  ├── timeseries_*.csv")
print("│  ├── trace_*.csv")
print("│  └── simulation_summary.json")
print("│")
print("│  Sincronizados automáticamente a Windows:")
print("│  d:\\diseñopvbesscar\\outputs\\oe3\\simulations\\")
print("│")
print("└─ Localización: Visible en Windows vía bind mount")
print()

# Diagrama completo
print("="*100)
print("📡 FLUJO COMPLETO DE DATOS:")
print("="*100)
print("""
Windows (d:\\diseñopvbesscar\\)
        ↓
    (volumen montado)
        ↓
WSL 2 (/mnt/c/...)
        ↓
    (namespace filesystem)
        ↓
Docker Container (/app/)
        ↓
    (Python execution)
        ↓
    (GPU NVIDIA CUDA 12.7)
        ↓
    (SAC/PPO/A2C training)
        ↓
Resultados → /app/outputs/oe3/
        ↓
    (volumen montado)
        ↓
Windows (d:\\diseñopvbesscar\\outputs\\oe3\\) ✓
""")

print("="*100)
print("✅ RESUMEN:")
print("="*100)
print("""
HOST:           d:\\diseñopvbesscar\\
                ↓
DOCKER:         /app/
                ↓
RESULTADOS:     d:\\diseñopvbesscar\\outputs\\oe3\\simulations\\
                
AGENTES:        SAC ✓  |  PPO ✓  |  A2C ✓
STATUS:         Completado ✓
""")
print("="*100 + "\n")
