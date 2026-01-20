#!/usr/bin/env python3
"""
Corregir errores MD060 en archivos Markdown
Agrega espacios después de pipes en bordes izquierdo y derecho de tablas
"""

from pathlib import Path

def fix_markdown_tables(filepath):
    """Corregir tablas Markdown para cumplir MD060"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Patrones para tablas Markdown
    # Buscar líneas que empiezan con | y terminan con |
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        if line.strip().startswith('|') and line.strip().endswith('|'):
            # Esta es una línea de tabla
            # Asegurar que hay espacio después del primer | y antes del último |
            
            # Agregar espacio después del primer |
            if line.startswith('|') and len(line) > 1 and line[1] != ' ':
                line = '| ' + line[1:]
            elif line.startswith('|') and len(line) > 1 and line[1] == ' ':
                pass  # Ya tiene espacio
            
            # Agregar espacio antes del último | si no lo tiene
            if line.endswith('|') and len(line) > 1 and line[-2] != ' ':
                line = line[:-1] + ' |'
            elif line.endswith('|') and len(line) > 1 and line[-2] == ' ':
                pass  # Ya tiene espacio
            
            # Procesar el interior - asegurar espacios alrededor de todos los pipes
            parts = line.split('|')
            fixed_parts = []
            
            for i, part in enumerate(parts):
                part = part.strip()
                if i == 0 or i == len(parts) - 1:
                    # Primer o último elemento (vacío en bordes)
                    fixed_parts.append(part)
                else:
                    # Elementos intermedios
                    fixed_parts.append(part)
            
            fixed_line = ' | '.join(fixed_parts)
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)
    
    fixed_content = '\n'.join(fixed_lines)
    
    if fixed_content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        return True
    
    return False

if __name__ == "__main__":
    md_files = list(Path("d:/diseñopvbesscar").rglob("*.md"))
    
    print(f"\nCorrigiendo {len(md_files)} archivos Markdown...")
    
    fixed_count = 0
    for md_file in md_files:
        if fix_markdown_tables(md_file):
            print(f"✓ Corregido: {md_file.name}")
            fixed_count += 1
    
    print(f"\n✅ Archivos corregidos: {fixed_count}/{len(md_files)}")
