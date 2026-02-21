#!/usr/bin/env python3
"""
ACLARACIÓN - ENTRADA vs SALIDA en bess.py y balance.py
========================================================

Diagrama Correcto del Flujo de Datos:

BESS.PY (Dimensionamiento):
  ENTRA (Lee):
    ├─ pv_generation_citylearn2024.csv        ← ENTRA
    ├─ chargers_ev_ano_2024_v3.csv            ← ENTRA
    └─ demandamallhorakwh.csv                 ← ENTRA
  
  PROCESA: 6 Fases de BESS
  
  SALE (Genera):
    └─ bess_ano_2024.csv                      ← SALE (OUTPUT)

BALANCE.PY (Visualización):
  ENTRA (Lee):
    └─ bess_ano_2024.csv                      ← ENTRA (que BESS generó)
  
  PROCESA: Visualización (16 gráficas)
  
  SALE (Genera):
    ├─ 00_BALANCE_INTEGRADO_COMPLETO.png      ← SALE (OUTPUT)
    ├─ 01_balance_5dias.png                   ← SALE (OUTPUT)
    └─ ... (más gráficas)
"""

print(__doc__)

print("\n" + "="*90)
print("RESUMEN EJECUTIVO")
print("="*90)

print("""

┌─────────────────────────────────────────────────────────────────────────────┐
│ BESS.PY - Dimensionamiento OE2                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│ ARCHIVOS QUE USA (ENTRADAS - 3):                                            │
│   1️⃣  pv_generation_citylearn2024.csv                                       │
│       └─ Generación solar horaria (4,050 kWp)                              │
│       └─ Total: 8,292,514 kWh/año                                         │
│       └─ Ubicación: data/oe2/Generacionsolar/                             │
│                                                                               │
│   2️⃣  chargers_ev_ano_2024_v3.csv                                          │
│       └─ Demanda EV horaria (38 sockets: 30 motos + 8 mototaxis)           │
│       └─ Total: 408,282 kWh/año                                           │
│       └─ Ubicación: data/oe2/chargers/                                    │
│                                                                               │
│   3️⃣  demandamallhorakwh.csv                                               │
│       └─ Demanda MALL horaria (Centro Comercial)                           │
│       └─ Total: 12,368,653 kWh/año                                        │
│       └─ Ubicación: data/oe2/demandamallkwh/                              │
│                                                                               │
├─ ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──┤
│ PROCESAMIENTO:                                                              │
│   • Simula operación BESS con 6 fases (carga, descarga, holding, peak     │
│     shaving, reposo)                                                        │
│   • Calcula flujos energéticos (PV→EV, PV→BESS, BESS→MALL, Grid)         │
│   • Calcula estado BESS (SOC, carga, descarga)                            │
│   • Calcula beneficios (CO₂ evitado, ahorros tarifarios)                  │
├─ ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──┤
│ ARCHIVO QUE GENERA (SALIDA - 1):                                            │
│   📦 bess_ano_2024.csv                                                      │
│      └─ Contiene: 8,760 horas × 35 columnas                               │
│      └─ Incluye: PV, EV, MALL, flujos, BESS, grid, beneficios            │
│      └─ Ubicación: data/oe2/bess/                                         │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘

                                    ↓ (genera)

┌─────────────────────────────────────────────────────────────────────────────┐
│ BALANCE.PY - Visualización                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│ ARCHIVO QUE USA (ENTRADA - 1):                                              │
│   📊 bess_ano_2024.csv                                                      │
│      └─ Generado por bess.py                                               │
│      └─ Contiene datos precalculados (6 fases BESS)                        │
│      └─ Ubicación: data/oe2/bess/                                         │
│                                                                               │
├─ ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──┤
│ PROCESAMIENTO:                                                              │
│   • Lee columnas del dataset (energías, flujos, estado)                    │
│   • Procesa datos para visualización (normalizaciones, agregaciones)       │
│   • Genera 16 gráficas de balance energético                              │
│   • NO regenera lógica BESS (está precalculada)                            │
├─ ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ── ──┤
│ ARCHIVOS QUE GENERA (SALIDA - 16 GRÁFICAS):                                 │
│   1️⃣  00_BALANCE_INTEGRADO_COMPLETO.png                                    │
│   2️⃣  00.1_EXPORTACION_Y_PEAK_SHAVING.png                                  │
│   3️⃣  01_balance_5dias.png                                                 │
│   4️⃣  02_balance_diario.png                                                │
│   5️⃣  03_distribucion_fuentes.png                                          │
│   6️⃣  04_cascada_energetica.png                                            │
│   7️⃣  05_bess_soc.png                                                      │
│   8️⃣  05.1_bess_carga_descarga.png                                         │
│   9️⃣  06_emisiones_co2.png                                                 │
│  1️⃣0️⃣  07_utilizacion_pv.png                                               │
│  ... y 6 más                                                                │
│                                                                               │
│  Ubicación: outputs/balance_energetico/                                     │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
""")

print("\n" + "="*90)
print("TABLA COMPARATIVA")
print("="*90)

tabla = """
┌──────────┬──────────────────────────────────────────┬──────────────────────┐
│ MÓDULO   │ ARCHIVOS DE ENTRADA (USA)                │ ARCHIVOS DE SALIDA   │
├──────────┼──────────────────────────────────────────┼──────────────────────┤
│ BESS.PY  │ • pv_generation_citylearn2024.csv        │ bess_ano_2024.csv    │
│          │ • chargers_ev_ano_2024_v3.csv            │ (1 archivo)          │
│          │ • demandamallhorakwh.csv                 │                      │
│          │ (3 archivos fuente)                      │                      │
├──────────┼──────────────────────────────────────────┼──────────────────────┤
│BALANCE.PY│ • bess_ano_2024.csv                      │ 16 gráficas PNG      │
│          │ (1 archivo)                              │ (visualización)      │
│          │ [generado por BESS.PY]                   │                      │
└──────────┴──────────────────────────────────────────┴──────────────────────┘
"""

print(tabla)

print("\n" + "="*90)
print("RESPUESTA A LA PREGUNTA")
print("="*90)

respuesta = """

Q: "¿Para BESS usa ese dataset data/oe2/bess/bess_ano_2024.csv?"

A: ❌ NO. Es al revés:

   ► BESS.PY USA como entradas (input):
     1. pv_generation_citylearn2024.csv
     2. chargers_ev_ano_2024_v3.csv
     3. demandamallhorakwh.csv

   ► BESS.PY GENERA como salida (output):
     bess_ano_2024.csv

   ► BALANCE.PY USA como entrada:
     bess_ano_2024.csv (que BESS.PY generó)

   ► BALANCE.PY GENERA como salida:
     16 gráficas PNG


FLUJO CORRECTO:
===============

Paso 1: Ejecutar BESS.PY
   python -m src.dimensionamiento.oe2.disenobess.bess
   
   Lee:   pv_generation_citylearn2024.csv
          chargers_ev_ano_2024_v3.csv
          demandamallhorakwh.csv
   
   Genera: bess_ano_2024.csv ← SALIDA de BESS

Paso 2: Ejecutar BALANCE.PY
   python -m src.dimensionamiento.oe2.balance_energetico.balance
   
   Lee:   bess_ano_2024.csv ← ENTRADA para BALANCE
   
   Genera: 16 gráficas PNG ← SALIDA de BALANCE

"""

print(respuesta)

print("="*90)
print()
