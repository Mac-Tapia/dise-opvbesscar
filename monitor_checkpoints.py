#!/usr/bin/env python3
"""
Monitor checkpoints del entrenamiento RL y muestra progreso en tiempo real.
"""

import os
from pathlib import Path
import time
from datetime import datetime

checkpoint_dir = Path('d:\\diseñopvbesscar\\outputs\\oe3\\checkpoints')

print("""
╔════════════════════════════════════════════════════════════════╗
║         MONITOR DE CHECKPOINTS - ENTRENAMIENTO RL              ║
╚════════════════════════════════════════════════════════════════╝
""")

agents = ['SAC', 'PPO', 'A2C']

while True:
    os.system('clear' if os.name != 'nt' else 'cls')
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Monitoreo Checkpoints RL\n")
    
    for agent in agents:
        agent_dir = checkpoint_dir / agent
        
        print(f"📊 Agente: {agent}")
        
        if not agent_dir.exists():
            print(f"   ⏳ Pendiente - directorio no creado\n")
            continue
        
        # Buscar checkpoints
        checkpoints = sorted(agent_dir.glob(f'{agent}_step_*.zip'))
        final_ckpt = agent_dir / f'{agent}_final.zip'
        
        if checkpoints:
            latest = checkpoints[-1]
            size_mb = latest.stat().st_size / (1024 * 1024)
            mod_time = datetime.fromtimestamp(latest.stat().st_mtime)
            
            # Extraer número de step
            step = int(latest.stem.split('_')[-1])
            
            print(f"   ✓ Último checkpoint: Step {step}")
            print(f"   📁 Tamaño: {size_mb:.2f} MB")
            print(f"   🕐 Modificado: {mod_time.strftime('%H:%M:%S')}")
            print(f"   📍 Total checkpoints: {len(checkpoints)}")
        
        if final_ckpt.exists():
            size_mb = final_ckpt.stat().st_size / (1024 * 1024)
            print(f"   ✓ Checkpoint FINAL guardado: {size_mb:.2f} MB")
        
        print()
    
    print("─" * 60)
    print("Presiona Ctrl+C para salir | Actualizando cada 5 segundos...")
    
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        print("\n✓ Monitor detenido")
        break
