#!/usr/bin/env python3
"""
Verificación simple de archivos técnicos generados por PPO al final del entrenamiento.
"""
from pathlib import Path
import json
import pandas as pd

print("\n" + "="*80)
print("📊 VERIFICACIÓN POST-ENTRENAMIENTO: ARCHIVOS TÉCNICOS PPO")
print("="*80 + "\n")

ppo_dir = Path("outputs/agents/ppo")
expected_files = {
    "result_ppo.json": "Resultados principales (CO2, grid, etc)",
    "timeseries_ppo.csv": "Datos horarios (8,760 timesteps × 15 columnas)",
    "trace_ppo.csv": "Observaciones + acciones + rewards",
    "ppo_summary.json": "Resumen ejecutivo del agente",
}

print(f"Directorio: {ppo_dir}\n")

if not ppo_dir.exists():
    print("❌ Directorio no existe")
    exit(1)

all_present = True
print("📋 ARCHIVOS ENCONTRADOS:\n")

for filename, description in expected_files.items():
    filepath = ppo_dir / filename

    if filepath.exists():
        size = filepath.stat().st_size
        size_str = f"{size/1024/1024:.2f} MB" if size > 1024*1024 else f"{size/1024:.2f} KB"

        # Verificar contenido
        if filename.endswith(".json"):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                    print(f"✅ {filename}")
                    print(f"   └─ {size_str} | Keys: {', '.join(list(data.keys())[:3])}...")
            except Exception as e:
                print(f"⚠️  {filename} (JSON inválido: {e})")
                all_present = False
        elif filename.endswith(".csv"):
            try:
                df = pd.read_csv(filepath, nrows=1)
                rows = sum(1 for _ in open(filepath)) - 1
                cols = len(df.columns)
                print(f"✅ {filename}")
                print(f"   └─ {size_str} | {rows:,} filas × {cols} columnas")
            except Exception as e:
                print(f"⚠️  {filename} (CSV inválido: {e})")
                all_present = False
    else:
        print(f"❌ {filename} - NO ENCONTRADO")
        print(f"   Descripción: {description}")
        all_present = False
    print()

print("="*80)
if all_present:
    print("✅ TODOS LOS ARCHIVOS TÉCNICOS GENERADOS CORRECTAMENTE")
else:
    print("⏳ Algunos archivos aún no se han generado")
    print("   (El entrenamiento podría aún estar en curso)")
print("="*80 + "\n")
