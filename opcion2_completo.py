#!/usr/bin/env python3
"""
OPCION 2 SIMPLIFICADA: Modificar bess.py + Regenerar TODO automáticamente

PASO 1: Editar bess.py línea 197
================
Archivo: src/dimensionamiento/oe2/disenobess/bess.py (línea 197)

Cambiar:
    BESS_SOC_MIN_V53 = 0.20          # Valor actual

A:
    BESS_SOC_MIN_V53 = 0.15          # Valor nuevo (ejemplo: 15% en lugar de 20%)

PASO 2: Ejecutar ESTE script (una sola vez)
================
$ python opcion2_completo.py

¡Listo! Automáticamente:
  1. Lee bess.py y detecta el nuevo SOC_MIN
  2. Regenera dataset transformado
  3. Regenera gráficos
  4. Valida integridad
  5. Muestra resumen de cambios
"""

import subprocess
import sys
from pathlib import Path
import re

def read_bess_param(param_name):
    """Leer parámetro actual de bess.py"""
    bess_file = Path('src/dimensionamiento/oe2/disenobess/bess.py')
    
    with open(bess_file) as f:
        content = f.read()
    
    # Buscar patrón: BESS_SOC_MIN_V53 = 0.20
    pattern = f'{param_name}\\s*=\\s*([0-9.]+)'
    match = re.search(pattern, content)
    
    if match:
        return float(match.group(1))
    return None

def run_step(cmd, step_name):
    """Ejecutar paso y reportar"""
    print(f"\n{'▶'*40}")
    print(f"  {step_name}")
    print(f"{'▶'*40}")
    
    result = subprocess.run(cmd, shell=True)
    return result.returncode == 0

def main():
    print("\n" + "="*80)
    print(" OPCION 2 COMPLETO: Editar bess.py + Regenerar TODO")
    print("="*80)
    
    # Paso 0: Detectar parámetros actuales
    print("\n📖 Leyendo parámetros de bess.py...")
    soc_min = read_bess_param('BESS_SOC_MIN_V53')
    capacity = read_bess_param('BESS_CAPACITY_KWH_V53')
    power = read_bess_param('BESS_POWER_KW_V53')
    dod = read_bess_param('BESS_DOD_V53')
    
    if soc_min:
        print(f"   ✓ BESS_SOC_MIN_V53 = {soc_min*100:.0f}%")
    if capacity:
        print(f"   ✓ BESS_CAPACITY_KWH_V53 = {capacity:.0f} kWh")
    if power:
        print(f"   ✓ BESS_POWER_KW_V53 = {power:.0f} kW")
    if dod:
        print(f"   ✓ BESS_DOD_V53 = {dod*100:.0f}%")
    
    # Paso 1: Regenerar dataset
    success = True
    if not run_step(
        "python scripts/transform_dataset_v57.py",
        "PASO 1: Transformar dataset (leyendo bess.py modificado)"
    ):
        success = False
    
    # Paso 2: Regenerar gráficos
    if not run_step(
        "python scripts/regenerate_graphics_v57.py",
        "PASO 2: Regenerar gráficos"
    ):
        success = False
    
    # Paso 3: Validar
    if not run_step(
        "python verify_soc_min.py",
        "PASO 3: Validar integridad"
    ):
        success = False
    
    # Resumen
    print("\n" + "="*80)
    if success:
        print("✅ OPCION 2 COMPLETADA: Todo regenerado automáticamente")
        print("="*80)
        print(f"\n📊 Cambios aplicados:")
        print(f"   • SOC mínimo BESS: {soc_min*100:.0f}%")
        print(f"   • Capacidad: {capacity:.0f} kWh")
        print(f"   • Archivos regenerados:")
        print(f"     - data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv")
        print(f"     - reports/balance_energetico/ (15 gráficos PNG)")
        print(f"\n✨ Listo para usar")
        return 0
    else:
        print("❌ Error en regeneración")
        print("="*80)
        return 1

if __name__ == '__main__':
    sys.exit(main())
