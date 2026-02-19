#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REPORTE DETALLADO: ALINEACIÓN CO2, VEHÍCULOS Y DATOS
====================================================
Comparativa línea-por-línea entre SAC, PPO y A2C
"""

print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║         REPORTE ALINEACIÓN: SAC vs PPO vs A2C - CO2 y DATOS REALES          ║
╚══════════════════════════════════════════════════════════════════════════════╝

[SECCIÓN 1] IMPORTACIÓN DE CONSTANTES
═══════════════════════════════════════════════════════════════════════════════

┌─ SAC (train_sac.py líneas 46-92) ─────────────────────────────────────────┐
│                                                                              │
│  ✓ Importa de: src.dataset_builder_citylearn.data_loader                   │
│    - BESS_CAPACITY_KWH                  ← importado               [2000 kWh]│
│    - BESS_MAX_POWER_KW                  ← importado               [400 kW]  │
│    - N_CHARGERS                         ← importado               [19]      │
│    - TOTAL_SOCKETS                      ← importado               [38]      │
│    - SOLAR_PV_KWP                       ← importado               [4050]    │
│    - CO2_FACTOR_GRID_KG_PER_KWH         ← importado               [0.4521]  │
│                                                                              │
│  ✓ Define localmente (líneas 70-92):                                       │
│    CO2_FACTOR_IQUITOS = 0.4521          kg CO2/kWh (grid termico)         │
│    BESS_MAX_KWH_CONST = 2000.0          kWh max SOC                        │
│    SOLAR_MAX_KW = 2887.0                real observado en datos            │
│    CHARGER_MAX_KW = 3.7                 max per socket (7.4/2)             │
│    MOTOS_TARGET_DIARIOS = 270           vehículos por día                  │
│    MOTOTAXIS_TARGET_DIARIOS = 39        vehículos por día                  │
│    CO2_FACTOR_MOTO_KG_KWH = 0.87        kg CO2/kWh vs gasolina             │
│    CO2_FACTOR_MOTOTAXI_KG_KWH = 0.47    kg CO2/kWh vs gasolina             │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌─ PPO (train_ppo.py líneas 71-89) ─────────────────────────────────────────┐
│                                                                              │
│  ✓ Importa de: common_constants                                            │
│    - CO2_FACTOR_IQUITOS                 ← importado               [0.4521]  │
│    - HOURS_PER_YEAR                     ← importado               [8760]    │
│    - BESS_MAX_KWH_CONST                 ← importado               [2000.0]  │
│    - SOLAR_MAX_KW                       ← importado               [2887.0]  │
│    - CHARGER_MAX_KW                     ← importado               [10.0]    │
│    - MOTOS_TARGET_DIARIOS               ← importado               [270]     │
│    - MOTOTAXIS_TARGET_DIARIOS           ← importado               [39]      │
│    - CO2_FACTOR_MOTO_KG_KWH             ← importado               [0.87]    │
│    - CO2_FACTOR_MOTOTAXI_KG_KWH         ← importado               [0.47]    │
│                                                                              │
│  ⚠️  CHARGER_MAX_KW ≠ SAC (10.0 vs 3.7)  ← DIFERENCIA ENCONTRADA!          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌─ A2C (train_a2c.py líneas 44-62) ─────────────────────────────────────────┐
│                                                                              │
│  ✓ Importa de: common_constants (igual que PPO)                            │
│    - CO2_FACTOR_IQUITOS                 ← importado               [0.4521]  │
│    - HOURS_PER_YEAR                     ← importado               [8760]    │
│    - BESS_MAX_KWH_CONST                 ← importado               [2000.0]  │
│    - SOLAR_MAX_KW                       ← importado               [2887.0]  │
│    - CHARGER_MAX_KW                     ← importado               [10.0]    │
│    - MOTOS_TARGET_DIARIOS               ← importado               [270]     │
│    - MOTOTAXIS_TARGET_DIARIOS           ← importado               [39]      │
│    - CO2_FACTOR_MOTO_KG_KWH             ← importado               [0.87]    │
│    - CO2_FACTOR_MOTOTAXI_KG_KWH         ← importado               [0.47]    │
│                                                                              │
│  ✓ Import locales adicionales:                                             │
│    - Dataset loader v5.8 de data_loader (igual que SAC)                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

[SECCIÓN 2] CARGA DE DATOS REALES DE CO2 DIRECTO
═══════════════════════════════════════════════════════════════════════════════

┌─ SAC (train_sac.py líneas 687-725) ───────────────────────────────────────┐
│                                                                              │
│  Dataset: data/oe2/chargers/chargers_ev_ano_2024_v3.csv                    │
│                                                                              │
│  Columnas buscadas:                                                        │
│    'reduccion_directa_co2_kg'  ✅ ENCONTRADA y USADA                       │
│    'ev_demand_kwh'              ✅ ENCONTRADA y USADA                       │
│                                                                              │
│  Carga (línea 697):                                                        │
│    chargers_data[col] = df_chargers[col].values[:8760].astype(...)         │
│                                                                              │
│  Validación (línea 724):                                                   │
│    if 'reduccion_directa_co2_kg' in chargers_data:                         │
│        print(f"CO2 DIRECTO: {sum(co2_data):,.0f} kg/año")                  │
│                                                                              │
│  ✅ REAL DATA: SÍ, usa columna real 'reduccion_directa_co2_kg' del CSV     │
│  ✅ 8,760 HORAS: SÍ, extrae [:8760] de los datos                          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌─ PPO (train_ppo.py línea 636) ────────────────────────────────────────────┐
│                                                                              │
│  Dataset: data/oe2/chargers/chargers_ev_ano_2024_v3.csv                    │
│                                                                              │
│  Carga (línea 636):                                                        │
│    self.chargers_co2_df = pd.read_csv(                                     │
│        'data/oe2/chargers/chargers_ev_ano_2024_v3.csv'                     │
│    )                                                                         │
│                                                                              │
│  ⚠️  PROBLEMA: Carga el DataFrame pero NO VEMOS DONDE LO USA               │
│                                                                              │
│  Búsqueda de uso de 'reduccion_directa_co2_kg':                            │
│    → Línea 303: ['ev_reduccion_directa_co2_kg', 'ev_demand_kwh']           │
│    → Línea 368: Retorna 'reduccion_directa_co2_kg, demand_kwh'             │
│                                                                              │
│  ❓ ESTADO: DESCONOCIDO - Necesita verificación de líneas 303-400          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌─ A2C (train_a2c.py líneas 1634-1635, 2348-2349) ─────────────────────────┐
│                                                                              │
│  Dataset: data/oe2/chargers/chargers_ev_ano_2024_v3.csv                    │
│                                                                              │
│  Aló carga (línea 1635):                                                   │
│    if 'reduccion_directa_co2_kg' in chargers_df.columns:                   │
│        chargers_co2_data['co2_total_kg'] =                                 │
│            chargers_df['reduccion_directa_co2_kg'].astype(np.float32)      │
│                                                                              │
│  Segunda carga (línea 2349):                                               │
│    chargers_co2_data['co2_total_kg'] =                                     │
│        df_chargers['reduccion_directa_co2_kg'].values[:8760].astype(...)   │
│                                                                              │
│  ✅ REAL DATA: SÍ, usa columna real 'reduccion_directa_co2_kg' del CSV     │
│  ✅ 8,760 HORAS: SÍ, extrae [:8760] de los datos                          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

[SECCIÓN 3] RESUMEN COMPARATIVO
═══════════════════════════════════════════════════════════════════════════════

┌─ Constantes ──────────────────────────────────────────────────────────────┐
│                                                                              │
│  Constante                    SAC              PPO              A2C          │
│  ───────────────────────────────────────────────────────────────────────   │
│  BESS_MAX_KWH_CONST           2000.0           2000.0           2000.0    ✅│
│  CO2_FACTOR_IQUITOS           0.4521           0.4521           0.4521    ✅│
│  MOTOS_TARGET_DIARIOS         270              270              270       ✅│
│  MOTOTAXIS_TARGET_DIARIOS     39               39               39        ✅│
│  CO2_FACTOR_MOTO              0.87             0.87             0.87      ✅│
│  CO2_FACTOR_MOTOTAXI          0.47             0.47             0.47      ✅│
│  CHARGER_MAX_KW               3.7              10.0             10.0      ❌│
│  SOLAR_MAX_KW                 2887.0           2887.0           2887.0    ✅│
│                                                                              │
│  → DIFERENCIA: CHARGER_MAX_KW en SAC (3.7) vs PPO/A2C (10.0)              │
│    • SAC: 7.4 kW / 2 sockets = 3.7 kW/socket   ← CORRECTO (física)        │
│    • PPO/A2C: 10.0 kW - INCORRECTO (sobrestima)                           │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌─ Carga de CO2 Directo Real ──────────────────────────────────────────────┐
│                                                                              │
│  Agente      Dataset                                Estado                  │
│  ─────────────────────────────────────────────────────────────────────────  │
│  SAC         reduccion_directa_co2_kg               ✅ Visible y usado      │
│  PPO         ? (código necesita análisis)          ❓ INCERTIDUMBRE        │
│  A2C         reduccion_directa_co2_kg               ✅ Visible y usado      │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘


[SECCIÓN 4] ACCIONES REQUERIDAS
═══════════════════════════════════════════════════════════════════════════════

✅ COMPLETADO:
   • SAC y A2C usan datos REALES de 'reduccion_directa_co2_kg'
   • Todos los tres usan 8,760 horas (HOURS_PER_YEAR)
   • Constantes de CO2 (0.4521, 0.87, 0.47) alineadas en tres agentes

❌ REQUIERE ALINEACIÓN:
   1. CHARGER_MAX_KW: SAC=3.7 (correcto) vs PPO/A2C=10.0 (incorrecto)
      → ACCIÓN: Cambiar PPO y A2C a 3.7 desde common_constants.py
   
   2. PPO CO2 directo: Verificar línea 303-368 para confirmar uso de datos reales
      → ACCIÓN: Analizar cómo PPO usa chargers_co2_df
   
   3. Harmonía de cálculos: Verificar que los tres usan MISMA lógica de flujos
      → ACCIÓN: Buscar líneas de cálculo de CO2 indirecto en cada uno

═══════════════════════════════════════════════════════════════════════════════
""")
