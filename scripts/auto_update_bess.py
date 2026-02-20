"""
SCRIPT AUTOMATICO: Regenerar dataset y graficos cuando cambien parametros BESS

Uso:
    python scripts/auto_update_bess.py

Este script integra AUTOMATICAMENTE:
  1. Detectar cambios en bess.py
  2. Regenerar dataset transformado
  3. Regenerar graficos
  4. Validar que todo esté correcto
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Ejecutar comando y reportar resultado"""
    print(f"\n{'='*80}")
    print(f"  {description}")
    print(f"{'='*80}")
    
    result = subprocess.run(cmd, shell=True, cwd=str(Path(__file__).parent.parent))
    
    if result.returncode != 0:
        print(f"\n❌ ERROR: {description} falló")
        return False
    
    print(f"\n✅ OK: {description}")
    return True

def main():
    print("\n" + "="*80)
    print("AUTO-UPDATE BESS: Regeneración automática de dataset y gráficos")
    print("="*80)
    
    all_success = True
    
    # PASO 1: Regenerar dataset transformado
    if not run_command(
        "python scripts/transform_dataset_v57.py",
        "PASO 1/3: Transformando dataset desde bess_ano_2024.csv"
    ):
        all_success = False
    
    # PASO 2: Regenerar gráficos
    if not run_command(
        "python scripts/regenerate_graphics_v57.py",
        "PASO 2/3: Regenerando gráficos de balance energético"
    ):
        all_success = False
    
    # PASO 3: Validar integridad
    if not run_command(
        "python verify_soc_min.py",
        "PASO 3/3: Validando integridad de SOC"
    ):
        all_success = False
    
    # RESUMEN FINAL
    print("\n" + "="*80)
    if all_success:
        print("✅ AUTO-UPDATE COMPLETADO EXITOSAMENTE")
        print("="*80)
        print("\n📂 Archivos actualizados:")
        print("  • data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv")
        print("  • reports/balance_energetico/*.png (15 gráficos)")
        print("\n🎯 Listos para usar en análisis o training de agentes")
        return 0
    else:
        print("❌ AUTO-UPDATE FALLÓ EN ALGUNOS PASOS")
        print("="*80)
        print("\nVerifica los errores anteriores y reintenta")
        return 1

if __name__ == '__main__':
    sys.exit(main())
