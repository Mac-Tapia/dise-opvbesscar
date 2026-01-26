#!/usr/bin/env python
"""Monitor training progress in real-time."""

import json
import time
from pathlib import Path

def monitor_training():
    """Monitor training progress from checkpoints."""

    print("="*80)
    print("MONITOR DE ENTRENAMIENTO OE3 - SAC | PPO | A2C")
    print("="*80)
    print(f"Tiempo inicial: {time.strftime('%H:%M:%S')}\n")

    agents = ['SAC', 'PPO', 'A2C']
    checkpoint_dir = Path('checkpoints')

    iteration = 0
    while True:
        iteration += 1
        print(f"\n[ITERACIÓN {iteration}] {time.strftime('%H:%M:%S')}")
        print("-" * 80)

        all_active = False

        for agent_name in agents:
            agent_dir = checkpoint_dir / agent_name

            # Look for checkpoint summary
            summary_files = list(agent_dir.glob('TRAINING_CHECKPOINTS_SUMMARY_*.json'))

            if summary_files:
                all_active = True
                latest_summary = max(summary_files, key=lambda p: p.stat().st_mtime)

                with open(latest_summary) as f:
                    data = json.load(f)

                print(f"\n🔵 {agent_name}:")
                print(f"   Checkpoints: {data.get('total_checkpoints', 'N/A')}")
                print(f"   Episode actual: {data.get('current_episode', 'N/A')}")
                print(f"   Total timesteps: {data.get('total_timesteps', 'N/A'):,}")

                if 'best_reward' in data:
                    print(f"   Mejor reward: {data['best_reward']:.4f}")
                if 'last_episode_reward' in data:
                    print(f"   Último reward: {data['last_episode_reward']:.4f}")

                # Estimate progress
                episode = data.get('current_episode', 0)
                total_eps = 5  # Configured in default.yaml
                progress = (episode / total_eps) * 100
                print(f"   Progreso: [{progress:.0f}%] ({episode}/{total_eps} episodios)")
            else:
                print(f"\n⚪ {agent_name}: Esperando inicio...")

        if not all_active:
            print("\n⏳ Entrenamiento aún no ha iniciado...")
        else:
            print("\n" + "="*80)
            print("PRÓXIMA VERIFICACIÓN EN 30 SEGUNDOS...")
            print("="*80)

        try:
            time.sleep(30)
        except KeyboardInterrupt:
            print("\n\n✓ Monitor detenido")
            break

if __name__ == "__main__":
    monitor_training()
