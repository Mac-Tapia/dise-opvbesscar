#!/usr/bin/env python3
"""
Corregir errores MD040: Agregar lenguajes a bloques de código fenced
"""

import re
from pathlib import Path

def fix_fenced_code_blocks(filepath):
    """Agregar lenguaje a bloques de código fenced sin lenguaje especificado"""

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Buscar bloques de código fenced sin lenguaje
        # Patrón: ``` seguido de newline (sin lenguaje)
        pattern = r'```\n'
        # Reemplazar con ```text\n (lenguaje genérico)
        fixed_content = re.sub(pattern, '```text\n', content)

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

    print(f"\nAgregando lenguajes a bloques de código en {len(md_files)} archivos...")

    fixed_count = 0
    for md_file in md_files:
        if fix_fenced_code_blocks(md_file):
            fixed_count += 1
            print(f"✓ Corregido: {md_file.relative_to(Path('d:/diseñopvbesscar'))}")

    print(f"\n✅ Archivos con cambios: {fixed_count}/{len(md_files)}")
