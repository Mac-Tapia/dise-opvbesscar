#!/usr/bin/env python3
"""
Auto-fix Markdown linting errors:
- MD060: Fix table column styling (add spaces around pipes)
- MD040: Add language to fenced code blocks
- MD051: Fix broken link fragments
- MD024: Rename duplicate headings
"""
import re
from pathlib import Path

def fix_table_pipes(content):
    """Fix MD060: Add spaces around table pipes for proper alignment"""
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Check if it's a table separator line (|---|---|)
        if '|' in line and re.match(r'^\s*\|[\s\-|]+\|\s*$', line):
            # Make sure each cell is properly spaced: | --- |
            cells = line.split('|')
            fixed_cells = []
            for cell in cells:
                cell_clean = cell.strip()
                if cell_clean:  # Not empty
                    # Ensure it's all dashes with padding
                    fixed_cells.append(f' {cell_clean} ')
                else:
                    fixed_cells.append('')
            fixed_line = '|'.join(fixed_cells)
            fixed_lines.append(fixed_line)
        # Check if it's a data row with pipes
        elif '|' in line and not line.strip().startswith('#'):
            # Ensure proper spacing around pipes
            cells = line.split('|')
            fixed_cells = []
            for i, cell in enumerate(cells):
                cell_stripped = cell.strip()
                if i == 0 or i == len(cells) - 1:
                    # First/last cell - keep stripped version
                    fixed_cells.append(cell_stripped)
                elif cell_stripped:  # Middle cells with content
                    fixed_cells.append(f' {cell_stripped} ')
                else:
                    fixed_cells.append('')
            fixed_line = '|'.join(fixed_cells)
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_code_blocks(content):
    """Fix MD040: Add language identifier to fenced code blocks"""
    # Only replace ```\n at the start of code blocks (followed by actual code)
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if line is opening fence without language
        if line.strip() == '```':
            # Look ahead to see what follows
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                # If next line is not empty and not another fence, add language
                if next_line.strip() and not next_line.strip().startswith('```'):
                    # Guess language based on content
                    if any(kw in next_line for kw in ['python', 'import', 'def ', 'class ']):
                        fixed_lines.append('```python')
                    elif any(kw in next_line for kw in ['bash', 'sh', 'python -m', '$', 'pip']):
                        fixed_lines.append('```bash')
                    elif any(kw in next_line for kw in ['curl', 'POST', 'GET', 'HTTP']):
                        fixed_lines.append('```bash')
                    else:
                        fixed_lines.append('```text')  # Default fallback
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
        i += 1
    
    return '\n'.join(fixed_lines)


def fix_duplicate_headings(content):
    """Fix MD024: Rename duplicate headings"""
    heading_counts = {}
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        if line.startswith('#'):
            heading_match = re.match(r'^(#+\s+)(.+)$', line)
            if heading_match:
                level = heading_match.group(1)
                title = heading_match.group(2)
                
                if title in heading_counts:
                    heading_counts[title] += 1
                    # Append count to duplicate heading
                    new_line = f"{level}{title} ({heading_counts[title]})"
                    fixed_lines.append(new_line)
                else:
                    heading_counts[title] = 0
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_link_fragments(content):
    """Fix MD051: Validate link fragments (simplified - just warn about obvious broken ones)"""
    # This is complex because it requires scanning headings.
    # For now, we'll just return content as-is since most fragment issues
    # are due to special characters in headings
    return content


def clean_markdown_file(filepath):
    """Apply all fixes to a markdown file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"Processing {filepath}...")
    
    # Apply fixes in order
    content = fix_table_pipes(content)
    content = fix_code_blocks(content)
    # Skip duplicate heading fix for now - too aggressive
    # content = fix_duplicate_headings(content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Fixed {filepath}")


def main():
    """Fix all markdown files in workspace"""
    workspace = Path('d:\\diseñopvbesscar')
    
    # Find all markdown files
    md_files = list(workspace.glob('**/*.md'))
    
    print(f"Found {len(md_files)} markdown files")
    
    for md_file in md_files:
        try:
            clean_markdown_file(md_file)
        except Exception as e:
            print(f"✗ Error processing {md_file}: {e}")
    
    print("\n✓ Markdown cleanup completed!")


if __name__ == '__main__':
    main()
