"""
BASELINE COMPARISON GUIDE - DUAL SCENARIOS

================================================================================
DOS BASELINES PARA ENTENDER EL IMPACTO DE SOLAR EN OE3
================================================================================

BASELINE 1: Sin Control, Sin BESS, CON Solar ⭐ (ACTUAL - Lo que tenemos ahora)
├─ Mall: 100 kW constante
├─ EVs: 50 kW constante  
├─ Solar: 4,050 kWp = ~8M kWh/año
├─ BESS: Desactivado
└─ RL Agents: NO (demanda constante)

RESULTADO: ~190,000 kg CO₂/año (grid imports ~420,000 kWh)

────────────────────────────────────────────────────────────────────────────────

BASELINE 2: Sin Control, Sin BESS, SIN Solar 🔴 (NUEVO - Peor escenario)
├─ Mall: 100 kW constante
├─ EVs: 50 kW constante
├─ Solar: 0 kWp = 0 kWh/año
├─ BESS: Desactivado
└─ RL Agents: NO (demanda constante)

RESULTADO: ~640,000 kg CO₂/año (grid imports ~1.4M kWh)

────────────────────────────────────────────────────────────────────────────────

IMPACTO SOLAR: Diferencia entre Baseline 1 y Baseline 2
├─ Grid reduction: 420k → 1.4M kWh (380% más sin solar)
├─ CO₂ reduction: 190k → 640k kg (237% más sin solar)
└─ Solar value: ~450k kg CO₂/año EVITADO por los 4,050 kWp

================================================================================
EJECUCIÓN
================================================================================

1. EJECUTAR AMBOS BASELINES:

   python -m scripts.run_dual_baselines --config configs/default.yaml

   Duración: ~20 segundos (2 × 10 sec cada uncontrolled)

────────────────────────────────────────────────────────────────────────────────

2. ARCHIVOS GENERADOS:

   outputs/baselines/
   ├── with_solar/
   │   ├── result_uncontrolled_with_solar.json
   │   └── timeseries_uncontrolled_with_solar.csv
   ├── without_solar/
   │   ├── result_uncontrolled_without_solar.json
   │   └── timeseries_uncontrolled_without_solar.csv
   ├── baseline_comparison.csv
   └── baseline_comparison.json

────────────────────────────────────────────────────────────────────────────────

3. INTERPRETAR RESULTADOS:

   COLUMNA "CON Solar":    Baseline 1 - Lo que pasará CON nuestro sistema
   COLUMNA "SIN Solar":    Baseline 2 - Comparativa sin generación solar

   DIFERENCIA = Valor real de tener 4,050 kWp instalados

────────────────────────────────────────────────────────────────────────────────

4. COMPARAR CON AGENTES RL:

   Luego de entrenar SAC, PPO, A2C:

   Agent CO₂ vs Baseline 1 (CON Solar):
   % Mejora = (CO₂_Baseline1 - CO₂_Agent) / CO₂_Baseline1 × 100%

   Ejemplo:
   • SAC: -26% → 140,000 kg CO₂/año
   • PPO: -29% → 135,000 kg CO₂/año
   • A2C: -24% → 144,000 kg CO₂/año

================================================================================
REFERENCIAS
================================================================================

IQUITOS CONTEXT (informacional):
• Grid total Iquitos: 290,000 tCO₂/año
• Transporte combustión: 258,250 tCO₂/año
• Total ciudad: 548,250 tCO₂/año

OE3 BASELINES:
• Con solar: ~190 tCO₂/año (0.035% del grid Iquitos)
• Sin solar: ~640 tCO₂/año (0.11% del grid Iquitos)

OE3 RL AGENTS (esperado):
• SAC: ~140 tCO₂/año (-26% vs baseline con solar)
• PPO: ~135 tCO₂/año (-29% vs baseline con solar)
• A2C: ~144 tCO₂/año (-24% vs baseline con solar)

================================================================================
"""

# Scriptable version - ver archivo run_dual_baselines.py
