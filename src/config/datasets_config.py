"""
CONFIGURACION FIJA DE DATASETS - NUNCA CAMBIAR RUTAS
====================================================

Rutas DEFINITIVAS de los 3 datasets que usa BESS.PY
Estas rutas están BLOQUEADAS y NO deben modificarse bajo ninguna circunstancia.

ACTUALIZACIÓN AUTOMÁTICA:
- Si los archivos con MISMO NOMBRE se reemplazan/actualizan → bess.py carga automáticamente
- Sistema de detección de cambios: file size + modification date + hash
- Metadata guardada en: data/.datasets_metadata.json

Última verificación: 2026-02-21
Estado: ✅ FIJO - LISTO PARA PRODUCCION CON AUTO-UPDATE
"""
from pathlib import Path
from typing import Final, Optional
import json
import hashlib
from datetime import datetime

# ============================================================================
# RAIZ DEL PROYECTO
# ============================================================================
# datasets_config.py está en: src/config/datasets_config.py
# __file__ path: d:\diseñopvbesscar\src\config\datasets_config.py
# .parent = src/config/
# .parent.parent = src/
# .parent.parent.parent = d:\diseñopvbesscar (PROYECTO RAIZ)
PROJECT_ROOT: Final = Path(__file__).parent.parent.parent

# ============================================================================
# DIRECTORIO DE DATOS OE2
# ============================================================================
OE2_DATA_DIR: Final = PROJECT_ROOT / "data" / "oe2"

# ============================================================================
# ARCHIVO DE METADATA (PARA AUTO-DETECCION DE CAMBIOS)
# ============================================================================
DATASETS_METADATA_FILE: Final = PROJECT_ROOT / "data" / ".datasets_metadata.json"

# ============================================================================
# DATASET 1: GENERACION SOLAR (PV)
# ============================================================================
# ARCHIVO: pv_generation_citylearn2024.csv
# RUTA FIJA: data/oe2/Generacionsolar/pv_generation_citylearn2024.csv
# DESCRIPCION:
#   - Generación horaria de PV (solar) para 1 año completo (2024)
#   - 8,760 registros (365 días × 24 horas)
#   - Columna usada: 'energia_kwh'
#   - Total anual: 8,292,514 kWh
# NUNCA CAMBIAR ESTA RUTA
# ============================================================================
PV_GENERATION_DATA_PATH: Final = OE2_DATA_DIR / "Generacionsolar" / "pv_generation_citylearn2024.csv"

# ============================================================================
# DATASET 2: DEMANDA EV (MOTOS Y MOTOTAXIS)
# ============================================================================
# ARCHIVO: chargers_ev_ano_2024_v3.csv
# RUTA FIJA: data/oe2/chargers/chargers_ev_ano_2024_v3.csv
# DESCRIPCION:
#   - Datos detallados de 38 sockets de carga (19 cargadores × 2)
#   - 8,760 registros (365 días × 24 horas)
#   - 1,060 columnas (cada socket con múltiples parámetros)
#   - Columna agregada usada: 'ev_energia_total_kwh'
#   - Total anual: 408,282 kWh
#   - 30 sockets → Motos (15 cargadores)
#   - 8 sockets → Mototaxis (4 cargadores)
# NUNCA CAMBIAR ESTA RUTA
# ============================================================================
EV_DEMAND_DATA_PATH: Final = OE2_DATA_DIR / "chargers" / "chargers_ev_ano_2024_v3.csv"

# ============================================================================
# DATASET 3: DEMANDA MALL (CENTRO COMERCIAL)
# ============================================================================
# ARCHIVO: demandamallhorakwh.csv
# RUTA FIJA: data/oe2/demandamallkwh/demandamallhorakwh.csv
# DESCRIPCION:
#   - Demanda horaria del centro comercial para 1 año completo (2024)
#   - 8,760 registros (365 días × 24 horas)
#   - Columna usada: 'mall_demand_kwh'
#   - Total anual: 12,368,653 kWh
#   - Pico máximo: 2,763 kW (BESS descarga cuando > 1,900 kW)
# NUNCA CAMBIAR ESTA RUTA
# ============================================================================
MALL_DEMAND_DATA_PATH: Final = OE2_DATA_DIR / "demandamallkwh" / "demandamallhorakwh.csv"

