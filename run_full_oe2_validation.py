#!/usr/bin/env python3
"""Validación COMPLETA de OE2 v5.5 + Actualización de agentes y configs"""

import sys
import json
from pathlib import Path

# Configurar path
sys.path.insert(0, str(Path.cwd()))

from src.dimensionamiento.oe2.disenocargadoresev.data_loader import (
    rebuild_oe2_datasets_complete,
    validate_oe2_complete
)

print('\n' + '='*120)
print('VALIDACION COMPLETA OE2 v5.5 - PREPARAR PARA ENTRENAMIENTO RL')
print('='*120 + '\n')

# Ejecutar validación completa
result = validate_oe2_complete(cleanup_interim=False)

print('\n' + '='*120)
print('RESUMEN DE VALIDACION')
print('='*120)

if result["is_valid"]:
    print('\n✅ OE2 v5.5 VALIDACIÓN EXITOSA\n')
    
    # Solar
    if result.get("solar"):
        print(f'☀️  SOLAR:')
        print(f'    • Capacidad: {result["solar"]["capacity_kwp"]:,.0f} kWp')
        print(f'    • Media: {result["solar"]["mean_kw"]:,.0f} kW')
        print(f'    • Máximo: {result["solar"]["max_kw"]:,.0f} kW')
        print(f'    • Timesteps: {result["solar"]["timesteps"]} horas')
    
    # BESS
    if result.get("bess"):
        print(f'\n🔋 BESS v5.5:')
        print(f'    • Capacidad: {result["bess"]["capacity_kwh"]:,.0f} kWh')
        print(f'    • Potencia: {result["bess"]["power_kw"]} kW (actualizado)')
        print(f'    • Eficiencia: {result["bess"]["efficiency"]*100:.0f}%')
        print(f'    • Timesteps: {result["bess"]["timesteps"]} horas')
    
    # Chargers
    if result.get("chargers"):
        print(f'\n⚡ CHARGERS:')
        print(f'    • Unidades: {result["chargers"]["total_units"]} cargadores')
        print(f'    • Sockets: {result["chargers"]["total_sockets"]} totales (2 c/u)')
        print(f'    • Motos: {result["chargers"]["motos"]} × 2 = {result["chargers"]["motos"]*2} sockets')
        print(f'    • Mototaxis: {result["chargers"]["mototaxis"]} × 2 = {result["chargers"]["mototaxis"]*2} sockets')
        print(f'    • Timesteps: {result["chargers"]["timesteps"]} horas')
    
    # Mall Demand
    if result.get("mall_demand"):
        print(f'\n🏢 MALL DEMAND:')
        print(f'    • Media: {result["mall_demand"]["mean_kw"]:,.0f} kW')
        print(f'    • Máximo: {result["mall_demand"]["max_kw"]:,.0f} kW')
        print(f'    • Mínimo: {result["mall_demand"]["min_kw"]:,.0f} kW')
        print(f'    • Timesteps: {result["mall_demand"]["timesteps"]} horas')
    
    print(f'\n✅ ESTADO: LISTO PARA ENTRENAMIENTO RL (SAC/PPO/A2C)\n')
    
    # Guardar resultado de validación
    validation_report = {
        "timestamp": "2026-02-13",
        "oe2_version": "v5.5",
        "is_valid": result["is_valid"],
        "solar": result.get("solar"),
        "bess": result.get("bess"),
        "chargers": result.get("chargers"),
        "mall_demand": result.get("mall_demand"),
        "errors": result.get("errors", []),
        "notes": result.get("notes", [])
    }
    
    report_path = Path("reports/oe2/validation_oe2_v55_complete.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump(validation_report, f, indent=2)
    
    print(f'📊 Reporte guardado: {report_path}\n')
    
else:
    print('\n❌ VALIDACION FALLIDA\n')
    print('Errores:')
    for err in result.get("errors", []):
        print(f'  - {err}')
    sys.exit(1)

print('='*120 + '\n')
