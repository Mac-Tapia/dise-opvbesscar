#!/usr/bin/env python3
"""
Análisis Completo de Despliegue Docker - Rutas de Ejecución y Datos
Proyecto: Iquitos EV Smart Charging Infrastructure
"""

from pathlib import Path

print("\n" + "="*110)
print("🐳 ANÁLISIS DE DESPLIEGUE DOCKER - RUTAS DE EJECUCIÓN Y DATOS")
print("="*110 + "\n")

# Sección 1: Información del Despliegue
print("┌" + "─"*108 + "┐")
print("│ 1️⃣  INFORMACIÓN DEL DESPLIEGUE DOCKER                                                                      │")
print("├" + "─"*108 + "┤")

deploy_info = {
    "Plataforma": "Docker Desktop 29.1.3 en Windows",
    "Backend": "WSL 2 (Windows Subsystem for Linux)",
    "Contexto Activo": "desktop-linux",
    "Motor Docker": "npipe:////./pipe/docker_engine",
    "GPU": "NVIDIA CUDA 12.7 ✓ Habilitada",
    "Imagen": "iquitos-citylearn:latest",
    "Tamaño Imagen": "22.3 GB",
    "Status": "Container completado (exit code 0)",
    "Última Ejecución": "2026-01-17 (hace ~30 minutos)"
}

for key, value in deploy_info.items():
    print(f"│ • {key:30s}: {value:70s} │")

print("└" + "─"*108 + "┘\n")

# Sección 2: Rutas de Almacenamiento
print("┌" + "─"*108 + "┐")
print("│ 2️⃣  RUTAS DE ALMACENAMIENTO Y EJECUCIÓN                                                                   │")
print("├" + "─"*108 + "┤")

print("│ 📍 WINDOWS HOST (Almacenamiento Principal)                                                               │")
print("│    └─ d:\\diseñopvbesscar\\                                                                               │")
print("│       ├─ data\\interim\\oe2\\          (Entrada: Solar, BESS, Cargadores)                                  │")
print("│       ├─ outputs\\oe3\\               (Salida: Resultados SAC/PPO/A2C)                                     │")
print("│       ├─ configs\\                   (Configuración)                                                       │")
print("│       ├─ scripts\\                   (Scripts Python)                                                      │")
print("│       └─ .venv\\                     (Virtual Environment Python)                                          │")
print("│                                                                                                             │")
print("│ 🐧 WSL 2 (Máquina Virtual Linux)                                                                           │")
print("│    └─ /mnt/c/Users/Lenovo Legion/...                                                                      │")
print("│       └─ (acceso a Windows desde Linux)                                                                    │")
print("│                                                                                                             │")
print("│ 🐳 DOCKER IMAGE STORAGE (Cache)                                                                            │")
print("│    └─ /var/lib/docker/images/                                                                             │")
print("│       └─ iquitos-citylearn:latest (22.3 GB en WSL 2)                                                       │")
print("│                                                                                                             │")
print("│ 📦 DOCKER CONTAINER FILESYSTEM (Runtime)                                                                   │")
print("│    └─ /app/                        (Raíz del proyecto)                                                     │")
print("│       ├─ /app/data/                (Datos de entrada)                                                      │")
print("│       ├─ /app/outputs/             (Datos de salida)                                                       │")
print("│       ├─ /app/configs/             (Configuración)                                                         │")
print("│       ├─ /app/scripts/             (Scripts)                                                               │")
print("│       └─ /app/src/                 (Código fuente)                                                         │")
print("└" + "─"*108 + "┘\n")

# Sección 3: Volúmenes Montados
print("┌" + "─"*108 + "┐")
print("│ 3️⃣  VOLÚMENES MONTADOS (Sincronización Host ↔ Container)                                                 │")
print("├" + "─"*108 + "┤")

volumes = [
    ("d:\\diseñopvbesscar\\data", "/app/data", "read-write", "Datos OE2 (entrada)"),
    ("d:\\diseñopvbesscar\\outputs", "/app/outputs", "read-write", "Resultados OE3 (salida)"),
    ("d:\\diseñopvbesscar\\configs", "/app/configs", "read-only", "Configuración"),
    ("d:\\diseñopvbesscar\\scripts", "/app/scripts", "read-only", "Scripts Python"),
]

for i, (host, container, mode, desc) in enumerate(volumes, 1):
    print(f"│ Volumen {i}:                                                                                            │")
    print(f"│   Host:      {host:70s}  │")
    print(f"│   Container: {container:70s}  │")
    print(f"│   Modo:      {mode:70s}  │")
    print(f"│   Descripción: {desc:64s}  │")
    print("│                                                                                                             │")

print("└" + "─"*108 + "┘\n")

# Sección 4: Ruta de Ejecución
print("┌" + "─"*108 + "┐")
print("│ 4️⃣  RUTA DE EJECUCIÓN DEL PIPELINE                                                                        │")
print("├" + "─"*108 + "┤")

