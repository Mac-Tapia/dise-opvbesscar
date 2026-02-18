"""
FIX SAC CALLBACKS v1 - SINCRONIZAR CON PPO/A2C
================================================

PROBLEMA RAIZ:
- SAC no está guardando COSTO, CO2, MOTOS/MOTOTAXIS en los CSVs
- Falta implementación de SACMetricsCallback._on_step() para registrar métricas

SOLUCIÓN:
- Agregar método a SACMetricsCallback que registre timeseries y trace
- Implementar guardado de CSVs al final del entrenamiento
- Asegurar TODAS las métricas se calculan durante step()
"""

import os
import re
from pathlib import Path

# Ruta del archivo SAC a modificar
SAC_TRAIN_PATH = Path('scripts/train/train_sac.py')

# Verificar que el archivo exista
if not SAC_TRAIN_PATH.exists():
    print(f"ERROR: {SAC_TRAIN_PATH} no encontrado")
    exit(1)

# Leer el archivo completo
with open(SAC_TRAIN_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

print("="*80)
print("DIAGNÓSTICO: Búsqueda de callbacks SAC incompletos")
print("="*80)

# 1. Verificar si SACMetricsCallback existe
if 'class SACMetricsCallback' in content:
    print("[OK] SACMetricsCallback encontrado")
    
    # Buscar si tiene _on_step que registre timeseries
    sac_metrics_match = re.search(
        r'class SACMetricsCallback.*?def _on_step\(self\).*?(?=\n    def |\nclass |\Z)',
        content,
        re.DOTALL
    )
    
    if sac_metrics_match:
        sac_metrics_code = sac_metrics_match.group(0)
        
        # Verificar si registra las métricas clave en timeseries_records
        if 'timeseries_records' in sac_metrics_code:
            print("[OK] timeseries_records está presente")
        else:
            print("[PROBLEMA] timeseries_records NO está siendo usado")
        
        # Verificar métricas específicas
        metrics_to_check = [
            ('electricity_cost', 'costo actual'),
            ('carbon_emissions_kg', 'emisiones CO2'),
            ('motos_charged', 'motos cargadas'),
            ('mototaxis_charged', 'mototaxis cargadas'),
        ]
        
        for metric, description in metrics_to_check:
            if metric in sac_metrics_code:
                print(f"[OK] {metric} ({description}) registrado")
            else:
                print(f"[FALTA] {metric} ({description}) NO registrado")
else:
    print("[FALTA] SACMetricsCallback no encontrado")

# 2. Verificar si hay guardado final de CSVs
if 'timeseries_records' in content and 'to_csv' in content:
    # Buscar guardado de timeseries_sac.csv
    if 'timeseries_sac.csv' in content:
        print("[OK] timeseries_sac.csv se guarda al final")
    else:
        print("[FALTA] timeseries_sac.csv NO se guarda")
else:
    print("[FALTA] Sistema de guardado de timeseries no implementado")

print("\n" + "="*80)
print("RESUMEN: SAC necesita:")
print("="*80)
print("1. Agregar registro de COST en timeseries (_on_step)")
print("2. Agregar registro de CO2 en timeseries (_on_step)")
print("3. Agregar registro de MOTOS/MOTOTAXIS en timeseries (_on_step)")
print("4. Implementar guardado final de CSVs (timeseries_sac.csv, trace_sac.csv)")
print("5. Sincronizar columnas con PPO (actualmente PPO=33 cols, SAC=8 cols)")
print()
