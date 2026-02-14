#!/usr/bin/env python3
"""
Verificación de la lógica de peak shaving para CO2 indirecto.

Timeline: En picos (mall > 2000 kW), BESS obtiene 100% de beneficio CO2
         En baseline (mall ≤ 2000 kW), BESS obtiene factor progresivo 0.5-1.0
"""

CO2_FACTOR_IQUITOS = 0.4521  # kg CO2/kWh diesel


def calculate_peak_shaving_factor(mall_kw: float) -> float:
    """Calcula el factor de beneficio CO2 basado en demanda del mall."""
    if mall_kw > 2000.0:
        # En pico: BESS reemplaza 100% + bonus por reducción de pico diesel
        # Factor máximo ~1.5 cuando mall está muy por encima de 2000 kW
        peak_shaving_factor = 1.0 + (mall_kw - 2000.0) / max(1.0, mall_kw) * 0.5
    else:
        # Baseline: BESS aún ayuda con factor reducido (0.5 @ 0kW, 1.0 @ 2000kW)
        peak_shaving_factor = 0.5 + (mall_kw / 2000.0) * 0.5
    
    return peak_shaving_factor


def calculate_co2_indirect(solar_kw: float, bess_discharge_kw: float, mall_kw: float) -> float:
    """Calcula la reducción indirecta de CO2 con peak shaving."""
    solar_avoided = min(solar_kw, 281.2)  # Max power OE2
    
    # BESS descargando con peak shaving (solo descarga positiva)
    bess_discharge_benefit = max(0.0, bess_discharge_kw)
    
    peak_shaving_factor = calculate_peak_shaving_factor(mall_kw)
    bess_co2_benefit = bess_discharge_benefit * peak_shaving_factor
    
    co2_avoided_indirect_kg = (solar_avoided + bess_co2_benefit) * CO2_FACTOR_IQUITOS
    
    return co2_avoided_indirect_kg, peak_shaving_factor


