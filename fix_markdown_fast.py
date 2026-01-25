#!/usr/bin/env python3
"""Corrige errores markdown restantes de forma agresiva."""

import re
from pathlib import Path
from collections import defaultdict

def fix_file(filepath: Path) -> int:
    """Corrige un archivo markdown.

    Returns:
        Número de correcciones aplicadas
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ Error leyendo {filepath.name}: {e}")
        return 0

    corrections = 0
    new_lines = []
    heading_counter = defaultdict(int)

    i = 0
    while i < len(lines):
        line = lines[i]

        # 1. MD040: Agregar bash a ``` vacío
        if line.strip() == '```':
            new_lines.append('```bash\n')
            corrections += 1
            i += 1
            continue

        # 2. MD024: Hacer headings únicos
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            level = heading_match.group(1)
            text = heading_match.group(2).strip()

            heading_counter[text] += 1
            if heading_counter[text] > 1:
                # Agregar número
                new_lines.append(f"{level} {text} ({heading_counter[text]})\n")
                corrections += 1
                i += 1
                continue

        # 3. MD036: Convertir **Título** a #### Título
        emphasis_heading = re.match(r'^\*\*([^*]+)\*\*\s*$', line)
        if emphasis_heading:
            text = emphasis_heading.group(1)
            # Solo si parece título (corto, sin punto final)
            if len(text) < 60 and not text.strip().endswith('.'):
                new_lines.append(f"#### {text}\n")
                corrections += 1
                i += 1
                continue

        # 4. Dejar línea como está
        new_lines.append(line)
        i += 1

    # Guardar si hubo cambios
    if corrections > 0:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            return corrections
        except Exception as e:
            print(f"❌ Error escribiendo {filepath.name}: {e}")
            return 0

    return 0

def main():
    """Procesa todos los MD del proyecto."""
    root = Path("d:/diseñopvbesscar")

    # Archivos específicos con más errores
    priority_files = [
        "CODE_FIXES_OE2_DATA_FLOW.md",
        "TECHNICAL_ANALYSIS_OE2_DATA_FLOW_AGENTS.md",
    ]

    total_corrections = 0

    print("🔧 Corrigiendo archivos markdown...")
    print("="*60)

    # Procesar archivos prioritarios
    for filename in priority_files:
        filepath = root / filename
        if filepath.exists():
            corr = fix_file(filepath)
            if corr > 0:
                total_corrections += corr
                print(f"✅ {filename}: {corr} correcciones")

    # Procesar todos los demás MD
    for md_file in root.glob("**/*.md"):
        # Ignorar carpetas especiales
        if any(p in md_file.parts for p in ['.venv', 'node_modules', '.git', 'analyses']):
            continue

        # Skip si ya lo procesamos
        if md_file.name in priority_files:
            continue

        corr = fix_file(md_file)
        if corr > 0:
            total_corrections += corr
            print(f"✅ {md_file.name}: {corr} correcciones")

    print("="*60)
    print(f"✅ Total correcciones: {total_corrections}")

if __name__ == "__main__":
    main()
