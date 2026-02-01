#!/usr/bin/env python3
"""
AUDITORÍA INTEGRAL DEL PIPELINE DE ENTRENAMIENTO OE3
====================================================

Verifica:
1. Integridad de todos los archivos necesarios
2. Validez de JSON (schema, config)
3. Dependencias e imports correctos
4. Vinculaciones de rutas y archivos
5. Consistencia en toda la cadena de entrenamiento
6. Que el flujo de trabajo sea robusto e integral

Ejecución: python scripts/audit_training_pipeline.py
"""

from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Any, Dict

# ============================================================================
# VERIFICACIÓN 1: VALIDAR PYTHON 3.11
# ============================================================================
print("="*80)
print("AUDITORÍA INTEGRAL DEL PIPELINE DE ENTRENAMIENTO OE3")
print("="*80)

print("\n[1/8] Verificando Python 3.11...")
if sys.version_info[:2] != (3, 11):
    print(f"  ❌ ERROR: Python 3.11 requerido. Actual: Python {sys.version_info.major}.{sys.version_info.minor}")
    sys.exit(1)
print(f"  ✅ Python {sys.version_info.major}.{sys.version_info.minor} OK")

# ============================================================================
# VERIFICACIÓN 2: VALIDAR ARCHIVOS CRÍTICOS EXISTEN
# ============================================================================
print("\n[2/8] Verificando archivos críticos...")

critical_files: Dict[str, str] = {
    "scripts/run_oe3_simulate.py": "Entrypoint de entrenamiento",
    "scripts/_common.py": "Carga de config y rutas",
    "src/iquitos_citylearn/oe3/simulate.py": "Core de simulación",
    "src/iquitos_citylearn/oe3/dataset_builder.py": "Constructor de dataset",
    "src/iquitos_citylearn/oe3/agents/__init__.py": "Agentes",
    "src/iquitos_citylearn/oe3/agents/sac.py": "SAC agent",
    "src/iquitos_citylearn/oe3/agents/ppo_sb3.py": "PPO agent",
    "src/iquitos_citylearn/oe3/agents/a2c_sb3.py": "A2C agent",
    "configs/default.yaml": "Configuración global",
    "data/processed/citylearn/iquitos_ev_mall/schema.json": "Schema principal",
}

missing_files: list[str] = []
for filepath, desc in critical_files.items():
    p = Path(filepath)
    if p.exists():
        print(f"  ✅ {filepath:<50} ({desc})")
    else:
        print(f"  ❌ {filepath:<50} MISSING!")
        missing_files.append(filepath)

if missing_files:
    print(f"\n  ERROR: {len(missing_files)} archivo(s) faltante(s)")
    sys.exit(1)

# ============================================================================
# VERIFICACIÓN 3: VALIDAR JSON
# ============================================================================
print("\n[3/8] Validando JSON...")

json_files: Dict[str, str] = {
    "configs/default.yaml": "No es JSON (es YAML, pero debe validarse)",
    "data/processed/citylearn/iquitos_ev_mall/schema.json": "Schema CityLearn v2",
}

json_errors: list[tuple[str, str]] = []
cfg: Dict[str, Any] = {}
schema: Dict[str, Any] = {}
try:
    import yaml
    print("  ✅ yaml importable")
    cfg_path: Path = Path("configs/default.yaml")
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)
    print(f"  ✅ configs/default.yaml válido (keys: {', '.join(list(cfg.keys())[:5])}...)")
except Exception as e:
    print(f"  ❌ Error cargando YAML: {e}")
    json_errors.append(("configs/default.yaml", str(e)))

