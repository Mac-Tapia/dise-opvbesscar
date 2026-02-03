#!/usr/bin/env python3
"""
🚀 SCRIPT PARA INICIAR ENTRENAMIENTO ROBUSTO CON MÁXIMA VISIBILIDAD

Uso:
    python scripts/quick_train.py

Qué hace:
    1. Limpia logs antiguos
    2. Inicia el entrenamiento con monitoreo visible
    3. Muestra progreso en tiempo real
    4. Genera reporte final automático
"""

import subprocess
import time
import json
import sys
from pathlib import Path
from datetime import datetime

def print_banner(text: str):
    """Imprime un banner visual."""
    print("\n" + "="*80)
    print(text.center(80))
    print("="*80 + "\n")

def main():
    print_banner("🚀 ENTRENAMIENTO ROBUSTO CON VISIBILIDAD")

    # Paths
    project_root = Path(__file__).parent.parent
    training_log = project_root / "training_live.log"
    status_file = project_root / "outputs" / "oe3_simulations" / "training_status.json"

    print(f"📍 Proyecto: {project_root}")
    print(f"📝 Log: {training_log}")
    print(f"📊 Estado: {status_file}\n")

    # Limpiar log anterior
    if training_log.exists():
        training_log.unlink()
        print("🧹 Log anterior limpiado\n")

    print("🎯 Iniciando entrenamiento...")
    print("💡 Consejo: Abre otro terminal y ejecuta:")
    print(f"   watch -n 5 'tail -20 {training_log}'")
    print("   O monitorea en tiempo real:")
    print(f"   tail -f {training_log}\n")

    # Preparar comando
    cmd = [
        sys.executable,
        "-m", "scripts.run_oe3_simulate",
        "--config", "configs/default.yaml",
        "--skip-baseline"
    ]

    print("📢 INICIANDO COMANDO:")
    print("   " + " ".join(cmd) + "\n")
    print("⏳ El entrenamiento comenzará ahora...\n")

    # Ejecutar en foreground para ver output
    try:
        with open(training_log, "w") as log_file:
            process = subprocess.Popen(
                cmd,
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1  # Line buffering
            )

            # Leer output línea por línea
            for line in process.stdout:
                # Escribir a log
                log_file.write(line)
                log_file.flush()

                # Mostrar en terminal
                sys.stdout.write(line)
                sys.stdout.flush()

        # Esperar a que termine
        exit_code = process.wait()

        if exit_code == 0:
            print_banner("✅ ENTRENAMIENTO COMPLETADO EXITOSAMENTE")

            # Intentar leer resumen
            summary_file = project_root / "outputs" / "oe3_simulations" / "simulation_summary.json"
            if summary_file.exists():
                print("📊 RESUMEN FINAL:\n")
                try:
                    with open(summary_file) as f:
                        summary = json.load(f)
                    print(f"🏆 Mejor agente: {summary.get('best_agent', 'desconocido')}")
                    print(f"📈 Resultados guardados en: {summary_file}")
                except Exception as e:
                    print(f"No se pudo leer resumen: {e}")
        else:
            print_banner("❌ ENTRENAMIENTO FALLÓ")
            print(f"Exit code: {exit_code}")

    except KeyboardInterrupt:
        print_banner("⚠️  ENTRENAMIENTO CANCELADO POR USUARIO")
    except Exception as e:
        print_banner("❌ ERROR DURANTE EJECUCIÓN")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
