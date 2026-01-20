#!/usr/bin/env python3
"""
Corregir errores MD009: Eliminar espacios finales (trailing spaces)
"""

from pathlib import Path

def fix_trailing_spaces(filepath):
    """Eliminar espacios finales de todas las líneas"""
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Dividir en líneas y eliminar espacios finales
        lines = content.split('\n')
        fixed_lines = [line.rstrip() for line in lines]
        fixed_content = '\n'.join(fixed_lines)
        
        # Si hubo cambios, guardar
        if fixed_content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True
        
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

if __name__ == "__main__":
    md_files = list(Path("d:/diseñopvbesscar").rglob("*.md"))
    
    print(f"\nEliminando espacios finales en {len(md_files)} archivos Markdown...")
    
    fixed_count = 0
    for md_file in md_files:
        if fix_trailing_spaces(md_file):
            fixed_count += 1
            # Solo mostrar archivos corregidos del plots/README.md
            if "plots/README.md" in str(md_file):
                print(f"✓ Corregido: {md_file.name}")
    
    print(f"\n✅ Archivos con cambios: {fixed_count}/{len(md_files)}")
