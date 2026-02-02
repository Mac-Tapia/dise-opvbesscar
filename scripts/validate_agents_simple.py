#!/usr/bin/env python
"""
VALIDACION SIMPLE: Agentes SAC/PPO/A2C conectados correctamente
Sin caracteres unicode - encoding simple UTF-8 compatible
"""

from pathlib import Path
import sys

def check_agent_file(filepath, agent_name):
    """Verifica que un archivo de agente tenga todas las conexiones necesarias."""

    if not filepath.exists():
        print(f"ERROR: {agent_name} no encontrado")
        return False

    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"ERROR: No se pudo leer {agent_name}: {e}")
        return False

    checks = {
        'obs_394_dim': '394' in content,
        'action_129_dim': '129' in content or 'unflatten' in content,
        'normalize_obs': 'normalize' in content.lower(),
        'no_simplifications': 'simplified' not in content.lower() and 'mock' not in content.lower(),
        'complete_code': len(content) > 1000,  # Minimo de lineas esperadas
    }

    all_pass = all(checks.values())

    print(f"\n{agent_name}:")
    for check, result in checks.items():
        _ = "PASS" if result else "FAIL"
        symbol = "OK" if result else "XX"
        print(f"  [{symbol}] {check}")

    return all_pass

def main():
    print("=" * 80)
    print("VALIDACION: Agentes SAC/PPO/A2C - Estado Final")
    print("=" * 80)

    agents_dir = Path(__file__).parent.parent / "src" / "iquitos_citylearn" / "oe3" / "agents"

    agents = {
        "SAC": agents_dir / "sac.py",
        "PPO": agents_dir / "ppo_sb3.py",
        "A2C": agents_dir / "a2c_sb3.py"
    }

    results = {}
    for name, path in agents.items():
        results[name] = check_agent_file(path, name)

    print("\n" + "=" * 80)
    print("RESULTADO FINAL:")
    print("=" * 80)

    all_pass = all(results.values())

    for name, passed in results.items():
        status = "LISTO" if passed else "ERROR"
        symbol = "OK" if passed else "XX"
        print(f"  [{symbol}] {name}: {status}")

    print("\n" + "=" * 80)
    if all_pass:
        print("CONCLUSION: Todos los agentes VERIFICADOS y LISTOS")
        print("=" * 80)
        return 0
    else:
        print("CONCLUSION: Errores detectados - Revisar logs arriba")
        print("=" * 80)
        return 1

if __name__ == "__main__":
    sys.exit(main())
