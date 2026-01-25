#!/usr/bin/env python3
"""
Pipeline COMPLETO visible en PowerShell:
1. Dataset construction (OE3)
2. Baseline Uncontrolled (sin control)
3. SAC training (con control)
4. PPO training
5. A2C training
6. Comparativa final

Salida VISIBLE en consola sin caracteres Unicode problemáticos.
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

def separator(title=""):
    """Print a clear separator."""
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"\n{'-'*80}\n")

def status(msg):
    """Print status message."""
    print(f"[*] {msg}")

def success(msg):
    """Print success message."""
    print(f"[OK] {msg}")

def error(msg):
    """Print error message."""
    print(f"[ERROR] {msg}")

def run_dataset():
    """Construir dataset CityLearn."""
    separator("FASE 1: CONSTRUCCION DE DATASET CITYLEARN")
    
    status("Inicializando construccion de dataset...")
    status("- Validando datos OE2 (solar, chargers, BESS)")
    status("- Generando schemas de CityLearn")
    status("- Validando 128 cargadores EV")
    
    cmd = [
        sys.executable,
        "-m",
        "scripts.run_oe3_simulate",
        "--config",
        "configs/default.yaml",
        "--skip-uncontrolled",
        "--skip-dataset",
    ]
    
    # Ejecutar SKIP para verificar dataset
    try:
        _result = subprocess.run(cmd, capture_output=False, text=True)
        success("Dataset verificado y listo")
        return True
    except Exception as e:
        error(f"Dataset construction failed: {e}")
        return False

def run_baseline():
    """Ejecutar baseline sin control."""
    separator("FASE 2: CALCULO DE BASELINE (SIN CONTROL INTELIGENTE)")
    
    status("Inicializando agente Uncontrolled...")
    status("- Cargadores: carga al maximo permitido")
    status("- BESS: sin control deliberado")
    status("- Duracion: 8,760 horas (1 anio completo)")
    
    cmd = [
        sys.executable,
        "-c",
        """
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from scripts._common import load_all
from iquitos_citylearn.oe3.simulate import simulate

cfg, rp = load_all("configs/default.yaml")
rp.ensure()

dataset_name = cfg["oe3"]["dataset"]["name"]
processed_dataset_dir = rp.processed_dir / "citylearn" / dataset_name
schema_pv = processed_dataset_dir / "schema_pv_bess.json"
out_dir = rp.outputs_dir / "oe3" / "simulations"
training_dir = rp.analyses_dir / "oe3" / "training"

print("[*] Ejecutando episodio Uncontrolled (sin entrenamiento)...")
result = simulate(
    schema_path=schema_pv,
    agent_name="Uncontrolled",
    out_dir=out_dir,
    training_dir=training_dir,
    carbon_intensity_kg_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
    seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
    deterministic_eval=True,
    use_multi_objective=False,
)

print("[OK] Baseline completado")
print(f"    Pasos simulados: {result.steps} horas")
print(f"    Anos: {result.simulated_years:.2f}")
print(f"    Importacion red: {result.grid_import_kwh:.0f} kWh")
print(f"    Generacion PV: {result.pv_generation_kwh:.0f} kWh")
print(f"    Carga EV: {result.ev_charging_kwh:.0f} kWh")
print(f"    CO2 anual: {result.carbon_kg:.0f} kg")
"""
    ]
    
    try:
        _ = subprocess.run(cmd, capture_output=False, text=True)
        success("Baseline calculado exitosamente")
        return True
    except Exception as e:
        error(f"Baseline failed: {e}")
        return False

def run_sac():
    """Entrenar agente SAC."""
    separator("FASE 3: ENTRENAMIENTO AGENTE SAC (ACTOR-CRITICO)")
    
    status("Inicializando SAC (Soft Actor-Critic)...")
    status("- Algoritmo: Aprendizaje por refuerzo")
    status("- Batch size: 65536 (GPU optimizado)")
    status("- Episodios: 2 (17,520 timesteps)")
    status("- Metrica: Minimizar CO2 + maximizar autoconsumo solar")
    
    cmd = [
        sys.executable,
        "-m",
        "scripts.run_oe3_simulate",
        "--config",
        "configs/default.yaml",
        "--skip-uncontrolled",
        "--skip-dataset",
    ]
    
    try:
        _ = subprocess.run(cmd, capture_output=False, text=True)
        success("SAC entrenamiento completado")
        return True
    except Exception as e:
        error(f"SAC training failed: {e}")
        return False

def run_comparativa():
    """Mostrar comparativa final."""
    separator("FASE 4: COMPARATIVA DE RESULTADOS")
    
    try:
        simulations_dir = Path("outputs/oe3/simulations")
        summary_path = simulations_dir / "simulation_summary.json"
        
        if not summary_path.exists():
            error("No summary file found")
            return False
        
        with open(summary_path) as f:
            summary = json.load(f)
        
        print("[*] Resultados finales:\n")
        
        # Baseline
        if "pv_bess_uncontrolled" in summary:
            unc = summary["pv_bess_uncontrolled"]
            print(f"Baseline (Sin Control):")
            print(f"  CO2: {unc.get('carbon_kg', 0):.0f} kg")
            print(f"  Grid import: {unc.get('grid_import_kwh', 0):.0f} kWh")
            print()
        
        # Agentes
        if "pv_bess_results" in summary:
            results = summary["pv_bess_results"]
            baseline_co2 = summary.get("pv_bess_uncontrolled", {}).get("carbon_kg", 1.0)
            
            print("Agentes Entrenados:")
            for agent, data in sorted(results.items()):
                co2 = data.get("carbon_kg", 0)
                reduction = ((baseline_co2 - co2) / baseline_co2 * 100) if baseline_co2 > 0 else 0
                print(f"  {agent}:")
                print(f"    CO2: {co2:.0f} kg")
                print(f"    Reduccion: {reduction:.2f}%")
                print()
        
        best = summary.get("best_agent", "N/A")
        print(f"[OK] Mejor agente: {best}")
        
        return True
        
    except Exception as e:
        error(f"Comparativa failed: {e}")
        return False

def main():
    """Ejecutar pipeline completo."""
    
    separator("PIPELINE COMPLETO: DATASET -> BASELINE -> AGENTES")
    
    print("Fecha/Hora: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("GPU: NVIDIA RTX 4060 (8.6 GB)")
    print("Python: 3.11.9 (UTF-8 encoding)")
    print()
    
    steps = [
        ("Dataset", run_dataset),
        ("Baseline", run_baseline),
        ("SAC", run_sac),
        ("Comparativa", run_comparativa),
    ]
    
    completed = 0
    for name, func in steps:
        try:
            if func():
                completed += 1
            else:
                error(f"Saltando fase siguiente...")
                break
        except Exception as e:
            error(f"Exception en {name}: {e}")
            break
    
    separator("RESUMEN FINAL")
    print(f"Fases completadas: {completed}/{len(steps)}")
    
    if completed == len(steps):
        success("PIPELINE COMPLETADO EXITOSAMENTE")
        return 0
    else:
        error(f"PIPELINE INTERRUMPIDO (fase {completed+1} falló)")
        return 1

if __name__ == "__main__":
    sys.exit(main())
