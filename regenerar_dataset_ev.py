#!/usr/bin/env python3
"""Regenerar dataset EV con parámetros corregidos (lambda=2.0)"""
from pathlib import Path
from src.dimensionamiento.oe2.disenocargadoresev.chargers import generate_socket_level_dataset_v3

print("🔄 Regenerando dataset EV con parámetros corregidos...")
print("   • Motos: lambda_arrivals = 2.0 (2 motos/socket/hora)")
print("   • Mototaxis: lambda_arrivals = 2.0 (2 mototaxis/socket/hora)")
print()

output_dir = Path('data/interim/oe2/chargers')
output_dir.mkdir(parents=True, exist_ok=True)

try:
    df_annual, df_daily = generate_socket_level_dataset_v3(
        output_dir=output_dir,
        random_seed=42
    )
    
    # Calcular energía total
    energy_cols = [col for col in df_annual.columns if '_power_kw' in col]
    total_energy = sum(df_annual[col].sum() for col in energy_cols)
    
    print("✅ DATASET REGENERADO EXITOSAMENTE")
    print(f"\n📊 Resumen:")
    print(f"   • Dataset anual: {len(df_annual)} filas × {len(df_annual.columns)} columnas")
    print(f"   • Energía total: {total_energy:,.0f} kWh/año")
    print(f"   • Archivo: {output_dir / 'chargers_ev_ano_2024_v3.csv'}")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
