#!/usr/bin/env python3
"""
SCHEMA LOCK - Protege schema.json contra modificaciones accidentales

Funciones:
1. Lock: Congela schema y lo protege
2. Verify: Valida que schema NO fue modificado
3. Unlock: Permite cambios (solo si es necesario)

Uso:
    python scripts/schema_lock.py lock      # Congelar schema
    python scripts/schema_lock.py verify    # Verificar que no cambio
    python scripts/schema_lock.py unlock    # Desbloquear (admin only)
"""

import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime

SCHEMA_PATH = Path("data/processed/citylearn/iquitos_ev_mall/schema.json")
LOCK_FILE = SCHEMA_PATH.parent / ".schema.lock"

def get_schema_hash():
    """Calcula hash SHA256 del schema"""
    with open(SCHEMA_PATH, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def lock_schema():
    """Congela schema y crea archivo lock"""
    print("\n" + "="*80)
    print("SCHEMA LOCK - Congelando schema")
    print("="*80)

    if not SCHEMA_PATH.exists():
        print(f"ERROR: {SCHEMA_PATH} no existe")
        sys.exit(1)

    schema_hash = get_schema_hash()

    lock_info = {
        'locked_at': datetime.now().isoformat(),
        'schema_hash': schema_hash,
        'schema_path': str(SCHEMA_PATH),
        'status': 'LOCKED',
        'message': 'Este schema NO debe ser modificado entre entrenamientos de agentes'
    }

    with open(LOCK_FILE, 'w') as f:
        json.dump(lock_info, f, indent=2)

    print(f"\n[OK] Schema congelado")
    print(f"  Ruta: {SCHEMA_PATH}")
    print(f"  Hash: {schema_hash[:16]}...")
    print(f"  Lock file: {LOCK_FILE}")
    print(f"\nIMPORTANTE:")
    print("  - No modifiques schema.json manualmente")
    print("  - SAC, PPO, A2C compartiran este MISMO schema")
    print("  - El schema es FIJO durante todo el entrenamiento")
    print("="*80 + "\n")

def verify_schema():
    """Verifica que schema NO fue modificado"""
    print("\n" + "="*80)
    print("SCHEMA LOCK - Verificando integridad")
    print("="*80)

    if not LOCK_FILE.exists():
        print(f"\nWARNING: Lock file no existe: {LOCK_FILE}")
        print("Ejecuta primero: python scripts/schema_lock.py lock")
        return False

    with open(LOCK_FILE, 'r') as f:
        lock_info = json.load(f)

    saved_hash = lock_info['schema_hash']
    current_hash = get_schema_hash()

    print(f"\n  Lock creado: {lock_info['locked_at']}")
    print(f"  Hash esperado: {saved_hash[:16]}...")
    print(f"  Hash actual:   {current_hash[:16]}...")

    if saved_hash == current_hash:
        print(f"\n[OK] Schema NO fue modificado")
        print(f"  Integridad: VERIFICADA")
        print("="*80 + "\n")
        return True
    else:
        print(f"\n[FAIL] SCHEMA FUE MODIFICADO")
        print(f"  Este es un error potencial que puede causar")
        print(f"  inconsistencias entre entrenamientos de agentes")
        print(f"\nACCION REQUERIDA:")
        print(f"  1. Restaurar schema desde backup")
        print(f"  2. O validar cambios y re-ejecutar: python scripts/schema_lock.py lock")
        print("="*80 + "\n")
        return False

def unlock_schema():
    """Desbloquea schema (solo si es necesario)"""
    print("\n" + "="*80)
    print("SCHEMA LOCK - Desbloqueando (SOLO SI ES NECESARIO)")
    print("="*80)

    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
        print(f"\n[OK] Lock removido: {LOCK_FILE}")
    else:
        print(f"\n[INFO] No hay lock activo")

    print(f"\nADVERTENCIA:")
    print(f"  El schema ahora puede ser modificado")
    print(f"  Recuerda re-ejecutar 'lock' despues de cambios")
    print("="*80 + "\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUso:")
        print("  python scripts/schema_lock.py lock     # Congelar schema")
        print("  python scripts/schema_lock.py verify   # Verificar integridad")
        print("  python scripts/schema_lock.py unlock   # Desbloquear (admin)")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "lock":
        lock_schema()
    elif command == "verify":
        success = verify_schema()
        sys.exit(0 if success else 1)
    elif command == "unlock":
        unlock_schema()
    else:
        print(f"Comando desconocido: {command}")
        sys.exit(1)
