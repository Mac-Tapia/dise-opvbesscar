#!/usr/bin/env python3
"""
Script para limpiar warnings de Python (imports no usados, variables no usadas)
Procesa archivos específicos que generan warnings
Genera reporte de cambios realizados
"""

import re
from pathlib import Path

# Diccionario de archivos a limpiar con sus reglas específicas
ARCHIVOS_A_LIMPIAR = {
    'verify_real_oe2_training.py': [
        {
            'descripcion': 'Remover línea de acceso a attribute zones (no disponible)',
            'buscar': r'    print\(f"  ✓ Zones: {len\(building\.zones\)}"\)\n',
            'reemplazar': ''
        },
        {
            'descripcion': 'Remover bucle sobre zones no disponible',
            'buscar': r'    for i, zone in enumerate\(building\.zones\[:5\]\):\n        print\(f"    Zone {i\+1}: {zone}"\)\n',
            'reemplazar': ''
        }
    ],
    'verify_mall_demand_integration.py': [
        {
            'descripcion': 'Remover import numpy no usado',
            'buscar': r'import numpy as np\n',
            'reemplazar': ''
        }
    ],
    'EVALUACION_METRICAS_COMPLETAS.py': [
        {
            'descripcion': 'Remover import datetime no usado',
            'buscar': r'from datetime import datetime\n',
            'reemplazar': ''
        },
        {
            'descripcion': 'Cambiar variable "info" por "_" (no usada)',
            'buscar': r'            obs, reward, terminated, truncated, info = env\.step\(action\)',
            'reemplazar': r'            obs, reward, terminated, truncated, _ = env.step(action)'
        }
    ],
    'EVALUACION_MODELOS_SIMPLE.py': [
        {
            'descripcion': 'Remover import datetime no usado',
            'buscar': r'from datetime import datetime\n',
            'reemplazar': ''
        }
    ],
    'EVALUACION_METRICAS_MODELOS.py': [
        {
            'descripcion': 'Remover import datetime no usado',
            'buscar': r'from datetime import datetime\n',
            'reemplazar': ''
        },
        {
            'descripcion': 'Cambiar variable "learning_rate" por "_"',
            'buscar': r'        learning_rate = model\.learning_rate',
            'reemplazar': r'        _ = model.learning_rate'
        },
        {
            'descripcion': 'Cambiar variable "agent_key" por "_" en loop 1',
            'buscar': r'    for agent_key, data in sorted\(all_results\.items\(\)\):\n        print\(f"\\n{agente",',
            'reemplazar': r'    for _, data in sorted(all_results.items()):\n        print(f"\n{agente",'
        }
    ],
    'REGENERAR_TODAS_GRAFICAS_REALES.py': [
        {
            'descripcion': 'Remover imports no usados (os, json, ZipFile, pickle, shutil, BaseCallback)',
            'buscar': r'import os\nimport json\n',
            'reemplazar': ''
        },
        {
            'descripcion': 'Cambiar "fig" por "_" en subplots (no usado)',
            'buscar': r'        fig, ax = plt\.subplots\(figsize=\(',
            'reemplazar': r'        _, ax = plt.subplots(figsize=('
        },
        {
            'descripcion': 'Cambiar "model_name" por "_" en loop',
            'buscar': r'    for model_name, model_data in models_data\.items\(\):',
            'reemplazar': r'    for _, model_data in models_data.items():'
        }
    ],
    'LIMPIAR_GRAFICAS_REGENERADAS.py': [
        {
            'descripcion': 'Remover import os no usado',
            'buscar': r'import os\n',
            'reemplazar': ''
        }
    ],
    'ANALIZAR_RAIZ.py': [
        {
            'descripcion': 'Remover import os no usado',
            'buscar': r'import os\n',
            'reemplazar': ''
        }
    ],
    'CORREGIR_ERRORES_MD060.py': [
        {
            'descripcion': 'Remover import re no usado',
            'buscar': r'import re\n',
            'reemplazar': ''
        }
    ],
    'INDICE_LIMPIEZA_RAIZ.md': [
        {
            'descripcion': 'Cambiar ### a ## en primera línea (MD001)',
            'buscar': r'### 📊 Resumen Ejecutivo',
            'reemplazar': r'## 📊 Resumen Ejecutivo'
        },
        {
            'descripcion': 'Cambiar bold a heading en Status Final',
            'buscar': r'\*\*Status Final: ✅ LIMPIEZA COMPLETADA\*\*',
            'reemplazar': r'### Status Final: ✅ LIMPIEZA COMPLETADA'
        },
        {
            'descripcion': 'Cambiar cursiva a heading en fecha',
            'buscar': r'\*Limpieza realizada: 2026-01-19\*',
            'reemplazar': r'### Limpieza realizada: 2026-01-19'
        }
    ]
}

def limpiar_archivo(filepath, reglas):
    """Limpia un archivo aplicando reglas de reemplazo"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        cambios = []
        
        for regla in reglas:
            patron = regla['buscar']
            reemplazo = regla['reemplazar']
            descripcion = regla['descripcion']
            
            nuevo_contenido = re.sub(patron, reemplazo, contenido)
            
            if nuevo_contenido != contenido:
                cambios.append(descripcion)
                contenido = nuevo_contenido
        
        if cambios:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(contenido)
            return True, cambios
        return False, []
    
    except Exception as e:
        return False, [f"ERROR: {str(e)}"]

def main():
    print("=" * 80)
    print("🔧 LIMPIAR WARNINGS DE PYTHON")
    print("=" * 80)
    print()
    
    raiz = Path('d:\\diseñopvbesscar')
    archivos_procesados = 0
    cambios_totales = 0
    
    for archivo_name, reglas in ARCHIVOS_A_LIMPIAR.items():
        filepath = raiz / archivo_name
        
        if not filepath.exists():
            print(f"⚠️  NO EXISTE: {archivo_name}")
            continue
        
        procesado, cambios = limpiar_archivo(filepath, reglas)
        
        if procesado:
            archivos_procesados += 1
            cambios_totales += len(cambios)
            print(f"✅ {archivo_name}")
            for cambio in cambios:
                print(f"   ├─ {cambio}")
        else:
            print(f"⏭️  SIN CAMBIOS: {archivo_name}")
    
    print()
    print("=" * 80)
    print(f"✅ RESUMEN: {archivos_procesados} archivos procesados, {cambios_totales} cambios aplicados")
    print("=" * 80)

if __name__ == '__main__':
    main()
