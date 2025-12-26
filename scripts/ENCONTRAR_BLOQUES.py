#!/usr/bin/env python3
"""
IDENTIFICADOR Y REEMPLAZO DE BLOQUES VACÍOS
Encuentra todos los bloques ``` \n ``` y los reemplaza con contenido
"""

import re
from pathlib import Path

def encontrar_bloques_vacios(contenido):
    """Encuentra bloques vacíos exactos"""
    # Busca ``` seguido de newlines/espacios y luego ```
    patron = r'```\s*[\r\n]+\s*[\r\n]*\s*```'
    bloques = re.finditer(patron, contenido)
    return list(bloques)

def procesar():
    """Procesa archivos"""
    proyecto = Path(__file__).parent.parent
    
    archivos = [
        'VALIDACION.md',
        'RESUMEN.md',
        'OPERACIONALIZACION.md',
        'CUMPLIMIENTO_ESTRICTO.md',
    ]
    
    for nombre in archivos:
        ruta = proyecto / nombre
        if not ruta.exists():
            continue
        
        contenido = ruta.read_text(encoding='utf-8')
        bloques = encontrar_bloques_vacios(contenido)
        
        print(f"\n{nombre}: {len(bloques)} bloques vacíos encontrados")
        for i, bloque in enumerate(bloques):
            pos_start = bloque.start()
            # Encontrar contexto alrededor
            linea_start = contenido.rfind('\n', 0, pos_start) + 1
            linea_end = contenido.find('\n', bloque.end())
            
            contexto_before = contenido[max(0, linea_start-100):linea_start].split('\n')[-2:]
            contexto_after = contenido[bloque.end():min(len(contenido), bloque.end()+100)].split('\n')[0:2]
            
            print(f"  Bloque {i+1}:")
            print(f"    Antes: {contexto_before[-1][:50]}...")
            print(f"    Bloque: {repr(bloque.group()[:30])}...")
            print(f"    Después: {contexto_after[0][:50]}...")

if __name__ == "__main__":
    procesar()
