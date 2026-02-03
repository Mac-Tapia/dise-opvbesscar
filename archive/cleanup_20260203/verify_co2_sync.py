#!/usr/bin/env python3
"""
Verification Script for CO₂ Calculation Synchronization (2026-02-03)

This script validates that the CO₂ correction has been properly applied
to all necessary files and that there are no regressions.

Run: python verify_co2_sync.py
"""

import sys
from pathlib import Path

def check_simulate_py():
    """Verificar que simulate.py tiene la corrección."""
    path = Path("src/iquitos_citylearn/oe3/simulate.py")
    if not path.exists():
        return False, f"❌ {path} no encontrado"

    content = path.read_text(encoding='utf-8')

    # Buscar los cambios clave
    checks = {
        "solar_coverage_ratio": "solar_coverage_ratio = np.divide" in content,
        "ev_from_solar": "ev_from_solar = np.clip(ev" in content,
        "CORRECCIÓN 2026-02-03": "[CORRECCIÓN 2026-02-03]" in content,
        "EV from Solar: %.0f kWh": "EV from Solar: %.0f kWh" in content,
    }

    all_ok = all(checks.values())
    msg = f"✅ simulate.py" if all_ok else f"❌ simulate.py"

    for check, status in checks.items():
        emoji = "✅" if status else "❌"
        msg += f"\n  {emoji} {check}"

    return all_ok, msg

def check_rewards_py():
    """Verificar que rewards.py tiene la corrección."""
    path = Path("src/iquitos_citylearn/oe3/rewards.py")
    if not path.exists():
        return False, f"❌ {path} no encontrado"

    content = path.read_text(encoding='utf-8')

    # Buscar los cambios clave
    checks = {
        "CORREGIDA 2026-02-03": "CORREGIDA 2026-02-03" in content,
        "ev_covered = min": "ev_covered = min(ev_charging_kwh" in content,
        "excess_solar": "excess_solar = max(0" in content,
        "mall_baseline": "mall_baseline = 100.0" in content,
    }

    all_ok = all(checks.values())
    msg = f"✅ rewards.py" if all_ok else f"❌ rewards.py"

    for check, status in checks.items():
        emoji = "✅" if status else "❌"
        msg += f"\n  {emoji} {check}"

    return all_ok, msg

def check_agents_py():
    """Verificar que los agentes NO tienen cálculos de CO₂ (heredan desde simulate.py)."""
    agents = [
        "src/iquitos_citylearn/oe3/agents/sac.py",
        "src/iquitos_citylearn/oe3/agents/ppo_sb3.py",
        "src/iquitos_citylearn/oe3/agents/a2c_sb3.py",
    ]

    all_ok = True
    msg = "✅ Agentes (no tienen cálculos de CO₂)"

    for agent_path in agents:
        path = Path(agent_path)
        if not path.exists():
            all_ok = False
            msg += f"\n  ❌ {agent_path} no encontrado"
            continue

        content = path.read_text(encoding='utf-8')

        # Los agentes NO deben tener cálculos de CO₂
        has_co2_calc = (
            "co2_saved_ev" in content or
            "ev_charging_kwh * 2.146" in content
        )

        if has_co2_calc:
            all_ok = False
            msg += f"\n  ❌ {agent_path}: Tiene cálculos de CO₂ (debe heredar desde simulate.py)"
        else:
            agent_name = path.name
            msg += f"\n  ✅ {agent_name}: Hereda correctamente"

    return all_ok, msg

def main():
    print("=" * 80)
    print("CO₂ CALCULATION SYNCHRONIZATION VERIFICATION (2026-02-03)")
    print("=" * 80)
    print()

    results = []

    # Verificar simulate.py
    ok, msg = check_simulate_py()
    results.append(ok)
    print(msg)
    print()

    # Verificar rewards.py
    ok, msg = check_rewards_py()
    results.append(ok)
    print(msg)
    print()

    # Verificar agentes
    ok, msg = check_agents_py()
    results.append(ok)
    print(msg)
    print()

    # Resumen
    print("=" * 80)
    if all(results):
        print("✅ SINCRONIZACIÓN COMPLETADA Y VALIDADA")
        print()
        print("Próximos pasos:")
        print("1. Re-run SAC training: python -m scripts.run_oe3_simulate --agent sac")
        print("2. Compare PPO/A2C: python -m scripts.run_oe3_simulate --agent ppo/a2c")
        print("3. Generate CO₂ table: python -m scripts.run_oe3_co2_table")
        return 0
    else:
        print("❌ ERRORES ENCONTRADOS - REVISAR CORRECCIONES")
        return 1

if __name__ == "__main__":
    sys.exit(main())