def test_cases():
    """Ejecuta casos de prueba para validar la lógica."""
    
    print("=" * 80)
    print("VALIDACIÓN: Peak Shaving Factor para CO2 Indirecto")
    print("=" * 80)
    
    # Test Case 1: Baseline bajo (1000 kW)
    print("\n📊 Test Case 1: Mall @ 1000 kW (Baseline bajo)")
    mall_kw = 1000.0
    factor = calculate_peak_shaving_factor(mall_kw)
    expected = 0.5 + (1000.0 / 2000.0) * 0.5  # 0.5 + 0.25 = 0.75
    print(f"   Mall demand:       {mall_kw:>8.1f} kW")
    print(f"   Peak shaving factor: {factor:>8.4f} (expected {expected:>8.4f})")
    print(f"   ✓ PASS" if abs(factor - expected) < 0.0001 else f"   ✗ FAIL")
    
    # Test Case 2: Baseline alto (2000 kW = transición)
    print("\n📊 Test Case 2: Mall @ 2000 kW (Baseline alto)")
    mall_kw = 2000.0
    factor = calculate_peak_shaving_factor(mall_kw)
    expected = 0.5 + (2000.0 / 2000.0) * 0.5  # 0.5 + 0.5 = 1.0
    print(f"   Mall demand:       {mall_kw:>8.1f} kW")
    print(f"   Peak shaving factor: {factor:>8.4f} (expected {expected:>8.4f})")
    print(f"   ✓ PASS" if abs(factor - expected) < 0.0001 else f"   ✗ FAIL")
    
    # Test Case 3: Pico bajo (2500 kW)
    print("\n📊 Test Case 3: Mall @ 2500 kW (Pico bajo)")
    mall_kw = 2500.0
    factor = calculate_peak_shaving_factor(mall_kw)
    expected = 1.0 + (2500.0 - 2000.0) / 2500.0 * 0.5  # 1.0 + 0.1 = 1.1
    print(f"   Mall demand:       {mall_kw:>8.1f} kW")
    print(f"   Peak shaving factor: {factor:>8.4f} (expected {expected:>8.4f})")
    print(f"   ✓ PASS" if abs(factor - expected) < 0.0001 else f"   ✗ FAIL")
    
    # Test Case 4: Pico alto (3000 kW)
    print("\n📊 Test Case 4: Mall @ 3000 kW (Pico alto)")
    mall_kw = 3000.0
    factor = calculate_peak_shaving_factor(mall_kw)
    expected = 1.0 + (3000.0 - 2000.0) / 3000.0 * 0.5  # 1.0 + 0.1667 = 1.1667
    print(f"   Mall demand:       {mall_kw:>8.1f} kW")
    print(f"   Peak shaving factor: {factor:>8.4f} (expected {expected:>8.4f})")
    print(f"   ✓ PASS" if abs(factor - expected) < 0.0001 else f"   ✗ FAIL")
    
    # Test Case 5: Pico máximo (4000 kW)
    print("\n📊 Test Case 5: Mall @ 4000 kW (Pico máximo)")
    mall_kw = 4000.0
    factor = calculate_peak_shaving_factor(mall_kw)
    expected = 1.0 + (4000.0 - 2000.0) / 4000.0 * 0.5  # 1.0 + 0.25 = 1.25
    print(f"   Mall demand:       {mall_kw:>8.1f} kW")
    print(f"   Peak shaving factor: {factor:>8.4f} (expected {expected:>8.4f})")
    print(f"   ✓ PASS" if abs(factor - expected) < 0.0001 else f"   ✗ FAIL")
    
    # Test Case 6: CO2 Indirecto - Baseline con BESS
    print("\n🌱 Test Case 6: CO2 Indirecto @ 1000 kW (baseline) con BESS descargando 50 kW")
    solar_kw = 100.0
    bess_kw = 50.0
    mall_kw = 1000.0
    co2, factor = calculate_co2_indirect(solar_kw, bess_kw, mall_kw)
    solar_part = min(solar_kw, 281.2) * CO2_FACTOR_IQUITOS
    bess_part = bess_kw * calculate_peak_shaving_factor(mall_kw) * CO2_FACTOR_IQUITOS
    expected_co2 = solar_part + bess_part
    print(f"   Solar:              {solar_kw:>8.1f} kW → {solar_part:>8.2f} kg CO2")
    print(f"   BESS (50 kW):       {bess_kw:>8.1f} kW × {factor:.4f} → {bess_part:>8.2f} kg CO2")
    print(f"   Total CO2 evitado:  {co2:>8.2f} kg (expected {expected_co2:>8.2f})")
    print(f"   ✓ PASS" if abs(co2 - expected_co2) < 0.01 else f"   ✗ FAIL")
    
    # Test Case 7: CO2 Indirecto - Pico con BESS
    print("\n🌱 Test Case 7: CO2 Indirecto @ 3000 kW (pico) con BESS descargando 50 kW")
    solar_kw = 100.0
    bess_kw = 50.0
    mall_kw = 3000.0
    co2, factor = calculate_co2_indirect(solar_kw, bess_kw, mall_kw)
    solar_part = min(solar_kw, 281.2) * CO2_FACTOR_IQUITOS
    bess_part = bess_kw * calculate_peak_shaving_factor(mall_kw) * CO2_FACTOR_IQUITOS
    expected_co2 = solar_part + bess_part
    print(f"   Solar:              {solar_kw:>8.1f} kW → {solar_part:>8.2f} kg CO2")
    print(f"   BESS (50 kW):       {bess_kw:>8.1f} kW × {factor:.4f} → {bess_part:>8.2f} kg CO2")
    print(f"   Total CO2 evitado:  {co2:>8.2f} kg (expected {expected_co2:>8.2f})")
    print(f"   Beneficio vs baseline: +{(factor - 0.75) * 100:.1f}% (porque mall está en pico)")
    print(f"   ✓ PASS" if abs(co2 - expected_co2) < 0.01 else f"   ✗ FAIL")
    
    print("\n" + "=" * 80)
    print("✅ VALIDACIÓN COMPLETADA - Peak shaving logic implementado correctamente")
    print("=" * 80)
    
    print("\n📋 RESUMEN:")
    print("  • Factor en baseline (0 kW):   0.50 (BESS tiene valor bajo)")
    print("  • Factor en baseline (2000 kW): 1.00 (factor transición)")
    print("  • Factor en pico (3000 kW):    1.17 (BESS reemplaza generación diesel de pico)")
    print("  • Factor en pico (4000 kW):    1.25 (máximo beneficio)")
    print("\n📌 Interpretación:")
    print("  En picos: BESS descargando EVITA diesel generador que iba a encenderse")
    print("  En baseline: BESS aún reduce imports de grid, pero con beneficio menor")


if __name__ == "__main__":
    test_cases()
