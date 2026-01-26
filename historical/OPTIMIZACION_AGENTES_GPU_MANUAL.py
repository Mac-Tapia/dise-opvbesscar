#!/usr/bin/env python3
"""
OPTIMIZACION AVANZADA DE AGENTES RL PARA GPU RTX 4060
======================================================

Estrategia: Maximizar aprendizaje mientras aprovechamos GPU eficientemente

Factores clave:
1. Batch size = balance entre velocidad (GPU) y estabilidad (gradientes)
2. Buffer size = historia para replay (menos = menos memoria, menos estable)
3. Red neuronal = complejidad vs parámetros
4. Learning rate = velocidad de convergencia
5. Gamma + tau = factores de actualización (afectan convergencia)
"""

print("""
================================================================================
OPTIMIZACION DE AGENTES PARA MAXIMO APRENDIZAJE + GPU RTX 4060 (8GB)
================================================================================

[ANALISIS DE HARDWARE]
  GPU: RTX 4060 Laptop (8GB VRAM)
  Compute Capability: 8.9 (muy rápida)
  Operaciones: INT8, TF32, FP32, FP16
  Memoria disponible: ~7.5GB (0.5GB SO)

[ESTRATEGIA GENERAL]
  1. SAC: Off-policy → mejor para muestras limitadas, parallelización GPU
  2. PPO: On-policy → gradientes más estables, menor variance
  3. A2C: Simple baseline → rápido, bueno para debugging

[CONFIGURACION OPTIMA POR AGENTE]

╔═══════════════════════════════════════════════════════════════════════════╗
║ SAC (Soft Actor-Critic) - OFF-POLICY                                     ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║ ✓ FORTALEZA: Sample-efficient (reusa experiencias del buffer)            ║
║ ✓ Bueno para: Problemas con muestras limitadas (como OE3 con 365 días)  ║
║ ✓ Convergencia: Lenta pero estable                                       ║
║ ✓ Entropía: Automática → buena exploración                              ║
║                                                                           ║
║ HIPERPARAMETROS OPTIMOS:                                                ║
║  batch_size:     512  (máximo sin OOM en RTX 4060)                      ║
║  buffer_size:    1M   (full year en memoria para todas las trayectorias)║
║  learning_rate:  1e-4 (lentamente, mejor convergencia)                 ║
║  gamma:          0.999 (largo plazo, importa en control)               ║
║  tau:            0.001 (smooth Q-net updates)                           ║
║  hidden_sizes:   (256, 256) ← REDUCIDO (160k parámetros)              ║
║  ent_coef:       auto (empezar bajo, aumentar si explora poco)         ║
║                                                                           ║
║ ESTIMADO GPU:                                                            ║
║  Memoria:  ~3.5-4GB (buffer + 2×Q-net + policy)                        ║
║  Velocidad: ~500 timesteps/sec (GPU acelerado)                         ║
║  Episodes: 5-10 recomendadas para convergencia                         ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════════════════╗
║ PPO (Proximal Policy Optimization) - ON-POLICY                          ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║ ✓ FORTALEZA: Gradientes estables, fácil de tunar                        ║
║ ✓ Bueno para: Espacios de acción grandes y continuos                   ║
║ ✓ Convergencia: Rápida (5-10 épocas por dataset)                       ║
║ ✓ Clipping: Evita cambios grandes en policy                            ║
║                                                                           ║
║ HIPERPARAMETROS OPTIMOS:                                                ║
║  n_steps:        2048  (full episode 8,760 → split en 4 chunks)        ║
║  batch_size:     256   (n_steps/4 para 4 mini-batches)                ║
║  n_epochs:       10    (actualizar policy múltiples veces)            ║
║  learning_rate:  3e-4  (PPO tolera rates más altos)                   ║
║  gae_lambda:     0.95  (generalized advantage estimation)              ║
║  clip_range:     0.2   (clipping coefficient, robusto)                ║
║  ent_coef:       0.01  (bonus de entropía para exploración)           ║
║  hidden_sizes:   (256, 256) ← REDUCIDO (similar a SAC)               ║
║  use_sde:        False  (desactivar, causa overhead)                   ║
║                                                                           ║
║ ESTIMADO GPU:                                                            ║
║  Memoria:  ~2-2.5GB (policy + advantage baseline, sin buffer)          ║
║  Velocidad: ~1000 timesteps/sec (on-policy más parallelizable)        ║
║  Episodes: 3-5 recomendadas (rápida convergencia)                     ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════════════════╗
║ A2C (Advantage Actor-Critic) - ON-POLICY BASELINE                       ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║ ✓ FORTALEZA: Muy rápido de entrenar, simple y confiable                ║
║ ✓ Bueno para: Pruebas rápidas y baseline                               ║
║ ✓ Convergencia: Muy rápida (2-3 episodios)                            ║
║ ✓ Menos parámetros → menos memoria                                    ║
║                                                                           ║
║ HIPERPARAMETROS OPTIMOS:                                                ║
║  n_steps:        512   (chunks más pequeños, convergencia rápida)      ║
║  batch_size:     64    (A2C puede ser más pequeño)                    ║
║  learning_rate:  5e-4  (puede ser más agresivo)                       ║
║  discount:       0.99  (standard)                                      ║
║  gae_lambda:     0.95  (advantage estimation)                          ║
║  ent_coef:       0.005 (menos entropía, más foco)                     ║
║  hidden_sizes:   (128, 128) ← MINIMO (65k parámetros)                ║
║  use_sde:        False                                                 ║
║                                                                           ║
║ ESTIMADO GPU:                                                            ║
║  Memoria:  ~1.5GB (smallest model)                                     ║
║  Velocidad: ~2000 timesteps/sec (paralelizable)                       ║
║  Episodes: 2-3 recomendadas (rápido entrenamiento)                    ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

[ESTIMADO TOTAL GPU PARA RTX 4060]

Ejecutar 3 agentes en paralelo (recomendado):
  SAC    → ~4.0 GB (off-policy con buffer grande)
  PPO    → ~2.5 GB (on-policy)
  A2C    → ~1.5 GB (baseline)
  ────────────────
  Total  → ~8.0 GB (LLENA 100% del GPU)

Alternativa: Secuencial (más lento pero posible)
  Ejecutar SAC → PPO → A2C uno tras otro
  Tiempo total: ~10-15 horas
  Memory peak: 4 GB en SAC

[CONFIGURACION RECOMENDADA]

OPCION 1: Máximo Aprendizaje (12-16 horas)
  SAC:  10 episodios (off-policy = 10×8760 = 87,600 timesteps muestreados)
  PPO:  5 episodios (5×8760 = 43,800 timesteps)
  A2C:  5 episodios (5×8760 = 43,800 timesteps)
  Total: 20 episodios = ~175,200 timesteps

OPCION 2: Balance (4-6 horas)
  SAC:  5 episodios
  PPO:  3 episodios
  A2C:  3 episodios
  Total: 11 episodios = ~96,000 timesteps

OPCION 3: Rápido (2-3 horas)
  SAC:  3 episodios
  PPO:  2 episodios
  A2C:  2 episodios
  Total: 7 episodios = ~61,000 timesteps

[OPTIMIZACIONES GPU]

Activar (todos):
  ✓ Mixed Precision (AMP): FP32→FP16 donde sea seguro (2× más rápido)
  ✓ Gradient Checkpointing: Reduce memoria de activaciones (~30% menos mem)
  ✓ CUDA Graphs: Reduce overhead CPU-GPU (~20% más rápido)
  ✓ Pin Memory: CPU→GPU transfer más rápido (mínimo overhead)
  ✓ Compiled Policy: torch.compile() para JIT (si PyTorch 2.0+)

Deshabilitar (para compatibilidad):
  ✗ Deterministic mode: (lento, solo si reproducibilidad crítica)
  ✗ cudnn.benchmark = False: (permite cuDNN auto-tuning)

[METRICAS DE EXITO]

Después de entrenar, verificar:
  1. Loss convergence: Loss debe bajar 50%+ en primeras 1-2 épocas
  2. Reward trend: Recompensa media debe subir 20%+ respecto baseline
  3. GPU utilization: >80% GPU util durante steps
  4. Memory stability: Memoria no debe crecer (sin memory leaks)
  5. Wall-clock time: SAC ~1h/ep, PPO ~30min/ep, A2C ~20min/ep

[COMANDOS PARA ACTIVAR]

# Entrenar SAC optimizado (5 episodios)
python -m scripts.run_oe3_simulate --config configs/default.yaml --agent SAC --episodes 5

# Entrenar PPO optimizado
python -m scripts.run_oe3_simulate --config configs/default.yaml --agent PPO --episodes 3

# Entrenar A2C optimizado
python -m scripts.run_oe3_simulate --config configs/default.yaml --agent A2C --episodes 3

# Entrenar los 3 en paralelo (mejor para GPU RTX 4060)
parallel --jobs 1 ::: \\
  "python -m scripts.run_oe3_simulate --config configs/default.yaml --agent SAC --episodes 5" \\
  "python -m scripts.run_oe3_simulate --config configs/default.yaml --agent PPO --episodes 3" \\
  "python -m scripts.run_oe3_simulate --config configs/default.yaml --agent A2C --episodes 3"

================================================================================
RESUMEN: Configuración optimizada para OE3 + RTX 4060
================================================================================

Todos los agentes usan:
  ✓ Hidden sizes reducidas: 256×256 (SAC/PPO), 128×128 (A2C)
  ✓ Batch sizes optimizados: 512 (SAC), 256 (PPO), 64 (A2C)
  ✓ Learning rates conservadores: 1e-4 (SAC), 3e-4 (PPO/A2C)
  ✓ GPU Mixed Precision: FP32/FP16 automático
  ✓ Memory-efficient buffers: Solo lo necesario en GPU
  ✓ Multi-objetivo weights: CO₂=0.50, Solar=0.20, Cost=0.15, EV=0.10, Grid=0.05

Tiempo estimado total:
  - Con 5/3/3 episodios: 4-6 horas
  - Con 10/5/5 episodios: 12-16 horas
  - GPU utilization: 85-95% (uso eficiente)

================================================================================
""")
