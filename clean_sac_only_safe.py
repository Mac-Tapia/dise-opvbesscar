#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LIMPIEZA SEGURA - SOLO CHECKPOINTS SAC
=============================================
Protege A2C y PPO al 100%. VALIDA antes de borrar.
Genera reporte detallado de lo que se eliminó.

Uso:
    python clean_sac_only_safe.py --dry-run    # Ver qué se va a borrar SIN borrar
    python clean_sac_only_safe.py --confirm     # Borrar SOLO SAC (protege A2C/PPO)
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# ===== CONFIGURACION =====
CHECKPOINT_DIR = Path('checkpoints')
OUTPUT_DIR = Path('outputs')
PROTECTED_AGENTS = {'A2C', 'PPO'}  # NUNCA borrar estos
TARGET_AGENT = 'SAC'

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def validate_checkpoint_structure() -> Dict[str, List[Path]]:
    """Valida estructura de checkpoints. Devuelve diccionario por agente."""
    checkpoint_data = {agent: [] for agent in ['SAC', 'A2C', 'PPO']}
    
    if not CHECKPOINT_DIR.exists():
        logger.warning(f"❌ CHECKPOINT_DIR no existe: {CHECKPOINT_DIR}")
        return checkpoint_data
    
    # Listar agentes presentes
    for agent_dir in CHECKPOINT_DIR.iterdir():
        if not agent_dir.is_dir():
            continue
            
        agent_name = agent_dir.name.upper()
        if agent_name not in checkpoint_data:
            logger.info(f"⚠️  Agente desconocido (ignorado): {agent_name}")
            continue
        
        # Listar archivos del agente
        checkpoint_files = list(agent_dir.glob('*.zip'))
        checkpoint_data[agent_name] = checkpoint_files
        
        logger.info(f"  {agent_name}: {len(checkpoint_files)} checkpoint(s)")
        for f in sorted(checkpoint_files, key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
            size_mb = f.stat().st_size / 1e6
            logger.info(f"    - {f.name} ({size_mb:.1f} MB)")
    
    return checkpoint_data


def validate_output_structure() -> Dict[str, List[Path]]:
    """Valida agentes en outputs/. Devuelve diccionario por agente."""
    output_data = {agent: [] for agent in ['sac_training', 'a2c_training', 'ppo_training']}
    
    if not OUTPUT_DIR.exists():
        logger.warning(f"❌ OUTPUT_DIR no existe: {OUTPUT_DIR}")
        return output_data
    
    # Buscar directorios de training
    for training_dir in OUTPUT_DIR.iterdir():
        if not training_dir.is_dir():
            continue
            
        dir_name = training_dir.name.lower()
        for key in output_data.keys():
            if key in dir_name or key.split('_')[0] in dir_name:
                files = list(training_dir.glob('*'))
                output_data[key] = files
                if files:
                    logger.info(f"  {training_dir.name}: {len(files)} archivo(s)")
                break
    
    return output_data


def get_deletion_candidates() -> Tuple[List[Path], Dict[str, int]]:
    """Obtiene archivos a BORRAR. PROTEGE A2C/PPO."""
    candidates = []
    stats = {'sac_zip': 0, 'sac_outputs': 0, 'protected': 0}
    
    # CHECKPOINTS A BORRAR
    checkpoint_data = validate_checkpoint_structure()
    sac_checkpoints = checkpoint_data.get('SAC', [])
    if sac_checkpoints:
        candidates.extend(sac_checkpoints)
        stats['sac_zip'] = len(sac_checkpoints)
        logger.info(f"✅ SAC checkpoints a BORRAR: {len(sac_checkpoints)}")
    
    # A2C y PPO - PROTEGIDOS
    for agent in PROTECTED_AGENTS:
        protected_files = checkpoint_data.get(agent, [])
        if protected_files:
            stats['protected'] += len(protected_files)
            logger.info(f"🔒 {agent} PROTEGIDO: {len(protected_files)} checkpoint(s)")
    
    # OUTPUTS A BORRAR
    output_data = validate_output_structure()
    sac_output_files = output_data.get('sac_training', [])
    if sac_output_files:
        # Solo borrar archivos JSON, CSV, TXT (NO directorios)
        sac_files = [f for f in sac_output_files if f.is_file()]
        candidates.extend(sac_files)
        stats['sac_outputs'] = len(sac_files)
        logger.info(f"✅ SAC output files a BORRAR: {len(sac_files)}")
    
    # A2C y PPO en outputs - PROTEGIDOS
    for agent_key in ['a2c_training', 'ppo_training']:
        protected_files = output_data.get(agent_key, [])
        if protected_files:
            stats['protected'] += len(protected_files)
            logger.info(f"🔒 {agent_key} PROTEGIDO: {len(protected_files)} archivo(s)")
    
    return candidates, stats


def print_summary(candidates: List[Path], stats: Dict[str, int], dry_run: bool = True):
    """Imprime resumen de limpieza."""
    print("\n" + "="*80)
    print("RESUMEN LIMPIEZA SAC - OPCION B (2026-02-17)")
    print("="*80)
    
    total_size_mb = sum(f.stat().st_size for f in candidates) / 1e6
    
    print(f"\n📊 ESTADISTICAS:")
    print(f"  - SAC checkpoints a borrar:  {stats['sac_zip']}")
    print(f"  - SAC output files a borrar: {stats['sac_outputs']}")
    print(f"  - Archivos PROTEGIDOS:       {stats['protected']} (A2C + PPO)")
    print(f"  - Total a liberar:           {total_size_mb:.1f} MB")
    
    if candidates:
        print(f"\n📋 ARCHIVOS A BORRAR ({len(candidates)} total):")
        cwd = Path.cwd()
        for f in sorted(candidates):
            try:
                rel_path = f.relative_to(cwd)
            except ValueError:
                rel_path = f
            size_mb = f.stat().st_size / 1e6
            print(f"  ❌ {rel_path} ({size_mb:.1f} MB)")
    
    # Contar archivos protegidos
    a2c_count = len(list((CHECKPOINT_DIR / 'A2C').glob('*.zip'))) if (CHECKPOINT_DIR / 'A2C').exists() else 0
    ppo_count = len(list((CHECKPOINT_DIR / 'PPO').glob('*.zip'))) if (CHECKPOINT_DIR / 'PPO').exists() else 0
    
    print(f"\n🔒 ARCHIVOS PROTEGIDOS:")
    print(f"  ✅ checkpoints/A2C/ - {a2c_count} checkpoint(s)")
    print(f"  ✅ checkpoints/PPO/ - {ppo_count} checkpoint(s)")
    print(f"  ✅ outputs/a2c_training/ - (todos los archivos)")
    print(f"  ✅ outputs/ppo_training/ - (todos los archivos)")
    
    if dry_run:
        print(f"\n⚠️  MODO DRY-RUN: Nada fue borrado. Usar --confirm para ejecutar.")
    else:
        print(f"\n✅ LIMPIEZA COMPLETADA: {len(candidates)} archivo(s) borrado(s)")
    
    print("="*80 + "\n")


def clean_sac(candidates: List[Path], confirm: bool = False) -> bool:
    """Borra archivos candidatos."""
    if not confirm:
        logger.warning("⚠️ Modo dry-run. Use --confirm para ejecutar limpieza.")
        return False
    
    success_count = 0
    error_count = 0
    
    for f in candidates:
        try:
            f.unlink()
            logger.info(f"✅ Borrado: {f.relative_to(Path.cwd())}")
            success_count += 1
        except Exception as e:
            logger.error(f"❌ Error borrando {f.name}: {e}")
            error_count += 1
    
    logger.info(f"\n✅ Limpieza SAC completa: {success_count} OK, {error_count} errores")
    return error_count == 0


def generate_report(candidates: List[Path], stats: Dict[str, int]) -> None:
    """Genera reporte JSON."""
    report = {
        'timestamp': str(Path.cwd()),
        'operation': 'SAC checkpoint cleanup - OPCION B',
        'target_agent': TARGET_AGENT,
        'protected_agents': list(PROTECTED_AGENTS),
        'statistics': stats,
        'files_deleted': [str(f.relative_to(Path.cwd())) for f in candidates],
        'total_size_mb': sum(f.stat().st_size for f in candidates) / 1e6,
    }
    
    report_path = OUTPUT_DIR / 'sac_cleanup_report_2026-02-17.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"📄 Reporte guardado: {report_path}")


def main():
    """Main flow."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Limpieza SAC - Protege A2C/PPO')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Ver qué se va a borrar SIN borrar (default)')
    parser.add_argument('--confirm', action='store_true',
                       help='Ejecutar limpieza real (borra archivos)')
    parser.add_argument('--no-report', action='store_true',
                       help='No generar reporte JSON')
    
    args = parser.parse_args()
    
    # Modo
    if args.confirm:
        if '--dry-run' in sys.argv:
            args.dry_run = False
        else:
            args.dry_run = False
    
    print("\n" + "="*80)
    print("LIMPIEZA SAC - SEGURA Y VALIDADA")
    print("="*80)
    print(f"Modo: {'DRY-RUN' if args.dry_run else 'CONFIRMAR'}")
    print(f"Directorio trabajo: {Path.cwd()}")
    print()
    
    # Validar estructura
    logger.info("🔍 Validando estructura de checkpoints...")
    candidates, stats = get_deletion_candidates()
    
    # Mostrar resumen
    print_summary(candidates, stats, dry_run=args.dry_run)
    
    # Ejecutar limpieza si confirm
    if args.confirm and not args.dry_run:
        success = clean_sac(candidates, confirm=True)
        if success and not args.no_report:
            generate_report(candidates, stats)
        return 0 if success else 1
    else:
        if not args.no_report:
            generate_report(candidates, stats)
        logger.info("💡 Para ejecutar limpieza: python clean_sac_only_safe.py --confirm")
        return 0


if __name__ == '__main__':
    sys.exit(main())
