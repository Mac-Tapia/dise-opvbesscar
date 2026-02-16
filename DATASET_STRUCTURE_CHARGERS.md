"""
📋 ESTRUCTURA DEL DATASET CHARGERS - chargers_ev_ano_2024_v3.csv

RESUMEN EJECUTIVO:
- GENERADO EN: src/dimensionamiento/oe2/disenocargadoresev/chargers.py (línea 950)
- DIMENSIONES FINALES: 8,760 filas × 240 columnas
- PERIODO: 1 año (2024) con resolución horaria
- CONTENIDO: Simulación estocástica de 38 puertos de carga (19 chargers × 2 sockets)

ARQUITECTURA DE COLUMNAS (240 total):
═════════════════════════════════════════════════════════════════════════════

[GRUPO 1] POWER DEMANDS - Para CityLearn v2 (38 columnas)
───────────────────────────────────────────────────────
  Uso: Action space control en agentes RL
  Columnas: socket_000_charging_power_kw ... socket_037_charging_power_kw
  Descripción: Potencia instantánea de carga en kW (0-7.4 kW) por socket
  Rango: [0.0, 7.4] kW
  Suma horaria: ev_energia_total_kwh (validar en columna companion)
  NECESARIAS: ✓ SÍ (crítica para RL control)

[GRUPO 2] STATE OF CHARGE (SOC) - Para debugging y validación (114 columnas)
────────────────────────────────────────────────────────────────────────────
  Uso: Análisis de comportamiento, debugging, validación de carga
  Columnas: socket_XXX_soc_arrival, socket_XXX_soc_current, socket_XXX_soc_target
  Descripción: 
    - soc_arrival: SOC cuando el vehículo llega (0-1)
    - soc_current: SOC actual durante carga (0-1)
    - soc_target: SOC objetivo de carga (0-1)
  Nota: Mantener para análisis profundo de patrones de carga
  NECESARIAS: ✓ SÍ (debugging y validación)

[GRUPO 3] SOCKET STATE - Para tracking y debugging (76 columnas)
────────────────────────────────────────────────────────────────
  Uso: Estado e historial del socket
  Columnas: socket_XXX_active, socket_XXX_vehicle_count
  Descripción:
    - _active: 1 si hay vehículo siendo cargado, 0 si vacío
    - _vehicle_count: Número de vehículos en cola esperando (0-N)
  NECESARIAS: ✓ SÍ (para conteo de vehículos activos)

[GRUPO 4] VEHICLE COUNTS - Para análisis de demanda (3 columnas)
─────────────────────────────────────────────────────────────────
  Uso: Cuantificación de actividad simultánea
  Columnas:
    1. cantidad_motos_activas: Número de motos siendo cargadas (0-30)
    2. cantidad_mototaxis_activas: Número de taxis siendo cargados (0-8)
    3. cantidad_total_vehiculos_activos: Total activos (sum de arriba)
  Descripción: Agregados por hora para tracking de demanda por tipo
  Validación: cantidad_total_vehiculos_activos = cantidad_motos_activas + cantidad_mototaxis_activas
  NECESARIAS: ✓ SÍ (esencial para tracking de demanda)

[GRUPO 5] ENERGY AGGREGATES - Para validación energética (3 columnas)
──────────────────────────────────────────────────────────────────────
  Uso: Validación de balances energéticos
  Columnas:
    1. ev_energia_total_kwh: Energía total cargada en la hora (kWh)
    2. ev_energia_motos_kwh: Energía solo en motos (kWh)
    3. ev_energia_mototaxis_kwh: Energía solo en mototaxis (kWh)
  Descripción:
    - ev_energia_total_kwh = SUM(socket_XXX_charging_power_kw) por hora
    - ev_energia_motos_kwh = SUM(socket_0..29) por hora
    - ev_energia_mototaxis_kwh = SUM(socket_30..37) por hora
  Validación: ev_energia_motos_kwh + ev_energia_mototaxis_kwh = ev_energia_total_kwh
  Anual: 565,875 kWh/año (476,501 motos + 89,374 taxis)
  NECESARIAS: ✓ SÍ (crítica para balance)

[GRUPO 6] CO2 EMISSION REDUCTIONS - Para optimización de CO₂ (5 columnas)
──────────────────────────────────────────────────────────────────────────
  Uso: Objetivo principal de optimización (minimizar CO₂)
  Columnas:
    1. co2_reduccion_motos_kg: CO₂ EVITADO por motos (gasol → EV)
       = ev_energia_motos_kwh × 0.87 kg CO₂/kWh
       Significado: Gasolina que NO se quema porque cargan con electricidad
    
    2. co2_reduccion_mototaxis_kg: CO₂ EVITADO por taxis (gasol → EV)
       = ev_energia_mototaxis_kwh × 0.47 kg CO₂/kWh
       Significado: Gasolina que NO se quema
    
    3. reduccion_directa_co2_kg: CO₂ DIRECTO evitado (cambio combustible)
       = co2_reduccion_motos_kg + co2_reduccion_mototaxis_kg
       Significado: Total de gasolina ahorrada en equivalente CO₂
    
    4. co2_grid_kwh: CO₂ DEL GRID (Diesel para generar electricidad)
       = ev_energia_total_kwh × 0.4521 kg CO₂/kWh
       Significado: Emisiones del diesel importado para cargar EVs (Iquitos 100% térmico)
    
    5. co2_neto_por_hora_kg: CO₂ NETO (reducción - grid)
       = reduccion_directa_co2_kg - co2_grid_kwh
       Significado: CO₂ realmente ahorrado después de considerar el grid
       Interpretación: Si > 0, hay ganancia neta. Si < 0, grid contamina más.
  
  Anual:
    - co2_reduccion_motos_kg: 414,555 kg (gasolina ahorrada motos)
    - co2_reduccion_mototaxis_kg: 42,006 kg (gasolina ahorrada taxis)
    - reduccion_directa_co2_kg: 456,561 kg (total gasolina ahorrada)
    - co2_grid_kwh: 255,832 kg (diesel generador)
    - co2_neto_por_hora_kg: 200,729 kg (ganancia neta anual)
  
  NECESARIAS: ✓ SÍ (objetivo principal de RL)

[GRUPO 7] CITYLEARN ALIAS - Para compatibilidad (1 columna)
──────────────────────────────────────────────────────────
  Uso: Compatibilidad con environment CityLearn v2
  Columnas:
    1. ev_demand_kwh: Alias de ev_energia_total_kwh
       Por qué: CityLearn puede esperar esta nomenclatura específica
  NECESARIAS: ✓ SÍ (compatibilidad)

═════════════════════════════════════════════════════════════════════════════

COLUMNAS ELIMINADAS (118) - Y POR QUÉ:
───────────────────────────────────────

❌ socket_XXX_charger_power_kw (38 columnas)
   Razón: Potencia nominal constante (siempre 7.4 kW), no agrega valor
   Impacto: Se puede recuperar del spec del charger (7.4 kW)

❌ socket_XXX_battery_kwh (38 columnas)
   Razón: Capacidad de batería constante por tipo (4.6 o 7.4 kWh)
   Impacto: Se puede recuperar del spec del vehículo por socket tipo

❌ socket_XXX_vehicle_type (38 columnas)
   Razón: Tipo de vehículo constante por socket (moto o mototaxi)
   Impacto: Se puede recuperar de la asignación fija:
            - Sockets 0-29: motos
            - Sockets 30-37: mototaxis

❌ is_hora_punta (1 columna)
   Razón: Redundante con header timestamp (puede calcularse de la hora)
   Impacto: is_hora_punta = (hour >= 18 AND hour < 23) ? 1 : 0

❌ tarifa_aplicada_soles (1 columna)
   Razón: Tarifa es fija (igual para todoslos datos de ese periodo)
   Impacto: Constante, no impacta decisiones de RL

❌ costo_carga_ev_soles (1 columna)
   Razón: Se calcula en simulación como energy × tarifa
   Impacto: Puede recalcularse si es necesario

═════════════════════════════════════════════════════════════════════════════

VALIDACIONES DE INTEGRIDAD:
───────────────────────────

✓ Filas: 8,760 (365 días × 24 horas)
✓ Energía anual: 565,875 kWh
  - Motos: 476,501 kWh (84.2%)
  - Taxis: 89,374 kWh (15.8%)
✓ Promedio diario: 1,549.52 kWh/día (CORRECTO para 38 sockets)
✓ CO₂ neto evitado: 200,729 kg/año (34% de reducción directa)
✓ Índice: datetime (8,760 registros únicos por hora)

═════════════════════════════════════════════════════════════════════════════

COMPATIBILIDAD CON SISTEMAS:
──────────────────────────

✓ CityLearn v2:
  - Demanda por socket: ✓ socket_XXX_charging_power_kw (38 cols)
  - Observación ambiada: ✓ Can extract from other datasets
  - Reward signal: ✓ co2_neto_por_hora_kg disponible

✓ Training scripts (train_sac_multiobjetivo.py, train_ppo_multiobjetivo.py, etc.):
  - Carga: pd.read_csv('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
  - Energia: df['ev_energia_total_kwh']
  - Conteos: df['cantidad_motos_activas'], df['cantidad_mototaxis_activas']
  - CO2: df['co2_reduccion_motos_kg'], df['reduccion_directa_co2_kg'], etc.

✓ Data loaders (data_loader.py, dataset_builder.py):
  - Input: chargers CSV
  - Output: CityLearn environment observations

═════════════════════════════════════════════════════════════════════════════

NOTAS IMPORTANTES:
──────────────────

1. BACKUP: chargers_ev_ano_2024_v3_backup.csv (18.30 MB)
   - Contiene todas las 358 columnas originales
   - Conservar para análisis profundo si es necesario

2. REGENERACIÓN: Si se ejecuta de nuevo src/dimensionamiento/oe2/disenocargadoresev/chargers.py:
   - Salida inicial: 358 columnas
   - Se requiere ejecutar clean_datasets.py para reducir a 240

3. SOC VARIABLE: Los valores de carga (charging_power_kw) reflejan SOC variable
   - Carga parcial en lugar de carga completa a 100%
   - Impacta: -34% energía anual vs carga completa
   - CO₂ también reducido proporcionalmente

4. HORIZONTE FUTURO:
   - Considerar generación separada de chargers_minimal.csv con apenas 39 columnas
     (1 datetime + 38 poderes) si se necesita ultra-optimización
   - Actual (240 cols) es buen balance entre compilación y debugging

═════════════════════════════════════════════════════════════════════════════
Versión: 2026-02-16
Generado: clean_datasets.py
Actualizado: chargers.py línea 950
═════════════════════════════════════════════════════════════════════════════
"""
