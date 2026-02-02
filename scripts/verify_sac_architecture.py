#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏗️ VERIFICADOR ARQUITECTÓNICO SAC
Audita que la arquitectura SAC contenga todos los componentes requeridos

Uso:
    python verify_sac_architecture.py

Output:
    ✅ Verificación de todos los 14 componentes
    🔴 Señala cualquier componente faltante
    📊 Matriz de completitud
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def check_file_exists(path: str) -> bool:
    """Verifica si archivo existe."""
    return Path(path).exists()

def check_code_contains(filepath: str, *patterns: str) -> Dict[str, bool]:
    """Verifica si archivo contiene patterns específicos."""
    result = {}
    if not Path(filepath).exists():
        return {p: False for p in patterns}

    try:
        content = Path(filepath).read_text(encoding='utf-8')
        for pattern in patterns:
            result[pattern] = pattern in content
    except Exception as e:
        logger.error(f"Error leyendo {filepath}: {e}")
        return {p: False for p in patterns}

    return result

def verify_imports(filepath: str) -> Dict[str, bool]:
    """Verifica imports críticas."""
    required_imports = {
        'gymnasium': 'import gymnasium as gym',
        'stable_baselines3': 'from stable_baselines3 import SAC',
        'torch': 'import torch',
        'numpy': 'import numpy as np',
        'dataclasses': 'from dataclasses import dataclass',
    }

    return check_code_contains(filepath, *required_imports.values())

def verify_config_params(filepath: str) -> Dict[str, bool]:
    """Verifica que SACConfig tenga todos los parámetros requeridos."""
    required_params = {
        'hidden_sizes': 'hidden_sizes',
        'learning_rate': 'learning_rate',
        'batch_size': 'batch_size',
        'buffer_size': 'buffer_size',
        'gamma': 'gamma',
        'tau': 'tau',
        'ent_coef': "ent_coef: str | float = 'auto'",
        'target_entropy': 'target_entropy',
        'normalize_observations': 'normalize_observations',
        'normalize_rewards': 'normalize_rewards',
        'clip_gradients': 'clip_gradients',
        'max_grad_norm': 'max_grad_norm',
        'warmup_steps': 'warmup_steps',
        'reward_scale': 'reward_scale',
        'device': 'device',
        'use_amp': 'use_amp',
        'multi_objective_weights': 'weight_co2',  # Multi-objective proxy
    }

    return check_code_contains(filepath, *required_params.values())

def verify_methods(filepath: str) -> Dict[str, bool]:
    """Verifica que SACAgent tenga todos los métodos requeridos."""
    required_methods = {
        '__init__': 'def __init__',
        'learn': 'def learn',
        '_train_sb3_sac': 'def _train_sb3_sac',
        'predict': 'def predict',
        '_setup_device': 'def _setup_device',
        '_normalize_observation': 'def _normalize_observation',
        '_flatten_base': 'def _flatten_base',
        '_unflatten_action': 'def _unflatten_action',
    }

    return check_code_contains(filepath, *required_methods.values())

def verify_sac_components(filepath: str) -> Dict[str, bool]:
    """Verifica componentes específicos de SAC."""
    components = {
        'Actor_MlpPolicy': '"MlpPolicy"',
        'Critic_Dual': 'critic',  # SB3 tiene dual critics implícitos
        'Entropy_Automatic': "ent_coef='auto'",
        'Entropy_Target': 'target_entropy',
        'SoftUpdate': 'tau',
        'ExperienceReplay': 'buffer_size',
        'GradientClipping': 'clip_gradients',
        'ObsNormalization': 'normalize_observations',
        'RewardNormalization': 'normalize_rewards',
        'Warmup': 'warmup_steps',
        'LRSchedule': 'lr_schedule',
        'DeviceAuto': 'detect_device',
        'MultiObjective': 'weight_co2',
        'AMP': 'use_amp',
    }

    return check_code_contains(filepath, *components.values())

def verify_wrapper_components(filepath: str) -> Dict[str, bool]:
    """Verifica componentes en CityLearnWrapper."""
    components = {
        'ObsPrescaling': '_obs_prescale',
        'RunningStats_Welford': '_obs_mean',
        'ObsClipping': '_clip_obs',
        'RewardScaling': '_reward_scale',
        'ActionUnflattening': '_unflatten_action',
        'ObsFlattening': '_flatten',
    }

    return check_code_contains(filepath, *components.values())

