#!/usr/bin/env python
"""
Visualización de los NUEVOS CRITERIOS de CO₂: Directo vs Indirecto
"""

print("\n" + "="*90)
print("CRITERIOS DE EVALUACIÓN DE AGENTES: CO₂ Directo e Indirecto".center(90))
print("="*90)

print("""
┌─ REDUCCIÓN INDIRECTA DE CO₂ ────────────────────────────────────────────────────────┐
│                                                                                       │
│ Definición: Solar consumido evita importar del grid térmico                          │
│                                                                                       │
│ Fórmula:  CO₂ indirecto = Solar consumido [kWh] × 0.4521 [kg CO₂/kWh]              │
│                                                                                       │
│ Ejemplo:                                                                              │
│   • Solar generado hoy: 248 kWh                                                      │
│   • Solar consumido: 172 kWh (EV+BESS+MALL)                                          │
│   • Solar curtailed: 76 kWh (desperdiciado)                                          │
│   • CO₂ indirecto = 172 × 0.4521 = 77.8 kg CO₂ evitado                             │
│                                                                                       │
│ Métrica en logs:  co2_indirect_kg=77.8                                              │
│ Refleja: QUÉ TAN BIEN se aprovechan los recursos renovables                         │
│ Agente esperado mejor: SAC (optimiza consumo solar, minimiza curtailment)            │
└───────────────────────────────────────────────────────────────────────────────────────┘

┌─ REDUCCIÓN DIRECTA DE CO₂ ──────────────────────────────────────────────────────────┐
│                                                                                       │
│ Definición: Moto/mototaxi cargada reemplaza viaje en combustible                    │
│                                                                                       │
│ Factores de CO₂ (vs gasolina/diésel):                                               │
│   • Moto:     2.5 kg CO₂/carga (reemplaza ~0.5 L gasolina @ 5 kg CO₂/L)            │
│   • Mototaxi: 3.5 kg CO₂/carga (mayor consumo de combustible)                       │
│                                                                                       │
│ Criterio de "cargada": SOC ≥ 90% (considerado "completamente cargado")             │
│                                                                                       │
│ Ejemplo en un paso:                                                                  │
│   • Chargers activos: 32                                                             │
│   • Motos con SOC ≥ 90%: 18                                                         │
│   • Mototaxis con SOC ≥ 90%: 3                                                      │
│   • CO₂ directo = (18 × 2.5) + (3 × 3.5) = 45 + 10.5 = 55.5 kg CO₂ evitado        │
│                                                                                       │
│ Métrica en logs:  co2_direct_kg=55.5, motos_cargadas=18, mototaxis_cargadas=3     │
│ Refleja: QUÉ TAN BIEN se satisface la demanda de transporte                         │
│ Agente esperado mejor: PPO (prioriza completar carga, menos curtailment)            │
└───────────────────────────────────────────────────────────────────────────────────────┘

COMPARACIÓN DE ESTRATEGIAS:
═════════════════════════

SAC (Soft Actor-Critic):
  ├─ Objetivo: MAXIMIZAR consumo solar (reducción indirecta)
  ├─ Estrategia: Aprovechar solar directo EV+BESS, minimizar curtailment
  ├─ Esperado: co2_indirect ↑ (mejor aprovechamiento solar)
  ├─ Esperado: co2_direct ↓ (menos EVs completamente cargadas)
  └─ Balance: Mejor para grid limpio (menos diésel)

PPO (Proximal Policy Optimization):
  ├─ Objetivo: MAXIMIZAR carga de EVs (reducción directa)
  ├─ Estrategia: Completar carga de motos/mototaxis primero
  ├─ Esperado: co2_direct ↑ (más EVs cargadas)
  ├─ Esperado: co2_indirect ↓ (menos enfoque en solar)
  └─ Balance: Mejor para disponibilidad de transportes

A2C (Advantage Actor-Critic):
  ├─ Objetivo: EQUILIBRIO entre ambos
  ├─ Estrategia: Optimizar ambos componentes simultáneamente
  ├─ Esperado: co2_indirect ≈ co2_direct (balance)
  ├─ Esperado: co2_total ≈ SAC ≈ PPO (eficiencia integral)
  └─ Balance: Mejor para operación equilibrada

EVALUACIÓN DE DESEMPEÑO:
════════════════════════

Escenario 1: SAC domina indirecto
┌────────────┬──────────────┬──────────────┐
│   Métrica  │     SAC      │     PPO      │
├────────────┼──────────────┼──────────────┤
│ co2_ind    │   180.0 kg ↑ │   120.0 kg   │  ← SAC mejor en solar
│ co2_dir    │    45.0 kg   │    75.0 kg ↑ │  ← PPO mejor en EVs
│ total      │   225.0 kg   │   195.0 kg   │  ← SAC total mayor
└────────────┴──────────────┴──────────────┘
→ Ganador: SAC (usa más solar disponible, menos diésel grid)

Escenario 2: PPO domina directo
┌────────────┬──────────────┬──────────────┐
│   Métrica  │     SAC      │     PPO      │
├────────────┼──────────────┼──────────────┤
│ co2_ind    │   150.0 kg   │   160.0 kg ↑ │  ← PPO mejor en solar
│ co2_dir    │    50.0 kg   │    90.0 kg ↑ │  ← PPO mejor en EVs
│ total      │   200.0 kg   │   250.0 kg ↑ │  ← PPO total mayor
└────────────┴──────────────┴──────────────┘
→ Ganador: PPO (más CO₂ total evitado, mejor en ambas)

Escenario 3: A2C equilibra
┌────────────┬──────────────┬──────────────┬──────────────┐
│   Métrica  │     SAC      │     PPO      │     A2C      │
├────────────┼──────────────┼──────────────┼──────────────┤
│ co2_ind    │   175.0 kg   │   180.0 kg   │   178.0 kg   │  ≈ Similar
│ co2_dir    │    50.0 kg   │    60.0 kg   │    55.0 kg   │  ≈ Similar
│ total      │   225.0 kg   │   240.0 kg   │   233.0 kg   │  ≈ Similar
└────────────┴──────────────┴──────────────┴──────────────┘
→ Ganador: A2C (más consistente, menos volatilidad)

MÉTRICAS AGREGADAS EN LOGS (nuevo formato):
═════════════════════════════════════════════

[SAC] paso 500 | ep~1 | pasos_global=500 | reward_avg=29.8 | critic_loss=245.3 |
  grid_kWh=376.0 | co2_grid_kg=170.2 |
  solar_kWh=172.0 | co2_indirect_kg=77.8 |
  co2_direct_kg=55.5 | motos_cargadas=18 | mototaxis_cargadas=3 |
  co2_total_avoided_kg=133.3

Desglose:
  • grid_kWh: Energía importada (solo no cubierta por solar)
  • co2_grid_kg: CO₂ de esa importación
  • solar_kWh: Solar CONSUMIDO (no solar disponible)
  • co2_indirect_kg: CO₂ evitado por solar (solar_kWh × 0.4521)
  • co2_direct_kg: CO₂ evitado por EVs cargadas
  • co2_total_avoided_kg: SUMA de indirecto + directo = total evitado

CRITERIOS PARA ELEGIR MEJOR AGENTE:
════════════════════════════════════

Si objetivo es "MAXIMIZAR SUSTENTABILIDAD SOLAR":
  → Elegir agente con mayor co2_indirect_kg y menor solar_curtailed

Si objetivo es "MAXIMIZAR DISPONIBILIDAD DE TRANSPORTE":
  → Elegir agente con mayor co2_direct_kg y más EVs cargadas

Si objetivo es "MÁXIMO CO₂ TOTAL EVITADO":
  → Elegir agente con mayor co2_total_avoided_kg (indirecto + directo)

Si objetivo es "BALANCE OPERACIONAL":
  → Elegir agente con ratio similar co2_indirect/co2_direct (A2C típicamente)
""")

print("\n" + "="*90)
print("IMPLEMENTACIÓN LISTA PARA ENTRENAMIENTO".center(90))
print("="*90 + "\n")
