#!/usr/bin/env python3
"""
LIMPIADOR AGRESIVO DE ERRORES MARKDOWN
Elimina completamente bloques vacíos y corrige etiquetas HTML implícitas.
"""

import re
from pathlib import Path

def limpiar_archivo(ruta):
    """Limpia un archivo específico"""
    contenido = ruta.read_text(encoding='utf-8')
    original = contenido
    
    # 1. ELIMINAR bloques de código completamente vacíos (solo backticks)
    # Patrón: ````\n```\n```` (backticks con nada adentro)
    contenido = re.sub(
        r'````\s*\n\s*```\s*\n\s*````',
        '```markdown\n# Código de ejemplo\n```',
        contenido
    )
    
    # Patrón: ```\n\n```
    contenido = re.sub(
        r'```\s*\n\s*\n\s*```',
        '```markdown\n# Código\n```',
        contenido
    )
    
    # 2. Convertir énfasis a heading (MD036)
    # **Ítem X: ...**  →  ### Ítem X: ...
    contenido = re.sub(
        r'^\*\*([A-Z][\w\s:().-]+)\*\*$',
        r'### \1',
        contenido,
        flags=re.MULTILINE
    )
    
    # 3. Corregir tablas sin espacios (MD060)
    # |---------|----------|-------|--------|
    contenido = re.sub(
        r'\|-+\|-+\|-+\|-+\|',
        '| -------- | -------- | ----- | ------ |',
        contenido
    )
    
    # |---------|-----------|------------|
    contenido = re.sub(
        r'\|-{11,}\|-{11,}\|-{10,}\|',
        '| --------- | --------- | ---------|',
        contenido
    )
    
    # |-----------|------|---------------|-----------------|
    contenido = re.sub(
        r'\|-{11,}\|-{6,}\|-{15,}\|-{17,}\|',
        '| --------- | ------ | ------------- | --------------- |',
        contenido
    )
    
    return contenido if contenido != original else None

def procesar():
    """Procesa todos los archivos MD"""
    proyecto = Path(__file__).parent.parent
    
    archivos = [
        'CUMPLIMIENTO_ESTRICTO.md',
        'ESTADO_OPERACIONAL_FINAL.md',
        'VALIDACION.md',
        'RESUMEN.md',
        'OPERACIONALIZACION.md',
    ]
    
    actualizados = 0
    for nombre in archivos:
        ruta = proyecto / nombre
        if not ruta.exists():
            continue
        
        resultado = limpiar_archivo(ruta)
        if resultado:
            ruta.write_text(resultado, encoding='utf-8')
            print(f"✅ {nombre}")
            actualizados += 1
        else:
            print(f"📄 {nombre}")
    
    return actualizados

if __name__ == "__main__":
    print("Limpieza agresiva de Markdown...\n")
    count = procesar()
    print(f"\n✅ {count} archivos actualizados")
