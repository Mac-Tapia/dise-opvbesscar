#!/usr/bin/env python3
"""
Test que el baseline se calcula correctamente.
"""

import sys
from pathlib import Path
import json

# Agregar raíz al path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts._common import load_all
from iquitos_citylearn.oe3.simulate import simulate

def test_baseline_calculation():
    """Test que el baseline uncontrolled se calcula sin errores."""
    
    print("\n" + "="*80)
    print("TEST: Cálculo de Baseline Uncontrolled")
    print("="*80)
    
    # Cargar config
    cfg, rp = load_all("configs/default.yaml")
    rp.ensure()
    
    dataset_name = cfg["oe3"]["dataset"]["name"]
    processed_dataset_dir = rp.processed_dir / "citylearn" / dataset_name
    
    if not processed_dataset_dir.exists():
        print(f"\n✗ Dataset no encontrado: {processed_dataset_dir}")
        print("Primero ejecuta: python -m scripts.run_oe3_simulate")
        return False
    
    schema_pv = processed_dataset_dir / "schema_pv_bess.json"
    if not schema_pv.exists():
        print(f"\n✗ Schema no encontrado: {schema_pv}")
        return False
    
    out_dir = rp.outputs_dir / "oe3" / "simulations"
    training_dir = rp.analyses_dir / "oe3" / "training"
    
    print(f"\n[1] Ejecutando baseline Uncontrolled...")
    print(f"    Schema: {schema_pv}")
    print(f"    Output: {out_dir}")
    
    try:
        # Ejecutar baseline
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
        
        print(f"\n✓ Baseline completado exitosamente")
        print(f"\n  Métricas:")
        print(f"    Pasos: {result.steps}")
        print(f"    Años simulados: {result.simulated_years:.2f}")
        print(f"    Importación red: {result.grid_import_kwh:.2f} kWh")
        print(f"    Exportación red: {result.grid_export_kwh:.2f} kWh")
        print(f"    Carga EV: {result.ev_charging_kwh:.2f} kWh")
        print(f"    Generación PV: {result.pv_generation_kwh:.2f} kWh")
        print(f"    CO₂ Total: {result.carbon_kg:.2f} kg")
        
        # Validar que los números tenga sentido
        if result.steps == 0:
            print(f"\n✗ ERROR: steps = 0 (episode failed)")
            return False
        
        if result.carbon_kg <= 0:
            print(f"\n⚠  ADVERTENCIA: carbon_kg = {result.carbon_kg} (debería ser > 0)")
        
        if result.ev_charging_kwh == 0:
            print(f"\n⚠  ADVERTENCIA: EV charging = 0 (debería ser > 0)")
        
        # Verificar archivo de salida
        results_json = out_dir / "uncontrolled_results.json"
        if results_json.exists():
            with open(results_json) as f:
                stored = json.load(f)
            print(f"\n✓ Archivo guardado: {results_json}")
            print(f"  CO₂ (from file): {stored.get('carbon_kg', 'N/A')} kg")
        
        # Verificar timeseries
        ts_csv = out_dir / "timeseries_uncontrolled.csv"
        if ts_csv.exists():
            print(f"✓ Timeseries guardado: {ts_csv}")
        
        print("\n" + "="*80)
        print("✓ TEST PASADO: Baseline se calcula correctamente")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR durante baseline:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_baseline_calculation()
    sys.exit(0 if success else 1)
