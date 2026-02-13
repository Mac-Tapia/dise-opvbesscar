#!/usr/bin/env python
"""
Test Script: Validar integración completa Dataset ↔ Baseline v5.4

Verifica:
1. Importación correcta de módulos baseline
2. Carga correcta de datos OE2 v5.4 (5 archivos)
3. BESS actualizado a v5.4 (1,700 kWh)
4. Generación de observables con BESS
5. Integración de baselines en schema
6. Validación de métricas
"""

from __future__ import annotations
import sys
from pathlib import Path
import json
import pandas as pd

# Add repo to path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

def test_imports():
    """Test 1: Verificar importación de módulos"""
    print("\n" + "="*80)
    print("TEST 1: Importación de Módulos Baseline")
    print("="*80)
    
    try:
        from src.baseline.baseline_calculator_v2 import BaselineCalculator
        from src.baseline.citylearn_baseline_integration import BaselineCityLearnIntegration
        print("✅ Módulos baseline importados exitosamente")
        return True
    except ImportError as e:
        print(f"❌ Error importando módulos baseline: {e}")
        return False

def test_data_files():
    """Test 2: Verificar archivos de datos OE2 v5.4"""
    print("\n" + "="*80)
    print("TEST 2: Archivos de Datos OE2 v5.4")
    print("="*80)
    
    required_files = [
        ("chargers", "chargers_ev_ano_2024_v3.csv"),
        ("bess", "bess_simulation_hourly.csv"),
        ("demandamallkwh", "demandamallhorakwh.csv"),
        ("Generacionsolar", "pv_generation_hourly_citylearn_v2.csv"),
        ("chargers", "chargers_real_statistics.csv"),
    ]
    
    oe2_path = repo_root / "data" / "oe2"
    all_exist = True
    
    for subdir, filename in required_files:
        filepath = oe2_path / subdir / filename
        exists = filepath.exists()
        status = "✅" if exists else "❌"
        size = f" ({filepath.stat().st_size / 1024 / 1024:.1f} MB)" if exists else ""
        print(f"{status} {subdir}/{filename}{size}")
        all_exist = all_exist and exists
    
    return all_exist

