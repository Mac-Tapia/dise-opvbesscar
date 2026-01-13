#!/usr/bin/env python3
"""
Mostrar estado de entrenamiento y checkpoints guardados (sin ejecutar nuevamente).
"""

from pathlib import Path
import json
from datetime import datetime

base_dir = Path("d:\\diseñopvbesscar")
outputs_dir = base_dir / "outputs" / "oe3"
checkpoint_dir = outputs_dir / "checkpoints"
analysis_dir = base_dir / "analyses" / "oe3"
training_dir = outputs_dir / "training"

print("""
╔══════════════════════════════════════════════════════════════════════╗
║            ESTADO ENTRENAMIENTO RL - CHECKPOINTS Y RESULTADOS        ║
╚══════════════════════════════════════════════════════════════════════╝
""")

# 1. Mostrar resultados previos
print(f"\n📊 RESULTADOS PREVIOS (análisis):")
print(f"{'─'*70}")

comparison_csv = analysis_dir / "co2_comparison_table.csv"
if comparison_csv.exists():
    with open(comparison_csv) as f:
        lines = f.readlines()[:7]  # Mostrar header + 6 rows
    for line in lines:
        print(line.rstrip())

# 2. Mostrar checkpoints existentes
print(f"\n\n📁 CHECKPOINTS GUARDADOS:")
print(f"{'─'*70}")

if not checkpoint_dir.exists():
    print("⏳ Directorio de checkpoints no existe aún (primera ejecución)")
else:
    agents = ['SAC', 'PPO', 'A2C']
    for agent in agents:
        agent_dir = checkpoint_dir / agent
        
        if not agent_dir.exists():
            print(f"\n{agent:>5}: ⏳ Pendiente")
        else:
            # Buscar checkpoints
            steps = sorted([int(f.stem.split('_')[-1]) for f in agent_dir.glob(f'{agent}_step_*.zip')])
            final_ckpt = agent_dir / f'{agent}_final.zip'
            
            if steps:
                latest_step = steps[-1]
                latest_file = agent_dir / f'{agent}_step_{latest_step}.zip'
                size_mb = latest_file.stat().st_size / (1024*1024)
                mod_time = datetime.fromtimestamp(latest_file.stat().st_mtime)
                
                print(f"\n{agent:>5}: ✓ ENTRENANDO")
                print(f"        Latest: Step {latest_step}")
                print(f"        Tamaño: {size_mb:.2f} MB")
                print(f"        Total checkpoints: {len(steps)}")
                print(f"        Última actualización: {mod_time.strftime('%H:%M:%S')}")
            
            if final_ckpt.exists():
                size_mb = final_ckpt.stat().st_size / (1024*1024)
                mod_time = datetime.fromtimestamp(final_ckpt.stat().st_mtime)
                print(f"        FINAL: {size_mb:.2f} MB (completado {mod_time.strftime('%H:%M:%S')})")

# 3. Mostrar métrica de entrenamiento
print(f"\n\n📈 MÉTRICAS DE ENTRENAMIENTO:")
print(f"{'─'*70}")

if training_dir.exists():
    for csv_file in sorted(training_dir.glob("*_training_metrics.csv")):
        agent = csv_file.stem.split('_')[0]
        with open(csv_file) as f:
            lines = f.readlines()
        if len(lines) > 1:
            last_line = lines[-1]
            values = last_line.split(',')
            print(f"\n{agent:>5}: Episode {len(lines)-2} (last)")
            if len(values) >= 4:
                try:
                    print(f"        Reward: {float(values[1]):.4f}")
                    print(f"        Loss: {float(values[2]):.6f}")
                except:
                    pass

# 4. Mostrar configuraciones
print(f"\n\n⚙️ CONFIGURACIONES DE AGENTES:")
print(f"{'─'*70}")

for json_file in sorted(training_dir.glob("*_config.json")):
    agent = json_file.stem.split('_')[0]
    with open(json_file) as f:
        cfg = json.load(f)
    print(f"\n{agent}:")
    for key in ['device', 'batch_size', 'episodes', 'learning_rate']:
        if key in cfg:
            print(f"  {key}: {cfg[key]}")

print(f"\n{'='*70}")
print(f"✓ Estado actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*70}\n")

# 5. Recomendaciones
print(f"\n💡 PRÓXIMOS PASOS:")
print(f"{'─'*70}")
print("""
1. Para RELANZAR entrenamiento:
   python -m scripts.run_oe3_simulate --config configs/default.yaml
   
2. Para REANUDAR desde checkpoints:
   - La configuración resume_checkpoints=true lo hará automáticamente
   - Los checkpoints se guardan cada 1000 steps en: outputs/oe3/checkpoints/
   
3. Para MONITOREAR en vivo:
   python monitor_checkpoints.py
   
4. Para VER RESULTADOS finales:
   - CSV: analyses/oe3/co2_comparison_table.csv
   - Markdown: analyses/oe3/co2_comparison_table.md
""")
