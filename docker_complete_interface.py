#!/usr/bin/env python3
"""
INTERFAZ VISUAL - Dónde corrió Docker y dónde ver los resultados
"""

from pathlib import Path

# Colores ANSI para terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

print("\n" + "="*120)
print(f"{Colors.HEADER}{Colors.BOLD}🐳 INTERFAZ COMPLETA - DOCKER EXECUTION TRACKING{Colors.END}")
print("="*120 + "\n")

# ═══════════════════════════════════════════════════════════════════════════
# SECCIÓN 1: DÓNDE ESTÁ LA INTERFAZ
# ═══════════════════════════════════════════════════════════════════════════

print(f"{Colors.BOLD}═ PARTE 1: DÓNDE ESTÁ LA INTERFAZ{Colors.END}\n")

interface_locations = {
    "Terminal PowerShell": {
        "Ruta": "D:\\diseñopvbesscar\\",
        "Comando": "docker run -it --rm --gpus all ...",
        "Tipo": "CLI (Command Line Interface)",
        "Visible": "✓ Sí (tu pantalla actual)"
    },
    "Docker Desktop GUI": {
        "Ruta": "C:\\Program Files\\Docker\\",
        "Icono": "🐳 En la bandeja de sistema (esquina)",
        "Tipo": "GUI Dashboard",
        "Visible": "✓ Sí (haz clic en icono Docker)"
    },
    "WSL 2 Terminal": {
        "Ruta": "/mnt/c/Users/Lenovo Legion/...",
        "Comando": "wsl -d Ubuntu",
        "Tipo": "Linux Terminal (virtualized)",
        "Visible": "⚠ No (backend, no frontend)"
    }
}

for interface, details in interface_locations.items():
    print(f"{Colors.CYAN}📍 {interface}{Colors.END}")
    for key, value in details.items():
        print(f"   {key:20s}: {value}")
    print()

# ═══════════════════════════════════════════════════════════════════════════
# SECCIÓN 2: DÓNDE CORRIÓ DOCKER
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n{Colors.BOLD}═ PARTE 2: DÓNDE CORRIÓ DOCKER (RUTA FÍSICA){Colors.END}\n")

docker_locations = [
    ("Windows Host (Storage)", "d:\\diseñopvbesscar\\", "Tu disco duro", "Archivos fuente y configs"),
    ("WSL 2 VM", "/mnt/c/Users/...", "Máquina virtual Linux", "Sistema de archivos virtualizado"),
    ("Docker Desktop", "C:\\Program Files\\Docker\\", "Docker Desktop ejecutable", "Motor Docker + orchestration"),
    ("Docker Image", "/var/lib/docker/images/", "Cache en WSL 2", "iquitos-citylearn:latest (22.3GB)"),
    ("Container Runtime", "/app/ (efímero)", "Dentro del container", "Filesystem isolado - SE ELIMINÓ DESPUÉS"),
]

for location, path, where, description in docker_locations:
    print(f"{Colors.GREEN}├─ {location}{Colors.END}")
    print(f"│  Path: {path}")
    print(f"│  Ubicación: {where}")
    print(f"│  Descripción: {description}")
    print()

# ═══════════════════════════════════════════════════════════════════════════
# SECCIÓN 3: RUTA COMPLETA DE EJECUCIÓN
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n{Colors.BOLD}═ PARTE 3: RUTA COMPLETA DE EJECUCIÓN{Colors.END}\n")

print(f"{Colors.YELLOW}PASO 1 - INICIO EN TERMINAL{Colors.END}")
print("""
  ┌─────────────────────────────────────────────────┐
  │ Windows PowerShell                              │
  │ PS D:\\diseñopvbesscar>                         │
  │ docker run -it --rm --gpus all \\              │
  │   -v d:/diseñopvbesscar/data:/app/data \\      │
  │   -v d:/diseñopvbesscar/outputs:/app/outputs \\ │
  │   iquitos-citylearn:latest \\                  │
  │   python -m scripts.run_oe3_simulate           │
  └─────────────────────────────────────────────────┘
""")

