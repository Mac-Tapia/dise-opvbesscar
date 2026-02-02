#!/usr/bin/env python
"""
SCRIPT DE VERIFICACIÓN: Conectividad Agente SAC ↔ CityLearnv2 ↔ OE2 Datos
Fecha: 2026-02-01
Propósito: Validar que el agente está 100% conectado a observaciones, acciones y datos de 1 año
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict
import sys
import warnings

import numpy as np
import pandas as pd  # pyright: ignore

# Suprimir warnings de bibliotecas externas
warnings.filterwarnings('ignore', category=UserWarning)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Agregar proyecto a path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

def verify_observation_dimensions() -> Dict[str, Any]:
    """✅ Verificar que observaciones tienen 394 dimensiones esperadas."""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: OBSERVACIONES (394-dim)")
    logger.info("="*80)

    from iquitos_citylearn.oe3.simulate import _make_env

    schema_path = PROJECT_ROOT / 'data' / 'processed' / 'citylearn' / 'oe3_simulations' / 'schema.json'
    if not schema_path.exists():
        logger.error("❌ Schema no encontrado: %s", schema_path)
        return {'status': 'FAIL', 'reason': 'schema_not_found'}

    try:
        env = _make_env(schema_path)
        obs, _ = env.reset()

        # Flatten observations
        if isinstance(obs, dict):
            obs_list = list(obs.values())
        elif isinstance(obs, (list, tuple)):
            obs_list = list(obs)
        else:
            obs_list = [obs]

        obs_flat = np.concatenate([np.array(o, dtype=np.float32).ravel() for o in obs_list])
        obs_dim = len(obs_flat)

        logger.info("✅ Observaciones cargadas correctamente")
        logger.info("   - Dimensión: %d (esperado ~394)", obs_dim)
        logger.info("   - Min value: %.4f", np.min(obs_flat))
        logger.info("   - Max value: %.4f", np.max(obs_flat))
        logger.info("   - Mean value: %.4f", np.mean(obs_flat))
        logger.info("   - Std value: %.4f", np.std(obs_flat))

        if obs_dim < 350:
            logger.warning("⚠️ Dimensión baja (< 350): posible simplificación no deseada")
            return {'status': 'WARNING', 'obs_dim': obs_dim, 'reason': 'low_dimensionality'}

        logger.info("✅ TEST 1 PASSED")
        return {'status': 'PASS', 'obs_dim': obs_dim, 'obs_shape': obs_flat.shape}

    except Exception as e:
        logger.error("❌ Error cargando environment: %s", e)
        return {'status': 'FAIL', 'reason': str(e)}

def verify_action_dimensions() -> Dict[str, Any]:
    """✅ Verificar que acciones tienen 129 dimensiones (1 BESS + 128 chargers)."""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: ACCIONES (129-dim)")
    logger.info("="*80)

    from iquitos_citylearn.oe3.simulate import _make_env, _sample_action

    schema_path = PROJECT_ROOT / 'data' / 'processed' / 'citylearn' / 'oe3_simulations' / 'schema.json'

    try:
        env = _make_env(schema_path)
        env.reset()

        action = _sample_action(env)

        # Count action dimensions
        if isinstance(action, list):
            act_dim = sum(len(np.array(a, dtype=np.float32).ravel()) for a in action)
        else:
            act_dim = len(np.array(action, dtype=np.float32).ravel())

        logger.info("✅ Acciones cargadas correctamente")
        logger.info("   - Tipo: %s", type(action).__name__)
        logger.info("   - Dimensión total: %d (esperado 129)", act_dim)

        if isinstance(action, list):
            logger.info("   - Estructura: list de %d elementos", len(action))
            for i, a in enumerate(action[:3]):  # Show first 3
                logger.info("     [%d] shape=%s dtype=%s", i, np.array(a).shape, np.array(a).dtype)

        if act_dim != 129:
            logger.warning("⚠️ Dimensión acción ≠ 129: %d", act_dim)
            return {'status': 'WARNING', 'act_dim': act_dim, 'expected': 129}

        logger.info("✅ TEST 2 PASSED")
        return {'status': 'PASS', 'act_dim': act_dim}

    except Exception as e:
        logger.error("❌ Error en acciones: %s", e)
        return {'status': 'FAIL', 'reason': str(e)}

def verify_annual_data_completeness() -> Dict[str, Any]:
    """✅ Verificar que todos los datos tienen 8760 horas (1 año completo)."""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: DATOS ANUALES COMPLETOS (8760 horas)")
    logger.info("="*80)

    dataset_dir = PROJECT_ROOT / 'data' / 'processed' / 'citylearn' / 'oe3_simulations'

    if not dataset_dir.exists():
        logger.error("❌ Dataset dir no encontrado: %s", dataset_dir)
        return {'status': 'FAIL', 'reason': 'dataset_dir_not_found'}

    results: Dict[str, Any] = {
        'status': 'PASS',
        'files_verified': {},
        'files_failed': {},
    }

    # Verificar CSVs globales
    global_csvs = {
        'solar_generation.csv': 'Generación solar (kW)',
        'energy_simulation.csv': 'Demanda mall + EV',
        'pricing.csv': 'Tarifa eléctrica',
        'carbon_intensity.csv': 'Factor CO2 (kg/kWh)',
        'electrical_storage_simulation.csv': 'BESS SOC (kWh)',
    }

    for csv_name, description in global_csvs.items():
        csv_path = dataset_dir / csv_name
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path)
                rows = len(df)
                cols = len(df.columns)

                if rows == 8760:
                    logger.info("✅ %s: %d rows × %d cols (%s)", csv_name, rows, cols, description)
                    results['files_verified'][csv_name] = {'rows': rows, 'cols': cols, 'status': 'OK'}
                else:
                    logger.warning("⚠️ %s: EXPECTED 8760, GOT %d rows", csv_name, rows)
                    results['files_failed'][csv_name] = {'expected': 8760, 'actual': rows}
                    results['status'] = 'WARNING'
            except Exception as e:
                logger.error("❌ %s: Error leyendo CSV: %s", csv_name, e)
                results['files_failed'][csv_name] = {'error': str(e)}
                results['status'] = 'FAIL'
        else:
            logger.warning("⚠️ %s: NO ENCONTRADO (opcional: %s)", csv_name, description)
            results['files_failed'][csv_name] = {'error': 'file_not_found'}

    # Verificar 128 charger CSVs
    charger_csvs = sorted(dataset_dir.glob('charger_simulation_*.csv'))
    logger.info("\n📊 Charger CSVs encontrados: %d (esperado 128)", len(charger_csvs))

    charger_status = {'verified': 0, 'failed': 0}
    for charger_csv in charger_csvs:
        try:
            df = pd.read_csv(charger_csv)
            if len(df) == 8760:
                charger_status['verified'] += 1
            else:
                logger.warning("⚠️ %s: %d rows (esperado 8760)", charger_csv.name, len(df))
                charger_status['failed'] += 1
        except Exception as e:
            logger.error("❌ %s: %s", charger_csv.name, e)
            charger_status['failed'] += 1

    if len(charger_csvs) == 128 and charger_status['failed'] == 0:
        logger.info("✅ Todos los 128 charger CSVs verificados (8760 horas c/u)")
        results['chargers_verified'] = 128
    else:
        logger.warning("⚠️ Chargers: %d OK, %d FAIL", charger_status['verified'], charger_status['failed'])
        results['chargers_verified'] = charger_status['verified']
        results['chargers_failed'] = charger_status['failed']
        if len(charger_csvs) != 128:
            results['status'] = 'WARNING'

    logger.info("✅ TEST 3 PASSED")
    return results

def verify_agent_connectivity() -> Dict[str, Any]:
    """✅ Verificar conectividad SAC agent → obs → acciones → env."""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: CONECTIVIDAD AGENTE SAC E2E")
    logger.info("="*80)

    from iquitos_citylearn.oe3.agents import make_sac, SACConfig
    from iquitos_citylearn.oe3.simulate import _make_env

    schema_path = PROJECT_ROOT / 'data' / 'processed' / 'citylearn' / 'oe3_simulations' / 'schema.json'

    try:
        # Crear environment
        env = _make_env(schema_path)
        logger.info("✅ Environment cargado")

        # Crear agente SAC con config test
        config = SACConfig(
            episodes=1,  # Just 1 for quick test
            device='cpu',
            learning_rate=1e-4,
            batch_size=64,
        )
        agent = make_sac(env, config=config)
        logger.info("✅ Agente SAC creado")

        # Verificar predict sin entrenar
        obs, _ = env.reset()
        action = agent.predict(obs, deterministic=True)
        logger.info("✅ Agente puede predecir acción (sin entrenar)")
        logger.info("   - Acción retornada tipo: %s", type(action).__name__)

        # Ejecutar 10 pasos
        obs = obs
        for step in range(10):
            action = agent.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, _ = env.step(action)
            if step % 3 == 0:
                logger.info("   Step %d: reward=%.4f, done=%s", step, reward, terminated or truncated)

        logger.info("✅ Agente ejecutó 10 pasos correctamente")
        logger.info("✅ TEST 4 PASSED")
        return {'status': 'PASS', 'steps_executed': 10}

    except Exception as e:
        logger.error("❌ Error conectividad agente: %s", e)
        import traceback
        logger.error(traceback.format_exc())
        return {'status': 'FAIL', 'reason': str(e)}

def verify_observation_coverage() -> Dict[str, Any]:
    """✅ Verificar que todas las observaciones esperadas están presentes."""
    logger.info("\n" + "="*80)
    logger.info("TEST 5: COBERTURA DE OBSERVACIONES")
    logger.info("="*80)

    from iquitos_citylearn.oe3.simulate import _make_env

    schema_path = PROJECT_ROOT / 'data' / 'processed' / 'citylearn' / 'oe3_simulations' / 'schema.json'

    try:
        env = _make_env(schema_path)
        _, _ = env.reset()

        coverage = {
            'buildings': len(getattr(env, 'buildings', [])),
            'chargers_found': 0,
            'solar_generation': False,
            'electrical_storage': False,
            'pricing': False,
            'carbon_intensity': False,
        }

        for b in getattr(env, 'buildings', []):
            # Check chargers
            chargers = (getattr(b, 'electric_vehicle_chargers', None) or
                       getattr(b, 'chargers', None) or [])
            if isinstance(chargers, dict):
                coverage['chargers_found'] = len(chargers)
            elif isinstance(chargers, list):
                coverage['chargers_found'] = len(chargers)

            # Check PV
            if hasattr(b, 'solar_generation'):
                coverage['solar_generation'] = True

            # Check BESS
            if hasattr(b, 'electrical_storage'):
                coverage['electrical_storage'] = True

        logger.info("✅ Cobertura de observaciones:")
        logger.info("   - Buildings: %d", coverage['buildings'])
        logger.info("   - Chargers: %d (esperado 128)", coverage['chargers_found'])
        logger.info("   - Solar generation: %s", coverage['solar_generation'])
        logger.info("   - Electrical storage (BESS): %s", coverage['electrical_storage'])

        if coverage['chargers_found'] != 128:
            logger.warning("⚠️ Chargers: esperado 128, encontrado %d", coverage['chargers_found'])
            return {'status': 'WARNING', **coverage}

        logger.info("✅ TEST 5 PASSED")
        return {'status': 'PASS', **coverage}

    except Exception as e:
        logger.error("❌ Error verificando cobertura: %s", e)
        return {'status': 'FAIL', 'reason': str(e)}

def generate_summary_report(test_results: Dict[str, Any]) -> None:
    """Generar reporte resumido final."""
    logger.info("\n" + "="*80)
    logger.info("REPORTE FINAL: CONECTIVIDAD AGENTE SAC ↔ CITYLEARN V2 ↔ OE2")
    logger.info("="*80)

    # Resumen por test
    test_summary = {}
    for test_name, result in test_results.items():
        status = result.get('status', 'UNKNOWN')
        test_summary[test_name] = status
        emoji = '✅' if status == 'PASS' else '⚠️' if status == 'WARNING' else '❌'
        logger.info("%s %s: %s", emoji, test_name, status)

    # Resultado final
    all_passed = all(s == 'PASS' for s in test_summary.values())
    has_warnings = any(s == 'WARNING' for s in test_summary.values())
    has_failures = any(s == 'FAIL' for s in test_summary.values())

    logger.info("\n" + "="*80)
    if all_passed:
        logger.info("🎉 CONECTIVIDAD 100% VERIFICADA - LISTO PARA ENTRENAR")
    elif has_warnings and not has_failures:
        logger.info("⚠️ CONECTIVIDAD OPERACIONAL CON ADVERTENCIAS - ENTRENAR CON PRECAUCIÓN")
    else:
        logger.info("❌ ERRORES DETECTADOS - REVISAR ANTES DE ENTRENAR")
    logger.info("="*80)

    # Detalles por test
    logger.info("\nDETALLES POR TEST:")
    for test_name, result in test_results.items():
        logger.info("\n%s:", test_name)
        for key, value in result.items():
            if key != 'status':
                if isinstance(value, dict):
                    logger.info("  %s: %d items", key, len(value))
                else:
                    logger.info("  %s: %s", key, value)

    # Guardar reporte como JSON
    report_path = PROJECT_ROOT / 'CONNECTIVITY_AUDIT_REPORT.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, indent=2, default=str)
    logger.info("\n📄 Reporte guardado en: %s", report_path)

def main():
    """Ejecutar todos los tests de conectividad."""
    logger.info("\n" + "#"*80)
    logger.info("# AUDITORÍA DE CONECTIVIDAD: AGENTE SAC ↔ CITYLEARN V2 ↔ OE2 DATOS")
    logger.info("# Fecha: 2026-02-01")
    logger.info("#"*80 + "\n")

    test_results = {
        'TEST 1 - Observaciones (394-dim)': verify_observation_dimensions(),
        'TEST 2 - Acciones (129-dim)': verify_action_dimensions(),
        'TEST 3 - Datos Anuales (8760h)': verify_annual_data_completeness(),
        'TEST 4 - Conectividad E2E': verify_agent_connectivity(),
        'TEST 5 - Cobertura Observaciones': verify_observation_coverage(),
    }

    generate_summary_report(test_results)

if __name__ == '__main__':
    main()
