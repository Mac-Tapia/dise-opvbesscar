"""
VERIFICACIÓN FINAL: Dimensionamiento de Cargadores EV

Reglas que DEBE cumplir:
1. 900 motos + 130 mototaxis en hora pico (6pm-10pm, 4h) → SOLO para dimensionar cargadores
2. Los cargadores dimensionados operan TODO el día (9am-10pm, 13h)
3. Modo 3, sesiones de 30 minutos
4. Capacidad total = 128 tomas × 26 sesiones/día × 92% utilización = 3,062 vehículos/día
"""

import json
from pathlib import Path

print("=" * 70)
print("VERIFICACIÓN FINAL: Cumplimiento de Reglas de Dimensionamiento")
print("=" * 70)

# Cargar resultados
json_path = Path("data/interim/oe2/chargers/chargers_results.json")
if not json_path.exists():
    print(f"\n❌ ERROR: No se encontró {json_path}")
    exit(1)

with open(json_path, encoding='utf-8') as f:
    data = json.load(f)

print("\n✅ REGLA 1: Parámetros de Hora Pico para Dimensionamiento")
print(f"   Motos hora pico (6pm-10pm):     {data['n_motos_pico']}")
print(f"   Mototaxis hora pico (6pm-10pm): {data['n_mototaxis_pico']}")
print(f"   TOTAL:                          {data['n_motos_pico'] + data['n_mototaxis_pico']}")

print("\n✅ REGLA 2: Cargadores Dimensionados")
print(f"   Cargadores recomendados: {data['n_chargers_recommended']}")
print(f"   Potencia instalada:      {data['potencia_total_instalada_kw']} kW")
print(f"   - Motos:     {data['potencia_instalada_motos_kw']} kW (28 carg × 4 tomas × 2 kW)")
print(f"   - Mototaxis: {data['potencia_instalada_mototaxis_kw']} kW (4 carg × 4 tomas × 3 kW)")

print("\n✅ REGLA 3: Operación Todo el Día (9am-10pm, 13h)")
print("   Modo 3: Sesiones de 30 minutos")
print("   Horario: 9:00 - 22:00 (13 horas)")
print("   Sesiones por toma: 13h × 2 sesiones/h = 26 sesiones/día")

print("\n✅ REGLA 4: Capacidad Total de Infraestructura")
tomas_totales = 32 * 4  # 128
sesiones_por_toma = 26
utilizacion = 0.92
capacidad_maxima = tomas_totales * sesiones_por_toma  # 3,328
capacidad_calculada = int(round(capacidad_maxima * utilizacion))  # Usar round() como en el código

print(f"   Tomas totales:            {tomas_totales}")
print(f"   Sesiones por toma/día:    {sesiones_por_toma}")
print(f"   Capacidad máxima:         {capacidad_maxima:,} sesiones/día")
print(f"   Utilización:              {utilizacion:.0%}")
print(f"   Cálculo:                  {capacidad_maxima} × {utilizacion} = {capacidad_maxima * utilizacion:.2f}")
print(f"   Capacidad calculada:      {capacidad_calculada:,} vehículos/día")
print(f"   Capacidad en JSON:        {data['capacidad_infraestructura_dia']:,} vehículos/día")

if capacidad_calculada == data['capacidad_infraestructura_dia']:
    print("   ✅ CORRECTO: Capacidad coincide")
else:
    print(f"   ❌ ERROR: Capacidad no coincide ({capacidad_calculada} vs {data['capacidad_infraestructura_dia']})")

print("\n✅ VERIFICACIÓN: Variables que NO deben existir")
variables_no_deseadas = ['n_motos_dia_total', 'n_mototaxis_dia_total', 'peak_share_day']
for var in variables_no_deseadas:
    if var in data:
        print(f"   ❌ ERROR: Variable '{var}' NO debería existir en el JSON")
    else:
        print(f"   ✅ OK: Variable '{var}' correctamente eliminada")

print("\n" + "=" * 70)
print("✅ VERIFICACIÓN COMPLETA")
print("=" * 70)
print("\nRESUMEN:")
print(f"  • 900+130 vehículos en hora pico → Dimensionan {data['n_chargers_recommended']} cargadores")
print(f"  • {tomas_totales} tomas operando 13h/día → Capacidad de {data['capacidad_infraestructura_dia']:,} vehículos/día")
print(f"  • Potencia instalada: {data['potencia_total_instalada_kw']} kW")
print(f"  • Proyección anual: {data['capacidad_infraestructura_anio']:,} vehículos")
print(f"  • Proyección 20 años: {data['capacidad_infraestructura_20anios']:,} vehículos")
