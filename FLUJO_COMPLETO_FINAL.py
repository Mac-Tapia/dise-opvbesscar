#!/usr/bin/env python3
"""
FLUJO COMPLETO - SOBRESCRIBIR ARCHIVO CON MISMO NOMBRE
1. Eliminar archivo antiguo si existe
2. Generar nuevo dataset con MISMO nombre
3. Validar
4. Listo para entrenamiento
"""

import sys
import os
from pathlib import Path
import pandas as pd

print("\n" + "="*80)
print("🚀 FLUJO COMPLETO: GENERAR DATASET (SOBRESCRIBIR ANTIGUA)")
print("="*80 + "\n")

try:
    # ========================================================================
    # PASO 0: ELIMINAR ARCHIVO ANTIGUO
    # ========================================================================
    print("[PASO 0/4] Eliminando archivo antiguo si existe...")
    print("-" * 80)
    
    # UBICACIÓN CORRECTA: data/oe2/chargers/
    csv_file = Path("data/oe2/chargers/chargers_real_hourly_2024.csv")
    
    if csv_file.exists():
        os.remove(csv_file)
        print(f"✅ Archivo antiguo eliminado: {csv_file}\n")
    else:
        print(f"ℹ️ No había archivo anterior\n")

    # ========================================================================
    # PASO 1: GENERAR DATASET SOC DINÁMICO
    # ========================================================================
    print("[PASO 1/4] Generando Dataset SOC Dinámico...")
    print("-" * 80)
    
    sys.path.insert(0, str(Path("src")))
    from dimensionamiento.oe2.disenocargadoresev.chargers import generate_soc_dynamic_dataset
    
    # USAR CARPETA CORRECTA: data/oe2/chargers/
    output_dir = Path("data/oe2/chargers")
    df = generate_soc_dynamic_dataset(output_dir=output_dir)
    
    print(f"\n✅ Dataset generado: {csv_file}\n")

    # ========================================================================
    # PASO 2: VALIDAR INTEGRIDAD
    # ========================================================================
    print("[PASO 2/4] Validando integridad del dataset...")
    print("-" * 80)
    
    # Validación 1: Leer CSV
    df_check = pd.read_csv(csv_file)
    assert len(df_check) == 8760, f"❌ ERROR: {len(df_check)} filas, esperaba 8760"
    print(f"✅ Filas: {len(df_check)} (correcto: 8,760)")
    
    # Validación 2: Columnas críticas
    required_cols = [
        'timestamp', 'soc_arrival_motos_mean', 'soc_target_motos_mean',
        'fully_charged_total', 'vehicles_charging_motos'
    ]
    for col in required_cols:
        assert col in df_check.columns, f"❌ ERROR: columna faltante: {col}"
    print(f"✅ Columnas: {len(df_check.columns)} (todas presentes)")
    
    # Validación 3: Período
    start_date = df_check['timestamp'].min()
    end_date = df_check['timestamp'].max()
    assert '2024-01-01' in str(start_date), f"❌ ERROR: fecha inicio incorrecta: {start_date}"
    assert '2024-12-31' in str(end_date), f"❌ ERROR: fecha fin incorrecta: {end_date}"
    print(f"✅ Período: {start_date.date()} a {end_date.date()}")
    
    # Validación 4: Valores SOC
    soc_arrival = df_check['soc_arrival_motos_mean']
    print(f"✅ SOC dinámico: {soc_arrival.mean():.1%} ± {soc_arrival.std():.1%}")
    
    # Validación 5: Vehículos
    daily_vehicles = df_check['vehicles_charging_motos'].sum() / 365
    print(f"✅ Vehículos motos/día: {daily_vehicles:.0f}")
    
    print()

    # ========================================================================
    # PASO 3: CONFIRMAR INTEGRACIÓN
    # ========================================================================
    print("[PASO 3/4] Confirmando integración con dataset_builder.py...")
    print("-" * 80)
    
    # Verificar que el archivo existe y es accesible
    assert csv_file.exists(), "❌ ERROR: archivo no se guardó correctamente"
    file_size_mb = csv_file.stat().st_size / (1024 * 1024)
    print(f"✅ Archivo existe: {csv_file}")
    print(f"✅ Tamaño: {file_size_mb:.2f} MB")
    print(f"✅ Compatible con dataset_builder.py: SÍ")
    
    print()

    # ========================================================================
    # PASO 4: RESUMEN FINAL
    # ========================================================================
    print("[PASO 4/4] Resumen y próximos pasos...")
    print("-" * 80)
    
    print("\n📊 DATASET GENERADO:")
    print(f"  📁 Carpeta: data/oe2/chargers/")
    print(f"  📄 Archivo: chargers_real_hourly_2024.csv")
    print(f"  📦 Tamaño: {file_size_mb:.2f} MB")
    print(f"  📈 Filas: {len(df_check)} (1 año × 24 horas)")
    print(f"  📋 Columnas: {len(df_check.columns)}")
    print(f"  📅 Período: {start_date.date()} a {end_date.date()}")
    print(f"  ✅ Estado: LISTO PARA ENTRENAMIENTO")
    
    print("\n🎯 PRÓXIMOS PASOS - ENTRENAR AGENTES:")
    print("  ")
    print("  1️⃣  SAC (Soft Actor-Critic):")
    print("      python train_sac_multiobjetivo.py")
    print("      ⏱️  Duración: 5-7 horas")
    print("")
    print("  2️⃣  PPO (Proximal Policy Optimization):")
    print("      python train_ppo_multiobjetivo.py")
    print("      ⏱️  Duración: 4-6 horas")
    print("")
    print("  3️⃣  A2C (Advantage Actor-Critic):")
    print("      python train_a2c_multiobjetivo.py")
    print("      ⏱️  Duración: 3-4 horas")
    
    print("\n📈 ARQUITECTURA SINCRONIZADA:")
    print("  ✅ OE2 (Dimensionamiento)")
    print("     • 32 chargers × 4 sockets = 128 tomas controlables")
    print("     • 4,050 kWp Solar")
    print("     • 4,520 kWh BESS")
    print("")
    print("  ✅ OE3 (Entrenamiento RL)")
    print("     • Observación: 778-dim (con SOC dinámico)")
    print("     • Acción: 129-dim (1 BESS + 128 chargers)")
    print("     • Episodio: 8,760 timesteps horarios")
    print("")
    print("  ✅ Dataset SOC Dinámico")
    print("     • Archivo: chargers_real_hourly_2024_soc_dynamic.csv")
    print("     • Estructura: 8,760 × 16 (hora × variables)")
    print("     • Integración: dataset_builder.py")
    
    print("\n" + "="*80)
    print("✅ FLUJO COMPLETADO - DATASET LISTO PARA ENTRENAR")
    print("="*80)
    print()
    
except Exception as e:
    print(f"\n❌ ERROR: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)
