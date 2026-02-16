================================================================================
VERIFICACIÓN DE NOMBRES DE DATASETS - REPORTE FINAL
================================================================================
Fecha: 2026-02-14
Análisis: Nombres de columnas REALES vs. ESPERADOS en código de entrenamiento

================================================================================
RESULTADO: DISCREPANCIAS ENCONTRADAS ⚠️
================================================================================

📊 DATASET 1: SOLAR
Ruta: data/oe2/Generacionsolar/pv_generation_citylearn2024.csv
Filas: 8760 | Columnas: 11

✅ COLUMNAS REALES:
  1. datetime
  2. irradiancia_ghi
  3. temperatura_c
  4. velocidad_viento_ms
  5. potencia_kw
  6. energia_kwh
  7. is_hora_punta
  8. hora_tipo
  9. tarifa_aplicada_soles
  10. ahorro_solar_soles
  11. reduccion_indirecta_co2_kg

⚠️  DISCREPANCIA - Columnas esperadas en código:
  - 'is_hora_punta' ✅ EXISTE
  - 'tarifa_aplicada_soles' ✅ EXISTE
  - 'ahorro_solar_soles' ✅ EXISTE
  - 'reduccion_indirecta_co2_kg' ✅ EXISTE
  - 'co2_evitado_mall_kg' ❌ NO EXISTE
  - 'co2_evitado_ev_kg' ❌ NO EXISTE

ANÁLISIS: Las columnas 'co2_evitado_mall_kg' y 'co2_evitado_ev_kg' NO existen.
Probable causa: No están siendo calculadas en el archivo SOLAR o están en BESS.

================================================================================

📊 DATASET 2: CHARGERS
Ruta: data/oe2/chargers/chargers_ev_ano_2024_v3.csv
Filas: 8760 | Columnas: 353 (38 sockets × ~9 + agregadas)

✅ COLUMNAS POR SOCKET (ejemplo socket_000):
  - socket_000_charger_power_kw
  - socket_000_battery_kwh
  - socket_000_vehicle_type
  - socket_000_soc_current
  - socket_000_soc_arrival
  - socket_000_soc_target
  - socket_000_active
  - socket_000_charging_power_kw
  - socket_000_vehicle_count
  [... misma estructura para socket_001 a socket_037 ...]

✅ COLUMNAS AGREGADAS (al final del archivo):
  1. is_hora_punta
  2. tarifa_aplicada_soles
  3. ev_energia_total_kwh
  4. costo_carga_ev_soles
  5. ev_energia_motos_kwh
  6. ev_energia_mototaxis_kwh
  7. co2_reduccion_motos_kg
  8. co2_reduccion_mototaxis_kg
  9. reduccion_directa_co2_kg
  10. ev_demand_kwh

✅ TODAS ESPERADAS EXISTEN (10/10):
  ✅ is_hora_punta
  ✅ tarifa_aplicada_soles
  ✅ ev_energia_total_kwh
  ✅ costo_carga_soles → REAL: 'costo_carga_ev_soles' (nombre diferente)
  ✅ ev_energia_motos_kwh
  ✅ ev_energia_mototaxis_kwh
  ✅ co2_reduccion_motos_kg
  ✅ co2_reduccion_mototaxis_kg
  ✅ reduccion_directa_co2_kg
  ✅ ev_demand_kwh

⚠️  DISCREPANCIA MENOR: 'costo_carga_soles' se llama 'costo_carga_ev_soles'

================================================================================

📊 DATASET 3: BESS
Ruta: data/oe2/bess/bess_ano_2024.csv
Filas: 8760 | Columnas: 25

