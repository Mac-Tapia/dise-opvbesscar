#!/usr/bin/env python3
"""
Script rápido para ver el progreso en tiempo real
Uso: python monitor_a2c_launch.py
"""

import time
from pathlib import Path
from datetime import datetime
import os

def get_latest_checkpoint(agent: str) -> dict | None:
    """Obtiene el último checkpoint de un agente."""
    checkpoint_dir = Path(f"analyses/oe3/training/checkpoints/{agent}")
    if not checkpoint_dir.exists():
        return None
    
    checkpoints = sorted(checkpoint_dir.glob(f"{agent}_step_*.zip"), 
                        key=lambda x: int(x.stem.split("_")[2]))
    if checkpoints:
        return {
            "path": checkpoints[-1],
            "step": int(checkpoints[-1].stem.split("_")[2]),
            "time": checkpoints[-1].stat().st_mtime
        }
    return None

def print_progress_bar(current: int, total: int, label: str = "", width: int = 40) -> None:
    """Imprime una barra de progreso."""
    if total == 0:
        pct = 0
    else:
        pct = int((current / total) * 100)
    
    filled = int((current / total) * width) if total > 0 else 0
    bar = "█" * filled + "░" * (width - filled)
    print(f"{label}: [{bar}] {pct}% ({current:,}/{total:,})")

def main():
    print("\n" + "="*70)
    print("📊 MONITOR A2C AUTO-LAUNCH")
    print("="*70 + "\n")
    
    ppo_target = 43800
    a2c_target = 43800
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("="*70)
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")
        
        # PPO
        ppo_ckpt = get_latest_checkpoint("ppo")
        if ppo_ckpt:
            ppo_step = ppo_ckpt["step"]
            ppo_pct = int((ppo_step / ppo_target) * 100)
            
            print("🟢 PPO Training:")
            print_progress_bar(ppo_step, ppo_target, "   Progress", width=40)
            
            if ppo_step >= ppo_target - 800:
                print("   Status: ✅ ALMOST DONE! (>= 43,000 steps)")
                print("   Next: A2C Auto-Launch Triggered ⏳\n")
            else:
                mins_remaining = max(1, int((ppo_target - ppo_step) / 1000 * 3))  # ~3 min per 1k steps
                print(f"   Status: ⏳ Training... (~{mins_remaining} min remaining)")
                print(f"   Latest checkpoint: ppo_step_{ppo_step}\n")
        else:
            print("🔴 PPO Training: No checkpoints found yet\n")
        
        # A2C
        a2c_ckpt = get_latest_checkpoint("a2c")
        if a2c_ckpt:
            a2c_step = a2c_ckpt["step"]
            print("🟡 A2C Training:")
            print_progress_bar(a2c_step, a2c_target, "   Progress", width=40)
            print(f"   Latest checkpoint: a2c_step_{a2c_step}\n")
        else:
            print("⚪ A2C Training: Waiting for PPO to complete...\n")
        
        # Overall
        print("="*70)
        
        if ppo_ckpt and ppo_ckpt["step"] >= ppo_target - 800:
            if a2c_ckpt:
                if a2c_ckpt["step"] >= a2c_target - 800:
                    print("✅ BOTH PPO AND A2C COMPLETE!")
                    print("   Ready for CO₂ analysis")
                    break
                else:
                    print("⏳ PPO Done ✅ | A2C In Progress...")
            else:
                print("✅ PPO Complete! A2C Auto-Launched...")
        else:
            print("⏳ PPO In Progress... A2C Waiting...")
        
        print("="*70 + "\n")
        
        time.sleep(15)  # Update every 15 seconds

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Monitor stopped by user")
