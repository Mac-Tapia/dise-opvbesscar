#!/usr/bin/env python3
"""Script de diagnóstico detallado."""

import sys
from pathlib import Path

try:
    print("[1/5] Importando módulos...")
    from src.dimensionamiento.oe2.balance_energetico.balance import (
        BalanceEnergeticoSystem,
        BalanceEnergeticoConfig,
    )
    print("  ✓ Módulos importados")
    
    print("\n[2/5] Creando sistema...")
    config = BalanceEnergeticoConfig(
        data_dir=Path("data/processed/citylearn/iquitos_ev_mall")
    )
    system = BalanceEnergeticoSystem(config)
    print("  ✓ Sistema creado")
    
    print("\n[3/5] Cargando datasets...")
    if not system.load_all_datasets():
        print("  ✗ Error al cargar datasets")
        sys.exit(1)
    print("  ✓ Datasets cargados")
    
    # Debug: Verificar qué se cargó
    print(f"\n[DEBUG] Columnas de each dataframe:")
    print(f"  Solar: {list(system.df_solar.columns)[:5]}")
    print(f"  Chargers: {list(system.df_chargers.columns)[:5]}")
    print(f"  Mall: {list(system.df_mall.columns)}")
    print(f"  BESS: {list(system.df_bess.columns)}")
    
    print("\n[4/5] Calculando balance...")
    try:
        df_balance = system.calculate_balance()
        print(f"  ✓ Balance calculado ({len(df_balance)} horas)")
    except Exception as e:
        print(f"  ✗ Error en calculate_balance: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n[5/5] Imprimiendo métricas...")
    system.print_summary()
    
    print("\n✓ Análisis completado exitosamente")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
