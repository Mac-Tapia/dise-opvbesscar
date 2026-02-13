#!/usr/bin/env python3
"""
Validación de Integración de Métricas v5.4 en CityLearn

Verifica que:
1. Dataset BESS contiene nuevas columnas
2. Valores están normalizados correctamente [0,1]
3. Dataset builder puede procesarlas
4. Estadísticas coinciden con cálculos esperados
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Tuple
import json

# ─────────────────────────────────────────────────────────────────────────
# CONSTANTES ESPERADAS
# ─────────────────────────────────────────────────────────────────────────

EXPECTED_ROWS = 8760  # Horas/año
EXPECTED_AHORROS_ANUAL_MIN = 100000  # S/. mínimo esperado (100k)
EXPECTED_CO2_ANUAL_MIN = 150000  # kg mínimo esperado (150 ton)
EXPECTED_CO2_ANUAL_MAX = 250000  # kg máximo esperado (250 ton)

# ─────────────────────────────────────────────────────────────────────────
# FUNCIONES DE VALIDACIÓN
# ─────────────────────────────────────────────────────────────────────────


def validate_dataset_structure(df: pd.DataFrame) -> Tuple[bool, str]:
    """Valida estructura básica del dataset."""
    
    # Verificar número de filas
    if len(df) != EXPECTED_ROWS:
        return False, f"ERROR: {len(df)} filas encontradas, se esperan {EXPECTED_ROWS}"
    
    # Verificar nuevas columnas
    required_cols = [
        'peak_reduction_savings_soles',
        'peak_reduction_savings_normalized',
        'co2_avoided_indirect_kg',
        'co2_avoided_indirect_normalized'
    ]
    
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        return False, f"ERROR: Columnas faltantes: {missing}"
    
    return True, "✓ Estructura correcta"


def validate_normalization(df: pd.DataFrame) -> Tuple[bool, str]:
    """Valida que columnas normalizadas estén en rango [0,1]."""
    
    cols_norm = [
        'peak_reduction_savings_normalized',
        'co2_avoided_indirect_normalized'
    ]
    
    for col in cols_norm:
        min_val = df[col].min()
        max_val = df[col].max()
        
        if min_val < 0.0 or max_val > 1.0:
            return False, (
                f"ERROR: {col} fuera de rango [0,1]"
                f" → min={min_val:.4f}, max={max_val:.4f}"
            )
    
    return True, "✓ Normalización correcta [0,1]"


def validate_annual_totals(df: pd.DataFrame) -> Tuple[bool, str]:
    """Valida que los totales anuales sean razonables."""
    
    ahorros_total = df['peak_reduction_savings_soles'].sum()
    co2_total = df['co2_avoided_indirect_kg'].sum()
    
    # Validar ahorros
    if ahorros_total < EXPECTED_AHORROS_ANUAL_MIN:
        return False, f"ERROR: Ahorros total = S/. {ahorros_total:,.0f} < S/. {EXPECTED_AHORROS_ANUAL_MIN:,}"
    
    # Validar CO2
    if co2_total < EXPECTED_CO2_ANUAL_MIN or co2_total > EXPECTED_CO2_ANUAL_MAX:
        return False, (
            f"ERROR: CO2 total = {co2_total:,.0f} kg fuera de rango "
            f"[{EXPECTED_CO2_ANUAL_MIN:,}, {EXPECTED_CO2_ANUAL_MAX:,}]"
        )
    
    return True, (
        f"✓ Totales anuales correctos:\n"
        f"    Ahorros: S/. {ahorros_total:,.0f}/año\n"
        f"    CO2 evitado: {co2_total:,.0f} kg/año ({co2_total/1000:.1f} ton/año)"
    )


def validate_no_nulls(df: pd.DataFrame) -> Tuple[bool, str]:
    """Valida que no haya valores nulos."""
    
    cols = [
        'peak_reduction_savings_soles',
        'peak_reduction_savings_normalized',
        'co2_avoided_indirect_kg',
        'co2_avoided_indirect_normalized'
    ]
    
    null_cols = [col for col in cols if df[col].isna().any()]
    if null_cols:
        return False, f"ERROR: Valores nulos encontrados en: {null_cols}"
    
    return True, "✓ Sin valores nulos"


def validate_correlation(df: pd.DataFrame) -> Tuple[bool, str]:
    """Valida que valores reales y normalizados estén correlacionados."""
    
    # Los valores normalizados deben estar altamente correlacionados con los reales
    corr = df['peak_reduction_savings_soles'].corr(
        df['peak_reduction_savings_normalized']
    )
    
    if corr < 0.99:  # Debe ser casi perfecto (1.0)
        return False, f"ERROR: Correlación débil en ahorros: {corr:.4f}"
    
    corr_co2 = df['co2_avoided_indirect_kg'].corr(
        df['co2_avoided_indirect_normalized']
    )
    
    if corr_co2 < 0.99:  # Debe ser casi perfecto (1.0)
        return False, f"ERROR: Correlación débil en CO2: {corr_co2:.4f}"
    
    return True, f"✓ Correlación excelente (r={corr:.6f}, r_co2={corr_co2:.6f})"


def validate_dataset_builder_compatibility(df: pd.DataFrame) -> Tuple[bool, str]:
    """Valida que dataset_builder pueda procesar estos datos."""
    
    required_for_builder = ['bess_soc_percent']
    
    if 'bess_soc_percent' not in df.columns:
        return False, "ERROR: bess_soc_percent no encontrado (requerido por dataset_builder)"
    
    # Verificar que soc está en porcentaje [0,100]
    soc_min = df['bess_soc_percent'].min()
    soc_max = df['bess_soc_percent'].max()
    
    if soc_min < 0 or soc_max > 100:
        return False, f"ERROR: SOC fuera de rango [0,100]: min={soc_min}, max={soc_max}"
    
    return True, (
        f"✓ Compatible con dataset_builder\n"
        f"    SOC: {soc_min:.1f}% - {soc_max:.1f}%"
    )


# ─────────────────────────────────────────────────────────────────────────
# EJECUCIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────


def main():
    """Ejecuta todas las validaciones."""
    
    dataset_path = Path('data/oe2/bess/bess_simulation_hourly.csv')
    
    print("\n" + "="*80)
    print("VALIDACIÓN DE INTEGRACIÓN DE MÉTRICAS v5.4 - CityLearn Compatibility")
    print("="*80)
    print()
    
    # Verificar que el archivo existe
    if not dataset_path.exists():
        print(f"❌ ERROR: No se encontró {dataset_path}")
        return False
    
    print(f"📂 Cargando dataset: {dataset_path}")
    print(f"   Tamaño: {dataset_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    try:
        df = pd.read_csv(dataset_path)
    except Exception as e:
        print(f"❌ ERROR al cargar CSV: {e}")
        return False
    
    print(f"   Filas: {len(df):,}")
    print(f"   Columnas: {len(df.columns)}")
    print()
    
    # Lista de validaciones
    validations = [
        ("Estructura Dataset", validate_dataset_structure),
        ("Normalización [0,1]", validate_normalization),
        ("Totales Anuales", validate_annual_totals),
        ("Sin valores nulos", validate_no_nulls),
        ("Correlación real/normalizado", validate_correlation),
        ("Compatibilidad dataset_builder", validate_dataset_builder_compatibility),
    ]
    
    all_passed = True
    results: Dict[str, Tuple[bool, str]] = {}
    
    for name, validator in validations:
        try:
            passed, message = validator(df)
            results[name] = (passed, message)
            
            status = "✅" if passed else "❌"
            print(f"{status} {name}")
            
            # Mostrar mensaje multi-línea formateado
            for line in message.split("\n"):
                if line:
                    print(f"   {line}")
            print()
            
            if not passed:
                all_passed = False
        
        except Exception as e:
            print(f"❌ {name}")
            print(f"   Excepción: {e}")
            print()
            all_passed = False
            results[name] = (False, str(e))
    
    # ─────────────────────────────────────────────────────────────────
    # RESUMEN ESTADÍSTICO
    # ─────────────────────────────────────────────────────────────────
    
    print("="*80)
    print("RESUMEN ESTADÍSTICO DE MÉTRICAS")
    print("="*80)
    print()
    
    # Ahorros
    ahorros = df['peak_reduction_savings_soles']
    print("📊 Ahorros por Reducción de Picos:")
    print(f"   Min:     S/. {ahorros.min():>10,.2f}/h")
    print(f"   Max:     S/. {ahorros.max():>10,.2f}/h")
    print(f"   Median:  S/. {ahorros.median():>10,.2f}/h")
    print(f"   Mean:    S/. {ahorros.mean():>10,.2f}/h")
    print(f"   Std:     S/. {ahorros.std():>10,.2f}/h")
    print(f"   Total:   S/. {ahorros.sum():>10,.2f}/año")
    print()
    
    # CO2
    co2 = df['co2_avoided_indirect_kg']
    print("📊 CO₂ Evitado Indirectamente (BESS):")
    print(f"   Min:     {co2.min():>10,.2f} kg/h")
    print(f"   Max:     {co2.max():>10,.2f} kg/h")
    print(f"   Median:  {co2.median():>10,.2f} kg/h")
    print(f"   Mean:    {co2.mean():>10,.2f} kg/h")
    print(f"   Std:     {co2.std():>10,.2f} kg/h")
    print(f"   Total:   {co2.sum():>10,.0f} kg/año  ({co2.sum()/1000:>6.1f} ton/año)")
    print()
    
    # ─────────────────────────────────────────────────────────────────
    # VERIFICACIÓN FINAL
    # ─────────────────────────────────────────────────────────────────
    
    print("="*80)
    if all_passed:
        print("✅ VALIDACIÓN EXITOSA - Dataset listo para CityLearn v2 OE3")
        print("="*80)
        return True
    else:
        print("❌ VALIDACIÓN FALLIDA - Revisar errores arriba")
        print("="*80)
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
