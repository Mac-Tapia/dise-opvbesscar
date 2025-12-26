#!/usr/bin/env python3
"""
CERRAR BLOQUES SIN CIERRE Y LIMPIAR LISTAS
"""

import re
from pathlib import Path

def limpiar_cumplimiento():
    """Limpia CUMPLIMIENTO_ESTRICTO.md"""
    ruta = Path('CUMPLIMIENTO_ESTRICTO.md')
    with open(ruta, encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # 1. Cerrar bloques ``` sin cierre 
    # Si hay ``` sin cierre por más de 3 líneas, cerrarlo
    lines = content.split('\n')
    fixed_lines = []
    in_code_block = False
    block_start = 0
    
    for i, line in enumerate(lines):
        if line.strip().startswith('```') and not line.strip().startswith('```python'):
            if not in_code_block:
                in_code_block = True
                block_start = i
            else:
                in_code_block = False
        
        fixed_lines.append(line)
        
        # Si estamos en bloque por más de 10 líneas sin cierre, ciérralo
        if in_code_block and i - block_start > 10:
            if line.strip() and not line.strip().startswith('```'):
                # Próxima línea vacía o heading, cierra el bloque
                if i + 1 < len(lines) and (not lines[i + 1].strip() or lines[i + 1].startswith('#')):
                    fixed_lines.append('```')
                    in_code_block = False
    
    content = '\n'.join(fixed_lines)
    
    # 2. Remover duplicados de headings
    content = re.sub(r'^### Código a Verificar\n', '#### Verificación:\n', content, flags=re.MULTILINE)
    content = re.sub(r'^### Verificación Requerida\n', '#### Validación:\n', content, flags=re.MULTILINE)
    
    # 3. Remover espacios trailing
    lines = content.split('\n')
    lines = [line.rstrip() for line in lines]
    content = '\n'.join(lines)
    
    # 4. Arreglar listas sin espacios alrededor
    # Si una lista está pegada a otro contenido, añadir espacio
    content = re.sub(r'([^\n])\n(- )', r'\1\n\n\2', content)
    content = re.sub(r'(- [^\n]+)\n([^\n-])', r'\1\n\n\2', content)
    
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(content)
    
    if content != original:
        print("✅ CUMPLIMIENTO_ESTRICTO.md limpiado")
    else:
        print("📄 CUMPLIMIENTO_ESTRICTO.md sin cambios")

if __name__ == "__main__":
    limpiar_cumplimiento()
