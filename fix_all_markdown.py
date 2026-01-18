#!/usr/bin/env python3
"""Script para corregir todos los problemas de Markdown automáticamente."""

import re
import os
from pathlib import Path

def fix_markdown_file(filepath):
    """Corrige problemas MD040 y MD060 en un archivo Markdown."""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Fix MD040: Fenced code blocks without language specification
        if line.strip() == '```':
            # Peek at next line to guess language
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                # Simple heuristics
                if 'python' in next_line.lower() or 'import' in next_line or 'def ' in next_line:
                    fixed_lines.append('```python\n')
                    i += 1
                    continue
                elif 'yaml' in next_line.lower() or next_line.startswith('  '):
                    fixed_lines.append('```yaml\n')
                    i += 1
                    continue
                elif next_line.startswith('$') or next_line.startswith('#') or 'bash' in next_line:
                    fixed_lines.append('```bash\n')
                    i += 1
                    continue
                elif 'json' in next_line.lower() or '{' in next_line:
                    fixed_lines.append('```json\n')
                    i += 1
                    continue
                else:
                    # Default to bash for terminal-like commands
                    fixed_lines.append('```bash\n')
                    i += 1
                    continue
        
        # Fix MD060: Table column spacing
        # Pattern: |---|---|...|  (without spaces)
        if re.match(r'^\|\s*[-:]+\s*(\|\s*[-:]+\s*)+\|\s*$', line):
            # This is a table separator, ensure proper spacing
            parts = line.split('|')
            fixed_parts = []
            for part in parts:
                if part.strip():
                    # Ensure spaces around dashes
                    dashes = part.strip()
                    fixed_parts.append(' ' + dashes + ' ')
                else:
                    fixed_parts.append('')
            
            fixed_line = '|' + '|'.join(fixed_parts) + '|\n'
            # Clean up multiple pipes
            fixed_line = re.sub(r'\|\s*\|', '|', fixed_line)
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)
        
        i += 1
    
    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    return True

# Process all markdown files
md_files = [
    "PLAN_CONTROL_OPERATIVO.md",
    "GUIA_IMPLEMENTACION_CONTROL_OPERATIVO.md",
    "RESUMEN_MAESTRO_CAMBIOS.md",
]

for md_file in md_files:
    if os.path.exists(md_file):
        try:
            fix_markdown_file(md_file)
            print(f"✓ Fixed {md_file}")
        except Exception as e:
            print(f"✗ Error fixing {md_file}: {e}")
    else:
        print(f"! Skipped {md_file} (not found)")

print("\n✓ Markdown fixes complete")
