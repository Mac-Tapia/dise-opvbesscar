#!/usr/bin/env python3
r"""
QUICK REFERENCE - Training RL Agents
====================================

Copy-paste commands para iniciar entrenamiento rápidamente.
"""

# ============================================================================
# 1. SETUP INICIAL (ejecutar una vez)
# ============================================================================

# En PowerShell (Windows):
# python -m venv .venv
# .venv\Scripts\Activate.ps1
# pip install -r requirements.txt
# pip install -r requirements-training.txt

# En Bash (Linux/Mac):
# python -m venv .venv
# source .venv/bin/activate
# pip install -r requirements.txt
# pip install -r requirements-training.txt

# ============================================================================
# 2. VALIDACIÓN PRE-ENTRENAMIENTO
# ============================================================================

# Verificar que todo está configurado:
# python src/iquitos_citylearn/oe3/agents/validate_training_env.py

# Debe mostrar:
# ✓ Agents imported successfully
# ✓ Rewards imported successfully
# ✓ GPU available: (device name) OR ⚠ GPU not available; using CPU
# ✓ Checkpoint dir: (path)
# ✓ All checks passed! Ready to train.

# ============================================================================
# 3. CONSTRUIR DATASET (una sola vez, antes de entrenar)
# ============================================================================

# Build CityLearn dataset:
# python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# Debe crear: outputs/schema_TIMESTAMP.json
# Valida: 128 chargers, 4 sockets each = 512 outlets

# ============================================================================
# 4. ENTRENAR AGENTES
# ============================================================================

# OPCIÓN A: QUICK TRAINING (5 episodios, ~5 min, para testing)
# python scripts/train_quick.py --device cuda --episodes 5

# Con CPU si no tiene GPU:
# python scripts/train_quick.py --device cpu --episodes 5

# Con seed específico (reproducible):
# python scripts/train_quick.py --device cuda --episodes 5 --seed 42


# OPCIÓN B: FULL TRAINING (50 episodios, ~50 min, para resultados)
# python scripts/train_agents_serial.py --device cuda --episodes 50

# Con CPU:
# python scripts/train_agents_serial.py --device cpu --episodes 50

# Solo entrenar SAC (no PPO/A2C):
# python scripts/train_agents_serial.py --device cuda --episodes 50 --agent SAC

# Reanudar desde checkpoint anterior:
# python scripts/train_agents_serial.py --device cuda --episodes 50 --resume

# ============================================================================
# 5. MONITOREAR ENTRENAMIENTO (en otra terminal)
# ============================================================================

# Monitoreo en tiempo real (actualiza cada 5 seg):
# python scripts/monitor_training_live_2026.py

# Muestra: Agent | Episode | Reward | Total Timesteps | Status

# ============================================================================
# 6. RESULTADOS & COMPARATIVA
# ============================================================================

# Ver resultados baseline vs RL:
# python -m scripts.run_oe3_co2_table --config configs/default.yaml

# Genera: COMPARACION_BASELINE_VS_RL.txt
# Muestra reducción de CO2 por agente

# Ver checkpoints guardados:
# ls -la checkpoints/SAC
# ls -la checkpoints/PPO
# ls -la checkpoints/A2C

# Ver logs de entrenamiento:
# ls -la analyses/logs/

# ============================================================================
# 7. TROUBLESHOOTING
# ============================================================================

# PROBLEMA: "Schema not found"
# SOLUCIÓN:
#     python -m scripts.run_oe3_build_dataset --config configs/default.yaml

# PROBLEMA: "GPU out of memory"
# SOLUCIÓN:
#     python scripts/train_quick.py --device cpu --episodes 5  # usar CPU
#     O ajustar n_steps en src/iquitos_citylearn/oe3/agents/ppo_sb3.py

# PROBLEMA: "128 chargers not found"
# SOLUCIÓN:
#     Verificar: data/interim/oe2/chargers/individual_chargers.json
#     Debe contener exactamente 32 chargers

# PROBLEMA: "Agentes no se importan"
# SOLUCIÓN:
#     python -c "from src.iquitos_citylearn.oe3.agents import PPOAgent; print('OK')"
#     Si falla, revisar PYTHONPATH

# PROBLEMA: "Reward es NaN"
# SOLUCIÓN:
#     Verificar que pesos sumen 1.0:
#     python -c "from src.iquitos_citylearn.oe3.rewards import MultiObjectiveWeights; print(sum([0.50, 0.20, 0.10, 0.10, 0.10]))"

# ============================================================================
# 8. PARÁMETROS AJUSTABLES
# ============================================================================

# AGENTES - Ubicación: src/iquitos_citylearn/oe3/agents/

# PPOConfig:
#     - train_steps: Pasos totales de entrenamiento (default: 1000000)
#     - n_steps: Experiencias por update (default: 2048)
#     - learning_rate: LR (default: 2.0e-4)
#     - batch_size: Batch size (default: 128)
#     - hidden_sizes: Capas ocultas (default: (1024, 1024))

