#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IMPLEMENTAR INTEGRACION DATA_LOADER EN AGENTES (SAC, PPO, A2C)

Este script modifica automáticamente los agentes para que usen el data_loader
centralizado en lugar de cargar datos manualmente.

Cambios:
1. Agregar imports de data_loader
2. Usar rebuild_oe2_datasets_complete() en load_datasets_from_processed()
3. Reemplazar constantes hardcoded con imports de data_loader
"""
from __future__ import annotations

import re
from pathlib import Path

def integrate_data_loader_imports(filepath: str) -> tuple[int, str]:
    """Agrega imports de data_loader al inicio del archivo."""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Encontrar donde están los imports de reward functions
    reward_import_pattern = r'(from dataset_builder_citylearn\.rewards import \((?:[^)]+)\))'
    match = re.search(reward_import_pattern, content, re.MULTILINE | re.DOTALL)
    
    if not match:
        print(f"❌ No se encontró patrón de imports de rewards en {filepath}")
        return 0, content
    
    insert_pos = match.end()
    
    # Nuevo import a agregar
    data_loader_import = """

# Data loader v5.8 - Centralizado con validación automática y fallbacks
from dataset_builder_citylearn.data_loader import (
    rebuild_oe2_datasets_complete,
    load_citylearn_dataset,
    BESS_CAPACITY_KWH,      # Constante centralizada (2,000 kWh verificado)
    BESS_MAX_POWER_KW,      # 400 kW
    N_CHARGERS,             # 19 chargers
    TOTAL_SOCKETS,          # 38 sockets
    SOLAR_PV_KWP,           # 4,050 kWp
    CO2_FACTOR_GRID_KG_PER_KWH,  # 0.4521 kg CO2/kWh
    CO2_FACTOR_EV_KG_PER_KWH,    # 2.146 kg CO2/kWh
    OE2ValidationError,
)"""
    
    # Verificar si ya existe el import
    if 'from dataset_builder_citylearn.data_loader import' in content:
        print(f"⚠️  Ya tiene imports de data_loader: {filepath}")
        return 0, content
    
    # Insertar el import
    new_content = content[:insert_pos] + data_loader_import + content[insert_pos:]
    
    print(f"✅ Agregados imports de data_loader en {filepath}")
    return 1, new_content


def integrate_constants(filepath: str, content: str) -> tuple[int, str]:
    """Reemplaza constantes hardcoded con imports de data_loader."""
    
    replacements = [
        # BESS Capacity
        (r'BESS_CAPACITY_KWH\s*[:=]\s*float\s*=\s*[\d.]+\s*(?:#[^\n]*)?',
         '# BESS_CAPACITY_KWH importado de data_loader (2,000 kWh verificado)'),
        
        # BESS Power
        (r'BESS_MAX_POWER_KW\s*[:=]\s*float\s*=\s*[\d.]+\s*(?:#[^\n]*)?',
         '# BESS_MAX_POWER_KW importado de data_loader (400 kW)'),
        
        # Solar Max
        (r'SOLAR_MAX_KW\s*[:=]\s*float\s*=\s*[\d.]+\s*(?:#[^\n]*)?',
         '# SOLAR_MAX_KW reemplazado con SOLAR_PV_KWP (4,050 kWp)'),
    ]
    
    modified = 0
    for pattern, replacement in replacements:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            modified += 1
    
    if modified > 0:
        print(f"✅ Reemplazadas {modified} constantes hardcoded en {filepath}")
    
    return modified, content


def integrate_load_function(filepath: str, content: str) -> tuple[int, str]:
    """Reemplaza load_datasets_from_processed() con versión usando data_loader."""
    
    # Encontrar la función
    pattern = r'def load_datasets_from_processed\(\):.*?(?=\n    def |\n# .*?\n|$)'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print(f"❌ No se encontró load_datasets_from_processed() en {filepath}")
        return 0, content
    
    # Nueva función simplificada
    new_function = '''def load_datasets_from_processed():
    """Cargar datasets OE2 usando data_loader centralizado con validación automática.
    
    Esta función usa rebuild_oe2_datasets_complete() que:
    - Carga Solar, BESS, Chargers, Mall demand desde rutas OE2
    - Valida automáticamente: 8,760 horas, capacidad BESS, etc.
    - Usa fallbacks automáticos si archivos en rutas predeterminadas no existen
    - Retorna datos validados en formato estándar
    
    Returns:
        Tuple con arrays: (solar_kw, chargers_kw, mall_kw, bess_soc, ...)
    """
    print('[CARGA DE DATOS] Usando data_loader centralizado v5.8')
    print('-' * 80)
    
    try:
        # Cargar todos los datasets OE2 con validación automática
        datasets = rebuild_oe2_datasets_complete()
        
        solar_df = datasets['solar'].df
        bess_df = datasets['bess'].df
        chargers_df = datasets['chargers'].df
        demand_df = datasets['demand'].df
        
        print(f'✅ Datasets cargados desde data_loader:')
        print(f'   • Solar: {len(solar_df)} horas, {datasets["solar"].mean_kw:.1f} kW promedio')
        print(f'   • BESS: {len(bess_df)} horas, {datasets["bess"].capacity_kwh:.0f} kWh capacidad')
        print(f'   • Chargers: {len(chargers_df)} horas, {datasets["chargers"].total_sockets} sockets')
        print(f'   • Demand: {len(demand_df)} horas, {datasets["demand"].mall_mean_kw:.1f} kW mall')
        print()
        
        # RESTO DEL CODIGO (igual que antes)
        # Aquí van las líneas que extraen columnas del dataset
        # Esto es específico para cada agente, así que dejamos un placeholder
        return solar_df, bess_df, chargers_df, demand_df
        
    except OE2ValidationError as e:
        print(f'❌ ERROR de validación OE2: {e}')
        raise
'''
    
    content = content[:match.start()] + new_function + content[match.end():]
    
    print(f"✅ Reemplazada función load_datasets_from_processed() en {filepath}")
    return 1, content


def main():
    print("=" * 100)
    print("INTEGRACION: AGENTES (SAC, PPO, A2C) → DATA_LOADER")
    print("=" * 100)
    print()
    
    agentes_files = {
        'SAC': 'scripts/train/train_sac.py',
        'PPO': 'scripts/train/train_ppo.py',
        'A2C': 'scripts/train/train_a2c.py',
    }
    
    total_changes = 0
    
    for agent_name, filepath in agentes_files.items():
        print(f"\n[{agent_name}] {filepath}")
        print("-" * 100)
        
        p = Path(filepath)
        if not p.exists():
            print(f"❌ ARCHIVO NO ENCONTRADO")
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        content = original_content
        
        # PASO 1: Agregar imports
        changes_1, content = integrate_data_loader_imports(filepath)
        total_changes += changes_1
        
        # PASO 2: Reemplazar constantes
        changes_2, content = integrate_constants(filepath, content)
        total_changes += changes_2
        
        # PASO 3: Actualizar función load_datasets_from_processed()
        # (Este paso requiere análisis más cuidadoso de la estructura específica)
        
        # Solo guardar si hay cambios
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"\n✅ GUARDADOS CAMBIOS en {filepath}")
        else:
            print(f"\nℹ️  Sin cambios significativos en {filepath}")
    
    # Resumen
    print("\n" + "=" * 100)
    print("RESUMEN DE CAMBIOS")
    print("=" * 100)
    print(f"\n✅ Total de cambios realizados: {total_changes}")
    print(f"\nTareas completadas:")
    print(f"  1. ✅ Imports de data_loader agregados")
    print(f"  2. ✅ Constantes reemplazadas (BESS, Solar, etc.)")
    print(f"  3. ℹ️  Función load_datasets_from_processed() - REVISAR MANUALMENTE")
    print(f"\nPRÓXIMO PASO:")
    print(f"  Revisa manualmente los agentes para verificar que la función")
    print(f"  load_datasets_from_processed() integre correctamente la lógica")
    print(f"  específica de cada agente con el nuevo data_loader.")

if __name__ == '__main__':
    main()
