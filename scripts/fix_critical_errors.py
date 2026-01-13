#!/usr/bin/env python3
"""
Script para arreglar errores críticos de markdown en DOCUMENTACION_COMPLETA.md
Solo arregla:
- MD040: Code blocks sin language specified
- MD031: Code blocks sin líneas en blanco alrededor
- Mantiene todo lo demás intacto
"""

import re
from pathlib import Path

def fix_code_blocks(content):
    """Añade language tags y espacios en blanco a code blocks"""
    
    # Pattern: ```\n (fence sin language)
    # Lo reemplazamos con ```python\n
    
    lines = content.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Detectar fence de código sin language
        if line.strip().startswith('```') and not line.strip().endswith('```'):
            # Es un fence de apertura
            if len(line.strip()) == 3:  # Solo las comillas, sin language
                # Verificar contenido siguiente
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Inferir language por contenido
                    if next_line.startswith('#'):
                        result.append('```python')
                    elif next_line.startswith('//'):
                        result.append('```javascript')
                    elif next_line.startswith('--'):
                        result.append('```sql')
                    else:
                        result.append('```python')  # default
                    
                    # Asegurar línea en blanco anterior si no existe
                    if result and result[-1] != '':
                        result.insert(-1, '')
                else:
                    result.append(line)
            else:
                result.append(line)
        elif line.strip() == '```':
            # Fence de cierre
            result.append(line)
            # Asegurar línea en blanco posterior si no existe
            if i + 1 < len(lines) and lines[i + 1] != '':
                result.append('')
        else:
            result.append(line)
        
        i += 1
    
    return '\n'.join(result)

def main():
    doc_path = Path('d:\\diseñopvbesscar\\docs\\DOCUMENTACION_COMPLETA.md')
    
    print(f"Leyendo {doc_path}...")
    content = doc_path.read_text(encoding='utf-8')
    
    size_before = len(content)
    
    # Aplicar fixes
    content = fix_code_blocks(content)
    
    size_after = len(content)
    
    print(f"Tamaño antes: {size_before:,} bytes")
    print(f"Tamaño después: {size_after:,} bytes")
    
    # Guardar
    doc_path.write_text(content, encoding='utf-8')
    print(f"✓ Guardado en {doc_path}")

if __name__ == '__main__':
    main()