# SACConfig:
#     - train_steps: Pasos totales (default: 1000000)
#     - learning_rate: LR (default: 3.0e-4)
#     - batch_size: Batch size (default: 256)
#     - use_sde: Stochastic dynamics (default: True)

# A2CConfig:
#     - train_steps: Pasos totales (default: 1000000)
#     - n_steps: Experiencias por update (default: 2048)
#     - learning_rate: LR (default: 1.5e-4)
#     - batch_size: Batch size (default: 128)

# REWARDS - Ubicación: src/iquitos_citylearn/oe3/rewards.py

# MultiObjectiveWeights:
#     - co2: Peso CO2 (default: 0.50) - PRIMARIO
#     - solar: Peso solar (default: 0.20) - SECUNDARIO
#     - cost: Peso costo (default: 0.10) - TERCIARIO
#     - ev_satisfaction: Peso EV (default: 0.10)
#     - grid_stability: Peso grid (default: 0.10)

#     NOTA: Deben sumar ~1.0 (auto-normalizados)

# ============================================================================
# 9. FLUJO TÍPICO DE UN DÍA
# ============================================================================

# Morning:
#     1. Activar venv
#     2. Run validation: python src/iquitos_citylearn/oe3/agents/validate_training_env.py
#     3. Start training: python scripts/train_quick.py --device cuda --episodes 5
#     4. In another terminal: python scripts/monitor_training_live_2026.py
#     5. Wait ~5 minutes

# Afternoon:
#     6. Once quick training completes, start full training:
#        python scripts/train_agents_serial.py --device cuda --episodes 50
#     7. Monitorear en background

# Evening:
#     8. Check results: python -m scripts.run_oe3_co2_table --config configs/default.yaml
#     9. Review COMPARACION_BASELINE_VS_RL.txt
#     10. Commit resultados si son buenos

# ============================================================================
# 10. ESPERADO VS REAL
# ============================================================================

# BASELINE (Sin Control RL):
#     CO2 emissions: ~10,200 kg/year
#     Grid import: ~41,300 kWh/year
#     Solar utilization: ~40%
#     EV satisfaction: 100%

# EXPECTED AFTER RL TRAINING:
#     SAC:
#         CO2: ~7,500 kg/year (-26%)
#         Solar utilization: ~65%
#         Training time: ~1 hour per episode

#     PPO:
#         CO2: ~7,200 kg/year (-29%)
#         Solar utilization: ~68%
#         Training time: ~1 hour per episode

#     A2C:
#         CO2: ~7,800 kg/year (-24%)
#         Solar utilization: ~60%
#         Training time: ~45 min per episode

# REALITY CHECK:
#     Si primeros episodios muestran rewards negativos o planos -> normal
#     Si nunca converge -> revisar reward signal, observables
#     Si muy lento -> reducir batch_size, usar CPU en GPU con 4GB

# ============================================================================
# 11. EMERGENCY COMMANDS
# ============================================================================

# Limpiar checkpoints y empezar desde cero:
# rm -r checkpoints  # Linux/Mac
# Remove-Item -Recurse checkpoints  # PowerShell

# Limpiar logs:
# rm -r analyses/logs  # Linux/Mac
# Remove-Item -Recurse analyses/logs  # PowerShell

# Matar entrenamiento (Ctrl+C en la terminal)
# Checkpoints se guardan automáticamente cada 1000 pasos
# Puedes reanudar con --resume

# Ver GPU status (durante entrenamiento):
# nvidia-smi  # Linux/Mac
# & 'nvidia-smi'  # PowerShell

# Ver consumo CPU/RAM:
# htop  # Linux (Ctrl+Q para salir)
# Get-Process | Sort CPU -Descending | Select -First 10  # PowerShell

# ============================================================================
# 12. PREGUNTAS FRECUENTES
# ============================================================================

# P: ¿Cuánto tiempo toma entrenar?
# R: ~5-10 minutos por episodio dependiendo del hardware.
#    5 episodios: ~25-50 min
#    50 episodios: ~4-8 horas

# P: ¿Necesito GPU?
# R: No, pero es ~10x más rápido. CPU funciona pero es lento.

# P: ¿Puedo parar y reanudar?
# R: Sí, presiona Ctrl+C. Checkpoints se guardan cada 1000 pasos.
#    Reanudar: python scripts/train_agents_serial.py --resume

# P: ¿Qué significa "reward NaN"?
# R: Indica problema en cálculo de rewards. Check:
#    - Pesos sumen 1.0
#    - Observables no sean infinito/NaN
#    - Solar timeseries cargado correctamente

# P: ¿Cómo ajusto el comportamiento del agente?
# R: Modifica pesos de rewards en src/iquitos_citylearn/oe3/rewards.py
#    Ej: para priorizar solar sobre CO2:
#    co2: 0.30, solar: 0.50

# P: ¿Cuáles son los mejores parámetros?
# R: Los defaults están tuned para Iquitos. Mantén igual salvo que:
#    - Memoria limitada: reduce n_steps de 2048 a 1024
#    - Más convergencia: aumenta train_steps de 1M a 2M

# ✓ Quick Reference ready. Copy-paste commands above to start training.
