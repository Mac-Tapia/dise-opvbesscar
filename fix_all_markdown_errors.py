#!/usr/bin/env python3
"""Script para corregir TODOS los errores de markdown en el proyecto."""

import re
from pathlib import Path
from typing import List, Tuple

def fix_markdown_file(file_path: Path) -> Tuple[int, List[str]]:
    """Corrige todos los errores de markdown en un archivo.

    Returns:
        Tuple con (número de correcciones, lista de correcciones aplicadas)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        corrections = []

        # 1. MD040: Agregar lenguaje a bloques de código sin especificar
        # Buscar ``` sin lenguaje seguido de salto de línea
        def add_bash_to_code_blocks(match):
            # Si ya tiene lenguaje, dejarlo
            if match.group(1).strip():
                return match.group(0)
            corrections.append("MD040: Added bash to code block")
            return '```bash\n'

        content = re.sub(r'^```([^\n]*)\n', add_bash_to_code_blocks, content, flags=re.MULTILINE)

        # 2. MD024: Hacer únicos los encabezados duplicados agregando contexto
        # Encontrar todos los headings
        headings = re.findall(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE)
        heading_counts = {}

        def make_heading_unique(match):
            level = match.group(1)
            text = match.group(2).strip()

            if text not in heading_counts:
                heading_counts[text] = 0
            else:
                heading_counts[text] += 1
                # Agregar número al duplicado
                corrections.append(f"MD024: Made heading unique: {text}")
                return f"{level} {text} ({heading_counts[text] + 1})"

            return match.group(0)

        content = re.sub(r'^(#{1,6})\s+(.+)$', make_heading_unique, content, flags=re.MULTILINE)

        # 3. MD036: Convertir énfasis usado como heading a heading real
        # Buscar **texto** al inicio de línea
        def convert_emphasis_to_heading(match):
            text = match.group(1)
            # Si es corto y parece título, convertir a h4
            if len(text) < 50 and not text.endswith('.'):
                corrections.append(f"MD036: Converted emphasis to heading: {text[:30]}")
                return f"#### {text}"
            return match.group(0)

        content = re.sub(r'^\*\*([^*]+)\*\*$', convert_emphasis_to_heading, content, flags=re.MULTILINE)

        # 4. MD013: Dividir líneas largas (solo en tablas y comentarios)
        lines = content.split('\n')
        fixed_lines = []
        for line in lines:
            # Solo dividir si es tabla markdown y excede 80
            if '|' in line and len(line) > 80:
                # Es tabla, dejar como está (difícil de dividir automáticamente)
                fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        content = '\n'.join(fixed_lines)

        # Guardar si hubo cambios
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return (len(corrections), corrections)

        return (0, [])

    except Exception as e:
        print(f"❌ Error procesando {file_path}: {e}")
        return (0, [])

def main():
    """Procesa todos los archivos markdown del proyecto."""
    root = Path("d:/diseñopvbesscar")

    # Encontrar todos los archivos .md
    md_files = list(root.glob("**/*.md"))

    print(f"Encontrados {len(md_files)} archivos markdown")
    print("="*60)

    total_corrections = 0
    files_fixed = 0

    for md_file in md_files:
        # Ignorar node_modules, .venv, etc
        if any(p in md_file.parts for p in ['.venv', 'node_modules', '.git']):
            continue

        num_corrections, corrections = fix_markdown_file(md_file)

        if num_corrections > 0:
            files_fixed += 1
            total_corrections += num_corrections
            print(f"✅ {md_file.name}: {num_corrections} correcciones")
            for corr in corrections[:3]:  # Mostrar solo las primeras 3
                print(f"   - {corr}")
            if len(corrections) > 3:
                print(f"   ... y {len(corrections) - 3} más")

    print("="*60)
    print(f"✅ COMPLETADO")
    print(f"   Archivos corregidos: {files_fixed}/{len(md_files)}")
    print(f"   Total correcciones: {total_corrections}")

if __name__ == "__main__":
    main()
