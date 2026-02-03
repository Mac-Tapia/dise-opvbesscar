#!/usr/bin/env python3
"""
Monitor script to track training pipeline completion.
Checks for result_*.json files and reports status in real-time.
"""

from pathlib import Path
import json
import time
from datetime import datetime
from typing import Any

output_dir = Path("d:/diseñopvbesscar/outputs/oe3/simulations")
sac_result: Path = output_dir / "result_SAC.json"
ppo_result: Path = output_dir / "result_PPO.json"
a2c_result: Path = output_dir / "result_A2C.json"

print("=" * 80)
print("🚀 TRAINING PIPELINE MONITOR - Started 2026-02-03 06:20+")
print("=" * 80)
print()

agents_status: dict[str, dict[str, Any]] = {
    "SAC": {"file": sac_result, "found": False, "time": None},
    "PPO": {"file": ppo_result, "found": False, "time": None},
    "A2C": {"file": a2c_result, "found": False, "time": None},
}

start_time: datetime = datetime.now()
last_check: float = 0.0

while True:
    try:
        current_time = time.time()

        # Check every 30 seconds
        if current_time - last_check < 30:
            time.sleep(5)
            continue

        last_check = current_time
        elapsed = (datetime.now() - start_time).total_seconds() / 60

        current_datetime = datetime.now()
        print(f"[{current_datetime.strftime('%H:%M:%S')}] Elapsed: {elapsed:.1f} min | Checking for result files...")

        all_done = True
        for agent_name, agent_info in agents_status.items():
            result_file = agent_info["file"]

            if not agent_info["found"] and result_file.exists():
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    agent_info["found"] = True
                    agent_info["time"] = datetime.now()

                    steps = data.get("steps", "?")
                    co2_neto = data.get("co2_neto_kg", "?")

                    time_str = agent_info['time'].strftime('%H:%M:%S') if agent_info['time'] is not None else "unknown"
                    print(f"\n✅ {agent_name} COMPLETE at {time_str}")
                    print(f"   File: {result_file.name}")
                    print(f"   Steps: {steps}")
                    if isinstance(co2_neto, (int, float)):
                        print(f"   CO₂ Neto: {co2_neto:,.0f} kg")
                    print()

                except json.JSONDecodeError:
                    print(f"   ⚠️  {agent_name} file exists but invalid JSON")
                except Exception as e:
                    print(f"   ❌ Error reading {agent_name}: {e}")

            elif agent_info["found"]:
                time_str = agent_info['time'].strftime('%H:%M:%S') if agent_info['time'] is not None else "unknown"
                print(f"   ✅ {agent_name} - Completed at {time_str}")
            else:
                print(f"   ⏳ {agent_name} - Waiting...")
                all_done = False

        if all_done:
            print("\n" + "=" * 80)
            print("🎉 TRAINING PIPELINE COMPLETE!")
            print("=" * 80)
            total_time = (datetime.now() - start_time).total_seconds() / 60
            print(f"Total training time: {total_time:.1f} minutes")
            break

        print()

    except KeyboardInterrupt:
        print("\n⚠️  Monitor stopped by user")
        break
    except Exception as e:
        print(f"Error in monitor: {e}")
        time.sleep(30)
