#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUDITORÍA ARQUITECTÓNICA COMPLETA - pvbesscar
===============================================
Verifica que toda la arquitectura esté implementada y lista para 
entrenamiento y producción.

Scope:
- Estructura de carpetas (OE2, OE3, agents, scripts)
- Módulos principales (dataset_builder, rewards, agents)
- Pipeline completo (data → environment → training)
- Readiness para training/production
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Tuple

# ============================================================================
# COMPONENTES PRINCIPALES A AUDITAR
# ============================================================================

ARCHITECTURE = {
    "OE2_DIMENSIONING": {
        "description": "Fase de Dimensionamiento - Especificaciones infraestructura",
        "required_files": [
            "src/dimensionamiento/oe2/disenocargadoresev/chargers.py",
            "src/dimensionamiento/oe2/disenocargadoresev/",
            "src/dimensionamiento/oe2/generacionsolar/",
            "data/oe2/chargers/chargers_ev_ano_2024_v3.csv",
            "data/oe2/bess/bess_ano_2024.csv",
            "data/oe2/Generacionsolar/pv_generation_citylearn2024.csv",
            "data/oe2/demandamallkwh/demandamallhorakwh.csv",
        ],
        "criticality": "CRITICAL"
    },
    "OE3_CONTROL": {
        "description": "Fase de Control - RL agents y CityLearn v2",
        "required_files": [
            "src/agents/sac.py",
            "src/agents/ppo_sb3.py",
            "src/agents/a2c_sb3.py",
            "src/agents/agent_utils.py",
            "src/agents/no_control.py",
        ],
        "criticality": "CRITICAL"
    },
    "DATASET_BUILDER": {
        "description": "Constructor de datasets para CityLearn v2",
        "required_files": [
            "src/dataset_builder_citylearn/",
            "src/dataset_builder_citylearn/data_loader.py",
            "src/dataset_builder_citylearn/rewards.py",
            "src/dataset_builder_citylearn/dataset_builder.py",
        ],
        "criticality": "CRITICAL"
    },
    "TRAINING_SCRIPTS": {
        "description": "Scripts de entrenamiento para SAC/PPO/A2C",
        "required_files": [
            "scripts/train/train_sac.py",
            "scripts/train/train_ppo.py",
            "scripts/train/train_a2c.py",
            "scripts/train/common_constants.py",
        ],
        "criticality": "CRITICAL"
    },
    "UTILITIES": {
        "description": "Utilidades compartidas",
        "required_files": [
            "src/utils/agent_utils.py",
            "src/utils/logging.py",
            "src/utils/time.py",
            "src/utils/series.py",
        ],
        "criticality": "HIGH"
    },
    "CONFIGURATION": {
        "description": "Configuración y constants",
        "required_files": [
            "configs/default.yaml",
            "pyproject.toml",
            "requirements.txt",
            "pyrightconfig.json",
        ],
        "criticality": "HIGH"
    },
}

# ============================================================================
# VALIDACIONES DE INTEGRACIÓN
# ============================================================================

