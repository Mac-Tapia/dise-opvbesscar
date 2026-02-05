#!/usr/bin/env python3
"""
SCRIPT DE MIGRACIÓN: Dataset Builder Consolidado
Actualiza automáticamente imports en otros archivos
Date: 2026-02-04
"""

from __future__ import annotations
from pathlib import Path
import re
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACIÓN DE MIGRACIÓN
# ============================================================================

REPO_ROOT = Path(__file__).parent

# Archivos que usan dataset_builder imports (excepto los que estamos consolidando)
FILES_TO_UPDATE = [
    "src/iquitos_citylearn/oe3/simulate.py",
    "src/iquitos_citylearn/oe3/agent_interface.py",
    "src/metrics/metric/__init__.py",
    "scripts/run_oe3_build_dataset.py",
]

# Mapeo de imports viejos → nuevos
IMPORT_REPLACEMENTS = {
    # dataset_builder.py
    "from src.citylearnv2.dataset_builder.dataset_builder import build_citylearn_dataset":
        "from src.citylearnv2.dataset_builder.dataset_builder_consolidated import build_citylearn_dataset",

    "from src.citylearnv2.dataset_builder import build_citylearn_dataset":
        "from src.citylearnv2.dataset_builder.dataset_builder_consolidated import build_citylearn_dataset",

    # build_citylearn_dataset.py
    "from src.citylearnv2.dataset_builder.build_citylearn_dataset import CityLearnV2DatasetBuilder":
        "from src.citylearnv2.dataset_builder.dataset_builder_consolidated import CityLearnV2DatasetBuilder",

    # data_loader.py
    "from src.citylearnv2.dataset_builder.data_loader import OE2DataLoader":
        "from src.citylearnv2.dataset_builder.dataset_builder_consolidated import OE2DataLoader",

    "from src.citylearnv2.dataset_builder.data_loader import OE2DataLoaderException":
        "from src.citylearnv2.dataset_builder.dataset_builder_consolidated import OE2DataLoaderException",

    # validate_citylearn_build.py
    "from src.citylearnv2.dataset_builder.validate_citylearn_build import CityLearnDataValidator":
        "from src.citylearnv2.dataset_builder.dataset_builder_consolidated import CityLearnDataValidator",
}

# ============================================================================
# FUNCIONES DE MIGRACIÓN
# ============================================================================

def check_file_exists(file_path: Path) -> bool:
    """Verifica si un archivo existe."""
    if file_path.exists():
        logger.info(f"✅ Encontrado: {file_path}")
        return True
    else:
        logger.warning(f"⚠️  No encontrado: {file_path}")
        return False


def read_file(file_path: Path) -> str | None:
    """Lee el contenido de un archivo."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"❌ Error leyendo {file_path}: {e}")
        return None


def write_file(file_path: Path, content: str) -> bool:
    """Escribe contenido en un archivo."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"❌ Error escribiendo {file_path}: {e}")
        return False


def migrate_imports_in_file(file_path: Path) -> int:
    """
    Migra imports en un archivo individual.
    Retorna: número de replacements realizados
    """
    logger.info(f"\n📝 Procesando: {file_path}")

    content = read_file(file_path)
    if content is None:
        return 0

    original_content = content
    replacement_count = 0

    # Realizar replacements
    for old_import, new_import in IMPORT_REPLACEMENTS.items():
        if old_import in content:
            content = content.replace(old_import, new_import)
            replacement_count += 1
            logger.info(f"  ✅ Replaced: {old_import[:60]}...")

    # Si hubo cambios, guardar
    if replacement_count > 0:
        if write_file(file_path, content):
            logger.info(f"  ✅ {file_path} actualizado ({replacement_count} changes)")
            return replacement_count
        else:
            logger.error(f"  ❌ Error guardando {file_path}")
            return 0
    else:
        logger.info(f"  ℹ️  No changes needed in {file_path}")
        return 0


def show_migration_plan() -> None:
    """Muestra el plan de migración."""
    print("\n" + "="*80)
    print("📋 PLAN DE MIGRACIÓN: Dataset Builder Consolidado")
    print("="*80)
    print("\n1. ARCHIVOS A ACTUALIZAR:")
    for i, file_path in enumerate(FILES_TO_UPDATE, 1):
        full_path = REPO_ROOT / file_path
        exists = "✅" if full_path.exists() else "⚠️"
        print(f"   {i}. {exists} {file_path}")

    print("\n2. IMPORTS QUE SERÁN MIGRADOS:")
    for i, (old, new) in enumerate(IMPORT_REPLACEMENTS.items(), 1):
        print(f"   {i}. {old[:70]}")
        print(f"      → {new[:70]}")

    print("\n3. ARCHIVOS A ELIMINAR (OPCIONAL):")
    old_files = [
        "src/citylearnv2/dataset_builder/build_oe3_dataset.py",
        "src/citylearnv2/dataset_builder/generate_pv_dataset_citylearn.py",
    ]
    for file_path in old_files:
        print(f"   • {file_path} (OBSOLETO)")

    print("\n4. ARCHIVOS A DEPRECAR (OPCIONAL):")
    deprecate_files = [
        "src/citylearnv2/dataset_builder/dataset_builder.py",
        "src/citylearnv2/dataset_builder/build_citylearn_dataset.py",
        "src/citylearnv2/dataset_builder/data_loader.py",
        "src/citylearnv2/dataset_builder/validate_citylearn_build.py",
    ]
    for file_path in deprecate_files:
        print(f"   • {file_path} (Usar dataset_builder_consolidated.py)")

    print("\n" + "="*80)


