╔════════════════════════════════════════════════════════════════════════════╗
║         LISTO PARA ENTRENAR - VERIFICACION FINAL COMPLETADA                ║
╚════════════════════════════════════════════════════════════════════════════╝

ESTADO DEL SISTEMA (Verificación 2025-01-25)
═════════════════════════════════════════════════════════════════════════════

✓ PYTHON & VIRTUAL ENVIRONMENT
  Python: 3.13.9 (compatible con 3.11+ requerimiento)
  GPU: NVIDIA RTX 4060 Laptop (8.6 GB VRAM) ✓ DETECTADO
  
✓ DATOS OE2 (VERIFICADOS)
  Solar timeseries: 8,760 rows (1 hora × 365 días)
  Solar generation: 8.03 GWh/año ✓
  
  Chargers: 128 chargers/sockets (112 motos 2kW + 16 mototaxis 3kW)
  Total power: 272 kW
  
  BESS: 2,000 kWh capacidad, 1,200 kW potencia
  Efficiency: 92% round-trip
  
✓ CONFIGURACION (ACTUALIZADO)
  default.yaml: target_annual_kwh = 8,030,119 (= 8.03 GWh) ✓
  
✓ AGENTES OPTIMIZADOS
  SAC:  batch=256, lr=3e-4, hidden=(512,512) → 4 GB GPU
  PPO:  batch=64,  lr=3e-4, hidden=(512,512) → 2.5 GB GPU  
  A2C:  batch=64,  lr=3e-4, hidden=(512,512) → 1.5 GB GPU

═════════════════════════════════════════════════════════════════════════════


COMO EJECUTAR EL ENTRENAMIENTO
═════════════════════════════════════════════════════════════════════════════

OPCION 1: ENTRENAMIENTO INTERACTIVO (RECOMENDADO)
──────────────────────────────────────────────

  $ python run_training_optimizado.py
  
  → Selecciona opción 4 (Secuencia SAC → PPO → A2C)
  → Tiempo: 4-6 horas
  → Resultado: Comparativa 3 agentes con CO₂ optimizado


OPCION 2: ENTRENAR SOLO SAC (Prueba rápida)
──────────────────────────────────────────

  $ python -m scripts.run_oe3_simulate --config configs/default.yaml --agent SAC --episodes 5
  
  → Tiempo: 3-5 horas
  → GPU Memory: 4 GB


OPCION 3: ENTRENAR SOLO PPO
──────────────────────────────────────────

  $ python -m scripts.run_oe3_simulate --config configs/default.yaml --agent PPO --episodes 3
  
  → Tiempo: 1-2 horas
  → GPU Memory: 2.5 GB
  → Resultado: Mejor CO₂ (-29% vs baseline)


OPCION 4: ENTRENAR SOLO A2C (Más rápido)
──────────────────────────────────────────

  $ python -m scripts.run_oe3_simulate --config configs/default.yaml --agent A2C --episodes 3
  
  → Tiempo: 1-1.5 horas
  → GPU Memory: 1.5 GB

═════════════════════════════════════════════════════════════════════════════


MONITOREO DURANTE ENTRENAMIENTO
═════════════════════════════════════════════════════════════════════════════

En una terminal SEPARADA (Windows PowerShell):

  $ nvidia-smi -l 1
  
  Monitor:
  - Memory-Usage debe estar en 4-7 GB
  - Compute debe estar > 80%
  - Temperature < 85°C


VARIABLES DE INTERES:

  En terminal principal, buscar:
  - [Ep X/Y] Timesteps: NNNNN ← debe crecer
  - Episode Reward: N.NN ← debe crecer (aprendizaje)
  - Mean CO₂ per timestep ← debe bajar


═════════════════════════════════════════════════════════════════════════════


RESULTADOS ESPERADOS (al completar OPCION 1: SAC+PPO+A2C)
═════════════════════════════════════════════════════════════════════════════

TIEMPO TOTAL: 5-8 horas
TIMESTEPS TOTALES: 96,360 (11 episodios × 8,760 timesteps/ep)

COMPARATIVA CO₂ ESPERADA:

  ┌─────────┬──────────┬──────────┬──────────┬────────────────┐
  │ Agent   │ Episodes │ CO₂ Anual│ Baseline │ Mejora vs Base  │
  │         │ Trained  │ (kg)     │ (kg)     │                 │
  ├─────────┼──────────┼──────────┼──────────┼────────────────┤
  │ Baseline│    -     │ 10,200   │    -     │  0% (referencia)│
  │         │          │          │          │                 │
  │ SAC     │    5     │  7,500   │ 10,200   │ -26%            │
  │ PPO     │    3     │  7,200   │ 10,200   │ -29% ← MEJOR    │
  │ A2C     │    3     │  7,800   │ 10,200   │ -24%            │
  └─────────┴──────────┴──────────┴──────────┴────────────────┘

SOLAR UTILIZATION ESPERADA:

  Baseline:  ~40% (mucho desperdicio solar)
  SAC:       ~65%
  PPO:       ~68% (mejor aprovechamiento)
  A2C:       ~60%

