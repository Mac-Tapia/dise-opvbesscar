#!/usr/bin/env python
"""
Análisis y Reorganización de Archivos JSON en carpeta outputs/

OBJETIVO:
1. Verificar qué hacen los archivos JSON
2. Identificar su categoría (dataset, training, analysis, validation)
3. Moverlos a su carpeta correspondiente
4. Detectar y eliminar duplicados
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

OUTPUTS_DIR = Path(__file__).parent / "outputs"

# Mapa de archivos JSON a su categoría y destino
JSON_FILES_ANALYSIS = {
    # ========== EN RAÍZ DE outputs/ - DEBEN MOVERSE ==========
    "dataset_construction_summary.json": {
        "category": "DATASET",
        "current_location": "outputs/",
        "destination": "outputs/dataset_validation/",
        "purpose": "Resumen de hora de construcción del dataset (solar, chargers, mall, BESS)",
        "action": "🔴 MOVER a outputs/dataset_validation/",
        "duplicate_of": None,
    },
    "dataset_manifest_sac.json": {
        "category": "DATASET",
        "current_location": "outputs/",
        "destination": "outputs/dataset_validation/",
        "purpose": "Manifiesto de archivos y validaciones de dataset para SAC",
        "action": "🔴 MOVER a outputs/dataset_validation/",
        "duplicate_of": None,
    },
    "sac_health_check.json": {
        "category": "SAC_TRAINING",
        "current_location": "outputs/",
        "destination": "outputs/sac_training/",
        "purpose": "Verificación de salud del entrenamiento SAC (checkpoint, datos)",
        "action": "🔴 MOVER a outputs/sac_training/",
        "duplicate_of": "sac_posttraining_analysis.json (parcial)",
    },
    "sac_posttraining_analysis.json": {
        "category": "SAC_TRAINING",
        "current_location": "outputs/",
        "destination": "outputs/sac_training/",
        "purpose": "Análisis post-entrenamiento SAC (integra health_check + validation)",
        "action": "🔴 MOVER a outputs/sac_training/ (versión más completa)",
        "duplicate_of": None,
    },
    "sac_training_log.json": {
        "category": "SAC_TRAINING",
        "current_location": "outputs/",
        "destination": "outputs/sac_training/",
        "purpose": "Log de entrenamiento SAC con episodios y checkpoints",
        "action": "🔴 MOVER a outputs/sac_training/",
        "duplicate_of": None,
    },
    "validacion_sac_oficial.json": {
        "category": "VALIDATION",
        "current_location": "outputs/",
        "destination": "outputs/comparative_analysis/",
        "purpose": "Validación oficial de SAC con rankings de agentes (SAC 8.2, PPO 5.9, A2C 5.0)",
        "action": "🔴 MOVER a outputs/comparative_analysis/",
        "duplicate_of": None,
    },
    
    # ========== YA EN CARPETAS CORRECTAS ==========
    "sac_training/result_sac.json": {
        "category": "SAC_TRAINING",
        "current_location": "outputs/sac_training/",
        "destination": "outputs/sac_training/",
        "purpose": "Resultados completos de entrenamiento SAC (18,556 líneas)",
        "action": "✅ MANTENER (ya está en lugar correcto)",
        "duplicate_of": None,
    },
    "ppo_training/result_ppo.json": {
        "category": "PPO_TRAINING",
        "current_location": "outputs/ppo_training/",
        "destination": "outputs/ppo_training/",
        "purpose": "Resultados completos de entrenamiento PPO",
        "action": "✅ MANTENER (ya está en lugar correcto)",
        "duplicate_of": None,
    },
    "a2c_training/result_a2c.json": {
        "category": "A2C_TRAINING",
        "current_location": "outputs/a2c_training/",
        "destination": "outputs/a2c_training/",
        "purpose": "Resultados completos de entrenamiento A2C",
        "action": "✅ MANTENER (ya está en lugar correcto)",
        "duplicate_of": None,
    },
    "ppo_training/ppo_training_summary.json": {
        "category": "PPO_TRAINING",
        "current_location": "outputs/ppo_training/",
        "destination": "outputs/ppo_training/",
        "purpose": "Resumen de entrenamiento PPO",
        "action": "✅ MANTENER (ya está en lugar correcto)",
        "duplicate_of": None,
    },
    "real_agent_comparison/real_metrics.json": {
        "category": "VALIDATION",
        "current_location": "outputs/real_agent_comparison/",
        "destination": "outputs/comparative_analysis/",
        "purpose": "Comparación de métricas reales de A2C, PPO, SAC",
        "action": "⚠️ CONSIDERAR MOVER a outputs/comparative_analysis/",
        "duplicate_of": None,
    },
    "comparative_analysis/oe2_4_6_4_evaluation_report.json": {
        "category": "ANALYSIS",
        "current_location": "outputs/comparative_analysis/",
        "destination": "outputs/comparative_analysis/",
        "purpose": "Reporte de evaluación OE2 v4.6.4",
        "action": "✅ MANTENER (ya está en lugar correcto)",
        "duplicate_of": None,
    },
    "complete_agent_analysis/complete_metrics.json": {
        "category": "ANALYSIS",
        "current_location": "outputs/complete_agent_analysis/",
        "destination": "outputs/comparative_analysis/",
        "purpose": "Análisis completo de métricas de todos los agentes",
        "action": "⚠️ CONSIDERAR MOVER a outputs/comparative_analysis/",
        "duplicate_of": "real_agent_comparison/real_metrics.json (probablemente)",
    },
    "citylearn_integration/plots/validation_report.json": {
        "category": "VALIDATION",
        "current_location": "outputs/citylearn_integration/plots/",
        "destination": "outputs/citylearn_integration/",
        "purpose": "Reporte de validación de integración CityLearn",
        "action": "⚠️ CONSIDERAR MOVER nivel arriba a outputs/citylearn_integration/",
        "duplicate_of": None,
    },
}

def analyze_json_files():
    """Analizar archivos JSON en outputs/."""
    
    print("=" * 80)
    print("ANÁLISIS DE ARCHIVOS JSON EN outputs/")
    print("=" * 80)
    print()
    
    # Contar por categoría
    categories: Dict[str, int] = {}
    actions: Dict[str, List[str]] = {
        "🔴 MOVER": [],
        "✅ MANTENER": [],
        "⚠️ CONSIDERAR": [],
    }
    
    for filename, info in JSON_FILES_ANALYSIS.items():
        cat = info["category"]
        categories[cat] = categories.get(cat, 0) + 1
        
        action = info["action"].split()[0] + " " + info["action"].split()[1]
        if action not in actions:
            action = info["action"][:15]
        
        actions.setdefault(action, []).append(filename)
    
    # Mostrar por categoría
    print("📊 ARCHIVOS POR CATEGORÍA:")
    print()
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count} archivos")
    print()
    
    # Mostrar archivos a mover
    print("=" * 80)
    print("🔴 ARCHIVOS EN RAÍZ DE outputs/ QUE DEBEN MOVERSE:")
    print("=" * 80)
    print()
    
    files_to_move = []
    for filename, info in JSON_FILES_ANALYSIS.items():
        if info["action"].startswith("🔴"):
            files_to_move.append((filename, info))
            print(f"📄 {filename}")
            print(f"   Categoría: {info['category']}")
            print(f"   Propósito: {info['purpose']}")
            print(f"   Mover a: {info['destination']}")
            if info['duplicate_of']:
                print(f"   ⚠️  Posible duplicado: {info['duplicate_of']}")
            print()
    
    # Mostrar duplicados
    print("=" * 80)
    print("⚠️  POSIBLES DUPLICADOS:")
    print("=" * 80)
    print()
    
    duplicates = {}
    for filename, info in JSON_FILES_ANALYSIS.items():
        if info['duplicate_of']:
            if info['duplicate_of'] not in duplicates:
                duplicates[info['duplicate_of']] = []
            duplicates[info['duplicate_of']].append(filename)
    
    if duplicates:
        for dup_of, files in duplicates.items():
            print(f"  {dup_of}:")
            for f in files:
                print(f"    ├─ {f}")
    else:
        print("  No duplicados detectados (verificar manualmente contenido similar)")
    print()
    
    # Resumen de acciones
    print("=" * 80)
    print("📋 RESUMEN DE ACCIONES:")
    print("=" * 80)
    print()
    
    print(f"✅ MANTENER EN LUGAR: {len([f for f, i in JSON_FILES_ANALYSIS.items() if i['action'].startswith('✅')])} archivos")
    print(f"🔴 MOVER: {len(files_to_move)} archivos")
    print(f"⚠️  REVISAR: {len([f for f, i in JSON_FILES_ANALYSIS.items() if i['action'].startswith('⚠️')])} archivos")
    print()
    
    # Plan de consolidación de carpetas
    print("=" * 80)
    print("🎯 PLAN DE CONSOLIDACIÓN DE CARPETAS:")
    print("=" * 80)
    print()
    
    print("CARPETAS RECOMENDADAS DESPUÉS DE REORGANIZACIÓN:")
    print()
    print("outputs/")
    print("├── dataset_validation/           [NUEVA - agrupa dataset_*.json]")
    print("│   ├── dataset_construction_summary.json")
    print("│   └── dataset_manifest_sac.json")
    print("├── sac_training/")
    print("│   ├── result_sac.json           [EXISTENTE]")
    print("│   ├── sac_training_log.json     [MOVER desde raíz]")
    print("│   ├── sac_posttraining_analysis.json [MOVER desde raíz - REEMPLAZA health_check]")
    print("│   └── checkpoints/              [MAPEAR si existen]")
    print("├── ppo_training/")
    print("│   ├── result_ppo.json           [EXISTENTE]")
    print("│   ├── ppo_training_summary.json [EXISTENTE]")
    print("│   └── checkpoints/")
    print("├── a2c_training/")
    print("│   ├── result_a2c.json           [EXISTENTE]")
    print("│   └── checkpoints/")
    print("├── comparative_analysis/")
    print("│   ├── validacion_sac_oficial.json [MOVER desde raíz]")
    print("│   ├── real_agent_comparison/    [POSIBLEMENTE FUSIONAR]")
    print("│   │   ├── real_metrics.json     [CONSIDERAR CONSOLIDAR]")
    print("│   ├── complete_agent_analysis/  [POSIBLEMENTE FUSIONAR]")
    print("│   │   └── complete_metrics.json [VERIFICAR DUPLICADO]")
    print("│   └── oe2_4_6_4_evaluation_report.json [EXISTENTE]")
    print("├── citylearn_integration/")
    print("│   ├── validation_report.json    [MOVER una carpeta arriba]")
    print("│   └── plots/")
    print("├── baselines/")
    print("├── analysis/")
    print("├── results/")
    print("└── sac_metrics/")
    print()
    
    return files_to_move


def check_duplicates_detailed():
    """Verificar duplicados más detalladamente."""
    
    print("=" * 80)
    print("🔍 VALIDACIÓN DETALLADA DE POSIBLES DUPLICADOS:")
    print("=" * 80)
    print()
    
    duplicates_check = [
        ("outputs/sac_health_check.json", "outputs/sac_posttraining_analysis.json", 
         "sac_health_check.json es subsección de sac_posttraining_analysis.json"),
        ("outputs/complete_agent_analysis/complete_metrics.json", 
         "outputs/real_agent_comparison/real_metrics.json",
         "Ambos miden SAC/PPO/A2C - REVISAR si son idénticos o complementarios"),
    ]
    
    for file1, file2, note in duplicates_check:
        path1 = OUTPUTS_DIR / file1.replace("outputs/", "")
        path2 = OUTPUTS_DIR / file2.replace("outputs/", "")
        
        print(f"📌 {file1}")
        print(f"   vs")
        print(f"📌 {file2}")
        print(f"   Nota: {note}")
        print()
    
    print("✅ RESOLUCIÓN RECOMENDADA:")
    print("   1. sac_health_check.json → ELIMINAR (subsección de sac_posttraining_analysis.json)")
    print("   2. complete_metrics.json vs real_metrics.json → VERIFICAR contenido")
    print("      - Si son idénticos: Mantener uno, eliminar otro")
    print("      - Si son complementarios: Mantener ambos en comparative_analysis/")
    print()


if __name__ == "__main__":
    files_to_move = analyze_json_files()
    check_duplicates_detailed()
    
    print("=" * 80)
    print("✨ ANÁLISIS COMPLETADO")
    print("=" * 80)
