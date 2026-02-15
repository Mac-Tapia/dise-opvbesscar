"""
Ejemplo de uso del módulo Balance Energético.

Este script demuestra cómo utilizar el sistema de balance energético
para analizar el sistema eléctrico de Iquitos.
"""
from pathlib import Path
from balance import BalanceEnergeticoSystem, BalanceEnergeticoConfig, main


def example_full_analysis():
    """Ejemplo 1: Análisis completo con todas las gráficas."""
    print("\n" + "="*70)
    print("EJEMPLO 1: Análisis Completo del Balance Energético")
    print("="*70)
    
    # Opción 1: Usar la función main (más simple)
    system = main(
        data_dir=Path("data/processed/citylearn/iquitos_ev_mall"),
        output_dir=Path("reports/balance_energetico"),
        year=2024,
        generate_plots=True
    )
    
    return system


def example_custom_config():
    """Ejemplo 2: Análisis con configuración personalizada."""
    print("\n" + "="*70)
    print("EJEMPLO 2: Análisis con Configuración Personalizada")
    print("="*70)
    
    # Crear configuración personalizada
    config = BalanceEnergeticoConfig(
        data_dir=Path("data/processed/citylearn/iquitos_ev_mall"),
        pv_capacity_kwp=4050.0,
        bess_capacity_kwh=940.0,   # v5.2: 940 kWh (exclusivo EV, 100% cobertura)
        bess_power_kw=342.0,       # v5.2: 342 kW
        dod=0.80,  # Profundidad de descarga 80%
        efficiency_roundtrip=0.95,  # Eficiencia 95%
        year=2024,
        co2_intensity_kg_per_kwh=0.4521,  # kg CO2/kWh (generación térmica Iquitos)
    )
    
    # Crear sistema
    system = BalanceEnergeticoSystem(config)
    
    # Cargar todos los datasets
    if system.load_all_datasets():
        # Calcular balance energético
        df_balance = system.calculate_balance()
        
        # Imprimir resumen
        system.print_summary()
        
        # Generar gráficas
        system.plot_energy_balance(Path("reports/balance_energetico"))
        system.export_balance_csv(Path("reports/balance_energetico"))
    else:
        print("Error al cargar los datasets")
    
    return system


def example_metrics_only():
    """Ejemplo 3: Solo calcular métricas sin gráficas."""
    print("\n" + "="*70)
    print("EJEMPLO 3: Cálculo de Métricas (sin Gráficas)")
    print("="*70)
    
    config = BalanceEnergeticoConfig(
        data_dir=Path("data/processed/citylearn/iquitos_ev_mall")
    )
    
    system = BalanceEnergeticoSystem(config)
    
    if system.load_all_datasets():
        system.calculate_balance()
        
        # Mostrar solo resumen
        system.print_summary()
        
        # Acceder a métricas individuales
        print("\nMétricas individuales:")
        for metric, value in system.metrics.items():
            print(f"  {metric}: {value}")
    
    return system


def example_incremental_analysis():
    """Ejemplo 4: Análisis incremental - generar cada gráfica por separado."""
    print("\n" + "="*70)
    print("EJEMPLO 4: Generación Incremental de Gráficas")
    print("="*70)
    
    config = BalanceEnergeticoConfig(
        data_dir=Path("data/processed/citylearn/iquitos_ev_mall")
    )
    
    system = BalanceEnergeticoSystem(config)
    
    # Cargar y calcular
    print("\n1. Cargando datasets...")
    if not system.load_all_datasets():
        return None
    
    print("2. Calculando balance...")
    system.calculate_balance()
    
    print("3. Imprimiendo métricas...")
    system.print_summary()
    
    print("4. Generando gráficas (puede tomar un momento)...")
    output_dir = Path("reports/balance_energetico")
    try:
        system.plot_energy_balance(output_dir)
        system.export_balance_csv(output_dir)
        print(f"\n✓ Análisis completado. Ver resultados en {output_dir}")
    except Exception as e:
        print(f"Error al generar gráficas: {e}")
    
    return system


if __name__ == "__main__":
    import sys
    
    print("\n" + "#"*70)
    print("# BALANCE ENERGÉTICO - SISTEMA ELÉCTRICO IQUITOS")
    print("#"*70)
    
    # Ejecutar ejemplo según argumento (default: ejemplo completo)
    if len(sys.argv) > 1:
        ejemplo = sys.argv[1]
        if ejemplo == "1":
            system = example_full_analysis()
        elif ejemplo == "2":
            system = example_custom_config()
        elif ejemplo == "3":
            system = example_metrics_only()
        elif ejemplo == "4":
            system = example_incremental_analysis()
        else:
            print(f"Ejemplo {ejemplo} no reconocido")
            print("Uso: python example_usage.py [1|2|3|4]")
            sys.exit(1)
    else:
        # Ejecutar ejemplo completo por defecto
        print("\nEjecutando análisis completo (defecto)...")
        print("Uso: python example_usage.py [1|2|3|4]")
        print("  1 = Análisis completo (recomendado)")
        print("  2 = Configuración personalizada")
        print("  3 = Solo métricas")
        print("  4 = Generación incremental")
        
        system = example_full_analysis()
    
    print("\n✓ Script finalizado")