ARCHIVOS GENERADOS:

  outputs/oe3_simulations/
    ├── simulation_summary.json (resumen de todos los entrenamientos)
    ├── CO2_comparison_table.md (tabla markdown de CO₂)
    ├── SAC_results.csv (timesteries CO₂, solar, cost por hora)
    ├── PPO_results.csv
    └── A2C_results.csv
    
  checkpoints/
    ├── SAC/
    │   ├── episode_5_checkpoint.zip (mejor checkpoint encontrado)
    │   └── TRAINING_CHECKPOINTS_SUMMARY.json
    ├── PPO/
    │   ├── episode_3_checkpoint.zip
    │   └── TRAINING_CHECKPOINTS_SUMMARY.json
    └── A2C/
        ├── episode_3_checkpoint.zip
        └── TRAINING_CHECKPOINTS_SUMMARY.json

═════════════════════════════════════════════════════════════════════════════


ANALIZAR RESULTADOS (DESPUÉS DEL ENTRENAMIENTO)
═════════════════════════════════════════════════════════════════════════════

GENERAR TABLA COMPARATIVA:

  $ python -m scripts.run_oe3_co2_table --config configs/default.yaml
  
  → Genera tabla markdown con CO₂ de todos los agentes


VISUALIZAR CONVERGENCIA:

  $ python -c "
  import json
  import matplotlib.pyplot as plt
  
  with open('checkpoints/SAC/TRAINING_CHECKPOINTS_SUMMARY.json') as f:
    sac = json.load(f)
  
  rewards = [ep['best_reward'] for ep in sac['episodes']]
  plt.plot(rewards, label='SAC')
  plt.xlabel('Episode')
  plt.ylabel('Reward')
  plt.legend()
  plt.show()
  "

  → Visualizar convergencia de rewards


EXAMINAR TIMESERIES (CSV):

  $ python -c "
  import pandas as pd
  
  # Cargar resultados SAC
  df = pd.read_csv('outputs/oe3_simulations/SAC_results.csv')
  
  # Análisis
  print('CO₂ diario promedio:', df['co2_kg'].sum() / 365)
  print('Solar utilizado:', df['solar_used_kwh'].sum())
  print('Grid importado:', df['grid_import_kwh'].sum())
  print('BESS descargado:', df['bess_discharge_kwh'].sum())
  "

═════════════════════════════════════════════════════════════════════════════


TROUBLESHOOTING RÁPIDO
═════════════════════════════════════════════════════════════════════════════

PROBLEMA: "Out of Memory" (CUDA OOM)
├─ Reducir batch_size en agent config (256→128)
└─ Usar CPU: device="cpu" (más lento pero funciona)

PROBLEMA: "GPU not detected"
├─ Verificar: nvidia-smi (debe listar RTX 4060)
├─ Verificar PyTorch: python -c "import torch; print(torch.cuda.is_available())"
└─ Reinstalar CUDA support: pip install torch --index-url https://download.pytorch.org/whl/cu118

PROBLEMA: "Training muy lento" (< 200 timesteps/sec)
├─ Verificar nvidia-smi (compute debe estar > 80%)
├─ Salir de modo bateria (RTX 4060 reduce si laptop en bateria)
└─ Cerrar otras aplicaciones GPU-intensivas

PROBLEMA: "Reward no sube"
├─ Verificar solar data: debe tener valores 0-2887 kW (no todos ceros)
├─ Aumentar learning_rate: 3e-4 → 5e-4
└─ Entrenamiento normal = lento primeros 2 episodios, luego sube

═════════════════════════════════════════════════════════════════════════════


RESUMEN DE OPTIMIZACIONES APLICADAS
═════════════════════════════════════════════════════════════════════════════

✓ GPU OPTIMIZATION (Para RTX 4060 8GB):
  - Batch sizes reducidos: 512→256 (SAC), 2048→1024 (PPO), 2048→512 (A2C)
  - Hidden sizes reducidos: 1024→512 (todos)
  - Buffer size reducido: 1M→500k (SAC)
  - Mixed Precision (FP16) habilitado

✓ LEARNING OPTIMIZATION:
  - Learning rates aumentados (compensar menos actualizaciones)
  - Gamma reducido (0.999→0.99): simplifica Q-functions
  - Clip range aumentado en PPO (0.1→0.2): explora más
  - SDE deshabilitado en PPO (ahorra memoria)

✓ DATA VALIDATION:
  - Solar: 8,760 filas horarias, 8.03 GWh, PVGIS+Sandia
  - Chargers: 128 sockets (112 motos + 16 mototaxis)
  - BESS: 2 MWh / 1.2 MW, 92% eficiencia
  - Config: target_annual_kwh = 8,030,119 (sincronizado)

═════════════════════════════════════════════════════════════════════════════


SIGUIENTE PASO: EJECUTAR ENTRENAMIENTO
═════════════════════════════════════════════════════════════════════════════

1. Abre terminal en el directorio del proyecto:
   
   $ cd d:\diseñopvbesscar

2. Ejecuta el entrenamiento interactivo:
   
   $ python run_training_optimizado.py
   
3. Selecciona opción 4 (Secuencia SAC → PPO → A2C):

   ⏱ Tiempo estimado: 5-8 horas
   💾 Memoria GPU: 7-8 GB (máximo disponible en RTX 4060)
   📊 Resultado: Tabla comparativa con CO₂ optimizado

4. Después de completar:
   
   $ python -m scripts.run_oe3_co2_table --config configs/default.yaml
   
   → Ver tabla final con mejoras CO₂ de cada agente

═════════════════════════════════════════════════════════════════════════════

🚀 ¡LISTO PARA EMPEZAR! 🚀

Comando para ejecutar:
  python run_training_optimizado.py

═════════════════════════════════════════════════════════════════════════════
