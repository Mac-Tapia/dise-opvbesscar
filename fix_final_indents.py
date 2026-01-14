#!/usr/bin/env python3
"""
Final final cleanup: Fix 4-space indentation (MD007) and table pipes (MD060)
"""

from pathlib import Path
import re


def fix_tabla_contenidos_indents(filepath):
    """Fix 4-space indentation to 2-space"""
    content = filepath.read_text(encoding='utf-8')
    
    # Replace 4 spaces at start of lines with 2 spaces (but not inside code blocks)
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # If line starts with 4+ spaces and is a list item, reduce to 2
        if re.match(r'^    -', line):
            fixed_line = line.replace('    ', '  ', 1)
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)
    
    filepath.write_text('\n'.join(fixed_lines), encoding='utf-8')
    print(f"✓ Fixed: {filepath.name} - 4-space indents to 2-space")


def fix_table_pipes(filepath):
    """Fix MD060 table pipe spacing"""
    content = filepath.read_text(encoding='utf-8')
    
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Check if it's a table line (has pipes)
        if '|' in line and not re.match(r'^\s*\|[\s\-:|\s]+\|?\s*$', line):
            # Split by pipes
            parts = line.split('|')
            fixed_parts = []
            
            for part in parts:
                trimmed = part.strip()
                # Add proper spacing
                if trimmed or fixed_parts:  # Don't add empty first cell
                    fixed_parts.append(f' {trimmed} ' if trimmed else '')
            
            # Rejoin
            fixed_line = '|'.join(fixed_parts)
            fixed_lines.append(fixed_line)
        # Fix table ending (missing trailing pipe)
        elif re.search(r'\|[^|]*\*\*[^|]*$', line):
            # Line ends with ** but no trailing |, add it
            if not line.rstrip().endswith('|'):
                parts = line.rstrip().split('|')
                fixed_parts = []
                for part in parts:
                    trimmed = part.strip()
                    fixed_parts.append(f' {trimmed} ' if trimmed else '')
                fixed_line = '|'.join(fixed_parts).rstrip() + '|'
                fixed_lines.append(fixed_line)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    filepath.write_text('\n'.join(fixed_lines), encoding='utf-8')
    print(f"✓ Fixed: {filepath.name} - Table pipes")


def main():
    base = Path('d:\\diseñopvbesscar')
    
    # Fix TABLA_CONTENIDOS.md indentation
    tabla_file = base / 'TABLA_CONTENIDOS.md'
    if tabla_file.exists():
        fix_tabla_contenidos_indents(tabla_file)
    
    # Fix table pipes in multiple files
    files_to_fix = [
        'TABLA_CONTENIDOS.md',
        'VERIFICACION_ENTRENAMIENTO_SAC.md',
    ]
    
    for rel_path in files_to_fix:
        filepath = base / rel_path
        if filepath.exists():
            fix_table_pipes(filepath)
    
    print("\n✓ All indentation and table fixes completed!")


if __name__ == '__main__':
    main()
