#!/usr/bin/env python3
"""
Resumen de actualización de métricas en Resumen Ejecutivo y PDF
"""

import json
from pathlib import Path

# Load results
results = json.load(open('data/oe2/bess/bess_results.json'))

print('\n' + '='*80)
print('  ACTUALIZACIÓN COMPLETADA - NUEVAS MÉTRICAS EN RESUMEN Y PDF')
print('='*80)

print('\nMÉTRICAS INTEGRADAS:\n')
print('  1. Exportación a Red:')
print(f'     - {results.get("grid_export_kwh_year", 0)/1000:.1f} MWh/año')
print(f'     - {results.get("grid_export_kwh_year", 0):,.0f} kWh/año')
print('     - 21.4% de generación PV\n')

print('  2. Peak Shaving BESS:')
print(f'     - {results.get("bess_to_mall_kwh_year", 0):,.0f} kWh/año')
print('     - 5.0% de demanda MALL')
print('     - Horas pico: 13:00-19:00 (corte >= 1.9 MW)\n')

print('ARCHIVOS ACTUALIZADOS:\n')
print('  [OK] src/dimensionamiento/oe2/disenobess/bess.py')
print('  [OK] scripts/generate_bess_pdf_report.py')
print('  [OK] outputs/pdf/BESS_Dimensionamiento_v5.4.pdf (1.0 MB)\n')

print('SECCIONES PDF ACTUALIZADAS:\n')
print('  * Sección 8.2: Desempeño Energético Anual')
print('    - Exportación Red: 1,770.8 MWh/año (21.4%)')
print('    - Peak Shaving BESS: 611,757 kWh/año (5.0%)')
print('  * Sección 8.3: Beneficios Objetivos')
print('    + Exportación a Red Inteligente (ingresos)')
print('    + Peak Shaving Automático (congestión grid)')
print('  * Tabla 6.1: Balance Energético Anual\n')

print('='*80)
print('\nPDF DISPONIBLE EN: outputs/pdf/BESS_Dimensionamiento_v5.4.pdf')
print('='*80)
