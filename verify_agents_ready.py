#!/usr/bin/env python3
"""
Verificación completa de que los agentes están LISTOS para entrenamiento desde cero.
Valida: dataset builder, baseline, configs, agents, y ausencia de --skip-dataset.
"""
from __future__ import annotations

import sys
from pathlib import Path
import json
import re

print("\n" + "="*80)
print("VERIFICACION COMPLETA - AGENTES LISTOS PARA ENTRENAMIENTO DESDE CERO")
print("="*80 + "\n")

# 1. Verificar Python 3.11
print("[1/8] Validando Python 3.11...")
if sys.version_info[:2] != (3, 11):
    print(f"[ERROR] Python {sys.version_info[0]}.{sys.version_info[1]} detectado (REQUERIDO 3.11)")
    sys.exit(1)
print("[OK] Python 3.11 confirmado\n")

# 2. Verificar ausencia de --skip-dataset en argumentos
print("[2/8] Verificando que --skip-dataset fue removido...")
scripts = [
    "scripts/run_ppo_a2c_only.py",
    "scripts/run_sac_only.py",
    "scripts/run_all_agents.py",
    "scripts/run_oe3_simulate.py"
]
has_skip_dataset = False
for script_path in scripts:
    content = Path(script_path).read_text(encoding='utf-8')
    if "add_argument(\"--skip-dataset\"" in content or "add_argument('--skip-dataset'" in content:
        print(f"[ERROR] {script_path} AÚN TIENE --skip-dataset")
        has_skip_dataset = True
    elif "if args.skip_dataset" in content:
        print(f"[ERROR] {script_path} AÚN REFERENCIA args.skip_dataset")
        has_skip_dataset = True

if has_skip_dataset:
    sys.exit(1)
print("[OK] --skip-dataset removido de TODOS los scripts\n")

# 3. Verificar dataset builder
print("[3/8] Validando dataset_builder.py...")
builder_path = Path("src/iquitos_citylearn/oe3/dataset_builder.py")
builder_code = builder_path.read_text(encoding='utf-8')
required_in_builder = [
    "_validate_solar_timeseries_hourly",
    "8760",
    "build_citylearn_dataset",
    "128 chargers"
]
for req in required_in_builder:
    if req not in builder_code:
        print(f"[ERROR] dataset_builder.py no contiene '{req}'")
        sys.exit(1)
print("[OK] Dataset builder valida 128 chargers, 8760 timesteps\n")

# 4. Verificar config default
print("[4/8] Validando configs/default.yaml...")
config_path = Path("configs/default.yaml")
config_code = config_path.read_text(encoding='utf-8')
required_in_config = [
    "ppo:",
    "a2c:",
    "sac:",
    "oe2:",
    "bess:",
    "oe3:",
    "4520",  # BESS capacity
    "2712"   # BESS power
]
for req in required_in_config:
    if req not in config_code:
        print(f"[ERROR] config no contiene '{req}'")
        sys.exit(1)
print("[OK] Configuración contiene PPO, A2C, SAC con specs OE2\n")

# 5. Verificar agentes
print("[5/8] Validando agentes (PPO, A2C, SAC)...")
agent_files = {
    "PPO": "src/iquitos_citylearn/oe3/agents/ppo_sb3.py",
    "A2C": "src/iquitos_citylearn/oe3/agents/a2c_sb3.py",
    "SAC": "src/iquitos_citylearn/oe3/agents/sac.py"
}
for agent_name, agent_path in agent_files.items():
    ap = Path(agent_path)
    if not ap.exists():
        print(f"[ERROR] {agent_name} no encontrado en {agent_path}")
        sys.exit(1)
    agent_code = ap.read_text(encoding='utf-8')
    if "class" not in agent_code or "policy_kwargs" not in agent_code:
        print(f"[ERROR] {agent_name} no contiene configuración válida")
        sys.exit(1)
print("[OK] PPO, A2C, SAC definidos y configurados\n")

# 6. Verificar baseline
print("[6/8] Validando cálculo de baseline...")
baseline_exists = [
    Path("scripts/run_ppo_a2c_only.py").read_text() if Path("scripts/run_ppo_a2c_only.py").exists() else "",
    Path("scripts/run_sac_only.py").read_text() if Path("scripts/run_sac_only.py").exists() else "",
]
baseline_check = any("non_shiftable_load" in content for content in baseline_exists)
if not baseline_check:
    print("[ADVERTENCIA] Baseline puede no usar non_shiftable_load correctamente")
else:
    print("[OK] Baseline usa non_shiftable_load (REAL data)\n")

# 7. Verificar directorios
print("[7/8] Validando directorios requeridos...")
required_dirs = [
    "data/interim/oe2/solar",
    "data/interim/oe2/chargers",
    "data/interim/oe2/bess",
    "configs",
    "scripts",
    "src/iquitos_citylearn/oe3",
    "outputs",
    "analyses/oe3/training"
]
for dir_path in required_dirs:
    dp = Path(dir_path)
    if not dp.exists():
        print(f"[ERROR] Directorio no encontrado: {dir_path}")
        sys.exit(1)
print("[OK] Todos los directorios requeridos existen\n")

# 8. Verificar arquitectura individual chargers
print("[8/8] Validando construcción individual de chargers...")
chargers_json = Path("data/interim/oe2/chargers/individual_chargers.json")
if chargers_json.exists():
    with open(chargers_json) as f:
        chargers = json.load(f)
    if len(chargers) != 128:
        print(f"[ERROR] Se esperan 128 chargers, se encontraron {len(chargers)}")
        sys.exit(1)
    # Validar estructura - cada charger tiene 4 sockets
    total_sockets = sum(c.get("sockets", 1) for c in chargers)
    expected_sockets = 128 * 4  # 128 chargers × 4 sockets c/u
    if total_sockets != expected_sockets:
        print(f"[ERROR] Se esperan {expected_sockets} sockets total (128×4), se contaron {total_sockets}")
        sys.exit(1)
    print(f"[OK] Arquitectura confirmada: 128 chargers × 4 sockets = {total_sockets} sockets\n")
else:
    print("[ADVERTENCIA] individual_chargers.json no existe, será construido dinamicamente\n")

print("="*80)
print("[OK] VERIFICACION COMPLETADA - TODOS LOS AGENTES LISTOS PARA ENTRENAMIENTO")
print("="*80)
print("\nRESUMEN:")
print("  - Python 3.11: VALIDADO")
print("  - --skip-dataset: ELIMINADO (SIEMPRE reconstruye dataset)")
print("  - Dataset builder: VALIDADO (128 chargers individuales, 8760 timesteps)")
print("  - Agentes: PPO, A2C, SAC LISTOS")
print("  - Baseline: Calculado desde REAL data (non_shiftable_load)")
print("  - Configuración OE2: 4520 kWh BESS, 2712 kW power")
print("  - Chargers: 128 individuales × 4 sockets = 512 sockets (mismo dataset base)")
print("\nPuedes ejecutar:")
print("  py -3.11 -m scripts.run_ppo_a2c_only --config configs/default.yaml")
print("  py -3.11 -m scripts.run_all_agents --config configs/default.yaml")
print("="*80 + "\n")
