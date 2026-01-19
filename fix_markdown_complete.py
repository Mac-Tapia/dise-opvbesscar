#!/usr/bin/env python3
"""Fix ALL remaining Markdown errors comprehensively"""
import re
from pathlib import Path

def fix_markdown_files():
    """Fix all Markdown files in workspace"""
    md_files = sorted(Path('.').glob('*.md'))
    
    fixes_applied = {}
    
    for md_file in md_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original = content
            count = 0
            
            # 1. Fix MD040: Code blocks without language
            # Find ``` lines that are opening blocks
            lines = content.split('\n')
            new_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                if line.strip() == '```':
                    # Check if this is an opening block
                    if i == 0 or not lines[i-1].strip().startswith('```'):
                        # This is likely an opening block
                        if i + 1 < len(lines) and not lines[i+1].strip().startswith('```'):
                            # Next line is not a close, so add language
                            new_lines.append('```text')
                            count += 1
                            i += 1
                            continue
                new_lines.append(line)
                i += 1
            
            content = '\n'.join(new_lines)
            
            # 2. Fix MD060: Table spacing issues
            # Pattern: |---|---|
            replacements = [
                (r'\|(-{3,})\|', '| --- |'),  # |----|  → | --- |
                (r'\| ---\|', '| --- |'),      # | ---|  → | --- |
                (r'\|---\|', '| --- |'),       # |---|   → | --- |
                (r'\|(-{1,})\|(-{1,})\|', '| --- | --- |'),  # Multi-column
            ]
            
            for pattern, repl in replacements:
                new_content = re.sub(pattern, repl, content)
                count += len(re.findall(pattern, content))
                content = new_content
            
            # 3. Fix MD024: Duplicate headings (make them unique)
            if 'ENTRENAMIENTO' in md_file.name:
                if '### Monitoreo en Vivo\n---' in content:
                    content = content.replace(
                        '### Monitoreo en Vivo\n---\n\n### Indicadores Clave',
                        '### Monitoreo en Vivo (Session)\n\n---\n\n### Indicadores Clave'
                    )
                    count += 1
                
                if '#### Monitorear Progreso' in content:
                    content = content.replace(
                        '#### Monitorear Progreso',
                        '### Monitorear Progreso'
                    )
                    count += 1
            
            if 'TIER1_FIXES' in md_file.name:
                # Make duplicates unique
                matches = re.findall(r'#### ❌ PROBLEMA ORIGINAL(?!\s*-)', content)
                if len(matches) > 1:
                    counter = 0
                    def replace_prob(m):
                        nonlocal counter
                        counter += 1
                        return f'#### ❌ PROBLEMA ORIGINAL {counter}'
                    content = re.sub(r'#### ❌ PROBLEMA ORIGINAL(?!\s*-)', replace_prob, content)
                    count += 1
                
                matches = re.sub(r'#### ✅ SOLUCIÓN APLICADA(?!\s*-)', '#### ✅ SOLUCIÓN APLICADA - S', content)
                if matches != content:
                    content = matches
                    count += 1
            
            # 4. Fix MD051: Link fragments
            if 'SAC_TIER2_INDICE' in md_file.name:
                content = content.replace(
                    '#sac_tier2_resumen_ejecutivocmd',
                    '#sac_tier2_resumen_ejecutivomd'
                )
                content = content.replace(
                    '#sac_tier2_implementation_step_by_stepcmd',
                    '#sac_tier2_implementation_step_by_stepmd'
                )
                content = content.replace(
                    '#sac_tier2_optimizationmd)',
                    '#sac_tier2_optimizationmd)'  # Already correct
                )
                count += 2
            
            if content != original:
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixes_applied[md_file.name] = count
                print(f'✓ {md_file.name} ({count} fixes)')
        
        except Exception as e:
            print(f'✗ {md_file.name}: {e}')
    
    print(f'\n✓ Total files fixed: {len(fixes_applied)}')
    print(f'✓ Total fixes applied: {sum(fixes_applied.values())}')

if __name__ == '__main__':
    fix_markdown_files()
