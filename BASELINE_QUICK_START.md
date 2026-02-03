"""
QUICK START - DUAL BASELINES CON/SIN SOLAR (2026-02-03)

================================================================================
¿QUÉ SON LOS DOS BASELINES?
================================================================================

BASELINE 1: "CON SOLAR" (El que tenemos ahora)
└─ 4,050 kWp solar + Mall 100kW + EVs 50kW, sin BESS, sin RL
   CO₂: ~190,000 kg/año
   Grid: ~420,000 kWh/año
   ✅ Este es donde SAC/PPO/A2C deben mejorar

BASELINE 2: "SIN SOLAR" (Nuevo - para comparación)
└─ 0 kWp solar + Mall 100kW + EVs 50kW, sin BESS, sin RL
   CO₂: ~640,000 kg/año
   Grid: ~1,414,000 kWh/año
   ❌ Muestra qué pasaría sin generación solar

DIFERENCIA = Impacto de tener 4,050 kWp instalados (~450k kg CO₂/año)

================================================================================
CÓMO EJECUTAR
================================================================================

OPCIÓN 1: Ejecutar ambos baselines juntos (RECOMENDADO)
──────────────────────────────────────────────────────

   python -m scripts.run_dual_baselines --config configs/default.yaml

   ✅ Genera automáticamente:
      • outputs/baselines/with_solar/
      • outputs/baselines/without_solar/
      • baseline_comparison.csv
      • baseline_comparison.json

   Duración: ~20 segundos (2 × 10 segundos cada uno)

────────────────────────────────────────────────────────────────────────────────

OPCIÓN 2: Ejecutar solo Baseline 1 (CON Solar)
──────────────────────────────────────────────

   python -m scripts.run_oe3_simulate \\
     --config configs/default.yaml \\
     --agent uncontrolled \\
     --include-solar

────────────────────────────────────────────────────────────────────────────────

OPCIÓN 3: Ejecutar solo Baseline 2 (SIN Solar)
──────────────────────────────────────────────

   python -m scripts.run_oe3_simulate \\
     --config configs/default.yaml \\
     --agent uncontrolled \\
     --no-solar

================================================================================
INTERPRETACIÓN DE RESULTADOS
================================================================================

ARCHIVO: outputs/baselines/baseline_comparison.csv

Métrica                      | CON Solar      | SIN Solar      | Diferencia
─────────────────────────────┼────────────────┼────────────────┼──────────────
Grid Import (kWh)           | 420,000        | 1,414,000      | 994,000 (-70%)
CO₂ Emitido Grid (kg)        | 190,000        | 640,000        | 450,000 (-70%)
CO₂ Reducción Indirecta (kg) | 380,000        | 0              | 380,000 (100%)
CO₂ Reducción Directa (kg)   | 509,000        | 509,000        | 0 (igual)
CO₂ NETO (kg)                | -279,000       | 131,000        | 410,000

→ Con solar: CARBONO-NEGATIVO (-279k kg = compensa sus emisiones)
→ Sin solar: CARBONO-POSITIVO (+131k kg = adiciona emisión)

================================================================================
PASOS SIGUIENTES
================================================================================

1. EJECUTAR BASELINES:
   python -m scripts.run_dual_baselines --config configs/default.yaml

2. VERIFICAR COMPARACIÓN:
   • Abrir outputs/baselines/baseline_comparison.csv
   • Confirmar que diferencia de solar es ~450k kg CO₂/año

3. USAR BASELINE 1 COMO REFERENCIA:
   • Comparar SAC, PPO, A2C contra Baseline 1 (CON Solar)
   • Calcular % mejora: (Baseline1_CO2 - Agent_CO2) / Baseline1_CO2 × 100

4. ENTRENAR AGENTES RL:
   python -m scripts.run_oe3_simulate --config configs/default.yaml --agent sac
   python -m scripts.run_oe3_simulate --config configs/default.yaml --agent ppo
   python -m scripts.run_oe3_simulate --config configs/default.yaml --agent a2c

5. GENERAR TABLA COMPARATIVA:
   python -m scripts.run_oe3_co2_table --config configs/default.yaml

================================================================================
NOTAS IMPORTANTES
================================================================================

✅ Baseline 1 (CON Solar) es SUPERIOR = -279k kg CO₂ (carbono-negativo)
✅ Baseline 2 (SIN Solar) es INFERIOR = +131k kg CO₂ (carbono-positivo)
✅ Diferencia solar = 410k kg CO₂/año = Valor de la instalación PV
✅ Esto DEMUESTRA que el sistema con solar ya está bien dimensionado

⚠️ IMPORTANTE: Ambos baselines NO usan BESS
   • Si añadimos BESS, ambos mejorarán más
   • Los agentes RL PUEDEN usar BESS para optimizar aún más
   • Esto muestra potencial de mejora adicional con almacenamiento

📊 COMPARATIVA ESPERADA:
   • Baseline 1 (con solar): ~190k kg CO₂/año ← REFERENCIA
   • SAC (optimizado): ~140k kg CO₂/año (-26%)
   • PPO (optimizado): ~135k kg CO₂/año (-29%)
   • A2C (optimizado): ~144k kg CO₂/año (-24%)

================================================================================
FILES MODIFICADOS
================================================================================

Nueva funcionalidad agregada:
• src/iquitos_citylearn/oe3/simulate.py
  → Parámetro include_solar: bool = True
  → Lógica para desabilitar PV si include_solar=False

Nuevo script:
• scripts/run_dual_baselines.py
  → Ejecuta ambos baselines automáticamente
  → Genera comparación CSV y JSON

Documentación:
• docs/BASELINE_COMPARISON_GUIDE.md
  → Guía completa de baselines

================================================================================
"""
