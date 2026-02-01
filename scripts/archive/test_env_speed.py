import sys
import os
from pathlib import Path

# Change to dataset directory to avoid encoding issues
os.chdir(str(Path('d:\\diseñopvbesscar\\data\\processed\\citylearn\\iquitos_ev_mall')))
sys.path.insert(0, 'd:\\diseñopvbesscar')

from citylearn.citylearn import CityLearnEnv
import time

print(f"Working directory: {os.getcwd()}\n")

# Load environment
env = CityLearnEnv('schema.json')
print("=== ENVIRONMENT LOADED ===")
print(f"Buildings: {len(env.buildings)}")

b = env.buildings[0]
print(f"Building name: {b.name}")

evs = len(b.electric_vehicles) if hasattr(b, 'electric_vehicles') else 0
print(f"Electric vehicles: {evs}")

if evs > 0:
    print(f"  First EV type: {type(b.electric_vehicles[0]).__name__}")

# Reset and test
obs, _ = env.reset()
print(f"\nObservation length: {len(obs)}")
print(f"Action space dim: 126 (manual)")

# Time 1000 steps
print("\n=== TIMING TEST ===")
start = time.time()
for i in range(1000):
    obs, reward, terminated, truncated, _ = env.step([0.5]*126)

elapsed = time.time() - start
steps_per_sec = 1000 / elapsed
est_8760 = (8760 * elapsed) / 1000

print(f"1000 steps: {elapsed:.2f}sec = {steps_per_sec:.0f} steps/sec")
print(f"Estimated 8,760 steps: {est_8760:.1f} seconds ({est_8760/60:.2f} minutes)")
print(f"\nExpected (realistic): 250-300 seconds (4-5 minutes)")
print(f"Ratio (actual/expected): {est_8760/275:.2f}x")

if est_8760 < 100:
    print("\n⚠️  STILL TOO FAST!")
    print("This suggests CityLearn is not actually processing charger control.")