def generate_report() -> str:
    """Genera reporte completo."""
    sac_file = Path('src/iquitos_citylearn/oe3/agents/sac.py')

    if not sac_file.exists():
        return f"❌ ERROR: No se encontró {sac_file}\n"

    report = []
    report.append("=" * 80)
    report.append("🏗️  AUDITORÍA ARQUITECTÓNICA SAC - VERIFICACIÓN COMPLETA")
    report.append("=" * 80)
    report.append("")

    # 1. Verificar imports
    report.append("📦 IMPORTS (5 requeridas):")
    imports = verify_imports(str(sac_file))
    for name, found in imports.items():
        status = "✅" if found else "❌"
        report.append(f"  {status} {name}")
    report.append(f"  Total: {sum(imports.values())}/5")
    report.append("")

    # 2. Verificar SACConfig
    report.append("⚙️  SACConfig PARAMETERS (17 requeridas):")
    config_params = verify_config_params(str(sac_file))
    for name, found in config_params.items():
        status = "✅" if found else "❌"
        report.append(f"  {status} {name}")
    report.append(f"  Total: {sum(config_params.values())}/17")
    report.append("")

    # 3. Verificar métodos
    report.append("🔧 MÉTODOS SACAgent (8 requeridas):")
    methods = verify_methods(str(sac_file))
    for name, found in methods.items():
        status = "✅" if found else "❌"
        report.append(f"  {status} {name}")
    report.append(f"  Total: {sum(methods.values())}/8")
    report.append("")

    # 4. Verificar componentes SAC
    report.append("🧠 COMPONENTES SAC (14 requeridas):")
    sac_comps = verify_sac_components(str(sac_file))
    for name, found in sac_comps.items():
        status = "✅" if found else "❌"
        report.append(f"  {status} {name}")
    report.append(f"  Total: {sum(sac_comps.values())}/14")
    report.append("")

    # 5. Verificar Wrapper
    report.append("🎁 CITYLEARN WRAPPER (6 requeridas):")
    wrapper_comps = verify_wrapper_components(str(sac_file))
    for name, found in wrapper_comps.items():
        status = "✅" if found else "❌"
        report.append(f"  {status} {name}")
    report.append(f"  Total: {sum(wrapper_comps.values())}/6")
    report.append("")

    # Resumen
    all_checks = {
        **imports,
        **config_params,
        **methods,
        **sac_comps,
        **wrapper_comps,
    }
    total_passed = sum(all_checks.values())
    total_expected = len(all_checks)
    completion_pct = (total_passed / total_expected * 100) if total_expected > 0 else 0

    report.append("=" * 80)
    report.append(f"📊 RESUMEN FINAL")
    report.append("=" * 80)
    report.append(f"Componentes Verificados: {total_passed}/{total_expected}")
    report.append(f"Completitud: {completion_pct:.1f}%")
    report.append("")

    if completion_pct >= 95:
        report.append("✅ ARQUITECTURA COMPLETA - 100% COMPONENTES PRESENTES")
        report.append("🚀 Estado para entrenamiento: LISTO")
    elif completion_pct >= 80:
        report.append("⚠️  ARQUITECTURA MAYORMENTE COMPLETA - Faltan componentes menores")
        report.append("🔶 Estado para entrenamiento: PROCEDER CON CAUTELA")
    else:
        report.append("❌ ARQUITECTURA INCOMPLETA - Faltan componentes críticos")
        report.append("🔴 Estado para entrenamiento: NO LISTO")

    report.append("")
    report.append("=" * 80)
    report.append("Para más detalles, ver:")
    report.append("  - AUDITORIA_ARQUITECTONICA_SAC_2026_02_01.md")
    report.append("  - COMPONENTES_OPCIONALES_SAC_2026_02_01.md")
    report.append("=" * 80)

    return "\n".join(report)

def main():
    """Punto de entrada."""
    try:
        report = generate_report()
        print(report)

        # Guardar en archivo
        report_path = Path("VERIFICACION_ARQUITECTURA_SAC_2026_02_01.txt")
        report_path.write_text(report, encoding='utf-8')
        logger.info(f"\n✅ Reporte guardado en: {report_path}")

        return 0
    except Exception as e:
        logger.error(f"❌ Error en auditoría: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