# ============================================================================
# FUNCIONES DE DETECCION DE CAMBIOS
# ============================================================================

def calculate_file_hash(file_path: Path, chunk_size: int = 8192) -> str:
    """
    Calcular MD5 hash de un archivo.
    Usado para detectar cambios en contenido de datasets.
    """
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        return f"ERROR:{str(e)}"

def get_file_metadata(file_path: Path) -> dict:
    """
    Obtener metadata de un archivo para comparación.
    Incluye: tamaño, fecha modificación, hash
    """
    if not file_path.exists():
        return {"exists": False, "error": f"Archivo no encontrado: {file_path}"}
    
    stat = file_path.stat()
    return {
        "exists": True,
        "file_name": file_path.name,
        "file_size_bytes": stat.st_size,
        "modified_timestamp": stat.st_mtime,
        "modified_date": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "hash_md5": calculate_file_hash(file_path),
    }

def load_datasets_metadata() -> dict:
    """
    Cargar metadata guardada de datasets previos.
    Retorna {} si no existe archivo de metadata.
    """
    if not DATASETS_METADATA_FILE.exists():
        return {}
    
    try:
        with open(DATASETS_METADATA_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def save_datasets_metadata(metadata: dict) -> bool:
    """
    Guardar metadata de datasets para comparación futura.
    Retorna True si se guardó exitosamente.
    """
    try:
        DATASETS_METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DATASETS_METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=2)
        return True
    except Exception:
        return False

def detect_dataset_changes() -> dict[str, bool]:
    """
    DETECTAR cambios en datasets comparando con metadata previa.
    
    Retorna diccionario:
    {
        "pv_changed": bool,
        "ev_changed": bool,
        "mall_changed": bool,
        "any_changed": bool,
    }
    """
    old_metadata = load_datasets_metadata()
    
    current_pv = get_file_metadata(PV_GENERATION_DATA_PATH)
    current_ev = get_file_metadata(EV_DEMAND_DATA_PATH)
    current_mall = get_file_metadata(MALL_DEMAND_DATA_PATH)
    
    # Comparar PV
    pv_changed = (
        old_metadata.get("pv", {}).get("hash_md5") != current_pv.get("hash_md5") or
        old_metadata.get("pv", {}).get("file_size_bytes") != current_pv.get("file_size_bytes")
    )
    
    # Comparar EV
    ev_changed = (
        old_metadata.get("ev", {}).get("hash_md5") != current_ev.get("hash_md5") or
        old_metadata.get("ev", {}).get("file_size_bytes") != current_ev.get("file_size_bytes")
    )
    
    # Comparar MALL
    mall_changed = (
        old_metadata.get("mall", {}).get("hash_md5") != current_mall.get("hash_md5") or
        old_metadata.get("mall", {}).get("file_size_bytes") != current_mall.get("file_size_bytes")
    )
    
    # Guardar metadata actual para próxima comparación
    new_metadata = {
        "last_checked": datetime.now().isoformat(),
        "pv": current_pv,
        "ev": current_ev,
        "mall": current_mall,
    }
    save_datasets_metadata(new_metadata)
    
    return {
        "pv_changed": pv_changed,
        "ev_changed": ev_changed,
        "mall_changed": mall_changed,
        "any_changed": pv_changed or ev_changed or mall_changed,
    }