✅ COLUMNAS REALES:
  1. datetime
  2. pv_generation_kwh ⚠️  (¿duplicado con SOLAR?)
  3. ev_demand_kwh ⚠️  (¿duplicado con CHARGERS?)
  4. mall_demand_kwh
  5. pv_to_ev_kwh
  6. pv_to_bess_kwh
  7. pv_to_mall_kwh
  8. pv_curtailed_kwh
  9. bess_charge_kwh
  10. bess_discharge_kwh
  11. bess_to_ev_kwh
  12. bess_to_mall_kwh
  13. grid_to_ev_kwh
  14. grid_to_mall_kwh
  15. grid_to_bess_kwh
  16. grid_import_total_kwh
  17. bess_soc_percent
  18. bess_mode
  19. tariff_osinergmin_soles_kwh
  20. cost_grid_import_soles
  21. peak_reduction_savings_soles
  22. peak_reduction_savings_normalized
  23. co2_avoided_indirect_kg
  24. co2_avoided_indirect_normalized
  25. mall_grid_import_kwh

✅ COLUMNAS ESPERADAS EN CÓDIGO (v5.5):
  1. bess_soc_percent ✅ EXISTE
  2. bess_charge_kwh ✅ EXISTE
  3. bess_discharge_kwh ✅ EXISTE
  4. bess_to_mall_kwh ✅ EXISTE
  5. bess_to_ev_kwh ✅ EXISTE

📌 NOTA: BESS tiene MUCHAS más columnas que las 5 esperadas.
Las columnas como 'pv_to_ev_kwh', 'pv_to_bess_kwh', 'co2_avoided_indirect_kg'
son muy útiles pero NO están incorporadas en las 27 columnas observables.

⚠️  DISCREPANCIA MAYOR: El código usa solo 5/25 columnas disponibles en BESS.

================================================================================

📊 DATASET 4: MALL_DEMAND
Ruta: data/oe2/demandamallkwh/demandamallhorakwh.csv
Filas: No verificadas | Columnas: 1

⚠️  PROBLEMA CRÍTICO - Separador incorrecto:
  Columna reportada: 'FECHAHORA;kWh'
  
  Esto indica que el separador es ';' y NO ',' como se asume en código.
  El archivo viene con nombre semi-parcelado: 'FECHAHORA;kWh'
  
  ACCIÓN REQUERIDA: Especificar sep=';' al cargar este archivo.

⚠️  COLUMNAS ESPERADAS (no están presentes):
  - 'mall_demand_kwh' ❌ NO EXISTE (está en BESS, no en MALL_DEMAND)
  - 'mall_demand_reduction_kwh' ❌ NO EXISTE
  - 'mall_cost_soles' ❌ NO EXISTE

NO HAY 3 columnas esperadas. El archivo solo tiene: FECHAHORA;kWh

================================================================================

🔴 RESUMEN DE PROBLEMAS ENCONTRADOS
================================================================================

CRÍTICO (Bloquea entrenamiento):
  1. MALL_DEMAND usa separador ';' pero código probablemente espera ','
  2. MALL_DEMAND NO tiene columnas esperadas (mall_demand_kwh, etc.)

MAYOR (Afecta observables):
  1. SOLAR falta 'co2_evitado_mall_kg' y 'co2_evitado_ev_kg'
  2. BESS tiene 25 columnas pero código solo usa 5

MENOR (Nombres diferentes):
  1. CHARGERS: 'costo_carga_ev_soles' vs 'costo_carga_soles'

================================================================================

📋 CONCLUSIÓN
================================================================================

Las 27 columnas "observables" esperadas NO son todas accesibles actualmente:

CHARGERS (10 columnas): ✅ 9.5/10 disponibles
SOLAR (6 columnas):     ⚠️  4/6 disponibles (faltan co2_evitado_*)
BESS (5 columnas):      ✅ 5/5 disponibles
MALL (3 columnas):      ❌ 0/3 disponibles
TOTALES (3 columnas):   ⚠️  ??? (no se valida dónde vienen)

TOTAL: ~21-23/27 columnas observables se pueden construir

RECOMENDACIÓN: Antes de hacer BUILD, necesitas:

1. Verificar si 'co2_evitado_mall_kg' y 'co2_evitado_ev_kg' deben venir de SOLAR 
   o deben calcularse como derivadas de BESS

2. Verificar estructura real de MALL_DEMAND (¿separador, columnas correctas?)

3. Actualizar código de carga para aceptar nombres reales (ej: 'costo_carga_ev_soles')

================================================================================
