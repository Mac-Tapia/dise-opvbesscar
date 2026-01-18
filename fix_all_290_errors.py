#!/usr/bin/env python3
"""
Script para corregir todos los 290 errores Markdown restantes.
Maneja: MD040, MD029, MD060, MD022, MD037
"""

import re
from pathlib import Path

def fix_file(filepath):
    """Procesa un archivo para corregir todos los errores Markdown."""
    path = Path(filepath)
    if not path.exists():
        print(f"❌ {path.name}: NO ENCONTRADO")
        return False
    
    content = path.read_text(encoding='utf-8')
    original = content
    
    # ============================================================================
    # FIX 1: MD040 - Fenced code blocks without language specification
    # ============================================================================
    # Busca bloques de código sin lenguaje: ``` → ```python (por defecto)
    content = re.sub(
        r'^```\s*$',
        '```python',
        content,
        flags=re.MULTILINE
    )
    
    # ============================================================================
    # FIX 2: MD029 - Ordered list item prefix (numbering)
    # ============================================================================
    # Reemplaza numeración incorrecta con secuencia 1, 2, 3...
    lines = content.split('\n')
    new_lines = []
    list_counter = 0
    prev_indent = -1
    
    for line in lines:
        # Detecta líneas de lista ordenada
        match = re.match(r'^(\s*)\d+\.\s+(.*)$', line)
        if match:
            indent = len(match.group(1))
            text = match.group(2)
            
            # Reinicia el contador si cambia la indentación
            if indent != prev_indent:
                list_counter = 1
                prev_indent = indent
            else:
                list_counter += 1
            
            new_lines.append(f"{match.group(1)}{list_counter}. {text}")
        else:
            # No es una línea de lista, reinicia el contador
            if not re.match(r'^\s*\d+\.\s+', line):
                list_counter = 0
                prev_indent = -1
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    # ============================================================================
    # FIX 3: MD022 - Headings should be surrounded by blank lines
    # ============================================================================
    # Asegura que los encabezados tengan línea en blanco encima
    content = re.sub(
        r'([^\n])\n(#{1,6}\s+)',
        r'\1\n\n\2',
        content
    )
    
    # ============================================================================
    # FIX 4: MD037 - No spaces in emphasis markers
    # ============================================================================
    # Remueve espacios dentro de marcadores de énfasis: ** text** → **text**
    content = re.sub(r'\*\*\s+', r'**', content)
    content = re.sub(r'\s+\*\*', r'**', content)
    content = re.sub(r'__\s+', r'__', content)
    content = re.sub(r'\s+__', r'__', content)
    
    # ============================================================================
    # FIX 5: MD060 - Table column style (espacios alrededor de pipes)
    # ============================================================================
    # Procesa cada tabla encontrada
    table_pattern = r'(\|.+\|.*\n)+\|[\s\-|:]+\|(\n\|.+\|.*\n)*'
    
    def fix_table_spacing(match):
        table_text = match.group(0)
        lines = table_text.split('\n')
        fixed_lines = []
        
        for line in lines:
            if line.strip():  # No procesar líneas vacías
                # Divide por pipes y procesa
                parts = line.split('|')
                
                # Si es línea separadora (todos guiones/espacios/dos puntos)
                if all(p.strip().replace('-', '').replace(':', '') == '' for p in parts[1:-1]):
                    # Línea separadora: | --- | --- | --- |
                    separator = '| ' + ' | '.join(p.strip() if p.strip() else '---' for p in parts[1:-1]) + ' |'
                    fixed_lines.append(separator)
                else:
                    # Línea de contenido: agregar espacios alrededor de pipes
                    fixed = '| ' + ' | '.join(p.strip() for p in parts[1:-1]) + ' |'
                    fixed_lines.append(fixed)
        
        return '\n'.join(fixed_lines)
    
    # Aplica el arreglo de tablas
    content = re.sub(table_pattern, fix_table_spacing, content, flags=re.MULTILINE)
    
    # ============================================================================
    # VERIFICACIÓN Y ESCRITURA
    # ============================================================================
    if content != original:
        path.write_text(content, encoding='utf-8')
        print(f"✅ {path.name}: ARREGLADO")
        return True
    else:
        print(f"⚠️  {path.name}: SIN CAMBIOS")
        return False

def main():
    print("=" * 80)
    print("CORRECTOR AUTOMÁTICO DE MARKDOWN (290 errores restantes)")
    print("=" * 80)
    print()
    
    files_to_fix = [
        'd:\\diseñopvbesscar\\INICIO_RAPIDO_CONTROL_OPERATIVO.md',
        'd:\\diseñopvbesscar\\RESUMEN_EJECUTIVO_CONTROL_OPERATIVO.md',
        'd:\\diseñopvbesscar\\INDICE_CONTROL_OPERATIVO.md',
    ]
    
    fixed_count = 0
    for filepath in files_to_fix:
        if fix_file(filepath):
            fixed_count += 1
    
    print()
    print("=" * 80)
    print(f"RESULTADO: {fixed_count}/{len(files_to_fix)} archivos procesados")
    print("=" * 80)

if __name__ == '__main__':
    main()