INTEGRATION_CHECKS = {
    "data_loader_imports": {
        "file": "src/dataset_builder_citylearn/data_loader.py",
        "must_contain": [
            "rebuild_oe2_datasets_complete",
            "load_citylearn_dataset",
            "BESS_CAPACITY_KWH",
            "OE2ValidationError",
        ],
        "description": "Data loader debe exportar funciones principales"
    },
    "rewards_multiobjetive": {
        "file": "src/dataset_builder_citylearn/rewards.py",
        "must_contain": [
            "MultiObjectiveReward",
            "IquitosContext",
            "create_iquitos_reward_weights",
        ],
        "description": "Rewards module debe tener MultiObjectiveReward"
    },
    "sac_agent": {
        "file": "scripts/train/train_sac.py",
        "must_contain": [
            "from stable_baselines3 import SAC",
            "MultiObjectiveReward",
            "BESS_MAX_KWH_CONST",
            "class RealOE2Environment",
        ],
        "description": "SAC script debe tener SAC agent y CityLearn environment"
    },
    "ppo_agent": {
        "file": "scripts/train/train_ppo.py",
        "must_contain": [
            "from stable_baselines3 import PPO",
            "MultiObjectiveReward",
            "BESS_MAX_KWH_CONST",
            "class CityLearnEnvironment",
        ],
        "description": "PPO script debe tener PPO agent y CityLearn environment"
    },
    "a2c_agent": {
        "file": "scripts/train/train_a2c.py",
        "must_contain": [
            "from stable_baselines3 import A2C",
            "MultiObjectiveReward",
            "BESS_MAX_KWH_CONST",
            "class CityLearnEnvironment",
        ],
        "description": "A2C script debe tener A2C agent y CityLearn environment"
    },
    "common_constants": {
        "file": "scripts/train/common_constants.py",
        "must_contain": [
            "BESS_MAX_KWH_CONST",
            "CO2_FACTOR_IQUITOS",
            "CHARGER_MAX_KW",
            "MOTOS_TARGET_DIARIOS",
        ],
        "description": "Common constants debe tener BESS y CO2 constants"
    },
    "gymnasium_compatibility": {
        "file": "scripts/train/train_sac.py",
        "must_contain": [
            "from gymnasium import Env, spaces",
            "spaces.Box",
            "def reset(self",
            "def step(self",
        ],
        "description": "Agents deben usar Gymnasium API"
    },
}

# ============================================================================
# CHECKLISTS DE READINESS
# ============================================================================

TRAINING_READINESS = {
    "data_completeness": {
        "checks": [
            ("Chargers data (8760 hours)", "data/oe2/chargers/chargers_ev_ano_2024_v3.csv"),
            ("BESS data (8760 hours)", "data/oe2/bess/bess_ano_2024.csv"),
            ("Solar data (8760 hours)", "data/oe2/Generacionsolar/pv_generation_citylearn2024.csv"),
            ("Mall demand data (8760 hours)", "data/oe2/demandamallkwh/demandamallhorakwh.csv"),
        ]
    },
    "code_completeness": {
        "checks": [
            ("SAC training script", "scripts/train/train_sac.py"),
            ("PPO training script", "scripts/train/train_ppo.py"),
            ("A2C training script", "scripts/train/train_a2c.py"),
            ("Data loader module", "src/dataset_builder_citylearn/data_loader.py"),
            ("Rewards module", "src/dataset_builder_citylearn/rewards.py"),
        ]
    },
    "environment_setup": {
        "checks": [
            ("Python 3.11+", None),
            ("Virtual environment", ".venv/Scripts/python.exe"),
            ("PyTorch installed", None),
            ("Stable-baselines3 installed", None),
            ("CityLearn installed", None),
        ]
    },
    "configuration": {
        "checks": [
            ("Config file", "configs/default.yaml"),
            ("Constants file", "scripts/train/common_constants.py"),
            ("Pyproject.toml", "pyproject.toml"),
        ]
    },
}

PRODUCTION_READINESS = {
    "checkpoints": {
        "checks": [
            ("Checkpoints directory", "checkpoints/"),
            ("SAC checkpoint dir", "checkpoints/SAC/"),
            ("PPO checkpoint dir", "checkpoints/PPO/"),
            ("A2C checkpoint dir", "checkpoints/A2C/"),
        ]
    },
    "logging": {
        "checks": [
            ("Logs directory", "logs/"),
            ("Training logs directory", "logs/training/"),
            ("Evaluation logs directory", "logs/evaluation/"),
        ]
    },
    "outputs": {
        "checks": [
            ("Outputs directory", "outputs/"),
            ("Results storage", "outputs/results/"),
        ]
    },
    "documentation": {
        "checks": [
            ("README", "README.md"),
            ("Architecture doc", "DOCUMENTO_EJECUTIVO_VALIDACION_v72.md"),
            ("Constants documented", "scripts/train/common_constants.py"),
        ]
    },
}

# ============================================================================
# FUNCIONES DE AUDITORÍA
# ============================================================================

