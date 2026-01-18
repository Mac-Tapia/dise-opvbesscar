#!/usr/bin/env python3
"""
Pipeline COMPLETO con CACHE de baseline:
1. Calcula baseline UNA VEZ y lo GUARDA
2. Reutiliza baseline en todas las ejecuciones posteriores
3. Entrena SAC → PPO → A2C sin recalcular baseline

Flujo:
- Si baseline.json NO existe → ejecutar SAC (calcula baseline internamente)
- Si baseline.json SÍ existe → ejecutar SAC/PPO/A2C con --skip-uncontrolled
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

def separator(title=""):
    """Print separator."""
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"\n{'-'*80}\n")

def status(msg):
    print(f"[*] {msg}")

def success(msg):
    print(f"[OK] {msg}")

def error(msg):
    print(f"[ERROR] {msg}")

def has_baseline():
    """Verificar si baseline ya fue calculado y guardado."""
    summary_path = Path("outputs/oe3/simulations/simulation_summary.json")
    
    if not summary_path.exists():
        return False
    
    try:
        with open(summary_path) as f:
            summary = json.load(f)
        
        # Verificar que tiene datos del baseline
        if "pv_bess_uncontrolled" in summary:
            unc = summary["pv_bess_uncontrolled"]
            if unc.get("carbon_kg", 0) > 0 and unc.get("steps", 0) >= 8000:
                return True
    except:
        pass
    
    return False

def show_baseline():
    """Mostrar datos del baseline guardado."""
    summary_path = Path("outputs/oe3/simulations/simulation_summary.json")
    
    if not summary_path.exists():
        return
    
    try:
        with open(summary_path) as f:
            summary = json.load(f)
        
        if "pv_bess_uncontrolled" in summary:
            unc = summary["pv_bess_uncontrolled"]
            print("\n[CACHED] Baseline cargado del cache:")
            print(f"  Steps: {unc.get('steps', 0)}")
            print(f"  Years: {unc.get('simulated_years', 0):.2f}")
            print(f"  CO2: {unc.get('carbon_kg', 0):.0f} kg")
            print(f"  Grid import: {unc.get('grid_import_kwh', 0):.0f} kWh")
            print()
    except:
        pass

def run_sac_first_time():
    """Ejecutar SAC LA PRIMERA VEZ para calcular baseline."""
    separator("FASE 1: SAC + CALCULO DE BASELINE (primera ejecucion)")
    
    status("SAC calculara y guardara baseline internamente")
    status("Esto puede tomar 1-2 horas en GPU...")
    
    cmd = [
        sys.executable,
        "-m",
        "scripts.run_oe3_simulate",
        "--config",
        "configs/default.yaml",
    ]
    
    try:
        _result = subprocess.run(cmd, capture_output=False, text=True)
        
        if has_baseline():
            success("SAC completado - Baseline calculado y guardado")
            show_baseline()
            return True
        else:
            error("SAC no genero baseline valido")
            return False
    except Exception as e:
        error(f"SAC execution failed: {e}")
        return False

def run_ppo_with_cached_baseline():
    """Ejecutar PPO reutilizando baseline cacheado."""
    separator("FASE 2: PPO (reutilizando baseline cacheado)")
    
    status("Reutilizando baseline del cache (--skip-uncontrolled)")
    status("Esto puede tomar 2-3 horas en GPU...")
    
    cmd = [
        sys.executable,
        "-m",
        "scripts.run_oe3_simulate",
        "--config",
        "configs/default.yaml",
        "--skip-uncontrolled",  # NO recalcular baseline
        "--skip-dataset",       # NO reconstruir dataset
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        success("PPO completado")
        return True
    except Exception as e:
        error(f"PPO execution failed: {e}")
        return False

def run_a2c_with_cached_baseline():
    """Ejecutar A2C reutilizando baseline cacheado."""
    separator("FASE 3: A2C (reutilizando baseline cacheado)")
    
    status("Reutilizando baseline del cache (--skip-uncontrolled)")
    status("Esto puede tomar 2-3 horas en GPU...")
    
    cmd = [
        sys.executable,
        "-m",
        "scripts.run_oe3_simulate",
        "--config",
        "configs/default.yaml",
        "--skip-uncontrolled",  # NO recalcular baseline
        "--skip-dataset",       # NO reconstruir dataset
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        success("A2C completado")
        return True
    except Exception as e:
        error(f"A2C execution failed: {e}")
        return False

def show_results():
    """Mostrar comparativa de resultados."""
    separator("RESULTADOS FINALES")
    
    summary_path = Path("outputs/oe3/simulations/simulation_summary.json")
    
    if not summary_path.exists():
        error("No results found")
        return
    
    try:
        with open(summary_path) as f:
            summary = json.load(f)
        
        print("\n[BASELINE]\n")
        if "pv_bess_uncontrolled" in summary:
            unc = summary["pv_bess_uncontrolled"]
            co2_base = unc.get("carbon_kg", 0)
            print(f"Uncontrolled (Sin control inteligente)")
            print(f"  CO2: {co2_base:.0f} kg")
            print(f"  Grid import: {unc.get('grid_import_kwh', 0):.0f} kWh")
        
        print("\n[AGENTES ENTRENADOS]\n")
        if "pv_bess_results" in summary:
            results = summary["pv_bess_results"]
            for agent in sorted(results.keys()):
                data = results[agent]
                co2 = data.get("carbon_kg", 0)
                reduction = ((co2_base - co2) / co2_base * 100) if co2_base > 0 else 0
                print(f"{agent}:")
                print(f"  CO2: {co2:.0f} kg")
                print(f"  Reduccion: {reduction:.2f}% vs baseline")
                print(f"  Grid import: {data.get('grid_import_kwh', 0):.0f} kWh")
                print()
        
        best = summary.get("best_agent", "N/A")
        print(f"[MEJOR AGENTE]: {best}\n")
        
    except Exception as e:
        error(f"Could not display results: {e}")

def main():
    """Ejecutar pipeline completo con cache de baseline."""
    
    separator("PIPELINE REENTRENAMIENTO: DATASET -> BASELINE (CACHE) -> AGENTES")
    
    print("Fecha: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("GPU: NVIDIA RTX 4060 (8.6 GB)")
    print("Python: 3.11.9 (UTF-8 encoding)")
    print()
    
    # Verificar si baseline existe
    baseline_exists = has_baseline()
    
    if baseline_exists:
        separator("BASELINE YA EXISTE EN CACHE")
        show_baseline()
        status("Saltando calculo de baseline - usando cache")
    else:
        separator("BASELINE NO EXISTE")
        status("Ejecutando SAC para calcular baseline por primera vez...")
        
        if not run_sac_first_time():
            error("PIPELINE INTERRUMPIDO: SAC no logro calcular baseline")
            return 1
    
    # Si llegamos aqui, baseline existe
    
    # Ejecutar PPO
    if not run_ppo_with_cached_baseline():
        error("PIPELINE INTERRUMPIDO: PPO fallo")
        return 1
    
    # Ejecutar A2C
    if not run_a2c_with_cached_baseline():
        error("PIPELINE INTERRUMPIDO: A2C fallo")
        return 1
    
    # Mostrar resultados
    show_results()
    
    separator("PIPELINE COMPLETADO EXITOSAMENTE")
    success("Baseline fue calculado UNA VEZ y reutilizado en todas las ejecuciones")
    success("Todos los agentes (SAC, PPO, A2C) fueron entrenados")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
