#!/usr/bin/env python
"""Monitor PPO training progress en tiempo real."""
import time
import sys
from pathlib import Path
from datetime import datetime

def monitor_ppo():
    """Monitorea checkpoints y progreso de entrenamiento PPO."""
    checkpoint_dir = Path("analyses/oe3/training/checkpoints/ppo")
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*60)
    print("MONITOREO PPO ENTRENAMIENTO EN VIVO")
    print("="*60)
    print(f"Directorio: {checkpoint_dir.absolute()}")
    print(f"Iniciado: {datetime.now().strftime('%H:%M:%S')}")
    print("="*60 + "\n")
    
    last_count = 0
    check_interval = 10  # segundos
    
    try:
        while True:
            checkpoints = sorted(checkpoint_dir.glob("ppo_step_*.zip"))
            current_count = len(checkpoints)
            
            if current_count != last_count:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Checkpoints generados: {current_count}")
                
                # Mostrar últimos 3 checkpoints
                for ckpt in checkpoints[-3:]:
                    size_mb = ckpt.stat().st_size / (1024**2)
                    print(f"  ✓ {ckpt.name} ({size_mb:.1f}MB)")
                
                last_count = current_count
            
            # Estimar progreso (500 steps por checkpoint)
            total_expected = 17520 // 500  # = 35 checkpoints
            if current_count > 0:
                progress = (current_count / total_expected) * 100
                print(f"  Progreso: {progress:.1f}% ({current_count}/{total_expected})")
            
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        print("\n\n✓ Monitoreo detenido")
        print(f"Total checkpoints: {current_count}")
        if current_count > 0:
            final_path = checkpoint_dir / "ppo_final.zip"
            if final_path.exists():
                size = final_path.stat().st_size / (1024**2)
                print(f"✓ Modelo final: {final_path.name} ({size:.1f}MB)")
        sys.exit(0)

if __name__ == "__main__":
    monitor_ppo()
