#!/usr/bin/env python3
"""
Final cleanup: Remove accents from link anchors and fix list indentation
"""

from pathlib import Path
import re
import unicodedata


def remove_accents(text):
    """Remove accents from text"""
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join([c for c in nfkd if not unicodedata.combining(c)])


def fix_construccion_dataset(filepath):
    """Fix MD051 by removing accents from link anchors"""
    content = filepath.read_text(encoding='utf-8')
    
    # Fix table of contents links - remove accents
    def fix_link(match):
        text = match.group(1)
        anchor = match.group(2).lower().replace(' ', '-').replace(':', '')
        # Remove accents from anchor
        anchor = remove_accents(anchor)
        return f'[{text}](#{anchor})'
    
    # Pattern: [text](#anchor-text)
    content = re.sub(r'\[([^\]]+)\]\(#([^\)]+)\)', fix_link, content)
    
    filepath.write_text(content, encoding='utf-8')
    print(f"✓ Fixed: {filepath.name} - Removed accents from link anchors")


def fix_tabla_contenidos(filepath):
    """Fix MD007/MD032/MD022 in TABLA_CONTENIDOS.md"""
    lines = filepath.read_text(encoding='utf-8').split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check for heading without blank line after
        if line.startswith('###') and i + 1 < len(lines):
            fixed_lines.append(line)
            # Add blank line after heading if missing
            if lines[i + 1].strip() and not lines[i + 1].startswith('#'):
                fixed_lines.append('')
            i += 1
        # Check for list with 2-space indent (MD007)
        elif re.match(r'^  -', line):
            # Remove 2-space indent
            fixed_line = line.lstrip()
            fixed_lines.append(fixed_line)
            i += 1
        # Check for list without blank line before (MD032)
        elif re.match(r'^-', line) and i > 0:
            prev = fixed_lines[-1].strip() if fixed_lines else ''
            if prev and not prev.startswith('-') and not prev.startswith('#'):
                # Add blank line before list
                fixed_lines.append('')
            fixed_lines.append(line)
            i += 1
        else:
            fixed_lines.append(line)
            i += 1
    
    filepath.write_text('\n'.join(fixed_lines), encoding='utf-8')
    print(f"✓ Fixed: {filepath.name} - Fixed list indentation and heading spacing")


def main():
    base = Path('d:\\diseñopvbesscar')
    
    # Fix CONSTRUCCION_DATASET_COMPLETA.md
    construccion_file = base / 'docs/CONSTRUCCION_DATASET_COMPLETA.md'
    if construccion_file.exists():
        fix_construccion_dataset(construccion_file)
    
    # Fix TABLA_CONTENIDOS.md
    tabla_file = base / 'TABLA_CONTENIDOS.md'
    if tabla_file.exists():
        fix_tabla_contenidos(tabla_file)
    
    print("\n✓ All final fixes completed!")


if __name__ == '__main__':
    main()
