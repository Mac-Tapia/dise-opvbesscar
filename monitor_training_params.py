#!/usr/bin/env python
"""
Script de monitoreo en TIEMPO REAL del entrenamiento SAC.
Verifica que los parámetros sincronizados se están usando correctamente.
"""

import json
from pathlib import Path
import time

def check_training_params():
    """Verificar que training está usando parámetros óptimos."""
    print("\n" + "=" * 80)
    print("[MONITOREO ENTRENAMIENTO SAC] Verificación de parámetros en TIEMPO REAL")
    print("=" * 80 + "\n")

    # Verificar archivos de configuración
    checks = {
        "sac.py gamma": ("src/iquitos_citylearn/oe3/agents/sac.py", "gamma: float = 0.995"),
        "sac.py tau": ("src/iquitos_citylearn/oe3/agents/sac.py", "tau: float = 0.02"),
        "simulate.py gamma": ("src/iquitos_citylearn/oe3/simulate.py", "gamma=0.995,"),
        "simulate.py tau": ("src/iquitos_citylearn/oe3/simulate.py", "tau=0.02,"),
        "yaml gamma": ("configs/default.yaml", "gamma: 0.995"),
        "yaml tau": ("configs/default.yaml", "tau: 0.02"),
        "yaml max_grad_norm": ("configs/default.yaml", "max_grad_norm: 10.0"),
        "yaml clip_obs": ("configs/default.yaml", "clip_obs: 100.0"),
    }

    all_ok = True
    for check_name, (file_path, expected_text) in checks.items():
        try:
            content = Path(file_path).read_text()
            if expected_text in content:
                print(f"✅ {check_name}: CORRECTO")
            else:
                print(f"❌ {check_name}: FALLO (texto no encontrado)")
                all_ok = False
        except Exception as e:
            print(f"❌ {check_name}: ERROR ({e})")
            all_ok = False

    # Verificar checkpoints
    print("\n[CHECKPOINTS]")
    sac_checkpoints = list(Path("checkpoints/sac").glob("sac_step_*.zip"))
    print(f"  SAC checkpoints en ejecución: {len(sac_checkpoints)}")
    if len(sac_checkpoints) > 0:
        latest = max(sac_checkpoints, key=lambda p: p.stat().st_mtime)
        print(f"  Último checkpoint: {latest.name}")

    # Verificar dataset
    print("\n[DATASET]")
    solar = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
    chargers = Path("data/interim/oe2/chargers/chargers_hourly_profiles_annual.csv")
    schema = Path("data/processed/citylearn/iquitos_ev_mall/schema.json")

    print(f"  Solar: {'✅ OK' if solar.exists() else '❌ MISSING'}")
    print(f"  Chargers: {'✅ OK' if chargers.exists() else '❌ MISSING'}")
    print(f"  Schema: {'✅ OK' if schema.exists() else '❌ MISSING'}")

    # Resumen
    print("\n" + "=" * 80)
    if all_ok:
        print("✅ SISTEMA COMPLETAMENTE SINCRONIZADO Y LISTO")
    else:
        print("⚠️ ADVERTENCIA: Algunos parámetros no están sincronizados")
    print("=" * 80 + "\n")

    return all_ok

if __name__ == "__main__":
    check_training_params()
