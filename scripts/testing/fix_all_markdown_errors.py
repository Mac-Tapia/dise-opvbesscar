#!/usr/bin/env python3.11
"""
Script para corregir todos los errores Markdown del proyecto
Corrige: MD036, MD040, MD060
"""

import os
import re
from pathlib import Path

def fix_md_errors(file_path):
    """Corrige errores Markdown en un archivo"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # MD036: Reemplazar **texto** en línea por ## Texto cuando esté al inicio
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        # Si la línea es solo **texto**, convertir a ## Texto
        if line.startswith('**') and line.endswith('**') and line.count('**') == 2:
            text = line[2:-2]
            new_lines.append(f'## {text}')
        else:
            new_lines.append(line)
    content = '\n'.join(new_lines)
    
    # MD040: Agregar lenguaje "text" a bloques vacíos
    content = re.sub(r'```\n', '```text\n', content)
    
    # MD060: Arreglar tablas - reemplazar |---|---|...| por | --- | --- | ... |
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if line.startswith('|') and line.endswith('|') and '---' in line:
            # Reemplazar |---|...| con | --- | ... |
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if all(cell == '---' or all(c == '-' for c in cell) for cell in cells):
                new_line = '| ' + ' | '.join(['---'] * len(cells)) + ' |'
                new_lines.append(new_line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    content = '\n'.join(new_lines)
    
    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

# Buscar todos los archivos .md
root = Path('d:\\diseñopvbesscar')
md_files = list(root.glob('**/*.md'))

fixed_count = 0
for md_file in md_files:
    if fix_md_errors(str(md_file)):
        fixed_count += 1
        print(f'Corregido: {md_file.name}')

print(f'\nTotal archivos corregidos: {fixed_count}/{len(md_files)}')