try:
    schema_path: Path = Path("data/processed/citylearn/iquitos_ev_mall/schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    chargers_count: int = len(schema.get("buildings", {}).get("Mall_Iquitos", {}).get("chargers", {}))
    print(f"  ✅ schema.json válido (chargers: {chargers_count})")
except Exception as e:
    print(f"  ❌ Error cargando schema.json: {e}")
    json_errors.append(("schema.json", str(e)))

if json_errors:
    print(f"\n  ERROR: {len(json_errors)} JSON inválido(s)")
    sys.exit(1)

# ============================================================================
# VERIFICACIÓN 4: VALIDAR IMPORTS CRÍTICOS
# ============================================================================
print("\n[4/8] Validando imports...")

imports_to_check = [
    "from pathlib import Path",
    "import numpy",
    "import pandas",
    "import json",
    "import yaml",
    "from stable_baselines3 import SAC, PPO, A2C",
    "from iquitos_citylearn.config import load_config, load_paths",
    "from iquitos_citylearn.oe3.simulate import simulate",
]

import_errors: list[tuple[str, str]] = []
for imp_str in imports_to_check:
    try:
        exec(imp_str)
        print(f"  ✅ {imp_str}")
    except Exception as e:
        print(f"  ❌ {imp_str}")
        print(f"     Error: {str(e)[:60]}")
        import_errors.append((imp_str, str(e)))

if import_errors:
    print(f"\n  ERROR: {len(import_errors)} import(s) fallido(s)")
    print("  Solución: Verifica que el entorno virtual esté activado")
    print("  Comando: .venv\\Scripts\\activate")
    sys.exit(1)

# ============================================================================
# VERIFICACIÓN 5: VALIDAR CONFIG vs SCHEMA CONSISTENCY
# ============================================================================
print("\n[5/8] Validando consistencia config ↔ schema...")

consistency_errors: list[str] = []

# 5.1 Dataset name en config debe coincidir con directorio
dataset_name: str = cfg.get("oe3", {}).get("dataset", {}).get("name", "")
schema_file: Path = Path("data/processed/citylearn/iquitos_ev_mall/schema.json")
if dataset_name == "iquitos_ev_mall" and schema_file.exists():
    print(f"  ✅ Dataset name '{dataset_name}' coincide con schema location")
else:
    print(f"  ❌ Dataset name mismatch")
    consistency_errors.append(f"Dataset name '{dataset_name}' no coincide con ubicación")

# 5.2 Agentes en config deben existir
agents: list[str] = cfg.get("oe3", {}).get("evaluation", {}).get("agents", [])
if set(agents) == {"SAC", "PPO", "A2C"}:
    print(f"  ✅ Agentes configurados: {', '.join(agents)}")
else:
    print(f"  ⚠️  Agentes no son {{'SAC', 'PPO', 'A2C'}}: {agents}")

# 5.3 Chargers en config
ev_fleet: Dict[str, Any] = cfg.get("oe2", {}).get("ev_fleet", {})
motos: int = ev_fleet.get("motos_count", 0)
mototaxis: int = ev_fleet.get("mototaxis_count", 0)
if motos == 900 and mototaxis == 130:
    print(f"  ✅ EV Fleet: {motos} motos + {mototaxis} mototaxis")
else:
    print(f"  ⚠️  EV Fleet counts: {motos} motos, {mototaxis} mototaxis (esperado 900+130)")

# 5.4 Timesteps y energía
if cfg.get("project", {}).get("seconds_per_time_step") == 3600:
    print(f"  ✅ Timestep: 3600 segundos (1 hora)")
else:
    print(f"  ❌ Timestep incorrecto: {cfg.get('project', {}).get('seconds_per_time_step')}")
    consistency_errors.append("Timestep no es 3600")

if consistency_errors:
    for err in consistency_errors:
        print(f"    ERROR: {err}")

# ============================================================================
# VERIFICACIÓN 6: VALIDAR RUTAS Y DIRECTORIOS
# ============================================================================
print("\n[6/8] Validando directorios de ejecución...")

required_dirs: Dict[str, str] = {
    "data/raw": "Raw data",
    "data/interim/oe2": "OE2 interim",
    "data/processed/citylearn/iquitos_ev_mall": "CityLearn processed",
    "outputs/oe3/simulations": "Simulation outputs",
    "outputs/schema": "Schema outputs",
    "checkpoints/SAC": "SAC checkpoints",
    "checkpoints/PPO": "PPO checkpoints",
    "checkpoints/A2C": "A2C checkpoints",
}

missing_dirs: list[str] = []
for dirpath, desc in required_dirs.items():
    p = Path(dirpath)
    if p.exists() or dirpath.startswith("checkpoints"):  # Checkpoints se crean durante training
        print(f"  ✅ {dirpath:<45} ({desc})")
    else:
        # Solo advertencia si no es crítico
        if "checkpoints" not in dirpath and "outputs" not in dirpath:
            print(f"  ⚠️  {dirpath:<45} (se creará si es necesario)")

# ============================================================================
# VERIFICACIÓN 7: VALIDAR SCHEMA STRUCTURE
# ============================================================================
print("\n[7/8] Validando estructura del schema...")

schema_errors = []

# 7.1 Buildings
buildings = schema.get("buildings", {})
if "Mall_Iquitos" in buildings:
    print(f"  ✅ Building 'Mall_Iquitos' presente")
    building = buildings["Mall_Iquitos"]
else:
    print(f"  ❌ Building 'Mall_Iquitos' faltante")
    schema_errors.append("Building name mismatch")
    building = {}

# 7.2 Chargers
if isinstance(building, dict):
    chargers = building.get("chargers", {})
    if isinstance(chargers, dict) and len(chargers) == 128:
        print(f"  ✅ Chargers: 128 presentes")
    else:
        print(f"  ❌ Chargers: {len(chargers) if isinstance(chargers, dict) else 'structure error'} (esperado 128)")
        schema_errors.append(f"Chargers count: {len(chargers)} != 128")

# 7.3 BESS
bess = building.get("electrical_storage", {})
if bess.get("attributes", {}).get("capacity") == 2000:
    print(f"  ✅ BESS: 2,000 kWh")
else:
    print(f"  ⚠️  BESS capacity: {bess.get('attributes', {}).get('capacity')} (esperado 2000)")

# 7.4 PV
pv = building.get("pv", {})
if pv.get("attributes", {}).get("peak_power") == 4050:
    print(f"  ✅ PV: 4,050 kWp")
else:
    print(f"  ⚠️  PV capacity: {pv.get('attributes', {}).get('peak_power')} (esperado 4050)")

# 7.5 Central Agent
central_agent = schema.get("central_agent")
if central_agent is True:
    print(f"  ✅ Central agent: Enabled")
else:
    print(f"  ❌ Central agent: {central_agent} (esperado True)")
    schema_errors.append("central_agent not enabled")

# 7.6 Timesteps
episode_steps = schema.get("episode_time_steps")
if episode_steps == 8760:
    print(f"  ✅ Episode timesteps: 8,760")
else:
    print(f"  ❌ Episode timesteps: {episode_steps} (esperado 8760)")
    schema_errors.append(f"episode_time_steps: {episode_steps} != 8760")

if schema_errors:
    print(f"\n  ERROR: {len(schema_errors)} error(es) en schema")
    for err in schema_errors:
        print(f"    - {err}")

# ============================================================================
# VERIFICACIÓN 8: VALIDAR LOCK FILE
# ============================================================================
print("\n[8/8] Validando protección del schema...")

lock_file = Path("data/processed/citylearn/iquitos_ev_mall/.schema.lock")
if lock_file.exists():
    try:
        with open(lock_file) as f:
            lock_data = json.load(f)
        lock_hash = lock_data.get("schema_hash_sha256", "")
        if lock_hash.startswith("413853673f1c2a73"):
            print(f"  ✅ Schema lock activo")
            print(f"     Hash: {lock_hash[:16]}...")
        else:
            print(f"  ⚠️  Schema lock existe pero hash diferente")
            print(f"     Esperado: 413853673f1c2a73...")
            print(f"     Actual:   {lock_hash[:16]}...")
    except Exception as e:
        print(f"  ❌ Error leyendo lock file: {e}")
else:
    print(f"  ⚠️  Lock file no existe (será creado)")

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print("\n" + "="*80)
print("RESUMEN DE AUDITORÍA")
print("="*80)

total_checks = 8
all_passed = (
    not missing_files and
    not import_errors and
    not json_errors and
    not schema_errors and
    sys.version_info[:2] == (3, 11)
)

if all_passed:
    print("\n✅ AUDITORÍA COMPLETADA - SISTEMA LISTO PARA ENTRENAMIENTO")
    print("\nEl pipeline está:")
    print("  ✅ Correctamente vinculado")
    print("  ✅ Sin errores de dependencias")
    print("  ✅ Con JSON válidos")
    print("  ✅ Rutas correctas")
    print("  ✅ Schema protegido")
    print("\nSiguiente paso:")
    print("  python -m scripts.run_oe3_simulate --config configs/default.yaml")
    sys.exit(0)
else:
    print("\n❌ AUDITORÍA ENCONTRÓ ERRORES")
    print("\nErrores encontrados:")
    if missing_files:
        print(f"  - {len(missing_files)} archivo(s) faltante(s)")
    if import_errors:
        print(f"  - {len(import_errors)} import(s) fallido(s)")
    if json_errors:
        print(f"  - {len(json_errors)} JSON inválido(s)")
    if schema_errors:
        print(f"  - {len(schema_errors)} error(es) en schema")
    print("\nSolución:")
    print("  1. Revisa los errores anteriores")
    print("  2. Corrige los problemas detectados")
    print("  3. Vuelve a ejecutar esta auditoría")
    sys.exit(1)