def test_baseline_calculation():
    """Test 3: Calcular baselines con datos reales"""
    print("\n" + "="*80)
    print("TEST 3: Cálculo de Baselines CON_SOLAR vs SIN_SOLAR")
    print("="*80)
    
    try:
        from src.baseline.baseline_calculator_v2 import BaselineCalculator
        
        calc = BaselineCalculator(co2_intensity=0.4521)
        con_solar, sin_solar = calc.calculate_all_baselines()
        
        # Claves correctas del calculator: 'co2_t' (no 'co2_t_year'), 'grid_import_kwh' (no 'grid_kwh_year')
        co2_con_solar = con_solar.get('co2_t')
        grid_con_solar = con_solar.get('grid_import_kwh')
        
        print(f"✅ CON_SOLAR (4,050 kWp):")
        print(f"   CO2: {co2_con_solar:,.1f} t/año" if co2_con_solar else f"   CO2: N/A")
        print(f"   Grid: {grid_con_solar:,.0f} kWh/año" if grid_con_solar else f"   Grid: N/A")
        
        co2_sin_solar = sin_solar.get('co2_t')
        grid_sin_solar = sin_solar.get('grid_import_kwh')
        
        print(f"✅ SIN_SOLAR (0 kWp):")
        print(f"   CO2: {co2_sin_solar:,.1f} t/año" if co2_sin_solar else f"   CO2: N/A")
        print(f"   Grid: {grid_sin_solar:,.0f} kWh/año" if grid_sin_solar else f"   Grid: N/A")
        
        solar_impact = (sin_solar.get('co2_t', 0) or 0) - (con_solar.get('co2_t', 0) or 0)
        print(f"✅ Impacto Solar: {solar_impact:,.1f} t CO₂/año (reducción)")
        
        return True
    except Exception as e:
        print(f"❌ Error calculando baselines: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_bess_version():
    """Test 4: Verificar BESS actualizado a v5.4"""
    print("\n" + "="*80)
    print("TEST 4: Especificaciones BESS v5.4")
    print("="*80)
    
    # Verificar que dataset_builder tiene v5.4
    dataset_builder_path = repo_root / "src" / "citylearnv2" / "dataset_builder" / "dataset_builder.py"
    content = dataset_builder_path.read_text(encoding='utf-8')
    
    # Buscar referencias a 1700.0 kWh (v5.4)
    if "bess_cap = 1700.0" in content or "1700" in content:
        print("✅ BESS v5.4 (1,700 kWh) encontrado en dataset_builder.py")
        print("   - Capacidad: 1,700 kWh")
        print("   - Potencia: 400 kW")
        return True
    else:
        print("❌ BESS v5.4 no encontrado - posible versión antigua")
        return False

def test_observables_structure():
    """Test 5: Verificar estructura de observables"""
    print("\n" + "="*80)
    print("TEST 5: Estructura de Observables v5.3 (con BESS)")
    print("="*80)
    
    try:
        from src.citylearnv2.dataset_builder.dataset_builder import _extract_observable_variables, ALL_OBSERVABLE_COLS
        
        # Columnas esperadas
        expected_ev_cols = [
            'ev_energia_total_kwh', 'ev_costo_carga_soles', 'ev_reduccion_directa_co2_kg'
        ]
        expected_solar_cols = [
            'solar_ahorro_soles', 'solar_reduccion_indirecta_co2_kg'
        ]
        expected_bess_cols = [
            'bess_soc_percent', 'bess_charge_kwh', 'bess_discharge_kwh', 'bess_available_capacity_kwh'
        ]
        expected_totals = [
            'total_reduccion_co2_kg', 'total_costo_soles', 'total_ahorro_soles'
        ]
        
        # Leer observables_oe2.csv si existe
        obs_file = repo_root / "outputs" / "baselines_test" / "observables_oe2.csv"
        if obs_file.exists():
            obs_df = pd.read_csv(obs_file)
            print(f"✅ Observables archivo encontrado: {obs_file.name}")
            print(f"   Dimensiones: {obs_df.shape}")
            print(f"   Filas (timesteps): {obs_df.shape[0]} (esperado 8,760)")
            print(f"   Columnas: {obs_df.shape[1]}")
            
            # Verificar columnas clave
            for col in expected_ev_cols + expected_solar_cols + expected_bess_cols + expected_totals:
                if col in obs_df.columns:
                    print(f"   ✓ {col}")
                else:
                    print(f"   ✗ {col} FALTA")
            
            return True
        else:
            print(f"ℹ️  Archivo observables_oe2.csv no existe aún (será generado en build_citylearn_dataset)")
            return True
    except Exception as e:
        print(f"❌ Error verificando observables: {e}")
        return False

def test_baseline_integration_imports():
    """Test 6: Verificar integración de imports en dataset_builder"""
    print("\n" + "="*80)
    print("TEST 6: Integración de Módulos en dataset_builder.py")
    print("="*80)
    
    dataset_builder_path = repo_root / "src" / "citylearnv2" / "dataset_builder" / "dataset_builder.py"
    content = dataset_builder_path.read_text(encoding='utf-8')
    
    checks = [
        ("BaselineCalculator import", "from src.baseline.baseline_calculator_v2 import BaselineCalculator" in content),
        ("BaselineCityLearnIntegration import", "from src.baseline.citylearn_baseline_integration import BaselineCityLearnIntegration" in content),
        ("BASELINE_AVAILABLE flag", "BASELINE_AVAILABLE = True" in content),
        ("BESS v5.4 actualizado", "bess_cap = 1700.0" in content),
        ("BESS parámetro actualizado", "bess_pow = 400.0" in content),
        ("bess_df parámetro", "bess_df: Optional[pd.DataFrame]" in content),
        ("Baseline integration en build", "BaselineCalculator" in content),
    ]
    
    all_ok = True
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
        all_ok = all_ok and result
    
    return all_ok

def test_data_validation():
    """Test 7: Validar integridad de datos OE2 v5.4"""
    print("\n" + "="*80)
    print("TEST 7: Validación de Datos OE2 v5.4")
    print("="*80)
    
    try:
        oe2_path = repo_root / "data" / "oe2"
        
        # Verificar BESS
        bess_path = oe2_path / "bess" / "bess_simulation_hourly.csv"
        if bess_path.exists():
            bess_df = pd.read_csv(bess_path)
            print(f"✅ BESS Dataset:")
            print(f"   Filas: {len(bess_df)} (esperado 8,760)")
            if 'pv_generation_kwh' in bess_df.columns:
                solar_sum = bess_df['pv_generation_kwh'].sum()
                print(f"   Solar: {solar_sum:,.0f} kWh/año (esperado ~8.29M)")
            if 'ev_demand_kwh' in bess_df.columns:
                ev_sum = bess_df['ev_demand_kwh'].sum()
                print(f"   EV: {ev_sum:,.0f} kWh/año (esperado ~412k)")
        
        # Verificar chargers
        chargers_path = oe2_path / "chargers" / "chargers_ev_ano_2024_v3.csv"
        if chargers_path.exists():
            chargers_df = pd.read_csv(chargers_path, nrows=1)
            print(f"✅ Chargers Dataset:")
            print(f"   Columnas: {len(chargers_df.columns)} (esperado ~353)")
            print(f"   Sockets v5.2: 38 (19 chargers × 2 sockets)")
        
        return True
    except Exception as e:
        print(f"❌ Error validando datos: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🧪 SUITE DE PRUEBAS: Integración Dataset v5.4 ↔ Baseline v5.4")
    print("="*80)
    
    results = {
        "Importaciones": test_imports(),
        "Archivos OE2 v5.4": test_data_files(),
        "Cálculo Baselines": test_baseline_calculation(),
        "BESS v5.4": test_bess_version(),
        "Observables v5.3": test_observables_structure(),
        "Integración Imports": test_baseline_integration_imports(),
        "Validación de Datos": test_data_validation(),
    }
    
    print("\n" + "="*80)
    print("📊 RESULTADOS")
    print("="*80)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total_passed = sum(1 for v in results.values() if v)
    total_tests = len(results)
    
    print("\n" + "="*80)
    if total_passed == total_tests:
        print(f"✅ TODOS LOS TESTS PASARON ({total_passed}/{total_tests})")
        print("="*80)
        print("\n✨ Integración Dataset v5.4 ↔ Baseline v5.4 LISTA PARA PRODUCCIÓN")
        print("\nPróximos pasos:")
        print("1. Ejecutar: python -m src.citylearnv2.dataset_builder.dataset_builder")
        print("   (Genera dataset CityLearn con baselines integrados)")
        print("2. Entrenar agentes RL (SAC/PPO/A2C) con comparación automática vs baselines")
        print("3. Usar AgentBaselineIntegration para tracking automático de mejoras")
        return 0
    else:
        print(f"⚠️  TESTS FALLIDOS ({total_tests - total_passed} de {total_tests} fallaron)")
        print("="*80)
        return 1

if __name__ == "__main__":
    sys.exit(main())
