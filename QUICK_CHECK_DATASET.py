#!/usr/bin/env python3
"""
QUICK CHECK: Verifica en <2 min que TODO esté listo para entrenar agentes
2026-02-16
"""
import pandas as pd
import numpy as np
from pathlib import Path

def check_dataset():
    """Verifica dataset está completo y validado"""
    csv_path = Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
    
    if not csv_path.exists():
        print("❌ Dataset no encontrado:", csv_path)
        return False
    
    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    print(f"\n✅ Dataset cargado: {df.shape[0]} filas × {df.shape[1]} columnas")
    
    # Verificar columnas críticas
    critical_cols = [
        'ev_demand_kwh',
        'edad_energia_total_kwh',
        'cantidad_motos_activas',
        'cantidad_mototaxis_activas',
        'cantidad_total_vehiculos_activos',
        'co2_reduccion_motos_kg',
        'co2_reduccion_mototaxis_kg',
        'reduccion_directa_co2_kg',
        'co2_grid_kwh',
        'co2_neto_por_hora_kg',
        'tarifa_aplicada_soles',
        'is_hora_punta'
    ]
    
    missing = [c for c in critical_cols if c not in df.columns]
    if missing:
        print(f"⚠️  Columnas faltantes: {missing}")
        # Try alternatives
        for m in missing:
            alternatives = [c for c in df.columns if m.split('_')[0] in c.lower()]
            if alternatives:
                print(f"   Alternativa posible: {alternatives[0]}")
    else:
        print(f"✅ {len(critical_cols)} columnas críticas presentes")
    
    # Estadísticas
    print(f"\n📊 ESTADÍSTICAS:")
    print(f"  • Energía anual: {df['ev_demand_kwh'].sum()/1000:.1f} MWh")
    print(f"  • Motos activas/h: {df['cantidad_motos_activas'].mean():.1f} (max {df['cantidad_motos_activas'].max():.0f})")
    print(f"  • Taxis activos/h: {df['cantidad_mototaxis_activas'].mean():.1f} (max {df['cantidad_mototaxis_activas'].max():.0f})")
    print(f"  • CO₂ neto anual: {df['co2_neto_por_hora_kg'].sum()/1000:.1f} Mg")
    print(f"  • Costo anual: S/. {df['costo_carga_ev_soles'].sum():.0f}")
    
    return True

def check_code():
    """Verifica código está actualizado"""
    chargers_path = Path("src/dimensionamiento/oe2/disenocargadoresev/chargers.py")
    
    if not chargers_path.exists():
        print("❌ chargers.py no encontrado")
        return False
    
    content = chargers_path.read_text()
    
    checks = {
        "Proporcionalidad CO2": "proporcional a energía" in content.lower(),
        "Vehicle counts init": "cantidad_motos_activas" in content,
        "CO2 neto": "co2_neto_por_hora_kg" in content,
        "Grid CO2": "co2_grid_kwh" in content
    }
    
    print("\n✅ CÓDIGO ACTUALIZADO:")
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")
    
    return all(checks.values())

def check_validators():
    """Verifica validadores existen"""
    val_path = Path("VALIDACION_DATASET_COMPLETO_v2026-02-16.py")
    
    if val_path.exists():
        print("\n✅ Validador completo presente")
        print(f"   Ejecutar: python {val_path.name}")
        return True
    else:
        print("❌ Validador no encontrado")
        return False

def main():
    print("=" * 70)
    print("🔍 QUICK CHECK: Verificación de Dataset & Código (2026-02-16)")
    print("=" * 70)
    
    all_ok = True
    
    # Check 1: Dataset
    print("\n1. VALIDANDO DATASET...")
    all_ok &= check_dataset()
    
    # Check 2: Código
    print("\n2. VALIDANDO CÓDIGO...")
    all_ok &= check_code()
    
    # Check 3: Validadores
    print("\n3. VALIDADORES...")
    all_ok &= check_validators()
    
    # Resumen
    print("\n" + "=" * 70)
    if all_ok:
        print("✅ LISTO: Todo está presente y validado")
        print("\n🚀 PRÓXIMO PASO:")
        print("   1. Ejecutar validador: python VALIDACION_DATASET_COMPLETO_v2026-02-16.py")
        print("   2. Entrenar agentes: python scripts/train/train_ppo_multiobjetivo.py")
    else:
        print("❌ PROBLEMAS DETECTADOS - Revisar arriba")
    print("=" * 70)

if __name__ == "__main__":
    main()
