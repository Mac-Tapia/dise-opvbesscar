#!/usr/bin/env python3.11
"""Fix all remaining markdown linting errors: MD036, MD040, MD060"""

import re
from pathlib import Path

files_to_fix = [
    'RESUMEN_OPCION_1_Y_4_COMPLETADAS.md',
    'RESUMEN_OPCION_C_Y_E_COMPLETADAS.md',
    'docs/index.md'
]

def fix_md036(content):
    """Fix MD036: Emphasis used instead of a heading"""
    # **1. Text** -> ## 1. Text
    content = re.sub(r'^(\*\*\d+\.\s+[^*]+\*\*)$', lambda m: f'## {m.group(1)[2:-2]}', content, flags=re.MULTILINE)
    # **OPCIÓN X: Text** -> ## OPCIÓN X: Text  
    content = re.sub(r'^(\*\*OPCIÓN\s+[A-Z]:[^*]+\*\*)$', lambda m: f'## {m.group(1)[2:-2]}', content, flags=re.MULTILINE)
    # **Text** at line start -> ## Text
    content = re.sub(r'^(\*\*[A-Z][^*\n]*\*\*)$', lambda m: f'## {m.group(1)[2:-2]}', content, flags=re.MULTILINE)
    return content

def fix_md040(content):
    """Fix MD040: Fenced code blocks should have a language specified"""
    # ``` (empty) -> ```text
    content = re.sub(r'```\s*\n', '```text\n', content)
    # Triple backtick alone on line -> text language
    content = re.sub(r'^```$', '```text', content, flags=re.MULTILINE)
    return content

def fix_md060(content):
    """Fix MD060: Table pipes without proper spacing"""
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        if line.strip().startswith('|') and '---' in line:
            # This is a separator line
            # Replace |---| with | --- |
            line = re.sub(r'\|(-+)\|', r'| --- |', line)
            # Fix edges: |---... -> | --- | ...
            line = re.sub(r'^\|(-+)', r'| ---', line)
            line = re.sub(r'(-+)\|$', r'--- |', line)
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def process_file(filepath):
    """Process single markdown file"""
    if not Path(filepath).exists():
        print(f"⏭️  File not found: {filepath}")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()
    
    content = original
    
    # Apply fixes in order
    content = fix_md036(content)
    content = fix_md040(content)
    content = fix_md060(content)
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Fixed: {filepath}")
        return True
    else:
        print(f"⏭️  No changes needed: {filepath}")
        return False

if __name__ == '__main__':
    print("🔧 Fixing markdown linting errors...")
    print()
    
    fixed_count = 0
    for fpath in files_to_fix:
        if process_file(fpath):
            fixed_count += 1
    
    print()
    print(f"✅ DONE: {fixed_count}/{len(files_to_fix)} files fixed")
