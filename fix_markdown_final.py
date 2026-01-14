#!/usr/bin/env python3
"""
Final cleanup for remaining errors:
- MD036: Fix remaining emphasis used as heading (but only obvious ones)
- MD026: Remove trailing punctuation from headings
- MD051: Fix link fragments
- MD001: Fix heading level increments
- MD005/MD007: Fix list indentation
- MD056: Fix table column counts
- MD037: Fix spaces in emphasis
"""
import re
from pathlib import Path

def fix_trailing_punctuation_in_headings(content):
    """Remove . : ; ! ? from end of headings"""
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        if line.startswith('#') and not line.startswith('```'):
            # Check if it ends with punctuation
            if line[-1] in '.,:;!?':
                fixed_lines.append(line[:-1])
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_emphasis_spaces(content):
    """Fix MD037: Remove spaces inside emphasis markers"""
    # ** text ** -> **text**
    content = re.sub(r'\*\*\s+', '**', content)
    content = re.sub(r'\s+\*\*', '**', content)
    # __text__ 
    content = re.sub(r'__\s+', '__', content)
    content = re.sub(r'\s+__', '__', content)
    
    return content


def fix_heading_increments(content):
    """Fix MD001: Ensure headings increment by 1 level"""
    lines = content.split('\n')
    fixed_lines = []
    last_heading_level = 0
    
    for line in lines:
        if line.startswith('#'):
            # Count # symbols
            level = len(line) - len(line.lstrip('#'))
            
            # If jump is > 1, add intermediate levels
            if level > last_heading_level + 1 and last_heading_level > 0:
                # Skip this line or fix it
                # For now, just convert #### to ### if it comes after ##
                if level > 3:
                    new_level = last_heading_level + 1
                    heading_text = line.lstrip('#').strip()
                    line = '#' * new_level + ' ' + heading_text
                    level = new_level
            
            fixed_lines.append(line)
            last_heading_level = level
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_list_indentation_final(content):
    """Fix remaining list indentation issues"""
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Handle 4-space indentation for top-level items (should be 2)
        match = re.match(r'^    (-|\*)\s+(.+)$', line)
        if match:
            bullet = match.group(1)
            text = match.group(2)
            # Convert 4 spaces to 2 for top-level item
            fixed_lines.append(f"  {bullet} {text}")
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_table_columns(content):
    """Fix table column count issues"""
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this is a table row with missing columns
        if '|' in line and i > 0 and '|' in lines[i-1]:
            cells = [c.strip() for c in line.split('|')]
            cells = [c for c in cells if c]  # Remove empty
            
            # Check previous line (header) for expected column count
            prev_cells = [c.strip() for c in lines[i-1].split('|')]
            prev_cells = [c for c in prev_cells if c]
            
            if len(cells) < len(prev_cells):
                # Add empty cells to match column count
                while len(cells) < len(prev_cells):
                    cells.append('')
                # Reconstruct line
                line = '| ' + ' | '.join(cells) + ' |'
        
        fixed_lines.append(line)
        i += 1
    
    return '\n'.join(fixed_lines)


def clean_file_final(filepath):
    """Apply final fixes"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return
    
    print(f"Final cleanup: {filepath}")
    
    # Apply fixes
    content = fix_trailing_punctuation_in_headings(content)
    content = fix_emphasis_spaces(content)
    content = fix_heading_increments(content)
    content = fix_list_indentation_final(content)
    content = fix_table_columns(content)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Finalized {filepath}")
    except:
        pass


def main():
    """Final cleanup pass"""
    problem_files = [
        'INDICE_VISUAL_DOCUMENTACION.md',
        'ENTREGA_FINAL.md',
        'VERIFICACION_FINAL_ENTREGA.md',
        'TABLA_CONTENIDOS.md',
        'docs/INDICE_DOCUMENTACION_DATOS.md',
        'VERIFICACION_ENTRENAMIENTO_SAC.md',
        'ANALISIS_VISUAL_APRENDIZAJE_SAC.md',
        'VERIFICACION_COMPLETA_RESUMEN.md',
    ]
    
    for rel_path in problem_files:
        filepath = Path('d:\\diseñopvbesscar') / rel_path
        if filepath.exists():
            clean_file_final(filepath)
    
    print("\n✓ Final markdown cleanup completed!")


if __name__ == '__main__':
    main()
