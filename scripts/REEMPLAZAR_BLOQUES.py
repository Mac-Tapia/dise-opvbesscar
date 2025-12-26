#!/usr/bin/env python3
"""
REEMPLAZAR BLOQUES SIN LENGUAJE CON MARKDOWN
"""

import re
from pathlib import Path

def reemplazar_bloques(ruta):
    """Reemplaza bloques ``` sin lenguaje con ```markdown"""
    with open(ruta, encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Patrón: ``` seguido de newline directo, sin lenguaje (captura el siguiente contenido hasta el cierre)
    # Esto busca bloques que abren sin lenguaje
    content = re.sub(
        r'```\n(?![\w-])',  # triple backtick + newline, no seguido de lenguaje
        '```markdown\n',
        content
    )
    
    # Patrón alternativo: ``` en línea que cierra abruptamente
    content = re.sub(
        r'```\s*\n\s*\n```',  # backticks, newline, espacio/newline, backticks
        '```markdown\n# Código de ejemplo\n```',
        content
    )
    
    if content != original:
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    proyecto = Path.cwd()
    archivos = [
        'VALIDACION.md',
        'RESUMEN.md',
        'OPERACIONALIZACION.md',
        'CUMPLIMIENTO_ESTRICTO.md',
    ]
    
    for nombre in archivos:
        ruta = proyecto / nombre
        if ruta.exists():
            if reemplazar_bloques(ruta):
                print(f"✅ {nombre}")
            else:
                print(f"📄 {nombre}")

if __name__ == "__main__":
    main()