def migrate_all() -> None:
    """Ejecuta la migración completa."""
    print("\n🚀 INICIANDO MIGRACIÓN...")

    total_changes = 0
    successful_files = 0

    for file_path_str in FILES_TO_UPDATE:
        file_path = REPO_ROOT / file_path_str

        if not file_path.exists():
            logger.warning(f"⏭️  Saltando (no existe): {file_path}")
            continue

        changes = migrate_imports_in_file(file_path)
        if changes > 0:
            total_changes += changes
            successful_files += 1

    print("\n" + "="*80)
    print("📊 RESULTADOS DE MIGRACIÓN")
    print("="*80)
    print(f"Archivos procesados: {successful_files}")
    print(f"Total de cambios: {total_changes}")

    if total_changes > 0:
        print("\n✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("\nProximos pasos:")
        print("  1. Ejecutar tests: python -m pytest tests/ -v")
        print("  2. Verificar imports: python -c 'from src.citylearnv2.dataset_builder.dataset_builder_consolidated import build_citylearn_dataset; print(\"OK\")'")
        print("  3. (Opcional) Eliminar archivos antiguos")
    else:
        print("\n⚠️  No se realizaron cambios. Verifica que los archivos existen.")

    print("\n" + "="*80)


def cleanup_old_files(dry_run: bool = True) -> None:
    """
    Elimina archivos antiguos (CUIDADO: es destructivo)

    Args:
        dry_run: Si True, solo muestra qué se eliminaría
    """
    old_files = [
        "src/citylearnv2/dataset_builder/build_oe3_dataset.py",
        "src/citylearnv2/dataset_builder/generate_pv_dataset_citylearn.py",
        "src/citylearnv2/dataset_builder/dataset_builder.py",
        "src/citylearnv2/dataset_builder/build_citylearn_dataset.py",
        "src/citylearnv2/dataset_builder/data_loader.py",
        "src/citylearnv2/dataset_builder/validate_citylearn_build.py",
    ]

    print("\n" + "="*80)
    if dry_run:
        print("🔍 DRY-RUN: Archivos que PODRÍAN eliminarse")
    else:
        print("⚠️  CUIDADO: Eliminando archivos antiguos")
    print("="*80)

    for file_path_str in old_files:
        file_path = REPO_ROOT / file_path_str

        if file_path.exists():
            if dry_run:
                logger.info(f"[DRY-RUN] Eliminaría: {file_path}")
            else:
                try:
                    file_path.unlink()
                    logger.info(f"✅ Eliminado: {file_path}")
                except Exception as e:
                    logger.error(f"❌ Error eliminando {file_path}: {e}")
        else:
            logger.info(f"ℹ️  No existe (saltando): {file_path}")

    print("\n" + "="*80)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import sys

    # Mostrar plan
    show_migration_plan()

    # Ejecutar migración
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        logger.info("Ejecutando migración...")
        migrate_all()
    else:
        print("\n⚠️  MODO PREVIEW (sin cambios reales)")
        print("   Para ejecutar la migración, usa: python migrate_dataset_builder.py --force")

        # Preview de cambios
        print("\n🔍 PREVIEW DE CAMBIOS:")
        for file_path_str in FILES_TO_UPDATE:
            file_path = REPO_ROOT / file_path_str
            if file_path.exists():
                content = read_file(file_path)
                if content:
                    changes = sum(1 for old_import in IMPORT_REPLACEMENTS if old_import in content)
                    if changes > 0:
                        print(f"  {file_path}: {changes} import(s) que cambiarían")

    # Opción de cleanup
    print("\n🧹 LIMPIEZA DE ARCHIVOS ANTIGUOS")
    print("   Para ver qué se eliminaría: python migrate_dataset_builder.py --cleanup-preview")
    print("   Para eliminar archivos: python migrate_dataset_builder.py --cleanup-force")

    if len(sys.argv) > 1 and sys.argv[1] == "--cleanup-preview":
        cleanup_old_files(dry_run=True)
    elif len(sys.argv) > 1 and sys.argv[1] == "--cleanup-force":
        cleanup_old_files(dry_run=False)
