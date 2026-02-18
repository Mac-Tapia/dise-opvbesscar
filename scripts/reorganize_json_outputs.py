#!/usr/bin/env python
"""
Script para Reorganizar Archivos JSON en outputs/

ACCIONES:
1. Crear carpeta outputs/dataset_validation/ (si no existe)
2. Mover dataset*.json a outputs/dataset_validation/
3. Mover sac*.json (salvo health_check) a outputs/sac_training/
4. Mover validation_sac_oficial.json a outputs/comparative_analysis/
5. ELIMINAR sac_health_check.json (es subsección de sac_posttraining_analysis.json)
6. Mantener complete_metrics.json y real_metrics.json (son complementarios, no duplicados)
"""

from __future__ import annotations

import shutil
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"

# Plan de reorganización
REORGANIZATION_PLAN = {
    # Archivos a MOVER
    "MOVER": [
        # dataset*.json → dataset_validation/
        ("dataset_construction_summary.json", "dataset_validation/"),
        ("dataset_manifest_sac.json", "dataset_validation/"),
        # sac*.json (excepto health_check) → sac_training/
        ("sac_posttraining_analysis.json", "sac_training/"),
        ("sac_training_log.json", "sac_training/"),
        # validacion_sac_oficial.json → comparative_analysis/
        ("validacion_sac_oficial.json", "comparative_analysis/"),
    ],
    # Archivos a ELIMINAR
    "ELIMINAR": [
        "sac_health_check.json",  # Subsección de sac_posttraining_analysis.json
    ],
    # Archivos a MANTENER (ya están en lugar correcto)
    "MANTENER": [
        "sac_training/result_sac.json",
        "ppo_training/result_ppo.json",
        "ppo_training/ppo_training_summary.json",
        "a2c_training/result_a2c.json",
        "comparative_analysis/oe2_4_6_4_evaluation_report.json",
        "real_agent_comparison/real_metrics.json",  # Complementario a complete_metrics.json
        "complete_agent_analysis/complete_metrics.json",  # Complementario a real_metrics.json
        "citylearn_integration/plots/validation_report.json",
    ],
}


def create_directories():
    """Crear carpetas necesarias."""
    logger.info("🐣 CREANDO CARPETAS...")
    
    dirs_to_create = [
        OUTPUTS_DIR / "dataset_validation",
    ]
    
    for dir_path in dirs_to_create:
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"   ✅ Creada: {dir_path.relative_to(OUTPUTS_DIR)}/")
        else:
            logger.info(f"   ℹ️  Existe: {dir_path.relative_to(OUTPUTS_DIR)}/")
    print()


def move_files():
    """Mover archivos a sus carpetas correctas."""
    logger.info("🚚 MOVIENDO ARCHIVOS...")
    print()
    
    moved = 0
    failed = 0
    
    for filename, dest_dir in REORGANIZATION_PLAN["MOVER"]:
        src = OUTPUTS_DIR / filename
        dest = OUTPUTS_DIR / dest_dir / filename
        
        if not src.exists():
            logger.warning(f"   ⚠️  NO ENCONTRADO: {filename}")
            continue
        
        try:
            # Crear carpeta destino si no existe
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            # Mover archivo
            shutil.move(str(src), str(dest))
            logger.info(f"   ✅ {filename}")
            logger.info(f"      └─ → {dest_dir}")
            moved += 1
        except Exception as e:
            logger.error(f"   ❌ Error moviendo {filename}: {e}")
            failed += 1
    
    print()
    logger.info(f"📊 Movidos: {moved}/{len(REORGANIZATION_PLAN['MOVER'])}")
    if failed > 0:
        logger.warning(f"   Fallos: {failed}")
    print()