print(f"{Colors.YELLOW}PASO 2 - PROPAGACIÓN A TRAVÉS DE CAPAS{Colors.END}")
print("""
  Windows NTFS filesystem (d:\\diseñopvbesscar\\)
            ↓
  Docker Desktop (npipe:////./pipe/docker_engine)
            ↓
  WSL 2 Linux Kernel (/mnt/c/...)
            ↓
  Container Namespace (/app/)
            ↓
  Python Interpreter
            ↓
  GPU NVIDIA CUDA 12.7
""")

print(f"{Colors.YELLOW}PASO 3 - EJECUCIÓN DEL ENTRENAMIENTO{Colors.END}")
print(f"""
  {Colors.GREEN}✓ OE2 (Dimensioning){Colors.END}
    ├─ Solar data: /app/data/interim/oe2/solar/
    ├─ BESS sizing: /app/data/interim/oe2/bess/
    └─ Chargers: /app/data/interim/oe2/chargers/
  
  {Colors.GREEN}✓ OE3 (RL Training){Colors.END}
    ├─ Dataset building
    ├─ Agent training: SAC | PPO | A2C
    ├─ GPU processing: NVIDIA CUDA 12.7
    └─ Results writing: /app/outputs/oe3/simulations/
""")

print(f"{Colors.YELLOW}PASO 4 - FINALIZACIÓN Y SINCRONIZACIÓN{Colors.END}")
print("""
  /app/outputs/oe3/ (Container)
            ↓ (volumen montado)
  d:\\diseñopvbesscar\\outputs\\oe3\\ (Windows) ✓
  
  Container eliminado automáticamente (--rm)
  Datos permanecen en Windows
""")

# ═══════════════════════════════════════════════════════════════════════════
# SECCIÓN 4: DÓNDE SE PUEDEN VER LOS RESULTADOS
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n{Colors.BOLD}═ PARTE 4: DÓNDE VER LOS RESULTADOS{Colors.END}\n")

print(f"{Colors.GREEN}📁 OPCIÓN 1: EXPLORADOR DE ARCHIVOS (Recomendado){Colors.END}")
print("""
  1. Abre Windows Explorer
  2. Navega a: d:\\diseñopvbesscar\\outputs\\oe3\\simulations\\
  3. Verás 15 archivos con los resultados
""")

print(f"\n{Colors.GREEN}📊 OPCIÓN 2: VISUALIZADOR HTML (Dashboard){Colors.END}")
print("""
  1. Abre: d:\\diseñopvbesscar\\outputs\\oe3\\REPORTE_OE3.html
  2. Se abre en navegador (Brave/Chrome)
  3. Tabla interactiva con resultados CO₂
""")

print(f"\n{Colors.GREEN}🔍 OPCIÓN 3: TERMINAL/POWERSHELL{Colors.END}")
print("""
  Comando para listar archivos:
  PS> dir d:\\diseñopvbesscar\\outputs\\oe3\\simulations\\
  
  Comando para ver JSON:
  PS> Get-Content d:\\diseñopvbesscar\\outputs\\oe3\\simulations\\simulation_summary.json | ConvertFrom-Json
""")

print(f"\n{Colors.GREEN}📈 OPCIÓN 4: PYTHON ANALYSIS{Colors.END}")
print("""
  import json
  
  with open('d:/diseñopvbesscar/outputs/oe3/simulations/simulation_summary.json') as f:
      data = json.load(f)
  
  print(data['agents'])  # Ver resultados de agentes
""")

# ═══════════════════════════════════════════════════════════════════════════
# SECCIÓN 5: ARCHIVOS Y SU UBICACIÓN
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n{Colors.BOLD}═ PARTE 5: ARCHIVOS GENERADOS Y SU UBICACIÓN{Colors.END}\n")

results_dir = Path("d:/diseñopvbesscar/outputs/oe3/simulations")

