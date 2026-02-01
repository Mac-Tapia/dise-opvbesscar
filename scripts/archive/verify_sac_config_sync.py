from __future__ import annotations

import json
from pathlib import Path
import yaml
import sys

def verify_sac_config_sync():
    """Verifica que los parámetros de SAC estén sincronizados en todos los archivos"""

    print("\n" + "="*100)
    print("🔍 VERIFICACIÓN DE SINCRONIZACIÓN DE CONFIGURACIÓN SAC".center(100))
    print("="*100 + "\n")

    # Valores esperados (CRÍTICOS)
    expected = {
        "ent_coef_init": 0.1,
        "ent_coef_lr": 1e-5,
        "tau": 0.005,
        "learning_rate": 1e-4,
        "max_grad_norm": 0.5,
        "hidden_sizes": (256, 256),
        "use_prioritized_replay": False,
    }

    issues = []

    # 1. Verificar config/default.yaml
    print("✓ Verificando configs/default.yaml...")
    with open("configs/default.yaml") as f:
        config = yaml.safe_load(f)
        sac_cfg = config["oe3"]["evaluation"]["sac"]

        checks = {
            "ent_coef_init": sac_cfg.get("ent_coef_init"),
            "ent_coef_lr": sac_cfg.get("ent_coef_lr"),
            "tau": sac_cfg.get("tau"),
            "learning_rate": sac_cfg.get("learning_rate"),
            "max_grad_norm": sac_cfg.get("max_grad_norm"),
            "hidden_sizes": sac_cfg.get("hidden_sizes"),
            "use_prioritized_replay": sac_cfg.get("use_prioritized_replay"),
        }

        for param, expected_val in expected.items():
            actual_val = checks[param]

            # Conversión para comparación (1e-5 == 1e-05 == 0.00001)
            if isinstance(expected_val, float) and isinstance(actual_val, (int, float, str)):
                if isinstance(actual_val, str):
                    actual_val = float(actual_val.replace('e-05', 'e-5').replace('e-04', 'e-4'))
                match = abs(float(actual_val) - expected_val) < 1e-10
            elif isinstance(expected_val, (tuple, list)) and isinstance(actual_val, (tuple, list)):
                match = tuple(actual_val) == tuple(expected_val)
            else:
                match = actual_val == expected_val

            if match:
                print(f"  ✅ {param}: {actual_val}")
            else:
                print(f"  ❌ {param}: {actual_val} (esperado: {expected_val})")
                issues.append(f"configs/default.yaml: {param} = {actual_val}, expected {expected_val}")

    # 2. Verificar src/iquitos_citylearn/oe3/agents/sac.py
    print("\n✓ Verificando src/iquitos_citylearn/oe3/agents/sac.py...")
    with open("src/iquitos_citylearn/oe3/agents/sac.py", encoding="utf-8") as f:
        content = f.read()

        # Buscar valores numéricos en las líneas de dataclass
        import re

        patterns = {
            "ent_coef_init: float = ": r"ent_coef_init:\s*float\s*=\s*([\d.e-]+)",
            "ent_coef_lr: float = ": r"ent_coef_lr:\s*float\s*=\s*([\d.e-]+)",
            "tau: float = ": r"tau:\s*float\s*=\s*([\d.]+)(?!\d)",
            "learning_rate: float = ": r"learning_rate:\s*float\s*=\s*([\d.e-]+)",
            "max_grad_norm: float = ": r"max_grad_norm:\s*float\s*=\s*([\d.]+)",
            "hidden_sizes: tuple = ": r"hidden_sizes:\s*tuple\s*=\s*\((\d+),\s*(\d+)\)",
            "use_prioritized_replay: bool = ": r"use_prioritized_replay:\s*bool\s*=\s*(True|False)",
        }

        for param_name, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                if "hidden_sizes" in param_name:
                    size = (int(match.group(1)), int(match.group(2)))
                    print(f"  ✅ hidden_sizes: {size}")
                    if size != expected["hidden_sizes"]:
                        issues.append(f"sac.py: hidden_sizes = {size}, expected {expected['hidden_sizes']}")
                elif "use_prioritized_replay" in param_name:
                    val = match.group(1) == "True"
                    print(f"  ✅ use_prioritized_replay: {val}")
                    if val != expected["use_prioritized_replay"]:
                        issues.append(f"sac.py: use_prioritized_replay = {val}, expected {expected['use_prioritized_replay']}")
                else:
                    val = float(match.group(1))
                    param = param_name.replace(": float = ", "").strip()
                    expected_val = expected.get(param)
                    if val == expected_val:
                        print(f"  ✅ {param}: {val}")
                    else:
                        print(f"  ❌ {param}: {val} (esperado: {expected_val})")
                        issues.append(f"sac.py: {param} = {val}, expected {expected_val}")
            else:
                print(f"  ⚠️  {param_name} no encontrado")

    # Resumen
    print("\n" + "="*100)
    if not issues:
        print("✅ TODAS LAS CONFIGURACIONES ESTÁN SINCRONIZADAS".center(100))
        print("="*100)
        return 0
    else:
        print("❌ PROBLEMAS ENCONTRADOS:".center(100))
        print("="*100)
        for issue in issues:
            print(f"  • {issue}")
        print("="*100)
        return 1

if __name__ == "__main__":
    exit_code = verify_sac_config_sync()
    sys.exit(exit_code)
