#!/usr/bin/env python3
"""
Fix MD060 table spacing errors using simple string replacement.
"""

from pathlib import Path
import re


def fix_table_md060(content: str) -> str:
    """Fix MD060 errors by ensuring exact spacing around pipes"""
    lines = content.split('\n')
    result_lines = []
    
    for line in lines:
        # Check if line contains table cells (has | but not markdown separator)
        if '|' in line and not re.match(r'^\s*\|[\s\-:|\s]+\|?\s*$', line):
            # Split by |, process each cell
            cells = line.split('|')
            fixed_cells = []
            
            for i, cell in enumerate(cells):
                # For first and last empty cells (from edge pipes)
                if i == 0 or i == len(cells) - 1:
                    if not cell.strip():
                        fixed_cells.append('')
                        continue
                
                # Trim whitespace and re-add single space padding
                trimmed = cell.strip()
                if trimmed:
                    fixed_cells.append(f' {trimmed} ')
                else:
                    fixed_cells.append(' ')
            
            # Rejoin with pipes
            fixed_line = '|'.join(fixed_cells)
            result_lines.append(fixed_line)
        else:
            result_lines.append(line)
    
    return '\n'.join(result_lines)


def main():
    base = Path('d:\\diseñopvbesscar')
    
    # Files with MD060 errors
    files = [
        'docs/INDICE_DOCUMENTACION_DATOS.md',
        'INDICE_VISUAL_DOCUMENTACION.md',
        'ENTREGA_FINAL.md',
    ]
    
    for rel_path in files:
        filepath = base / rel_path
        if not filepath.exists():
            print(f"⚠ {filepath} not found")
            continue
        
        print(f"Fixing MD060: {filepath.name}")
        content = filepath.read_text(encoding='utf-8')
        fixed = fix_table_md060(content)
        filepath.write_text(fixed, encoding='utf-8')
        print(f"✓ Fixed: {filepath.name}")


if __name__ == '__main__':
    main()
