#!/usr/bin/env python3
"""Monitor de entrenamiento SAC en tiempo real - muestra progress, GPU, checkpoints."""
from __future__ import annotations

import subprocess
from pathlib import Path
from datetime import datetime
import time
import sys

def get_latest_checkpoint() -> tuple[str, int] | None:
    """Retorna (nombre_checkpoint, step) del más reciente."""
    cp_dir = Path("analyses/oe3/training/checkpoints/sac")
    if not cp_dir.exists():
        return None

    checkpoints = sorted(cp_dir.glob("sac_step_*.zip"),
                        key=lambda p: int(p.stem.split("_")[-1]) if "_" in p.stem else 0)
    if not checkpoints:
        return None

    latest = checkpoints[-1]
    step = int(latest.stem.split("_")[-1]) if "_" in latest.stem else 0
    return latest.name, step

def get_gpu_status() -> dict:
    """Retorna uso de GPU."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            line = result.stdout.strip().split('\n')[0]
            gpu_util, mem_used, mem_total = line.split(", ")
            return {
                "gpu_util": gpu_util.strip(),
                "mem_used": mem_used.strip(),
                "mem_total": mem_total.strip()
            }
    except:
        pass
    return {"gpu_util": "N/A", "mem_used": "N/A", "mem_total": "N/A"}

def get_process_status() -> dict:
    """Retorna status del proceso Python."""
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -match 'continue_sac'} | Select-Object Id"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if "Id" in result.stdout:
            return {"running": True, "raw": result.stdout.strip()}
        return {"running": False}
    except:
        return {"running": False}

def print_status():
    """Imprime estado actual."""
    print("\n" + "="*70)
    print(f"SAC Training Monitor | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    # Checkpoint info
    cp_info = get_latest_checkpoint()
    if cp_info:
        name, step = cp_info
        print(f"✅ Último checkpoint: {name} (paso {step:,})")
    else:
        print("❌ No hay checkpoints")

    # GPU status
    gpu = get_gpu_status()
    print(f"\n📊 GPU:")
    print(f"   Utilización: {gpu['gpu_util']}")
    print(f"   Memoria: {gpu['mem_used']} / {gpu['mem_total']}")

    # Process status
    proc = get_process_status()
    print(f"\n🔄 Proceso:")
    if proc.get("running"):
        print(f"   Status: ✅ EN EJECUCIÓN")
    else:
        print(f"   Status: ⏸️  DETENIDO")

    # Archivo de salida más reciente
    output_file = Path("outputs/oe3/simulations/sac_pv_bess.json")
    if output_file.exists():
        stat = output_file.stat()
        age_secs = (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).total_seconds()
        age_mins = int(age_secs / 60)
        size_kb = stat.st_size / 1024
        print(f"\n📁 Salida:")
        print(f"   Archivo: {output_file.name}")
        print(f"   Tamaño: {size_kb:.1f} KB")
        print(f"   Actualizado hace: {age_mins} minutos atrás")

        # Leer últimas líneas
        try:
            with open(output_file) as f:
                content = f.read()
                if content.strip():
                    # Intentar parse last line
                    lines = content.strip().split('\n')
                    for line in lines[-3:]:
                        if line.strip():
                            print(f"   Último: {line[:65]}...")
        except:
            pass

    # Timeline estimado
    _cp_name, step = cp_info if cp_info else ("none", 0)
    if step > 0:
        episodes_completed = step // 3500  # ~3500 steps per episode
        episodes_remaining = 5 - episodes_completed
        time_per_episode = 12  # minutos
        eta = episodes_remaining * time_per_episode
        print(f"\n⏱️  Estimado:")
        print(f"   Episodios completados: {episodes_completed}/5")
        print(f"   ETA de finalización: {eta} minutos")

    print("="*70 + "\n")

if __name__ == "__main__":
    # Loop con actualización cada N segundos
    interval = 10 if len(sys.argv) < 2 else int(sys.argv[1])

    try:
        while True:
            print_status()
            print(f"Próxima actualización en {interval}s (Ctrl+C para detener)...")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n✅ Monitor detenido")
        sys.exit(0)