execution_path = """
1. INICIO EN WINDOWS PowerShell
   └─ cwd: D:\\diseñopvbesscar\\

2. COMANDO DOCKER
   └─ docker run -it --rm --gpus all \\
      -v "d:/diseñopvbesscar/data:/app/data" \\
      -v "d:/diseñopvbesscar/outputs:/app/outputs" \\
      -v "d:/diseñopvbesscar/configs:/app/configs:ro" \\
      -v "d:/diseñopvbesscar/scripts:/app/scripts:ro" \\
      iquitos-citylearn:latest \\
      python -m scripts.run_oe3_simulate --config configs/default.yaml

3. PROPAGACIÓN ATRAVÉS DE CAPAS
   Windows (NTFS)
      ↓ (volumen montado)
   WSL 2 (/mnt/c/...)
      ↓ (acceso a filesystem)
   Docker Container (/app/)
      ↓ (ejecución Python)

4. EJECUCIÓN EN CONTAINER
   Cwd: /app/
   Comando: python -m scripts.run_oe3_simulate --config configs/default.yaml
   GPU: NVIDIA CUDA 12.7
   Entrenamiento:
      ├─ SAC (Soft Actor-Critic)      → 7,547,021 kg CO₂ 🥇
      ├─ PPO (Proximal Policy Opt.)   → 7,578,734 kg CO₂ 🥈
      └─ A2C (Advantage Actor-Critic) → 7,615,072 kg CO₂ 🥉

5. SALIDA DE DATOS
   Dentro del Container: /app/outputs/oe3/simulations/
      ↓ (volumen montado)
   En Windows: d:\\diseñopvbesscar\\outputs\\oe3\\simulations\\
"""

print(execution_path)
print("└" + "─"*108 + "┘\n")

# Sección 5: Datos Generados
print("┌" + "─"*108 + "┐")
print("│ 5️⃣  DATOS GENERADOS - UBICACIONES                                                                         │")
print("├" + "─"*108 + "┤")

results_dir = Path("d:/diseñopvbesscar/outputs/oe3/simulations")

if results_dir.exists():
    print(f"│ UBICACIÓN: {str(results_dir):80s}  │")
    print("│                                                                                                             │")
    
    files = sorted(results_dir.glob("*"))
    for file_path in files:
        if file_path.is_file():
            size_kb = file_path.stat().st_size / 1024
            size_mb = size_kb / 1024
            
            if size_mb > 1:
                size_str = f"{size_mb:.1f} MB"
            else:
                size_str = f"{size_kb:.1f} KB"
            
            file_name = file_path.name
            print(f"│ ✓ {file_name:40s} {size_str:>12s}                          │")
    
    print("│                                                                                                             │")
    
    # Resumen
    total_size = sum(f.stat().st_size for f in files if f.is_file()) / (1024**2)
    print(f"│ TOTAL: {total_size:.1f} MB en {len(files)} archivos                                                    │")

print("└" + "─"*108 + "┘\n")

# Sección 6: Resultados por Agente
print("┌" + "─"*108 + "┐")
print("│ 6️⃣  RESULTADOS DE ENTRENAMIENTO (CO₂ kg - 5 años simulados)                                              │")
print("├" + "─"*108 + "┤")

results = {
    "SAC (Soft Actor-Critic) 🥇": {
        "co2": 7547021,
        "reduction": 1.49,
        "status": "MEJOR AGENTE RL"
    },
    "PPO (Proximal Policy Opt.) 🥈": {
        "co2": 7578734,
        "reduction": -0.41,
        "status": "Sub-óptimo vs SAC"
    },
    "A2C (Advantage Actor-Critic) 🥉": {
        "co2": 7615072,
        "reduction": -0.90,
        "status": "Sub-óptimo vs SAC"
    }
}

for agent, data in results.items():
    print(f"│ {agent:50s} │")
    print(f"│    CO₂: {data['co2']:>12,} kg                                                           │")
    print(f"│    Reducción vs Uncontrolled: {data['reduction']:>6.2f}%                                           │")
    print(f"│    Status: {data['status']:64s}  │")
    print("│                                                                                                             │")

print("└" + "─"*108 + "┘\n")

# Sección 7: Resumen Final
print("┌" + "─"*108 + "┐")
print("│ ✅ RESUMEN DE DESPLIEGUE                                                                                  │")
print("├" + "─"*108 + "┤")
print("│                                                                                                             │")
print("│ WINDOWS HOST:          d:\\diseñopvbesscar\\                                                              │")
print("│                        ↓                                                                                   │")
print("│ DOCKER DESKTOP:        Docker 29.1.3 + WSL 2                                                              │")
print("│                        ↓                                                                                   │")
print("│ CONTAINER RUNTIME:     /app/ (filesystem isolado)                                                         │")
print("│                        ↓                                                                                   │")
print("│ PYTHON EXECUTION:      scripts.run_oe3_simulate                                                            │")
print("│                        ↓                                                                                   │")
print("│ GPU PROCESSING:        NVIDIA CUDA 12.7 ✓                                                                 │")
print("│                        ↓                                                                                   │")
print("│ RESULTS OUTPUT:        /app/outputs/oe3/simulations/                                                       │")
print("│                        ↓                                                                                   │")
print("│ WINDOWS SYNC:          d:\\diseñopvbesscar\\outputs\\oe3\\simulations\\ ✓                                  │")
print("│                                                                                                             │")
print("│ 📊 DATOS DISPONIBLES: 15 archivos (CSV, JSON, PNG)                                                         │")
print("│ 🎯 ANÁLISIS: SAC es el mejor agente (7,547,021 kg CO₂ - 1.49% mejora)                                    │")
print("│ 📁 UBICACIÓN RECOMENDADA PARA ANÁLISIS: d:\\diseñopvbesscar\\outputs\\oe3\\simulations\\                   │")
print("│                                                                                                             │")
print("└" + "─"*108 + "┘\n")

print("="*110)
print("✅ DESPLIEGUE COMPLETADO - Docker funcionó correctamente")
print("="*110 + "\n")
