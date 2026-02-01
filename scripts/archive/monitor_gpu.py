#!/usr/bin/env python3
"""
Script de monitoreo de GPU para entrenamiento A2C
Verifica si el entrenamiento está usando GPU al máximo
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def check_nvidia_gpu() -> bool:
    """Verifica si NVIDIA GPU está disponible."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            gpu_names = result.stdout.strip().split("\n")
            print("✅ NVIDIA GPU DISPONIBLE:")
            for i, name in enumerate(gpu_names):
                if name.strip():
                    print(f"   GPU {i}: {name.strip()}")
            return True
        else:
            print("❌ NVIDIA GPU NO DISPONIBLE")
            return False
    except FileNotFoundError:
        print("❌ nvidia-smi NO encontrado (NVIDIA drivers no instalados)")
        return False
    except subprocess.TimeoutExpired:
        print("⚠️  nvidia-smi timeout")
        return False
    except Exception as e:
        print(f"❌ Error verificando GPU: {e}")
        return False


def check_gpu_memory() -> bool:
    """Verifica uso de memoria GPU."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            print("\n✅ USO DE MEMORIA GPU:")
            for i, line in enumerate(lines):
                if line.strip():
                    used, total = line.strip().split(", ")
                    used_mb = float(used.strip())
                    total_mb = float(total.strip())
                    percent = (used_mb / total_mb) * 100

                    bar_length = 30
                    filled = int(bar_length * percent / 100)
                    bar = "█" * filled + "░" * (bar_length - filled)

                    print(f"   GPU {i}: [{bar}] {percent:.1f}% ({used_mb:.0f}MB / {total_mb:.0f}MB)")

            return True
        else:
            print("⚠️  No se pudo obtener info de memoria GPU")
            return False
    except Exception as e:
        print(f"❌ Error obteniendo memoria GPU: {e}")
        return False


def check_gpu_utilization() -> bool:
    """Verifica porcentaje de utilización GPU."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            utils = result.stdout.strip().split("\n")
            print("\n✅ UTILIZACIÓN GPU:")
            for i, util_str in enumerate(utils):
                if util_str.strip():
                    util = float(util_str.strip())

                    bar_length = 30
                    filled = int(bar_length * util / 100)
                    bar = "█" * filled + "░" * (bar_length - filled)

                    status = "🔥 MÁXIMO" if util > 90 else "✅ BUENO" if util > 70 else "⚠️  BAJO"
                    print(f"   GPU {i}: [{bar}] {util:.1f}% {status}")

            return True
        else:
            print("⚠️  No se pudo obtener utilización GPU")
            return False
    except Exception as e:
        print(f"❌ Error obteniendo utilización GPU: {e}")
        return False


def check_python_processes() -> None:
    """Verifica procesos Python activos."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "TABLE"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            print("\n✅ PROCESOS PYTHON ACTIVOS:")
            lines = result.stdout.strip().split("\n")
            count = 0
            for line in lines[3:]:  # Skip header
                if line.strip():
                    print(f"   {line}")
                    count += 1

            if count == 0:
                print("   ℹ️  No hay procesos Python activos")
    except Exception as e:
        print(f"⚠️  Error listando procesos: {e}")


def check_training_status() -> None:
    """Verifica estado del entrenamiento."""
    training_log = Path("training_a2c_robust.log")
    if training_log.exists():
        try:
            with open(training_log, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    print("\n✅ ESTADO DEL ENTRENAMIENTO (últimas líneas):")
                    for line in lines[-5:]:
                        print(f"   {line.rstrip()}")
        except Exception as e:
            print(f"⚠️  Error leyendo log: {e}")
    else:
        print("\n⚠️  Log de entrenamiento no encontrado")


def main() -> None:
    """Main function."""
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║         🔍 MONITOR DE GPU - ENTRENAMIENTO A2C                 ║")
    print("║                   27 Enero 2026                               ║")
    print("╚════════════════════════════════════════════════════════════════╝\n")

    # Verificaciones
    has_gpu = check_nvidia_gpu()

    if has_gpu:
        check_gpu_memory()
        check_gpu_utilization()
    else:
        print("\n⚠️  SIN GPU - Usando CPU (entrenamiento será más lento)")

    check_python_processes()
    check_training_status()

    print("\n" + "═" * 64)

    if has_gpu:
        print("✅ GPU detectada - Monitorea utilización regularmente")
        print("   Comando: nvidia-smi -l 1  (actualiza cada segundo)")
    else:
        print("⚠️  No hay GPU - El entrenamiento usará solo CPU")
        print("   Para mejor performance, necesita NVIDIA GPU + CUDA")

    print("═" * 64 + "\n")


if __name__ == "__main__":
    main()
