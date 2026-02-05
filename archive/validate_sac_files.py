#!/usr/bin/env python3
"""
================================================================================
VALIDACION Y GENERACION DE ARCHIVOS TECNICOS SAC
================================================================================
Verifica que SAC genere correctamente:
- result_sac.json (métricas y CO2)
- timeseries_sac.csv (series temporal con energía y recompensas)
- trace_sac.csv (traza de observaciones y acciones)
================================================================================
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from iquitos_citylearn.config import load_config, load_paths
from iquitos_citylearn.oe3.simulate import simulate

def main():
    """Ejecutar simulacion SAC y validar generacion de archivos."""
    print()
    print("=" * 80)
    print("  VALIDACION Y GENERACION DE ARCHIVOS SAC")
    print("=" * 80)
    print()

    # Cargar configuracion
    config_path = Path(__file__).parent.parent / "configs" / "default.yaml"
    cfg = load_config(config_path)
    rp = load_paths(cfg)

    # Paths criticos
    schema_path = rp.processed_dir / "citylearn" / "iquitos_ev_mall" / "schema.json"
    out_dir = rp.oe3_simulations_dir

    if not schema_path.exists():
        print(f"[ERROR] Schema no existe: {schema_path}")
        print(f"[INFO] Ejecuta primero: python -m scripts.run_oe3_build_dataset")
        return False

    print(f"[CONFIG] Schema: {schema_path}")
    print(f"[CONFIG] Output: {out_dir}")
    print(f"[CONFIG] Checkpoints: {rp.checkpoints_dir}")
    print()

    # Ejecutar simulacion SAC (solo 1 episodio para validar rapidamente)
    print("[SIMULATE] Iniciando simulacion SAC (1 episodio = 8,760 pasos)...")
    print()

    try:
        result = simulate(
            schema_path=schema_path,
            agent_name="sac",
            out_dir=out_dir,
            training_dir=rp.checkpoints_dir,
            carbon_intensity_kg_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
            seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
            use_multi_objective=True,
            multi_objective_priority="co2_focus",
            include_solar=True,
            sac_episodes=1,  # Solo 1 episodio para validacion
            sac_batch_size=512,
            sac_learning_rate=5e-5,
            sac_checkpoint_freq_steps=1000,
            sac_log_interval=500,
            sac_device="cpu",  # Force CPU para evitar errores de GPU/matplotlib
        )
    except Exception as e:
        print(f"[ERROR] Simulacion falló: {type(e).__name__}: {e}")
        return False

    print()
    print("=" * 80)
    print("  VALIDACION DE ARCHIVOS GENERADOS")
    print("=" * 80)
    print()

    # Validar archivos generados
    files_to_check = [
        ("result_sac.json", out_dir / "result_sac.json"),
        ("timeseries_sac.csv", out_dir / "timeseries_sac.csv"),
        ("trace_sac.csv", out_dir / "trace_sac.csv"),
    ]

    all_ok = True
    for name, path in files_to_check:
        if path.exists():
            size_kb = path.stat().st_size / 1024
            print(f"  [OK] {name:<30} {size_kb:>10.1f} KB")

            # Validar contenido
            try:
                if name.endswith(".json"):
                    with open(path) as f:
                        data = json.load(f)
                        print(f"       Claves: {', '.join(list(data.keys())[:5])}{'...' if len(data) > 5 else ''}")
                elif name.endswith(".csv"):
                    with open(path) as f:
                        lines = f.readlines()
                        print(f"       Filas: {len(lines)}, Columnas: {len(lines[0].split(',')) if lines else 0}")
            except Exception as e:
                print(f"       [WARNING] Error leyendo archivo: {e}")
                all_ok = False
        else:
            print(f"  [MISSING] {name:<30}")
            all_ok = False

    print()
    print("=" * 80)
    print("  RESUMEN DE METRICAS")
    print("=" * 80)
    print()
    print(f"  Agente: {result.agent}")
    print(f"  Pasos: {result.steps:,}")
    print(f"  Anos: {result.simulated_years:.2f}")
    print()
    print(f"  ENERGIA (kWh):")
    print(f"    PV Generado: {result.pv_generation_kwh:>12,.0f}")
    print(f"    Grid Import: {result.grid_import_kwh:>12,.0f}")
    print(f"    EV Charging: {result.ev_charging_kwh:>12,.0f}")
    print()
    print(f"  CO2 (kg) - 3 COMPONENTES:")
    print(f"    Emitido Grid: {result.co2_emitido_grid_kg:>12,.0f}")
    print(f"    Reduccion Ind: {result.co2_reduccion_indirecta_kg:>12,.0f}")
    print(f"    Reduccion Dir: {result.co2_reduccion_directa_kg:>12,.0f}")
    print(f"    NETO: {result.co2_neto_kg:>12,.0f}")
    print()
    print(f"  MULTI-OBJETIVO:")
    print(f"    Priority: {result.multi_objective_priority}")
    print(f"    Reward Total: {result.reward_total_mean:>12.4f}")
    print()
    print("=" * 80)

    if all_ok:
        print("[SUCCESS] Todos los archivos generados correctamente!")
        return True
    else:
        print("[WARNING] Algunos archivos estan faltando - revisar logs")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
