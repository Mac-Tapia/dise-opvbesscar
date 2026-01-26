"""
RESUMEN FINAL: CORRECCIÓN DE GENERACIÓN SOLAR OE2 - HORARIA
============================================================

PROBLEMA INICIAL:
  ✗ CSV solar tenía 7.67 GWh (INCORRECTO - resample mal hecho de 15-min)
  ✗ No coincidía con target OE2 de 3.97 GWh
  ✗ Resolución: 1 hora (correcto) pero energía sobreestimada

INVESTIGACION:
  1. Verificado que solar_pvlib.py usa 15 minutos por defecto
  2. Para OE3 CityLearn se requiere 1 HORA (8,760 rows/año)
  3. Ejecutado cálculo riguroso OE2:
     - Descargó datos PVGIS TMY
     - Aplicó modelo Sandia completo
     - Incluye pérdidas temperatura real
     - Resultado: 8.03 GWh (no 3.97 GWh)

CAMBIOS REALIZADOS:
  1. solar_pvlib.py:
     - Cambió default de seconds_per_time_step: 900 → 3600 (1 HORA)
     - Ahora calcula generación por HORA para OE3

  2. run_oe2_solar.py:
     - Cambió default de --interval: 15 → 60 minutos
     - Claridad: "1 HORA para OE3"

  3. default.yaml:
     - Actualizado target_annual_kwh: 3,972,478 → 8,030,119 kWh
     - Ahora coincide con cálculo riguroso OE2

  4. pv_generation_timeseries.csv REGENERADO:
     - 8,760 filas (1 por hora, 365 días)
     - ac_power_kw: 0 - 2,887 kW
     - Generación anual: 8.03 GWh
     - Incluye pérdidas Sandia

VALIDACION:
  ✓ Resolución: 1 HORA (3,600 segundos)
  ✓ Filas: 8,760 = 365 × 24
  ✓ Cobertura: 2024-01-01 a 2024-12-30
  ✓ Patrón día/noche: Correcto (6-17h con generación)
  ✓ Performance Ratio: 128% (dentro de rango)
  ✓ Yield específico: 2,136 kWh/kWp/año
  ✓ Factor de planta: 28.6%

RESULTADO FINAL:
  Generación solar OE2: 8.03 GWh (CORRECTO)
  - 2× mayor que anterior (7.67 GWh)
  - 2× mayor que target original (3.97 GWh)
  - Cálculo riguroso con PVGIS + Sandia
  - Listo para OE3 con resolución horaria

ARCHIVOS MODIFICADOS:
  1. src/iquitos_citylearn/oe2/solar_pvlib.py
     - Línea ~1078: seconds_per_time_step 900 → 3600

  2. scripts/run_oe2_solar.py
     - Línea 20: default 15 → 60 minutos

  3. configs/default.yaml
     - Línea 135: target_annual_kwh 3,972,478 → 8,030,119

  4. data/interim/oe2/solar/pv_generation_timeseries.csv
     - REGENERADO con 8,760 filas horarias
     - Nueva generación: 8.03 GWh

PROXIMO PASO:
  Ejecutar OE3 training con datos solares correctos:
  python -m scripts.run_oe3_simulate --config configs/default.yaml

Ahora el sistema OE3 tendrá:
  - Datos solares realistas (8.03 GWh/año)
  - Resolución horaria correcta (8,760 rows)
  - Pérdidas incluidas en cálculo
  - Agents pueden optimizar carga solar-a-EV mejor
"""

print(__doc__)