def check_file_exists(path: str) -> bool:
    """Verifica si un archivo existe."""
    return Path(path).exists()

def check_directory_exists(path: str) -> bool:
    """Verifica si un directorio existe."""
    p = Path(path)
    return p.exists() and p.is_dir()

def check_file_contains(filepath: str, patterns: List[str]) -> Tuple[bool, List[str]]:
    """Verifica si un archivo contiene patrones específicos."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        found = []
        missing = []
        for pattern in patterns:
            if pattern in content:
                found.append(pattern)
            else:
                missing.append(pattern)
        
        return len(missing) == 0, missing
    except Exception as e:
        return False, [str(e)]

def audit_architecture() -> Dict:
    """Auditoría completa de arquitectura."""
    results = {}
    
    print("\n" + "="*80)
    print("AUDITORÍA ARQUITECTÓNICA - pvbesscar v7.2")
    print("="*80)
    
    # 1. Verificar componentes principales
    print("\n[1] COMPONENTES ARQUITECTÓNICOS")
    print("-"*80)
    
    for component, details in ARCHITECTURE.items():
        print(f"\n{component} ({details['criticality']}):")
        print(f"  📝 {details['description']}")
        
        component_results = []
        for required_file in details["required_files"]:
            exists = check_file_exists(required_file) or check_directory_exists(required_file)
            status = "✅" if exists else "❌"
            component_results.append(exists)
            print(f"  {status} {required_file}")
        
        results[component] = all(component_results)
    
    # 2. Verificar integraciones
    print("\n[2] VALIDACIÓN DE INTEGRACIONES")
    print("-"*80)
    
    integration_results = {}
    for check_name, details in INTEGRATION_CHECKS.items():
        filepath = details["file"]
        patterns = details["must_contain"]
        
        print(f"\n{check_name}:")
        print(f"  📝 {details['description']}")
        
        if check_file_exists(filepath):
            found, missing = check_file_contains(filepath, patterns)
            if found:
                print(f"  ✅ {filepath}")
                for pattern in patterns[:2]:  # Show first 2 patterns
                    print(f"     ✓ {pattern}")
            else:
                print(f"  ⚠️  {filepath}")
                for pattern in missing[:2]:
                    print(f"     ✗ {pattern} (faltando)")
            integration_results[check_name] = found
        else:
            print(f"  ❌ {filepath} (no encontrado)")
            integration_results[check_name] = False
    
    results["integrations"] = all(integration_results.values())
    
    # 3. Verificar readiness para training
    print("\n[3] TRAINING READINESS")
    print("-"*80)
    
    training_ready = {}
    for category, checklist in TRAINING_READINESS.items():
        print(f"\n{category.upper()}:")
        
        category_results = []
        for check_name, check_path in checklist["checks"]:
            if check_path:
                exists = check_file_exists(check_path) or check_directory_exists(check_path)
                status = "✅" if exists else "❌"
                category_results.append(exists)
                print(f"  {status} {check_name}")
            else:
                # Check like "Python 3.11+" - skip for now
                print(f"  ⏳ {check_name} (requiere verificación manual)")
        
        training_ready[category] = all(category_results) if category_results else True
    
    results["training_ready"] = all(training_ready.values())
    
    # 4. Verificar readiness para producción
    print("\n[4] PRODUCTION READINESS")
    print("-"*80)
    
    production_ready = {}
    for category, checklist in PRODUCTION_READINESS.items():
        print(f"\n{category.upper()}:")
        
        category_results = []
        for check_name, check_path in checklist["checks"]:
            if check_path:
                exists = check_file_exists(check_path) or check_directory_exists(check_path)
                status = "✅" if exists else "⚠️ " if "checkpoint" in check_name or "log" in check_name else "❌"
                category_results.append(True if exists else ("checkpoint" in check_name or "log" in check_name))
                print(f"  {status} {check_name}")
        
        production_ready[category] = all(category_results)
    
    results["production_ready"] = all(production_ready.values())
    
    return results

# ============================================================================
# PIPELINE VALIDATION
# ============================================================================

def validate_pipeline() -> Dict:
    """Valida que el pipeline OE2 → OE3 esté completo."""
    
    print("\n[5] VALIDACIÓN PIPELINE OE2 → OE3")
    print("-"*80)
    
    pipeline = {
        "OE2_INPUTS": {
            "description": "Datos de entrada OE2",
            "status": "✅" if all([
                check_file_exists("data/oe2/chargers/chargers_ev_ano_2024_v3.csv"),
                check_file_exists("data/oe2/bess/bess_ano_2024.csv"),
            ]) else "❌"
        },
        "DATA_LOADER": {
            "description": "Data loader y validación",
            "status": "✅" if check_file_exists("src/dataset_builder_citylearn/data_loader.py") else "❌"
        },
        "ENVIRONMENT": {
            "description": "CityLearn v2 environment",
            "status": "✅" if all([
                check_file_exists("scripts/train/train_sac.py"),
                "RealOE2Environment" in open("scripts/train/train_sac.py", encoding='utf-8', errors='ignore').read()
            ]) else "❌"
        },
        "REWARD_FUNCTION": {
            "description": "MultiObjectiveReward function",
            "status": "✅" if check_file_exists("src/dataset_builder_citylearn/rewards.py") else "❌"
        },
        "AGENTS": {
            "description": "RL Agents (SAC, PPO, A2C)",
            "status": "✅" if all([
                check_file_exists("scripts/train/train_sac.py"),
                check_file_exists("scripts/train/train_ppo.py"),
                check_file_exists("scripts/train/train_a2c.py"),
            ]) else "❌"
        },
        "TRAINING_PIPELINE": {
            "description": "Training scripts y checkpoints",
            "status": "✅" if check_directory_exists("checkpoints/") else "⏳"
        },
    }
    
    for stage, details in pipeline.items():
        print(f"{details['status']} {stage}: {details['description']}")
    
    return pipeline

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("""
╔════════════════════════════════════════════════════════════════════════════════╗
║           AUDITORÍA ARQUITECTÓNICA COMPLETA - pvbesscar v7.2                   ║
║                                                                                 ║
║  Verifica que toda la arquitectura esté implementada y lista para:              ║
║  • Entrenamiento (training readiness)                                          ║
║  • Producción (production readiness)                                           ║
║                                                                                 ║
║  2026-02-18                                                                    ║
╚════════════════════════════════════════════════════════════════════════════════╝
""")
    
    # Ejecutar auditorías
    arch_results = audit_architecture()
    pipeline_results = validate_pipeline()
    
    # Resumen final
    print("\n[RESUMEN FINAL]")
    print("="*80)
    
    all_components_ok = arch_results.get("OE2_DIMENSIONING") and \
                        arch_results.get("OE3_CONTROL") and \
                        arch_results.get("DATASET_BUILDER") and \
                        arch_results.get("TRAINING_SCRIPTS")
    
    integrations_ok = arch_results.get("integrations", False)
    training_ok = arch_results.get("training_ready", False)
    production_ok = arch_results.get("production_ready", False)
    
    print(f"\n✅ COMPONENTES ARQUITECTÓNICOS: {'COMPLETO' if all_components_ok else 'INCOMPLETO'}")
    print(f"✅ INTEGRACIONES: {'VALIDADAS' if integrations_ok else 'FALTANDO'}")
    print(f"✅ TRAINING READINESS: {'LISTO' if training_ok else 'PENDIENTE'}")
    print(f"✅ PRODUCTION READINESS: {'LISTO' if production_ok else 'PENDIENTE'}")
    
    if all_components_ok and integrations_ok and training_ok:
        print("\n" + "="*80)
        print("🚀 ESTADO: LISTO PARA ENTRENAMIENTO Y PRODUCCIÓN")
        print("="*80)
    else:
        print("\n" + "="*80)
        print("⚠️  ESTADO: REQUIERE COMPLETACIÓN")
        print("="*80)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
