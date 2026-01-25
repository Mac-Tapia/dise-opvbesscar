#!/usr/bin/env python3
"""
Pipeline simplificado: Ejecuta run_oe3_simulate que incluye TODO
- Dataset CityLearn
- Baseline Uncontrolled
- Entrenamiento SAC, PPO, A2C
- Comparativa

TODO visible en consola.
"""

import sys
import subprocess

def main():
    print("\n" + "="*100)
    print("PIPELINE COMPLETO CON OUTPUT VISIBLE")
    print("="*100)
    print("\nEjecutando: python -m scripts.run_oe3_simulate")
    print("Incluye:")
    print("  1. Construcción de Dataset CityLearn")
    print("  2. Cálculo de Baseline Uncontrolled (sin control)")
    print("  3. Entrenamiento SAC")
    print("  4. Entrenamiento PPO")
    print("  5. Entrenamiento A2C")
    print("  6. Tabla comparativa CO2")
    print("\nDuración estimada: 6-16 horas (GPU RTX 4060)")
    print("\n" + "="*100 + "\n")
    
    cmd = (
        ".venv\\Scripts\\Activate.ps1 ; "
        "python -m scripts.run_oe3_simulate --config configs/default.yaml"
    )
    
    try:
        subprocess.run(cmd, shell=True, check=True)
        print("\n" + "="*100)
        print("PIPELINE COMPLETADO EXITOSAMENTE")
        print("="*100)
        print("\nResultados guardados en:")
        print("  - outputs/oe3/simulations/simulation_summary.json")
        print("  - outputs/oe3/simulations/co2_comparison.md")
        print("  - outputs/oe3/simulations/timeseries_*.csv")
        print("\nVerifica el mejor agente en simulation_summary.json")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: Salida con codigo {e.returncode}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
