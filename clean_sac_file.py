#!/usr/bin/env python3
"""Herramienta para limpiar y reparar sac.py automáticamente."""

import re
from pathlib import Path

def clean_sac_file():
    """Limpia errores de indentación y sintaxis en sac.py."""
    file_path = Path("src/iquitos_citylearn/oe3/agents/sac.py")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Arreglar except sin cuerpo
    # Patrón: except XXX:\n<siguiente línea sin indent>
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Si es una línea except
        if re.search(r'^\s*except\s+', line) and line.rstrip().endswith(':'):
            fixed_lines.append(line)
            i += 1

            # Verificar si la siguiente línea está indentada
            if i < len(lines):
                next_line = lines[i]
                if next_line.strip() and not (next_line[0].isspace() or next_line.strip() == ''):
                    # Falta indentación, agregar pass
                    indent = ' ' * (len(line) - len(line.lstrip()) + 4)
                    fixed_lines.append(f'{indent}pass')
        else:
            fixed_lines.append(line)
            i += 1

    content = '\n'.join(fixed_lines)

    # 2. Arreglar formato de logger con % (ya corregido antes)
    # 3. Arreglar open() con encoding
    content = re.sub(
        r'open\("([^"]+)",\s*"([^"]+)"\)',
        r'open("\1", "\2", encoding="utf-8")',
        content
    )

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ sac.py limpiado")

if __name__ == "__main__":
    clean_sac_file()
