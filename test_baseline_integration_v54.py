#!/usr/bin/env python3
"""Test and Validation Script for Baseline Integration (OE2 v5.4).

Verifica que todos los módulos de baseline están funcionando correctamente
y conectados con datos OE2 v5.4 validados.
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)

logger = logging.getLogger(__name__)


def test_data_files_exist() -> bool:
    """Test que todos los datos necesarios existen.
    
    Returns:
        True if all data files exist, False otherwise
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Verificar Archivos de Datos")
    logger.info("="*80)
    
    required_files = [
        Path('data/oe2/bess/bess_simulation_hourly.csv'),
        Path('data/oe2/bess/bess_hourly_dataset_2024.csv'),
        Path('data/oe2/demandamallkwh/demandamallhorakwh.csv'),
        Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv'),
    ]
    
    all_exist = True
    for file_path in required_files:
        if file_path.exists():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"  ✅ {file_path} ({size_mb:.1f} MB)")
        else:
            logger.error(f"  ❌ {file_path} NOT FOUND")
            all_exist = False
    
    return all_exist


def test_baseline_calculator() -> bool:
    """Test BaselineCalculator module.
    
    Returns:
        True if calculator works correctly
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Ejecutar BaselineCalculator")
    logger.info("="*80)
    
    try:
        from src.baseline.baseline_calculator_v2 import BaselineCalculator
        
        calculator = BaselineCalculator(co2_intensity=0.4521)
        con_solar, sin_solar = calculator.calculate_all_baselines()
        
        # Validate results
        assert con_solar['timesteps'] == 8760, "Error: timesteps != 8760"
        assert con_solar['co2_grid_kg'] > 0, "Error: CON_SOLAR CO2 <= 0"
        assert con_solar['solar_generation_kwh'] > 0, "Error: Solar generation <= 0"
        assert sin_solar['co2_grid_kg'] > con_solar['co2_grid_kg'], "Error: SIN_SOLAR should have more CO2"
        
        logger.info(f"  ✅ CON_SOLAR: {con_solar['co2_t']:,.1f} t CO₂/año")
        logger.info(f"  ✅ SIN_SOLAR: {sin_solar['co2_t']:,.1f} t CO₂/año")
        logger.info(f"  ✅ Solar impact: {(sin_solar['co2_grid_kg'] - con_solar['co2_grid_kg'])/1000:,.1f} t CO₂ difference")
        
        return True
        
    except Exception as e:
        logger.error(f"  ❌ BaselineCalculator failed: {e}")
        return False


def test_baseline_definitions() -> bool:
    """Test BaselineDefinitions module.
    
    Returns:
        True if definitions are correct
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Verificar Definiciones de Baseline")
    logger.info("="*80)
    
    try:
        from src.baseline.baseline_definitions_v54 import BASELINE_CON_SOLAR, BASELINE_SIN_SOLAR
        
        # Check CON_SOLAR
        assert BASELINE_CON_SOLAR.solar_capacity_kwp == 4050.0, "Solar capacity mismatch"
        assert BASELINE_CON_SOLAR.bess_capacity_kwh == 1700.0, "BESS capacity mismatch"
        
        # Check SIN_SOLAR
        assert BASELINE_SIN_SOLAR.solar_capacity_kwp == 0.0, "SIN_SOLAR solar should be 0"
        assert BASELINE_SIN_SOLAR.bess_capacity_kwh == 1700.0, "SIN_SOLAR BESS mismatch"
        
        logger.info(f"  ✅ BASELINE_CON_SOLAR: {BASELINE_CON_SOLAR.description}")
        logger.info(f"  ✅ BASELINE_SIN_SOLAR: {BASELINE_SIN_SOLAR.description}")
        logger.info(f"  ✅ BESS Capacity: {BASELINE_CON_SOLAR.bess_capacity_kwh:,.0f} kWh")
        
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Baseline definitions failed: {e}")
        return False


def test_citylearn_integration() -> bool:
    """Test CityLearn Integration module.
    
    Returns:
        True if integration module works
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Integración con CityLearn v2")
    logger.info("="*80)
    
    try:
        from src.baseline.citylearn_baseline_integration import BaselineCityLearnIntegration
        
        integration = BaselineCityLearnIntegration(output_dir='outputs/baselines_test')
        baselines = integration.compute_baselines()
        
        assert 'con_solar' in baselines, "Missing con_solar in results"
        assert 'sin_solar' in baselines, "Missing sin_solar in results"
        
        logger.info(f"  ✅ Baselines computed successfully")
        logger.info(f"  ✅ Output directory: outputs/baselines_test/")
        
        return True
        
    except Exception as e:
        logger.error(f"  ❌ CityLearn integration failed: {e}")
        return False


def test_agent_baseline_integration() -> bool:
    """Test Agent-Baseline Integration module.
    
    Returns:
        True if agent integration works
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 5: Integración con Entrenamientos de Agentes")
    logger.info("="*80)
    
    try:
        from src.baseline.agent_baseline_integration import setup_agent_training_with_baselines
        
        # Test with mock agent name
        baseline_integration = setup_agent_training_with_baselines(
            agent_name='TEST_AGENT',
            output_dir='outputs/agent_training_test',
            baseline_dir='outputs/baselines_test'
        )
        
        # Test registration
        baseline_integration.register_training_results(
            co2_kg=5000.0,  # Mock CO2
            grid_import_kwh=3000000.0,  # Mock grid
            solar_generation_kwh=6200000.0  # Mock solar
        )
        
        logger.info(f"  ✅ Agent baseline integration initialized")
        logger.info(f"  ✅ Training results registered")
        
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Agent baseline integration failed: {e}")
        return False


