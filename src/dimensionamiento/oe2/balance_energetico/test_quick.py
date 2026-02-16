"""
Script de prueba rapida del modulo Balance Energetico.

Valida que todos los datasets esten disponibles y ejecuta un analisis
basico del balance energetico con generacion de las 7 graficas principales.
"""
from pathlib import Path
from balance import main


def run_quick_test():
    """Ejecuta una prueba rapida del sistema."""
    print("\n" + "="*70)
    print("PRUEBA RAPIDA: Balance Energetico del Sistema Electrico")
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
        exists = "[OK]" if f.exists() else "[X]"
        status = "Encontrado" if f.exists() else "FALTA"
        print(f"  {exists} {f.relative_to(Path('.').parent)}: {status}")
        if not f.exists():
            all_exist = False
    
    if not all_exist:
        print("\n[X] Algunos archivos estan faltando. Verifique la ruta data/processed/citylearn/iquitos_ev_mall/")
        return False
    
    # Ejecutar analisis
    try:
        print("\nEjecutando analisis completo...")
        system = main(
            data_dir=data_dir,
            output_dir=output_dir,
            year=2024,
            generate_plots=True
        )
        
        print(f"\n[OK] Analisis completado exitosamente")
        print(f"  Resultados guardados en: {output_dir}")
        
        return True
    
    except Exception as e:
        print(f"\n[X] Error durante el analisis: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_quick_test()
    exit(0 if success else 1)
