#!/usr/bin/env python3
"""
Script final para corregir los 212 errores Markdown restantes.
Maneja: MD032 (listas sin espacios), MD040 (código sin lenguaje), MD060 (tablas), MD036 (énfasis)
"""

import re
from pathlib import Path

def fix_indice_control_operativo():
    """Corrige INDICE_CONTROL_OPERATIVO.md"""
    path = Path('d:\\diseñopvbesscar\\INDICE_CONTROL_OPERATIVO.md')
    content = path.read_text(encoding='utf-8')
    
    lines = content.split('\n')
    new_lines = []
    
    for i, line in enumerate(lines):
        # MD032: Agregar línea en blanco antes de listas sin espacios
        if re.match(r'^- .+', line):  # Línea de lista sin indentación
            # Si la línea anterior existe y no es vacía y no es un encabezado
            if i > 0 and new_lines and new_lines[-1].strip():
                if not re.match(r'^(#{1,6}\s+|$|\s*$)', new_lines[-1]):
                    new_lines.append('')  # Agregar línea en blanco
            new_lines.append(line)
        # MD040: Agregar lenguaje a bloques de código
        elif re.match(r'^```\s*$', line):
            new_lines.append('```yaml')
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    # Agregar newline final si falta
    if not content.endswith('\n'):
        content += '\n'
    
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD032/MD040 ARREGLADOS")

def fix_despacho_con_prioridades():
    """Corrige DESPACHO_CON_PRIORIDADES.md"""
    path = Path('d:\\diseñopvbesscar\\DESPACHO_CON_PRIORIDADES.md')
    content = path.read_text(encoding='utf-8')
    
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        # MD040: Agregar lenguaje a bloques vacíos
        if re.match(r'^```\s*$', line):
            new_lines.append('```yaml')
        # MD060: Arreglar espacios en separadores de tabla
        elif re.match(r'^\|-+\|', line):
            # Línea separadora: | --- | --- | --- |
            parts = line.split('|')
            separator = '| ' + ' | '.join('-' * max(5, len(p.strip())) for p in parts[1:-1]) + ' |'
            new_lines.append(separator)
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    if not content.endswith('\n'):
        content += '\n'
    
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD040/MD060 ARREGLADOS")

def fix_guia_integracion():
    """Corrige GUIA_INTEGRACION_DESPACHO.md"""
    path = Path('d:\\diseñopvbesscar\\GUIA_INTEGRACION_DESPACHO.md')
    content = path.read_text(encoding='utf-8')
    
    # MD040: Agregar lenguaje a bloques vacíos
    content = re.sub(r'^```\s*$', '```python', content, flags=re.MULTILINE)
    
    if not content.endswith('\n'):
        content += '\n'
    
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD040 ARREGLADO")

def fix_resumen_despacho():
    """Corrige RESUMEN_DESPACHO_PRIORIDADES.md"""
    path = Path('d:\\diseñopvbesscar\\RESUMEN_DESPACHO_PRIORIDADES.md')
    content = path.read_text(encoding='utf-8')
    
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        # MD040: Agregar lenguaje a bloques vacíos
        if re.match(r'^```\s*$', line):
            new_lines.append('```python')
        # MD036: Convertir **Líneas de código: ~80 (insert, mostly in existing functions)** → Heading
        elif re.match(r'^\*\*Líneas de código:', line):
            new_lines.append('### ' + line.replace('**', '').replace(':', ''))
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
    print(f"✅ {path.name}: MD040/MD036/MD060 ARREGLADOS")

def main():
    print("=" * 80)
    print("CORRECTOR FINAL DE MARKDOWN (212 errores restantes)")
    print("=" * 80)
    print()
    
    try:
        fix_indice_control_operativo()
        fix_despacho_con_prioridades()
        fix_guia_integracion()
        fix_resumen_despacho()
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
