#!/usr/bin/env python3
"""
Monitor EN VIVO de progreso de entrenamiento de agentes RL
Muestra: Agent, Episodes, Timesteps, Reward, Status
"""

import time
from pathlib import Path

def get_checkpoint_info(agent_name):
    """Obtener información del checkpoint más reciente."""
    checkpoint_dir = Path(f"outputs/oe3/checkpoints/{agent_name.upper()}")
    if not checkpoint_dir.exists():
        return None, 0, 0
    
    # Buscar último checkpoint
    checkpoints = list(checkpoint_dir.glob(f"{agent_name.lower()}_step_*.zip"))
    if not checkpoints:
        final = checkpoint_dir / f"{agent_name.lower()}_final.zip"
        if final.exists():
            return final.name, 87600, 87600  # 1 episodio = 8760 timesteps
        return None, 0, 0
    
    checkpoints.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    latest = checkpoints[0]
    
    # Extraer step del nombre
    try:
        step = int(latest.stem.split('_step_')[-1])
        episode = step // 8760
        return latest.name, episode, step
    except:
        return latest.name, 0, 0

def monitor_training():
    """Monitor en vivo."""
    print("\n" + "=" * 100)
    print("📊 MONITOR EN VIVO - ENTRENAMIENTO SERIAL RL (SAC → PPO → A2C)")
    print("=" * 100)
    
    agents = ["SAC", "PPO", "A2C"]
    start_time = time.time()
    
    while True:
        # Limpiar pantalla (pseudocódigo)
        os.system('cls' if os.name == 'nt' else 'clear')
        
        elapsed = time.time() - start_time
        hours = elapsed / 3600
        minutes = (elapsed % 3600) / 60
        
        print("\n" + "=" * 100)
        print(f"📊 MONITOR EN VIVO - ENTRENAMIENTO SERIAL | Tiempo: {hours:.1f}h {minutes:.0f}m")
        print("=" * 100)
        print()
        print(f"{'Agent':<10} | {'Episodes':<12} | {'Timesteps':<15} | {'Checkpoint':<40} | Status")
        print("-" * 100)
        
        for agent in agents:
            checkpoint, episode, timestep = get_checkpoint_info(agent)
            
            if checkpoint is None:
                status = "⏳ Esperando..."
            elif "final" in checkpoint.lower():
                status = "✅ COMPLETADO"
            else:
                pct = (episode / 5) * 100
                status = f"🔄 {pct:.0f}% ({episode}/5 eps)"
            
            print(f"{agent:<10} | {episode:<12} | {timestep:<15} | {checkpoint or '-':<40} | {status}")
        
        print("\n" + "-" * 100)
        print("💡 Presiona CTRL+C para terminar monitoreo (entrenamiento continúa en background)")
        print("=" * 100)
        
        # Actualizar cada 10 segundos
        time.sleep(10)

if __name__ == "__main__":
    import os
    try:
        monitor_training()
    except KeyboardInterrupt:
        print("\n\n✓ Monitoreo detenido (entrenamiento sigue en ejecución)")
