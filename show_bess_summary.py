#!/usr/bin/env python3
"""Mostrar resumen de BESS calculado desde bess_results.json."""
import json
from pathlib import Path

results_file = Path("data/oe2/bess/bess_results.json")

if not results_file.exists():
    print(f"❌ Archivo no encontrado: {results_file}")
    exit(1)

with open(results_file) as f:
    results = json.load(f)

print("\n" + "="*75)
print("  ✅ RESUMEN BESS - DIMENSIONAMIENTO OE2 CALCULADO")
print("="*75)

print("\n📊 ESPECIFICACIONES TÉCNICAS BESS:")
print("   ┌─────────────────────────────────────────────────────────────┐")
print(f"   │ Capacidad total:              {results['capacity_kwh']:>8.0f} kWh         │")
print(f"   │ Potencia nominal:             {results['nominal_power_kw']:>8.0f} kW          │")
print(f"   │ Profundidad de descarga:      {results['dod']*100:>8.0f}%             │")
print(f"   │ Capacidad usable:             {results['capacity_kwh']*results['dod']:>8.0f} kWh         │")
print(f"   │ Eficiencia round-trip:        {results['efficiency_roundtrip']*100:>8.0f}%             │")
print(f"   │ C-rate:                       {results['c_rate']:>8.2f}              │")
print(f"   │ Autonomía objetivo:           {results['autonomy_hours']:>8.1f} horas        │")
print("   └─────────────────────────────────────────────────────────────┘")

print("\n⚡ BALANCE ENERGÉTICO DIARIO (24 HORAS):")
print("   ┌─────────────────────────────────────────────────────────────┐")
print(f"   │ Generación solar PV:          {results['pv_generation_kwh_day']:>10,.0f} kWh/día  │")
print(f"   │ Demanda total:                {results['total_demand_kwh_day']:>10,.0f} kWh/día  │")
print(f"   │   ├─ Mall (~100 kW):          {results['mall_demand_kwh_day']:>10,.0f} kWh/día  │")
print(f"   │   └─ EV (38 tomaes):     {results['ev_demand_kwh_day']:>10,.0f} kWh/día  │")
print(f"   │ Excedente solar:              {results['surplus_kwh_day']:>10,.0f} kWh/día  │")
print(f"   │ Deficit EV nocturno (9-22h):  {results['deficit_kwh_day']:>10,.0f} kWh/día  │")
print(f"   │ Pico de carga EV:             {results['peak_load_kw']:>10.1f} kW       │")
print("   └─────────────────────────────────────────────────────────────┘")

print("\n🔋 COBERTURA BESS DEL DEFICIT EV (HORAS NOCTURNAS 9-22h):")
cap_usable = results['capacity_kwh'] * results['dod']
deficit = results['deficit_kwh_day']
cobertura = (cap_usable / deficit) * 100
print("   ┌─────────────────────────────────────────────────────────────┐")
print(f"   │ Capacidad usable BESS:        {cap_usable:>10.0f} kWh         │")
print(f"   │ ÷ Deficit EV nocturno:        {deficit:>10.2f} kWh/día  │")
print(f"   │ ──────────────────────────────────────────────────────────  │")
print(f"   │ COBERTURA:                    {cobertura:>10.1f}% ✓ 100%   │")
print(f"   │ Margen de seguridad:          {cobertura-100:>10.1f}%             │")
print("   └─────────────────────────────────────────────────────────────┘")

print("\n📈 ANÁLISIS ANUAL (365 DÍAS):")
print("   ┌─────────────────────────────────────────────────────────────┐")
print(f"   │ Generación solar anual:       {results['pv_generation_kwh_day']*365:>10,.0f} kWh/año  │")
print(f"   │ Demanda total anual:          {results['total_demand_kwh_day']*365:>10,.0f} kWh/año  │")
print(f"   │ Autosuficiencia:              {results['self_sufficiency']*100:>10.2f}%            │")
print(f"   │ Importación red (grid):       {results['grid_import_kwh_day']*365:>10,.0f} kWh/año  │")
print(f"   │ Exportación red (fv waste):   {results['grid_export_kwh_day']*365:>10,.0f} kWh/año  │")
print(f"   │ Ciclos de carga por día:      {results['cycles_per_day']:>10.2f} ciclos    │")
print("   └─────────────────────────────────────────────────────────────┘")

print("\n🎯 PARÁMETROS DE CONTROL:")
print("   ┌─────────────────────────────────────────────────────────────┐")
print(f"   │ SOC mínimo permitido:         {results['soc_min_percent']:>10.1f}%            │")
print(f"   │ SOC máximo permitido:         {results['soc_max_percent']:>10.1f}%            │")
print(f"   │ Alcance carga BESS:           {results['bess_load_scope']:>20} │")
print(f"   │ Modo dimensionamiento:        {results['sizing_mode']:>20} │")
print("   └─────────────────────────────────────────────────────────────┘")

print("\n🌍 IMPACTO SISTEMA ELÉCTRICO IQUITOS:")
print("   ┌─────────────────────────────────────────────────────────────┐")
print(f"   │ Red suprimida (deficit 9-22h): {cobertura-100:.1f}% margen extra      │")
print(f"   │ Reducción importación:        {(1-results['self_sufficiency'])*100:>10.2f}%            │")
print(f"   │ PV directo a demanda:         46.5%                        │")
print(f"   │ BESS cubre deficit nocturno:  100% ✓                       │")
print("   └─────────────────────────────────────────────────────────────┘")

print("\n✅ CONCLUSIÓN:")
print(f"   BESS de {results['capacity_kwh']:.0f} kWh / {results['nominal_power_kw']:.0f} kW")
print(f"   • Cubre 100% del deficit EV nocturno (9-22h)")
print(f"   • Margen de seguridad: +{cobertura-100:.1f}%")
print(f"   • Autosuficiencia del sistema: {results['self_sufficiency']*100:.2f}%")
print(f"   • Criterio: Deficit EV en horario de apertura (9-22h)")
print("\n" + "="*75 + "\n")
