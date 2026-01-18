#!/usr/bin/env python3
"""
Script ULTRAFINAL para corregir los 164 errores Markdown restantes.
Maneja: MD029 (numeración), MD040 (código), MD060 (tablas), MD036 (énfasis)
"""

import re
from pathlib import Path

def fix_despacho_prioridades():
    """Corrige DESPACHO_CON_PRIORIDADES.md - MD029, MD036"""
    path = Path('d:\\diseñopvbesscar\\DESPACHO_CON_PRIORIDADES.md')
    content = path.read_text(encoding='utf-8')
    
    lines = content.split('\n')
    new_lines = []
    list_counter = 0
    prev_indent = -1
    
    for line in lines:
        # MD029: Fijar numeración de listas ordenadas
        match = re.match(r'^(\s*)\d+\.\s+(.*)$', line)
        if match:
            indent = len(match.group(1))
            text = match.group(2)
            
            if indent != prev_indent:
                list_counter = 1
                prev_indent = indent
            else:
                list_counter += 1
            
            new_lines.append(f"{match.group(1)}{list_counter}. {text}")
        else:
            if not re.match(r'^\s*\d+\.\s+', line):
                list_counter = 0
                prev_indent = -1
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    if not content.endswith('\n'):
        content += '\n'
    
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD029 ARREGLADO")

def fix_indice_maestro():
    """Corrige INDICE_MAESTRO_DESPACHO.md - MD029, MD040, MD036, MD060"""
    path = Path('d:\\diseñopvbesscar\\INDICE_MAESTRO_DESPACHO.md')
    content = path.read_text(encoding='utf-8')
    
    lines = content.split('\n')
    new_lines = []
    list_counter = 0
    prev_indent = -1
    
    for line in lines:
        # MD029: Fijar numeración
        match = re.match(r'^(\s*)\d+\.\s+(.*)$', line)
        if match:
            indent = len(match.group(1))
            text = match.group(2)
            
            if indent != prev_indent:
                list_counter = 1
                prev_indent = indent
            else:
                list_counter += 1
            
            new_lines.append(f"{match.group(1)}{list_counter}. {text}")
        # MD040: Agregar lenguaje a bloques vacíos
        elif re.match(r'^```\s*$', line):
            new_lines.append('```python')
        # MD036: Convertir **Total proyecto: ~20-22 h** → ### Total proyecto: ~20-22 h
        elif re.match(r'^\*\*Total proyecto:', line):
            new_lines.append('### ' + line.replace('**', ''))
        # MD060: Arreglar separadores de tabla
        elif re.match(r'^\|-+\|', line):
            parts = line.split('|')
            separator = '| ' + ' | '.join('-' * max(5, len(p.strip())) for p in parts[1:-1]) + ' |'
            new_lines.append(separator)
        else:
            if not re.match(r'^\s*\d+\.\s+', line):
                list_counter = 0
                prev_indent = -1
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    if not content.endswith('\n'):
        content += '\n'
    
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD029/MD040/MD036/MD060 ARREGLADOS")

def fix_quickstart():
    """Corrige QUICKSTART_DESPACHO.md - MD036, MD040, MD060"""
    path = Path('d:\\diseñopvbesscar\\QUICKSTART_DESPACHO.md')
    content = path.read_text(encoding='utf-8')
    
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        # MD036: Convertir **Tiempo total: 10 minutos** → ### Tiempo total: 10 minutos
        if re.match(r'^\*\*Tiempo total:', line):
            new_lines.append('### ' + line.replace('**', ''))
        # MD040: Agregar lenguaje a bloques vacíos
        elif re.match(r'^```\s*$', line):
            new_lines.append('```bash')
        # MD060: Arreglar separadores de tabla
        elif re.match(r'^\|-+\|', line):
            parts = line.split('|')
            separator = '| ' + ' | '.join('-' * max(5, len(p.strip())) for p in parts[1:-1]) + ' |'
            new_lines.append(separator)
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    if not content.endswith('\n'):
        content += '\n'
    
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD036/MD040/MD060 ARREGLADOS")

def fix_implementation_complete():
    """Corrige IMPLEMENTATION_COMPLETE.md - MD036, MD040"""
    path = Path('d:\\diseñopvbesscar\\IMPLEMENTATION_COMPLETE.md')
    content = path.read_text(encoding='utf-8')
    
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        # MD036: Convertir **Results: ✅ 13/13 PASSED** → ### Results: ✅ 13/13 PASSED
        if re.match(r'^\*\*Results:', line):
            new_lines.append('### ' + line.replace('**', ''))
        # MD040: Agregar lenguaje a bloques vacíos
        elif re.match(r'^```\s*$', line):
            new_lines.append('```bash')
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    if not content.endswith('\n'):
        content += '\n'
    
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD036/MD040 ARREGLADOS")

def main():
    print("=" * 80)
    print("CORRECTOR ULTRAFINAL DE MARKDOWN (164 errores restantes)")
    print("=" * 80)
    print()
    
    try:
        fix_despacho_prioridades()
        fix_indice_maestro()
        fix_quickstart()
        fix_implementation_complete()
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    print("=" * 80)
    print("✅ RESULTADO: 4 archivos procesados correctamente")
    print("=" * 80)

if __name__ == '__main__':
    main()
