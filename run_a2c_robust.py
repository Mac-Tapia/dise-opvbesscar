#!/usr/bin/env python3
"""
LANZADOR ROBUSTO - Entrenar A2C con verificacion completa
Sistema listo: Python 3.11, Schema CityLearn v2, datos de 1 ano
"""
from __future__ import annotations

import sys
import subprocess
from pathlib import Path

def main() -> int:
    print("\n" + "="*80)
    print("LANZADOR ROBUSTO A2C - ENTRENAMIENTO CON VERIFICACION")
    print("="*80)

    # ====================================================================
    # PASO 1: Verificar Python 3.11
    # ====================================================================
    print("\n[PASO 1/4] Verificando entorno Python...")
    if sys.version_info[:2] != (3, 11):
        print(f"  [FAIL] Se requiere Python 3.11, tienes Python {sys.version_info[0]}.{sys.version_info[1]}")
        return 1
    print(f"  [OK] Python 3.11.{sys.version_info[2]} detectado")

    # ====================================================================
    # PASO 2: Verificar que el sistema esta listo
    # ====================================================================
    print("\n[PASO 2/4] Ejecutando test de integracion...")
    result = subprocess.run(
        [sys.executable, "test_integration_complete.py"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("  [FAIL] Test de integracion fallo")
        print("\nSalida:")
        print(result.stdout)
        if result.stderr:
            print("\nErrores:")
            print(result.stderr)
        return 1

    print("  [OK] Sistema verificado y listo")

    # ====================================================================
    # PASO 3: Lanzar entrenamiento
    # ====================================================================
    print("\n[PASO 3/4] Preparando entrenamiento A2C...")
    print("  - Schema: CityLearn v2")
    print("  - Timesteps: 8,760 (1 ano)")
    print("  - Agente: A2C")
    print("  - Config: configs/default.yaml")

    print("\n[PASO 4/4] Lanzando entrenamiento A2C...")
    print("-" * 80)

    # ====================================================================
    # EJECUTAR A2C
    # ====================================================================
    try:
        result = subprocess.run(
            [sys.executable, "-m", "scripts.run_a2c_only", "--config", "configs/default.yaml"],
            cwd=Path(__file__).parent
        )
        return result.returncode
    except KeyboardInterrupt:
        print("\n[INFO] Entrenamiento interrumpido por usuario")
        return 1
    except Exception as e:
        print(f"\n[ERROR] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
