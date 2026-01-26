#!/usr/bin/env python
"""Real-time training monitor for SAC/PPO/A2C agents."""

import json
import time
from pathlib import Path
from datetime import datetime

def get_checkpoint_info(agent_dir):
    """Get latest checkpoint info for an agent."""
    try:
        summary_files = list(agent_dir.glob('TRAINING_CHECKPOINTS_SUMMARY_*.json'))
        if not summary_files:
            return None

        latest = max(summary_files, key=lambda p: p.stat().st_mtime)
        with open(latest) as f:
            return json.load(f)
    except:
        return None

def format_number(n):
    """Format large numbers with commas."""
    if isinstance(n, (int, float)):
        return f"{n:,.0f}" if isinstance(n, int) else f"{n:,.2f}"
    return str(n)

def monitor_live():
    """Monitor training in real-time."""

    checkpoint_dir = Path('checkpoints')
    agents = ['SAC', 'PPO', 'A2C']

    print("\n" + "="*90)
    print("🔵 MONITOR DE ENTRENAMIENTO OE3 - TIEMPO REAL")
    print("="*90)
    print(f"Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Presiona Ctrl+C para detener el monitor\n")

    iteration = 0
    start_time = time.time()

    try:
        while True:
            iteration += 1
            elapsed = time.time() - start_time
            hours = elapsed // 3600
            mins = (elapsed % 3600) // 60
            secs = elapsed % 60

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Iteración {iteration} | Tiempo transcurrido: {int(hours)}h {int(mins)}m {int(secs)}s")
            print("-" * 90)

            any_active = False

            for agent in agents:
                agent_dir = checkpoint_dir / agent
                info = get_checkpoint_info(agent_dir)

                if info:
                    any_active = True

                    ep = info.get('current_episode', 0)
                    total_ts = info.get('total_timesteps', 0)
                    last_reward = info.get('last_episode_reward')
                    best_reward = info.get('best_reward')

                    # Progress bar
                    progress_pct = (ep / 5) * 100
                    bar_len = 30
                    filled = int(bar_len * ep / 5)
                    bar = "█" * filled + "░" * (bar_len - filled)

                    print(f"\n🔷 {agent:5s} | Episode {ep}/5 [{bar}] {progress_pct:5.1f}%")
                    print(f"         Timesteps: {format_number(total_ts):>12s} | ", end="")

                    if last_reward is not None:
                        print(f"Last Reward: {last_reward:8.4f} | ", end="")

                    if best_reward is not None:
                        print(f"Best: {best_reward:8.4f}")
                    else:
                        print()

                    # ETA estimation
                    if total_ts > 0:
                        avg_ts_per_sec = total_ts / elapsed if elapsed > 0 else 0
                        remaining_ts = 5 * 8760 - total_ts  # 5 episodes × 8760 steps each
                        if avg_ts_per_sec > 0:
                            remaining_secs = remaining_ts / avg_ts_per_sec
                            remaining_mins = remaining_secs / 60
                            print(f"         ETA: ~{remaining_mins:.0f} minutos")
                else:
                    print(f"\n⚪ {agent:5s} | Esperando inicio...")

            if any_active:
                print("\n" + "-" * 90)
                print("Próxima actualización en 30 segundos...")

            time.sleep(30)

    except KeyboardInterrupt:
        print("\n\n" + "="*90)
        print("✓ Monitor detenido por usuario")
        print("="*90)
        elapsed = time.time() - start_time
        print(f"Tiempo total monitorizado: {elapsed/60:.1f} minutos")

if __name__ == "__main__":
    monitor_live()
