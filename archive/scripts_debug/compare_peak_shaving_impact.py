#!/usr/bin/env python3
"""
Comparación: Cálculo de CO₂ ANTES vs DESPUÉS de Peak Shaving Implementation
Muestra el impacto concreto en reducción indirecta de CO₂
"""

CO2_FACTOR_IQUITOS = 0.4521  # kg CO2/kWh from diesel


def calculate_peak_shaving_factor(mall_kw: float) -> float:
    """Nueva fórmula con peak shaving."""
    if mall_kw > 2000.0:
        return 1.0 + (mall_kw - 2000.0) / max(1.0, mall_kw) * 0.5
    else:
        return 0.5 + (mall_kw / 2000.0) * 0.5


def compare_co2_calculation(solar_kw: float, bess_discharge_kw: float, mall_kw: float) -> dict:
    """Compara método antiguo vs nuevo."""
    
    # MÉTODO ANTIGUO (sin peak shaving)
    solar_avoided = min(solar_kw, 281.2)  # Max OE2
    co2_old = solar_avoided * CO2_FACTOR_IQUITOS
    
    # MÉTODO NUEVO (con peak shaving)
    bess_benefit = max(0.0, bess_discharge_kw)
    peak_shaving_factor = calculate_peak_shaving_factor(mall_kw)
    bess_co2 = bess_benefit * peak_shaving_factor * CO2_FACTOR_IQUITOS
    co2_new = (solar_avoided + bess_benefit * peak_shaving_factor) * CO2_FACTOR_IQUITOS
    
    # Cálculo diferencia
    difference = co2_new - co2_old
    percent_increase = (difference / co2_old * 100) if co2_old > 0 else 0
    
    return {
        'solar_kw': solar_kw,
        'bess_kw': bess_discharge_kw,
        'mall_kw': mall_kw,
        'co2_old_method': co2_old,
        'co2_new_method': co2_new,
        'bess_co2_contribution': bess_co2,
        'peak_shaving_factor': peak_shaving_factor,
        'co2_difference': difference,
        'percent_increase': percent_increase,
    }


def print_comparison(scenarios: list):
    """Imprime tabla comparativa."""
    print("\n" + "="*120)
    print("ANTES vs DESPUÉS: Impacto de Peak Shaving en CO₂ Indirecto")
    print("="*120)
    print()
    
    for i, scenario in enumerate(scenarios, 1):
        result = compare_co2_calculation(
            scenario['solar'], 
            scenario['bess'], 
            scenario['mall']
        )
        
        print(f"📊 ESCENARIO {i}: {scenario['name']}")
        print(f"   {'='*110}")
        print(f"   Input:")
        print(f"     • Solar generation:      {result['solar_kw']:>8.1f} kW")
        print(f"     • BESS discharge:        {result['bess_kw']:>8.1f} kW")
        print(f"     • Mall demand:           {result['mall_kw']:>8.1f} kW")
        print()
        print(f"   MÉTODO ANTIGUO (sin peak shaving):")
        print(f"     CO₂ Indirecto evitado = {result['co2_old_method']:>8.2f} kg/h")
        print(f"     └─ Solo solar: {result['solar_kw'] * CO2_FACTOR_IQUITOS:.2f} kg/h")
        print()
        print(f"   MÉTODO NUEVO (con peak shaving):")
        print(f"     CO₂ Indirecto evitado = {result['co2_new_method']:>8.2f} kg/h")
        print(f"     ├─ Solar:               {result['solar_kw'] * CO2_FACTOR_IQUITOS:.2f} kg/h")
        print(f"     ├─ BESS contribution:   {result['bess_co2_contribution']:>8.2f} kg/h")
        print(f"     └─ Peak shaving factor: {result['peak_shaving_factor']:>8.4f}x")
        print()
        
        if result['co2_difference'] > 0:
            print(f"   ✅ MEJORA: +{result['co2_difference']:.2f} kg/h (+{result['percent_increase']:.1f}%)")
        elif result['co2_difference'] < 0:
            print(f"   ❌ PEOR: {result['co2_difference']:.2f} kg/h ({result['percent_increase']:.1f}%)")
        else:
            print(f"   ➖ SIN CAMBIO")
        
        # Proyección anual
        annual_difference = result['co2_difference'] * 24 * 365
        print(f"   → Impacto anual: {annual_difference:>+.0f} kg CO₂/año")
        print()


def main():
    """Ejecuta comparación completa."""
    
    # Definir escenarios para mostrar
    scenarios = [
        {
            'name': 'BASELINE BAJO: Madrugada con BESS descargando poco',
            'solar': 0,      # Solar = 0 en noche
            'bess': 30,      # BESS 30 kW
            'mall': 500,     # Mall baseline bajo
        },
        {
            'name': 'BASELINE NORMAL: Día con solar y BESS',
            'solar': 250,    # Solar en día
            'bess': 50,      # BESS 50 kW
            'mall': 1500,    # Mall en baseline
        },
        {
            'name': 'BASELINE ALTO: Fin de rango normal',
            'solar': 300,    # Solar en peak solar
            'bess': 60,      # BESS 60 kW
            'mall': 2000,    # Mall en transición (2000 kW)
        },
        {
            'name': 'PICO MODERADO: Tarde/noche con demanda alta',
            'solar': 50,     # Solar bajando
            'bess': 80,      # BESS descargando más
            'mall': 2800,    # Pico moderado
        },
        {
            'name': 'PICO MÁXIMO: Hora de máxima demanda',
            'solar': 0,      # Sin solar
            'bess': 100,     # BESS al máximo
            'mall': 4000,    # Pico máximo
        },
    ]
    
    # Imprimir comparativas
    print_comparison(scenarios)
    
    # Resumen estadístico
    print("\n" + "="*120)
    print("📈 RESUMEN ESTADÍSTICO")
    print("="*120)
    
    total_difference = 0
    total_old = 0
    total_new = 0
    
    for scenario in scenarios:
        result = compare_co2_calculation(scenario['solar'], scenario['bess'], scenario['mall'])
        total_difference += result['co2_difference']
        total_old += result['co2_old_method']
        total_new += result['co2_new_method']
    
    print()
    print(f"  Escenarios analizados:        {len(scenarios)}")
    print(f"  CO₂ antiguo (total):          {total_old:>12.2f} kg/h")
    print(f"  CO₂ nuevo (total):            {total_new:>12.2f} kg/h")
    print(f"  Diferencia por hora:          {total_difference:>+12.2f} kg/h")
    print(f"  % Improvement:                {(total_difference/total_old*100):>+12.1f}%")
    print()
    
    # Impacto anual
    hours_in_year = 365 * 24
    annual_impact = total_difference * hours_in_year
    print(f"  💡 Impacto ANUAL:")
    print(f"     CO₂ menor indicador con peak shaving:  {annual_impact:>+12,.0f} kg/año")
    if annual_impact > 0:
        print(f"     → Equivalente a {annual_impact/1000:>+.1f} toneladas de CO₂/año evitadas")
    else:
        print(f"     → RESULTADO NEGATIVO (revisar cálculos)")
    
    print()
    print("="*120)
    print("✅ CONCLUSIÓN:")
    print(f"   Peak shaving factor amplifica beneficio CO₂ de BESS especialmente en picos.")
    print(f"   En horas pico (mall > 2000 kW), BESS vale 1.17-1.25x más.")
    print(f"   En baseline (mall ≤ 2000 kW), BESS vale 0.5-1.0x según demanda.")
    print("="*120)


if __name__ == "__main__":
    main()
