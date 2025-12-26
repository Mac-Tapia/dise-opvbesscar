#!/usr/bin/env python3
"""
LIMPIADOR FINAL DE MARKDOWN
Elimina puntuación de headings y bloques vacíos restantes
"""

import re
from pathlib import Path

def limpiar_puntuacion_headings(contenido):
    """Remueve puntuación final (: ; ...) de headings"""
    # ### Título: →  ### Título
    contenido = re.sub(
        r'^(#{1,6}\s+[^:]+):\s*$',
        r'\1',
        contenido,
        flags=re.MULTILINE
    )
    return contenido

def limpiar_bloques_vacios(contenido):
    """Elimina bloques vacíos y añade lenguaje"""
    # Patrón: ```` backticks vacíos ````
    contenido = re.sub(
        r'````\s*\n\s*```\s*\n\s*````',
        '```python\n# Ejemplo\n```',
        contenido
    )
    # Patrón: ``` vacío ```
    contenido = re.sub(
        r'^```\s*\n\s*\n\s*```$',
        '```python\n# Ejemplo\n```',
        contenido,
        flags=re.MULTILINE
    )
    return contenido

def procesar():
    """Procesa todos los archivos MD"""
    proyecto = Path(__file__).parent.parent
    
    archivos = [
        'OBJETIVOS.md',
        'VALIDACION.md',
        'RESUMEN.md',
        'OPERACIONALIZACION.md',
    ]
    
    actualizados = 0
    for nombre in archivos:
        ruta = proyecto / nombre
        if not ruta.exists():
            continue
        
        contenido = ruta.read_text(encoding='utf-8')
        original = contenido
        
        # Aplicar limpiezas
        contenido = limpiar_puntuacion_headings(contenido)
        contenido = limpiar_bloques_vacios(contenido)
        
        if contenido != original:
            ruta.write_text(contenido, encoding='utf-8')
            print(f"✅ {nombre}")
            actualizados += 1
        else:
            print(f"📄 {nombre}")
    
    return actualizados

if __name__ == "__main__":
    print("Limpieza final de Markdown...\n")
    count = procesar()
    print(f"\n✅ {count} archivos actualizados")
