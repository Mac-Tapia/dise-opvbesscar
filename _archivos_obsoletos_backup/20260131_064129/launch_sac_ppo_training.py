#!/usr/bin/env python
"""
Script wrapper para lanzar entrenamiento SAC + PPO en background
sin interrupciones, saltando baseline y A2C
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

def main():
    project_root = Path(__file__).parent
    config_file = project_root / "configs" / "sac_ppo_only.yaml"

    # Verificar que config existe
    if not config_file.exists():
        print(f"❌ Config no encontrado: {config_file}")
        sys.exit(1)

    print("\n" + "="*80)
    print("🚀 LANZANDO ENTRENAMIENTO SAC + PPO")
    print("="*80)
    print(f"\n✅ Configuración: {config_file}")
    print("✅ Agentes: SAC + PPO (sin baseline, sin A2C)")
    print("✅ Python: 3.11 (proyecto)")
    print("\n⏱️  Tiempo estimado: 50-55 minutos")
    print("📝 Log: logs/training_sac_ppo.log")
    print("\n" + "="*80 + "\n")

    # Crear directorio logs si no existe
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)

    log_file = logs_dir / "training_sac_ppo.log"

    # Lanzar proceso en background
    with open(log_file, "w", encoding="utf-8") as log_f:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "scripts.run_oe3_simulate",
                "--config",
                str(config_file),
            ],
            cwd=str(project_root),
            stdout=log_f,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )

    print(f"✅ Proceso lanzado con PID: {process.pid}")
    print(f"✅ Log file: {log_file}")
    print(f"\n💡 Para monitorear:")
    print(f"   Get-Content -Tail 50 {log_file} -Wait")
    print(f"\n✅ Tu consola está LIBRE para otros comandos")

if __name__ == "__main__":
    main()
