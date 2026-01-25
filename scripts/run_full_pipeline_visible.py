#!/usr/bin/env python3
"""
Pipeline Completo: Dataset → Baseline → Entrenamiento de Agentes
Ejecuta TODO en secuencia con output visible en consola.
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

def print_section(title):
    """Print a section header."""
    print("\n" + "="*100)
    print(f"  {title}")
    print("="*100 + "\n")

def run_command(cmd, description):
    """Run a command and show output."""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {description}")
    print("-" * 100)
    
    try:
        _result = subprocess.run(cmd, shell=True, check=True, text=True)
        print(f"✓ {description} - COMPLETADO\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ ERROR en {description}")
        print(f"Exit code: {e.returncode}\n")
        return False
    except Exception as e:
        print(f"\n✗ ERROR inesperado: {e}\n")
        return False

def main():
    print_section("PIPELINE COMPLETO: Dataset - Baseline - Agentes RL")
    print("Duracion estimada: 6-16 horas (GPU RTX 4060)")
    print("Verificando pre-requisitos...")
    
    # Verificar que los datasets OE2 existan
    oe2_solar = Path("data/interim/oe2/solar/solar_generation.csv")
    if not oe2_solar.exists():
        print("\n✗ ERROR: Falta data OE2 solar")
        print("  Ejecuta primero: python -m scripts.run_oe2_solar --config configs/default.yaml")
        return False
    print(f"✓ OE2 Solar data existente ({oe2_solar.stat().st_size / 1e6:.2f} MB)")
    
    oe2_chargers = Path("data/interim/oe2/chargers")
    if not oe2_chargers.exists():
        print("\n✗ ERROR: Falta data OE2 chargers")
        return False
    charger_files = list(oe2_chargers.glob("*.csv"))
    print(f"✓ OE2 Chargers data existente ({len(charger_files)} archivos)")
    
    oe2_bess = Path("data/interim/oe2/bess/bess_results.json")
    if not oe2_bess.exists():
        print("\n✗ ERROR: Falta data OE2 BESS")
        return False
    print(f"✓ OE2 BESS data existente")
    
    print("\n✓ Todos los pre-requisitos (OE2) cumplidos\n")
    
    # FASE 1: Construir Dataset CityLearn
    print_section("FASE 1: Construir Dataset CityLearn")
    
    if not run_command(
        ".venv\\Scripts\\Activate.ps1 ; python -m scripts.run_oe3_build_dataset --config configs/default.yaml",
        "Construyendo dataset CityLearn (schema_pv_bess.json)"
    ):
        print("✗ Fallo en construcción de dataset. Abortando.")
        return False
    
    # FASE 2: Calcular Baseline Uncontrolled
    print_section("FASE 2: Calcular Baseline Uncontrolled (Sin Control)")
    
    if not run_command(
        ".venv\\Scripts\\Activate.ps1 ; python -m scripts.run_uncontrolled_baseline --config configs/default.yaml",
        "Ejecutando baseline sin control inteligente (8760 pasos)"
    ):
        print("✗ Fallo en baseline. Abortando.")
        return False
    
    # FASE 3: Entrenar Agentes RL
    print_section("FASE 3: Entrenar Agentes RL (SAC → PPO → A2C)")
    
    if not run_command(
        ".venv\\Scripts\\Activate.ps1 ; python -m scripts.run_oe3_simulate --config configs/default.yaml",
        "Entrenando SAC, PPO, A2C en secuencia"
    ):
        print("✗ Fallo en entrenamiento. Abortando.")
        return False
    
    # FASE 4: Generar Comparativa
    print_section("FASE 4: Generar Tabla Comparativa de Resultados")
    
    if not run_command(
        ".venv\\Scripts\\Activate.ps1 ; python -m scripts.run_oe3_co2_table --config configs/default.yaml",
        "Generando tabla de comparación CO₂"
    ):
        print("⚠  Advertencia: No se pudo generar tabla. Continuando...")
    
    # Resumen final
    print_section("✓ PIPELINE COMPLETADO EXITOSAMENTE")
    
    print(f"Tiempo total: Ver logs en training_reentrenamiento_*.log")
    print("\nArtefactos generados:")
    print("  Dataset:     data/processed/citylearn/iquitos_ev_mall/")
    print("  Baseline:    outputs/oe3/simulations/timeseries_uncontrolled.csv")
    print("  SAC:         outputs/oe3/simulations/timeseries_sac.csv")
    print("  PPO:         outputs/oe3/simulations/timeseries_ppo.csv")
    print("  A2C:         outputs/oe3/simulations/timeseries_a2c.csv")
    print("  Tabla:       outputs/oe3/simulations/co2_comparison.md")
    print("  Resumen:     outputs/oe3/simulations/simulation_summary.json")
    print("\nPróximos pasos:")
    print("  1. Revisar simulation_summary.json para ver mejor agente")
    print("  2. Analizar timeseries_*.csv para ver evolución")
    print("  3. Comparar CO₂: baseline vs SAC vs PPO vs A2C")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
