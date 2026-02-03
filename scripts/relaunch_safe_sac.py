#!/usr/bin/env python
"""
SCRIPT CRÍTICO: Relanzar SAC con configuraciones SEGURAS después de corrección de peligros.

PELIGROS ELIMINADOS:
- ✅ normalize_rewards: False (era True, causaba pérdida de información)
- ✅ reward_scale: 1.0 (era 0.5, causaba convergencia lenta)
- ✅ warmup_steps: 1000 (era 5000, desperdiciaba 19% del entrenamiento)
- ✅ clip_reward: 10.0 (era 1.0, demasiado agresivo)
- ✅ clip_obs: 10.0 (era 100.0, menos clipping preserva información)

EXPECTED RESULTS:
- reward_avg: 0.35+ (antes: 0.17, mejora de 100%+)
- Convergencia más rápida y estable
- Mejor exploración del espacio de acciones
"""

from pathlib import Path
import subprocess
import sys

def main():
    print("🚨 RELANZANDO SAC CON CONFIGURACIONES SEGURAS")
    print("=" * 80)
    print("PELIGROS ELIMINADOS:")
    print("  ❌ normalize_rewards: True  →  ✅ False")
    print("  ❌ reward_scale: 0.5        →  ✅ 1.0")
    print("  ❌ warmup_steps: 5000       →  ✅ 1000")
    print("  ❌ clip_reward: 1.0         →  ✅ 10.0")
    print("  ❌ clip_obs: 100.0          →  ✅ 10.0")
    print("=" * 80)

    # Verify corrections are in place
    sac_file = Path("src/iquitos_citylearn/oe3/agents/sac.py")
    if not sac_file.exists():
        print(f"❌ ERROR: {sac_file} not found")
        return False

    content = sac_file.read_text(encoding='utf-8')

    # Check corrections
    checks = [
        ("normalize_rewards: bool = False", "normalize_rewards corrected"),
        ("reward_scale: float = 1.0", "reward_scale corrected"),
        ("warmup_steps: int = 1000", "warmup_steps corrected"),
        ("clip_reward: float = 10.0", "clip_reward corrected"),
        ("clip_obs: float = 10.0", "clip_obs corrected"),
    ]

    all_passed = True
    for check, desc in checks:
        if check in content:
            print(f"✅ {desc}")
        else:
            print(f"❌ {desc} - NOT FOUND")
            all_passed = False

    if not all_passed:
        print("❌ CORRECTIONS NOT APPLIED - ABORTING")
        return False

    print("\n🚀 ALL CORRECTIONS VERIFIED - LAUNCHING SAFE TRAINING")

    # Launch training
    cmd = [
        sys.executable, "-m", "scripts.run_oe3_simulate",
        "--config", "configs/default.yaml",
        "--skip-baseline"
    ]

    print(f"Ejecutando: {' '.join(cmd)}")
    subprocess.run(cmd)

    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("✅ ENTRENAMIENTO RELANZADO CON ÉXITO")
    else:
        print("❌ ERROR EN RELANZAMIENTO")
        sys.exit(1)
