#!/usr/bin/env python3
"""
LIMPIADOR DE ESPACIOS EN MARKDOWN
Añade espacios en blanco alrededor de headings, lists y code blocks
"""

import re
from pathlib import Path

def limpiar_espacios(contenido):
    """Añade espacios en blanco alrededor de elementos"""
    
    # 1. Headings sin espacio arriba (MD022)
    # Excepto si ya hay espacio
    contenido = re.sub(
        r'([^\n])\n(#{1,6}\s+)',
        r'\1\n\n\2',
        contenido
    )
    
    # 2. Headings sin espacio abajo (MD022)
    contenido = re.sub(
        r'(#{1,6}\s+[^\n]+)\n([^\n])',
        r'\1\n\n\2',
        contenido
    )
    
    # 3. Lists sin espacio arriba (MD032)
    contenido = re.sub(
        r'([^\n])\n([-*+]\s+)',
        r'\1\n\n\2',
        contenido
    )
    
    # 4. Lists sin espacio abajo (MD032)
    contenido = re.sub(
        r'([-*+]\s+[^\n]+)\n([^\n-*+\s])',
        r'\1\n\n\2',
        contenido
    )
    
    # 5. Code blocks sin espacio (MD031)
    contenido = re.sub(
        r'([^\n])\n(```)',
        r'\1\n\n\2',
        contenido
    )
    contenido = re.sub(
        r'(```)\n([^\n])',
        r'\1\n\n\2',
        contenido
    )
    
    # 6. Eliminar espacios excesivos (máximo 2 newlines seguidos)
    contenido = re.sub(r'\n{4,}', '\n\n\n', contenido)
    
    return contenido

def procesar():
    """Procesa todos los archivos MD"""
    proyecto = Path(__file__).parent.parent
    
    archivos = [
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
        
        contenido = limpiar_espacios(contenido)
        
        if contenido != original:
            ruta.write_text(contenido, encoding='utf-8')
            print(f"✅ {nombre}")
            actualizados += 1
        else:
            print(f"📄 {nombre}")
    
    return actualizados

if __name__ == "__main__":
    print("Limpieza de espacios en blanco...\n")
    count = procesar()
    print(f"\n✅ {count} archivos actualizados")
