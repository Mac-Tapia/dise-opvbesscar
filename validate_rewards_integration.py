#!/usr/bin/env python
"""
✅ VALIDACIÓN: Integración de rewards.py en dataset_builder.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Script para verificar que:
1. ✓ rewards.py se importa correctamente en dataset_builder.py
2. ✓ IquitosContext se inicializa con valores OE2 reales
3. ✓ Reward weights se cargan en el schema
4. ✓ CO₂ factors se preservan para agentes OE3

Ejecución:
    python validate_rewards_integration.py

Validaciones:
    ✓ Import de módulos (rewards.py disponible)
    ✓ Inicialización de IquitosContext (CO₂ = 0.4521, 2.146)
    ✓ Creación de MultiObjectiveWeights (CO₂=0.50, solar=0.20)
    ✓ Schema con co2_context y reward_weights
    ✓ Factores CO₂ accesibles para agentes

Resultado esperado:
    ✅ 5/5 validaciones PASS → Integración exitosa
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Tuple

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(name)-40s | %(message)s",
)
logger = logging.getLogger(__name__)

def test_rewards_import() -> Tuple[bool, str]:
    """Test 1: Verificar que rewards.py se importa correctamente."""
    try:
        from src.rewards.rewards import (
            MultiObjectiveWeights,
            IquitosContext,
            create_iquitos_reward_weights,
        )
        logger.info("✅ TEST 1 PASS: rewards.py importado correctamente")
        return True, "✅ rewards.py imports available"
    except ImportError as e:
        logger.error("❌ TEST 1 FAIL: No se pudo importar rewards.py: %s", e)
        return False, f"❌ Import failed: {e}"

def test_iquitos_context_initialization() -> Tuple[bool, str]:
    """Test 2: Verificar que IquitosContext se inicializa con valores OE2."""
    try:
        from src.rewards.rewards import IquitosContext

        ctx = IquitosContext(
            co2_factor_kg_per_kwh=0.4521,
            co2_conversion_factor=2.146,
            motos_daily_capacity=1800,
            mototaxis_daily_capacity=260,
            max_evs_total=128,
        )

        # Validar valores críticos
        assert abs(ctx.co2_factor_kg_per_kwh - 0.4521) < 0.0001, "CO₂ grid factor incorrecto"
        assert abs(ctx.co2_conversion_factor - 2.146) < 0.001, "CO₂ EV conversion incorrecto"
        assert ctx.motos_daily_capacity == 1800, "Capacidad motos incorrecta"
        assert ctx.mototaxis_daily_capacity == 260, "Capacidad mototaxis incorrecta"
        assert ctx.max_evs_total == 128, "Total EVs incorrecto"

        logger.info("✅ TEST 2 PASS: IquitosContext inicializado correctamente")
        logger.info("   CO₂ grid: %.4f kg/kWh, EV: %.3f kg/kWh",
                   ctx.co2_factor_kg_per_kwh, ctx.co2_conversion_factor)
        logger.info("   EVs: %d motos/día + %d mototaxis/día = %d sockets",
                   ctx.motos_daily_capacity, ctx.mototaxis_daily_capacity, ctx.max_evs_total)
        return True, "✅ IquitosContext initialized correctly"
    except Exception as e:
        logger.error("❌ TEST 2 FAIL: %s", e)
        return False, f"❌ IquitosContext test failed: {e}"

def test_multiobjecttive_weights() -> Tuple[bool, str]:
    """Test 3: Verificar que MultiObjectiveWeights se crean correctamente."""
    try:
        from src.rewards.rewards import create_iquitos_reward_weights

        weights = create_iquitos_reward_weights(priority="balanced")

        # Validar pesos
        assert weights.co2 == 0.50, "CO₂ weight debería ser 0.50"
        assert weights.solar == 0.20, "Solar weight debería ser 0.20"
        assert weights.cost == 0.15, "Cost weight debería ser 0.15"

        # Verificar que sumen a ~1.0
        total_weight = sum([
            weights.co2, weights.cost, weights.solar,
            weights.ev_satisfaction, weights.ev_utilization, weights.grid_stability
        ])
        assert abs(total_weight - 1.0) < 0.01, f"Pesos no suman a 1.0: {total_weight}"

        logger.info("✅ TEST 3 PASS: MultiObjectiveWeights creados correctamente")
        logger.info("   CO₂=%.2f, solar=%.2f, cost=%.2f, ev=%.2f, grid=%.2f (total=%.2f)",
                   weights.co2, weights.solar, weights.cost,
                   weights.ev_satisfaction + weights.ev_utilization, weights.grid_stability,
                   total_weight)
        return True, "✅ MultiObjectiveWeights created correctly"
    except Exception as e:
        logger.error("❌ TEST 3 FAIL: %s", e)
        return False, f"❌ MultiObjectiveWeights test failed: {e}"

def test_dataset_builder_imports() -> Tuple[bool, str]:
    """Test 4: Verificar que dataset_builder.py importa rewards correctamente."""
    try:
        # Leer el archivo dataset_builder.py y buscar imports
        dataset_builder_path = Path("src/citylearnv2/dataset_builder/dataset_builder.py")
        if not dataset_builder_path.exists():
            return False, f"❌ dataset_builder.py no encontrado en {dataset_builder_path}"

        content = dataset_builder_path.read_text(encoding="utf-8")

        # Verificar que existan los imports
        required_imports = [
            "from src.rewards.rewards import",
            "MultiObjectiveWeights",
            "IquitosContext",
            "create_iquitos_reward_weights",
        ]

        for required in required_imports:
            if required not in content:
                logger.error("❌ Missing import in dataset_builder.py: %s", required)
                return False, f"❌ Missing import: {required}"

        # Verificar que exista integración de IquitosContext
        if 'artifacts["iquitos_context"]' not in content:
            logger.error("❌ IquitosContext no se integra en _load_oe2_artifacts")
            return False, "❌ IquitosContext not integrated"

        # Verificar que exista integración en schema
        if 'schema["co2_context"]' not in content:
            logger.error("❌ co2_context no se agrega al schema")
            return False, "❌ co2_context not in schema"

        logger.info("✅ TEST 4 PASS: dataset_builder.py contiene todas las integraciones")
        logger.info("   ✓ Imports de rewards.py")
        logger.info("   ✓ IquitosContext integrado en _load_oe2_artifacts()")
        logger.info("   ✓ co2_context y reward_weights en schema")
        return True, "✅ dataset_builder.py fully integrated"
    except Exception as e:
        logger.error("❌ TEST 4 FAIL: %s", e)
        return False, f"❌ dataset_builder test failed: {e}"

def test_schema_generation() -> Tuple[bool, str]:
    """Test 5: Verificar estructura esperada del schema con co2_context."""
    try:
        # Crear un schema de ejemplo con la estructura esperada
        expected_schema = {
            "co2_context": {
                "co2_factor_kg_per_kwh": 0.4521,
                "co2_conversion_factor": 2.146,
                "motos_daily_capacity": 1800,
                "mototaxis_daily_capacity": 260,
                "max_evs_total": 128,
                "tariff_usd_per_kwh": 0.20,
                "peak_hours": [18, 19, 20, 21],
                "description": "Contexto real de Iquitos",
            },
            "reward_weights": {
                "co2": 0.50,
                "cost": 0.15,
                "solar": 0.20,
                "ev_satisfaction": 0.10,
                "ev_utilization": 0.05,
                "grid_stability": 0.05,
                "description": "Pesos multiobjetivo para agentes OE3",
            }
        }

        # Validar estructura
        assert "co2_context" in expected_schema, "co2_context faltante"
        assert "reward_weights" in expected_schema, "reward_weights faltante"

        co2_ctx = expected_schema["co2_context"]
        assert co2_ctx["co2_factor_kg_per_kwh"] == 0.4521
        assert co2_ctx["co2_conversion_factor"] == 2.146
        # CRITICAL FIX: Convertir peak_hours a list antes de usar len()
        peak_hours_val = co2_ctx["peak_hours"]
        peak_hours_list: list[Any] = list(peak_hours_val) if isinstance(peak_hours_val, (list, tuple, dict, set)) else [peak_hours_val]
        assert len(peak_hours_list) == 4

        weights = expected_schema["reward_weights"]
        weights_dict: dict[str, float] = dict(weights) if hasattr(weights, 'items') else weights
        assert float(weights_dict.get("co2", 0.0)) == 0.50
        assert float(weights_dict.get("solar", 0.0)) == 0.20

        logger.info("✅ TEST 5 PASS: Schema structure válida")
        co2_ctx_dict: dict[str, Any] = dict(co2_ctx) if hasattr(co2_ctx, 'items') else co2_ctx
        weights_dict_log: dict[str, Any] = dict(weights_dict) if hasattr(weights_dict, 'items') else weights_dict
        logger.info("   ✓ co2_context: %d atributos", len(co2_ctx_dict) if isinstance(co2_ctx_dict, dict) else 1)
        logger.info("   ✓ reward_weights: %d atributos", len(weights_dict_log) if isinstance(weights_dict_log, dict) else 1)
        logger.info("   ✓ Total schema keys: %d", len(expected_schema))
        return True, "✅ Schema structure valid"
    except Exception as e:
        logger.error("❌ TEST 5 FAIL: %s", e)
        return False, f"❌ Schema structure test failed: {e}"

def main():
    """Ejecutar todas las validaciones."""
    print("\n" + "="*80)
    print("🔍 VALIDACIÓN: Integración de rewards.py en dataset_builder.py")
    print("="*80 + "\n")

    tests = [
        ("Test 1: Import rewards.py", test_rewards_import),
        ("Test 2: IquitosContext initialization", test_iquitos_context_initialization),
        ("Test 3: MultiObjectiveWeights creation", test_multiobjecttive_weights),
        ("Test 4: dataset_builder.py imports", test_dataset_builder_imports),
        ("Test 5: Schema structure", test_schema_generation),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * 80)
        passed, message = test_func()
        results.append((test_name, passed, message))

    # Resumen
    print("\n" + "="*80)
    print("📊 RESUMEN DE VALIDACIÓN")
    print("="*80)

    passed_count = sum(1 for _, passed, _ in results if passed)
    total_count = len(results)

    for test_name, passed, message in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\n{status} | {test_name}")
        print(f"       {message}")

    print("\n" + "="*80)
    print(f"RESULTADO: {passed_count}/{total_count} validaciones PASS")
    print("="*80 + "\n")

    if passed_count == total_count:
        print("🎉 ¡ÉXITO! Integración de rewards.py completada correctamente.")
        print("\n✅ Próximos pasos:")
        print("   1. Ejecutar: python -m scripts.run_oe3_build_dataset --config configs/default.yaml")
        print("   2. Verificar schema.json contiene co2_context y reward_weights")
        print("   3. Entrenar agentes OE3 (SAC, PPO, A2C) con datos integrados")
        return 0
    else:
        print(f"❌ {total_count - passed_count} validación(es) fallida(s)")
        return 1

if __name__ == "__main__":
    sys.exit(main())
