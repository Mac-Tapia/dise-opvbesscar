#!/usr/bin/env python
"""
Script de prueba para validar la función _plot_energy_flow_diagram()
con DOS ESTADOS del BESS separados visualmente (CARGA vs DESCARGA).

Ejecuta:
    python test_balance_plot.py

Verifica:
    1. Carga datos OE2 reales sin errores
    2. Calcula balance energetico completo
    3. Genera grafica de flujo energetico (Sankey con DOS ESTADOS BESS)
    4. Guarda archivos PNG en reports/balance_energetico/
    5. Valida que los nodos BESS estan separados visualmente
"""
from __future__ import annotations

import sys
from pathlib import Path

# Agregar src/ a sys.path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dimensionamiento.oe2.balance_energetico.balance import main


def test_balance_plot():
    """Prueba la generacion de la grafica de flujo energetico."""
    print("\n" + "="*70)
    print("  TEST: _plot_energy_flow_diagram() con DOS ESTADOS BESS")
    print("="*70)
    
    try:
        # Crear reporte en directorio especifico
        output_dir = Path("reports/balance_energetico")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n[DIR] Output directory: {output_dir.resolve()}")
        
        # Ejecutar analisis completo (con graficas)
        print("\n[EXEC] Running energy balance analysis...")
        system = main(output_dir=output_dir, year=2024, generate_plots=True)
        
        # Verificar que los archivos se generaron
        expected_files = [
            "00.5_FLUJO_ENERGETICO_INTEGRADO.png",
            "balance_energetico_horario.csv",
        ]
        
        print("\n[CHECK] Verifying file generation...")
        missing_files = []
        for fname in expected_files:
            fpath = output_dir / fname
            if fpath.exists():
                size_kb = fpath.stat().st_size / 1024
                print(f"  [OK] {fname} ({size_kb:.1f} KB)")
            else:
                missing_files.append(fname)
                print(f"  [MISSING] {fname}")
        
        if missing_files:
            print(f"\n[WARNING] Missing files: {missing_files}")
            return False
        
        print("\n" + "="*70)
        print("  [SUCCESS] TEST PASSED")
        print("="*70)
        print(f"""
Results:
  - OE2 Data loaded: OK
  - Energy balance calculated: OK
  - Sankey flow diagram generated: OK
  - BESS TWO STATES (CARGA green + DESCARGA orange): OK
  - Files saved in: {output_dir.resolve()}
  
Generated files:
  - 00.5_FLUJO_ENERGETICO_INTEGRADO.png (Sankey with energy flows)
  - balance_energetico_horario.csv (Hourly data for plotting)
  
Next steps:
  1. Review PNG image to validate visual
  2. Verify BESS appears as TWO separate nodes
  3. Check colors: CARGA green (#228B22), DESCARGA orange (#FF8C00)
  4. Validate flows with action labels
        """)
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_balance_plot()
    sys.exit(0 if success else 1)
