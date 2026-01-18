#!/usr/bin/env python3
"""
Script DEFINITIVO para corregir los 105 errores Markdown restantes.
Maneja: MD001, MD029, MD036, MD040, MD060
"""

import re
from pathlib import Path

def fix_all_files():
    """Aplica correcciones a todos los archivos con errores."""
    
    # ========================================================================
    # QUICKSTART_DESPACHO.md - MD001, MD036, MD040, MD060
    # ========================================================================
    path = Path('d:\\diseñopvbesscar\\QUICKSTART_DESPACHO.md')
    content = path.read_text(encoding='utf-8')
    content = content.replace('### Tiempo total: 10 minutos', '## Tiempo total: 10 minutos')
    content = re.sub(r'^```\s*$', '```bash', content, flags=re.MULTILINE)
    content = re.sub(r'^\|-+\|', lambda m: '| ' + ' | '.join('-' * 5 for _ in m.group(0).split('|')[1:-1]) + ' |', content, flags=re.MULTILINE)
    if not content.endswith('\n'): content += '\n'
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD001/MD036/MD040/MD060 ARREGLADOS")
    
    # ========================================================================
    # IMPLEMENTATION_COMPLETE.md - MD036, MD040
    # ========================================================================
    path = Path('d:\\diseñopvbesscar\\IMPLEMENTATION_COMPLETE.md')
    content = path.read_text(encoding='utf-8')
    content = re.sub(r'^\*\*Results:', '### Results:', content, flags=re.MULTILINE)
    content = re.sub(r'^\*\*Total Phase 7-8:', '### Total Phase 7-8:', content, flags=re.MULTILINE)
    content = re.sub(r'^```\s*$', '```bash', content, flags=re.MULTILINE)
    if not content.endswith('\n'): content += '\n'
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD036/MD040 ARREGLADOS")
    
    # ========================================================================
    # ENTREGA_FINAL_DESPACHO.md - MD029, MD036, MD040, MD060
    # ========================================================================
    path = Path('d:\\diseñopvbesscar\\ENTREGA_FINAL_DESPACHO.md')
    content = path.read_text(encoding='utf-8')
    
    # MD029: Fijar numeración
    lines = content.split('\n')
    new_lines = []
    list_counter = 0
    prev_indent = -1
    
    for line in lines:
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
    content = content.replace('**Status: ✅ COMPLETADO Y LISTO PARA PRODUCCIÓN**', 
                             '### Status: ✅ COMPLETADO Y LISTO PARA PRODUCCIÓN')
    content = re.sub(r'^```\s*$', '```yaml', content, flags=re.MULTILINE)
    content = re.sub(r'^\|-+\|', lambda m: '| ' + ' | '.join('-' * 5 for _ in m.group(0).split('|')[1:-1]) + ' |', content, flags=re.MULTILINE)
    if not content.endswith('\n'): content += '\n'
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD029/MD036/MD040/MD060 ARREGLADOS")
    
    # ========================================================================
    # CO2_REDUCTION_DIRECTA_INDIRECTA.md - MD040
    # ========================================================================
    path = Path('d:\\diseñopvbesscar\\CO2_REDUCTION_DIRECTA_INDIRECTA.md')
    content = path.read_text(encoding='utf-8')
    content = re.sub(r'^```\s*$', '```python', content, flags=re.MULTILINE)
    if not content.endswith('\n'): content += '\n'
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD040 ARREGLADO")
    
    # ========================================================================
    # INTEGRACION_CO2_EN_AGENTES.md - MD040
    # ========================================================================
    path = Path('d:\\diseñopvbesscar\\INTEGRACION_CO2_EN_AGENTES.md')
    content = path.read_text(encoding='utf-8')
    content = re.sub(r'^```\s*$', '```python', content, flags=re.MULTILINE)
    if not content.endswith('\n'): content += '\n'
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD040 ARREGLADO")
    
    # ========================================================================
    # FASE_6_5_COMPLETADA.md - MD036, MD040
    # ========================================================================
    path = Path('d:\\diseñopvbesscar\\FASE_6_5_COMPLETADA.md')
    content = path.read_text(encoding='utf-8')
    content = content.replace('**DIRECTO (Scope 2: Grid Import)**', 
                             '### DIRECTO (Scope 2: Grid Import)')
    content = content.replace('**INDIRECTO (Scope 1: BESS Efficiency)**', 
                             '### INDIRECTO (Scope 1: BESS Efficiency)')
    content = re.sub(r'^```\s*$', '```python', content, flags=re.MULTILINE)
    if not content.endswith('\n'): content += '\n'
    path.write_text(content, encoding='utf-8')
    print(f"✅ {path.name}: MD036/MD040 ARREGLADOS")

def main():
    print("=" * 80)
    print("CORRECTOR DEFINITIVO DE MARKDOWN (105 errores restantes)")
    print("=" * 80)
    print()
    
    try:
        fix_all_files()
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    print("=" * 80)
    print("✅ RESULTADO: 6 archivos procesados correctamente")
    print("=" * 80)

if __name__ == '__main__':
    main()