# ============================================================================
# VALIDACION DE INTEGRIDAD
# ============================================================================
def validate_dataset_paths() -> dict[str, bool]:
    """
    VALIDAR que las 3 rutas de datos existan y sean accesibles.
    Ejecutar ANTES de cualquier simulación BESS.
    Retorna diccionario con estado de cada archivo.
    """
    validation = {
        "PV_path_exists": PV_GENERATION_DATA_PATH.exists(),
        "EV_path_exists": EV_DEMAND_DATA_PATH.exists(),
        "MALL_path_exists": MALL_DEMAND_DATA_PATH.exists(),
    }
    
    # Verificar que TODOS existan
    all_exist = all(validation.values())
    validation["all_paths_valid"] = all_exist
    
    return validation

# ============================================================================
# RESUMEN DE DATASETS (INFORMACION)
# ============================================================================
DATASET_SUMMARY = {
    "PV": {
        "archivo": "pv_generation_citylearn2024.csv",
        "ruta": str(PV_GENERATION_DATA_PATH),
        "filas": 8760,
        "columnas": 11,
        "columna_principal": "energia_kwh",
        "total_kwh_ano": 8_292_514,
        "unidad": "kWh/hora",
        "descripcion": "Generación solar (4,050 kWp)",
    },
    "EV": {
        "archivo": "chargers_ev_ano_2024_v3.csv",
        "ruta": str(EV_DEMAND_DATA_PATH),
        "filas": 8760,
        "columnas": 1060,
        "columna_principal": "ev_energia_total_kwh",
        "total_kwh_ano": 408_282,
        "unidad": "kWh/hora",
        "descripcion": "Demanda EV (38 sockets: 30 motos + 8 mototaxis)",
    },
    "MALL": {
        "archivo": "demandamallhorakwh.csv",
        "ruta": str(MALL_DEMAND_DATA_PATH),
        "filas": 8760,
        "columnas": 6,
        "columna_principal": "mall_demand_kwh",
        "total_kwh_ano": 12_368_653,
        "unidad": "kWh/hora",
        "descripcion": "Demanda centro comercial (pico: 2,763 kW)",
    },
}

if __name__ == "__main__":
    """Mostrar configuración fija de datasets y detectar cambios"""
    print("\n" + "="*80)
    print("CONFIGURACION FIJA DE DATASETS - BESS v5.4")
    print("CON AUTO-DETECCION DE CAMBIOS")
    print("="*80)
    
    print("\n[1] PV GENERATION (SOLAR)")
    print("-"*80)
    print(f"Ruta FIJA: {PV_GENERATION_DATA_PATH}")
    print(f"Existe: {PV_GENERATION_DATA_PATH.exists()}")
    
    print("\n[2] EV DEMAND (MOTOS/MOTOTAXIS)")
    print("-"*80)
    print(f"Ruta FIJA: {EV_DEMAND_DATA_PATH}")
    print(f"Existe: {EV_DEMAND_DATA_PATH.exists()}")
    
    print("\n[3] MALL DEMAND (CENTRO COMERCIAL)")
    print("-"*80)
    print(f"Ruta FIJA: {MALL_DEMAND_DATA_PATH}")
    print(f"Existe: {MALL_DEMAND_DATA_PATH.exists()}")
    
    print("\n[VALIDACION] Integridad de datos")
    print("-"*80)
    validation = validate_dataset_paths()
    for key, value in validation.items():
        status = "✅" if value else "❌"
        print(f"{key:.<50} {status}")
    
    print("\n[DETECCION] Cambios automáticos en datasets")
    print("-"*80)
    changes = detect_dataset_changes()
    for key, value in changes.items():
        status = "⚠️ CAMBIO" if value else "✅ Sin cambios"
        print(f"{key:.<50} {status}")
    
    print("\n[RESUMEN] Información de datasets")
    print("-"*80)
    for dataset_name, info in DATASET_SUMMARY.items():
        print(f"\n{dataset_name}:")
        for key, value in info.items():
            if key != "ruta":  # Ocultar ruta completa en resumen
                print(f"  {key:.<35} {value}")
    
    print("\n" + "="*80)
    print("NOTA: Rutas FIJAS - Auto-actualización si archivos son reemplazados")
    print("="*80 + "\n")

