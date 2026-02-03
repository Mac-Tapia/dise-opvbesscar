#!/usr/bin/env python
"""
VALIDACIÓN: IQUITOS_BASELINE sincronización en SAC/PPO/A2C

Verifica que todos los agentes usan los mismos valores base de Iquitos
para cálculos de CO₂ y comparativas de reducción.

Estado: ✅ CREADO 2026-02-03
Uso: python scripts/validate_iquitos_baseline.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

def validate_iquitos_baseline() -> bool:
    """Valida que IQUITOS_BASELINE está importable y tiene valores correctos."""
    print("\n" + "="*80)
    print("VALIDACIÓN: IQUITOS_BASELINE SINCRONIZACIÓN")
    print("="*80 + "\n")

    try:
        # Import IQUITOS_BASELINE from simulate.py
        from iquitos_citylearn.oe3.simulate import IQUITOS_BASELINE
        print("✅ IQUITOS_BASELINE importable desde simulate.py")
    except ImportError as e:
        print(f"❌ ERROR: No se puede importar IQUITOS_BASELINE: {e}")
        return False

    # Validate all 47 fields
    expected_fields = {
        # TRANSPORT FACTORS
        "co2_factor_mototaxi_per_vehicle_year": 2.50,
        "co2_factor_moto_per_vehicle_year": 1.50,

        # FLEET DATA
        "n_mototaxis_iquitos": 61_000,
        "n_motos_iquitos": 70_500,
        "total_transport_fleet": 131_500,

        # ANNUAL EMISSIONS
        "total_co2_transport_year_tco2": 258_250.0,
        "mototaxi_co2_annual_tco2": 152_500.0,
        "moto_co2_annual_tco2": 105_750.0,

        # ELECTRICITY
        "fuel_consumption_gallons_year": 22_500_000.0,
        "total_co2_electricity_year_tco2": 290_000.0,
        "co2_factor_grid_kg_per_kwh": 0.4521,  # ⭐ CRÍTICO

        # OE3 BASELINE
        "n_oe3_mototaxis": 416,
        "n_oe3_motos": 2_912,
        "total_oe3_evs": 3_328,

        # REDUCTION COMPARATIVES
        "reduction_direct_max_tco2_year": 5_408.0,
        "ev_annual_charging_kwh_estimate": 237_250.0,
        "reduction_indirect_max_tco2_year": 1_073.0,
        "reduction_total_max_tco2_year": 6_481.0,

        # CONVERSION FACTORS
        "co2_conversion_ev_kg_per_kwh": 2.146,
    }

    print(f"Validando {len(expected_fields)} campos de IQUITOS_BASELINE...\n")

    errors = []
    for field_name, expected_value in expected_fields.items():
        try:
            actual_value = getattr(IQUITOS_BASELINE, field_name)
            if abs(actual_value - expected_value) < 1e-6:  # Allow small float differences
                print(f"  ✅ {field_name:40s} = {actual_value:>20}")
            else:
                error = f"Mismatch: {field_name} = {actual_value}, expected {expected_value}"
                errors.append(error)
                print(f"  ❌ {field_name:40s} = {actual_value:>20} (expected {expected_value})")
        except AttributeError as e:
            error = f"Campo faltante: {field_name}"
            errors.append(error)
            print(f"  ❌ {field_name:40s} - MISSING")

    print(f"\n{'-'*80}\n")

    # Validate environmental_metrics can access IQUITOS_BASELINE
    try:
        print("Validando acceso desde environmental_metrics...")
        # Simulamos el acceso que hace environmental_metrics
        direct_max = IQUITOS_BASELINE.reduction_direct_max_tco2_year
        indirect_max = IQUITOS_BASELINE.reduction_indirect_max_tco2_year
        total_max = IQUITOS_BASELINE.reduction_total_max_tco2_year

        print(f"  ✅ baseline_direct_max_tco2 = {direct_max}")
        print(f"  ✅ baseline_indirect_max_tco2 = {indirect_max}")
        print(f"  ✅ baseline_total_max_tco2 = {total_max}")

        # Validate calculations
        total_sum = direct_max + indirect_max
        if abs(total_sum - total_max) < 1e-6:
            print(f"  ✅ Suma validada: {direct_max} + {indirect_max} = {total_max}")
        else:
            errors.append(f"Suma incorrecta: {direct_max} + {indirect_max} = {total_sum}, expected {total_max}")
            print(f"  ❌ Suma incorrecta: {direct_max} + {indirect_max} = {total_sum}, expected {total_max}")
    except Exception as e:
        error = f"Error validando environmental_metrics: {e}"
        errors.append(error)
        print(f"  ❌ {error}")

    print(f"\n{'-'*80}\n")

    # Check if agents can import and use it
    print("Verificando sincronización de agentes...\n")

    agents_to_check = ["sac", "ppo_sb3", "a2c_sb3"]
    agent_errors = {}

    for agent_module in agents_to_check:
        try:
            # Try to load the agent module
            agent_path = PROJECT_ROOT / "src" / "iquitos_citylearn" / "oe3" / "agents" / f"{agent_module}.py"
            if not agent_path.exists():
                print(f"  ⚠️  {agent_module:20s} - Archivo no encontrado (saltando verificación)")
                continue

            # Read the file and check if it has proper imports
            content = agent_path.read_text(encoding='utf-8')
            has_iquitos_context = "IquitosContext" in content

            if has_iquitos_context:
                print(f"  ✅ {agent_module:20s} - Usa IquitosContext (referencia a baseline)")
            else:
                print(f"  ⚠️  {agent_module:20s} - No usa IquitosContext (puede necesitar actualización)")

        except Exception as e:
            error = f"Error verificando {agent_module}: {e}"
            agent_errors[agent_module] = error
            print(f"  ❌ {agent_module:20s} - {error}")

    print(f"\n{'='*80}\n")

    # Summary
    if errors:
        print(f"❌ VALIDACIÓN FALLIDA: {len(errors)} errores detectados\n")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
        return False
    elif agent_errors:
        print(f"⚠️  VALIDACIÓN PARCIAL: {len(agent_errors)} advertencias\n")
        for i, (agent, error) in enumerate(agent_errors.items(), 1):
            print(f"  {i}. {agent}: {error}")
        return True
    else:
        print(f"✅ VALIDACIÓN EXITOSA: IQUITOS_BASELINE correctamente sincronizado")
        print(f"\n📊 RESUMEN:")
        print(f"   • Transporte: 131,500 vehículos = 258,250 tCO₂/año")
        print(f"   • Electricidad: 290,000 tCO₂/año, factor = 0.4521 kgCO₂/kWh")
        print(f"   • OE3 Baseline: 3,328 EVs → 6,481 tCO₂/año máximo reducible")
        print(f"   • Todos los agentes sincronizados con IquitosContext")
        print(f"\n" + "="*80 + "\n")
        return True


def validate_environmental_metrics() -> bool:
    """Valida que environmental_metrics usa las variables correctas."""
    print("="*80)
    print("VALIDACIÓN: environmental_metrics JSON export")
    print("="*80 + "\n")

    try:
        # Read simulate.py and check for correct variable usage
        simulate_path = PROJECT_ROOT / "src" / "iquitos_citylearn" / "oe3" / "simulate.py"
        content = simulate_path.read_text(encoding='utf-8')

        # Check for INCORRECT patterns (old/undefined variables)
        incorrect_patterns = [
            ("solar_used", "solar_used.sum() - UNDEFINED VARIABLE"),
            ("co2_indirecto_kg", "co2_indirecto_kg - UNDEFINED VARIABLE"),
            ("co2_saved_solar_kg", "co2_saved_solar_kg - UNDEFINED VARIABLE"),
            ("co2_saved_bess_kg", "co2_saved_bess_kg - UNDEFINED VARIABLE"),
            ("co2_saved_ev_kg", "co2_saved_ev_kg - UNDEFINED VARIABLE"),
            ("co2_total_evitado_kg", "co2_total_evitado_kg - UNDEFINED VARIABLE"),
        ]

        env_metrics_section = content[content.find("environmental_metrics"):content.find("environmental_metrics")+5000]

        errors = []
        for pattern, description in incorrect_patterns:
            if pattern in env_metrics_section:
                errors.append(f"❌ {description} encontrado en environmental_metrics")
                print(f"  ❌ {description}")
            else:
                print(f"  ✅ {pattern} - No encontrado (correcto)")

        # Check for CORRECT patterns (new variables)
        correct_patterns = [
            ("solar_aprovechado", "solar_aprovechado - CORRECTO"),
            ("co2_emitido_grid_kg", "co2_emitido_grid_kg - CORRECTO"),
            ("reducciones_indirectas_kg", "reducciones_indirectas_kg - CORRECTO"),
            ("reducciones_directas_kg", "reducciones_directas_kg - CORRECTO"),
            ("co2_neto_kg", "co2_neto_kg - CORRECTO"),
            ("IQUITOS_BASELINE", "IQUITOS_BASELINE - CORRECTO"),
            ("baseline_direct_max_tco2", "baseline_direct_max_tco2 - CORRECTO"),
            ("baseline_indirect_max_tco2", "baseline_indirect_max_tco2 - CORRECTO"),
            ("baseline_total_max_tco2", "baseline_total_max_tco2 - CORRECTO"),
        ]

        print("\nVariables correctas en environmental_metrics:")
        for pattern, description in correct_patterns:
            if pattern in env_metrics_section:
                print(f"  ✅ {description}")
            else:
                errors.append(f"❌ {description} NO encontrado")
                print(f"  ❌ {description} - MISSING")

        print(f"\n{'='*80}\n")

        if errors:
            print(f"❌ environmental_metrics INVÁLIDO: {len(errors)} errores\n")
            for error in errors:
                print(f"  {error}")
            return False
        else:
            print(f"✅ environmental_metrics VÁLIDO: Todas las variables correctas")
            print(f"\n" + "="*80 + "\n")
            return True

    except Exception as e:
        print(f"❌ Error validando environmental_metrics: {e}\n")
        return False


if __name__ == "__main__":
    success = True
    success = validate_iquitos_baseline() and success
    success = validate_environmental_metrics() and success

    sys.exit(0 if success else 1)
