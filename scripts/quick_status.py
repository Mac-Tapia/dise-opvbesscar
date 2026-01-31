"""
Monitor Rápido del Entrenamiento (puede ejecutarse en otra terminal)
====================================================================

Uso:
    python scripts/quick_status.py

Muestra estado actual cada 5 segundos
"""

from pathlib import Path
import json
import time

OUT = Path("outputs/oe3/simulations")

while True:
    print("\n" + "="*100)
    for agent in ["Uncontrolled", "SAC", "PPO", "A2C"]:
        f = OUT / f"result_{agent}.json"
        if f.exists():
            d = json.load(open(f))
            print(f"✅ {agent:15}: {d['steps']:5}/8760 steps | CO₂: {d['carbon_kg']/1e6:7.2f}M kg")
        else:
            print(f"⏲️  {agent:15}: Pendiente")

    if (OUT / "simulation_summary.json").exists():
        s = json.load(open(OUT / "simulation_summary.json"))
        if s.get("pv_bess_uncontrolled"):
            print(f"\n📊 Baseline guardado: {s['pv_bess_uncontrolled']['carbon_kg']/1e6:.2f}M kg")

    time.sleep(5)
