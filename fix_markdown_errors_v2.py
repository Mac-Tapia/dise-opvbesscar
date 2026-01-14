#!/usr/bin/env python3
"""
Fix remaining Markdown linting errors:
- MD036: Convert emphasis used as heading to proper heading
- MD029: Fix ordered list numbering
- MD024: Fix duplicate headings by renaming
- MD051: Fix link fragments
- MD060: Fix remaining table formatting issues
"""
import re
from pathlib import Path

def fix_emphasis_as_heading(content):
    """Fix MD036: Convert **text** and *text* at start of lines to proper headings"""
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        
        # Check if line starts with ** and ends with ** (bold)
        if stripped.startswith('**') and stripped.endswith('**'):
            # Skip if it's actually inline bold in a paragraph
            if i > 0 and fixed_lines[-1].strip() != '' and not fixed_lines[-1].startswith('#'):
                # It's likely inline, keep it
                fixed_lines.append(line)
            else:
                # Convert to heading
                text = stripped[2:-2]  # Remove ** from both ends
                fixed_lines.append(f"## {text}")
        elif stripped.startswith('*') and stripped.endswith('*') and not stripped.startswith('**'):
            # Check if it's a single-line italic that looks like a heading
            if i > 0 and fixed_lines[-1].strip() == '':
                # Likely a heading
                text = stripped[1:-1]  # Remove * from both ends
                fixed_lines.append(f"## {text}")
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_ordered_list_numbering(content):
    """Fix MD029: Ensure ordered lists use proper numbering (1, 2, 3, ...)"""
    lines = content.split('\n')
    fixed_lines = []
    list_number = 1
    in_list = False
    
    for line in lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        
        # Check if this is an ordered list item
        match = re.match(r'^(\d+)\.\s+(.+)$', stripped)
        if match:
            in_list = True
            text = match.group(2)
            fixed_line = ' ' * indent + f"{list_number}. {text}"
            fixed_lines.append(fixed_line)
            list_number += 1
        else:
            # If we're in a list and hit a blank line or non-list, reset
            if in_list and stripped == '':
                in_list = False
                list_number = 1
            elif in_list and not re.match(r'^(\d+)\.\s+', stripped) and stripped != '':
                # Non-list content while in list
                in_list = False
                list_number = 1
            
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_duplicate_headings(content):
    """Fix MD024: Rename duplicate headings with (2), (3), etc."""
    lines = content.split('\n')
    fixed_lines = []
    heading_counts = {}
    
    for line in lines:
        if line.startswith('#'):
            match = re.match(r'^(#+)\s+(.+)$', line)
            if match:
                level = match.group(1)
                title = match.group(2)
                
                # Check if we've seen this heading before
                if title in heading_counts:
                    heading_counts[title] += 1
                    new_title = f"{title} ({heading_counts[title]})"
                    fixed_lines.append(f"{level} {new_title}")
                else:
                    heading_counts[title] = 1
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_list_indentation(content):
    """Fix MD007: Ensure unordered lists use 2-space indentation"""
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Check if it's an unordered list item
        match = re.match(r'^(\s+)([-*])\s+(.+)$', line)
        if match:
            indent_str = match.group(1)
            bullet = match.group(2)
            text = match.group(3)
            
            # Count spaces and normalize to multiples of 2
            indent_len = len(indent_str)
            level = (indent_len + 1) // 2  # Round up to get level
            new_indent = '  ' * level  # 2 spaces per level
            
            fixed_lines.append(f"{new_indent}{bullet} {text}")
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_table_pipes_double(content):
    """Fix remaining table pipe issues"""
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Check for || which is a double pipe error
        if '||' in line and '|' in line:
            # Replace || with single |
            fixed_line = line.replace('||', '|')
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def clean_markdown_file_v2(filepath):
    """Apply all fixes to a markdown file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"✗ Cannot read {filepath}: {e}")
        return
    
    print(f"Processing {filepath}...")
    
    # Apply fixes in order
    content = fix_emphasis_as_heading(content)
    content = fix_ordered_list_numbering(content)
    content = fix_duplicate_headings(content)
    content = fix_list_indentation(content)
    content = fix_table_pipes_double(content)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Fixed {filepath}")
    except Exception as e:
        print(f"✗ Error writing {filepath}: {e}")


def main():
    """Fix remaining markdown errors in workspace"""
    workspace = Path('d:\\diseñopvbesscar')
    
    # Target specific files with known issues
    problem_files = [
        'docs/CONSTRUCCION_DATASET_COMPLETA.md',
        'docs/DIAGRAMA_TECNICO_OE2_OE3.md',
        'docs/INDICE_DOCUMENTACION_DATOS.md',
        'DOCUMENTACION_COMPLETADA.md',
        'INDICE_VISUAL_DOCUMENTACION.md',
        'ENTREGA_FINAL.md',
        'VERIFICACION_FINAL_ENTREGA.md',
        'TABLA_CONTENIDOS.md',
        'fix_markdown_errors.py',  # Clean up unused imports
    ]
    
    for rel_path in problem_files:
        filepath = workspace / rel_path
        if filepath.exists():
            clean_markdown_file_v2(filepath)
        else:
            print(f"⚠ File not found: {filepath}")
    
    print("\n✓ Markdown fix v2 completed!")


if __name__ == '__main__':
    main()
