"""
Script de prueba rápida del módulo Balance Energético.

Valida que todos los datasets estén disponibles y ejecuta un análisis
básico del balance energético con generación de las 7 gráficas principales.
"""
from pathlib import Path
from balance import main


def run_quick_test():
    """Ejecuta una prueba rápida del sistema."""
    print("\n" + "="*70)
    print("PRUEBA RÁPIDA: Balance Energético del Sistema Eléctrico")
    print("="*70)
    
    # Directorios
    data_dir = Path("data/processed/citylearn/iquitos_ev_mall")
    output_dir = Path("reports/balance_energetico")
    
    # Validar que los datos existan
    required_files = [
        data_dir / "Generacionsolar" / "pv_generation_hourly_citylearn_v2.csv",
        data_dir / "chargers" / "chargers_real_hourly_2024.csv",
        data_dir / "demandamallkwh" / "demandamallhorakwh.csv",
        data_dir / "electrical_storage_simulation.csv",
    ]
    
    print("\nValidando archivos de entrada...")
    all_exist = True
    for f in required_files:
        exists = "✓" if f.exists() else "✗"
        status = "Encontrado" if f.exists() else "FALTA"
        print(f"  {exists} {f.relative_to(Path('.').parent)}: {status}")
        if not f.exists():
            all_exist = False
    
    if not all_exist:
        print("\n✗ Algunos archivos están faltando. Verifique la ruta data/processed/citylearn/iquitos_ev_mall/")
        return False
    
    # Ejecutar análisis
    try:
        print("\nEjecutando análisis completo...")
        system = main(
            data_dir=data_dir,
            output_dir=output_dir,
            year=2024,
            generate_plots=True
        )
        
        print(f"\n✓ Análisis completado exitosamente")
        print(f"  Resultados guardados en: {output_dir}")
        
        return True
    
    except Exception as e:
        print(f"\n✗ Error durante el análisis: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_quick_test()
    exit(0 if success else 1)
