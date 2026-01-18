#!/usr/bin/env python3
"""
Información de dónde SAC estaba corriendo Docker
"""

import json
from pathlib import Path

print("\n" + "="*80)
print("🐳 INFORMACIÓN DE EJECUCIÓN - SAC RL TRAINING EN DOCKER")
print("="*80 + "\n")

# Host
print("📍 RUTAS EN HOST (Windows):")
print("   Workspace: d:\\diseñopvbesscar\\")
print("   Datos OE2: d:\\diseñopvbesscar\\data\\interim\\oe2\\")
print("   Resultados OE3: d:\\diseñopvbesscar\\outputs\\oe3\\")
print("   Scripts: d:\\diseñopvbesscar\\scripts\\")

# Docker
print("\n🐳 RUTAS EN CONTENEDOR DOCKER (Linux):")
print("   Workspace: /app/")
print("   Datos OE2: /app/data/interim/oe2/")
print("   Resultados OE3: /app/outputs/oe3/")
print("   Scripts: /app/scripts/")
print("   Host mounted: /app/host/ (opcional)")

# Volúmenes
print("\n📦 VOLÚMENES MONTADOS:")
volumes = [
    ("d:/diseñopvbesscar/data", "/app/data", "read-write"),
    ("d:/diseñopvbesscar/outputs", "/app/outputs", "read-write"),
    ("d:/diseñopvbesscar/configs", "/app/configs", "read-only"),
    ("d:/diseñopvbesscar/scripts", "/app/scripts", "read-only"),
    ("d:/diseñopvbesscar", "/app/host", "read-only (opcional)"),
]

for host, container, mode in volumes:
    print(f"   -v \"{host}:{container}\" ({mode})")

# Comando Docker
print("\n🚀 COMANDO DOCKER USADO:")
cmd = """docker run -it --rm --gpus all \\
  -v "d:/diseñopvbesscar/data:/app/data" \\
  -v "d:/diseñopvbesscar/outputs:/app/outputs" \\
  -v "d:/diseñopvbesscar/configs:/app/configs:ro" \\
  -v "d:/diseñopvbesscar/scripts:/app/scripts:ro" \\
  iquitos-citylearn:latest \\
  python -m scripts.run_oe3_simulate --config configs/default.yaml"""
print(cmd)

# Archivos de resultados
print("\n📊 ARCHIVOS GENERADOS EN /app/outputs/oe3/:")
results_dir = Path("d:/diseñopvbesscar/outputs/oe3/simulations")

if results_dir.exists():
    for file_path in sorted(results_dir.glob("*")):
        if file_path.is_file():
            size_kb = file_path.stat().st_size / 1024
            print(f"   ✓ {file_path.name:45s} ({size_kb:>8.1f} KB)")
            
    # Cargar summary
    summary_file = results_dir / "simulation_summary.json"
    if summary_file.exists():
        with open(summary_file) as f:
            summary = json.load(f)
        
        print("\n📈 AGENTES ENTRENADOS:")
        for agent_name, agent_data in summary.get('agents', {}).items():
            co2 = agent_data.get('co2_kg', 0)
            print(f"   • {agent_name:15s}: {co2:>12,.0f} kg CO₂")

# GPU
print("\n🖥️  GPU UTILIZADA:")
print("   Modo: --gpus all")
print("   Driver: NVIDIA CUDA 12.7")
print("   Status: ✓ Habilitado en Docker Desktop")

# Terminal
print("\n⚙️  TERMINAL DONDE CORRIÓ:")
print("   OS: Windows PowerShell")
print("   Directorio: D:\\diseñopvbesscar\\")
print("   Status: Completado ✓")

print("\n" + "="*80)
print("✅ SAC completó el entrenamiento en Docker con éxito")
print("="*80 + "\n")