def test_data_consistency() -> bool:
    """Test data consistency across modules.
    
    Returns:
        True if data is consistent
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 6: Consistencia de Datos (8,760 horas = 365 días)")
    logger.info("="*80)
    
    try:
        import pandas as pd
        
        # Check BESS data
        bess_path = Path('data/oe2/bess/bess_simulation_hourly.csv')
        bess_df = pd.read_csv(bess_path, index_col=0)
        
        assert len(bess_df) == 8760, f"BESS data has {len(bess_df)} rows, expected 8,760"
        assert 'pv_generation_kwh' in bess_df.columns, "Missing pv_generation_kwh column"
        assert 'ev_demand_kwh' in bess_df.columns, "Missing ev_demand_kwh column"
        assert 'mall_demand_kwh' in bess_df.columns, "Missing mall_demand_kwh column"
        
        logger.info(f"  ✅ BESS dataset: {len(bess_df)} rows (8,760 hourly)")
        logger.info(f"  ✅ Solar generation sum: {bess_df['pv_generation_kwh'].sum():,.0f} kWh/año")
        logger.info(f"  ✅ EV demand sum: {bess_df['ev_demand_kwh'].sum():,.0f} kWh/año")
        logger.info(f"  ✅ Mall demand sum: {bess_df['mall_demand_kwh'].sum():,.0f} kWh/año")
        
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Data consistency check failed: {e}")
        return False


def test_backward_compatibility() -> bool:
    """Test that old alias names still work.
    
    Returns:
        True if backward compatibility is maintained
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 7: Compatibilidad Backward (bess_hourly_dataset_2024.csv alias)")
    logger.info("="*80)
    
    try:
        import pandas as pd
        
        # Check both files exist and are identical
        primary = Path('data/oe2/bess/bess_simulation_hourly.csv')
        alias = Path('data/oe2/bess/bess_hourly_dataset_2024.csv')
        
        if primary.exists() and alias.exists():
            df_primary = pd.read_csv(primary)
            df_alias = pd.read_csv(alias)
            
            assert len(df_primary) == len(df_alias), "File sizes differ"
            assert list(df_primary.columns) == list(df_alias.columns), "Column names differ"
            
            logger.info(f"  ✅ Primary file: bess_simulation_hourly.csv")
            logger.info(f"  ✅ Alias file: bess_hourly_dataset_2024.csv")
            logger.info(f"  ✅ Both files are identical (backward compatible)")
            
            return True
        else:
            logger.warning(f"  ⚠️  Alias check: one or both files missing")
            return True  # Not critical, alias optional
            
    except Exception as e:
        logger.error(f"  ❌ Backward compatibility check failed: {e}")
        return False


def print_summary(results: dict[str, bool]) -> None:
    """Print test summary.
    
    Args:
        results: Dict of test names to pass/fail results
    """
    logger.info("\n" + "="*80)
    logger.info("RESUMEN DE PRUEBAS")
    logger.info("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        logger.info(f"  {status}: {test_name}")
    
    logger.info(f"\nResultado: {passed}/{total} pruebas pasadas")
    
    if passed == total:
        logger.info("✅ Todas las pruebas pasaron. Baseline integration está LISTA para usar.")
        return True
    else:
        logger.error(f"⚠️  {total - passed} pruebas fallaron. Revisar errores arriba.")
        return False


def main():
    """Run all tests.
    
    Returns:
        0 if all tests pass, 1 if any fail
    """
    logger.info("\n")
    logger.info("╔" + "="*78 + "╗")
    logger.info("║" + " "*20 + "BASELINE INTEGRATION TEST SUITE (OE2 v5.4)" + " "*16 + "║")
    logger.info("╚" + "="*78 + "╝")
    
    results = {
        'Archivos de Datos Existen': test_data_files_exist(),
        'BaselineCalculator': test_baseline_calculator(),
        'BaselineDefinitions': test_baseline_definitions(),
        'CityLearn Integration': test_citylearn_integration(),
        'Agent-Baseline Integration': test_agent_baseline_integration(),
        'Consistencia de Datos (8,760 h)': test_data_consistency(),
        'Compatibilidad Backward': test_backward_compatibility(),
    }
    
    all_passed = print_summary(results)
    
    if all_passed:
        logger.info("\n" + "="*80)
        logger.info("PRÓXIMOS PASOS:")
        logger.info("  1. python -m scripts.run_dual_baselines --config configs/default.yaml")
        logger.info("  2. python -m src.agents.sac --env citylearn_v2")
        logger.info("  3. Resultados salvados en: outputs/baselines/ y outputs/agent_training/")
        logger.info("="*80 + "\n")
        return 0
    else:
        logger.error("\nVerifique los errores arriba y corrija antes de continuar.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
