#!/usr/bin/env python3
"""
Final ultra-cleanup: Fix remaining MD022, MD055, MD032 issues
"""

from pathlib import Path
import re


def fix_verificacion_entrenamiento(filepath):
    """Fix MD022, MD055, MD032, MD007 issues"""
    content = filepath.read_text(encoding='utf-8')
    
    # Fix blank lines around headings (MD022)
    content = re.sub(r'(\d+\.\*\*[^*]+\*\*)\n(- )', r'\1\n\n\2', content)
    content = re.sub(r'(###.*)\n(- )', r'\1\n\n\2', content)
    
    # Fix table pipe styles - remove leading pipe from table headers
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Check if it's a separator line (all dashes and pipes)
        if re.match(r'^[|\s\-:]+$', line) and i > 0:
            # Check if previous line is a table
            if '|' in lines[i-1] and not lines[i-1].startswith('|'):
                # This is a trailing-only table, skip the separator
                fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        # Fix list indentation with 3 spaces (MD007)
        elif re.match(r'^   -', line):
            fixed_line = line.replace('   ', '', 1)
            fixed_lines.append(fixed_line)
        # Fix single space indentation (MD007)
        elif re.match(r'^ - ', line) and i > 0:
            # Check if previous context suggests this should be a list
            prev_line = lines[i-1].strip() if i > 0 else ''
            if prev_line and not prev_line.startswith('#') and not prev_line.startswith('|'):
                # Add blank line before list
                if fixed_lines[-1].strip():
                    fixed_lines.append('')
            fixed_lines.append(line.lstrip())
        else:
            fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    filepath.write_text(content, encoding='utf-8')
    print(f"✓ Fixed: {filepath.name} - Headings, tables, lists")


def fix_analisis_visual(filepath):
    """Fix MD024 duplicate headings, MD022 spacing"""
    content = filepath.read_text(encoding='utf-8')
    
    # Fix duplicate "Interpretación" headings
    count = {}
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        if line.strip() == '### Interpretación':
            count['interpretacion'] = count.get('interpretacion', 0) + 1
            if count['interpretacion'] > 1:
                line = f"### Interpretación ({count['interpretacion']})"
        
        # Fix blank lines before headings (MD022)
        if line.startswith('###') or line.startswith('####'):
            if fixed_lines and fixed_lines[-1].strip():
                fixed_lines.append('')
        
        fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    filepath.write_text(content, encoding='utf-8')
    print(f"✓ Fixed: {filepath.name} - Duplicate headings")


def fix_verificacion_completa(filepath):
    """Fix MD032 blank lines around lists and MD060 table spacing"""
    content = filepath.read_text(encoding='utf-8')
    
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Fix blank lines before lists (MD032)
        if line.lstrip().startswith('- ') and i > 0:
            prev = fixed_lines[-1].strip() if fixed_lines else ''
            if prev and not prev.startswith('-') and not prev.startswith('#'):
                fixed_lines.append('')
        
        # Fix table pipes
        if '|' in line and not re.match(r'^\s*\|[\s\-:|\s]+\|?\s*$', line):
            parts = line.split('|')
            fixed_parts = []
            for part in parts:
                trimmed = part.strip()
                if trimmed:
                    fixed_parts.append(f' {trimmed} ')
                else:
                    fixed_parts.append('')
            fixed_line = '|'.join(fixed_parts)
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    filepath.write_text(content, encoding='utf-8')
    print(f"✓ Fixed: {filepath.name} - Lists and tables")


def main():
    base = Path('d:\\diseñopvbesscar')
    
    files = {
        'VERIFICACION_ENTRENAMIENTO_SAC.md': fix_verificacion_entrenamiento,
        'ANALISIS_VISUAL_APRENDIZAJE_SAC.md': fix_analisis_visual,
        'VERIFICACION_COMPLETA_RESUMEN.md': fix_verificacion_completa,
    }
    
    for filename, fixer in files.items():
        filepath = base / filename
        if filepath.exists():
            fixer(filepath)
    
    print("\n✓ Ultra-cleanup completed!")


if __name__ == '__main__':
    main()
