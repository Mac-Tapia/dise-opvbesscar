from __future__ import annotations

import time
from pathlib import Path
import pandas as pd
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def monitor_training_live(check_interval: int = 30, max_duration: int = 3600 * 10):
    """Monitor entrenamiento en vivo con actualizaciones periódicas"""

    sac_progress = Path("analyses/oe3/training/progress/sac_progress.csv")
    ppo_progress = Path("analyses/oe3/training/progress/ppo_progress.csv")
    sac_results = Path("outputs/oe3/simulations/sac_results.json")
    ppo_results = Path("outputs/oe3/simulations/ppo_results.json")

    start_time = time.time()
    last_sac_rows = 0
    last_ppo_rows = 0

    print("\n" + "="*100)
    print("🎯 MONITOR DE ENTRENAMIENTO EN TIEMPO REAL".center(100))
    print("="*100 + "\n")

    while time.time() - start_time < max_duration:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Check SAC
            if sac_progress.exists():
                sac_df = pd.read_csv(sac_progress)
                if len(sac_df) > last_sac_rows:
                    last_row = sac_df.iloc[-1]
                    print(f"\n[{current_time}] 🔵 SAC - ACTUALIZACIÓN")
                    print(f"  Episodios: {len(sac_df)} | ", end="")

                    if 'episode_reward_mean' in last_row:
                        print(f"Reward: {last_row['episode_reward_mean']:.4f} | ", end="")
                    if 'total_co2_kg' in last_row:
                        print(f"CO2: {last_row['total_co2_kg']:.2f} kg | ", end="")
                    if 'total_timesteps' in last_row:
                        print(f"Steps: {last_row['total_timesteps']:,.0f}", end="")
                    print()

                    last_sac_rows = len(sac_df)

            # Check PPO
            if ppo_progress.exists():
                ppo_df = pd.read_csv(ppo_progress)
                if len(ppo_df) > last_ppo_rows:
                    last_row = ppo_df.iloc[-1]
                    print(f"[{current_time}] 🟢 PPO - ACTUALIZACIÓN")
                    print(f"  Episodios: {len(ppo_df)} | ", end="")

                    if 'episode_reward_mean' in last_row:
                        print(f"Reward: {last_row['episode_reward_mean']:.4f} | ", end="")
                    if 'total_co2_kg' in last_row:
                        print(f"CO2: {last_row['total_co2_kg']:.2f} kg | ", end="")
                    if 'total_timesteps' in last_row:
                        print(f"Steps: {last_row['total_timesteps']:,.0f}", end="")
                    print()

                    last_ppo_rows = len(ppo_df)

            # Check final results
            if sac_results.exists():
                with open(sac_results) as f:
                    sac_res = json.load(f)
                    if sac_res.get("status") == "COMPLETED":
                        print(f"\n✅ SAC ENTRENAMIENTO COMPLETADO")
                        print(f"   Años simulados: {sac_res.get('simulated_years', 0):.1f}")
                        print(f"   CO2 final: {sac_res.get('total_co2_kg', 0):.2f} kg")

            if ppo_results.exists():
                with open(ppo_results) as f:
                    ppo_res = json.load(f)
                    if ppo_res.get("status") == "COMPLETED":
                        print(f"\n✅ PPO ENTRENAMIENTO COMPLETADO")
                        print(f"   Años simulados: {ppo_res.get('simulated_years', 0):.1f}")
                        print(f"   CO2 final: {ppo_res.get('total_co2_kg', 0):.2f} kg")

            time.sleep(check_interval)

        except Exception as e:
            logger.error(f"Error en monitoreo: {e}")
            time.sleep(check_interval)

    print("\n" + "="*100)
    print("⏱️  Monitoreo finalizado".center(100))
    print("="*100 + "\n")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Monitor en vivo del entrenamiento")
    ap.add_argument("--interval", type=int, default=30, help="Intervalo de chequeo en segundos")
    ap.add_argument("--duration", type=int, default=3600*10, help="Duración máxima en segundos")
    args = ap.parse_args()

    monitor_training_live(check_interval=args.interval, max_duration=args.duration)