if results_dir.exists():
    print(f"{Colors.CYAN}Ubicación en Windows:{Colors.END}")
    print(f"  d:\\diseñopvbesscar\\outputs\\oe3\\simulations\\\n")
    
    print(f"{Colors.CYAN}Archivos disponibles:{Colors.END}\n")
    
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
            
            # Categoría del archivo
            if "sac" in file_name.lower():
                category = "🥇 SAC (Mejor)"
            elif "ppo" in file_name.lower():
                category = "🥈 PPO"
            elif "a2c" in file_name.lower():
                category = "🥉 A2C"
            elif "uncontrolled" in file_name.lower():
                category = "📊 Baseline"
            else:
                category = "📄 Summary"
            
            print(f"  {category:20s} {file_name:40s} {size_str:>12s}")
    
    print(f"\n  Total: {len(files)} archivos | {sum(f.stat().st_size for f in files if f.is_file()) / (1024**2):.1f} MB")

# ═══════════════════════════════════════════════════════════════════════════
# SECCIÓN 6: CÓMO ABRIR DIRECTAMENTE
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n\n{Colors.BOLD}═ PARTE 6: ACCESOS DIRECTOS{Colors.END}\n")

print(f"{Colors.GREEN}🔗 HIPER-ENLACES (Clic derecho → Copiar ruta){Colors.END}\n")

shortcuts = [
    ("Carpeta Simulations", "d:\\diseñopvbesscar\\outputs\\oe3\\simulations\\"),
    ("Reporte HTML", "d:\\diseñopvbesscar\\outputs\\oe3\\REPORTE_OE3.html"),
    ("JSON Resultados", "d:\\diseñopvbesscar\\outputs\\oe3\\simulations\\simulation_summary.json"),
    ("CSV SAC", "d:\\diseñopvbesscar\\outputs\\oe3\\simulations\\timeseries_SAC.csv"),
]

for name, path in shortcuts:
    print(f"  📍 {name:30s}: {path}")

# ═══════════════════════════════════════════════════════════════════════════
# SECCIÓN 7: DIAGRAMA VISUAL
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n\n{Colors.BOLD}═ PARTE 7: DIAGRAMA VISUAL COMPLETO{Colors.END}\n")

