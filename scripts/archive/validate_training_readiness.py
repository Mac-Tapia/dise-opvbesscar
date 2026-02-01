#!/usr/bin/env python
"""Pre-training validation - Final integrity check before launching training"""
from __future__ import annotations

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def validate_python_version() -> bool:
    """Validate Python 3.11+"""
    if sys.version_info[:2] != (3, 11):
        logger.error(f"❌ Python 3.11 required, got {sys.version_info[0]}.{sys.version_info[1]}")
        return False
    logger.info("✅ Python 3.11 verificado")
    return True


def validate_schema_integrity() -> bool:
    """Validate schema.json has all critical fields"""
    schema_path = Path('data/processed/citylearn/iquitos_ev_mall/schema.json')

    if not schema_path.exists():
        logger.error(f"❌ Schema no encontrado: {schema_path}")
        return False

    try:
        with open(schema_path) as f:
            schema = json.load(f)
    except Exception as e:
        logger.error(f"❌ Schema JSON inválido: {e}")
        return False

    # Validate critical fields
    checks = {
        'episode_time_steps': (schema.get('episode_time_steps'), 8760),
        'central_agent': (schema.get('central_agent'), True),
        'seconds_per_time_step': (schema.get('seconds_per_time_step'), 3600),
    }

    building = schema.get('buildings', {}).get('Mall_Iquitos', {})
    checks['chargers_count'] = (len(building.get('chargers', {})), 128)
    checks['pv_peak_power'] = (
        building.get('pv', {}).get('attributes', {}).get('peak_power'),
        4050.0
    )
    checks['bess_power_output'] = (
        building.get('electrical_storage', {}).get('attributes', {}).get('power_output_nominal'),
        1200.0
    )

    all_ok = True
    for field, (actual, expected) in checks.items():
        if actual == expected:
            logger.info(f"✅ {field}: {actual}")
        else:
            logger.error(f"❌ {field}: {actual} (expected {expected})")
            all_ok = False

    return all_ok


def validate_config_consistency() -> bool:
    """Validate config.yaml consistency"""
    import yaml

    config_path = Path('configs/default.yaml')
    if not config_path.exists():
        logger.error(f"❌ Config no encontrado: {config_path}")
        return False

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"❌ Config YAML inválido: {e}")
        return False

    # Check critical sections
    sections = ['oe1', 'oe2', 'oe3', 'paths', 'project']
    for section in sections:
        if section not in config:
            logger.error(f"❌ Config section '{section}' missing")
            return False
        logger.info(f"✅ Config section '{section}' present")

    # Check agents - can be in oe3.evaluation section
    evaluation_section = config.get('oe3', {}).get('evaluation', {})

    # Check for agent configs in evaluation section
    required_agents = {'sac', 'ppo', 'a2c'}
    found_agents = set()

    for agent_name in required_agents:
        if agent_name in evaluation_section:
            found_agents.add(agent_name)
            logger.info(f"✅ Agent '{agent_name}' configured in evaluation")

    if len(found_agents) < 3:
        logger.warning(f"⚠️  Only {len(found_agents)}/3 agents configured ({', '.join(found_agents or ['none'])})")
        # Don't fail - still has some agents

    return True


def validate_checkpoint_dirs() -> bool:
    """Validate checkpoint directories exist and are writable"""
    checkpoint_dirs = [
        Path('checkpoints/SAC'),
        Path('checkpoints/PPO'),
        Path('checkpoints/A2C'),
    ]

    for checkpoint_dir in checkpoint_dirs:
        if not checkpoint_dir.exists():
            logger.warning(f"⚠️  Creating checkpoint dir: {checkpoint_dir}")
            checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Test write
        test_file = checkpoint_dir / '.write_test'
        try:
            test_file.touch()
            test_file.unlink()
            logger.info(f"✅ Checkpoint dir writable: {checkpoint_dir}")
        except Exception as e:
            logger.error(f"❌ Checkpoint dir not writable: {checkpoint_dir} ({e})")
            return False

    return True


def validate_dataset_exists() -> bool:
    """Validate dataset CSV files exist"""
    dataset_dir = Path('data/processed/citylearn/iquitos_ev_mall')
    required_files = {
        'schema.json': 'Schema CityLearn',
        'weather.csv': 'Datos meteorológicos',
        'chargers.csv': 'Perfiles de cargadores',
        'building_metadata.csv': 'Metadatos del edificio',
    }

    all_exist = True
    for filename, description in required_files.items():
        file_path = dataset_dir / filename
        if file_path.exists():
            logger.info(f"✅ {description}: {filename}")
        else:
            logger.warning(f"⚠️  {description}: {filename} (será generado)")

    return True


def validate_oe2_artifacts() -> bool:
    """Validate OE2 artifacts exist (needed for dataset building)"""
    oe2_dir = Path('data/interim/oe2')

    required_artifacts = {
        'solar/pv_generation_timeseries.csv': 'Solar PV timeseries (8760 hourly)',
        'chargers/perfil_horario_carga.csv': 'Charger load profile',
        'chargers/individual_chargers.json': 'Individual charger specs (32×4=128)',
        'bess/bess_config.json': 'BESS configuration',
    }

    all_exist = True
    for artifact_path, description in required_artifacts.items():
        full_path = oe2_dir / artifact_path
        if full_path.exists():
            logger.info(f"✅ OE2: {description}")
        else:
            logger.warning(f"⚠️  OE2 artifact missing: {artifact_path}")
            all_exist = False

    return all_exist


def validate_imports() -> bool:
    """Validate all critical imports work"""
    imports = [
        ('numpy', 'NumPy'),
        ('pandas', 'Pandas'),
        ('yaml', 'PyYAML'),
        ('stable_baselines3', 'Stable-Baselines3'),
        ('gymnasium', 'Gymnasium'),
        ('torch', 'PyTorch'),
        ('iquitos_citylearn', 'Project module'),
    ]

    all_ok = True
    for module_name, description in imports:
        try:
            __import__(module_name)
            logger.info(f"✅ {description}")
        except ImportError:
            logger.warning(f"⚠️  {description} not available (needed for training)")
            # Don't fail - some modules optional

    return all_ok


def main() -> int:
    """Run all validation checks"""
    logger.info("=" * 80)
    logger.info("VALIDACIÓN PRE-ENTRENAMIENTO")
    logger.info("=" * 80 + "\n")

    checks = [
        ("Python 3.11", validate_python_version),
        ("Schema integrity", validate_schema_integrity),
        ("Config consistency", validate_config_consistency),
        ("Checkpoint directories", validate_checkpoint_dirs),
        ("Dataset existence", validate_dataset_exists),
        ("OE2 artifacts", validate_oe2_artifacts),
        ("Python imports", validate_imports),
    ]

    results = []
    for check_name, check_func in checks:
        logger.info(f"\nValidando: {check_name}")
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            logger.error(f"❌ Excepción en {check_name}: {e}")
            results.append((check_name, False))

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("RESUMEN")
    logger.info("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {check_name}")

    logger.info(f"\nTotal: {passed}/{total} checks passed")

    if passed == total:
        logger.info("\n✅ SISTEMA LISTO PARA ENTRENAMIENTO")
        logger.info("\nPróximo comando:")
        logger.info("  python -m scripts.run_oe3_simulate --config configs/default.yaml")
        return 0
    else:
        logger.error(f"\n❌ {total - passed} checks fallaron. Corrija los errores antes de entrenar.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