def delete_duplicates():
    """Eliminar archivos que son duplicados."""
    logger.info("🗑️  ELIMINANDO DUPLICADOS...")
    print()
    
    deleted = 0
    failed = 0
    
    for filename in REORGANIZATION_PLAN["ELIMINAR"]:
        file_path = OUTPUTS_DIR / filename
        
        if not file_path.exists():
            logger.info(f"   ℹ️  No existe: {filename}")
            continue
        
        try:
            file_path.unlink()
            logger.info(f"   ✅ ELIMINADO: {filename}")
            logger.info(f"      (Subsección de sac_posttraining_analysis.json)")
            deleted += 1
        except Exception as e:
            logger.error(f"   ❌ Error eliminando {filename}: {e}")
            failed += 1
    
    print()
    logger.info(f"📊 Eliminados: {deleted}/{len(REORGANIZATION_PLAN['ELIMINAR'])}")
    if failed > 0:
        logger.warning(f"   Fallos: {failed}")
    print()


def verify_organization():
    """Verificar que los archivos estén organizados correctamente."""
    logger.info("=" * 80)
    logger.info("✅ ESTRUCTURA FINAL DE outputs/:")
    logger.info("=" * 80)
    print()
    
    # Listar estructura
    logger.info("outputs/")
    
    # dataset_validation/
    dataset_dir = OUTPUTS_DIR / "dataset_validation"
    if dataset_dir.exists():
        files = list(dataset_dir.glob("*.json"))
        logger.info(f"├── dataset_validation/ ({len(files)} archivos)")
        for f in files:
            logger.info(f"│   ├── {f.name}")
    
    # sac_training/
    sac_dir = OUTPUTS_DIR / "sac_training"
    if sac_dir.exists():
        files = [f for f in sac_dir.glob("*.json")]
        logger.info(f"├── sac_training/ ({len(files)} JSON)")
        for f in sorted(files):
            logger.info(f"│   ├── {f.name}")
    
    # comparative_analysis/
    comp_dir = OUTPUTS_DIR / "comparative_analysis"
    if comp_dir.exists():
        files = [f for f in comp_dir.glob("*.json")]
        logger.info(f"├── comparative_analysis/ ({len(files)} JSON)")
        for f in sorted(files):
            logger.info(f"│   ├── {f.name}")
    
    # ppo_training/
    ppo_dir = OUTPUTS_DIR / "ppo_training"
    if ppo_dir.exists():
        files = [f for f in ppo_dir.glob("*.json")]
        logger.info(f"├── ppo_training/ ({len(files)} JSON)")
        for f in sorted(files):
            logger.info(f"│   ├── {f.name}")
    
    # a2c_training/
    a2c_dir = OUTPUTS_DIR / "a2c_training"
    if a2c_dir.exists():
        files = [f for f in a2c_dir.glob("*.json")]
        logger.info(f"├── a2c_training/ ({len(files)} JSON)")
        for f in sorted(files):
            logger.info(f"│   ├── {f.name}")
    
    print()
    logger.info("=" * 80)
    logger.info("📊 RESUMEN FINAL:")
    logger.info("=" * 80)
    print()
    
    # Contar todos los JSON después de movimiento
    total_json = len(list(OUTPUTS_DIR.rglob("*.json")))
    logger.info(f"Total archivos JSON en outputs/: {total_json}")
    print()
    
    logger.info("✨ Reorganización completada satisfactoriamente")
    print()


def main():
    """Ejecutar reorganización."""
    
    print()
    logger.info("=" * 80)
    logger.info("REORGANIZACIÓN DE ARCHIVOS JSON EN outputs/")
    logger.info("=" * 80)
    print()
    logger.info("📋 PLAN:")
    logger.info(f"   • Crear: outputs/dataset_validation/")
    logger.info(f"   • Mover: {len(REORGANIZATION_PLAN['MOVER'])} archivos")
    logger.info(f"   • Eliminar: {len(REORGANIZATION_PLAN['ELIMINAR'])} duplicados")
    logger.info(f"   • Mantener: {len(REORGANIZATION_PLAN['MANTENER'])} archivos")
    print()
    
    if not OUTPUTS_DIR.exists():
        logger.error(f"❌ Carpeta {OUTPUTS_DIR} no existe")
        return False
    
    # Ejecutar plan
    create_directories()
    move_files()
    delete_duplicates()
    verify_organization()
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
