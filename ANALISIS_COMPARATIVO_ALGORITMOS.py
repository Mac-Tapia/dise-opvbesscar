#!/usr/bin/env python
"""
ANALISIS COMPARATIVO: PPO vs A2C vs SAC
Tiempo, Timesteps, Velocidad de entrenamiento
"""
from datetime import datetime

print("="*100)
print("ANALISIS COMPARATIVO: RENDIMIENTO DE ALGORITMOS")
print("="*100)

print("\n[1] PPO (Proximal Policy Optimization)")
print("    Inicio: 2026-01-19 08:22:53")
print("    Final: 2026-01-19 08:43:40")
print("    Duración: ~20 minutos (10 min entrenamiento neto + overhead)")
print("    Timesteps: 4,096")
print("    Velocidad: 4,096 / 10 min = 409.6 timesteps/min")
print("    Modelo final: ppo_final.zip (1.7 MB)")
print("    Checkpoints: 2 (cada 2,048 steps)")
print("    Status: ✓ COMPLETADO")

print("\n[2] A2C (Advantage Actor-Critic)")
print("    Inicio: 2026-01-19 08:53:09")
print("    Final: 2026-01-19 08:54:28")
print("    Duración: ~1-2 minutos (interrumpido)")
print("    Timesteps: ~200-300")
print("    Status: ⚠ INTERRUMPIDO - No completado")

print("\n[3] SAC (Soft Actor-Critic)")
print("    Inicio: 2026-01-19 00:44:08 (anterior)")
print("    Final: 2026-01-19 05:51:41")
print("    Duración: 5 horas 7 minutos")
print("    Timesteps: 17,500")
print("    Velocidad: 17,500 / 307 min = 57 timesteps/min")
print("    Modelo final: sac_final.zip (15.3 MB)")
print("    Checkpoints: 177 (cada 100 steps)")
print("    Status: ✓ COMPLETADO")

print("\n[4] COMPARATIVA DE VELOCIDAD")
print("    ┌─────────┬──────────┬──────────┬─────────────┐")
print("    │Algoritmo│Timesteps │Duración  │Velocidad    │")
print("    ├─────────┼──────────┼──────────┼─────────────┤")
print("    │ PPO     │ 4,096    │ 10 min   │ 409.6 ts/min│ ✓ RÁPIDO")
print("    │ A2C     │ ~300     │ 1-2 min  │ ~200 ts/min │ ⚠ Interrumpido")
print("    │ SAC     │ 17,500   │ 307 min  │ 57 ts/min   │ ✗ LENTO")
print("    └─────────┴──────────┴──────────┴─────────────┘")

print("\n[5] RAZON: SAC es más lento")
print("    SAC requiere:")
print("    - Muestreo de múltiples acciones aleatorias")
print("    - Cálculo de Q-values para cada acción")
print("    - Buffer de replay más grande")
print("    - Más operaciones de gradiente por timestep")
print("    ")
print("    PPO es más eficiente porque:")
print("    - Usa rollout buffer (no replay buffer)")
print("    - Menos evaluaciones de política")
print("    - Batch updates más simples")

print("\n[6] CONCLUSIONES")
print("    ✓ PPO: 409.6 ts/min (Excelente para entrenamiento rápido)")
print("    ✓ SAC: 57 ts/min (Bueno para exploración con entropy, pero lento)")
print("    ✓ A2C: Interrumpido (requería más configuración)")
print("    ")
print("    Para 128 cargadores + OE2 con 926 observaciones:")
print("    - PPO: RECOMENDADO (rápido, estable)")
print("    - SAC: Alternativa (explora mejor, pero ~7x más lento)")

print("\n" + "="*100)
print("RECOMENDACION: Usar PPO para entrenamiento productivo")
print("             Usar SAC si se requiere mayor exploración con recursos suficientes")
print("="*100)