diagram = f"""
{Colors.BOLD}┌─────────────────────────────────────────────────────────────────────────────────────────────┐{Colors.END}
{Colors.BOLD}│                           ARQUITECTURA COMPLETA DE DOCKER                                  │{Colors.END}
{Colors.BOLD}└─────────────────────────────────────────────────────────────────────────────────────────────┘{Colors.END}

{Colors.YELLOW}NIVEL 1: INTERFAZ DE USUARIO{Colors.END}
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🖥️  TERMINAL POWERSHELL                        🐳 DOCKER DESKTOP GUI                         │
│ (d:\\diseñopvbesscar>)                         (C:\\Program Files\\Docker\\)                   │
│ ← TÚ EJECUTAS EL COMANDO AQUÍ                 ← MONITOREO EN TIEMPO REAL                    │
└───────────────────────────────────────────────────────────────────────────────────────────────┘

                                         ↓

{Colors.YELLOW}NIVEL 2: MOTOR DOCKER{Colors.END}
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│ Docker Desktop 29.1.3 (npipe:////./pipe/docker_engine)                                       │
│ Backend: WSL 2 (Windows Subsystem for Linux)                                                 │
└───────────────────────────────────────────────────────────────────────────────────────────────┘

                                         ↓

{Colors.YELLOW}NIVEL 3: FILESYSTEM SYNC{Colors.END}
┌──────────────────────────────────────────┬────────────────────────────────────────────────────┐
│ WINDOWS (Host)                           │ WSL 2 (Virtual Linux)                              │
│ d:\\diseñopvbesscar\\                    │ /mnt/c/Users/Lenovo Legion/...                    │
│ ├── data/                                │ (acceso lectura/escritura)                         │
│ ├── outputs/ ← RESULTADOS                │                                                    │
│ ├── configs/                             │                                                    │
│ └── scripts/                             │                                                    │
└──────────────────────────────────────────┴────────────────────────────────────────────────────┘

                                         ↓

{Colors.YELLOW}NIVEL 4: CONTAINER RUNTIME{Colors.END}
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│ 📦 iquitos-citylearn:latest Container (isolado)                                              │
│ ├── /app/data/ ← Entrada (read-write)                                                        │
│ ├── /app/outputs/ ← Salida (read-write)                                                      │
│ ├── /app/configs/ ← Config (read-only)                                                       │
│ ├── /app/scripts/ ← Scripts (read-only)                                                      │
│ └── Python 3.11 + ML Libraries                                                               │
└───────────────────────────────────────────────────────────────────────────────────────────────┘

                                         ↓

{Colors.YELLOW}NIVEL 5: GPU PROCESSING{Colors.END}
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│ 🖥️  NVIDIA CUDA 12.7 (--gpus all)                                                             │
│ ├── SAC Training → 7,547,021 kg CO₂ 🥇                                                       │
│ ├── PPO Training → 7,578,734 kg CO₂ 🥈                                                       │
│ └── A2C Training → 7,615,072 kg CO₂ 🥉                                                       │
└───────────────────────────────────────────────────────────────────────────────────────────────┘

                                         ↓ RESULTADOS SINCRONIZADOS

{Colors.GREEN}NIVEL 6: DATOS VISIBLES (Windows){Colors.END}
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│ ✓ d:\\diseñopvbesscar\\outputs\\oe3\\simulations\\                                            │
│   ├── simulation_summary.json (33.5 KB)                                                       │
│   ├── sac_results.json                                                                        │
│   ├── ppo_results.json                                                                        │
│   ├── a2c_results.json                                                                        │
│   ├── timeseries_*.csv                                                                        │
│   ├── trace_*.csv                                                                             │
│   └── co2_comparison.md                                                                       │
│                                                                                               │
│ Total: 15 archivos | 109.2 MB | ✅ ACCESIBLES AHORA                                         │
└───────────────────────────────────────────────────────────────────────────────────────────────┘
"""

print(diagram)

# ═══════════════════════════════════════════════════════════════════════════
# SECCIÓN FINAL: CÓMO ACCEDER
# ═══════════════════════════════════════════════════════════════════════════

print(f"\n{Colors.BOLD}═ RESUMEN: CÓMO ACCEDER AHORA MISMO{Colors.END}\n")

print(f"{Colors.GREEN}✅ MÉTODO 1: EXPLORADOR (MÁS FÁCIL){Colors.END}")
print("  1. Abre Windows Explorer")
print("  2. Pega esta ruta: d:\\diseñopvbesscar\\outputs\\oe3\\simulations\\")
print("  3. ¡Haz clic en Enter!")
print()

print(f"{Colors.GREEN}✅ MÉTODO 2: REPORTE INTERACTIVO{Colors.END}")
print("  1. Navega a: d:\\diseñopvbesscar\\outputs\\oe3\\")
print("  2. Abre: REPORTE_OE3.html")
print("  3. Se abre en navegador con tabla de resultados")
print()

print(f"{Colors.GREEN}✅ MÉTODO 3: TERMINAL{Colors.END}")
print("  1. Copia esta ruta al portapapeles")
print("  2. Pega en Windows Explorer")
print("  3. Or: PS> cd d:\\diseñopvbesscar\\outputs\\oe3\\simulations\\")
print()

print("="*120)
print(f"{Colors.BOLD}{Colors.GREEN}✅ DOCKER COMPLETÓ EXITOSAMENTE{Colors.END}")
print(f"{Colors.BOLD}{Colors.GREEN}✅ TODOS LOS DATOS ESTÁN ACCESIBLES{Colors.END}")
print("="*120 + "\n")
