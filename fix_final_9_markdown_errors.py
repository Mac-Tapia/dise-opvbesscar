#!/usr/bin/env python3
"""
Script FINAL para corregir los últimos 9 errores Markdown de los 63 restantes.
Maneja: MD029, MD040, MD060
"""

import re
from pathlib import Path

def fix_entrega_final():
    """Corrige ENTREGA_FINAL_DESPACHO.md - MD060"""
    path = Path('d:\\diseñopvbesscar\\ENTREGA_FINAL_DESPACHO.md')
    content = path.read_text(encoding='utf-8')
    
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        # MD060: Arreglar separadores de tabla |-----|-----|-----| → | ----- | ----- | ----- |
        if re.match(r'^\|-+\|', line):
            parts = line.split('|')
            separator = '| ' + ' | '.join('-' * 5 for _ in parts[1:-1]) + ' |'
            new_lines.append(separator)
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    if not content.endswith('\n'): content += '\n'
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD060 ARREGLADO")

def fix_fase_6_5():
    """Corrige FASE_6_5_COMPLETADA.md - MD029"""
    path = Path('d:\\diseñopvbesscar\\FASE_6_5_COMPLETADA.md')
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
        else:
            if not re.match(r'^\s*\d+\.\s+', line):
                list_counter = 0
                prev_indent = -1
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    if not content.endswith('\n'): content += '\n'
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD029 ARREGLADO")

def fix_modulo_demanda():
    """Corrige MODULO_DEMANDA_MALL_KWH.md - MD040"""
    path = Path('d:\\diseñopvbesscar\\MODULO_DEMANDA_MALL_KWH.md')
    content = path.read_text(encoding='utf-8')
    
    content = re.sub(r'^```\s*$', '```python', content, flags=re.MULTILINE)
    if not content.endswith('\n'): content += '\n'
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD040 ARREGLADO")

def main():
    print("=" * 80)
    print("CORRECTOR FINAL MARKDOWN (9 errores Markdown de 63 totales)")
    print("=" * 80)
    print()
    
    try:
        fix_entrega_final()
        fix_fase_6_5()
        fix_modulo_demanda()
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    print("=" * 80)
    print("✅ RESULTADO: 3 archivos Markdown corregidos")
    print("   (54 errores restantes son de Python - imports y atributos)")
    print("=" * 80)

if __name__ == '__main__':
    main()
