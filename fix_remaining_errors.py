#!/usr/bin/env python3
"""
Final cleanup script for remaining Markdown errors.
Targets:
- CONSTRUCCION_DATASET_COMPLETA.md: MD051 link fragments, MD026 trailing punctuation
- INDICE_DOCUMENTACION_DATOS.md: MD007 list indentation, MD060 table formatting, MD026
"""

import re
from pathlib import Path


def fix_link_fragments(content: str) -> str:
    """Fix MD051: Remove accents from link fragments"""
    # Map Spanish accented characters to their non-accented versions
    accent_map = {
        'ó': 'o',
        'é': 'e',
        'í': 'i',
        'á': 'a',
        'ú': 'u',
        'ñ': 'n',
    }
    
    def replace_anchor(match):
        text = match.group(1)
        # Remove accents from anchor
        anchor = text.lower().replace(' ', '-').replace('.', '')
        for accented, plain in accent_map.items():
            anchor = anchor.replace(accented, plain)
        return f'[{text}](#{anchor})'
    
    # Pattern: [text](#text-with-accents)
    result = re.sub(r'\[([^\]]+)\]\(#([^\)]+)\)', replace_anchor, content)
    return result


def fix_list_indentation(content: str) -> str:
    """Fix MD007/MD032: Fix list indentation to be 0 spaces"""
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Match lines starting with 2+ spaces followed by dash or number
        if re.match(r'^  +[-*] ', line):
            # Remove leading spaces from lists
            fixed_line = re.sub(r'^  +', '', line)
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)
    
    # Fix blank lines around lists
    result = '\n'.join(fixed_lines)
    
    # Ensure blank line before list
    result = re.sub(r'([^\n])\n([-*] )', r'\1\n\n\2', result)
    
    return result


def fix_table_spacing(content: str) -> str:
    """Fix MD060: Normalize table pipe spacing"""
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        if '|' in line and not line.strip().startswith('|'):
            # Line contains table content
            # Split by |, trim, rejoin with proper spacing
            parts = line.split('|')
            fixed_parts = []
            for part in parts:
                stripped = part.strip()
                fixed_parts.append(f' {stripped} ' if stripped else '')
            fixed_line = '|'.join(fixed_parts)
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_trailing_punctuation(content: str) -> str:
    """Fix MD026: Remove trailing punctuation from headings"""
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Match heading pattern
        match = re.match(r'^(#{1,6})\s+(.+?)([.!?])\s*$', line)
        if match:
            hashes = match.group(1)
            text = match.group(2)
            fixed_line = f'{hashes} {text}'
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def clean_file(filepath: str) -> None:
    """Apply all fixes to a single file"""
    path = Path(filepath)
    if not path.exists():
        print(f"⚠ File not found: {filepath}")
        return
    
    print(f"Fixing: {filepath}")
    content = path.read_text(encoding='utf-8')
    
    # Apply fixes in order
    content = fix_link_fragments(content)
    content = fix_list_indentation(content)
    content = fix_table_spacing(content)
    content = fix_trailing_punctuation(content)
    
    path.write_text(content, encoding='utf-8')
    print(f"✓ Fixed: {filepath}")


def main():
    """Main entry point"""
    base_path = Path('d:\\diseñopvbesscar')
    
    files_to_fix = [
        'docs/CONSTRUCCION_DATASET_COMPLETA.md',
        'docs/INDICE_DOCUMENTACION_DATOS.md',
    ]
    
    for rel_path in files_to_fix:
        filepath = base_path / rel_path
        clean_file(str(filepath))
    
    print("\n✓ Final cleanup completed!")


if __name__ == '__main__':
    main()
