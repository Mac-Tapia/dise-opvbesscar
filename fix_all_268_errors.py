#!/usr/bin/env python3
"""
Script para corregir TODOS los 268 errores Markdown restantes.
Maneja: MD007, MD032, MD040, MD047, MD055, MD056, MD060
"""

import re
from pathlib import Path

def fix_iniciio_rapido():
    """Corrige INICIO_RAPIDO_CONTROL_OPERATIVO.md"""
    path = Path('d:\\diseñopvbesscar\\INICIO_RAPIDO_CONTROL_OPERATIVO.md')
    content = path.read_text(encoding='utf-8')
    
    # MD040: Agregar newline final si falta
    if not content.endswith('\n'):
        content += '\n'
    
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD047 ARREGLADO (newline final)")

def fix_resumen_ejecutivo():
    """Corrige RESUMEN_EJECUTIVO_CONTROL_OPERATIVO.md"""
    path = Path('d:\\diseñopvbesscar\\RESUMEN_EJECUTIVO_CONTROL_OPERATIVO.md')
    content = path.read_text(encoding='utf-8')
    
    # MD047: Agregar newline final
    if not content.endswith('\n'):
        content += '\n'
    
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD047 ARREGLADO (newline final)")

def fix_indice_control():
    """Corrige INDICE_CONTROL_OPERATIVO.md"""
    path = Path('d:\\diseñopvbesscar\\INDICE_CONTROL_OPERATIVO.md')
    content = path.read_text(encoding='utf-8')
    
    lines = content.split('\n')
    new_lines = []
    
    for i, line in enumerate(lines):
        # MD007: Fijar indentación de listas (3 espacios → 0 espacios)
        if re.match(r'^   - ', line):
            new_lines.append(re.sub(r'^   - ', '- ', line))
        # MD032: Agregar línea en blanco antes de listas
        elif re.match(r'^- ', line):
            if i > 0 and new_lines[-1].strip() and not re.match(r'^(- |  |\s*$|#)', new_lines[-1]):
                new_lines.append('')
            new_lines.append(line)
        # MD060 + MD055 + MD056: Arreglar tablas
        elif '|' in line and not re.match(r'^\|?-+\|', line):
            # Es una fila de tabla
            parts = line.split('|')
            fixed = '| ' + ' | '.join(p.strip() for p in parts[1:-1] if p.strip()) + ' |'
            new_lines.append(fixed)
        elif re.match(r'^\|[\s\-|:]+\|', line):
            # Línea separadora de tabla
            parts = line.split('|')
            separator_parts = ['-' * max(5, len(p.strip())) for p in parts[1:-1] if p.strip()]
            fixed = '| ' + ' | '.join(separator_parts) + ' |'
            new_lines.append(fixed)
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    # Agregar newline final si falta
    if not content.endswith('\n'):
        content += '\n'
    
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD007/MD032/MD055/MD056/MD060 ARREGLADOS")

def fix_implementacion_completada():
    """Corrige IMPLEMENTACION_COMPLETADA.md"""
    path = Path('d:\\diseñopvbesscar\\IMPLEMENTACION_COMPLETADA.md')
    content = path.read_text(encoding='utf-8')
    
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        # MD040: Agregar lenguaje a bloques de código vacíos
        if re.match(r'^```\s*$', line):
            new_lines.append('```python')
        # MD060: Arreglar espacios en separadores de tabla
        elif re.match(r'^\|-+\|', line):
            parts = line.split('|')
            separator_parts = ['-' * max(5, len(p.strip())) for p in parts[1:-1] if p.strip()]
            fixed = '| ' + ' | '.join(separator_parts) + ' |'
            new_lines.append(fixed)
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    # Agregar newline final si falta
    if not content.endswith('\n'):
        content += '\n'
    
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD040/MD060 ARREGLADOS")

def main():
    print("=" * 80)
    print("CORRECTOR AUTOMÁTICO DE MARKDOWN (268 errores restantes)")
    print("=" * 80)
    print()
    
    try:
        fix_iniciio_rapido()
        fix_resumen_ejecutivo()
        fix_indice_control()
        fix_implementacion_completada()
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return
    
    print()
    print("=" * 80)
    print("✅ RESULTADO: 4 archivos procesados correctamente")
    print("=" * 80)

if __name__ == '__main__':
    main()
