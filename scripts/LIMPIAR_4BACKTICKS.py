#!/usr/bin/env python3
"""
ELIMINAR 4 BACKTICKS Y REEMPLAZAR CON 3
"""

import re
from pathlib import Path

def limpiar_4backticks(ruta):
    """Reemplaza ```` con ```"""
    with open(ruta, encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Reemplazar 4 backticks con 3
    content = content.replace('````', '```')
    
    # Reemplazar puntuación al final de headings (#### Título: → #### Título)
    content = re.sub(r'^(#{1,6}\s+[^:\n]+):\s*$', r'\1', content, flags=re.MULTILINE)
    
    # Reemplazar indentación de 2 espacios en listas con 0
    content = re.sub(r'^  (-|\*|\+) ', r'\1 ', content, flags=re.MULTILINE)
    
    if content != original:
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    proyecto = Path.cwd()
    archivos = [
        'OBJETIVOS.md',
        'VALIDACION.md',
        'RESUMEN.md',
        'OPERACIONALIZACION.md',
        'CUMPLIMIENTO_ESTRICTO.md',
    ]
    
    actualizados = 0
    for nombre in archivos:
        ruta = proyecto / nombre
        if ruta.exists() and limpiar_4backticks(ruta):
            print(f"✅ {nombre}")
            actualizados += 1
        elif ruta.exists():
            print(f"📄 {nombre}")
    
    print(f"\nTotal: {actualizados} archivos actualizados")

if __name__ == "__main__":
    main()
