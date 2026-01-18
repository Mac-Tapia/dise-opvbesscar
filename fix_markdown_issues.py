import re
import os

# Archivos con problemas
files_with_issues = [
    "PLAN_CONTROL_OPERATIVO.md",
    "GUIA_IMPLEMENTACION_CONTROL_OPERATIVO.md",
    "RESUMEN_MAESTRO_CAMBIOS.md",
]

for filename in files_with_issues:
    filepath = os.path.join(filename)
    if not os.path.exists(filepath):
        print(f"Skipping {filepath} (not found)")
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Fix MD040: Add language to code blocks
    content = re.sub(r'^```\n', '```python\n', content, flags=re.MULTILINE)
    
    # Fix MD060: Table column style - add spaces
    # Find table separator lines and fix them
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Check if this is a table separator line
        if re.match(r'^\|[\s\-:|]+\|$', line):
            # This is a table separator, fix spacing
            parts = line.split('|')
            fixed_parts = []
            for part in parts:
                if part.strip() == '':
                    fixed_parts.append('|')
                else:
                    # Add spaces around dashes
                    fixed_part = ' ' + part.strip() + ' '
                    fixed_parts.append('|' + fixed_part)
            fixed_line = ''.join(fixed_parts)
            # Clean up extra pipes
            fixed_line = re.sub(r'\|\|+', '|', fixed_line)
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Fixed {filename}")
    else:
        print(f"  {filename} (no changes needed)")

print("\n✓ All Markdown files processed")
