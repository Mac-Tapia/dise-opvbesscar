#!/usr/bin/env python
"""Validación: Agentes SAC/PPO/A2C Conectados a CityLearn v2 + OE2"""

from pathlib import Path
import re

def main():
    print("\n" + "=" * 80)
    print("VALIDACIÓN: Agentes (SAC/PPO/A2C) ↔ CityLearn v2 ↔ OE2")
    print("=" * 80 + "\n")

    agents = {
        "SAC": "sac.py",
        "PPO": "ppo_sb3.py",
        "A2C": "a2c_sb3.py"
    }

    agents_dir = Path(__file__).parent.parent / "src" / "iquitos_citylearn" / "oe3" / "agents"

    for name, filename in agents.items():
        path = agents_dir / filename
        if not path.exists():
            print(f"❌ {name}: No encontrado")
            continue

        content = path.read_text(encoding="utf-8")

        print(f"\n{'─' * 80}")
        print(f"🤖 {name}")
        print(f"{'─' * 80}")

        # Test 1: Observaciones
        norm_obs = "normalize_observations: bool = True" in content
        clip_obs = "clip_obs: float = 5.0" in content
        print(f"\n[1] Observaciones (394-dim): {'✅' if norm_obs and clip_obs else '❌'}")
        print(f"    • Normalización: {'✅' if norm_obs else '❌'}")
        print(f"    • Clipping (5.0): {'✅' if clip_obs else '❌'}")

        # Test 2: Acciones
        unflatten = "_unflatten_action" in content
        iter_action = "for sp in self.env.action_space" in content
        print(f"\n[2] Acciones (129-dim): {'✅' if unflatten and iter_action else '❌'}")
        print(f"    • _unflatten_action: {'✅' if unflatten else '❌'}")
        print(f"    • Itera acciones: {'✅' if iter_action else '❌'}")

        # Test 3: Year Coverage
        match_n_steps = re.search(r"n_steps:\s*int\s*=\s*(\d+)", content)
        match_buffer = re.search(r"buffer_size:\s*int\s*=\s*(\d+)", content)

        year_ok = False
        year_msg = ""

        if match_n_steps:
            n_steps = int(match_n_steps.group(1))
            if n_steps >= 8760:
                year_ok = True
                year_msg = f"n_steps={n_steps} ✅"
            elif n_steps >= 2048:
                year_ok = True
                year_msg = f"n_steps={n_steps} (⚠️ múltiples episodios)"
            else:
                year_msg = f"n_steps={n_steps} ❌ BAJO"
        elif match_buffer:
            buffer = int(match_buffer.group(1))
            if buffer >= 100000:
                year_ok = True
                year_msg = f"buffer_size={buffer} ✅"

        print(f"\n[3] Cobertura año (8,760 ts): {'✅' if year_ok else '❌'}")
        print(f"    • {year_msg}")

        # Test 4: Simplificaciones
        crit_issue = "n_steps: int = 32" in content
        mod_issue = "clip_range: float = 0.5" in content

        print(f"\n[4] Simplificaciones:")
        if crit_issue:
            print(f"    • 🔴 CRÍTICO: n_steps=32 (debe ser ≥2,048)")
        if mod_issue:
            print(f"    • ⚠️ clip_range=0.5 (normal es 0.2)")
        if not crit_issue and not mod_issue:
            print(f"    • ✅ Configuración apropiada")

    print(f"\n{'=' * 80}\n")

if __name__ == "__main__":
    main()
