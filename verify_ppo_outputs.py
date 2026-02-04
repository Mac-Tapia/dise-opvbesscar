#!/usr/bin/env python3
"""
Monitoreo de archivos técnicos generados por PPO en tiempo real.
"""
from __future__ import annotations

from pathlib import Path
import time
from datetime import datetime
from typing import Dict

ppo_dir: Path = Path("d:/diseñopvbesscar/outputs/agents/ppo")
expected_files: list[str] = [
    "result_ppo.json",
    "timeseries_ppo.csv",
    "trace_ppo.csv",
    "ppo_summary.json",
]

print("\n" + "="*80)
print("📊 VERIFICACIÓN DE ARCHIVOS TÉCNICOS PPO")
print("="*80)
print(f"Directorio: {ppo_dir}\n")

ppo_dir.mkdir(parents=True, exist_ok=True)

print("⏳ Monitoreando generación de archivos...\n")

last_sizes: Dict[str, int] = {}
while True:
    print(f"[{datetime.now().strftime('%H:%M:%S')}]")

    # Listar archivos existentes
    existing_files = list(ppo_dir.glob("*"))

    if existing_files:
        for file_path in sorted(existing_files):
            file_size: int = file_path.stat().st_size
            size_str: str = f"{file_size/1024:.1f} KB" if file_size > 1024 else f"{file_size} bytes"

            # Detectar cambios de tamaño
            if file_path.name in last_sizes and last_sizes[file_path.name] != file_size:
                print(f"  ✅ {file_path.name:<30} {size_str:<12} (ACTUALIZADO)")
            else:
                print(f"  ✓ {file_path.name:<30} {size_str:<12}")

            last_sizes[file_path.name] = file_size
    else:
        print("  (Sin archivos todavía - entrenamiento en progreso...)")

    # Verificar archivos esperados
    missing: list[str] = [f for f in expected_files if not (ppo_dir / f).exists()]
    if missing:
        print(f"\n  ⏳ Esperando: {', '.join(missing)}")
    else:
        print("\n  ✅ TODOS LOS ARCHIVOS TÉCNICOS GENERADOS:")
        for f in expected_files:
            expected_path: Path = ppo_dir / f
            if expected_path.exists():
                file_size_kb: float = expected_path.stat().st_size / 1024
                print(f"     ✓ {f:<30} {file_size_kb:>8.1f} KB")

    print("-" * 80)
    time.sleep(5)

