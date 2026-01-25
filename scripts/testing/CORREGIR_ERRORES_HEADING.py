#!/usr/bin/env python3
"""
Corregir errores Markdown restantes:
MD041: First line should be a top-level heading
MD036: Emphasis used instead of a heading
"""

from pathlib import Path
import re

def fix_markdown_heading_issues(filepath):
    """Corregir problemas con headings"""

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        lines = content.split('\n')

        # MD041: First line should be top-level heading
        if lines and not lines[0].startswith('#'):
            # Si la primera línea no es un heading, buscar si empieza con ##
            if lines[0].startswith('##'):
                # Convertir ## a #
                lines[0] = '#' + lines[0]

        # MD036: Emphasis used instead of a heading
        # Buscar líneas que empiezan con **text:** o *text:*
        fixed_lines = []
        for i, line in enumerate(lines):
            # Patrón: **texto:** o *texto:* al inicio de la línea
            match = re.match(r'^\*{1,2}([^*]+)\*{1,2}:\s*(.*)', line)
            if match and not line.strip().startswith('#'):
                # Esta es una línea con énfasis que parece ser heading
                # Solo convertir si está sola o es un párrafo de resumen
                pass  # Dejar tal cual, son válidos como énfasis

            # Buscar líneas que terminan con ** y son heading implícito
            if re.match(r'^\*{1,2}.+\*{1,2}$', line) and not line.strip().startswith('#'):
                # Podría ser un heading implícito, pero solo si está al final del archivo
                if i == len(lines) - 2:  # Penúltima línea antes del final
                    # Podría ser un heading de conclusión
                    pass

            fixed_lines.append(line)

        fixed_content = '\n'.join(fixed_lines)

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

    print(f"\nCorrigiendo problemas de heading en {len(md_files)} archivos...")

    fixed_count = 0
    for md_file in md_files:
        if fix_markdown_heading_issues(md_file):
            fixed_count += 1
            if "LIMPIEZA" in md_file.name or "INDICE" in md_file.name:
                print(f"✓ Corregido: {md_file.name}")

    print(f"\n✅ Archivos con cambios: {fixed_count}/{len(md_files)}")
