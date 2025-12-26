#!/usr/bin/env python3
"""
LIMPIADOR DE BLOQUES DE CÓDIGO CON 4 BACKTICKS
Convierte ```` a ``` y añade lenguaje especificado
"""

import re
from pathlib import Path

def limpiar_backticks(contenido):
    """Convierte 4 backticks a 3 con lenguaje especificado"""
    
    # Patrón: ```` backticks exactos ````
    # Reemplaza con ``` markdown ``` 
    contenido = re.sub(
        r'````\s*\n(.*?)\n````',
        lambda m: f'```markdown\n{m.group(1).strip()}\n```',
        contenido,
        flags=re.DOTALL
    )
    
    # Patrón: bloques vacíos con 3 backticks sin lenguaje
    # ``` \n ``` → ```python\n# Ejemplo\n```
    contenido = re.sub(
        r'```\s*\n\s*```',
        '```python\n# Ejemplo\n```',
        contenido
    )
    
    return contenido

def procesar():
    """Procesa archivos específicos"""
    proyecto = Path(__file__).parent.parent
    
    archivos = [
        'VALIDACION.md',
        'RESUMEN.md',
        'OPERACIONALIZACION.md',
        'CUMPLIMIENTO_ESTRICTO.md',
    ]
    
    actualizados = 0
    for nombre in archivos:
        ruta = proyecto / nombre
        if not ruta.exists():
            continue
        
        contenido = ruta.read_text(encoding='utf-8')
        original = contenido
        
        contenido = limpiar_backticks(contenido)
        
        if contenido != original:
            ruta.write_text(contenido, encoding='utf-8')
            print(f"✅ {nombre}")
            actualizados += 1
        else:
            print(f"📄 {nombre}")
    
    return actualizados

if __name__ == "__main__":
    print("Limpieza de bloques con 4 backticks...\n")
    count = procesar()
    print(f"\n✅ {count} archivos actualizados")
