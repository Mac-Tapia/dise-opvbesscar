#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PIPELINE COMPLETO: Dataset -> Baseline -> Agentes SAC/PPO/A2C
Sin caracteres Unicode para PowerShell (encoding cp1252)
"""

import sys
import os
from pathlib import Path

# ASCII ONLY - Sin emojis ni caracteres especiales
def print_header(text):
    print("\n" + "="*80)
    print(text)
    print("="*80)

def print_section(text):
    print("\n>>> " + text)

def print_success(text):
    print("[OK] " + text)

def print_error(text):
    print("[ERROR] " + text)

def main():
    PROJECT_ROOT = Path(__file__).parent
    sys.path.insert(0, str(PROJECT_ROOT))
    
    # Activar UTF-8 con fallback gracioso en PowerShell
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    print_header("PIPELINE COMPLETO IQUITOS EV SMART CHARGING")
    print("Fecha: 18 Enero 2026")
    print("GPU: NVIDIA RTX 4060 (8GB VRAM)")
    
    try:
        from scripts._common import load_all
        print_success("Modulos importados correctamente")
    except Exception as e:
        print_error(f"No se pueden importar modulos: {e}")
        return False
    
    # ============================================================================
    # FASE 0: Cargar configuracion
    # ============================================================================
    print_section("FASE 0: Cargando configuracion")
    
    try:
        cfg, rp = load_all("configs/default.yaml")
        rp.ensure()
        print_success("Configuracion cargada desde configs/default.yaml")
        
        # Mostrar parametros clave
        print(f"  - Device: {cfg['oe3']['evaluation']['sac'].get('device', 'auto')}")
        print(f"  - Batch size SAC: {cfg['oe3']['evaluation']['sac'].get('batch_size', 512)}")
        print(f"  - Episodes: {cfg['oe3']['evaluation']['sac'].get('episodes', 5)}")
        print(f"  - Carbon intensity: {cfg['oe3']['grid']['carbon_intensity_kg_per_kwh']} kg/kWh")
    except Exception as e:
        print_error(f"Error cargando configuracion: {e}")
        return False
    
    # ============================================================================
    # FASE 1: Dataset
    # ============================================================================
    print_section("FASE 1: Construccion de Dataset CityLearn")
    
    dataset_name = cfg["oe3"]["dataset"]["name"]
    processed_dataset_dir = rp.processed_dir / "citylearn" / dataset_name
    
    if processed_dataset_dir.exists():
        print_success(f"Dataset ya existe en {processed_dataset_dir}")
    else:
        try:
            from iquitos_citylearn.oe3.dataset_builder import build_citylearn_dataset
            
            print("  Construyendo dataset...")
            built = build_citylearn_dataset(
                cfg=cfg,
                raw_dir=rp.raw_dir,
                interim_dir=rp.interim_dir,
                processed_dir=rp.processed_dir,
            )
            print_success(f"Dataset construido: {built.dataset_dir}")
        except Exception as e:
            print_error(f"Error construyendo dataset: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ============================================================================
    # FASE 2: Baseline Uncontrolled
    # ============================================================================
    print_section("FASE 2: Simulacion Baseline (sin control)")
    
    schema_pv = processed_dataset_dir / "schema_pv_bess.json"
    out_dir = rp.outputs_dir / "oe3" / "simulations"
    training_dir = rp.analyses_dir / "oe3" / "training"
    
    try:
        from iquitos_citylearn.oe3.simulate import simulate
        
        print("  Ejecutando agente Uncontrolled...")
        result_unc = simulate(
            schema_path=schema_pv,
            agent_name="Uncontrolled",
            out_dir=out_dir,
            training_dir=training_dir,
            carbon_intensity_kg_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
            seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
            deterministic_eval=True,
            use_multi_objective=False,
        )
        
        print_success("Baseline Uncontrolled completado")
        print(f"  - Pasos: {result_unc.steps}")
        print(f"  - Anos simulados: {result_unc.simulated_years:.4f}")
        print(f"  - CO2 Total: {result_unc.carbon_kg:,.2f} kg")
        print(f"  - Grid import: {result_unc.grid_import_kwh:,.2f} kWh")
        print(f"  - EV charging: {result_unc.ev_charging_kwh:,.2f} kWh")
        
    except Exception as e:
        print_error(f"Error en baseline: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ============================================================================
    # FASE 3: Agentes SAC, PPO, A2C
    # ============================================================================
    print_section("FASE 3: Entrenamiento de Agentes RL")
    
    agents = ["SAC", "PPO", "A2C"]
    results = {}
    
    for agent_name in agents:
        print_section(f"  Entrenando {agent_name}...")
        
        try:
            cfg_oe3 = cfg["oe3"]["evaluation"]
            
            if agent_name == "SAC":
                sac_cfg = cfg_oe3.get("sac", {})
                sac_episodes = int(sac_cfg.get("episodes", 5))
                sac_batch_size = int(sac_cfg.get("batch_size", 512))
                
                print(f"    Configuracion:")
                print(f"      - Episodes: {sac_episodes}")
                print(f"      - Batch size: {sac_batch_size}")
                print(f"      - Device: {sac_cfg.get('device', 'auto')}")
                
                res = simulate(
                    schema_path=schema_pv,
                    agent_name="SAC",
                    out_dir=out_dir,
                    training_dir=training_dir,
                    carbon_intensity_kg_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
                    seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
                    sac_episodes=sac_episodes,
                    sac_batch_size=sac_batch_size,
                    deterministic_eval=True,
                    use_multi_objective=True,
                    multi_objective_priority="balanced",
                )
                
            elif agent_name == "PPO":
                ppo_cfg = cfg_oe3.get("ppo", {})
                ppo_timesteps = int(ppo_cfg.get("timesteps", 43800))
                
                print(f"    Configuracion:")
                print(f"      - Timesteps: {ppo_timesteps}")
                print(f"      - Device: {ppo_cfg.get('device', 'auto')}")
                
                res = simulate(
                    schema_path=schema_pv,
                    agent_name="PPO",
                    out_dir=out_dir,
                    training_dir=training_dir,
                    carbon_intensity_kg_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
                    seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
                    ppo_timesteps=ppo_timesteps,
                    deterministic_eval=True,
                    use_multi_objective=True,
                )
                
            elif agent_name == "A2C":
                a2c_cfg = cfg_oe3.get("a2c", {})
                a2c_timesteps = int(a2c_cfg.get("timesteps", 43800))
                
                print(f"    Configuracion:")
                print(f"      - Timesteps: {a2c_timesteps}")
                print(f"      - Device: {a2c_cfg.get('device', 'auto')}")
                
                res = simulate(
                    schema_path=schema_pv,
                    agent_name="A2C",
                    out_dir=out_dir,
                    training_dir=training_dir,
                    carbon_intensity_kg_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
                    seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
                    a2c_timesteps=a2c_timesteps,
                    deterministic_eval=True,
                    use_multi_objective=True,
                )
            
            results[agent_name] = res
            print_success(f"{agent_name} completado")
            print(f"    - CO2: {res.carbon_kg:,.2f} kg")
            print(f"    - Anos: {res.simulated_years:.4f}")
            print(f"    - Grid import: {res.grid_import_kwh:,.2f} kWh")
            
        except Exception as e:
            print_error(f"Error en {agent_name}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # ============================================================================
    # FASE 4: Comparativa
    # ============================================================================
    print_section("FASE 4: Comparativa de Resultados")
    
    try:
        baseline_co2 = result_unc.carbon_kg
        
        print(f"\nRESULTADOS (CO2 en kg):")
        print(f"  Baseline (sin control): {baseline_co2:>15,.2f} kg")
        
        for agent_name, result in results.items():
            reduction_kg = baseline_co2 - result.carbon_kg
            reduction_pct = (reduction_kg / baseline_co2 * 100) if baseline_co2 > 0 else 0
            
            print(f"  {agent_name:<20}: {result.carbon_kg:>15,.2f} kg  (Reduccion: {reduction_pct:>6.2f}%)")
        
        # Guardar resumen
        summary_file = out_dir / "RESUMEN_RESULTADOS.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("RESUMEN DE RESULTADOS - IQUITOS EV SMART CHARGING\n")
            f.write("="*80 + "\n\n")
            f.write(f"Baseline (sin control): {baseline_co2:,.2f} kg CO2\n\n")
            for agent_name, result in results.items():
                reduction = baseline_co2 - result.carbon_kg
                reduction_pct = (reduction / baseline_co2 * 100) if baseline_co2 > 0 else 0
                f.write(f"{agent_name}: {result.carbon_kg:,.2f} kg CO2 (Reduccion {reduction_pct:.2f}%)\n")
        
        print_success(f"Resumen guardado en {summary_file}")
        
    except Exception as e:
        print_error(f"Error en comparativa: {e}")
    
    print_header("PIPELINE COMPLETADO EXITOSAMENTE")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
