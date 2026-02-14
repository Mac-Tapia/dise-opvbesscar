#!/usr/bin/env python
"""
Test script para validar generación de CSVs de cargadores.
Verifica:
- Que todos los archivos existan
- Que no haya duplicidades
- Que la estructura sea correcta
"""

import pandas as pd
from pathlib import Path
import json

def test_csv_generation():
    """Valida que todos los CSVs se generaron correctamente."""
    
    output_dir = Path("data/oe2/chargers")
    expected_files = [
        "tabla_parametros.csv",
        "tabla_infraestructura.csv",
        "tabla_escenarios_detallados.csv",
        "tabla_estadisticas_escenarios.csv",
        "tabla_escenario_recomendado.csv",
        "chargers_real_statistics.csv"
    ]
    
    print("="*70)
    print("VALIDACIÓN DE GENERACIÓN DE CSVs PARA CARGADORES")
    print("="*70)
    print()
    
    # 1. Verificar existencia de archivos
    print("1. VERIFICACIÓN DE EXISTENCIA:")
    print("-" * 70)
    missing_files = []
    for expected_file in expected_files:
        filepath = output_dir / expected_file
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"  ✓ {expected_file:<40} ({size:>6} bytes)")
        else:
            print(f"  ✗ {expected_file:<40} (FALTA)")
            missing_files.append(expected_file)
    
    if missing_files:
        print(f"\n⚠ Advertencia: {len(missing_files)} archivo(s) faltante(s)")
        return False
    print()
    
    # 2. Verificar estructura de cada CSV
    print("2. VERIFICACIÓN DE ESTRUCTURA:")
    print("-" * 70)
    
    results = {}
    
    # tabla_parametros.csv
    try:
        df = pd.read_csv(output_dir / "tabla_parametros.csv")
        expected_cols = ["Parámetro", "Valor"]
        if set(df.columns) == set(expected_cols) and len(df) == 12:
            print(f"  ✓ tabla_parametros.csv: {len(df)} parámetros")
            results["tabla_parametros.csv"] = "OK"
        else:
            print(f"  ✗ tabla_parametros.csv: Estructura incorrecta")
            results["tabla_parametros.csv"] = "ERROR"
    except Exception as e:
        print(f"  ✗ tabla_parametros.csv: {e}")
        results["tabla_parametros.csv"] = "ERROR"
    
    # tabla_infraestructura.csv
    try:
        df = pd.read_csv(output_dir / "tabla_infraestructura.csv")
        expected_cols = ["Concepto", "Valor"]
        if set(df.columns) == set(expected_cols) and len(df) == 9:
            print(f"  ✓ tabla_infraestructura.csv: {len(df)} conceptos")
            # Extraer datos o validación
            total_sockets = df[df["Concepto"] == "Total Tomas"]["Valor"].values
            if len(total_sockets) > 0:
                print(f"    → Total Tomas: {total_sockets[0]}")
            results["tabla_infraestructura.csv"] = "OK"
        else:
            print(f"  ✗ tabla_infraestructura.csv: Estructura incorrecta")
            results["tabla_infraestructura.csv"] = "ERROR"
    except Exception as e:
        print(f"  ✗ tabla_infraestructura.csv: {e}")
        results["tabla_infraestructura.csv"] = "ERROR"
    
    # tabla_escenarios_detallados.csv
    try:
        df = pd.read_csv(output_dir / "tabla_escenarios_detallados.csv")
        expected_cols = ["Escenario", "Penetración (pe)", "Factor Carga (fc)", 
                        "Cargadores (4 tomas)", "Total Tomas", "Energía Día (kWh)"]
        if len(df) == 4 and all(col in df.columns for col in ["Escenario"]):
            print(f"  ✓ tabla_escenarios_detallados.csv: {len(df)} escenarios")
            print(f"    → {', '.join(df['Escenario'].tolist())}")
            results["tabla_escenarios_detallados.csv"] = "OK"
        else:
            print(f"  ✗ tabla_escenarios_detallados.csv: Estructura incorrecta")
            results["tabla_escenarios_detallados.csv"] = "ERROR"
    except Exception as e:
        print(f"  ✗ tabla_escenarios_detallados.csv: {e}")
        results["tabla_escenarios_detallados.csv"] = "ERROR"
    
    # tabla_estadisticas_escenarios.csv
    try:
        df = pd.read_csv(output_dir / "tabla_estadisticas_escenarios.csv")
        expected_cols = ["Métrica", "Mínimo", "Máximo", "Promedio", "Mediana", "Desv_Std"]
        if set(df.columns) == set(expected_cols) and len(df) == 6:
            print(f"  ✓ tabla_estadisticas_escenarios.csv: {len(df)} métricas")
            results["tabla_estadisticas_escenarios.csv"] = "OK"
        else:
            print(f"  ✗ tabla_estadisticas_escenarios.csv: Estructura incorrecta")
            results["tabla_estadisticas_escenarios.csv"] = "ERROR"
    except Exception as e:
        print(f"  ✗ tabla_estadisticas_escenarios.csv: {e}")
        results["tabla_estadisticas_escenarios.csv"] = "ERROR"
    
    # tabla_escenario_recomendado.csv
    try:
        df = pd.read_csv(output_dir / "tabla_escenario_recomendado.csv")
        if "Periodo" in df.columns and len(df) == 3:
            print(f"  ✓ tabla_escenario_recomendado.csv: {len(df)} períodos")
            print(f"    → {', '.join(df['Periodo'].tolist())}")
            results["tabla_escenario_recomendado.csv"] = "OK"
        else:
            print(f"  ✗ tabla_escenario_recomendado.csv: Estructura incorrecta")
            results["tabla_escenario_recomendado.csv"] = "ERROR"
    except Exception as e:
        print(f"  ✗ tabla_escenario_recomendado.csv: {e}")
        results["tabla_escenario_recomendado.csv"] = "ERROR"
    
    # chargers_real_statistics.csv
    try:
        df = pd.read_csv(output_dir / "chargers_real_statistics.csv")
        expected_cols = ["socket_id", "mean_power_kw", "max_power_kw", "total_energy_kwh"]
        if set(df.columns) == set(expected_cols) and len(df) == 40:
            print(f"  ✓ chargers_real_statistics.csv: {len(df)} sockets")
            results["chargers_real_statistics.csv"] = "OK"
        else:
            print(f"  ✗ chargers_real_statistics.csv: Estructura incorrecta")
            results["chargers_real_statistics.csv"] = "ERROR"
    except Exception as e:
        print(f"  ✗ chargers_real_statistics.csv: {e}")
        results["chargers_real_statistics.csv"] = "ERROR"
    
    print()
    
    # 3. Verificar duplicidades
    print("3. VERIFICACIÓN DE DUPLICIDADES:")
    print("-" * 70)
    
    all_files = list(output_dir.glob("*.csv"))
    file_contents = {}
    duplicates = []
    
    for filepath in all_files:
        try:
            content = filepath.read_text(encoding='utf-8')
            content_hash = hash(content)
            
            if content_hash in file_contents:
                duplicates.append((filepath.name, file_contents[content_hash]))
                print(f"  ⚠ DUPLICADO: {filepath.name} ≈ {file_contents[content_hash].name}")
            else:
                file_contents[content_hash] = filepath
        except Exception as e:
            print(f"  ✗ Error procesando {filepath.name}: {e}")
    
    if not duplicates:
        print(f"  ✓ No hay archivos duplicados ({len(all_files)} archivos únicos)")
    
    print()
    
    # 4. Resumen
    print("4. RESUMEN:")
    print("-" * 70)
    
    success_count = sum(1 for v in results.values() if v == "OK")
    total_count = len(results)
    
    print(f"  Archivos validados: {success_count}/{total_count}")
    print(f"  Ubicación: {output_dir.resolve()}")
    print()
    
    if success_count == total_count and not duplicates:
        print("✓ VALIDACIÓN EXITOSA - Todos los archivos fueron generados correctamente")
        print("="*70)
        return True
    else:
        print("⚠ VALIDACIÓN CON ADVERTENCIAS")
        print("="*70)
        return False


if __name__ == "__main__":
    success = test_csv_generation()
    exit(0 if success else 1)
