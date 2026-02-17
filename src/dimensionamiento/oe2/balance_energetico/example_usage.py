"""
Ejemplo de uso del modulo Balance Energetico.

Este script demuestra como utilizar el sistema de balance energetico
para analizar el sistema electrico de Iquitos.
"""
from pathlib import Path
from balance import BalanceEnergeticoSystem, BalanceEnergeticoConfig, main


def example_full_analysis():
    """Ejemplo 1: Analisis completo con todas las graficas."""
    print("\n" + "="*70)
    print("EJEMPLO 1: Analisis Completo del Balance Energetico")
    print("="*70)
    
    # Opcion 1: Usar la funcion main (mas simple)
    system = main(
        data_dir=Path("data/processed/citylearn/iquitos_ev_mall"),
        output_dir=Path("reports/balance_energetico"),
        year=2024,
        generate_plots=True
    )
    
    return system


def example_custom_config():
    """Ejemplo 2: Analisis con configuracion personalizada."""
    print("\n" + "="*70)
    print("EJEMPLO 2: Analisis con Configuracion Personalizada")
    print("="*70)
    
    # Crear configuracion personalizada
    config = BalanceEnergeticoConfig(
        data_dir=Path("data/processed/citylearn/iquitos_ev_mall"),
        pv_capacity_kwp=4050.0,
        bess_capacity_kwh=1700.0,   # v5.4: 1,700 kWh max SOC
        bess_power_kw=400.0,        # v5.4: 400 kW
        dod=0.80,  # Profundidad de descarga 80%
        efficiency_roundtrip=0.95,  # Eficiencia 95%
        year=2024,
        co2_intensity_kg_per_kwh=0.4521,  # kg CO2/kWh (generacion termica Iquitos)
    )
    
    # Crear sistema
    system = BalanceEnergeticoSystem(config)
    
    # Cargar todos los datasets
    if system.load_all_datasets():
        # Calcular balance energetico
        df_balance = system.calculate_balance()
        
        # Imprimir resumen
        system.print_summary()
        
        # Generar graficas
        system.plot_energy_balance(Path("reports/balance_energetico"))
        system.export_balance_csv(Path("reports/balance_energetico"))
    else:
        print("Error al cargar los datasets")
    
    return system


def example_metrics_only():
    """Ejemplo 3: Solo calcular metricas sin graficas."""
    print("\n" + "="*70)
    print("EJEMPLO 3: Calculo de Metricas (sin Graficas)")
    print("="*70)
    
    config = BalanceEnergeticoConfig(
        data_dir=Path("data/processed/citylearn/iquitos_ev_mall")
    )
    
    system = BalanceEnergeticoSystem(config)
    
    if system.load_all_datasets():
        system.calculate_balance()
        
        # Mostrar solo resumen
        system.print_summary()
        
        # Acceder a metricas individuales
        print("\nMetricas individuales:")
        for metric, value in system.metrics.items():
            print(f"  {metric}: {value}")
    
    return system


def example_incremental_analysis():
    """Ejemplo 4: Analisis incremental - generar cada grafica por separado."""
    print("\n" + "="*70)
    print("EJEMPLO 4: Generacion Incremental de Graficas")
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
    
    print("3. Imprimiendo metricas...")
    system.print_summary()
    
    print("4. Generando graficas (puede tomar un momento)...")
    output_dir = Path("reports/balance_energetico")
    try:
        system.plot_energy_balance(output_dir)
        system.export_balance_csv(output_dir)
        print(f"\n[OK] Analisis completado. Ver resultados en {output_dir}")
    except Exception as e:
        print(f"Error al generar graficas: {e}")
    
    return system


if __name__ == "__main__":
    import sys
    
    print("\n" + "#"*70)
    print("# BALANCE ENERGETICO - SISTEMA ELECTRICO IQUITOS")
    print("#"*70)
    
    # Ejecutar ejemplo segun argumento (default: ejemplo completo)
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
        print("\nEjecutando analisis completo (defecto)...")
        print("Uso: python example_usage.py [1|2|3|4]")
        print("  1 = Analisis completo (recomendado)")
        print("  2 = Configuracion personalizada")
        print("  3 = Solo metricas")
        print("  4 = Generacion incremental")
        
        system = example_full_analysis()
    
    print("\n[OK] Script finalizado")
