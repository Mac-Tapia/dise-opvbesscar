#!/usr/bin/env python3
"""Script temporal de prueba del módulo Balance Energético."""

import sys
from pathlib import Path

# Debug info
print("Python:", sys.version)
print("Path:", Path.cwd())

try:
    print("\n[1/4] Importando módulos...")
    from src.dimensionamiento.oe2.balance_energetico.balance import (
        BalanceEnergeticoSystem,
        BalanceEnergeticoConfig,
    )
    print("  ✓ Importación exitosa")
    
    print("\n[2/4] Creando configuración...")
    config = BalanceEnergeticoConfig(
        data_dir=Path("data/processed/citylearn/iquitos_ev_mall")
    )
    print(f"  ✓ Config creada (data_dir: {config.data_dir})")
    
    print("\n[3/4] Inicializando sistema...")
    system = BalanceEnergeticoSystem(config)
    print("  ✓ Sistema inicializado")
    
    print("\n[4/4] Cargando datasets...")
    if system.load_all_datasets():
        print("  ✓ Datasets cargados exitosamente")
        
        print("\n[5/6] Calculando balance energético...")
        df = system.calculate_balance()
        print(f"  ✓ Balance calculado ({len(df)} horas)")
        
        print("\n[6/6] Métricas del sistema:")
        system.print_summary()
        
        print("\n[BONUS] Generando gráficas...")
        output_dir = Path("reports/balance_energetico")
        system.plot_energy_balance(output_dir)
        system.export_balance_csv(output_dir)
        
        print("\n" + "="*70)
        print("✓ ANÁLISIS COMPLETADO EXITOSAMENTE")
        print("="*70)
        print(f"\nResultados en: {output_dir}/")
        print("\nGráficas generadas:")
        for i in range(1, 8):
            print(f"  {i}. *.png")
        print("\nCSV: balance_energetico_horario.csv")
        
    else:
        print("  ✗ Error al cargar datasets")
        print("  Verificar: data/processed/citylearn/iquitos_ev_mall/")
        
except ImportError as e:
    print(f"✗ Error de importación: {e}")
    print("  Verificar que los módulos estén en su lugar")
    import traceback
    traceback.print_exc()
    
except FileNotFoundError as e:
    print(f"✗ Archivo no encontrado: {e}")
    import traceback
    traceback.print_exc()
    
except Exception as e:
    print(f"✗ Error inesperado: {e}")
    import traceback
    traceback.print_exc()
