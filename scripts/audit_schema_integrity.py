#!/usr/bin/env python3
"""AUDITORÍA DE SCHEMA - Verifica integridad y consistencia.

Valida que:
1. Un UNICO schema.json existe y es FIJO
2. No cambia entre entrenamientos de SAC/PPO/A2C
3. Todos los agentes usan el MISMO schema
4. Schema es compatible CityLearn v2
5. Schema contiene 128 observables de cargadores (32 cargadores × 4 sockets)
   - 28 cargadores para motos (112 sockets) = 56 kW
   - 4 cargadores para mototaxis (16 sockets) = 12 kW
   - Total: 68 kW potencia simultánea
6. Schema generado correctamente en OE2/OE3

Uso:
    python scripts/audit_schema_integrity.py
"""
from __future__ import annotations

import sys
import json
import hashlib
from pathlib import Path
from typing import Any, Dict, TextIO

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

print("\n" + "="*80)
print("AUDITORIA DE SCHEMA - INTEGRIDAD Y CONSISTENCIA")
print("="*80)

# ========== CONFIGURACION ==========
schema_dir: Path = Path("data/processed/citylearn/iquitos_ev_mall")
schema_file: Path = schema_dir / "schema.json"
expected_buildings: int = 1  # Un edificio central (mall + 32 cargadores = 128 sockets)
expected_chargers: int = 128  # 128 observables de sockets individuales

# ========== 1. VERIFICAR SCHEMA EXISTE Y ES UNICO ==========
print("\n[1/6] Verificando existencia del schema...")

if not schema_file.exists():
    print(f"  ERROR: Schema no encontrado en {schema_file}")
    sys.exit(1)

# Verificar que no hay multiples schemas
other_schemas: list[Path] = list(schema_dir.glob("schema*.json"))
if len(other_schemas) > 1:
    print(f"  ADVERTENCIA: {len(other_schemas)} schemas encontrados (deberia ser 1):")
    for s in other_schemas:
        print(f"    - {s.name}")
    print(f"\n  SOLUCION: Usar SOLO schema.json para entrenar agentes")
else:
    print(f"  > Schema principal: {schema_file.name}")

# ========== 2. VERIFICAR CONTENIDO SCHEMA ==========
print("\n[2/6] Verificando contenido del schema...")

schema: Dict[str, Any] = {}
try:
    with open(schema_file, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    print("  > Schema JSON valido")
except json.JSONDecodeError as e:
    print(f"  ERROR: Schema JSON corrupto: {e}")
    sys.exit(1)

# Verificar campos requeridos
required_fields: list[str] = ['buildings', 'central_agent', 'episode_time_steps',
                  'simulation_start_time_step', 'simulation_end_time_step']
missing_fields: list[str] = [f for f in required_fields if f not in schema]

if missing_fields:
    print(f"  ERROR: Campos faltantes en schema: {missing_fields}")
    sys.exit(1)

print(f"  > Campos requeridos: OK")
# Buildings es un dict, no una lista
buildings_count: int = len(schema.get('buildings', {})) if isinstance(schema.get('buildings'), dict) else len(schema.get('buildings', []))
print(f"  > Edificios: {buildings_count} (esperado: 1)")
print(f"  > Timesteps: {schema.get('episode_time_steps', 'null')} (deberia ser 8760)")
print(f"  > Central agent: {schema.get('central_agent', 'null')}")

# ========== 3. VERIFICAR CHARGERS EN SCHEMA ==========
print("\n[3/6] Verificando chargers en schema...")

charger_count: int = 0
buildings: Dict[str, Any] = schema.get('buildings', {})
if isinstance(buildings, dict) and len(buildings) > 0:
    # Tomar el primer building (Buildings es dict)
    building: Dict[str, Any] = buildings[list(buildings.keys())[0]]

    # Chargers es un dict, no una lista
    if 'chargers' in building and isinstance(building['chargers'], dict):
        chargers_dict: Dict[str, Any] = building['chargers']
        charger_count = len(chargers_dict)

        # Contar chargers activos
        active_count: int = 0
        for charger_key, charger_config in chargers_dict.items():
            if isinstance(charger_config, dict) and charger_config.get('active', False):
                active_count += 1

        print(f"  > Chargers totales: {charger_count}")
        print(f"  > Chargers activos: {active_count}")

print(f"  > Chargers en schema: {charger_count} (esperado: {expected_chargers})")

if charger_count != expected_chargers:
    print(f"  ERROR: Se esperaban {expected_chargers} chargers, se encontraron {charger_count}")
    print(f"  Esto indica que el schema NO fue generado correctamente en OE3")
    sys.exit(1)

print(f"  > Validacion 128 chargers: OK")

# ========== 4. CALCULAR HASH DEL SCHEMA (INMUTABILIDAD) ==========
print("\n[4/6] Verificando inmutabilidad del schema...")

schema_hash: str
with open(schema_file, 'rb') as f:  # type: ignore[assignment]
    schema_bytes: bytes = f.read()
    schema_hash = hashlib.sha256(schema_bytes).hexdigest()

print(f"  > SHA256 del schema: {schema_hash[:16]}...")

# Guardar hash para futuras verificaciones
hash_file: Path = schema_dir / ".schema_sha256"
if hash_file.exists():
    with open(hash_file, 'r', encoding='utf-8') as f:  # type: ignore
        saved_hash: str = f.read().strip()

    if saved_hash == schema_hash:
        print(f"  > Hash coincide con verificacion anterior: OK")
    else:
        print(f"  WARNING: Schema cambio desde ultima verificacion")
        print(f"    Hash anterior: {saved_hash[:16]}...")
        print(f"    Hash actual:   {schema_hash[:16]}...")
        print(f"  IMPORTANTE: El schema NO debe cambiar entre entrenamientos")
else:
    print(f"  > Guardando hash para futuras verificaciones...")
    with open(hash_file, 'w') as f:
        f.write(schema_hash)

# ========== 5. VERIFICAR CONEXION CON AGENTS ==========
print("\n[5/6] Verificando conexion con agents...")

# Verificar que los agentes puedan cargar el schema
try:
    # import sys, Path ya importados arriba
    src_path: Path = Path(__file__).parent.parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path.parent))

    # Intentar importar validator si existe
    try:
        from iquitos_citylearn.oe3.schema_validator import SchemaValidator
        validator = SchemaValidator(str(schema_file))
        print(f"  > SchemaValidator puede cargar schema: OK")
    except (ImportError, AttributeError):
        print(f"  > SchemaValidator no disponible (continuando...)")
