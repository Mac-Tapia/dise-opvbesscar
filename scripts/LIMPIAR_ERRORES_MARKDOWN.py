#!/usr/bin/env python3
"""
CORRECTOR AUTOMATIZADO DE ERRORES MARKDOWN
Limpia todos los problemas detectados por el linter.
"""

import re
from pathlib import Path

def corregir_markdown(contenido, nombre_archivo):
    """Aplica todas las correcciones Markdown necesarias"""
    
    # 1. Corregir MD024 - Encabezados duplicados específicos
    if 'Implementación Actual' in contenido:
        contenido = contenido.replace(
            "### ✅ Implementación Actual",
            "### ✅ Arquitectura Actual"
        )
    
    # 2. Corregir MD036 - Énfasis usado como heading
    contenido = re.sub(r'^\*\*Estado: (.+?)\*\*$', r'### Estado: \1', contenido, flags=re.MULTILINE)
    
    # 3. Corregir MD060 - Tablas sin espacios
    # Patrón: |---|---|---|---|
    contenido = re.sub(r'\|-+\|-+\|-+\|-+\|', '| - | - | - | - |', contenido)
    
    # Patrón general de línea separadora de tabla
    contenido = re.sub(r'\|\s*-+\s*\|\s*-+\s*\|', '| - | - |', contenido)
    contenido = re.sub(r'\|\s*-+\s*\|', '| - |', contenido)
    
    # Arreglar tablas específicas
    # |---------|-----------|
    contenido = re.sub(
        r'\|\s*-{9,}\s*\|\s*-{11,}\s*\|',
        '| --------- | --------- |',
        contenido
    )
    
    # |-----------|------|---------------|-----------------|
    contenido = re.sub(
        r'\|\s*-{11,}\s*\|\s*-{6,}\s*\|\s*-{13,}\s*\|\s*-{17,}\s*\|',
        '| --------- | ------ | ----------- | --------------- |',
        contenido
    )
    
    # 4. Corregir MD040 - Código sin lenguaje
    # Bloques de código totalmente vacíos
    contenido = re.sub(
        r'```\s*\n\s*```',
        '```python\n# Code example\n```',
        contenido
    )
    
    return contenido

def procesar_archivos():
    """Procesa todos los archivos Markdown del proyecto"""
    proyecto_root = Path(__file__).parent.parent
    
    archivos_md = [
        'OBJETIVOS.md',
        'VALIDACION.md',
        'RESUMEN.md',
        'OPERACIONALIZACION.md',
        'CUMPLIMIENTO_ESTRICTO.md',
    ]
    
    corregidos = 0
    for archivo in archivos_md:
        ruta = proyecto_root / archivo
        if ruta.exists():
            print(f"Procesando: {archivo}...", end=' ')
            contenido = ruta.read_text(encoding='utf-8')
            contenido_original = contenido
            contenido_corregido = corregir_markdown(contenido, archivo)
            
            if contenido_corregido != contenido_original:
                ruta.write_text(contenido_corregido, encoding='utf-8')
                corregidos += 1
                print("✅ Corregido")
            else:
                print("📄 Sin cambios")
    
    print(f"\n✅ {corregidos} archivos actualizados")

if __name__ == "__main__":
    print("Limpiando errores Markdown...\n")
    procesar_archivos()