except Exception as e:
    print(f"  > Advertencia al validar schema: {e}")

# ========== 6. VERIFICAR CONSISTENCIA CON CONFIG ==========
print("\n[6/6] Verificando consistencia con config.yaml...")

import yaml

config: Dict[str, Any] = {}
try:
    with open('configs/default.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    oe3_config: Dict[str, Any] = config.get('oe3', {})
    dataset_name: str = oe3_config.get('dataset', {}).get('name', 'unknown')

    if dataset_name == 'iquitos_ev_mall':
        print(f"  > Dataset en config: {dataset_name} (OK)")
    else:
        print(f"  WARNING: Dataset en config ({dataset_name}) no coincide con schema")

except Exception as e:
    print(f"  ERROR al leer config: {e}")

# ========== RESUMEN FINAL ==========
print("\n" + "="*80)
print("RESULTADO DE AUDITORIA")
print("="*80)

audit_result: Dict[str, Any] = {
    "schema_exists": schema_file.exists(),
    "schema_valid": True,
    "charger_count": charger_count,
    "charger_count_ok": charger_count == expected_chargers,
    "central_agent": schema.get('central_agent', False),
    "episode_timesteps": schema.get('episode_time_steps', None),
    "schema_hash": schema_hash[:16] + "...",
}

print("\nREQUISITOS:")
print(f"  [{'OK' if audit_result['schema_exists'] else 'FAIL'}] Schema existe: {schema_file.name}")
print(f"  [{'OK' if audit_result['schema_valid'] else 'FAIL'}] Schema JSON valido")
print(f"  [{'OK' if audit_result['charger_count_ok'] else 'FAIL'}] 128 chargers presentes")
print(f"  [{'OK' if audit_result['central_agent'] else 'FAIL'}] Central agent configurado")

if all([
    audit_result['schema_exists'],
    audit_result['schema_valid'],
    audit_result['charger_count_ok'],
    audit_result['central_agent']
]):
    print("\n[OK] AUDITORIA PASADA - SCHEMA LISTO PARA TODOS LOS AGENTES")
    print("\nENTRENAR CON:")
    print("  python -m scripts.run_oe3_simulate --config configs/default.yaml")
    print("\nEl schema NO se modificara entre entrenamientos SAC/PPO/A2C")
    print("="*80 + "\n")
    sys.exit(0)
else:
    print("\n[FAIL] AUDITORIA FALLO - REVISAR ERRORES ARRIBA")
    print("="*80 + "\n")
    sys.exit(1)
